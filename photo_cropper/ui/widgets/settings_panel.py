#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings Panel Widget for Photo Cropper v8.0.

Provides tabbed settings interface for all application settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QPushButton, QFormLayout, QFrame, QLineEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent

from ...core.settings import (
    AppSettings, AlgorithmSettings, ProcessingSettings, 
    OutputSettings, FilterSettings, UISettings,
    AdvancedProcessingSettings, FileManagementSettings, PerformanceSettings
)
from .toggle_switch import ModernToggleSwitch


# Custom widgets that ignore wheel events to prevent accidental value changes
class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel events."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollSlider(QSlider):
    """QSlider that ignores mouse wheel events."""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class SettingsPanel(QWidget):
    """
    Tabbed settings panel for all application settings.
    
    Signals:
        settings_changed: Emitted when any setting changes
        preview_requested: Emitted when preview is requested
    """
    
    settings_changed = pyqtSignal(AppSettings)
    preview_requested = pyqtSignal()
    
    def __init__(self, settings: AppSettings = None, parent=None):
        super().__init__(parent)
        self._settings = settings or AppSettings()
        self._block_signals = False
        self._setup_ui()
        self._load_settings(self._settings)
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_basic_tab()
        self._create_algorithm_tab()
        self._create_output_tab()
        self._create_filter_tab()
        self._create_advanced_tab()  # v8.0
        self._create_file_management_tab()  # v8.0
        self._create_performance_tab()  # v8.0
    
    def _make_scrollable_tab(self, content_widget: QWidget) -> QWidget:
        """Wrap widget in a scroll area for tab content."""
        scroll = QScrollArea()
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Style the scroll area to be transparent
        scroll.setStyleSheet("background: transparent;")
        
        return scroll

    def _create_basic_tab(self):
        """Create basic settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # Post-processing group
        post_group = QGroupBox("✨ 후처리 옵션")
        post_layout = QVBoxLayout(post_group)
        
        self.auto_contrast_check = QCheckBox("자동 대비 향상 (CLAHE)")
        self.auto_contrast_check.setToolTip("CLAHE 알고리즘으로 이미지 대비를 자동 향상합니다")
        self.auto_contrast_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.auto_contrast_check)
        
        self.grayscale_check = QCheckBox("흑백으로 변환")
        self.grayscale_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.grayscale_check)
        
        self.sharpening_check = QCheckBox("선명도 향상")
        self.sharpening_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.sharpening_check)
        
        # Sharpening strength
        sharpening_row = QHBoxLayout()
        sharpening_row.addSpacing(24)
        sharpening_row.addWidget(QLabel("강도:"))
        self.sharpening_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.sharpening_slider.setRange(1, 30)
        self.sharpening_slider.setValue(10)
        self.sharpening_slider.valueChanged.connect(self._on_setting_changed)
        sharpening_row.addWidget(self.sharpening_slider)
        self.sharpening_value = QLabel("1.0")
        self.sharpening_value.setMinimumWidth(40)
        sharpening_row.addWidget(self.sharpening_value)
        post_layout.addLayout(sharpening_row)
        
        self.denoise_check = QCheckBox("노이즈 제거")
        self.denoise_check.setToolTip("이미지 노이즈를 줄입니다 (처리 시간 증가)")
        self.denoise_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.denoise_check)
        
        layout.addWidget(post_group)
        
        # UI settings group
        ui_group = QGroupBox("🎨 인터페이스")
        ui_layout = QFormLayout(ui_group)
        
        self.theme_combo = NoScrollComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.currentTextChanged.connect(self._on_setting_changed)
        ui_layout.addRow("테마:", self.theme_combo)
        
        self.auto_preview_check = ModernToggleSwitch("설정 변경 시 자동 미리보기")
        self.auto_preview_check.setChecked(True)
        self.auto_preview_check.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.auto_preview_check)
        
        self.contour_overlay_check = ModernToggleSwitch("검출 영역 오버레이 표시")
        self.contour_overlay_check.setChecked(True)
        self.contour_overlay_check.toggled.connect(self._on_setting_changed)
        ui_layout.addRow(self.contour_overlay_check)
        
        layout.addWidget(ui_group)
        layout.addStretch()
        
        # Add scrollable tab
        self.tab_widget.addTab(self._make_scrollable_tab(content), "기본 설정")
    
    def _create_algorithm_tab(self):
        """Create algorithm settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # Canny edge detection
        canny_group = QGroupBox("🔍 Canny 엣지 검출")
        canny_layout = QVBoxLayout(canny_group)
        
        # Min threshold
        min_row = QHBoxLayout()
        min_row.addWidget(QLabel("최소 임계값:"))
        self.canny_min_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.canny_min_slider.setRange(0, 255)
        self.canny_min_slider.setValue(50)
        self.canny_min_slider.valueChanged.connect(self._on_canny_changed)
        min_row.addWidget(self.canny_min_slider)
        self.canny_min_label = QLabel("50")
        self.canny_min_label.setMinimumWidth(40)
        min_row.addWidget(self.canny_min_label)
        canny_layout.addLayout(min_row)
        
        # Max threshold
        max_row = QHBoxLayout()
        max_row.addWidget(QLabel("최대 임계값:"))
        self.canny_max_slider = NoScrollSlider(Qt.Orientation.Horizontal)
        self.canny_max_slider.setRange(0, 255)
        self.canny_max_slider.setValue(150)
        self.canny_max_slider.valueChanged.connect(self._on_canny_changed)
        max_row.addWidget(self.canny_max_slider)
        self.canny_max_label = QLabel("150")
        self.canny_max_label.setMinimumWidth(40)
        max_row.addWidget(self.canny_max_label)
        canny_layout.addLayout(max_row)
        
        self.multi_scale_check = QCheckBox("다중 스케일 엣지 검출")
        self.multi_scale_check.setToolTip("여러 스케일에서 엣지를 검출하여 정확도 향상")
        self.multi_scale_check.setChecked(True)
        self.multi_scale_check.stateChanged.connect(self._on_setting_changed)
        canny_layout.addWidget(self.multi_scale_check)
        
        layout.addWidget(canny_group)
        
        # CLAHE settings
        clahe_group = QGroupBox("🎛️ CLAHE 대비 향상")
        clahe_layout = QFormLayout(clahe_group)
        
        self.use_clahe_check = QCheckBox()
        self.use_clahe_check.setChecked(True)
        self.use_clahe_check.stateChanged.connect(self._on_setting_changed)
        clahe_layout.addRow("CLAHE 사용:", self.use_clahe_check)
        
        self.clahe_clip_spin = NoScrollDoubleSpinBox()
        self.clahe_clip_spin.setRange(0.1, 10.0)
        self.clahe_clip_spin.setSingleStep(0.1)
        self.clahe_clip_spin.setValue(2.0)
        self.clahe_clip_spin.valueChanged.connect(self._on_setting_changed)
        clahe_layout.addRow("클립 제한:", self.clahe_clip_spin)
        
        self.clahe_grid_spin = NoScrollSpinBox()
        self.clahe_grid_spin.setRange(2, 32)
        self.clahe_grid_spin.setValue(8)
        self.clahe_grid_spin.valueChanged.connect(self._on_setting_changed)
        clahe_layout.addRow("그리드 크기:", self.clahe_grid_spin)
        
        layout.addWidget(clahe_group)
        
        # Contour settings
        contour_group = QGroupBox("➰ 윤곽선 처리")
        contour_layout = QFormLayout(contour_group)
        
        self.scoring_combo = NoScrollComboBox()
        self.scoring_combo.addItems(["basic", "enhanced", "strict"])
        self.scoring_combo.setCurrentText("enhanced")
        self.scoring_combo.currentTextChanged.connect(self._on_setting_changed)
        contour_layout.addRow("컨투어 스코어링:", self.scoring_combo)
        
        self.corner_detection_check = QCheckBox("Harris 코너 검출 사용 (4단계)")
        self.corner_detection_check.setToolTip("다른 방법 실패 시 코너 검출로 시도")
        self.corner_detection_check.stateChanged.connect(self._on_setting_changed)
        contour_layout.addRow(self.corner_detection_check)
        
        layout.addWidget(contour_group)
        
        # Hint
        hint_label = QLabel("""💡 조정 가이드:
• 흰색/밝은 배경: 기본값 (50-150) 권장
• 어두운 배경: 최소값 ↓ (30-120)
• 복잡한 무늬: 최대값 ↑ (70-200)""")
        hint_label.setObjectName("subtitleLabel")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        layout.addStretch()
        self.tab_widget.addTab(self._make_scrollable_tab(content), "알고리즘")
    
    def _create_output_tab(self):
        """Create output settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Format group
        format_group = QGroupBox("💾 출력 형식")
        format_layout = QFormLayout(format_group)
        
        self.format_combo = NoScrollComboBox()
        self.format_combo.addItems(["JPG", "PNG", "WEBP"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addRow("파일 형식:", self.format_combo)
        
        # Quality (JPG/WEBP)
        self.quality_spin = NoScrollSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.valueChanged.connect(self._on_setting_changed)
        format_layout.addRow("JPG/WEBP 품질:", self.quality_spin)
        
        # PNG compression
        self.png_compression_spin = NoScrollSpinBox()
        self.png_compression_spin.setRange(0, 9)
        self.png_compression_spin.setValue(6)
        self.png_compression_spin.setEnabled(False)
        self.png_compression_spin.valueChanged.connect(self._on_setting_changed)
        format_layout.addRow("PNG 압축 레벨:", self.png_compression_spin)
        
        layout.addWidget(format_group)
        
        # Naming group
        naming_group = QGroupBox("📝 파일명 옵션")
        naming_layout = QVBoxLayout(naming_group)
        
        self.timestamp_check = QCheckBox("파일명에 타임스탬프 추가")
        self.timestamp_check.stateChanged.connect(self._on_setting_changed)
        naming_layout.addWidget(self.timestamp_check)
        
        layout.addWidget(naming_group)
        
        # Backup group
        backup_group = QGroupBox("📦 백업")
        backup_layout = QVBoxLayout(backup_group)
        
        self.backup_check = QCheckBox("원본 파일 백업 생성")
        self.backup_check.setToolTip("처리 전 원본 파일을 backup 폴더에 복사")
        self.backup_check.stateChanged.connect(self._on_setting_changed)
        backup_layout.addWidget(self.backup_check)
        
        layout.addWidget(backup_group)
        layout.addStretch()
        
        self.tab_widget.addTab(self._make_scrollable_tab(content), "출력 설정")
    
    def _create_filter_tab(self):
        """Create filter settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Size filter group
        size_group = QGroupBox("📏 크기 필터")
        size_layout = QVBoxLayout(size_group)
        
        self.skip_small_check = QCheckBox("작은 이미지 건너뛰기")
        self.skip_small_check.setChecked(True)
        self.skip_small_check.stateChanged.connect(self._on_filter_changed)
        size_layout.addWidget(self.skip_small_check)
        
        min_size_row = QHBoxLayout()
        min_size_row.addSpacing(24)
        min_size_row.addWidget(QLabel("최소 크기 (px):"))
        self.min_size_spin = NoScrollSpinBox()
        self.min_size_spin.setRange(50, 1000)
        self.min_size_spin.setValue(100)
        self.min_size_spin.valueChanged.connect(self._on_setting_changed)
        min_size_row.addWidget(self.min_size_spin)
        size_layout.addLayout(min_size_row)
        
        layout.addWidget(size_group)
        
        # Processing filter group
        process_group = QGroupBox("🔄 처리 필터")
        process_layout = QVBoxLayout(process_group)
        
        self.skip_processed_check = QCheckBox("이미 처리된 파일 건너뛰기")
        self.skip_processed_check.setToolTip("파일명에 '_cropped'가 포함된 파일 제외")
        self.skip_processed_check.stateChanged.connect(self._on_setting_changed)
        process_layout.addWidget(self.skip_processed_check)
        
        layout.addWidget(process_group)
        layout.addStretch()
        
        self.tab_widget.addTab(self._make_scrollable_tab(content), "필터")
    
    def _on_setting_changed(self):
        """Handle any setting change."""
        if self._block_signals:
            return
        
        # Update sharpening value label
        sharpening_val = self.sharpening_slider.value() / 10.0
        self.sharpening_value.setText(f"{sharpening_val:.1f}")
        
        self._emit_settings()
    
    def _on_canny_changed(self):
        """Handle Canny slider changes."""
        if self._block_signals:
            return
        
        self.canny_min_label.setText(str(self.canny_min_slider.value()))
        self.canny_max_label.setText(str(self.canny_max_slider.value()))
        self._emit_settings()
    
    def _on_format_changed(self, format_name: str):
        """Handle output format change."""
        is_png = format_name.upper() == "PNG"
        self.quality_spin.setEnabled(not is_png)
        self.png_compression_spin.setEnabled(is_png)
        self._on_setting_changed()
    
    def _on_filter_changed(self):
        """Handle filter checkbox change."""
        self.min_size_spin.setEnabled(self.skip_small_check.isChecked())
        self._on_setting_changed()
    
    def _emit_settings(self):
        """Build and emit current settings."""
        settings = self._build_settings()
        self._settings = settings
        self.settings_changed.emit(settings)
        
        # Auto preview if enabled
        if self.auto_preview_check.isChecked():
            self.preview_requested.emit()
    
    def _build_settings(self) -> AppSettings:
        """Build AppSettings from current UI state."""
        algorithm = AlgorithmSettings(
            canny_min=self.canny_min_slider.value(),
            canny_max=self.canny_max_slider.value(),
            use_clahe=self.use_clahe_check.isChecked(),
            clahe_clip_limit=self.clahe_clip_spin.value(),
            clahe_grid_size=self.clahe_grid_spin.value(),
            multi_scale_edge=self.multi_scale_check.isChecked(),
            use_corner_detection=self.corner_detection_check.isChecked(),
            contour_scoring=self.scoring_combo.currentText(),
        )
        
        processing = ProcessingSettings(
            auto_contrast=self.auto_contrast_check.isChecked(),
            to_grayscale=self.grayscale_check.isChecked(),
            apply_sharpening=self.sharpening_check.isChecked(),
            sharpening_strength=self.sharpening_slider.value() / 10.0,
            denoise=self.denoise_check.isChecked(),
        )
        
        output = OutputSettings(
            output_format=self.format_combo.currentText(),
            jpg_quality=self.quality_spin.value(),
            png_compression=self.png_compression_spin.value(),
            webp_quality=self.quality_spin.value(),  # Use same quality value as JPG
            add_timestamp=self.timestamp_check.isChecked(),
        )
        
        filter_settings = FilterSettings(
            skip_small_images=self.skip_small_check.isChecked(),
            min_image_size=self.min_size_spin.value(),
            skip_processed=self.skip_processed_check.isChecked(),
        )
        
        ui = UISettings(
            theme=self.theme_combo.currentText(),
            auto_preview=self.auto_preview_check.isChecked(),
            show_contour_overlay=self.contour_overlay_check.isChecked(),
        )
        
        return AppSettings(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            create_backup=self.backup_check.isChecked(),
        )
    
    def _load_settings(self, settings: AppSettings):
        """Load settings into UI."""
        self._block_signals = True
        
        # Algorithm
        self.canny_min_slider.setValue(settings.algorithm.canny_min)
        self.canny_max_slider.setValue(settings.algorithm.canny_max)
        self.canny_min_label.setText(str(settings.algorithm.canny_min))
        self.canny_max_label.setText(str(settings.algorithm.canny_max))
        self.use_clahe_check.setChecked(settings.algorithm.use_clahe)
        self.clahe_clip_spin.setValue(settings.algorithm.clahe_clip_limit)
        self.clahe_grid_spin.setValue(settings.algorithm.clahe_grid_size)
        self.multi_scale_check.setChecked(settings.algorithm.multi_scale_edge)
        self.corner_detection_check.setChecked(settings.algorithm.use_corner_detection)
        index = self.scoring_combo.findText(settings.algorithm.contour_scoring)
        if index >= 0:
            self.scoring_combo.setCurrentIndex(index)
        
        # Processing
        self.auto_contrast_check.setChecked(settings.processing.auto_contrast)
        self.grayscale_check.setChecked(settings.processing.to_grayscale)
        self.sharpening_check.setChecked(settings.processing.apply_sharpening)
        self.sharpening_slider.setValue(int(settings.processing.sharpening_strength * 10))
        self.sharpening_value.setText(f"{settings.processing.sharpening_strength:.1f}")
        self.denoise_check.setChecked(settings.processing.denoise)
        
        # Output
        index = self.format_combo.findText(settings.output.output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.quality_spin.setValue(settings.output.jpg_quality)
        self.png_compression_spin.setValue(settings.output.png_compression)
        self.timestamp_check.setChecked(settings.output.add_timestamp)
        
        # Filter
        self.skip_small_check.setChecked(settings.filter.skip_small_images)
        self.min_size_spin.setValue(settings.filter.min_image_size)
        self.min_size_spin.setEnabled(settings.filter.skip_small_images)
        self.skip_processed_check.setChecked(settings.filter.skip_processed)
        
        # UI
        index = self.theme_combo.findText(settings.ui.theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.auto_preview_check.setChecked(settings.ui.auto_preview)
        self.contour_overlay_check.setChecked(settings.ui.show_contour_overlay)
        
        # Misc
        self.backup_check.setChecked(settings.create_backup)
        
        # Format-dependent enables
        is_png = settings.output.output_format.upper() == "PNG"
        self.quality_spin.setEnabled(not is_png)
        self.png_compression_spin.setEnabled(is_png)
        
        self._block_signals = False
    
    # ========================================
    # v8.0 New Tabs
    # ========================================
    
    def _create_advanced_tab(self):
        """Create advanced processing tab (v8.0)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Auto corrections group
        auto_group = QGroupBox("🔧 자동 보정")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_deskew_check = ModernToggleSwitch("자동 기울기 보정")
        self.auto_deskew_check.setToolTip("Hough 변환으로 기울기를 감지하고 자동 교정")
        self.auto_deskew_check.toggled.connect(self._on_setting_changed)
        auto_layout.addWidget(self.auto_deskew_check)
        
        self.auto_color_check = ModernToggleSwitch("자동 색상 보정")
        self.auto_color_check.setToolTip("Gray World 알고리즘으로 화이트밸런스 보정")
        self.auto_color_check.toggled.connect(self._on_setting_changed)
        auto_layout.addWidget(self.auto_color_check)
        
        # Color correction method
        color_row = QHBoxLayout()
        color_row.addSpacing(24)
        color_row.addWidget(QLabel("보정 방식:"))
        self.color_method_combo = NoScrollComboBox()
        self.color_method_combo.addItems(["gray_world", "white_patch", "histogram"])
        self.color_method_combo.currentTextChanged.connect(self._on_setting_changed)
        color_row.addWidget(self.color_method_combo)
        auto_layout.addLayout(color_row)
        
        self.perspective_check = QCheckBox("자동 원근 교정")
        self.perspective_check.setToolTip("감지된 사각형을 기준으로 원근 왜곡 교정")
        self.perspective_check.stateChanged.connect(self._on_setting_changed)
        auto_layout.addWidget(self.perspective_check)
        
        layout.addWidget(auto_group)
        
        # Enhanced processing group
        enhanced_group = QGroupBox("✨ 강화 처리")
        enhanced_layout = QVBoxLayout(enhanced_group)
        
        self.enhanced_denoise_check = QCheckBox("강화된 노이즈 제거")
        self.enhanced_denoise_check.setToolTip("고급 비지역 평균 필터 적용")
        self.enhanced_denoise_check.stateChanged.connect(self._on_setting_changed)
        enhanced_layout.addWidget(self.enhanced_denoise_check)
        
        # Denoise strength
        denoise_row = QHBoxLayout()
        denoise_row.addSpacing(24)
        denoise_row.addWidget(QLabel("강도:"))
        self.enhanced_denoise_spin = NoScrollSpinBox()
        self.enhanced_denoise_spin.setRange(1, 30)
        self.enhanced_denoise_spin.setValue(10)
        self.enhanced_denoise_spin.valueChanged.connect(self._on_setting_changed)
        denoise_row.addWidget(self.enhanced_denoise_spin)
        enhanced_layout.addLayout(denoise_row)
        
        self.restore_old_check = QCheckBox("오래된 사진 복원")
        self.restore_old_check.setToolTip("색바램, 얼룩 보정 및 대비 향상")
        self.restore_old_check.stateChanged.connect(self._on_setting_changed)
        enhanced_layout.addWidget(self.restore_old_check)
        
        self.enhanced_sharpen_check = QCheckBox("강화된 선명도")
        self.enhanced_sharpen_check.stateChanged.connect(self._on_setting_changed)
        enhanced_layout.addWidget(self.enhanced_sharpen_check)
        
        self.auto_crop_border_check = QCheckBox("자동 테두리 제거")
        self.auto_crop_border_check.setToolTip("스캔 테두리 자동 감지 및 제거")
        self.auto_crop_border_check.stateChanged.connect(self._on_setting_changed)
        enhanced_layout.addWidget(self.auto_crop_border_check)
        
        layout.addWidget(enhanced_group)
        layout.addStretch()
        
        scroll.setWidget(tab)
        self.tab_widget.addTab(scroll, "고급 처리")
    
    def _create_file_management_tab(self):
        """Create file management tab (v8.0)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Recursive processing group
        recursive_group = QGroupBox("📁 폴더 처리")
        recursive_layout = QVBoxLayout(recursive_group)
        
        self.recursive_check = QCheckBox("하위 폴더 포함 (재귀 처리)")
        self.recursive_check.setToolTip("선택한 폴더와 모든 하위 폴더의 이미지를 처리")
        self.recursive_check.stateChanged.connect(self._on_setting_changed)
        recursive_layout.addWidget(self.recursive_check)
        
        layout.addWidget(recursive_group)
        
        # Naming rules group
        naming_group = QGroupBox("📝 파일명 규칙")
        naming_layout = QFormLayout(naming_group)
        
        self.use_naming_rules_check = QCheckBox()
        self.use_naming_rules_check.stateChanged.connect(self._on_setting_changed)
        naming_layout.addRow("규칙 사용:", self.use_naming_rules_check)
        
        self.naming_prefix_edit = QLineEdit()
        self.naming_prefix_edit.setPlaceholderText("예: scan_")
        """Create advanced processing settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # GPU Acceleration
        gpu_group = QGroupBox("🚀 하드웨어 가속")
        gpu_layout = QVBoxLayout(gpu_group)
        
        self.use_gpu_check = ModernToggleSwitch("GPU 가속 사용 (CUDA/OpenCL)")
        self.use_gpu_check.setChecked(False)  # Default off for stability
        self.use_gpu_check.setToolTip("가능한 경우 GPU를 사용하여 처리 속도를 높입니다.")
        self.use_gpu_check.toggled.connect(self._on_setting_changed)
        gpu_layout.addWidget(self.use_gpu_check)
        
        layout.addWidget(gpu_group)
        
        # Geometric correction
        geo_group = QGroupBox("📐 기하학 보정")
        geo_layout = QFormLayout(geo_group)
        
        self.auto_deskew_check = ModernToggleSwitch("자동 기울기 보정 (Deskew)")
        self.auto_deskew_check.setChecked(True)
        self.auto_deskew_check.toggled.connect(self._on_setting_changed)
        geo_layout.addRow(self.auto_deskew_check)
        
        self.perspective_check = ModernToggleSwitch("원근 왜곡 보정")
        self.perspective_check.setChecked(False)
        self.perspective_check.toggled.connect(self._on_setting_changed)
        geo_layout.addRow(self.perspective_check)
        
        layout.addWidget(geo_group)
        
        # Color & Restore
        restore_group = QGroupBox("✨ 복원 및 색상")
        restore_layout = QFormLayout(restore_group)
        
        self.auto_color_check = QCheckBox("자동 색상 보정")
        self.auto_color_check.stateChanged.connect(self._on_setting_changed)
        restore_layout.addRow(self.auto_color_check)
        
        self.restore_check = QCheckBox("오래된 사진 복원 (Inpainting)")
        self.restore_check.setToolTip("긁힘이나 먼지를 제거합니다. 속도가 느릴 수 있습니다.")
        self.restore_check.stateChanged.connect(self._on_setting_changed)
        restore_layout.addRow(self.restore_check)
        
        layout.addWidget(restore_group)
        layout.addStretch()
        
        self.tab_widget.addTab(self._make_scrollable_tab(content), "고급 처리")

    def _create_file_management_tab(self):
        """Create file management settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Conflict resolution
        conflict_group = QGroupBox("⚠️ 파일명 충돌 해결")
        conflict_layout = QVBoxLayout(conflict_group)
        
        self.conflict_combo = NoScrollComboBox()
        self.conflict_combo.addItems(["rename", "overwrite", "skip"])
        self.conflict_combo.setItemText(0, "자동 이름 변경 (숫자 추가)")
        self.conflict_combo.setItemText(1, "덮어쓰기")
        self.conflict_combo.setItemText(2, "건너뛰기")
        self.conflict_combo.currentTextChanged.connect(self._on_setting_changed)
        conflict_layout.addWidget(self.conflict_combo)
        
        layout.addWidget(conflict_group)
        
        # Sorting
        sort_group = QGroupBox("📂 파일 정렬")
        sort_layout = QFormLayout(sort_group)
        
        self.sort_by_combo = NoScrollComboBox()
        self.sort_by_combo.addItems(["name", "date", "size"])
        self.sort_by_combo.setItemText(0, "이름순")
        self.sort_by_combo.setItemText(1, "날짜순")
        self.sort_by_combo.setItemText(2, "크기순")
        self.sort_by_combo.currentTextChanged.connect(self._on_setting_changed)
        sort_layout.addRow("정렬 기준:", self.sort_by_combo)
        
        self.sort_reverse_check = QCheckBox("역순 정렬")
        self.sort_reverse_check.stateChanged.connect(self._on_setting_changed)
        sort_layout.addRow("", self.sort_reverse_check)
        
        layout.addWidget(sort_group)
        
        # Duplicate detection
        dup_group = QGroupBox("👯 중복 파일")
        dup_layout = QVBoxLayout(dup_group)
        self.detect_dups_check = ModernToggleSwitch("처리 전 중복 파일 검사")
        self.detect_dups_check.setChecked(False)
        self.detect_dups_check.toggled.connect(self._on_setting_changed)
        dup_layout.addWidget(self.detect_dups_check)
        
        layout.addWidget(dup_group)
        layout.addStretch()
        
        self.tab_widget.addTab(self._make_scrollable_tab(content), "파일 관리")

    def _create_performance_tab(self):
        """Create performance settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Multithreading
        thread_group = QGroupBox("⚡ 병렬 처리")
        thread_layout = QFormLayout(thread_group)
        
        self.max_threads_spin = NoScrollSpinBox()
        self.max_threads_spin.setRange(1, 32)
        self.max_threads_spin.setValue(4)
        self.max_threads_spin.setToolTip("동시에 처리할 이미지 수 (CPU 코어 수 권장)")
        self.max_threads_spin.valueChanged.connect(self._on_setting_changed)
        thread_layout.addRow("최대 스레드 수:", self.max_threads_spin)
        
        layout.addWidget(thread_group)
        
        # Memory
        mem_group = QGroupBox("💾 메모리 관리")
        mem_layout = QVBoxLayout(mem_group)
        
        self.low_mem_check = QCheckBox("저사양 모드 (메모리 절약)")
        self.low_mem_check.setToolTip("처리 속도가 느려질 수 있지만 메모리 사용량을 줄입니다.")
        self.low_mem_check.stateChanged.connect(self._on_setting_changed)
        mem_layout.addWidget(self.low_mem_check)
        
        layout.addWidget(mem_group)
        layout.addStretch()
        
        self.tab_widget.addTab(self._make_scrollable_tab(content), "성능")
    
    # ========================================
    # Updated _build_settings for v8.0
    # ========================================
    
    def _build_settings_v8(self) -> AppSettings:
        """Build v8.0 settings from UI."""
        # Build base settings first
        settings = self._build_settings()
        
        # Add v8.0 advanced settings
        settings.advanced = AdvancedProcessingSettings(
            auto_deskew=self.auto_deskew_check.isChecked(),
            auto_color_correct=self.auto_color_check.isChecked(),
            color_correct_method=self.color_method_combo.currentText(),
            perspective_correct=self.perspective_check.isChecked(),
            enhanced_denoise=self.enhanced_denoise_check.isChecked(),
            enhanced_denoise_strength=self.enhanced_denoise_spin.value(),
            restore_old_photo=self.restore_old_check.isChecked(),
            enhanced_sharpen=self.enhanced_sharpen_check.isChecked(),
            auto_crop_borders=self.auto_crop_border_check.isChecked(),
        )
        
        # Add file management settings
        settings.file_management = FileManagementSettings(
            recursive_search=self.recursive_check.isChecked(),
            use_naming_rules=self.use_naming_rules_check.isChecked(),
            naming_prefix=self.naming_prefix_edit.text(),
            naming_suffix=self.naming_suffix_edit.text(),
            naming_use_counter=self.naming_counter_check.isChecked(),
            naming_use_date=self.naming_date_check.isChecked(),
            move_failed_files=self.move_failed_check.isChecked(),
            copy_failed_instead_of_move=self.copy_failed_check.isChecked(),
            enable_logging=self.enable_log_check.isChecked(),
            log_format=self.log_format_combo.currentText(),
        )
        
        # Add performance settings
        settings.performance = PerformanceSettings(
            use_gpu=self.use_gpu_check.isChecked(),
            enable_multithreading=self.multithreading_check.isChecked(),
            thread_count=self.thread_count_spin.value(),
            max_image_size_mb=self.max_size_spin.value(),
            downscale_large_images=self.downscale_check.isChecked(),
        )
        
        return settings
    
    def _load_settings_v8(self, settings: AppSettings):
        """Load v8.0 settings into UI."""
        # Advanced settings
        if hasattr(settings, 'advanced'):
            adv = settings.advanced
            self.auto_deskew_check.setChecked(adv.auto_deskew)
            self.auto_color_check.setChecked(adv.auto_color_correct)
            idx = self.color_method_combo.findText(adv.color_correct_method)
            if idx >= 0:
                self.color_method_combo.setCurrentIndex(idx)
            self.perspective_check.setChecked(adv.perspective_correct)
            self.enhanced_denoise_check.setChecked(adv.enhanced_denoise)
            self.enhanced_denoise_spin.setValue(adv.enhanced_denoise_strength)
            self.restore_old_check.setChecked(adv.restore_old_photo)
            self.enhanced_sharpen_check.setChecked(adv.enhanced_sharpen)
            self.auto_crop_border_check.setChecked(adv.auto_crop_borders)
        
        # File management settings
        if hasattr(settings, 'file_management'):
            fm = settings.file_management
            self.recursive_check.setChecked(fm.recursive_search)
            self.use_naming_rules_check.setChecked(fm.use_naming_rules)
            self.naming_prefix_edit.setText(fm.naming_prefix)
            self.naming_suffix_edit.setText(fm.naming_suffix)
            self.naming_counter_check.setChecked(fm.naming_use_counter)
            self.naming_date_check.setChecked(fm.naming_use_date)
            self.move_failed_check.setChecked(fm.move_failed_files)
            self.copy_failed_check.setChecked(fm.copy_failed_instead_of_move)
            self.enable_log_check.setChecked(fm.enable_logging)
            idx = self.log_format_combo.findText(fm.log_format)
            if idx >= 0:
                self.log_format_combo.setCurrentIndex(idx)
        
        # Performance settings
        if hasattr(settings, 'performance'):
            perf = settings.performance
            self.use_gpu_check.setChecked(perf.use_gpu)
            self.multithreading_check.setChecked(perf.enable_multithreading)
            self.thread_count_spin.setValue(perf.thread_count)
            self.max_size_spin.setValue(perf.max_image_size_mb)
            self.downscale_check.setChecked(perf.downscale_large_images)
    
    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings
    
    @settings.setter
    def settings(self, value: AppSettings):
        """Set and load settings."""
        self._settings = value
        self._load_settings(value)
        self._load_settings_v8(value)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._load_settings(AppSettings())
        self._load_settings_v8(AppSettings())
        self._emit_settings()
