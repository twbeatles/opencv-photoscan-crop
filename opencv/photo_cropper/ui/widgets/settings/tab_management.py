from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..collapsible_section import CollapsibleSection
from ..toggle_switch import ModernToggleSwitch
from .controls import NoScrollComboBox, NoScrollDoubleSpinBox, NoScrollSpinBox

def create_management_tab(self):
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
    self.schedule_type_combo.setToolTip(
        "once는 날짜 지정 없이 다음 도래 HH:MM에 한 번만 실행됩니다."
    )
    self.schedule_type_combo.currentTextChanged.connect(self._on_schedule_type_changed)
    sched_form.addRow("스케줄 유형:", self.schedule_type_combo)

    self.schedule_time_edit = QLineEdit()
    self.schedule_time_edit.setPlaceholderText("HH:MM (예: 09:00)")
    self.schedule_time_edit.setText("00:00")
    self.schedule_time_edit.setToolTip(
        "daily/once에서 사용합니다. once는 날짜 없는 다음 도래 시각 1회 실행입니다."
    )
    self.schedule_time_edit.textChanged.connect(self._on_setting_changed)
    sched_form.addRow("시간:", self.schedule_time_edit)

    self.schedule_interval_spin = NoScrollSpinBox()
    self.schedule_interval_spin.setRange(5, 1440)
    self.schedule_interval_spin.setValue(60)
    self.schedule_interval_spin.valueChanged.connect(self._on_setting_changed)
    sched_form.addRow("간격 (분):", self.schedule_interval_spin)
    sched_layout.addLayout(sched_form)

    self.schedule_hint_label = QLabel()
    self.schedule_hint_label.setObjectName("subtitleLabel")
    self.schedule_hint_label.setWordWrap(True)
    sched_layout.addWidget(self.schedule_hint_label)

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

    self.multi_photo_refine_check = QCheckBox(
        "각 사진 ROI를 단일 탐지로 재정제 (권장)"
    )
    self.multi_photo_refine_check.setToolTip(
        "멀티포토로 찾은 영역마다 단일 사진 탐지를 한 번 더 돌려 경계를 다듬습니다."
    )
    self.multi_photo_refine_check.setChecked(True)
    self.multi_photo_refine_check.stateChanged.connect(self._on_setting_changed)
    mp_layout.addWidget(self.multi_photo_refine_check)

    mp_section.add_widget(mp_group)
    layout.addWidget(mp_section)

    # === File management section ===
    self.file_management_section = CollapsibleSection("📂 파일 관리", initially_expanded=False)
    fm_group = QWidget()
    fm_layout = QVBoxLayout(fm_group)
    fm_layout.setContentsMargins(0, 0, 0, 0)

    self.recursive_check = QCheckBox("하위 폴더 포함 (재귀 처리)")
    self.recursive_check.setToolTip("선택한 폴더와 모든 하위 폴더의 이미지를 처리")
    self.recursive_check.stateChanged.connect(self._on_setting_changed)
    fm_layout.addWidget(self.recursive_check)

    self.file_management_form = QFormLayout()
    self.use_naming_rules_check = QCheckBox()
    self.use_naming_rules_check.stateChanged.connect(self._on_setting_changed)
    self.file_management_form.addRow("파일명 규칙 사용:", self.use_naming_rules_check)

    self.naming_prefix_edit = QLineEdit()
    self.naming_prefix_edit.setPlaceholderText("예: scan_")
    self.naming_prefix_edit.textChanged.connect(self._on_setting_changed)
    self.file_management_form.addRow("접두사:", self.naming_prefix_edit)

    self.naming_suffix_edit = QLineEdit()
    self.naming_suffix_edit.setPlaceholderText("예: _cropped")
    self.naming_suffix_edit.setText("_cropped")
    self.naming_suffix_edit.textChanged.connect(self._on_setting_changed)
    self.file_management_form.addRow("접미사:", self.naming_suffix_edit)

    self.naming_counter_check = QCheckBox("일련번호 추가")
    self.naming_counter_check.stateChanged.connect(self._on_setting_changed)
    self.file_management_form.addRow(self.naming_counter_check)

    self.naming_date_check = QCheckBox("날짜 추가")
    self.naming_date_check.stateChanged.connect(self._on_setting_changed)
    self.file_management_form.addRow(self.naming_date_check)
    fm_layout.addLayout(self.file_management_form)

    self.naming_validation_label = QLabel()
    self.naming_validation_label.setObjectName("subtitleLabel")
    self.naming_validation_label.setWordWrap(True)
    self.naming_validation_label.hide()
    fm_layout.addWidget(self.naming_validation_label)

    self.move_failed_check = QCheckBox("실패 파일 별도 폴더로 이동")
    self.move_failed_check.stateChanged.connect(self._on_setting_changed)
    fm_layout.addWidget(self.move_failed_check)

    self.copy_failed_check = QCheckBox("이동 대신 복사")
    self.copy_failed_check.stateChanged.connect(self._on_setting_changed)
    fm_layout.addWidget(self.copy_failed_check)

    self.log_form = QFormLayout()
    self.enable_log_check = QCheckBox()
    self.enable_log_check.setChecked(True)
    self.enable_log_check.stateChanged.connect(self._on_setting_changed)
    self.log_form.addRow("처리 로그 저장:", self.enable_log_check)

    self.log_format_combo = NoScrollComboBox()
    self.log_format_combo.addItems(["json", "csv"])
    self.log_format_combo.currentTextChanged.connect(self._on_setting_changed)
    self.log_form.addRow("로그 형식:", self.log_format_combo)
    fm_layout.addLayout(self.log_form)

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

    self.file_management_section.add_widget(fm_group)
    layout.addWidget(self.file_management_section)

    # === Performance section ===
    self.performance_section = CollapsibleSection("⚡ 성능", initially_expanded=False)
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

    self.performance_section.add_widget(perf_group)
    layout.addWidget(self.performance_section)

    # === Language section ===
    self.language_section = CollapsibleSection("🌐 언어 설정", initially_expanded=False)
    lang_group = QWidget()
    self.language_form = QFormLayout(lang_group)
    self.language_form.setContentsMargins(0, 0, 0, 0)

    self.language_combo = NoScrollComboBox()
    self.language_combo.addItem("한국어", "ko")
    self.language_combo.addItem("English", "en")
    self.language_combo.addItem("日本語", "ja")
    self.language_combo.addItem("简体中文", "zh")
    self.language_combo.addItem("Español", "es")
    self.language_combo.currentIndexChanged.connect(self._on_language_changed)
    self.language_form.addRow("언어:", self.language_combo)

    self.language_info_label = QLabel("💡 언어 변경은 앱 재시작 후 완전히 적용됩니다.")
    self.language_info_label.setWordWrap(True)
    self.language_info_label.setObjectName("subtitleLabel")
    self.language_form.addRow(self.language_info_label)

    self.language_section.add_widget(lang_group)
    layout.addWidget(self.language_section)

    layout.addStretch()
    self.tab_widget.addTab(self._make_scrollable_tab(content), "📂 관리")
