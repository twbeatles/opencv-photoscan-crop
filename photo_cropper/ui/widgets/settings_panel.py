#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings Panel Widget for Photo Cropper.

Provides tabbed settings interface for algorithm, processing, output, and filter settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QPushButton, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent

from ...core.settings import (
    AppSettings, AlgorithmSettings, ProcessingSettings, 
    OutputSettings, FilterSettings, UISettings
)


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
    
    def _create_basic_tab(self):
        """Create basic settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
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
        self.sharpening_slider = QSlider(Qt.Orientation.Horizontal)
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
        
        self.auto_preview_check = QCheckBox()
        self.auto_preview_check.setChecked(True)
        self.auto_preview_check.stateChanged.connect(self._on_setting_changed)
        ui_layout.addRow("설정 변경 시 자동 미리보기:", self.auto_preview_check)
        
        self.contour_overlay_check = QCheckBox()
        self.contour_overlay_check.setChecked(True)
        self.contour_overlay_check.stateChanged.connect(self._on_setting_changed)
        ui_layout.addRow("검출 영역 오버레이 표시:", self.contour_overlay_check)
        
        layout.addWidget(ui_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "기본 설정")
    
    def _create_algorithm_tab(self):
        """Create algorithm settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Canny edge detection
        canny_group = QGroupBox("🔍 Canny 엣지 검출")
        canny_layout = QVBoxLayout(canny_group)
        
        # Min threshold
        min_row = QHBoxLayout()
        min_row.addWidget(QLabel("최소 임계값:"))
        self.canny_min_slider = QSlider(Qt.Orientation.Horizontal)
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
        self.canny_max_slider = QSlider(Qt.Orientation.Horizontal)
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
        
        # Advanced options
        advanced_group = QGroupBox("⚙️ 고급 옵션")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.corner_detection_check = QCheckBox("Harris 코너 검출 사용 (4단계)")
        self.corner_detection_check.setToolTip("다른 방법 실패 시 코너 검출로 시도")
        self.corner_detection_check.stateChanged.connect(self._on_setting_changed)
        advanced_layout.addWidget(self.corner_detection_check)
        
        scoring_row = QHBoxLayout()
        scoring_row.addWidget(QLabel("컨투어 스코어링:"))
        self.scoring_combo = NoScrollComboBox()
        self.scoring_combo.addItems(["basic", "enhanced", "strict"])
        self.scoring_combo.setCurrentText("enhanced")
        self.scoring_combo.currentTextChanged.connect(self._on_setting_changed)
        scoring_row.addWidget(self.scoring_combo)
        advanced_layout.addLayout(scoring_row)
        
        layout.addWidget(advanced_group)
        
        # Hint
        hint_label = QLabel("""💡 조정 가이드:
• 흰색/밝은 배경: 기본값 (50-150) 권장
• 어두운 배경: 최소값 ↓ (30-120)
• 복잡한 무늬: 최대값 ↑ (70-200)""")
        hint_label.setObjectName("subtitleLabel")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "알고리즘")
    
    def _create_output_tab(self):
        """Create output settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
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
        
        self.tab_widget.addTab(tab, "출력 설정")
    
    def _create_filter_tab(self):
        """Create filter settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
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
        
        self.tab_widget.addTab(tab, "필터")
    
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
    
    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings
    
    @settings.setter
    def settings(self, value: AppSettings):
        """Set and load settings."""
        self._settings = value
        self._load_settings(value)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._load_settings(AppSettings())
        self._emit_settings()
