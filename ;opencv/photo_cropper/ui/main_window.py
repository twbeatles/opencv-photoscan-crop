#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Window for Photo Cropper PyQt6 Application.

Provides the main application window with all UI components.
"""

import os
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QMessageBox, QGroupBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence, QDragEnterEvent, QDropEvent

from .widgets.settings_panel import SettingsPanel
from .widgets.preview_widget import ImagePreviewWidget
from .widgets.progress_dialog import ProgressDialog
from .widgets.histogram_widget import HistogramWidget
from .styles.themes import get_theme, get_available_themes

from ..core.settings import AppSettings, SettingsManager
from ..core.image_processor import ImageProcessor
from ..core.batch_processor import BatchProcessor, BatchProgress, FileResult
from ..utils.file_helpers import get_image_files, open_file_explorer, validate_directory

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
    """
    
    VERSION = "7.0"
    TITLE = f"사진 자동 자르기 v{VERSION}"
    
    def __init__(self):
        super().__init__()
        
        # Initialize managers
        self.settings_manager = SettingsManager()
        self._settings = self.settings_manager.load()
        
        # Initialize processors
        self.image_processor = ImageProcessor(
            self._settings.algorithm,
            self._settings.processing
        )
        self.batch_processor: Optional[BatchProcessor] = None
        
        # State
        self._current_image_path: Optional[str] = None
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._do_preview)
        self.progress_dialog: Optional[ProgressDialog] = None
        
        # Setup UI
        self._setup_window()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        
        # Apply saved settings
        self._apply_settings(self._settings)
        
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
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
    
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
        """Create toolbar."""
        toolbar = QToolBar("메인 도구모음")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Open folder button
        open_btn = QPushButton("📂 폴더 열기")
        open_btn.clicked.connect(self._select_input_folder)
        toolbar.addWidget(open_btn)
        
        toolbar.addSeparator()
        
        # Preview button
        preview_btn = QPushButton("🔍 미리보기")
        preview_btn.clicked.connect(self._request_preview)
        toolbar.addWidget(preview_btn)
        
        # Process button
        self.process_btn = QPushButton("▶️ 변환 시작")
        self.process_btn.setObjectName("primaryButton")
        self.process_btn.clicked.connect(self._start_processing)
        toolbar.addWidget(self.process_btn)
        
        toolbar.addSeparator()
        
        # Output folder button
        output_btn = QPushButton("📁 출력폴더")
        output_btn.clicked.connect(self._open_output_folder)
        toolbar.addWidget(output_btn)
        
        # Spacer
        spacer = QWidget()
        from PyQt6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(spacer)
        
        # Theme toggle
        theme_btn = QPushButton("🌙 테마")
        theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(theme_btn)
    
    def _setup_central_widget(self):
        """Create central widget with splitters."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Folder selection row
        folder_frame = QFrame()
        folder_layout = QHBoxLayout(folder_frame)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        
        folder_layout.addWidget(QLabel("입력:"))
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("입력 폴더를 선택하세요...")
        self.input_path_edit.textChanged.connect(self._on_input_path_changed)
        folder_layout.addWidget(self.input_path_edit)
        
        input_browse_btn = QPushButton("...")
        input_browse_btn.setMaximumWidth(40)
        input_browse_btn.clicked.connect(self._select_input_folder)
        folder_layout.addWidget(input_browse_btn)
        
        folder_layout.addWidget(QLabel("출력:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("출력 폴더 (선택사항)")
        folder_layout.addWidget(self.output_path_edit)
        
        output_browse_btn = QPushButton("...")
        output_browse_btn.setMaximumWidth(40)
        output_browse_btn.clicked.connect(self._select_output_folder)
        folder_layout.addWidget(output_browse_btn)
        
        main_layout.addWidget(folder_frame)
        
        # Info label
        self.info_label = QLabel("💡 3단계 지능형 탐색으로 다양한 배경에서 높은 검출 성공률을 제공합니다")
        self.info_label.setObjectName("subtitleLabel")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.info_label)
        
        # Main splitter (horizontal: preview | settings)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Preview area
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_widget = ImagePreviewWidget()
        left_layout.addWidget(self.preview_widget)
        
        # Histogram
        self.histogram_widget = HistogramWidget()
        left_layout.addWidget(self.histogram_widget)
        
        main_splitter.addWidget(left_widget)
        
        # Right side: Settings panel
        self.settings_panel = SettingsPanel(self._settings)
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.settings_panel.preview_requested.connect(self._request_preview)
        self.settings_panel.setMaximumWidth(400)
        main_splitter.addWidget(self.settings_panel)
        
        # Set splitter sizes
        main_splitter.setSizes([800, 350])
        
        main_layout.addWidget(main_splitter)
    
    def _setup_statusbar(self):
        """Create status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_label = QLabel("준비")
        self.statusbar.addWidget(self.status_label)
        
        self.statusbar.addPermanentWidget(QLabel("|"))
        
        self.file_count_label = QLabel("파일: 0개")
        self.statusbar.addPermanentWidget(self.file_count_label)
    
    # ========================================
    # Settings and Theme
    # ========================================
    
    def _apply_settings(self, settings: AppSettings):
        """Apply settings to UI and processors."""
        self._settings = settings
        
        # Update processors
        self.image_processor.update_settings(
            settings.algorithm,
            settings.processing
        )
        
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
            settings.processing
        )
        
        # Check theme change
        if settings.ui.theme != self._get_current_theme():
            self._set_theme(settings.ui.theme)
    
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
            self, "설정 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
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
            self, "입력 폴더 선택",
            self.input_path_edit.text() or ""
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
            self, "출력 폴더 선택",
            self.output_path_edit.text() or ""
        )
        
        if path:
            self.output_path_edit.setText(path)
    
    def _on_input_path_changed(self, path: str):
        """Handle input path change."""
        if os.path.isdir(path):
            files = get_image_files(path)
            self.file_count_label.setText(f"파일: {len(files)}개")
        else:
            self.file_count_label.setText("파일: 0개")
    
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
                if ext in ImageProcessor.SUPPORTED_FORMATS:
                    self._current_image_path = path
                    self._do_preview()
    
    # ========================================
    # Preview
    # ========================================
    
    def _open_single_image(self):
        """Open single image for preview."""
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;모든 파일 (*.*)"
        )
        
        if path:
            self._current_image_path = path
            self._do_preview()
    
    def _request_preview(self):
        """Request preview with debounce."""
        self._preview_timer.start(200)  # 200ms debounce
    
    def _do_preview(self):
        """Perform preview processing."""
        if not self._current_image_path:
            # Try to get first image from input folder
            input_path = self.input_path_edit.text()
            if input_path and os.path.isdir(input_path):
                files = get_image_files(input_path)
                if files:
                    self._current_image_path = files[0]
        
        if not self._current_image_path or not os.path.exists(self._current_image_path):
            return
        
        self.status_label.setText(f"미리보기 처리 중: {os.path.basename(self._current_image_path)}")
        QApplication.processEvents()
        
        # Get preview with contour
        original, overlay, message = self.image_processor.get_preview_with_contour(
            self._current_image_path
        )
        
        if original is not None:
            self.preview_widget.set_original_image(original, overlay)
            self.histogram_widget.set_image(original)
        
        # Process image
        result = self.image_processor.process_image(self._current_image_path)
        
        if result.success and result.image is not None:
            self.preview_widget.set_processed_image(result.image)
            stage = result.detection_stage.value if result.detection_stage else "Unknown"
            self.status_label.setText(f"미리보기 성공 ({stage})")
        else:
            self.preview_widget.set_processed_image(None)
            self.status_label.setText(f"미리보기 실패: {result.message}")
    
    # ========================================
    # Batch Processing
    # ========================================
    
    def _start_processing(self):
        """Start batch processing."""
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
        files = get_image_files(input_path)
        if not files:
            QMessageBox.information(self, "알림", "처리할 이미지 파일이 없습니다.")
            return
        
        # Create batch processor
        self.batch_processor = BatchProcessor(self._settings)
        self.batch_processor.set_callbacks(
            on_progress=self._on_batch_progress,
            on_log=self._on_batch_log,
            on_complete=self._on_batch_complete
        )
        
        # Show progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.cancel_requested.connect(self._cancel_processing)
        self.progress_dialog.show()
        
        # Start processing
        file_names = [os.path.basename(f) for f in files]
        self.batch_processor.start_async(input_path, output_path, file_names)
    
    def _cancel_processing(self):
        """Cancel batch processing."""
        if self.batch_processor:
            self.batch_processor.request_stop()
    
    def _on_batch_progress(self, progress: BatchProgress):
        """Handle batch progress update."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.update_progress(progress)
    
    def _on_batch_log(self, message: str, level: str):
        """Handle batch log message."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.log_message(message, level)
    
    def _on_batch_complete(self, progress: BatchProgress, results: list):
        """Handle batch processing completion."""
        self.status_label.setText(
            f"완료: {progress.success}개 성공, {progress.failed}개 실패"
        )
    
    def _retry_failed_files(self):
        """Retry failed files from last batch."""
        if self.batch_processor and self.batch_processor.failed_files:
            failed = self.batch_processor.failed_files
            reply = QMessageBox.question(
                self, "재처리",
                f"{len(failed)}개의 실패한 파일을 재처리하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                input_path = self.input_path_edit.text()
                output_path = self.output_path_edit.text()
                
                self.batch_processor = BatchProcessor(self._settings)
                self.batch_processor.set_callbacks(
                    on_progress=self._on_batch_progress,
                    on_log=self._on_batch_log,
                    on_complete=self._on_batch_complete
                )
                
                self.progress_dialog = ProgressDialog(self)
                self.progress_dialog.cancel_requested.connect(self._cancel_processing)
                self.progress_dialog.show()
                
                self.batch_processor.start_async(input_path, output_path, failed)
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
    
    def closeEvent(self, event):
        """Handle window close."""
        # Save settings
        self._settings.last_input_path = self.input_path_edit.text()
        self._settings.last_output_path = self.output_path_edit.text()
        self.settings_manager.save(self._settings)
        
        event.accept()
