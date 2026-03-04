#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for Photo Cropper v9.0 PyQt6 Application.

Provides the main application window with all UI components.
v9.0 Features:
    - Keyboard navigation (arrows, Enter, Space)
    - Before/After comparison
    - Crop editor
    - Settings presets
    - Thumbnail grid view
    - Fullscreen preview (F11)
    - Floating action button
    - Undo/Redo history
    - Folder watch mode
    - Multi-language support
"""

import os
import logging
from typing import Any, Optional, List
import threading

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QMenuBar,
    QMenu,
    QToolBar,
    QStatusBar,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFrame,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QGridLayout,
    QSizePolicy,
    QProgressBar,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QSettings, QSize, QThread
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QDragEnterEvent,
    QDropEvent,
    QKeyEvent,
    QCloseEvent,
)

from ..widgets.settings import SettingsPanel
from ..widgets.preview_widget import ImagePreviewWidget
from ..widgets.progress_dialog import ProgressDialog
from ..widgets.histogram_widget import HistogramWidget
from ..widgets.toast_notification import ToastManager
from ..widgets.preset_manager import PresetComboBox, get_preset_manager
from ..widgets.thumbnail_grid_widget import ThumbnailGridWidget
from ..widgets.fullscreen_viewer import FullscreenViewerManager
from ..widgets.floating_action_button import QuickActionFAB
from ..styles.themes import get_theme, get_available_themes
from .batch_actions import BatchActions
from .navigation_actions import NavigationActions
from .preview_actions import PreviewActions
from .feature_actions import FeatureActions
from .dialog_actions import DialogActions
from .preview_worker import PreviewWorker

from ...core.settings_model import AppSettings, SettingsManager
from ...core.image import ImageProcessor
from ...core.batch import BatchProcessor, BatchProgress
from ...core.manual_extract import (
    scale_contour_to_preview,
    normalize_contour_points,
    denormalize_contour_points,
)
from ...core.history_manager import HistoryManager, ImageHolder
from ...core.watch_mode import WatchModeCoordinator
from ...core.smart_enhancer import SmartEnhancer, EnhancementPreset, get_smart_enhancer
from ...core.face import FaceDetector, get_face_detector
from ...core.image_classifier import ImageClassifier, ImageCategory, get_classifier
from ...utils.file_helpers import (
    get_image_files,
    open_file_explorer,
    validate_directory,
    SUPPORTED_IMAGE_FORMATS,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for Photo Cropper.

    Features:
        - Modern PyQt6 UI with dark/light themes
        - Drag and drop support
        - Real-time preview
        - Batch processing with progress
        - Settings persistence
        - Thumbnail grid view (v8.5)
        - Fullscreen preview (v8.5)
        - Undo/Redo history (v8.5)
    """

    VERSION = "9.0"
    TITLE = f"📸 사진 자동 자르기 v{VERSION}"
    preview_process_requested = pyqtSignal(int, str, int, object)
    batch_progress_received = pyqtSignal(object)
    batch_log_received = pyqtSignal(str, str)
    batch_complete_received = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()

        # Initialize managers
        self.settings_manager = SettingsManager()
        self._settings = self.settings_manager.load()

        # Initialize processors
        self.image_processor = ImageProcessor(
            self._settings.algorithm,
            self._settings.processing,
            self._settings.advanced,  # v9.0: Include advanced processing settings
            self._settings.performance,
            debug_settings=self._settings.debug,
        )
        self.batch_processor: Optional[BatchProcessor] = None

        # v8.5: History Manager for Undo/Redo
        self.history_manager = HistoryManager(max_history=50)

        # v8.5: Fullscreen viewer manager
        self.fullscreen_manager = FullscreenViewerManager()

        # v9.0: Watch mode coordinator
        self.watch_mode_coordinator = WatchModeCoordinator(
            settings=self._settings,
            on_log=self._emit_batch_log,
            parent=self,
        )
        self.watch_mode_coordinator.processing_started.connect(
            lambda f: self.status_label.setText(
                f"👁️ 감시 중... 처리 시작: {os.path.basename(f)}"
            )
        )
        self.watch_mode_coordinator.processing_completed.connect(
            self._on_watched_file_complete
        )
        self.watch_mode_coordinator.processing_completed_detailed.connect(
            self._on_watched_file_complete_detailed
        )
        self.watch_mode_coordinator.queue_metrics_updated.connect(
            self._on_watch_queue_metrics
        )

        # State
        self._current_image_path: Optional[str] = None
        self._image_list: List[str] = []  # List of images in input folder
        self._current_image_index: int = -1  # Current image index
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._do_preview)
        self._preview_request_id = 0
        self._latest_preview_request_id = 0
        self._applied_preview_request_id = -1
        self._preview_request_paths: dict[int, str] = {}
        self._preview_settings_revision = 0
        self._preview_settings_snapshot = self._settings.to_dict()
        self._preview_worker_thread: Optional[QThread] = None
        self._preview_worker: Optional[PreviewWorker] = None
        self.progress_dialog: Optional[ProgressDialog] = None

        self._input_path_scan_timer = QTimer(self)
        self._input_path_scan_timer.setSingleShot(True)
        self._input_path_scan_timer.timeout.connect(self._flush_input_path_change)
        self._pending_input_path: str = ""

        # Last processed result for comparison
        self._last_original: Optional[Any] = None
        self._last_processed: Optional[Any] = None
        self._last_detected_contour: Optional[Any] = None
        self._active_input_root: str = ""
        self._batch_contours_norm: dict[str, Any] = {}
        self._batch_contours_edited: set[str] = set()
        self._failed_boundary_files: List[str] = []
        self._manual_extract_thread: Optional[threading.Thread] = None
        self._manual_extract_stop_event = threading.Event()
        self._manual_extract_running = False

        # Action coordinators
        self.preview_actions = PreviewActions(self)
        self.batch_actions = BatchActions(self)
        self.feature_actions = FeatureActions(self)
        self.navigation_actions = NavigationActions(self)
        self.dialog_actions = DialogActions(self)

        # Thread-safe callback bridges
        self.batch_progress_received.connect(self._on_batch_progress)
        self.batch_log_received.connect(self._on_batch_log)
        self.batch_complete_received.connect(self._on_batch_complete)

        # Preview worker
        self._setup_preview_worker()

        # Setup UI
        self._setup_window()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._setup_fab()  # v8.5: Floating Action Button

        # Initialize Toast Manager
        ToastManager.set_parent(self)

        # Apply saved settings
        self._apply_settings(self._settings)
        self._update_batch_edit_controls()

        # Restore window geometry
        self._restore_window_state()

        # Enable drag and drop

        self.setAcceptDrops(True)

    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowTitle(self.TITLE)
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Center on screen
        screen_obj = QApplication.primaryScreen()
        if screen_obj is not None:
            screen = screen_obj.geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )

    def _setup_preview_worker(self):
        """Create background worker thread for preview processing."""
        self._preview_worker_thread = QThread(self)
        self._preview_worker = PreviewWorker()
        self._preview_worker.moveToThread(self._preview_worker_thread)
        self.preview_process_requested.connect(self._preview_worker.process_preview)
        self._preview_worker.preview_ready.connect(self._on_preview_ready)
        self._preview_worker.preview_failed.connect(self._on_preview_failed)
        self._preview_worker_thread.start()

    def _teardown_preview_worker(self):
        """Stop preview worker thread safely."""
        if self._preview_worker_thread is None:
            return
        self._preview_worker_thread.quit()
        self._preview_worker_thread.wait(2000)
        self._preview_worker = None
        self._preview_worker_thread = None

    def _setup_menu(self):
        """Create menu bar."""
        menubar = self.menuBar()
        if menubar is None:
            return

        # File menu
        file_menu = menubar.addMenu("파일(&F)")
        if file_menu is None:
            return

        open_input_action = QAction("입력 폴더 선택(&O)", self)
        open_input_action.setShortcut(QKeySequence("Ctrl+O"))
        open_input_action.triggered.connect(self._select_input_folder)
        file_menu.addAction(open_input_action)

        open_output_action = QAction("출력 폴더 선택", self)
        open_output_action.triggered.connect(self._select_output_folder)
        file_menu.addAction(open_output_action)

        file_menu.addSeparator()

        open_image_action = QAction("이미지 열기(&I)", self)
        open_image_action.setShortcut(QKeySequence("Ctrl+I"))
        open_image_action.triggered.connect(self._open_single_image)
        file_menu.addAction(open_image_action)

        file_menu.addSeparator()

        open_folder_action = QAction("출력 폴더 열기(&E)", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+E"))
        open_folder_action.triggered.connect(self._open_output_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("편집(&E)")
        if edit_menu is None:
            return

        reset_settings_action = QAction("설정 초기화", self)
        reset_settings_action.triggered.connect(self._reset_settings)
        edit_menu.addAction(reset_settings_action)

        # View menu
        view_menu = menubar.addMenu("보기(&V)")
        if view_menu is None:
            return

        self.theme_actions = {}
        for theme_name in get_available_themes():
            action = QAction(f"{theme_name.title()} 테마", self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=theme_name: self._set_theme(t))
            view_menu.addAction(action)
            self.theme_actions[theme_name] = action

        # Tools menu
        tools_menu = menubar.addMenu("도구(&T)")
        if tools_menu is None:
            return

        preview_action = QAction("미리보기(&P)", self)
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        preview_action.triggered.connect(self._request_preview)
        tools_menu.addAction(preview_action)

        tools_menu.addSeparator()

        retry_failed_action = QAction("실패 파일 재처리", self)
        retry_failed_action.triggered.connect(self._retry_failed_files)
        tools_menu.addAction(retry_failed_action)

        # Refresh (F5)
        refresh_action = QAction("새로고침", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._refresh_file_list)
        tools_menu.addAction(refresh_action)

        # Rotate (Ctrl+R)
        rotate_action = QAction("회전(&R)", self)
        rotate_action.setShortcut(QKeySequence("Ctrl+R"))
        rotate_action.triggered.connect(self._rotate_preview)
        tools_menu.addAction(rotate_action)

        tools_menu.addSeparator()

        # v8.0: Compare mode
        compare_action = QAction("Before/After 비교 (&C)", self)
        compare_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        compare_action.triggered.connect(self._show_compare_dialog)
        tools_menu.addAction(compare_action)

        # v8.0: Crop editor
        crop_editor_action = QAction("수동 영역 편집...", self)
        crop_editor_action.triggered.connect(self._show_crop_editor)
        tools_menu.addAction(crop_editor_action)

        tools_menu.addSeparator()

        # v8.0: Duplicate detection
        duplicate_action = QAction("중복 파일 검색...", self)
        duplicate_action.triggered.connect(self._detect_duplicates)
        tools_menu.addAction(duplicate_action)

        tools_menu.addSeparator()

        # v9.0: AI Features menu
        ai_menu = tools_menu.addMenu("🤖 AI 기능")
        if ai_menu is None:
            return

        classification_action = QAction("이미지 자동 분류", self)
        classification_action.triggered.connect(self._show_classification_settings)
        ai_menu.addAction(classification_action)

        face_detect_action = QAction("얼굴 감지 설정", self)
        face_detect_action.triggered.connect(self._show_face_detection_settings)
        ai_menu.addAction(face_detect_action)

        smart_enhance_action = QAction("스마트 보정", self)
        smart_enhance_action.triggered.connect(self._show_smart_enhancement)
        ai_menu.addAction(smart_enhance_action)

        tools_menu.addSeparator()

        # v9.0: Watch Mode toggle
        self.watch_mode_action = QAction("👁️ 폴더 감시 모드", self)
        self.watch_mode_action.setCheckable(True)
        self.watch_mode_action.triggered.connect(self._toggle_watch_mode)
        tools_menu.addAction(self.watch_mode_action)

        tools_menu.addSeparator()

        # v9.0: Multi-compare window
        multi_compare_action = QAction("🖼️ 멀티 이미지 비교", self)
        multi_compare_action.setShortcut(QKeySequence("Ctrl+M"))
        multi_compare_action.triggered.connect(self._show_multi_compare)
        tools_menu.addAction(multi_compare_action)

        tools_menu.addSeparator()

        # v9.0: Profile switching
        profile_menu = tools_menu.addMenu("📋 프로파일")
        if profile_menu is None:
            return

        profile_manager_action = QAction("프로파일 관리...", self)
        profile_manager_action.triggered.connect(self._show_profile_manager)
        profile_menu.addAction(profile_manager_action)

        profile_menu.addSeparator()

        # Quick profile actions will be populated dynamically
        self._profile_menu = profile_menu

        # Help menu
        help_menu = menubar.addMenu("도움말(&H)")
        if help_menu is None:
            return

        help_action = QAction("사용 방법", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Create modern toolbar with glassmorphism styling."""
        toolbar = QToolBar("메인 도구모음")
        toolbar.setObjectName("mainToolBar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # File Operations Group
        open_action = QAction("📂 폴더 열기", self)
        open_action.setToolTip("입력 폴더 선택")
        open_action.triggered.connect(self._select_input_folder)
        toolbar.addAction(open_action)

        output_action = QAction("📁 출력 폴더", self)
        output_action.setToolTip("결과물 저장 위치 확인")
        output_action.triggered.connect(self._open_output_folder)
        toolbar.addAction(output_action)

        toolbar.addSeparator()

        # View Operations Group
        preview_action = QAction("🔍 미리보기", self)
        preview_action.setToolTip("현재 이미지 미리보기 업데이트")
        preview_action.triggered.connect(self._request_preview)
        toolbar.addAction(preview_action)

        rotate_action = QAction("🔄 회전", self)
        rotate_action.setToolTip("시계방향 90도 회전 (Ctrl+R)")
        rotate_action.triggered.connect(self._rotate_preview)
        toolbar.addAction(rotate_action)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Preset Selection (Right aligned)
        preset_label = QLabel("프리셋:")
        preset_label.setStyleSheet(
            "color: #8b949e; margin-right: 8px; font-weight: bold;"
        )
        toolbar.addWidget(preset_label)

        self._preset_combo = PresetComboBox()
        self._preset_combo.setMinimumWidth(140)
        self._preset_combo.preset_selected.connect(self._on_preset_selected)
        toolbar.addWidget(self._preset_combo)

        toolbar.addSeparator()

        # Primary Action - Process Button (Prominent)
        self.process_btn = QPushButton("▶️ 변환 시작")
        self.process_btn.setObjectName("primaryButton")
        self.process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_btn.setToolTip("일괄 처리 시작 (Space)")
        self.process_btn.clicked.connect(self._start_processing)
        toolbar.addWidget(self.process_btn)

    def _setup_central_widget(self):
        """Create central widget with resizable splitters."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Outer splitter for folder card and preview area (vertical)
        outer_splitter = QSplitter(Qt.Orientation.Vertical)
        outer_splitter.setHandleWidth(6)
        outer_splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5), 
                    stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
                height: 6px;
                margin: 2px 0;
            }
            QSplitter::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8), 
                    stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
            }
        """)

        # Folder Selection Card (Compact)
        folder_card = QFrame()
        folder_card.setObjectName("statsFrame")
        folder_card_layout = QVBoxLayout(folder_card)
        folder_card_layout.setContentsMargins(10, 8, 10, 8)
        folder_card_layout.setSpacing(6)

        # Input/Output Grid
        path_grid = QGridLayout()
        path_grid.setSpacing(6)
        path_grid.setContentsMargins(0, 0, 0, 0)
        path_grid.setColumnStretch(1, 1)

        # Input Path
        input_label = QLabel("입력 폴더:")
        input_label.setStyleSheet("font-weight: bold;")
        path_grid.addWidget(input_label, 0, 0)

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText(
            "이미지가 있는 폴더를 선택하거나 드래그하세요..."
        )
        self.input_path_edit.setMinimumHeight(32)
        self.input_path_edit.setTextMargins(8, 0, 8, 0)
        self.input_path_edit.textChanged.connect(self._on_input_path_changed)
        path_grid.addWidget(self.input_path_edit, 0, 1)

        input_browse_btn = QPushButton("찾아보기")
        input_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_browse_btn.setMinimumHeight(32)
        input_browse_btn.clicked.connect(self._select_input_folder)
        path_grid.addWidget(input_browse_btn, 0, 2)

        # Output Path
        output_label = QLabel("출력 폴더:")
        output_label.setStyleSheet("font-weight: bold;")
        path_grid.addWidget(output_label, 1, 0)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("결과물이 저장될 폴더 (자동 설정됨)")
        self.output_path_edit.setMinimumHeight(32)
        self.output_path_edit.setTextMargins(8, 0, 8, 0)
        path_grid.addWidget(self.output_path_edit, 1, 1)

        output_browse_btn = QPushButton("변경")
        output_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        output_browse_btn.setMinimumHeight(32)
        output_browse_btn.clicked.connect(self._select_output_folder)
        path_grid.addWidget(output_browse_btn, 1, 2)

        output_open_btn = QPushButton("변환 폴더 열기")
        output_open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        output_open_btn.setMinimumHeight(32)
        output_open_btn.clicked.connect(self._open_output_folder)
        path_grid.addWidget(output_open_btn, 1, 3)

        folder_card_layout.addLayout(path_grid)

        # Drag & Drop Hint (compact)
        hint_layout = QHBoxLayout()
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_icon = QLabel("💡")
        hint_text = QLabel("팁: 폴더를 이 영역으로 드래그하여 바로 열 수 있습니다.")
        hint_text.setObjectName("subtitleLabel")
        hint_layout.addWidget(hint_icon)
        hint_layout.addWidget(hint_text)
        hint_layout.addStretch()
        folder_card_layout.addLayout(hint_layout)

        edit_nav_layout = QHBoxLayout()
        edit_nav_layout.setContentsMargins(0, 2, 0, 0)

        self.batch_load_btn = QPushButton("폴더 일괄 불러오기")
        self.batch_load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_load_btn.setMinimumHeight(30)
        self.batch_load_btn.clicked.connect(self._load_batch_images_for_edit)
        edit_nav_layout.addWidget(self.batch_load_btn)

        self.batch_failed_btn = QPushButton("실패 파일 수동 보정")
        self.batch_failed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_failed_btn.setMinimumHeight(30)
        self.batch_failed_btn.clicked.connect(self._load_failed_boundary_images_for_edit)
        edit_nav_layout.addWidget(self.batch_failed_btn)

        self.batch_prev_btn = QPushButton("← 이전")
        self.batch_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_prev_btn.setMinimumHeight(30)
        self.batch_prev_btn.clicked.connect(self._navigate_prev)
        edit_nav_layout.addWidget(self.batch_prev_btn)

        self.batch_next_btn = QPushButton("다음 →")
        self.batch_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_next_btn.setMinimumHeight(30)
        self.batch_next_btn.clicked.connect(self._navigate_next)
        edit_nav_layout.addWidget(self.batch_next_btn)

        self.batch_save_edits_btn = QPushButton("편집 저장 추출")
        self.batch_save_edits_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_save_edits_btn.setMinimumHeight(30)
        self.batch_save_edits_btn.clicked.connect(self._save_batch_edited_crops)
        edit_nav_layout.addWidget(self.batch_save_edits_btn)

        self.batch_edit_status_label = QLabel("편집 0/0 | 수정 0")
        self.batch_edit_status_label.setObjectName("subtitleLabel")
        edit_nav_layout.addWidget(self.batch_edit_status_label)
        edit_nav_layout.addStretch()

        folder_card_layout.addLayout(edit_nav_layout)

        # Add folder card to outer splitter
        outer_splitter.addWidget(folder_card)

        # Main splitter (horizontal: preview | settings)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(6)
        main_splitter.setStyleSheet("""
            QSplitter::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5), 
                    stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
                width: 6px;
                margin: 0 2px;
            }
            QSplitter::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8), 
                    stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
            }
        """)

        # Left side: Preview area (Vertical Splitter)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setHandleWidth(6)
        left_splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5), 
                    stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
                height: 6px;
                margin: 2px 0;
            }
            QSplitter::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8), 
                    stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
            }
        """)

        self.preview_widget = ImagePreviewWidget()
        self.preview_widget.contour_edited.connect(self._on_preview_contour_edited)
        left_splitter.addWidget(self.preview_widget)

        # Histogram
        self.histogram_widget = HistogramWidget()
        left_splitter.addWidget(self.histogram_widget)

        # Set initial sizes (Give most space to preview)
        left_splitter.setStretchFactor(0, 5)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setSizes([500, 100])

        main_splitter.addWidget(left_splitter)

        # Right side: Settings panel
        self.settings_panel = SettingsPanel(self._settings)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.settings_panel.preview_requested.connect(self._request_preview)
        self.settings_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.settings_panel)

        # Set splitter sizes
        main_splitter.setSizes([850, 320])

        # Add main splitter to outer splitter
        outer_splitter.addWidget(main_splitter)

        # Configure outer splitter sizes (folder: small, preview: large)
        outer_splitter.setStretchFactor(0, 0)  # Folder card: don't stretch
        outer_splitter.setStretchFactor(1, 1)  # Main area: stretch
        outer_splitter.setSizes([110, 700])  # Initial sizes

        main_layout.addWidget(outer_splitter)

    def _setup_statusbar(self):
        """Create modern status bar with progress indication."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.setSizeGripEnabled(True)

        # Main status
        self.status_label = QLabel(" 준비 완료")
        self.status_label.setStyleSheet("font-weight: bold; margin-left: 4px;")
        self.statusbar.addWidget(self.status_label, 1)

        # Progress Bar (Hidden by default)
        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setMaximumHeight(16)
        self.status_progress.setVisible(False)
        self.statusbar.addWidget(self.status_progress)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.statusbar.addPermanentWidget(line)

        # Image Info Badge
        self.image_info_badge = QLabel(" 이미지: - ")
        self.image_info_badge.setStyleSheet("""
            background-color: rgba(128, 128, 128, 0.2);
            border-radius: 4px;
            padding: 2px 8px;
            margin: 0 4px;
        """)
        self.statusbar.addPermanentWidget(self.image_info_badge)

        # File Count Badge
        self.file_count_badge = QLabel(" 파일: 0개 ")
        self.file_count_badge.setStyleSheet("""
            background-color: rgba(9, 105, 218, 0.2);
            color: #58a6ff;
            border-radius: 4px;
            padding: 2px 8px;
            margin: 0 4px;
            font-weight: bold;
        """)
        self.statusbar.addPermanentWidget(self.file_count_badge)

    def _setup_fab(self):
        """Setup floating action button for quick actions (v8.5)."""
        self.fab = QuickActionFAB(self)

        # Connect QuickActionFAB signals to handlers
        self.fab.preview_requested.connect(self._request_preview)
        self.fab.process_requested.connect(self._start_processing)
        self.fab.rotate_requested.connect(self._rotate_preview)
        self.fab.fullscreen_requested.connect(self._show_fullscreen)

        # Position FAB in bottom-right corner
        self.fab.show()

    def _show_fullscreen(self):
        """Show fullscreen preview of current image (v8.5)."""
        images: List[str] = []
        if (
            isinstance(self._current_image_path, str)
            and self._current_image_path
            and os.path.isfile(self._current_image_path)
        ):
            images = [self._current_image_path]
        else:
            images = [path for path in self._image_list if os.path.isfile(path)]

        if not images:
            self.status_label.setText("전체화면으로 표시할 이미지가 없습니다")
            return

        current_index = 0
        if self._current_image_path in images:
            current_index = images.index(self._current_image_path)
        self.fullscreen_manager.show(images, current_index=current_index, parent=self)

    def _undo(self):
        """Undo last action (v8.5)."""
        self.feature_actions.undo()

    def _redo(self):
        """Redo last undone action (v8.5)."""
        self.feature_actions.redo()

    # ========================================
    # Settings and Theme
    # ========================================

    def _bump_preview_settings_snapshot(self):
        """Refresh immutable settings snapshot for preview worker."""
        self._preview_settings_revision += 1
        self._preview_settings_snapshot = self._settings.to_dict()

    def _apply_settings(self, settings: AppSettings):
        """Apply settings to UI and processors."""
        self._settings = settings

        # Update processors
        self.image_processor.update_settings(
            settings.algorithm,
            settings.processing,
            settings.advanced,  # v9.0: Include advanced processing settings
            settings.performance,
            settings.debug,
        )
        self._bump_preview_settings_snapshot()

        # Apply theme
        self._set_theme(settings.ui.theme)

        # Update paths
        if settings.last_input_path:
            self.input_path_edit.setText(settings.last_input_path)
        if settings.last_output_path:
            self.output_path_edit.setText(settings.last_output_path)

    @pyqtSlot(AppSettings)
    def _on_settings_changed(self, settings: AppSettings):
        """Handle settings change from panel."""
        self._settings = settings
        self.image_processor.update_settings(
            settings.algorithm,
            settings.processing,
            settings.advanced,  # v9.0: Include advanced processing settings
            settings.performance,
            settings.debug,
        )
        self._bump_preview_settings_snapshot()

        self.batch_actions.update_settings(settings)
        self.watch_mode_coordinator.update_settings(settings)

        # Check theme change
        if settings.ui.theme != self._get_current_theme():
            self._set_theme(settings.ui.theme)

        # v8.5: Auto-save settings with debounce (2 seconds)
        self._schedule_auto_save()

    def _schedule_auto_save(self):
        """Schedule auto-save with debounce to prevent excessive saves."""
        # Create timer if not exists
        if not hasattr(self, "_auto_save_timer"):
            self._auto_save_timer = QTimer()
            self._auto_save_timer.setSingleShot(True)
            self._auto_save_timer.timeout.connect(self._do_auto_save)

        # Restart timer (debounce)
        self._auto_save_timer.start(2000)  # 2 second delay

    def _do_auto_save(self):
        """Perform auto-save of settings."""
        self._settings.last_input_path = self.input_path_edit.text()
        self._settings.last_output_path = self.output_path_edit.text()

        if self.settings_manager.save(self._settings):
            self.status_label.setText("✓ 설정 자동 저장됨")
        else:
            self.status_label.setText("⚠ 설정 저장 실패")

    def _set_theme(self, theme_name: str):
        """Apply theme stylesheet."""
        stylesheet = get_theme(theme_name)
        self.setStyleSheet(stylesheet)

        # Update theme menu checkmarks
        for name, action in self.theme_actions.items():
            action.setChecked(name == theme_name)

        # Update settings
        if self._settings.ui.theme != theme_name:
            self._settings.ui.theme = theme_name

    def _get_current_theme(self) -> str:
        """Get current theme name."""
        for name, action in self.theme_actions.items():
            if action.isChecked():
                return name
        return "dark"

    def _toggle_theme(self):
        """Toggle between dark and light themes."""
        current = self._get_current_theme()
        new_theme = "light" if current == "dark" else "dark"
        self._set_theme(new_theme)

    def _reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "설정 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            default_settings = self.settings_manager.get_default()
            self.settings_panel.settings = default_settings
            self._apply_settings(default_settings)
            self.statusbar.showMessage("설정이 초기화되었습니다", 3000)

    # ========================================
    # Folder Selection
    # ========================================

    def _select_input_folder(self):
        """Open dialog to select input folder."""
        path = QFileDialog.getExistingDirectory(
            self, "입력 폴더 선택", self.input_path_edit.text() or ""
        )

        if path:
            self.input_path_edit.setText(path)

            # Auto-set output folder
            if not self.output_path_edit.text():
                output_path = os.path.join(path, "output_cropped")
                self.output_path_edit.setText(output_path)

    def _select_output_folder(self):
        """Open dialog to select output folder."""
        path = QFileDialog.getExistingDirectory(
            self, "출력 폴더 선택", self.output_path_edit.text() or ""
        )

        if path:
            self.output_path_edit.setText(path)

    def _on_input_path_changed(self, path: str):
        """Handle input path change."""
        self._pending_input_path = path or ""
        self._input_path_scan_timer.start(250)

    def _flush_input_path_change(self):
        """Apply debounced input-path side effects."""
        path = self._pending_input_path
        if os.path.isdir(path):
            normalized = os.path.abspath(path)
            if normalized != self._active_input_root:
                self._active_input_root = normalized
                self._batch_contours_norm.clear()
                self._batch_contours_edited.clear()
                self._failed_boundary_files = []
                self._last_detected_contour = None
            files = get_image_files(path)
            self.file_count_badge.setText(f" 파일: {len(files)}개 ")
            self.file_count_badge.setStyleSheet("""
                background-color: rgba(46, 160, 67, 0.2);
                color: #3fb950;
                border-radius: 4px;
                padding: 2px 8px;
                margin: 0 4px;
                font-weight: bold;
            """)
            self._update_image_list()
        else:
            self.file_count_badge.setText(" 파일: 0개 ")
            self.file_count_badge.setStyleSheet("""
                background-color: rgba(128, 128, 128, 0.2);
                color: #8b949e;
                border-radius: 4px;
                padding: 2px 8px;
                margin: 0 4px;
            """)
            self._active_input_root = ""
            self._image_list = []
            self._current_image_index = -1
            self._current_image_path = None
            self._failed_boundary_files = []
        self._update_batch_edit_controls()

    def _open_output_folder(self):
        """Open output folder in file explorer."""
        path = self.output_path_edit.text()
        if path and os.path.exists(path):
            open_file_explorer(path)
        else:
            QMessageBox.warning(self, "경고", "출력 폴더가 존재하지 않습니다.")

    # ========================================
    # Drag and Drop
    # ========================================

    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]):
        """Handle drag enter."""
        if a0 is None:
            return
        event = a0
        mime_data = event.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, a0: Optional[QDropEvent]):
        """Handle drop."""
        if a0 is None:
            return
        event = a0
        mime_data = event.mimeData()
        urls = mime_data.urls() if mime_data is not None else []
        if urls:
            path = urls[0].toLocalFile()

            if os.path.isdir(path):
                self.input_path_edit.setText(path)
            elif os.path.isfile(path):
                # Single image - load for preview
                ext = os.path.splitext(path)[1].lower()
                if ext in SUPPORTED_IMAGE_FORMATS:
                    self._current_image_path = path
                    self._request_preview()

    # ========================================
    # Preview
    # ========================================

    def _open_single_image(self):
        """Open single image for preview."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 선택",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;모든 파일 (*.*)",
        )

        if path:
            self._current_image_path = path
            self._request_preview()

    def _request_preview(self):
        """Request preview with debounce."""
        self.preview_actions.request_preview()

    def _resolve_preview_path(self) -> Optional[str]:
        """Resolve target image path for preview."""
        return self.preview_actions.resolve_preview_path()

    def _update_image_info_badge(self, image_path: str):
        """Update image info badge for current preview target."""
        self.preview_actions.update_image_info_badge(image_path)

    def _scale_contour_to_preview(self, preview_image, crop_result):
        """Scale contour points from source coordinates to current preview image."""
        return scale_contour_to_preview(preview_image, crop_result)

    @pyqtSlot(object)
    def _on_preview_contour_edited(self, contour_points):
        """Apply manually edited contour from original preview pane."""
        self.preview_actions.on_preview_contour_edited(contour_points)

    def _normalize_contour_points(self, points, image_shape):
        """Normalize contour points to 0..1 coordinates."""
        return normalize_contour_points(points, image_shape)

    def _denormalize_contour_points(self, normalized_points, image_shape):
        """Convert normalized contour points back to pixel coordinates."""
        return denormalize_contour_points(normalized_points, image_shape)

    def _update_batch_edit_controls(self):
        """Update batch edit navigation/save controls."""
        total = len(self._image_list) if self._image_list else 0
        current = self._current_image_index + 1 if total > 0 and self._current_image_index >= 0 else 0
        edited = sum(
            1 for path in self._batch_contours_edited if path in set(self._image_list or [])
        )
        failed = len(self._failed_boundary_files)
        if hasattr(self, "batch_edit_status_label"):
            self.batch_edit_status_label.setText(
                f"편집 {current}/{total} | 수정 {edited} | 실패 {failed}"
            )

        busy = bool(
            self._manual_extract_running
            or (self.batch_processor and self.batch_processor.is_running)
        )
        has_files = total > 0
        has_failed_targets = failed > 0
        if hasattr(self, "batch_prev_btn"):
            self.batch_prev_btn.setEnabled(has_files and total > 1 and not busy)
        if hasattr(self, "batch_next_btn"):
            self.batch_next_btn.setEnabled(has_files and total > 1 and not busy)
        if hasattr(self, "batch_save_edits_btn"):
            self.batch_save_edits_btn.setEnabled(has_files and not busy)
        if hasattr(self, "batch_failed_btn"):
            self.batch_failed_btn.setEnabled(has_failed_targets and not busy)
        if hasattr(self, "batch_load_btn"):
            self.batch_load_btn.setEnabled(not busy)

    def _load_batch_images_for_edit(self):
        """Load all images from input folder for navigation/editing."""
        input_path = self.input_path_edit.text()
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self, "경고", f"입력 폴더 오류: {error}")
            return

        if not self.output_path_edit.text():
            self.output_path_edit.setText(os.path.join(input_path, "output_cropped"))

        self._update_image_list()
        if not self._image_list:
            QMessageBox.information(self, "알림", "불러올 이미지가 없습니다.")
            self._update_batch_edit_controls()
            return

        self._current_image_index = 0
        self._current_image_path = self._image_list[0]
        self._request_preview()
        self._update_navigation_status()
        self._update_batch_edit_controls()

    def _collect_boundary_failed_files(self, results: list) -> List[str]:
        """Collect absolute paths for files failed due to boundary detection."""
        return self.batch_actions.collect_boundary_failed_files(results)

    def _load_failed_boundary_images_for_edit(self):
        """Load only boundary-failed files for manual contour adjustment."""
        self.batch_actions.load_failed_boundary_images_for_edit()

    def _save_batch_edited_crops(self):
        """Save cropped results for all images using edited (or auto) contours."""
        self.batch_actions.save_batch_edited_crops()

    def _run_manual_extract_worker(
        self,
        input_path: str,
        output_path: str,
        files: list,
        contours_norm: dict,
        settings_snapshot: dict,
    ):
        """Worker: extract all images with manual/auto contour fallback."""
        _ = input_path
        self.batch_actions.run_manual_extract_worker(
            output_path=output_path,
            files=files,
            contours_norm=contours_norm,
            settings_snapshot=settings_snapshot,
        )

    def _do_preview(self):
        """Dispatch preview processing to background worker."""
        self.preview_actions.do_preview()

    @pyqtSlot(int, object)
    def _on_preview_ready(self, request_id: int, preview_result: object):
        """Apply preview result from background worker."""
        self.preview_actions.on_preview_ready(request_id, preview_result)

    @pyqtSlot(int, str)
    def _on_preview_failed(self, request_id: int, message: str):
        """Handle preview worker failure."""
        self.preview_actions.on_preview_failed(request_id, message)

    # ========================================
    # Batch Processing
    # ========================================

    def _start_processing(self):
        """Start batch processing."""
        self.batch_actions.start_processing()

    def _cancel_processing(self):
        """Cancel batch processing."""
        self.batch_actions.cancel_processing()

    def _emit_batch_progress(self, progress: BatchProgress):
        """Bridge batch progress callback into UI thread."""
        self.batch_progress_received.emit(progress)

    def _emit_batch_log(self, message: str, level: str):
        """Bridge batch log callback into UI thread."""
        self.batch_log_received.emit(message, level)

    def _emit_batch_complete(self, progress: BatchProgress, results: list):
        """Bridge batch complete callback into UI thread."""
        self.batch_complete_received.emit(progress, results)

    def _on_batch_progress(self, progress: BatchProgress):
        """Handle batch progress update."""
        self.batch_actions.on_batch_progress(progress)

    def _on_batch_log(self, message: str, level: str):
        """Handle batch log message."""
        self.batch_actions.on_batch_log(message, level)

    @pyqtSlot(int)
    def _on_progress_dialog_finished(self, _result: int):
        """Release closed progress dialog to avoid stale UI updates."""
        dialog = self.sender()
        if dialog is None:
            return
        self.batch_actions.on_progress_dialog_finished(dialog)

    def _on_batch_complete(self, progress: BatchProgress, results: list):
        """Handle batch processing completion."""
        self.batch_actions.on_batch_complete(progress, results)

    def _retry_failed_files(self):
        """Retry failed files from last batch."""
        self.batch_actions.retry_failed_files()

    # ========================================
    # Help
    # ========================================

    def _show_help(self):
        """Show help dialog."""
        self.dialog_actions.show_help()

    def _show_about(self):
        """Show about dialog."""
        self.dialog_actions.show_about()

    # ========================================
    # Window Events
    # ========================================

    # NOTE: closeEvent is defined below at line 1145+

    def _save_window_state(self):
        """Save window geometry and state."""
        settings = QSettings("PhotoCropper", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def _restore_window_state(self):
        """Restore window geometry and state."""
        settings = QSettings("PhotoCropper", "MainWindow")
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    def _refresh_file_list(self):
        """Refresh file list from input folder."""
        input_path = self.input_path_edit.text()
        if input_path and os.path.isdir(input_path):
            files = get_image_files(input_path)
            self.file_count_badge.setText(f" 파일: {len(files)}개 ")
            self.status_label.setText(f"파일 목록 새로고침 완료: {len(files)}개 파일")
            # Auto preview first file
            if files:
                self._current_image_path = files[0]
                self._request_preview()

    def _rotate_preview(self):
        """
        Rotate the current preview image by 90 degrees clockwise.
        """
        if not self._current_image_path or not os.path.exists(self._current_image_path):
            self.status_label.setText("회전할 이미지가 없습니다")
            return

        # Load current image
        image = self.image_processor.load_image(self._current_image_path)
        if image is None:
            self.status_label.setText("이미지를 불러올 수 없습니다")
            return

        # Rotate image
        rotated = self.image_processor.rotate_image(image, 90)

        # Update preview
        self.preview_widget.set_original_image(rotated)
        self.preview_widget.set_processed_image(None)
        self.status_label.setText("이미지를 시계방향 90도 회전했습니다")

    # ========================================
    # Keyboard Navigation (v8.0)
    # ========================================

    def keyPressEvent(self, a0: Optional[QKeyEvent]):
        """Handle keyboard shortcuts for navigation."""
        if a0 is None:
            return
        event = a0
        key = event.key()

        # Arrow keys for navigation
        if key == Qt.Key.Key_Left:
            self._navigate_prev()
            event.accept()
            return
        elif key == Qt.Key.Key_Right:
            self._navigate_next()
            event.accept()
            return

        # Enter for preview
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._request_preview()
            event.accept()
            return

        # Space for start processing
        elif key == Qt.Key.Key_Space:
            if not (self.batch_processor and self.batch_processor.is_running) and not self._manual_extract_running:
                self._start_processing()
            event.accept()
            return

        # R for rotate
        elif key == Qt.Key.Key_R and not event.modifiers():
            self._rotate_preview()
            event.accept()
            return

        # C for compare mode
        elif key == Qt.Key.Key_C and not event.modifiers():
            self._show_compare_dialog()
            event.accept()
            return

        # F11 for fullscreen (v8.5)
        elif key == Qt.Key.Key_F11:
            self._show_fullscreen()
            event.accept()
            return

        # Ctrl+Z for undo (v8.5)
        elif (
            key == Qt.Key.Key_Z
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._undo()
            event.accept()
            return

        # Ctrl+Y for redo (v8.5)
        elif (
            key == Qt.Key.Key_Y
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._redo()
            event.accept()
            return

        super().keyPressEvent(event)

    def _update_image_list(self):
        """Update the list of images in the input folder."""
        self.navigation_actions.update_image_list()

    def _navigate_prev(self):
        """Navigate to previous image in list."""
        self.navigation_actions.navigate_prev()

    def _navigate_next(self):
        """Navigate to next image in list."""
        self.navigation_actions.navigate_next()

    def _update_navigation_status(self):
        """Update status bar with navigation info."""
        self.navigation_actions.update_navigation_status()

    def _show_compare_dialog(self):
        """Show before/after comparison dialog."""
        self.dialog_actions.show_compare_dialog()

    def _show_crop_editor(self):
        """Show manual crop editor dialog."""
        self.dialog_actions.show_crop_editor()

    def _on_crop_applied(self, cropped_image, dialog: Optional[QDialog] = None):
        """Handle crop applied from editor."""
        self.feature_actions.on_crop_applied(cropped_image, dialog)

    def _detect_duplicates(self):
        """Detect duplicate files in input folder."""
        input_path = self.input_path_edit.text()
        if not input_path or not os.path.isdir(input_path):
            QMessageBox.warning(self, "경고", "유효한 입력 폴더를 선택하세요.")
            return

        self.status_label.setText("중복 파일 검색 중...")

        from ...utils.file_helpers import detect_duplicates

        files = get_image_files(
            input_path, recursive=self._settings.file_management.recursive_search
        )
        if not files:
            QMessageBox.information(self, "결과", "검색할 이미지 파일이 없습니다.")
            return

        duplicates = detect_duplicates(files, method="size+hash")

        if not duplicates:
            QMessageBox.information(self, "결과", "중복 파일이 발견되지 않았습니다.")
            self.status_label.setText("중복 파일 없음")
            return

        dup_count = sum(len(v) - 1 for v in duplicates.values() if len(v) > 1)

        msg = f"총 {dup_count}개의 중복 파일이 발견되었습니다.\n\n"
        for hash_key, paths in list(duplicates.items())[:5]:
            if len(paths) > 1:
                msg += f"• {os.path.basename(paths[0])} ({len(paths)}개 중복)\n"

        if len(duplicates) > 5:
            msg += f"\n... 외 {len(duplicates) - 5}개 그룹"

        QMessageBox.information(self, "중복 검색 결과", msg)
        self.status_label.setText(f"중복 파일 {dup_count}개 발견")

    # ========================================
    # v9.0 Feature Handlers
    # ========================================

    def _show_classification_settings(self):
        """Show AI classification settings dialog."""
        from ...core.settings_model import ClassificationSettings

        # Toggle classification in settings panel
        enabled = not self._settings.classification.enabled
        self._settings.classification.enabled = enabled

        if enabled:
            ToastManager.success(
                "🤖 AI 분류 활성화됨 - 배치 처리 시 이미지가 자동 분류됩니다"
            )
            self.status_label.setText("AI 분류 활성화됨")
        else:
            ToastManager.info("AI 분류 비활성화됨")
            self.status_label.setText("AI 분류 비활성화됨")

        self._schedule_auto_save()

    def _show_face_detection_settings(self):
        """Show face detection settings dialog."""
        enabled = not self._settings.face_detection.enabled
        self._settings.face_detection.enabled = enabled

        if enabled:
            ToastManager.success("👤 얼굴 감지 활성화됨 - 인물 사진 자동 크롭 조정")
            self.status_label.setText("얼굴 감지 활성화됨")
            # Re-run preview with face detection
            if self._current_image_path:
                self._do_preview_with_faces()
        else:
            ToastManager.info("얼굴 감지 비활성화됨")
            self.status_label.setText("얼굴 감지 비활성화됨")

        self._schedule_auto_save()

    def _do_preview_with_faces(self):
        """Preview with face detection overlay."""
        if not self._current_image_path:
            return

        from ...core.face import get_face_detector
        import cv2
        import numpy as np

        detector = get_face_detector(
            use_dnn=getattr(self._settings.face_detection, "use_dnn", False),
            min_face_size=getattr(self._settings.face_detection, "min_face_size", 30),
        )

        # Load and detect faces
        image = cv2.imdecode(
            np.fromfile(self._current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR
        )

        if image is not None:
            result = detector.detect(image, detect_eyes=True, suggest_crop=True)

            if result.has_faces:
                # Draw face overlays
                overlay = detector.draw_detections(image, result)
                self.preview_widget.set_original_image(image, overlay)
                self.status_label.setText(f"👤 {len(result.faces)}개 얼굴 감지됨")
                ToastManager.info(f"👤 {len(result.faces)}개 얼굴 감지")
            else:
                self.status_label.setText("얼굴을 감지하지 못했습니다")

    def _show_smart_enhancement(self):
        """Show smart enhancement options."""
        if self._last_original is None:
            self.status_label.setText("먼저 이미지를 로드하세요")
            return

        from ...core.smart_enhancer import get_smart_enhancer, EnhancementPreset

        enhancer = get_smart_enhancer()
        preset_names = enhancer.get_preset_names()

        # Show preset selection dialog
        from PyQt6.QtWidgets import QInputDialog

        presets = [
            name for _, name in preset_names.items() if _ != EnhancementPreset.NONE
        ]
        preset, ok = QInputDialog.getItem(
            self, "스마트 보정", "적용할 프리셋을 선택하세요:", presets, 0, False
        )

        if ok and preset:
            # Find preset enum
            selected_preset = None
            for p, name in preset_names.items():
                if name == preset:
                    selected_preset = p
                    break

            if selected_preset:
                result = enhancer.apply_preset(self._last_original, selected_preset)
                self._last_processed = result.image
                self.preview_widget.set_processed_image(result.image)

                effects = ", ".join(result.applied_effects[:3])
                ToastManager.success(f"✨ {preset} 적용됨: {effects}")
                self.status_label.setText(f"스마트 보정 적용: {preset}")

    def _show_multi_compare(self):
        """Show multi-image comparison window."""
        from ..widgets.multi_compare_window import MultiCompareWindow

        if (
            not hasattr(self, "_multi_compare_window")
            or self._multi_compare_window is None
        ):
            self._multi_compare_window = MultiCompareWindow(self)

        # Add current images if available
        if self._last_original is not None:
            self._multi_compare_window.add_image(self._last_original, "원본", slot=0)

        if self._last_processed is not None:
            self._multi_compare_window.add_image(self._last_processed, "처리됨", slot=1)

        self._multi_compare_window.show()
        self._multi_compare_window.raise_()
        self._multi_compare_window.activateWindow()

    def _show_profile_manager(self):
        """Show profile manager dialog."""
        from ...core.batch_profile_manager import get_batch_profile_manager
        from PyQt6.QtWidgets import QInputDialog

        manager = get_batch_profile_manager()
        profiles = manager.list_profiles()

        if not profiles:
            ToastManager.warning("저장된 프로파일이 없습니다")
            return

        # Show profile selection
        profile, ok = QInputDialog.getItem(
            self, "프로파일 선택", "적용할 프로파일:", profiles, 0, False
        )

        if ok and profile:
            if manager.apply_profile(profile, self._settings):
                self.settings_panel.settings = self._settings
                self.image_processor.update_settings(
                    self._settings.algorithm,
                    self._settings.processing,
                    self._settings.advanced,
                    self._settings.performance,
                    self._settings.debug,
                )
                ToastManager.success(f"📋 '{profile}' 프로파일 적용됨")
                self.status_label.setText(f"프로파일 적용: {profile}")

                if self._settings.ui.auto_preview:
                    self._request_preview()

    def _on_preset_selected(self, preset_name: str):
        """Handle preset selection from dropdown."""
        if not preset_name:
            return

        manager = get_preset_manager()
        if manager.apply_preset(preset_name, self._settings):
            self.settings_panel.settings = self._settings
            self.image_processor.update_settings(
                self._settings.algorithm,
                self._settings.processing,
                self._settings.advanced,
                self._settings.performance,
                self._settings.debug,
            )
            self.status_label.setText(f"'{preset_name}' 프리셋 적용됨")
            ToastManager.success(f"🎨 {preset_name} 프리셋 적용")

            if self._settings.ui.auto_preview:
                self._request_preview()

    # ========================================
    # Watch Mode (v9.0)
    # ========================================

    def _toggle_watch_mode(self, checked: bool):
        """Toggle folder watch mode for automatic processing."""
        if checked:
            self._start_watch_mode()
        else:
            self._stop_watch_mode()

    def _start_watch_mode(self):
        """Start watching folder for new files."""
        input_path = self.input_path_edit.text()
        output_path = self.output_path_edit.text()
        watch_settings = getattr(self._settings, "watch_mode", None)

        start_result = self.watch_mode_coordinator.start(
            input_path=input_path,
            output_path=output_path,
            watch_settings=watch_settings,
        )

        if start_result.output_path and start_result.output_path != output_path:
            self.output_path_edit.setText(start_result.output_path)

        if not start_result.success:
            self.watch_mode_action.setChecked(False)
            if start_result.error_code == "invalid_input":
                QMessageBox.warning(self, "경고", "유효한 입력 폴더를 선택하세요.")
            elif start_result.error_code == "invalid_output":
                ToastManager.error("출력 폴더 준비 실패")
                if start_result.message:
                    self.status_label.setText(
                        f"폴더 감시 시작 실패: {start_result.message}"
                    )
            else:
                ToastManager.error("폴더 감시 시작 실패")
            return

        watch_root = input_path.strip() or self.input_path_edit.text()
        self.watch_mode_action.setText("👁️ 폴더 감시 중지")
        ToastManager.success(f"👁️ 폴더 감시 모드 시작: {watch_root}")
        self.status_label.setText(f"👁️ 폴더 감시 중: {watch_root}")

    def _stop_watch_mode(self):
        """Stop watching folder."""
        self.watch_mode_coordinator.stop()

        self.watch_mode_action.setText("👁️ 폴더 감시 모드")
        ToastManager.info("폴더 감시 모드 중지됨")
        self.status_label.setText("폴더 감시 중지됨")

    def _on_watched_file_complete(self, filepath: str, success: bool):
        """Handle completion of watched file processing."""
        filename = os.path.basename(filepath)
        if success:
            self.status_label.setText(f"👁️ 처리 완료: {filename}")
            ToastManager.success(f"✅ 자동 처리 완료: {filename}")
        else:
            self.status_label.setText(f"👁️ 처리 실패: {filename}")
            ToastManager.warning(f"⚠️ 자동 처리 실패: {filename}")

    def _on_watched_file_complete_detailed(
        self,
        filepath: str,
        success: bool,
        status: str,
        message: str,
        wait_ms: int,
    ):
        """Handle detailed completion status for watch mode."""
        filename = os.path.basename(filepath)
        status_key = (status or "").lower()
        wait_text = f"{int(wait_ms)}ms"

        if success:
            if status_key == "skipped":
                detail = message or "skip"
                self.status_label.setText(
                    f"👁️ 스킵: {filename} ({detail}, 대기 {wait_text})"
                )
                ToastManager.info(f"ℹ️ 자동 처리 스킵: {filename} ({detail})")
            else:
                self.status_label.setText(f"👁️ 처리 완료: {filename} (대기 {wait_text})")
                ToastManager.success(f"✅ 자동 처리 완료: {filename}")
            return

        reason = status_key or "failed"
        detail = message or reason
        self.status_label.setText(f"👁️ 처리 실패: {filename} ({reason}, 대기 {wait_text})")
        ToastManager.warning(f"⚠️ 자동 처리 실패: {filename} - {detail}")

    def _on_watch_queue_metrics(self, queue_size: int, avg_wait_ms: int):
        """Show queue metrics while watch mode is active."""
        if not self.watch_mode_coordinator.is_active:
            return
        self.status_label.setText(
            f"👁️ 감시 중... 대기열: {int(queue_size)}개, 평균 대기: {int(avg_wait_ms)}ms"
        )

    def closeEvent(self, a0: Optional[QCloseEvent]):
        """Handle window close event."""
        if a0 is None:
            return
        event = a0
        batch_running = bool(self.batch_processor and self.batch_processor.is_running)
        manual_running = bool(self._manual_extract_running)

        # Check if any processing is running
        if batch_running or manual_running:
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "작업이 진행 중입니다. 정말 종료하시겠습니까?\n종료 시 진행 중인 작업은 중단됩니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            if manual_running:
                self._manual_extract_stop_event.set()
            if batch_running and self.batch_processor:
                self.batch_processor.request_stop()

        if self.progress_dialog is not None:
            try:
                self.progress_dialog.close()
            except Exception:
                pass
            self.progress_dialog = None

        # Save settings
        self._settings.last_input_path = self.input_path_edit.text()
        self._settings.last_output_path = self.output_path_edit.text()
        self.settings_manager.save(self._settings)

        # Save window state
        self._save_window_state()

        # Cleanup batch processor
        self.batch_actions.cleanup()

        # Clear history to free memory
        if self.history_manager:
            self.history_manager.clear()

        # v9.0: Stop watch mode if active
        if self.watch_mode_coordinator.is_active:
            self.watch_mode_coordinator.stop()

        self._teardown_preview_worker()

        event.accept()
