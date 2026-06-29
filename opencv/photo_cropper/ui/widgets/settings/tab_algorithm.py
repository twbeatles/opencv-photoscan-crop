from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ....i18n.catalog import t
from .controls import NoScrollComboBox, NoScrollDoubleSpinBox, NoScrollSlider, NoScrollSpinBox

def create_algorithm_tab(self):
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
        self.tuning_group = QGroupBox(t("settings.precision"))
        tuning_layout = QFormLayout(self.tuning_group)

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

        layout.addWidget(self.tuning_group)

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

        self.debug_browse_btn = QPushButton(t("dialog.browse"))
        self.debug_browse_btn.clicked.connect(self._browse_debug_output_dir)

        debug_path_layout.addWidget(self.debug_output_dir_edit)
        debug_path_layout.addWidget(self.debug_browse_btn)
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
