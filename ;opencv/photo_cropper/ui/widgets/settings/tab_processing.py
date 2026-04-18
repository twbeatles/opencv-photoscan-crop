from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ....i18n.catalog import t
from ..collapsible_section import CollapsibleSection
from ..toggle_switch import ModernToggleSwitch
from .controls import NoScrollComboBox, NoScrollDoubleSpinBox, NoScrollSpinBox

def create_processing_tab(self):
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
    self.font_browse_btn = QPushButton(t("dialog.browse"))
    self.font_browse_btn.clicked.connect(self._browse_watermark_font)
    font_path_layout.addWidget(self.watermark_font_path_edit)
    font_path_layout.addWidget(self.font_browse_btn)
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
