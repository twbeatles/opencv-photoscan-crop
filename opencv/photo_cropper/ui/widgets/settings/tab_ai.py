from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ....core.settings_model import CLASSIFICATION_CATEGORY_KEYS
from ....i18n.catalog import get_category_folder_defaults, t
from ..toggle_switch import ModernToggleSwitch
from .controls import NoScrollComboBox, NoScrollSpinBox

def create_ai_settings_tab(self):
    """Create v9.0 AI settings tab."""
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(15)

    # Classification settings
    self.classification_group = QGroupBox("📊 이미지 자동 분류")
    class_layout = QVBoxLayout(self.classification_group)

    self.classification_enable_check = ModernToggleSwitch("자동 분류 사용")
    self.classification_enable_check.setToolTip(
        "이미지를 유형별로 자동 분류하여 저장"
    )
    self.classification_enable_check.toggled.connect(self._on_setting_changed)
    class_layout.addWidget(self.classification_enable_check)

    model_row = QHBoxLayout()
    self.classification_model_label = QLabel("분류 모델:")
    model_row.addWidget(self.classification_model_label)
    self.classification_model_combo = NoScrollComboBox()
    self.classification_model_combo.addItems(["basic", "advanced"])
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

    self.classification_folder_form = QFormLayout()
    self.classification_folder_inputs = {}
    defaults = get_category_folder_defaults()
    for key in CLASSIFICATION_CATEGORY_KEYS:
        folder_edit = QLineEdit()
        folder_edit.setPlaceholderText(str(defaults.get(key, key)))
        folder_edit.textChanged.connect(self._on_setting_changed)
        self.classification_folder_inputs[key] = folder_edit
        self.classification_folder_form.addRow(f"{key}:", folder_edit)
    class_layout.addLayout(self.classification_folder_form)

    self.classification_help_label = QLabel()
    self.classification_help_label.setObjectName("subtitleLabel")
    self.classification_help_label.setWordWrap(True)
    class_layout.addWidget(self.classification_help_label)

    self.classification_validation_label = QLabel()
    self.classification_validation_label.setObjectName("subtitleLabel")
    self.classification_validation_label.setWordWrap(True)
    self.classification_validation_label.hide()
    class_layout.addWidget(self.classification_validation_label)

    layout.addWidget(self.classification_group)

    # Face detection settings
    self.face_group = QGroupBox("👤 얼굴 감지")
    face_layout = QVBoxLayout(self.face_group)

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

    layout.addWidget(self.face_group)

    # Smart enhancement settings
    self.smart_group = QGroupBox("✨ 스마트 보정")
    smart_layout = QVBoxLayout(self.smart_group)

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

    layout.addWidget(self.smart_group)

    # Notification settings
    self.notification_group = QGroupBox("🔔 알림 설정")
    notif_layout = QVBoxLayout(self.notification_group)

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

    layout.addWidget(self.notification_group)
    layout.addStretch()

    self.tab_widget.addTab(self._make_scrollable_tab(content), "🤖 AI")

def schedule_hint_text(schedule_type: str) -> str:
    normalized = str(schedule_type or "").strip().lower()
    if normalized == "once":
        return t("settings.schedule_hint.once")
    if normalized == "daily":
        return t("settings.schedule_hint.daily")
    if normalized == "hourly":
        return t("settings.schedule_hint.hourly")
    return t("settings.schedule_hint.interval")

def on_schedule_type_changed(self, schedule_type: str):
    """Handle schedule type change to show/hide relevant controls."""
    # Show time field for daily/once, interval for interval mode
    if hasattr(self, "schedule_time_edit"):
        show_time = schedule_type in ("daily", "once")
        self.schedule_time_edit.setEnabled(show_time)
    if hasattr(self, "schedule_interval_spin"):
        show_interval = schedule_type in ("interval", "hourly")
        self.schedule_interval_spin.setEnabled(show_interval)
    if hasattr(self, "schedule_hint_label"):
        self.schedule_hint_label.setText(self._schedule_hint_text(schedule_type))
    self._on_setting_changed()
