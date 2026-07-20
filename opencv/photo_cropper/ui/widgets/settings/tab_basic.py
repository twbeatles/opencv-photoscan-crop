from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..collapsible_section import CollapsibleSection
from ..toggle_switch import ModernToggleSwitch
from .controls import NoScrollComboBox, NoScrollSlider, NoScrollSpinBox

def create_basic_tab(self):
    """Create consolidated basic settings tab (post-processing + UI + output + filter)."""
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(10)

    # === Post-processing section ===
    self.post_section = CollapsibleSection("✨ 후처리 옵션")
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

    self.post_section.add_widget(post_group)
    layout.addWidget(self.post_section)

    # === Output section ===
    self.output_section = CollapsibleSection("💾 출력 설정", initially_expanded=False)
    out_group = QWidget()
    self.output_form = QFormLayout(out_group)
    self.output_form.setContentsMargins(0, 0, 0, 0)

    self.format_combo = NoScrollComboBox()
    self.format_combo.addItems(["JPG", "PNG", "WEBP"])
    self.format_combo.currentTextChanged.connect(self._on_format_changed)
    self.output_form.addRow("파일 형식:", self.format_combo)

    self.quality_spin = NoScrollSpinBox()
    self.quality_spin.setRange(1, 100)
    self.quality_spin.setValue(95)
    self.quality_spin.valueChanged.connect(self._on_setting_changed)
    self.output_form.addRow("JPG/WEBP 품질:", self.quality_spin)

    self.png_compression_spin = NoScrollSpinBox()
    self.png_compression_spin.setRange(0, 9)
    self.png_compression_spin.setValue(6)
    self.png_compression_spin.setEnabled(False)
    self.png_compression_spin.valueChanged.connect(self._on_setting_changed)
    self.output_form.addRow("PNG 압축 레벨:", self.png_compression_spin)

    self.timestamp_check = QCheckBox("타임스탬프 추가")
    self.timestamp_check.stateChanged.connect(self._on_setting_changed)
    self.output_form.addRow(self.timestamp_check)

    self.preserve_metadata_check = QCheckBox("메타데이터 보존 (가능한 경우)")
    self.preserve_metadata_check.setToolTip(
        "EXIF/ICC 메타데이터를 best-effort로 복사합니다. 실패해도 저장은 계속됩니다."
    )
    self.preserve_metadata_check.stateChanged.connect(self._on_setting_changed)
    self.output_form.addRow(self.preserve_metadata_check)

    self.backup_original_check = QCheckBox("원본 백업")
    self.backup_original_check.setToolTip(
        "처리 전 원본 파일을 backup 폴더에 복사합니다"
    )
    self.backup_original_check.stateChanged.connect(self._on_setting_changed)
    self.output_form.addRow(self.backup_original_check)

    self.output_section.add_widget(out_group)
    layout.addWidget(self.output_section)

    # === Filter section ===
    self.filter_section = CollapsibleSection("📏 필터", initially_expanded=False)
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

    self.filter_section.add_widget(filter_group)
    layout.addWidget(self.filter_section)

    # === UI section ===
    self.ui_section = CollapsibleSection("🎨 인터페이스", initially_expanded=True)
    ui_group = QWidget()
    self.ui_form = QFormLayout(ui_group)
    self.ui_form.setContentsMargins(0, 0, 0, 0)

    self.simple_mode_check = ModernToggleSwitch("간단 모드 (고급 탭 숨기기)")
    self.simple_mode_check.setToolTip(
        "켜면 알고리즘/처리/관리/AI 탭을 숨기고 기본 작업에 집중합니다. "
        "장면 프리셋은 워크벤치 상단에서 사용할 수 있습니다."
    )
    self.simple_mode_check.setChecked(True)
    self.simple_mode_check.toggled.connect(self._on_simple_mode_toggled)
    self.ui_form.addRow(self.simple_mode_check)

    self.theme_combo = NoScrollComboBox()
    self.theme_combo.addItems(["dark", "light"])
    self.theme_combo.currentTextChanged.connect(self._on_setting_changed)
    self.ui_form.addRow("테마:", self.theme_combo)

    self.auto_preview_check = ModernToggleSwitch("설정 변경 시 자동 미리보기")
    self.auto_preview_check.setChecked(True)
    self.auto_preview_check.toggled.connect(self._on_setting_changed)
    self.ui_form.addRow(self.auto_preview_check)

    self.contour_overlay_check = ModernToggleSwitch("검출 영역 오버레이 표시")
    self.contour_overlay_check.setChecked(True)
    self.contour_overlay_check.toggled.connect(self._on_setting_changed)
    self.ui_form.addRow(self.contour_overlay_check)

    self.ui_section.add_widget(ui_group)
    layout.addWidget(self.ui_section)

    layout.addStretch()

    # Add scrollable tab
    self.tab_widget.addTab(self._make_scrollable_tab(content), "📷 기본")
