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
from typing import Optional, List
import numpy as np
import threading
import time

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
    QDialogButtonBox,
    QGridLayout,
    QSizePolicy,
    QProgressBar,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, pyqtSignal, QSettings, QSize, QObject, QThread
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
    QDragEnterEvent,
    QDropEvent,
    QKeyEvent,
    QShortcut,
)

from ..widgets.settings import SettingsPanel
from ..widgets.preview_widget import ImagePreviewWidget
from ..widgets.progress_dialog import ProgressDialog
from ..widgets.histogram_widget import HistogramWidget
from ..widgets.toast_notification import ToastManager
from ..widgets.compare_widget import BeforeAfterCompareWidget
from ..widgets.crop_editor_widget import CropEditorWidget
from ..widgets.preset_manager import PresetComboBox, get_preset_manager
from ..widgets.thumbnail_grid_widget import ThumbnailGridWidget
from ..widgets.fullscreen_viewer import FullscreenViewerManager
from ..widgets.floating_action_button import QuickActionFAB
from ..styles.themes import get_theme, get_available_themes

from ...core.settings_model import AppSettings, SettingsManager
from ...core.image import ImageProcessor
from ...core.batch import BatchProcessor, BatchProgress, FileResult, ProcessStatus
from ...core.history_manager import HistoryManager, ImageHolder
from ...core.folder_watcher import FolderWatcher, AutoProcessor
from ...core.smart_enhancer import SmartEnhancer, EnhancementPreset, get_smart_enhancer
from ...core.face import FaceDetector, get_face_detector
from ...core.image_classifier import ImageClassifier, ImageCategory, get_classifier
from ...utils.file_helpers import (
    get_image_files,
    get_unique_filename,
    open_file_explorer,
    validate_directory,
    SUPPORTED_IMAGE_FORMATS,
)

logger = logging.getLogger(__name__)


class PreviewWorker(QObject):
    """Background preview worker running in a dedicated QThread."""

    preview_ready = pyqtSignal(int, object)
    preview_failed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._processor: Optional[ImageProcessor] = None
        self._settings_revision: int = -1

    @pyqtSlot(int, str, int, object)
    def process_preview(
        self,
        request_id: int,
        image_path: str,
        settings_revision: int,
        settings_snapshot: object,
    ):
        try:
            if not image_path or not os.path.exists(image_path):
                self.preview_failed.emit(request_id, "미리보기할 파일이 없습니다.")
                return

            if isinstance(settings_snapshot, AppSettings):
                app_settings = settings_snapshot
            elif isinstance(settings_snapshot, dict):
                app_settings = AppSettings.from_dict(settings_snapshot)
            else:
                app_settings = AppSettings()

            if self._processor is None:
                self._processor = ImageProcessor(
                    app_settings.algorithm,
                    app_settings.processing,
                    app_settings.advanced,
                    app_settings.performance,
                    debug_settings=app_settings.debug,
                )
                self._settings_revision = settings_revision
            elif settings_revision != self._settings_revision:
                self._processor.update_settings(
                    app_settings.algorithm,
                    app_settings.processing,
                    app_settings.advanced,
                    app_settings.performance,
                    app_settings.debug,
                )
                self._settings_revision = settings_revision

            preview_result = self._processor.process_preview(
                image_path,
                max_size=800,
                debug_tag="preview",
            )
            self.preview_ready.emit(request_id, preview_result)
        except Exception as e:
            self.preview_failed.emit(request_id, str(e))


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
        self.watch_batch_processor: Optional[BatchProcessor] = None

        # v8.5: History Manager for Undo/Redo
        self.history_manager = HistoryManager(max_history=50)

        # v8.5: Fullscreen viewer manager
        self.fullscreen_manager = FullscreenViewerManager()

        # v9.0: Auto processor for watch mode
        self.auto_processor: Optional[AutoProcessor] = None

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
        self._preview_request_paths = {}
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
        self._last_original: Optional[any] = None
        self._last_processed: Optional[any] = None
        self._last_detected_contour = None
        self._active_input_root: str = ""
        self._batch_contours_norm = {}
        self._batch_contours_edited = set()
        self._failed_boundary_files: List[str] = []
        self._manual_extract_thread: Optional[threading.Thread] = None
        self._manual_extract_stop_event = threading.Event()
        self._manual_extract_running = False

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
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

    def _setup_preview_worker(self):
        """Create background worker thread for preview processing."""
        self._preview_worker_thread = QThread(self)
        self._preview_worker = PreviewWorker()
        self._preview_worker.moveToThread(self._preview_worker_thread)
        self.preview_process_requested.connect(
            self._preview_worker.process_preview,
            Qt.ConnectionType.QueuedConnection,
        )
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

        # File menu
        file_menu = menubar.addMenu("파일(&F)")

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

        reset_settings_action = QAction("설정 초기화", self)
        reset_settings_action.triggered.connect(self._reset_settings)
        edit_menu.addAction(reset_settings_action)

        # View menu
        view_menu = menubar.addMenu("보기(&V)")

        self.theme_actions = {}
        for theme_name in get_available_themes():
            action = QAction(f"{theme_name.title()} 테마", self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, t=theme_name: self._set_theme(t))
            view_menu.addAction(action)
            self.theme_actions[theme_name] = action

        # Tools menu
        tools_menu = menubar.addMenu("도구(&T)")

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

        profile_manager_action = QAction("프로파일 관리...", self)
        profile_manager_action.triggered.connect(self._show_profile_manager)
        profile_menu.addAction(profile_manager_action)

        profile_menu.addSeparator()

        # Quick profile actions will be populated dynamically
        self._profile_menu = profile_menu

        # Help menu
        help_menu = menubar.addMenu("도움말(&H)")

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
        if self._last_processed is not None:
            images = [self._last_processed]
            if self._last_original is not None:
                images.insert(0, self._last_original)
            self.fullscreen_manager.show_fullscreen(images, start_index=len(images) - 1)
        elif self._last_original is not None:
            self.fullscreen_manager.show_fullscreen([self._last_original])
        else:
            self.status_label.setText("전체화면으로 표시할 이미지가 없습니다")

    def _undo(self):
        """Undo last action (v8.5)."""
        if self.history_manager.can_undo():
            state = self.history_manager.undo()
            if state and state.image is not None:
                self._last_processed = state.image
                self.preview_widget.set_processed_image(state.image)
                self.status_label.setText("실행 취소됨")
                ToastManager.info("↩️ 실행 취소")
        else:
            self.status_label.setText("실행 취소할 항목이 없습니다")

    def _redo(self):
        """Redo last undone action (v8.5)."""
        if self.history_manager.can_redo():
            state = self.history_manager.redo()
            if state and state.image is not None:
                self._last_processed = state.image
                self.preview_widget.set_processed_image(state.image)
                self.status_label.setText("다시 실행됨")
                ToastManager.info("↪️ 다시 실행")
        else:
            self.status_label.setText("다시 실행할 항목이 없습니다")

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

        if self.watch_batch_processor:
            self.watch_batch_processor.update_settings(settings)

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

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop."""
        urls = event.mimeData().urls()
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
        self._preview_timer.start(200)  # 200ms debounce

    def _resolve_preview_path(self) -> Optional[str]:
        """Resolve target image path for preview."""
        if self._current_image_path and os.path.exists(self._current_image_path):
            return self._current_image_path

        input_path = self.input_path_edit.text()
        if input_path and os.path.isdir(input_path):
            files = get_image_files(input_path)
            if files:
                self._current_image_path = files[0]
                return self._current_image_path
        return None

    def _update_image_info_badge(self, image_path: str):
        """Update image info badge for current preview target."""
        try:
            info = self.image_processor.get_image_info(image_path)
            if info:
                w, h, _ = info
                file_size_kb = os.path.getsize(image_path) / 1024
                if file_size_kb >= 1024:
                    size_str = f"{file_size_kb / 1024:.1f} MB"
                else:
                    size_str = f"{file_size_kb:.0f} KB"
                self.image_info_badge.setText(f"📷 {w}×{h}px | {size_str}")
                return
        except Exception:
            pass
        self.image_info_badge.setText("이미지: -")

    def _scale_contour_to_preview(self, preview_image, crop_result):
        """Scale contour points from source coordinates to current preview image."""
        if preview_image is None or crop_result is None:
            return None
        contour = getattr(crop_result, "contour_points", None)
        if contour is None:
            return None
        original_size = getattr(crop_result, "original_size", None)
        if not original_size or len(original_size) < 2:
            return None
        orig_w = float(original_size[0] or 0)
        orig_h = float(original_size[1] or 0)
        if orig_w <= 0 or orig_h <= 0:
            return None
        preview_h, preview_w = preview_image.shape[:2]
        sx = float(preview_w) / orig_w
        sy = float(preview_h) / orig_h
        points = np.array(contour, dtype=np.float32).reshape((-1, 2)).copy()
        points[:, 0] *= sx
        points[:, 1] *= sy
        return points

    @pyqtSlot(object)
    def _on_preview_contour_edited(self, contour_points):
        """Apply manually edited contour from original preview pane."""
        if self._last_original is None:
            return
        try:
            points = np.array(contour_points, dtype=np.float32).reshape((-1, 2))
        except Exception:
            return
        if len(points) != 4:
            return

        self._last_detected_contour = points.copy()
        current_path = self._current_image_path
        if current_path:
            normalized = self._normalize_contour_points(
                points,
                self._last_original.shape if self._last_original is not None else None,
            )
            if normalized is not None:
                self._batch_contours_norm[current_path] = normalized
                self._batch_contours_edited.add(current_path)
                self._update_batch_edit_controls()

        try:
            from ...core.advanced import AdvancedImageProcessor

            processor = AdvancedImageProcessor()
            result = processor.correct_perspective(self._last_original, points)
            if result.success and result.image is not None:
                self.preview_widget.set_processed_image(result.image)
                self._last_processed = result.image.copy()
                self.status_label.setText("외곽선 수동 편집 반영됨")
            else:
                self.status_label.setText("외곽선 편집 반영 실패")
        except Exception as e:
            self.status_label.setText(f"외곽선 편집 오류: {e}")

    def _normalize_contour_points(self, points, image_shape):
        """Normalize contour points to 0..1 coordinates."""
        if points is None or image_shape is None:
            return None
        try:
            pts = np.array(points, dtype=np.float32).reshape((-1, 2)).copy()
            if len(pts) != 4:
                return None
            h, w = image_shape[:2]
            if w <= 0 or h <= 0:
                return None
            pts[:, 0] = np.clip(pts[:, 0] / float(w), 0.0, 1.0)
            pts[:, 1] = np.clip(pts[:, 1] / float(h), 0.0, 1.0)
            return pts
        except Exception:
            return None

    def _denormalize_contour_points(self, normalized_points, image_shape):
        """Convert normalized contour points back to pixel coordinates."""
        if normalized_points is None or image_shape is None:
            return None
        try:
            pts = np.array(normalized_points, dtype=np.float32).reshape((-1, 2)).copy()
            if len(pts) != 4:
                return None
            h, w = image_shape[:2]
            if w <= 0 or h <= 0:
                return None
            pts[:, 0] = np.clip(pts[:, 0] * float(w), 0.0, float(max(0, w - 1)))
            pts[:, 1] = np.clip(pts[:, 1] * float(h), 0.0, float(max(0, h - 1)))
            return pts
        except Exception:
            return None

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

    @staticmethod
    def _is_boundary_detection_failure(message: str) -> bool:
        """Return True when message indicates boundary detection failure."""
        if not message:
            return False
        msg = str(message).strip()
        msg_lower = msg.lower()
        if "failed to detect photo boundary" in msg_lower:
            return True
        if "boundary" in msg_lower and ("detect" in msg_lower or "failed" in msg_lower):
            return True
        if "외곽선" in msg and ("탐지" in msg or "실패" in msg):
            return True
        if "경계" in msg and ("탐지" in msg or "실패" in msg):
            return True
        return False

    def _collect_boundary_failed_files(self, results: list) -> List[str]:
        """Collect absolute paths for files failed due to boundary detection."""
        failed_names = []
        for result in results or []:
            if getattr(result, "status", None) != ProcessStatus.FAILED:
                continue
            message = str(getattr(result, "message", "") or "")
            if not self._is_boundary_detection_failure(message):
                continue
            filename = str(getattr(result, "filename", "") or "").strip()
            if filename:
                failed_names.append(filename)

        if not failed_names:
            return []

        input_root = self.input_path_edit.text().strip()
        candidate_paths = []

        if self.batch_processor:
            for entry in self.batch_processor.failed_files:
                if not entry:
                    continue
                if os.path.isabs(entry):
                    candidate_paths.append(os.path.normpath(entry))
                elif input_root:
                    candidate_paths.append(os.path.normpath(os.path.join(input_root, entry)))

        for path in self._image_list or []:
            if path:
                candidate_paths.append(os.path.normpath(path))

        if input_root and os.path.isdir(input_root):
            recursive = bool(
                getattr(self._settings.file_management, "recursive_search", False)
            )
            for path in get_image_files(input_root, recursive=recursive):
                candidate_paths.append(os.path.normpath(path))

        candidates_by_name = {}
        for path in candidate_paths:
            key = os.path.basename(path).lower()
            if not key:
                continue
            bucket = candidates_by_name.setdefault(key, [])
            if path not in bucket:
                bucket.append(path)

        resolved = []
        unresolved = []
        for name in failed_names:
            chosen = None
            if os.path.isabs(name) and os.path.exists(name):
                chosen = os.path.normpath(name)
            else:
                key = os.path.basename(name).lower()
                bucket = candidates_by_name.get(key, [])
                if bucket:
                    chosen = bucket.pop(0)
            if chosen and chosen not in resolved:
                resolved.append(chosen)
            else:
                unresolved.append(name)

        if unresolved:
            logger.warning(
                "Failed to resolve boundary-failed files: %s",
                ", ".join(unresolved[:10]),
            )

        return resolved

    def _load_failed_boundary_images_for_edit(self):
        """Load only boundary-failed files for manual contour adjustment."""
        if self._manual_extract_running or (self.batch_processor and self.batch_processor.is_running):
            QMessageBox.warning(self, "경고", "처리 작업이 진행 중입니다. 완료/취소 후 실행하세요.")
            return

        if not self._failed_boundary_files:
            QMessageBox.information(self, "알림", "수동 보정할 경계 실패 파일이 없습니다.")
            return

        files = [path for path in self._failed_boundary_files if os.path.exists(path)]
        if not files:
            self._failed_boundary_files = []
            QMessageBox.information(
                self,
                "알림",
                "경계 실패 파일을 찾지 못했습니다. 폴더 경로를 다시 확인해주세요.",
            )
            self._update_batch_edit_controls()
            return

        self._image_list = files
        self._current_image_index = 0
        self._current_image_path = files[0]
        self.status_label.setText(
            f"경계 실패 파일 수동 보정 모드: {len(files)}개 (4점 클릭 또는 점 드래그)"
        )
        ToastManager.info(f"경계 실패 {len(files)}개 파일만 불러왔습니다")
        self._request_preview()
        self._update_navigation_status()
        self._update_batch_edit_controls()

    def _save_batch_edited_crops(self):
        """Save cropped results for all images using edited (or auto) contours."""
        if self._manual_extract_running:
            QMessageBox.information(self, "알림", "편집 저장 추출이 이미 진행 중입니다.")
            return
        if self.batch_processor and self.batch_processor.is_running:
            QMessageBox.warning(self, "경고", "기존 배치 작업이 진행 중입니다.")
            return

        input_path = self.input_path_edit.text()
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self, "경고", f"입력 폴더 오류: {error}")
            return

        if not self._image_list:
            self._update_image_list()
        if not self._image_list:
            QMessageBox.information(self, "알림", "추출할 이미지가 없습니다.")
            return

        output_path = self.output_path_edit.text().strip()
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            self.output_path_edit.setText(output_path)
        os.makedirs(output_path, exist_ok=True)

        edited_count = sum(
            1 for path in self._image_list if path in self._batch_contours_edited
        )
        reply = QMessageBox.question(
            self,
            "편집 저장 추출",
            (
                f"총 {len(self._image_list)}장 추출을 시작합니다.\n"
                f"수정된 외곽선 {edited_count}장, 나머지는 자동 탐색 결과를 사용합니다.\n\n"
                "진행하시겠습니까?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        contours_snapshot = {}
        for path, points in self._batch_contours_norm.items():
            if points is None:
                continue
            try:
                contours_snapshot[path] = np.array(points, dtype=np.float32).reshape((-1, 2)).copy()
            except Exception:
                continue

        settings_snapshot = self._settings.to_dict()
        files_snapshot = list(self._image_list)

        self._manual_extract_stop_event.clear()
        self._manual_extract_running = True
        self._update_batch_edit_controls()

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.cancel_requested.connect(
            self._cancel_processing,
            Qt.ConnectionType.QueuedConnection,
        )
        self.progress_dialog.open_output_requested.connect(self._open_output_folder)
        self.progress_dialog.set_output_path(output_path)
        self.progress_dialog.finished.connect(self._on_progress_dialog_finished)
        self.progress_dialog.show()

        self._manual_extract_thread = threading.Thread(
            target=self._run_manual_extract_worker,
            args=(
                input_path,
                output_path,
                files_snapshot,
                contours_snapshot,
                settings_snapshot,
            ),
            daemon=True,
        )
        self._manual_extract_thread.start()

    def _run_manual_extract_worker(
        self,
        input_path: str,
        output_path: str,
        files: list,
        contours_norm: dict,
        settings_snapshot: dict,
    ):
        """Worker: extract all images with manual/auto contour fallback."""
        start = time.time()
        results = []
        total = len(files)

        try:
            from ...core.settings_model import AppSettings
            from ...core.advanced import AdvancedImageProcessor
            from ...core.image import ImageProcessor

            settings = AppSettings.from_dict(settings_snapshot or {})
            processor = ImageProcessor(
                settings.algorithm,
                settings.processing,
                settings.advanced,
                settings.performance,
                debug_settings=settings.debug,
            )
            perspective_processor = AdvancedImageProcessor(
                use_gpu=settings.performance.use_gpu
            )

            progress = BatchProgress(total=total, is_running=True, is_cancelled=False)
            self.batch_progress_received.emit(progress)

            for index, path in enumerate(files, 1):
                filename = os.path.basename(path)
                progress.current_file = filename
                self.batch_progress_received.emit(progress)

                if self._manual_extract_stop_event.is_set():
                    progress.is_cancelled = True
                    break

                file_start = time.time()
                file_result = None
                try:
                    image = processor.load_image(path)
                    if image is None:
                        raise RuntimeError("이미지를 불러올 수 없습니다.")

                    contour_norm = contours_norm.get(path)
                    used_manual = False
                    cropped = None

                    contour_valid = False
                    if contour_norm is not None:
                        try:
                            contour_valid = (
                                len(
                                    np.array(contour_norm, dtype=np.float32).reshape(
                                        (-1, 2)
                                    )
                                )
                                == 4
                            )
                        except Exception:
                            contour_valid = False

                    if contour_valid:
                        contour_orig = self._denormalize_contour_points(
                            contour_norm,
                            image.shape,
                        )
                        if contour_orig is not None:
                            corr = perspective_processor.correct_perspective(
                                image,
                                contour_orig.astype(np.float32),
                                auto_detect=False,
                            )
                            if corr.success and corr.image is not None:
                                cropped = processor._apply_post_processing(corr.image)
                                used_manual = True

                    if cropped is None:
                        auto_result = processor.process_image(path)
                        if not auto_result.success or auto_result.image is None:
                            raise RuntimeError(auto_result.message or "외곽선 탐지 실패")
                        cropped = auto_result.image

                    base_name = os.path.splitext(filename)[0] + "_cropped"
                    extension = "." + settings.output.output_format.lower()
                    out_path = get_unique_filename(
                        output_path,
                        base_name,
                        extension,
                        add_timestamp=bool(settings.output.add_timestamp),
                    )
                    ok, save_msg, size_kb = processor.save_image(
                        cropped,
                        out_path,
                        output_format=settings.output.output_format,
                        jpg_quality=settings.output.jpg_quality,
                        png_compression=settings.output.png_compression,
                        webp_quality=settings.output.webp_quality,
                    )
                    if not ok:
                        raise RuntimeError(save_msg or "저장 실패")

                    mode_label = "수동" if used_manual else "자동"
                    file_result = FileResult(
                        filename=filename,
                        status=ProcessStatus.SUCCESS,
                        message=f"{mode_label} 외곽선 적용",
                        output_path=out_path,
                        file_size_kb=float(size_kb or 0.0),
                        processing_time_ms=(time.time() - file_start) * 1000.0,
                    )
                    self.batch_log_received.emit(
                        f"[{index}/{total}] 완료: {filename} ({mode_label})",
                        "success",
                    )
                except Exception as e:
                    file_result = FileResult(
                        filename=filename,
                        status=ProcessStatus.FAILED,
                        message=str(e),
                        processing_time_ms=(time.time() - file_start) * 1000.0,
                    )
                    self.batch_log_received.emit(
                        f"[{index}/{total}] 실패: {filename} - {e}",
                        "error",
                    )

                results.append(file_result)
                progress.processed = len(results)
                if file_result.status == ProcessStatus.SUCCESS:
                    progress.success += 1
                elif file_result.status == ProcessStatus.SKIPPED:
                    progress.skipped += 1
                else:
                    progress.failed += 1
                elapsed_ms = (time.time() - start) * 1000.0
                progress.total_time_ms = elapsed_ms
                progress.avg_time_per_file_ms = (
                    elapsed_ms / progress.processed if progress.processed > 0 else 0.0
                )
                self.batch_progress_received.emit(progress)

            progress.is_running = False
            progress.current_file = ""
            self.batch_progress_received.emit(progress)
            self.batch_complete_received.emit(progress, results)
        finally:
            self._manual_extract_running = False
            self._manual_extract_thread = None
            self._manual_extract_stop_event.clear()

    def _do_preview(self):
        """Dispatch preview processing to background worker."""
        image_path = self._resolve_preview_path()
        if not image_path:
            return

        self._preview_request_id += 1
        request_id = self._preview_request_id
        self._latest_preview_request_id = request_id
        self._preview_request_paths[request_id] = image_path
        if len(self._preview_request_paths) > 50:
            old_keys = sorted(self._preview_request_paths.keys())[:-50]
            for key in old_keys:
                self._preview_request_paths.pop(key, None)

        self.status_label.setText(f"미리보기 처리 중: {os.path.basename(image_path)}")
        self._update_image_info_badge(image_path)

        self.preview_process_requested.emit(
            request_id,
            image_path,
            self._preview_settings_revision,
            self._preview_settings_snapshot,
        )

    @pyqtSlot(int, object)
    def _on_preview_ready(self, request_id: int, preview_result: object):
        """Apply preview result from background worker."""
        preview_path = self._preview_request_paths.pop(request_id, None)
        if request_id != self._latest_preview_request_id:
            return
        if request_id == self._applied_preview_request_id:
            return

        if preview_result is None:
            self.status_label.setText("미리보기 실패: 결과 없음")
            return

        preview_contour = None
        if preview_result.original_preview is not None:
            auto_contour = self._scale_contour_to_preview(
                preview_result.original_preview,
                preview_result.crop_result,
            )
            saved_norm = (
                self._batch_contours_norm.get(preview_path)
                if preview_path
                else None
            )
            if saved_norm is not None:
                preview_contour = self._denormalize_contour_points(
                    saved_norm, preview_result.original_preview.shape
                )
            else:
                preview_contour = auto_contour
                if preview_path and auto_contour is not None:
                    norm = self._normalize_contour_points(
                        auto_contour, preview_result.original_preview.shape
                    )
                    if norm is not None:
                        self._batch_contours_norm[preview_path] = norm
            self.preview_widget.set_original_image(
                preview_result.original_preview,
                preview_result.overlay_preview,
                preview_contour,
            )
            self.histogram_widget.set_image(preview_result.original_preview)
            self._last_original = preview_result.original_preview
            if preview_path:
                self._current_image_path = preview_path

        crop_result = preview_result.crop_result
        self._last_detected_contour = (
            preview_contour.copy() if preview_contour is not None else None
        )
        if crop_result.success and crop_result.image is not None:
            self.preview_widget.set_processed_image(crop_result.image)
            self._last_processed = crop_result.image
            stage = (
                crop_result.detection_stage.value
                if crop_result.detection_stage
                else "Unknown"
            )
            self.status_label.setText(f"미리보기 성공 ({stage})")
        else:
            self.preview_widget.set_processed_image(None)
            self._last_processed = None
            self.status_label.setText(f"미리보기 실패: {crop_result.message}")

        self._applied_preview_request_id = request_id
        self._update_batch_edit_controls()

    @pyqtSlot(int, str)
    def _on_preview_failed(self, request_id: int, message: str):
        """Handle preview worker failure."""
        self._preview_request_paths.pop(request_id, None)
        if request_id != self._latest_preview_request_id:
            return
        self.preview_widget.set_processed_image(None)
        self._last_processed = None
        self._last_detected_contour = None
        self.status_label.setText(f"미리보기 오류: {message}")
        self._update_batch_edit_controls()

    # ========================================
    # Batch Processing
    # ========================================

    def _start_processing(self):
        """Start batch processing."""
        if self._manual_extract_running:
            QMessageBox.warning(
                self,
                "경고",
                "편집 저장 추출이 진행 중입니다. 먼저 해당 작업을 취소하거나 완료하세요.",
            )
            return

        input_path = self.input_path_edit.text()
        output_path = self.output_path_edit.text()

        # Validate input
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self, "경고", f"입력 폴더 오류: {error}")
            return

        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            self.output_path_edit.setText(output_path)

        # Get files
        recursive = bool(
            getattr(self._settings.file_management, "recursive_search", False)
        )
        files = get_image_files(input_path, recursive=recursive)
        if not files:
            QMessageBox.information(self, "알림", "처리할 이미지 파일이 없습니다.")
            return

        # Cleanup previous batch processor if exists
        if self.batch_processor:
            self.batch_processor.cleanup()

        # Create batch processor
        self.batch_processor = BatchProcessor(self._settings)
        self.batch_processor.set_callbacks(
            on_progress=self._emit_batch_progress,
            on_log=self._emit_batch_log,
            on_complete=self._emit_batch_complete,
        )

        # Show progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.cancel_requested.connect(
            self._cancel_processing,
            Qt.ConnectionType.QueuedConnection,
        )
        self.progress_dialog.open_output_requested.connect(self._open_output_folder)
        self.progress_dialog.set_output_path(output_path)
        self.progress_dialog.finished.connect(self._on_progress_dialog_finished)
        self.progress_dialog.show()

        # Start processing (keep absolute paths to avoid basename collisions)
        self.batch_processor.start_async(input_path, output_path, files)
        self._update_batch_edit_controls()

    def _cancel_processing(self):
        """Cancel batch processing."""
        if self._manual_extract_running:
            self._manual_extract_stop_event.set()
            self.status_label.setText("편집 저장 추출 중단 요청됨")
            return
        if self.batch_processor:
            self.batch_processor.request_stop()

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
        if self.progress_dialog is not None and self.progress_dialog.isVisible():
            self.progress_dialog.update_progress(progress)

    def _on_batch_log(self, message: str, level: str):
        """Handle batch log message."""
        if self.progress_dialog is not None and self.progress_dialog.isVisible():
            self.progress_dialog.log_message(message, level)

    @pyqtSlot(int)
    def _on_progress_dialog_finished(self, _result: int):
        """Release closed progress dialog to avoid stale UI updates."""
        dialog = self.sender()
        if dialog is None:
            return
        if self.progress_dialog is dialog:
            self.progress_dialog = None
        try:
            dialog.deleteLater()
        except Exception:
            pass

    def _on_batch_complete(self, progress: BatchProgress, results: list):
        """Handle batch processing completion."""
        # Update progress dialog with completion
        if self.progress_dialog is not None and self.progress_dialog.isVisible():
            self.progress_dialog.update_progress(progress)
            # Log final summary
            self.progress_dialog.log_message(
                f"처리 완료: {progress.success}개 성공, {progress.failed}개 실패, {progress.skipped}개 건너뜀",
                "success" if progress.failed == 0 else "warning",
            )

        if progress.is_cancelled:
            self.status_label.setText(
                f"작업 취소됨: {progress.success}개 성공, {progress.failed}개 실패"
            )
            ToastManager.info("⏹️ 작업이 취소되었습니다")
        else:
            self.status_label.setText(
                f"완료: {progress.success}개 성공, {progress.failed}개 실패"
            )
            if progress.failed == 0:
                ToastManager.success(f"✅ {progress.success}개 파일 처리 완료!")
            else:
                ToastManager.warning(
                    f"⚠️ {progress.success}개 성공, {progress.failed}개 실패"
                )

        boundary_failed_files = self._collect_boundary_failed_files(results)
        self._failed_boundary_files = boundary_failed_files
        if boundary_failed_files and not progress.is_cancelled:
            failed_count = len(boundary_failed_files)
            reply = QMessageBox.question(
                self,
                "경계 실패 파일 감지",
                (
                    f"경계 자동 탐지 실패 파일 {failed_count}개가 있습니다.\n"
                    "해당 파일만 따로 불러와 수동으로 경계를 지정할 수 있습니다.\n\n"
                    "지금 실패 파일 수동 보정 모드로 이동하시겠습니까?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._load_failed_boundary_images_for_edit()

        # v9.0: Show system notification if enabled
        if self._settings.notification.enabled and not progress.is_cancelled:
            try:
                from ..utils.system_notification import get_notification_manager

                notifier = get_notification_manager()

                if progress.failed == 0:
                    notifier.notify_success(
                        "배치 처리 완료", f"{progress.success}개 파일 처리 완료!"
                    )
                else:
                    notifier.notify_warning(
                        "배치 처리 완료",
                        f"{progress.success}개 성공, {progress.failed}개 실패",
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(f"System notification error: {e}")

        # Auto-open output folder if enabled
        if self._settings.ui.open_output_on_complete and not progress.is_cancelled:
            output_path = self.output_path_edit.text()
            if output_path and os.path.isdir(output_path):
                open_file_explorer(output_path)

        self._update_batch_edit_controls()

    def _retry_failed_files(self):
        """Retry failed files from last batch."""
        if self.batch_processor and self.batch_processor.failed_files:
            failed = self.batch_processor.failed_files
            reply = QMessageBox.question(
                self,
                "재처리",
                f"{len(failed)}개의 실패한 파일을 재처리하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                input_path = self.input_path_edit.text()
                output_path = self.output_path_edit.text()

                self.batch_processor = BatchProcessor(self._settings)
                self.batch_processor.set_callbacks(
                    on_progress=self._emit_batch_progress,
                    on_log=self._emit_batch_log,
                    on_complete=self._emit_batch_complete,
                )

                self.progress_dialog = ProgressDialog(self)
                self.progress_dialog.cancel_requested.connect(
                    self._cancel_processing,
                    Qt.ConnectionType.QueuedConnection,
                )
                self.progress_dialog.open_output_requested.connect(
                    self._open_output_folder
                )
                self.progress_dialog.set_output_path(output_path)
                self.progress_dialog.finished.connect(
                    self._on_progress_dialog_finished
                )
                self.progress_dialog.show()

                self.batch_processor.start_async(input_path, output_path, failed)
                self._update_batch_edit_controls()
        else:
            QMessageBox.information(self, "알림", "재처리할 실패 파일이 없습니다.")

    # ========================================
    # Help
    # ========================================

    def _show_help(self):
        """Show help dialog."""
        help_text = """🔧 사용 방법

1. 입력 폴더 선택: 처리할 이미지가 있는 폴더
2. 출력 폴더 선택: 결과를 저장할 폴더 (선택사항)
3. 설정 조정: 오른쪽 패널에서 설정 변경
4. 미리보기: Ctrl+P로 한 장 테스트
5. 변환 시작: 전체 이미지 처리

💡 팁
• 이미지를 드래그 앤 드롭으로 열 수 있습니다
• 마우스 휠로 미리보기 확대/축소
• Ctrl+클릭 드래그로 미리보기 이동

⚙️ 3단계+ 탐색 알고리즘
1단계: 다중 스케일 Canny Edge
2단계: Adaptive Threshold
3단계: Gradient Analysis (Sobel)
4단계: Harris Corner Detection (선택)"""

        QMessageBox.information(self, "사용 방법", help_text)

    def _show_about(self):
        """Show about dialog."""
        about_text = f"""사진 자동 자르기 v{self.VERSION}

3단계+ 지능형 CV 알고리즘으로
다양한 배경에서 사진을 자동으로 검출하고 자릅니다.

주요 기능:
• 다중 스케일 적응형 검출 알고리즘
• CLAHE 대비 향상
• 실시간 미리보기 (확대/축소 지원)
• 다크/라이트 테마
• 드래그 앤 드롭 지원
• 배치 처리 및 진행 상황 추적

기술: OpenCV, NumPy, PyQt6"""

        QMessageBox.about(self, "정보", about_text)

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

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts for navigation."""
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
        input_path = self.input_path_edit.text()
        if input_path and os.path.isdir(input_path):
            # Check if recursive search is enabled
            recursive = self._settings.file_management.recursive_search
            self._image_list = get_image_files(input_path, recursive=recursive)
            self.file_count_badge.setText(f" 파일: {len(self._image_list)}개 ")

            # Reset index
            if self._image_list:
                self._current_image_index = 0
                self._current_image_path = self._image_list[0]
            else:
                self._current_image_index = -1
                self._current_image_path = None
        else:
            self._image_list = []
            self._current_image_index = -1

        self._update_batch_edit_controls()

    def _navigate_prev(self):
        """Navigate to previous image in list."""
        if self._manual_extract_running:
            return

        if not self._image_list:
            self._update_image_list()

        if not self._image_list:
            self.status_label.setText("탐색할 이미지가 없습니다")
            return

        # Move to previous
        if self._current_image_index > 0:
            self._current_image_index -= 1
        else:
            self._current_image_index = len(self._image_list) - 1  # Wrap around

        self._current_image_path = self._image_list[self._current_image_index]
        self._request_preview()
        self._update_navigation_status()
        self._update_batch_edit_controls()

    def _navigate_next(self):
        """Navigate to next image in list."""
        if self._manual_extract_running:
            return

        if not self._image_list:
            self._update_image_list()

        if not self._image_list:
            self.status_label.setText("탐색할 이미지가 없습니다")
            return

        # Move to next
        if self._current_image_index < len(self._image_list) - 1:
            self._current_image_index += 1
        else:
            self._current_image_index = 0  # Wrap around

        self._current_image_path = self._image_list[self._current_image_index]
        self._request_preview()
        self._update_navigation_status()
        self._update_batch_edit_controls()

    def _update_navigation_status(self):
        """Update status bar with navigation info."""
        if self._image_list and self._current_image_index >= 0:
            total = len(self._image_list)
            current = self._current_image_index + 1
            filename = (
                os.path.basename(self._current_image_path)
                if self._current_image_path
                else ""
            )
            self.status_label.setText(
                f"[{current}/{total}] {filename} (← → 탐색, Enter 미리보기, Space 처리)"
            )

    def _show_compare_dialog(self):
        """Show before/after comparison dialog."""
        if self._last_original is None or self._last_processed is None:
            self.status_label.setText(
                "비교할 이미지가 없습니다. 먼저 미리보기를 실행하세요."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Before/After 비교")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        compare_widget = BeforeAfterCompareWidget()
        compare_widget.set_images(self._last_original, self._last_processed)
        layout.addWidget(compare_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dialog.close)
        layout.addWidget(btn_box)

        dialog.exec()

    def _show_crop_editor(self):
        """Show manual crop editor dialog."""
        source_path = self._resolve_preview_path()
        if source_path is None and self._last_original is None:
            self.status_label.setText(
                "편집할 이미지가 없습니다. 먼저 이미지를 불러오세요."
            )
            return

        if not self._image_list:
            self._update_image_list()

        dialog = QDialog(self)
        dialog.setWindowTitle("수동 영역 편집")
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout(dialog)

        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("← 이전 사진")
        next_btn = QPushButton("다음 사진 →")
        nav_hint = QLabel("외곽선 점을 드래그해 조정하세요 (←/→ 이동)")
        nav_hint.setObjectName("subtitleLabel")
        nav_pos_label = QLabel("")
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        nav_layout.addWidget(nav_hint)
        nav_layout.addStretch()
        nav_layout.addWidget(nav_pos_label)
        layout.addLayout(nav_layout)

        crop_editor = CropEditorWidget()
        crop_editor.crop_applied.connect(lambda img: self._on_crop_applied(img, None))
        crop_editor.crop_cancelled.connect(dialog.close)
        layout.addWidget(crop_editor)

        state = {"index": self._current_image_index}

        def _set_detected_contour(contour_points):
            if contour_points is None:
                crop_editor.set_rectangle_mode()
                return
            try:
                points = []
                for point in contour_points:
                    if point is None or len(point) < 2:
                        continue
                    points.append((float(point[0]), float(point[1])))
                if len(points) != 4:
                    crop_editor.set_rectangle_mode()
                    return
                crop_editor.set_perspective_points(points)
            except Exception:
                crop_editor.set_rectangle_mode()

        def _update_editor_title(path: Optional[str]):
            filename = os.path.basename(path) if path else "현재 이미지"
            if self._image_list and state["index"] >= 0:
                nav_pos_label.setText(f"{state['index'] + 1}/{len(self._image_list)}")
            else:
                nav_pos_label.setText("단일")
            dialog.setWindowTitle(f"수동 영역 편집 - {filename}")

        def _load_editor_image(path: Optional[str]) -> bool:
            if not path or not os.path.exists(path):
                return False
            try:
                preview_result = self.image_processor.process_preview(
                    path,
                    max_size=1200,
                    debug_tag="editor",
                )
            except Exception as e:
                QMessageBox.warning(
                    dialog, "경고", f"이미지를 불러올 수 없습니다.\n{os.path.basename(path)}\n\n{e}"
                )
                return False

            if preview_result is None or preview_result.original_preview is None:
                return False

            crop_editor.set_image(preview_result.original_preview)

            crop_result = preview_result.crop_result
            contour = self._scale_contour_to_preview(
                preview_result.original_preview,
                crop_result,
            )
            self._last_detected_contour = contour.copy() if contour is not None else None
            _set_detected_contour(contour)

            self.preview_widget.set_original_image(
                preview_result.original_preview,
                preview_result.overlay_preview,
                contour,
            )
            if crop_result and crop_result.success and crop_result.image is not None:
                self.preview_widget.set_processed_image(crop_result.image)
                self._last_processed = crop_result.image.copy()
            else:
                self.preview_widget.set_processed_image(None)
                self._last_processed = None

            self._last_original = preview_result.original_preview
            self._current_image_path = path

            if self._image_list:
                try:
                    state["index"] = self._image_list.index(path)
                    self._current_image_index = state["index"]
                except ValueError:
                    pass

            _update_editor_title(path)
            return True

        def _navigate_editor(delta: int):
            if not self._image_list:
                self._update_image_list()
            if not self._image_list:
                return

            idx = state["index"]
            if idx < 0:
                if self._current_image_path in self._image_list:
                    idx = self._image_list.index(self._current_image_path)
                else:
                    idx = 0
            idx = (idx + delta) % len(self._image_list)
            state["index"] = idx
            target_path = self._image_list[idx]
            _load_editor_image(target_path)

        prev_btn.clicked.connect(lambda: _navigate_editor(-1))
        next_btn.clicked.connect(lambda: _navigate_editor(1))
        prev_btn.setEnabled(len(self._image_list) > 1)
        next_btn.setEnabled(len(self._image_list) > 1)

        shortcut_prev = QShortcut(QKeySequence("Left"), dialog)
        shortcut_next = QShortcut(QKeySequence("Right"), dialog)
        shortcut_prev.activated.connect(lambda: _navigate_editor(-1))
        shortcut_next.activated.connect(lambda: _navigate_editor(1))
        dialog._shortcut_prev = shortcut_prev
        dialog._shortcut_next = shortcut_next

        loaded = False
        if source_path:
            loaded = _load_editor_image(source_path)
        if not loaded and self._last_original is not None:
            crop_editor.set_image(self._last_original)
            _set_detected_contour(self._last_detected_contour)
            _update_editor_title(self._current_image_path)

        dialog.exec()

    def _on_crop_applied(self, cropped_image, dialog: Optional[QDialog] = None):
        """Handle crop applied from editor."""
        self.preview_widget.set_processed_image(cropped_image)
        self._last_processed = cropped_image.copy()
        self.status_label.setText("수동 크롭이 적용되었습니다")
        if dialog is not None:
            dialog.close()
        ToastManager.success("✂️ 수동 크롭 적용됨")

    def _detect_duplicates(self):
        """Detect duplicate files in input folder."""
        input_path = self.input_path_edit.text()
        if not input_path or not os.path.isdir(input_path):
            QMessageBox.warning(self, "경고", "유효한 입력 폴더를 선택하세요.")
            return

        self.status_label.setText("중복 파일 검색 중...")

        from ..utils.file_helpers import detect_duplicates

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

        from ..core.smart_enhancer import get_smart_enhancer, EnhancementPreset

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
        from .widgets.multi_compare_window import MultiCompareWindow

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
        from ..core.batch_profile_manager import get_batch_profile_manager
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

        # Validate paths
        if not input_path or not os.path.isdir(input_path):
            self.watch_mode_action.setChecked(False)
            QMessageBox.warning(self, "경고", "유효한 입력 폴더를 선택하세요.")
            return

        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            self.output_path_edit.setText(output_path)

        # Create output folder if needed
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)

        # Create auto processor
        self.watch_batch_processor = BatchProcessor(self._settings)
        self.watch_batch_processor.set_callbacks(on_log=self._emit_batch_log)

        self.auto_processor = AutoProcessor(
            watch_path=input_path,
            output_path=output_path,
            recursive=bool(watch_settings and watch_settings.recursive),
            debounce_ms=int(watch_settings.debounce_ms if watch_settings else 500),
            max_wait_seconds=float(
                getattr(watch_settings, "max_wait_seconds", 30.0)
                if watch_settings is not None
                else 30.0
            ),
            process_callback=self._process_watched_file,
            parent=self,
        )

        # Connect signals
        self.auto_processor.processing_started.connect(
            lambda f: self.status_label.setText(
                f"👁️ 감시 중... 처리 시작: {os.path.basename(f)}"
            )
        )
        self.auto_processor.processing_completed.connect(self._on_watched_file_complete)
        self.auto_processor.processing_completed_detailed.connect(
            self._on_watched_file_complete_detailed
        )
        self.auto_processor.queue_metrics_updated.connect(
            self._on_watch_queue_metrics
        )

        # Start watching
        if self.auto_processor.start():
            self.watch_mode_action.setText("👁️ 폴더 감시 중지")
            ToastManager.success(f"👁️ 폴더 감시 모드 시작: {input_path}")
            self.status_label.setText(f"👁️ 폴더 감시 중: {input_path}")
        else:
            self.watch_mode_action.setChecked(False)
            ToastManager.error("폴더 감시 시작 실패")

    def _stop_watch_mode(self):
        """Stop watching folder."""
        if self.auto_processor:
            self.auto_processor.stop()
            self.auto_processor = None

        self.watch_batch_processor = None

        self.watch_mode_action.setText("👁️ 폴더 감시 모드")
        ToastManager.info("폴더 감시 모드 중지됨")
        self.status_label.setText("폴더 감시 중지됨")

    def _process_watched_file(self, input_path: str, output_path: str):
        """Process a single file from watch mode."""
        if self.watch_batch_processor is None:
            self.watch_batch_processor = BatchProcessor(self._settings)
            self.watch_batch_processor.set_callbacks(on_log=self._emit_batch_log)

        try:
            self.watch_batch_processor.update_settings(self._settings)
            result = self.watch_batch_processor.process_single(input_path, output_path)
            raw_status = ""
            if hasattr(result, "status") and result.status is not None:
                raw_status = (
                    str(getattr(result.status, "value", "") or "").strip()
                    or str(getattr(result.status, "name", "") or "").strip().lower()
                )
            status = (raw_status or "failed").lower()
            success = status in {"success", "skipped"}
            return {
                "success": success,
                "status": status,
                "message": str(getattr(result, "message", "") or ""),
            }
        except Exception as e:
            logger.error(f"Watch mode processing error: {e}")
            return {
                "success": False,
                "status": "process_exception",
                "message": str(e),
            }

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
        if self.auto_processor is None:
            return
        self.status_label.setText(
            f"👁️ 감시 중... 대기열: {int(queue_size)}개, 평균 대기: {int(avg_wait_ms)}ms"
        )

    def closeEvent(self, event):
        """Handle window close event."""
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
        if self.batch_processor:
            self.batch_processor.cleanup()

        # Clear history to free memory
        if self.history_manager:
            self.history_manager.clear()

        # v9.0: Stop watch mode if active
        if self.auto_processor:
            self.auto_processor.stop()
            self.auto_processor = None

        self._teardown_preview_worker()

        event.accept()
