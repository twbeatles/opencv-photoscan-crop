#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings Panel Widget for Photo Cropper v9.0.

Provides tabbed settings interface for all application settings.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFormLayout,
    QFrame,
    QLineEdit,
    QScrollArea,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent

from ....core.settings_model import (
    AppSettings,
    AlgorithmSettings,
    DebugSettings,
    ProcessingSettings,
    OutputSettings,
    FilterSettings,
    UISettings,
    AdvancedProcessingSettings,
    FileManagementSettings,
    PerformanceSettings,
    WatermarkSettings,
    ResizeSettings,
    WatchModeSettings,
    MultiPhotoSettings,
    ClassificationSettings,
    FaceDetectionSettings,
    SmartEnhancementSettings,
    NotificationSettings,
)
from ..toggle_switch import ModernToggleSwitch
from ..collapsible_section import CollapsibleSection


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

    v9.0 Redesign: 11 tabs consolidated into 5 logical groups.

    Signals:
        settings_changed: Emitted when any setting changes
        preview_requested: Emitted when preview is requested
    """

    settings_changed = pyqtSignal(AppSettings)
    preview_requested = pyqtSignal()

    def __init__(self, settings: Optional[AppSettings] = None, parent=None):
        super().__init__(parent)
        self._settings = settings or AppSettings()
        self._block_signals = False
        self._setup_ui()
        self._load_settings(self._settings)

    def _setup_ui(self):
        """Setup the UI components with 5 consolidated tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 5 consolidated tabs (was 11)
        self._create_basic_tab()          # 📷 기본 (후처리 + UI + 출력 + 필터)
        self._create_algorithm_tab()      # 🔬 알고리즘
        self._create_processing_tab()     # 🔧 처리 (워터마크 + 리사이즈 + 고급)
        self._create_management_tab()     # 📂 관리 (자동화 + 파일관리 + 성능)
        self._create_ai_settings_tab()    # 🤖 AI

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
        """Create consolidated basic settings tab (post-processing + UI + output + filter)."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        # === Post-processing section ===
        post_section = CollapsibleSection("✨ 후처리 옵션")
        post_group = QWidget()
        post_layout = QVBoxLayout(post_group)
        post_layout.setContentsMargins(0, 0, 0, 0)

        self.auto_contrast_check = QCheckBox("자동 대비 향상 (CLAHE)")
        self.auto_contrast_check.setToolTip(
            "CLAHE 알고리즘으로 이미지 대비를 자동 향상합니다"
        )
        self.auto_contrast_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.auto_contrast_check)

        self.grayscale_check = QCheckBox("흑백으로 변환")
        self.grayscale_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.grayscale_check)

        self.sharpening_check = QCheckBox("선명도 향상")
        self.sharpening_check.stateChanged.connect(self._on_setting_changed)
        post_layout.addWidget(self.sharpening_check)

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

        post_section.add_widget(post_group)
        layout.addWidget(post_section)

        # === Output section ===
        out_section = CollapsibleSection("💾 출력 설정", initially_expanded=False)
        out_group = QWidget()
        out_layout = QFormLayout(out_group)
        out_layout.setContentsMargins(0, 0, 0, 0)

        self.format_combo = NoScrollComboBox()
        self.format_combo.addItems(["JPG", "PNG", "WEBP"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        out_layout.addRow("파일 형식:", self.format_combo)

        self.quality_spin = NoScrollSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.valueChanged.connect(self._on_setting_changed)
        out_layout.addRow("JPG/WEBP 품질:", self.quality_spin)

        self.png_compression_spin = NoScrollSpinBox()
        self.png_compression_spin.setRange(0, 9)
        self.png_compression_spin.setValue(6)
        self.png_compression_spin.setEnabled(False)
        self.png_compression_spin.valueChanged.connect(self._on_setting_changed)
        out_layout.addRow("PNG 압축 레벨:", self.png_compression_spin)

        self.timestamp_check = QCheckBox("타임스탬프 추가")
        self.timestamp_check.stateChanged.connect(self._on_setting_changed)
        out_layout.addRow(self.timestamp_check)

        self.preserve_metadata_check = QCheckBox("메타데이터 보존 (가능한 경우)")
        self.preserve_metadata_check.setToolTip(
            "EXIF/ICC 메타데이터를 best-effort로 복사합니다. 실패해도 저장은 계속됩니다."
        )
        self.preserve_metadata_check.stateChanged.connect(self._on_setting_changed)
        out_layout.addRow(self.preserve_metadata_check)

        self.backup_original_check = QCheckBox("원본 백업")
        self.backup_original_check.setToolTip(
            "처리 전 원본 파일을 backup 폴더에 복사합니다"
        )
        self.backup_original_check.stateChanged.connect(self._on_setting_changed)
        out_layout.addRow(self.backup_original_check)

        out_section.add_widget(out_group)
        layout.addWidget(out_section)

        # === Filter section ===
        filter_section = CollapsibleSection("📏 필터", initially_expanded=False)
        filter_group = QWidget()
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        self.skip_small_check = QCheckBox("작은 이미지 건너뛰기")
        self.skip_small_check.setChecked(True)
        self.skip_small_check.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.skip_small_check)

        min_size_row = QHBoxLayout()
        min_size_row.addSpacing(24)
        min_size_row.addWidget(QLabel("최소 크기 (px):"))
        self.min_size_spin = NoScrollSpinBox()
        self.min_size_spin.setRange(50, 1000)
        self.min_size_spin.setValue(100)
        self.min_size_spin.valueChanged.connect(self._on_setting_changed)
        min_size_row.addWidget(self.min_size_spin)
        filter_layout.addLayout(min_size_row)

        self.skip_processed_check = QCheckBox("이미 처리된 파일 건너뛰기")
        self.skip_processed_check.setToolTip("파일명에 '_cropped'가 포함된 파일 제외")
        self.skip_processed_check.stateChanged.connect(self._on_setting_changed)
        filter_layout.addWidget(self.skip_processed_check)

        filter_section.add_widget(filter_group)
        layout.addWidget(filter_section)

        # === UI section ===
        ui_section = CollapsibleSection("🎨 인터페이스", initially_expanded=False)
        ui_group = QWidget()
        ui_layout = QFormLayout(ui_group)
        ui_layout.setContentsMargins(0, 0, 0, 0)

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

        ui_section.add_widget(ui_group)
        layout.addWidget(ui_section)

        layout.addStretch()

        # Add scrollable tab
        self.tab_widget.addTab(self._make_scrollable_tab(content), "📷 기본")

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

        # Precision tuning (advanced algorithm parameters)
        tuning_group = QGroupBox("Precision Tuning")
        tuning_layout = QFormLayout(tuning_group)

        self.min_area_ratio_spin = NoScrollDoubleSpinBox()
        self.min_area_ratio_spin.setRange(0.01, 0.9)
        self.min_area_ratio_spin.setSingleStep(0.01)
        self.min_area_ratio_spin.setDecimals(3)
        self.min_area_ratio_spin.setValue(0.10)
        self.min_area_ratio_spin.valueChanged.connect(self._on_setting_changed)
        tuning_layout.addRow("Min area ratio:", self.min_area_ratio_spin)

        self.max_area_ratio_spin = NoScrollDoubleSpinBox()
        self.max_area_ratio_spin.setRange(0.1, 1.0)
        self.max_area_ratio_spin.setSingleStep(0.01)
        self.max_area_ratio_spin.setDecimals(3)
        self.max_area_ratio_spin.setValue(0.95)
        self.max_area_ratio_spin.valueChanged.connect(self._on_setting_changed)
        tuning_layout.addRow("Max area ratio:", self.max_area_ratio_spin)

        self.bg_mask_delta_spin = NoScrollDoubleSpinBox()
        self.bg_mask_delta_spin.setRange(5.0, 80.0)
        self.bg_mask_delta_spin.setSingleStep(1.0)
        self.bg_mask_delta_spin.setDecimals(1)
        self.bg_mask_delta_spin.setValue(30.0)
        self.bg_mask_delta_spin.valueChanged.connect(self._on_setting_changed)
        tuning_layout.addRow("Background mask delta:", self.bg_mask_delta_spin)

        self.adaptive_block_size_spin = NoScrollSpinBox()
        self.adaptive_block_size_spin.setRange(3, 61)
        self.adaptive_block_size_spin.setSingleStep(2)
        self.adaptive_block_size_spin.setValue(15)
        self.adaptive_block_size_spin.valueChanged.connect(self._on_setting_changed)
        tuning_layout.addRow("Adaptive block size:", self.adaptive_block_size_spin)

        self.adaptive_c_spin = NoScrollDoubleSpinBox()
        self.adaptive_c_spin.setRange(-20.0, 20.0)
        self.adaptive_c_spin.setSingleStep(0.5)
        self.adaptive_c_spin.setDecimals(2)
        self.adaptive_c_spin.setValue(4.0)
        self.adaptive_c_spin.valueChanged.connect(self._on_setting_changed)
        tuning_layout.addRow("Adaptive C:", self.adaptive_c_spin)

        layout.addWidget(tuning_group)

        # Detection mode + debug (v9.x crop accuracy)
        mode_group = QGroupBox("검출 모드 / 디버그")
        mode_layout = QFormLayout(mode_group)

        self.detect_mode_combo = NoScrollComboBox()
        self.detect_mode_combo.addItems(["fast", "balanced", "accurate"])
        self.detect_mode_combo.setCurrentText("balanced")
        self.detect_mode_combo.currentTextChanged.connect(self._on_setting_changed)
        mode_layout.addRow("검출 모드:", self.detect_mode_combo)

        self.debug_detect_check = QCheckBox("검출 디버그 저장 (_debug 폴더)")
        self.debug_detect_check.setToolTip(
            "엣지/마스크/후보 오버레이 등 중간 결과를 저장해서 실패 원인 분석에 사용합니다."
        )
        self.debug_detect_check.stateChanged.connect(self._on_setting_changed)
        mode_layout.addRow(self.debug_detect_check)

        debug_path_row = QWidget()
        debug_path_layout = QHBoxLayout(debug_path_row)
        debug_path_layout.setContentsMargins(0, 0, 0, 0)

        self.debug_output_dir_edit = QLineEdit()
        self.debug_output_dir_edit.setPlaceholderText(
            r"(선택) 디버그 폴더. 비우면 출력폴더/_debug 또는 %TEMP%/PhotoCropper/_debug"
        )
        self.debug_output_dir_edit.textChanged.connect(self._on_setting_changed)

        debug_browse_btn = QPushButton("Browse...")
        debug_browse_btn.clicked.connect(self._browse_debug_output_dir)

        debug_path_layout.addWidget(self.debug_output_dir_edit)
        debug_path_layout.addWidget(debug_browse_btn)
        mode_layout.addRow("디버그 폴더:", debug_path_row)

        layout.addWidget(mode_group)

        # Hint
        hint_label = QLabel("""💡 조정 가이드:
• 흰색/밝은 배경: 기본값 (50-150) 권장
• 어두운 배경: 최소값 ↓ (30-120)
• 복잡한 무늬: 최대값 ↑ (70-200)""")
        hint_label.setObjectName("subtitleLabel")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        layout.addStretch()
        self.tab_widget.addTab(self._make_scrollable_tab(content), "🔬 알고리즘")

    # NOTE: _create_output_tab and _create_filter_tab removed.
    # Content moved into _create_basic_tab as CollapsibleSections.

    def _create_processing_tab(self):
        """Create consolidated processing tab (watermark + resize + advanced)."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        # === Watermark section ===
        wm_section = CollapsibleSection("💧 워터마크", initially_expanded=False)
        wm_group = QWidget()
        wm_layout = QVBoxLayout(wm_group)
        wm_layout.setContentsMargins(0, 0, 0, 0)

        self.watermark_enable_check = ModernToggleSwitch("워터마크 사용")
        self.watermark_enable_check.toggled.connect(self._on_setting_changed)
        wm_layout.addWidget(self.watermark_enable_check)

        text_form = QFormLayout()
        self.watermark_text_edit = QLineEdit()
        self.watermark_text_edit.setPlaceholderText("예: © 2026 My Studio")
        self.watermark_text_edit.textChanged.connect(self._on_setting_changed)
        text_form.addRow("텍스트:", self.watermark_text_edit)

        font_path_row = QWidget()
        font_path_layout = QHBoxLayout(font_path_row)
        font_path_layout.setContentsMargins(0, 0, 0, 0)
        self.watermark_font_path_edit = QLineEdit()
        self.watermark_font_path_edit.setPlaceholderText(
            r"C:\Windows\Fonts\malgun.ttf (optional)"
        )
        self.watermark_font_path_edit.textChanged.connect(self._on_setting_changed)
        font_browse_btn = QPushButton("Browse...")
        font_browse_btn.clicked.connect(self._browse_watermark_font)
        font_path_layout.addWidget(self.watermark_font_path_edit)
        font_path_layout.addWidget(font_browse_btn)
        text_form.addRow("폰트 파일:", font_path_row)

        self.watermark_font_spin = NoScrollDoubleSpinBox()
        self.watermark_font_spin.setRange(0.5, 5.0)
        self.watermark_font_spin.setValue(1.0)
        self.watermark_font_spin.setSingleStep(0.1)
        self.watermark_font_spin.valueChanged.connect(self._on_setting_changed)
        text_form.addRow("글꼴 크기:", self.watermark_font_spin)

        self.watermark_opacity_spin = NoScrollSpinBox()
        self.watermark_opacity_spin.setRange(10, 100)
        self.watermark_opacity_spin.setValue(70)
        self.watermark_opacity_spin.valueChanged.connect(self._on_setting_changed)
        text_form.addRow("투명도 (%):", self.watermark_opacity_spin)

        self.watermark_position_combo = NoScrollComboBox()
        self.watermark_position_combo.addItems([
            "bottom_right", "bottom_left", "bottom_center",
            "top_right", "top_left", "top_center",
            "center", "middle_left", "middle_right",
        ])
        self.watermark_position_combo.currentTextChanged.connect(self._on_setting_changed)
        text_form.addRow("위치:", self.watermark_position_combo)
        wm_layout.addLayout(text_form)

        self.watermark_shadow_check = QCheckBox("그림자 효과")
        self.watermark_shadow_check.stateChanged.connect(self._on_setting_changed)
        wm_layout.addWidget(self.watermark_shadow_check)

        self.watermark_tiled_check = QCheckBox("타일 패턴으로 반복")
        self.watermark_tiled_check.stateChanged.connect(self._on_setting_changed)
        wm_layout.addWidget(self.watermark_tiled_check)

        tile_row = QHBoxLayout()
        tile_row.addSpacing(24)
        tile_row.addWidget(QLabel("타일 간격:"))
        self.watermark_spacing_spin = NoScrollSpinBox()
        self.watermark_spacing_spin.setRange(50, 500)
        self.watermark_spacing_spin.setValue(200)
        self.watermark_spacing_spin.valueChanged.connect(self._on_setting_changed)
        tile_row.addWidget(self.watermark_spacing_spin)
        wm_layout.addLayout(tile_row)

        wm_section.add_widget(wm_group)
        layout.addWidget(wm_section)

        # === Resize section ===
        rs_section = CollapsibleSection("📐 리사이즈", initially_expanded=False)
        rs_group = QWidget()
        rs_layout = QVBoxLayout(rs_group)
        rs_layout.setContentsMargins(0, 0, 0, 0)

        self.resize_enable_check = ModernToggleSwitch("리사이즈 사용")
        self.resize_enable_check.toggled.connect(self._on_setting_changed)
        rs_layout.addWidget(self.resize_enable_check)

        rs_form = QFormLayout()
        self.resize_mode_combo = NoScrollComboBox()
        self.resize_mode_combo.addItems([
            "none", "fit", "fill", "stretch",
            "width", "height", "percentage", "max_dimension",
        ])
        self.resize_mode_combo.currentTextChanged.connect(self._on_setting_changed)
        rs_form.addRow("모드:", self.resize_mode_combo)

        self.resize_width_spin = NoScrollSpinBox()
        self.resize_width_spin.setRange(100, 10000)
        self.resize_width_spin.setValue(1920)
        self.resize_width_spin.valueChanged.connect(self._on_setting_changed)
        rs_form.addRow("너비 (px):", self.resize_width_spin)

        self.resize_height_spin = NoScrollSpinBox()
        self.resize_height_spin.setRange(100, 10000)
        self.resize_height_spin.setValue(1080)
        self.resize_height_spin.valueChanged.connect(self._on_setting_changed)
        rs_form.addRow("높이 (px):", self.resize_height_spin)

        self.resize_percent_spin = NoScrollSpinBox()
        self.resize_percent_spin.setRange(10, 200)
        self.resize_percent_spin.setValue(100)
        self.resize_percent_spin.valueChanged.connect(self._on_setting_changed)
        rs_form.addRow("비율 (%):", self.resize_percent_spin)

        self.resize_max_dim_spin = NoScrollSpinBox()
        self.resize_max_dim_spin.setRange(100, 10000)
        self.resize_max_dim_spin.setValue(1920)
        self.resize_max_dim_spin.valueChanged.connect(self._on_setting_changed)
        rs_form.addRow("최대 크기:", self.resize_max_dim_spin)
        rs_layout.addLayout(rs_form)

        self.resize_upscale_check = QCheckBox("원본보다 큰 크기로 확대 허용")
        self.resize_upscale_check.stateChanged.connect(self._on_setting_changed)
        rs_layout.addWidget(self.resize_upscale_check)

        self.resize_aspect_check = QCheckBox("가로세로 비율 유지")
        self.resize_aspect_check.setChecked(True)
        self.resize_aspect_check.stateChanged.connect(self._on_setting_changed)
        rs_layout.addWidget(self.resize_aspect_check)

        rs_section.add_widget(rs_group)
        layout.addWidget(rs_section)

        # === Advanced processing section ===
        adv_section = CollapsibleSection("🔧 고급 처리", initially_expanded=False)
        adv_group = QWidget()
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setContentsMargins(0, 0, 0, 0)

        self.auto_deskew_check = ModernToggleSwitch("자동 기울기 보정")
        self.auto_deskew_check.setToolTip("Hough 변환으로 기울기를 감지하고 자동 교정")
        self.auto_deskew_check.toggled.connect(self._on_setting_changed)
        adv_layout.addWidget(self.auto_deskew_check)

        self.auto_color_check = ModernToggleSwitch("자동 색상 보정")
        self.auto_color_check.setToolTip("Gray World 알고리즘으로 화이트밸런스 보정")
        self.auto_color_check.toggled.connect(self._on_setting_changed)
        adv_layout.addWidget(self.auto_color_check)

        color_row = QHBoxLayout()
        color_row.addSpacing(24)
        color_row.addWidget(QLabel("보정 방식:"))
        self.color_method_combo = NoScrollComboBox()
        self.color_method_combo.addItems(["gray_world", "white_patch", "histogram"])
        self.color_method_combo.currentTextChanged.connect(self._on_setting_changed)
        color_row.addWidget(self.color_method_combo)
        adv_layout.addLayout(color_row)

        self.perspective_check = QCheckBox("자동 원근 교정")
        self.perspective_check.setToolTip("감지된 사각형을 기준으로 원근 왜곡 교정")
        self.perspective_check.stateChanged.connect(self._on_setting_changed)
        adv_layout.addWidget(self.perspective_check)

        self.enhanced_denoise_check = QCheckBox("강화된 노이즈 제거")
        self.enhanced_denoise_check.setToolTip("고급 비지역 평균 필터 적용")
        self.enhanced_denoise_check.stateChanged.connect(self._on_setting_changed)
        adv_layout.addWidget(self.enhanced_denoise_check)

        denoise_row = QHBoxLayout()
        denoise_row.addSpacing(24)
        denoise_row.addWidget(QLabel("강도:"))
        self.enhanced_denoise_spin = NoScrollSpinBox()
        self.enhanced_denoise_spin.setRange(1, 30)
        self.enhanced_denoise_spin.setValue(10)
        self.enhanced_denoise_spin.valueChanged.connect(self._on_setting_changed)
        denoise_row.addWidget(self.enhanced_denoise_spin)
        adv_layout.addLayout(denoise_row)

        self.restore_old_check = QCheckBox("오래된 사진 복원")
        self.restore_old_check.setToolTip("색바램, 얼룩 보정 및 대비 향상")
        self.restore_old_check.stateChanged.connect(self._on_setting_changed)
        adv_layout.addWidget(self.restore_old_check)

        self.enhanced_sharpen_check = QCheckBox("강화된 선명도")
        self.enhanced_sharpen_check.stateChanged.connect(self._on_setting_changed)
        adv_layout.addWidget(self.enhanced_sharpen_check)

        self.auto_crop_border_check = QCheckBox("자동 테두리 제거")
        self.auto_crop_border_check.setToolTip("스캔 테두리 자동 감지 및 제거")
        self.auto_crop_border_check.stateChanged.connect(self._on_setting_changed)
        adv_layout.addWidget(self.auto_crop_border_check)

        adv_section.add_widget(adv_group)
        layout.addWidget(adv_section)

        layout.addStretch()
        self.tab_widget.addTab(self._make_scrollable_tab(content), "🔧 처리")

    def _create_management_tab(self):
        """Create consolidated management tab (automation + file management + performance)."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        # === Watch mode section ===
        watch_section = CollapsibleSection("👁️ 폴더 감시 모드")
        watch_group = QWidget()
        watch_layout = QVBoxLayout(watch_group)
        watch_layout.setContentsMargins(0, 0, 0, 0)

        self.watch_mode_check = ModernToggleSwitch("Watch Mode 사용")
        self.watch_mode_check.setToolTip("새 이미지가 추가되면 자동으로 처리")
        self.watch_mode_check.toggled.connect(self._on_setting_changed)
        watch_layout.addWidget(self.watch_mode_check)

        self.watch_recursive_check = QCheckBox("하위 폴더도 감시")
        self.watch_recursive_check.stateChanged.connect(self._on_setting_changed)
        watch_layout.addWidget(self.watch_recursive_check)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("감지 지연 (ms):"))
        self.watch_delay_spin = NoScrollSpinBox()
        self.watch_delay_spin.setRange(100, 5000)
        self.watch_delay_spin.setValue(500)
        self.watch_delay_spin.setToolTip("파일 쓰기 완료를 기다리는 시간")
        self.watch_delay_spin.valueChanged.connect(self._on_setting_changed)
        delay_row.addWidget(self.watch_delay_spin)
        watch_layout.addLayout(delay_row)

        max_wait_row = QHBoxLayout()
        max_wait_row.addWidget(QLabel("최대 대기 시간(s):"))
        self.watch_max_wait_spin = NoScrollDoubleSpinBox()
        self.watch_max_wait_spin.setRange(1.0, 600.0)
        self.watch_max_wait_spin.setSingleStep(0.5)
        self.watch_max_wait_spin.setValue(30.0)
        self.watch_max_wait_spin.setToolTip("파일 준비 대기 최대 시간")
        self.watch_max_wait_spin.valueChanged.connect(self._on_setting_changed)
        max_wait_row.addWidget(self.watch_max_wait_spin)
        watch_layout.addLayout(max_wait_row)

        watch_section.add_widget(watch_group)
        layout.addWidget(watch_section)

        # === Scheduler section ===
        sched_section = CollapsibleSection("⏰ 스케줄러", initially_expanded=False)
        sched_group = QWidget()
        sched_layout = QVBoxLayout(sched_group)
        sched_layout.setContentsMargins(0, 0, 0, 0)

        self.scheduler_enable_check = ModernToggleSwitch("스케줄러 사용")
        self.scheduler_enable_check.setToolTip("예약된 시간에 자동으로 배치 처리")
        self.scheduler_enable_check.toggled.connect(self._on_setting_changed)
        sched_layout.addWidget(self.scheduler_enable_check)

        sched_form = QFormLayout()
        self.schedule_type_combo = NoScrollComboBox()
        self.schedule_type_combo.addItems(["interval", "once", "daily", "hourly"])
        self.schedule_type_combo.currentTextChanged.connect(self._on_schedule_type_changed)
        sched_form.addRow("스케줄 유형:", self.schedule_type_combo)

        self.schedule_time_edit = QLineEdit()
        self.schedule_time_edit.setPlaceholderText("HH:MM (예: 09:00)")
        self.schedule_time_edit.setText("00:00")
        self.schedule_time_edit.textChanged.connect(self._on_setting_changed)
        sched_form.addRow("시간:", self.schedule_time_edit)

        self.schedule_interval_spin = NoScrollSpinBox()
        self.schedule_interval_spin.setRange(5, 1440)
        self.schedule_interval_spin.setValue(60)
        self.schedule_interval_spin.valueChanged.connect(self._on_setting_changed)
        sched_form.addRow("간격 (분):", self.schedule_interval_spin)
        sched_layout.addLayout(sched_form)

        sched_section.add_widget(sched_group)
        layout.addWidget(sched_section)

        # === Multi-photo section ===
        mp_section = CollapsibleSection("🖼️ 멀티포토", initially_expanded=False)
        mp_group = QWidget()
        mp_layout = QVBoxLayout(mp_group)
        mp_layout.setContentsMargins(0, 0, 0, 0)

        self.multi_photo_enable_check = ModernToggleSwitch("멀티포토 감지 사용")
        self.multi_photo_enable_check.setToolTip(
            "한 장의 스캔 이미지에서 여러 사진을 분리 저장합니다."
        )
        self.multi_photo_enable_check.toggled.connect(self._on_setting_changed)
        mp_layout.addWidget(self.multi_photo_enable_check)

        merge_row = QHBoxLayout()
        merge_row.addWidget(QLabel("중복 병합 거리(px):"))
        self.multi_photo_merge_distance_spin = NoScrollSpinBox()
        self.multi_photo_merge_distance_spin.setRange(0, 1000)
        self.multi_photo_merge_distance_spin.setValue(50)
        self.multi_photo_merge_distance_spin.setToolTip(
            "값이 클수록 가까운 검출 결과를 같은 사진으로 병합합니다."
        )
        self.multi_photo_merge_distance_spin.valueChanged.connect(
            self._on_setting_changed
        )
        merge_row.addWidget(self.multi_photo_merge_distance_spin)
        mp_layout.addLayout(merge_row)

        self.multi_photo_separate_folders_check = QCheckBox(
            "파일별 하위폴더(<원본파일명>_photos)로 저장"
        )
        self.multi_photo_separate_folders_check.stateChanged.connect(
            self._on_setting_changed
        )
        mp_layout.addWidget(self.multi_photo_separate_folders_check)

        mp_section.add_widget(mp_group)
        layout.addWidget(mp_section)

        # === File management section ===
        fm_section = CollapsibleSection("📂 파일 관리", initially_expanded=False)
        fm_group = QWidget()
        fm_layout = QVBoxLayout(fm_group)
        fm_layout.setContentsMargins(0, 0, 0, 0)

        self.recursive_check = QCheckBox("하위 폴더 포함 (재귀 처리)")
        self.recursive_check.setToolTip("선택한 폴더와 모든 하위 폴더의 이미지를 처리")
        self.recursive_check.stateChanged.connect(self._on_setting_changed)
        fm_layout.addWidget(self.recursive_check)

        fm_form = QFormLayout()
        self.use_naming_rules_check = QCheckBox()
        self.use_naming_rules_check.stateChanged.connect(self._on_setting_changed)
        fm_form.addRow("파일명 규칙 사용:", self.use_naming_rules_check)

        self.naming_prefix_edit = QLineEdit()
        self.naming_prefix_edit.setPlaceholderText("예: scan_")
        self.naming_prefix_edit.textChanged.connect(self._on_setting_changed)
        fm_form.addRow("접두사:", self.naming_prefix_edit)

        self.naming_suffix_edit = QLineEdit()
        self.naming_suffix_edit.setPlaceholderText("예: _cropped")
        self.naming_suffix_edit.setText("_cropped")
        self.naming_suffix_edit.textChanged.connect(self._on_setting_changed)
        fm_form.addRow("접미사:", self.naming_suffix_edit)

        self.naming_counter_check = QCheckBox("일련번호 추가")
        self.naming_counter_check.stateChanged.connect(self._on_setting_changed)
        fm_form.addRow(self.naming_counter_check)

        self.naming_date_check = QCheckBox("날짜 추가")
        self.naming_date_check.stateChanged.connect(self._on_setting_changed)
        fm_form.addRow(self.naming_date_check)
        fm_layout.addLayout(fm_form)

        self.move_failed_check = QCheckBox("실패 파일 별도 폴더로 이동")
        self.move_failed_check.stateChanged.connect(self._on_setting_changed)
        fm_layout.addWidget(self.move_failed_check)

        self.copy_failed_check = QCheckBox("이동 대신 복사")
        self.copy_failed_check.stateChanged.connect(self._on_setting_changed)
        fm_layout.addWidget(self.copy_failed_check)

        log_form = QFormLayout()
        self.enable_log_check = QCheckBox()
        self.enable_log_check.setChecked(True)
        self.enable_log_check.stateChanged.connect(self._on_setting_changed)
        log_form.addRow("처리 로그 저장:", self.enable_log_check)

        self.log_format_combo = NoScrollComboBox()
        self.log_format_combo.addItems(["json", "csv"])
        self.log_format_combo.currentTextChanged.connect(self._on_setting_changed)
        log_form.addRow("로그 형식:", self.log_format_combo)
        fm_layout.addLayout(log_form)

        self.conflict_combo = NoScrollComboBox()
        self.conflict_combo.addItems(["rename", "overwrite", "skip"])
        self.conflict_combo.setItemText(0, "자동 이름 변경 (숫자 추가)")
        self.conflict_combo.setItemText(1, "덮어쓰기")
        self.conflict_combo.setItemText(2, "건너뛰기")
        self.conflict_combo.currentTextChanged.connect(self._on_setting_changed)
        fm_layout.addWidget(QLabel("파일명 충돌 시:"))
        fm_layout.addWidget(self.conflict_combo)

        sort_form = QFormLayout()
        self.sort_by_combo = NoScrollComboBox()
        self.sort_by_combo.addItems(["name", "date", "size"])
        self.sort_by_combo.setItemText(0, "이름순")
        self.sort_by_combo.setItemText(1, "날짜순")
        self.sort_by_combo.setItemText(2, "크기순")
        self.sort_by_combo.currentTextChanged.connect(self._on_setting_changed)
        sort_form.addRow("정렬 기준:", self.sort_by_combo)

        self.sort_reverse_check = QCheckBox("역순 정렬")
        self.sort_reverse_check.stateChanged.connect(self._on_setting_changed)
        sort_form.addRow("", self.sort_reverse_check)
        fm_layout.addLayout(sort_form)

        self.detect_dups_check = ModernToggleSwitch("처리 전 중복 파일 검사")
        self.detect_dups_check.setChecked(False)
        self.detect_dups_check.toggled.connect(self._on_setting_changed)
        fm_layout.addWidget(self.detect_dups_check)

        fm_section.add_widget(fm_group)
        layout.addWidget(fm_section)

        # === Performance section ===
        perf_section = CollapsibleSection("⚡ 성능", initially_expanded=False)
        perf_group = QWidget()
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.setContentsMargins(0, 0, 0, 0)

        perf_form = QFormLayout()
        self.max_threads_spin = NoScrollSpinBox()
        self.max_threads_spin.setRange(1, 32)
        self.max_threads_spin.setValue(4)
        self.max_threads_spin.setToolTip("동시에 처리할 이미지 수 (CPU 코어 수 권장)")
        self.max_threads_spin.valueChanged.connect(self._on_setting_changed)
        perf_form.addRow("최대 스레드 수:", self.max_threads_spin)
        perf_layout.addLayout(perf_form)

        self.low_mem_check = QCheckBox("저사양 모드 (메모리 절약)")
        self.low_mem_check.setToolTip("처리 속도가 느려질 수 있지만 메모리 사용량을 줄입니다.")
        self.low_mem_check.stateChanged.connect(self._on_setting_changed)
        perf_layout.addWidget(self.low_mem_check)

        perf_section.add_widget(perf_group)
        layout.addWidget(perf_section)

        # === Language section ===
        lang_section = CollapsibleSection("🌐 언어 설정", initially_expanded=False)
        lang_group = QWidget()
        lang_layout = QFormLayout(lang_group)
        lang_layout.setContentsMargins(0, 0, 0, 0)

        self.language_combo = NoScrollComboBox()
        self.language_combo.addItem("한국어", "ko")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("日本語", "ja")
        self.language_combo.addItem("简体中文", "zh")
        self.language_combo.addItem("Español", "es")
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addRow("언어:", self.language_combo)

        lang_info = QLabel("💡 언어 변경은 앱 재시작 후 완전히 적용됩니다.")
        lang_info.setWordWrap(True)
        lang_info.setObjectName("subtitleLabel")
        lang_layout.addRow(lang_info)

        lang_section.add_widget(lang_group)
        layout.addWidget(lang_section)

        layout.addStretch()
        self.tab_widget.addTab(self._make_scrollable_tab(content), "📂 관리")

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
            detection_mode=getattr(self, "detect_mode_combo", None)
            and self.detect_mode_combo.currentText()
            or "balanced",
            canny_min=self.canny_min_slider.value(),
            canny_max=self.canny_max_slider.value(),
            use_clahe=self.use_clahe_check.isChecked(),
            clahe_clip_limit=self.clahe_clip_spin.value(),
            clahe_grid_size=self.clahe_grid_spin.value(),
            multi_scale_edge=self.multi_scale_check.isChecked(),
            use_corner_detection=self.corner_detection_check.isChecked(),
            contour_scoring=self.scoring_combo.currentText(),
            min_area_ratio=self.min_area_ratio_spin.value(),
            max_area_ratio=self.max_area_ratio_spin.value(),
            bg_mask_delta=self.bg_mask_delta_spin.value(),
            adaptive_block_size=self.adaptive_block_size_spin.value(),
            adaptive_c=self.adaptive_c_spin.value(),
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
            preserve_metadata=self.preserve_metadata_check.isChecked(),
        )

        filter_settings = FilterSettings(
            skip_small_images=self.skip_small_check.isChecked(),
            min_image_size=self.min_size_spin.value(),
            skip_processed=self.skip_processed_check.isChecked(),
        )

        # Safe language reference - widget may not exist yet during init
        language = "ko"
        if hasattr(self, "language_combo") and self.language_combo is not None:
            language = (
                self.language_combo.itemData(self.language_combo.currentIndex()) or "ko"
            )

        ui = UISettings(
            theme=self.theme_combo.currentText(),
            language=language,
            auto_preview=self.auto_preview_check.isChecked(),
            show_contour_overlay=self.contour_overlay_check.isChecked(),
        )

        debug = DebugSettings(
            enabled=getattr(self, "debug_detect_check", None)
            and self.debug_detect_check.isChecked()
            or False,
            output_dir=getattr(self, "debug_output_dir_edit", None)
            and self.debug_output_dir_edit.text().strip()
            or "",
        )

        # v8.5 settings
        watermark = WatermarkSettings(
            enabled=self.watermark_enable_check.isChecked(),
            text=self.watermark_text_edit.text(),
            text_font_path=getattr(self, "watermark_font_path_edit", None)
            and self.watermark_font_path_edit.text().strip()
            or "",
            text_font_scale=self.watermark_font_spin.value(),
            opacity=self.watermark_opacity_spin.value() / 100.0,
            position=self.watermark_position_combo.currentText(),
            text_shadow=self.watermark_shadow_check.isChecked(),
            tiled=self.watermark_tiled_check.isChecked(),
            tile_spacing=self.watermark_spacing_spin.value(),
        )

        resize = ResizeSettings(
            enabled=self.resize_enable_check.isChecked(),
            mode=self.resize_mode_combo.currentText(),
            width=self.resize_width_spin.value(),
            height=self.resize_height_spin.value(),
            percentage=float(self.resize_percent_spin.value()),
            max_dimension=self.resize_max_dim_spin.value(),
            maintain_aspect=self.resize_aspect_check.isChecked(),
            upscale_allowed=self.resize_upscale_check.isChecked(),
        )

        # Build watch_mode with scheduler fields
        scheduler_check = getattr(self, "scheduler_enable_check", None)
        schedule_type_combo = getattr(self, "schedule_type_combo", None)
        schedule_time_edit = getattr(self, "schedule_time_edit", None)
        schedule_interval_spin = getattr(self, "schedule_interval_spin", None)
        watch_mode = WatchModeSettings(
            enabled=self.watch_mode_check.isChecked(),
            recursive=self.watch_recursive_check.isChecked(),
            debounce_ms=self.watch_delay_spin.value(),
            max_wait_seconds=float(
                self.watch_max_wait_spin.value()
                if hasattr(self, "watch_max_wait_spin")
                else 30.0
            ),
            scheduler_enabled=bool(
                scheduler_check.isChecked() if scheduler_check is not None else False
            ),
            schedule_type=(
                schedule_type_combo.currentText()
                if schedule_type_combo is not None
                else "interval"
            ),
            schedule_time=(
                schedule_time_edit.text()
                if schedule_time_edit is not None
                else "00:00"
            ),
            schedule_interval_minutes=(
                int(schedule_interval_spin.value())
                if schedule_interval_spin is not None
                else 60
            ),
        )

        prev_multi_photo = getattr(self._settings, "multi_photo", MultiPhotoSettings())
        multi_photo = MultiPhotoSettings(
            enabled=self.multi_photo_enable_check.isChecked()
            if hasattr(self, "multi_photo_enable_check")
            else bool(getattr(prev_multi_photo, "enabled", False)),
            min_photos=int(getattr(prev_multi_photo, "min_photos", 1)),
            max_photos=int(getattr(prev_multi_photo, "max_photos", 20)),
            min_area_ratio=float(getattr(prev_multi_photo, "min_area_ratio", 0.02)),
            max_area_ratio=float(getattr(prev_multi_photo, "max_area_ratio", 0.8)),
            merge_distance=self.multi_photo_merge_distance_spin.value()
            if hasattr(self, "multi_photo_merge_distance_spin")
            else int(getattr(prev_multi_photo, "merge_distance", 50)),
            separate_output_folders=self.multi_photo_separate_folders_check.isChecked()
            if hasattr(self, "multi_photo_separate_folders_check")
            else bool(getattr(prev_multi_photo, "separate_output_folders", False)),
        )

        # v8.0 Advanced settings - safely build if widgets exist
        advanced = AdvancedProcessingSettings()
        if hasattr(self, "auto_deskew_check"):
            advanced = AdvancedProcessingSettings(
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

        # v8.0 File management settings
        file_management = FileManagementSettings()
        if hasattr(self, "recursive_check"):
            file_management = FileManagementSettings(
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

        # v9.x Performance settings (management tab controls)
        prev_perf = getattr(self._settings, "performance", PerformanceSettings())
        thread_count = max(1, int(self.max_threads_spin.value()))
        low_mem_mode = self.low_mem_check.isChecked()
        performance = PerformanceSettings(
            use_gpu=getattr(prev_perf, "use_gpu", False),
            gpu_device_id=getattr(prev_perf, "gpu_device_id", 0),
            enable_multithreading=thread_count > 1,
            thread_count=thread_count,
            max_image_size_mb=50 if low_mem_mode else 100,
            downscale_large_images=True,
            downscale_threshold_mp=24.0 if low_mem_mode else 50.0,
        )

        # v9.0 Classification settings
        prev_cls = getattr(self._settings, "classification", ClassificationSettings())
        classification = ClassificationSettings()
        if hasattr(self, "classification_enable_check"):
            category_folders = dict(getattr(prev_cls, "category_folders", {}) or {})
            default_folders = ClassificationSettings().category_folders
            folder_inputs = getattr(self, "classification_folder_inputs", {}) or {}
            if isinstance(folder_inputs, dict):
                for key in ("portrait", "landscape", "document", "blackwhite", "other"):
                    widget = folder_inputs.get(key)
                    if widget is None:
                        continue
                    value = str(widget.text() if hasattr(widget, "text") else "").strip()
                    category_folders[key] = value or str(default_folders.get(key, key))
            classification = ClassificationSettings(
                enabled=self.classification_enable_check.isChecked(),
                model=self.classification_model_combo.currentText()
                if hasattr(self, "classification_model_combo")
                else "basic",
                auto_folder=self.classification_subfolders_check.isChecked(),
                categories_enabled=dict(
                    getattr(prev_cls, "categories_enabled", {}) or {}
                ),
                category_folders=category_folders,
                min_confidence=float(getattr(prev_cls, "min_confidence", 0.5)),
            )

        # v9.0 Face detection settings
        prev_face = getattr(self._settings, "face_detection", FaceDetectionSettings())
        face_detection = FaceDetectionSettings()
        if hasattr(self, "face_detect_enable_check"):
            face_detection = FaceDetectionSettings(
                enabled=self.face_detect_enable_check.isChecked(),
                use_dnn=self.face_use_dnn_check.isChecked()
                if hasattr(self, "face_use_dnn_check")
                else False,
                auto_rotate=self.face_auto_orient_check.isChecked(),
                auto_center_crop=self.face_enhance_check.isChecked(),
                show_overlay=bool(getattr(prev_face, "show_overlay", True)),
                detect_eyes=bool(getattr(prev_face, "detect_eyes", True)),
                min_face_size=self.face_min_size_spin.value()
                if hasattr(self, "face_min_size_spin")
                else 30,
            )

        # v9.0 Smart enhancement settings
        prev_smart = getattr(
            self._settings, "smart_enhancement", SmartEnhancementSettings()
        )
        smart_enhancement = SmartEnhancementSettings()
        if hasattr(self, "smart_enhance_enable_check"):
            smart_enhancement = SmartEnhancementSettings(
                enabled=self.smart_enhance_enable_check.isChecked(),
                auto_preset=bool(getattr(prev_smart, "auto_preset", True)),
                default_preset=str(getattr(prev_smart, "default_preset", "none")),
                apply_to_batch=bool(getattr(prev_smart, "apply_to_batch", True)),
                adjust_exposure=self.smart_exposure_check.isChecked()
                if hasattr(self, "smart_exposure_check")
                else True,
                adjust_color_balance=self.smart_color_balance_check.isChecked()
                if hasattr(self, "smart_color_balance_check")
                else True,
                strength=self.smart_strength_spin.value()
                if hasattr(self, "smart_strength_spin")
                else 50,
            )

        # v9.0 Notification settings
        notification = NotificationSettings()
        if hasattr(self, "notification_enable_check"):
            notification = NotificationSettings(
                enabled=self.notification_enable_check.isChecked(),
                play_sound=self.notification_sound_check.isChecked(),
                on_error=self.notification_error_only_check.isChecked(),
            )

        return AppSettings(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            debug=debug,
            advanced=advanced,
            file_management=file_management,
            performance=performance,
            watermark=watermark,
            resize=resize,
            watch_mode=watch_mode,
            multi_photo=multi_photo,
            classification=classification,
            face_detection=face_detection,
            smart_enhancement=smart_enhancement,
            notification=notification,
            create_backup=self.backup_original_check.isChecked(),
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
        if hasattr(self, "min_area_ratio_spin"):
            self.min_area_ratio_spin.setValue(float(settings.algorithm.min_area_ratio))
        if hasattr(self, "max_area_ratio_spin"):
            self.max_area_ratio_spin.setValue(float(settings.algorithm.max_area_ratio))
        if hasattr(self, "bg_mask_delta_spin"):
            self.bg_mask_delta_spin.setValue(
                float(getattr(settings.algorithm, "bg_mask_delta", 30.0))
            )
        if hasattr(self, "adaptive_block_size_spin"):
            self.adaptive_block_size_spin.setValue(
                int(getattr(settings.algorithm, "adaptive_block_size", 15))
            )
        if hasattr(self, "adaptive_c_spin"):
            self.adaptive_c_spin.setValue(
                float(getattr(settings.algorithm, "adaptive_c", 4.0))
            )

        if hasattr(self, "detect_mode_combo"):
            idx = self.detect_mode_combo.findText(getattr(settings.algorithm, "detection_mode", "balanced"))
            if idx >= 0:
                self.detect_mode_combo.setCurrentIndex(idx)

        if hasattr(self, "debug_detect_check") and hasattr(settings, "debug"):
            self.debug_detect_check.setChecked(bool(settings.debug.enabled))
        if hasattr(self, "debug_output_dir_edit") and hasattr(settings, "debug"):
            self.debug_output_dir_edit.setText(getattr(settings.debug, "output_dir", "") or "")

        # Processing
        self.auto_contrast_check.setChecked(settings.processing.auto_contrast)
        self.grayscale_check.setChecked(settings.processing.to_grayscale)
        self.sharpening_check.setChecked(settings.processing.apply_sharpening)
        self.sharpening_slider.setValue(
            int(settings.processing.sharpening_strength * 10)
        )
        self.sharpening_value.setText(f"{settings.processing.sharpening_strength:.1f}")
        self.denoise_check.setChecked(settings.processing.denoise)

        # Output
        index = self.format_combo.findText(settings.output.output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.quality_spin.setValue(settings.output.jpg_quality)
        self.png_compression_spin.setValue(settings.output.png_compression)
        self.timestamp_check.setChecked(settings.output.add_timestamp)
        self.preserve_metadata_check.setChecked(
            bool(getattr(settings.output, "preserve_metadata", False))
        )

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

        # Language
        if hasattr(settings.ui, "language"):
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == settings.ui.language:
                    self.language_combo.setCurrentIndex(i)
                    break

        # Misc
        self.backup_original_check.setChecked(settings.create_backup)

        # Format-dependent enables
        is_png = settings.output.output_format.upper() == "PNG"
        self.quality_spin.setEnabled(not is_png)
        self.png_compression_spin.setEnabled(is_png)

        # v8.5 Watermark settings
        if hasattr(settings, "watermark"):
            wm = settings.watermark
            self.watermark_enable_check.setChecked(wm.enabled)
            self.watermark_text_edit.setText(wm.text)
            if hasattr(self, "watermark_font_path_edit"):
                self.watermark_font_path_edit.setText(getattr(wm, "text_font_path", ""))
            self.watermark_font_spin.setValue(wm.text_font_scale)
            self.watermark_opacity_spin.setValue(int(wm.opacity * 100))
            idx = self.watermark_position_combo.findText(wm.position)
            if idx >= 0:
                self.watermark_position_combo.setCurrentIndex(idx)
            self.watermark_shadow_check.setChecked(wm.text_shadow)
            self.watermark_tiled_check.setChecked(wm.tiled)
            self.watermark_spacing_spin.setValue(wm.tile_spacing)

        # v8.5 Resize settings
        if hasattr(settings, "resize"):
            rs = settings.resize
            self.resize_enable_check.setChecked(rs.enabled)
            idx = self.resize_mode_combo.findText(rs.mode)
            if idx >= 0:
                self.resize_mode_combo.setCurrentIndex(idx)
            self.resize_width_spin.setValue(rs.width)
            self.resize_height_spin.setValue(rs.height)
            self.resize_percent_spin.setValue(int(rs.percentage))
            self.resize_max_dim_spin.setValue(rs.max_dimension)
            self.resize_aspect_check.setChecked(rs.maintain_aspect)
            self.resize_upscale_check.setChecked(rs.upscale_allowed)

        # v8.5 Watch mode settings
        if hasattr(settings, "watch_mode"):
            wm = settings.watch_mode
            self.watch_mode_check.setChecked(wm.enabled)
            self.watch_recursive_check.setChecked(wm.recursive)
            self.watch_delay_spin.setValue(wm.debounce_ms)
            if hasattr(self, "watch_max_wait_spin"):
                self.watch_max_wait_spin.setValue(
                    float(getattr(wm, "max_wait_seconds", 30.0))
                )
            if hasattr(self, "scheduler_enable_check"):
                self.scheduler_enable_check.setChecked(
                    bool(getattr(wm, "scheduler_enabled", False))
                )
            if hasattr(self, "schedule_type_combo"):
                idx = self.schedule_type_combo.findText(
                    str(getattr(wm, "schedule_type", "interval") or "interval")
                )
                if idx >= 0:
                    self.schedule_type_combo.setCurrentIndex(idx)
            if hasattr(self, "schedule_time_edit"):
                self.schedule_time_edit.setText(
                    str(getattr(wm, "schedule_time", "00:00") or "00:00")
                )
            if hasattr(self, "schedule_interval_spin"):
                self.schedule_interval_spin.setValue(
                    int(getattr(wm, "schedule_interval_minutes", 60) or 60)
                )
            if hasattr(self, "schedule_type_combo"):
                self._on_schedule_type_changed(self.schedule_type_combo.currentText())

        if hasattr(settings, "multi_photo"):
            mp = settings.multi_photo
            if hasattr(self, "multi_photo_enable_check"):
                self.multi_photo_enable_check.setChecked(bool(mp.enabled))
            if hasattr(self, "multi_photo_merge_distance_spin"):
                self.multi_photo_merge_distance_spin.setValue(
                    int(getattr(mp, "merge_distance", 50))
                )
            if hasattr(self, "multi_photo_separate_folders_check"):
                self.multi_photo_separate_folders_check.setChecked(
                    bool(getattr(mp, "separate_output_folders", False))
                )

        # v9.0 AI settings
        if hasattr(settings, "classification"):
            cs = settings.classification
            self.classification_enable_check.setChecked(cs.enabled)
            self.classification_subfolders_check.setChecked(cs.auto_folder)
            if hasattr(self, "classification_model_combo"):
                idx = self.classification_model_combo.findText(
                    getattr(cs, "model", "basic")
                )
                if idx >= 0:
                    self.classification_model_combo.setCurrentIndex(idx)
            folder_inputs = getattr(self, "classification_folder_inputs", {}) or {}
            folder_map = dict(getattr(cs, "category_folders", {}) or {})
            defaults = ClassificationSettings().category_folders
            for key in ("portrait", "landscape", "document", "blackwhite", "other"):
                widget = folder_inputs.get(key) if isinstance(folder_inputs, dict) else None
                if widget is None:
                    continue
                widget.setText(str(folder_map.get(key, defaults.get(key, key))))

        if hasattr(settings, "face_detection"):
            fd = settings.face_detection
            self.face_detect_enable_check.setChecked(fd.enabled)
            if hasattr(self, "face_use_dnn_check"):
                self.face_use_dnn_check.setChecked(getattr(fd, "use_dnn", False))
            self.face_auto_orient_check.setChecked(fd.auto_rotate)
            self.face_enhance_check.setChecked(fd.auto_center_crop)
            if hasattr(self, "face_min_size_spin"):
                self.face_min_size_spin.setValue(
                    int(getattr(fd, "min_face_size", 30))
                )

        if hasattr(settings, "smart_enhancement"):
            se = settings.smart_enhancement
            self.smart_enhance_enable_check.setChecked(se.enabled)
            if hasattr(self, "smart_exposure_check"):
                self.smart_exposure_check.setChecked(
                    bool(getattr(se, "adjust_exposure", True))
                )
            if hasattr(self, "smart_color_balance_check"):
                self.smart_color_balance_check.setChecked(
                    bool(getattr(se, "adjust_color_balance", True))
                )
            if hasattr(self, "smart_strength_spin"):
                self.smart_strength_spin.setValue(int(getattr(se, "strength", 50)))

        if hasattr(settings, "notification"):
            ns = settings.notification
            self.notification_enable_check.setChecked(ns.enabled)
            self.notification_sound_check.setChecked(ns.play_sound)
            self.notification_error_only_check.setChecked(ns.on_error)

        # Performance (management tab)
        if hasattr(settings, "performance"):
            perf = settings.performance
            self.max_threads_spin.setValue(max(1, int(perf.thread_count)))
            low_mem_mode = (
                int(getattr(perf, "max_image_size_mb", 100)) <= 50
                or float(getattr(perf, "downscale_threshold_mp", 50.0)) <= 24.0
            )
            self.low_mem_check.setChecked(low_mem_mode)

        self._block_signals = False


    def _browse_watermark_font(self):

        """Browse for a font file (.ttf/.otf) for Unicode watermark rendering."""

        try:

            path, _ = QFileDialog.getOpenFileName(

                self,

                "폰트 파일 선택",

                "",

                "Font Files (*.ttf *.otf);;All Files (*)",

            )

            if path:

                self.watermark_font_path_edit.setText(path)

        except Exception:

            pass



    def _browse_debug_output_dir(self):

        """Browse for a directory to store detection debug artifacts."""

        try:

            path = QFileDialog.getExistingDirectory(

                self,

                "디버그 폴더 선택",

                "",

            )

            if path:

                self.debug_output_dir_edit.setText(path)

        except Exception:

            pass



    def _on_language_changed(self, index: int):

        """Handle language selection change."""

        lang_code = self.language_combo.itemData(index)

        if lang_code:

            from ....i18n.catalog import set_language



            set_language(lang_code)

            self._on_setting_changed()



    def _create_ai_settings_tab(self):
        """Create v9.0 AI settings tab."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(15)

        # Classification settings
        class_group = QGroupBox("📊 이미지 자동 분류")
        class_layout = QVBoxLayout(class_group)

        self.classification_enable_check = ModernToggleSwitch("자동 분류 사용")
        self.classification_enable_check.setToolTip(
            "이미지를 유형별로 자동 분류하여 저장"
        )
        self.classification_enable_check.toggled.connect(self._on_setting_changed)
        class_layout.addWidget(self.classification_enable_check)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("분류 모델:"))
        self.classification_model_combo = NoScrollComboBox()
        self.classification_model_combo.addItems(["basic", "advanced", "custom"])
        self.classification_model_combo.currentTextChanged.connect(
            self._on_setting_changed
        )
        model_row.addWidget(self.classification_model_combo)
        class_layout.addLayout(model_row)

        self.classification_subfolders_check = QCheckBox("분류된 하위 폴더에 저장")
        self.classification_subfolders_check.stateChanged.connect(
            self._on_setting_changed
        )
        class_layout.addWidget(self.classification_subfolders_check)

        folder_form = QFormLayout()
        self.classification_folder_inputs = {}
        folder_labels = [
            ("portrait", "인물 폴더명:"),
            ("landscape", "풍경 폴더명:"),
            ("document", "문서 폴더명:"),
            ("blackwhite", "흑백 폴더명:"),
            ("other", "기타 폴더명:"),
        ]
        defaults = ClassificationSettings().category_folders
        for key, label in folder_labels:
            folder_edit = QLineEdit()
            folder_edit.setPlaceholderText(str(defaults.get(key, key)))
            folder_edit.textChanged.connect(self._on_setting_changed)
            self.classification_folder_inputs[key] = folder_edit
            folder_form.addRow(label, folder_edit)
        class_layout.addLayout(folder_form)

        layout.addWidget(class_group)

        # Face detection settings
        face_group = QGroupBox("👤 얼굴 감지")
        face_layout = QVBoxLayout(face_group)

        self.face_detect_enable_check = ModernToggleSwitch("얼굴 감지 사용")
        self.face_detect_enable_check.setToolTip("인물 사진에서 얼굴을 감지하여 최적화")
        self.face_detect_enable_check.toggled.connect(self._on_setting_changed)
        face_layout.addWidget(self.face_detect_enable_check)

        self.face_use_dnn_check = QCheckBox("DNN 얼굴 감지 사용 (초기 모델 다운로드)")
        self.face_use_dnn_check.setToolTip(
            "활성화 시 더 정확한 얼굴 감지를 시도합니다. 네트워크 실패 시 기본(Haar) 방식으로 자동 전환됩니다."
        )
        self.face_use_dnn_check.stateChanged.connect(self._on_setting_changed)
        face_layout.addWidget(self.face_use_dnn_check)

        self.face_auto_orient_check = QCheckBox("얼굴 기준 자동 회전")
        self.face_auto_orient_check.stateChanged.connect(self._on_setting_changed)
        face_layout.addWidget(self.face_auto_orient_check)

        self.face_enhance_check = QCheckBox("얼굴 영역 보정 적용")
        self.face_enhance_check.stateChanged.connect(self._on_setting_changed)
        face_layout.addWidget(self.face_enhance_check)

        min_size_row = QHBoxLayout()
        min_size_row.addWidget(QLabel("최소 얼굴 크기 (px):"))
        self.face_min_size_spin = NoScrollSpinBox()
        self.face_min_size_spin.setRange(20, 500)
        self.face_min_size_spin.setValue(30)
        self.face_min_size_spin.valueChanged.connect(self._on_setting_changed)
        min_size_row.addWidget(self.face_min_size_spin)
        face_layout.addLayout(min_size_row)

        layout.addWidget(face_group)

        # Smart enhancement settings
        smart_group = QGroupBox("✨ 스마트 보정")
        smart_layout = QVBoxLayout(smart_group)

        self.smart_enhance_enable_check = ModernToggleSwitch("스마트 보정 사용")
        self.smart_enhance_enable_check.setToolTip("이미지 특성에 맞는 자동 보정 적용")
        self.smart_enhance_enable_check.toggled.connect(self._on_setting_changed)
        smart_layout.addWidget(self.smart_enhance_enable_check)

        self.smart_exposure_check = QCheckBox("노출 자동 조정")
        self.smart_exposure_check.stateChanged.connect(self._on_setting_changed)
        smart_layout.addWidget(self.smart_exposure_check)

        self.smart_color_balance_check = QCheckBox("색상 균형 자동 조정")
        self.smart_color_balance_check.stateChanged.connect(self._on_setting_changed)
        smart_layout.addWidget(self.smart_color_balance_check)

        strength_row = QHBoxLayout()
        strength_row.addWidget(QLabel("보정 강도:"))
        self.smart_strength_spin = NoScrollSpinBox()
        self.smart_strength_spin.setRange(0, 100)
        self.smart_strength_spin.setValue(50)
        self.smart_strength_spin.valueChanged.connect(self._on_setting_changed)
        strength_row.addWidget(self.smart_strength_spin)
        smart_layout.addLayout(strength_row)

        layout.addWidget(smart_group)

        # Notification settings
        notif_group = QGroupBox("🔔 알림 설정")
        notif_layout = QVBoxLayout(notif_group)

        self.notification_enable_check = ModernToggleSwitch("시스템 알림 사용")
        self.notification_enable_check.setToolTip("배치 처리 완료 시 시스템 알림 표시")
        self.notification_enable_check.toggled.connect(self._on_setting_changed)
        notif_layout.addWidget(self.notification_enable_check)

        self.notification_sound_check = QCheckBox("알림 소리 재생")
        self.notification_sound_check.stateChanged.connect(self._on_setting_changed)
        notif_layout.addWidget(self.notification_sound_check)

        self.notification_error_only_check = QCheckBox("오류 시에만 알림")
        self.notification_error_only_check.stateChanged.connect(
            self._on_setting_changed
        )
        notif_layout.addWidget(self.notification_error_only_check)

        layout.addWidget(notif_group)
        layout.addStretch()

        self.tab_widget.addTab(self._make_scrollable_tab(content), "🤖 AI")

    def _on_schedule_type_changed(self, schedule_type: str):
        """Handle schedule type change to show/hide relevant controls."""
        # Show time field for daily/once, interval for interval mode
        if hasattr(self, "schedule_time_edit"):
            show_time = schedule_type in ("daily", "once")
            self.schedule_time_edit.setEnabled(show_time)
        if hasattr(self, "schedule_interval_spin"):
            show_interval = schedule_type in ("interval", "hourly")
            self.schedule_interval_spin.setEnabled(show_interval)
        self._on_setting_changed()

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
        low_mem_mode = self.low_mem_check.isChecked()
        settings.performance = PerformanceSettings(
            use_gpu=getattr(settings.performance, "use_gpu", False),
            gpu_device_id=getattr(settings.performance, "gpu_device_id", 0),
            enable_multithreading=self.max_threads_spin.value() > 1,
            thread_count=self.max_threads_spin.value(),
            max_image_size_mb=50 if low_mem_mode else 100,
            downscale_large_images=True,
            downscale_threshold_mp=24.0 if low_mem_mode else 50.0,
        )

        return settings

    def _load_settings_v8(self, settings: AppSettings):
        """Load v8.0 settings into UI."""
        # Advanced settings
        if hasattr(settings, "advanced"):
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
        if hasattr(settings, "file_management"):
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
        if hasattr(settings, "performance"):
            perf = settings.performance
            if hasattr(self, "max_threads_spin"):
                self.max_threads_spin.setValue(max(1, int(perf.thread_count)))
            if hasattr(self, "low_mem_check"):
                self.low_mem_check.setChecked(
                    int(getattr(perf, "max_image_size_mb", 100)) <= 50
                    or float(getattr(perf, "downscale_threshold_mp", 50.0)) <= 24.0
                )

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
