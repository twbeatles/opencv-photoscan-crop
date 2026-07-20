from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PyQt6.QtWidgets import QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit, QWidget

from ....i18n.catalog import t


TEXT_BINDINGS = {
    "✨ 후처리 옵션": "settings.section.post",
    "📷 기본": "settings.tab.basic",
    "💾 출력 설정": "settings.section.output",
    "📏 필터": "settings.section.filter",
    "🎨 인터페이스": "settings.section.ui",
    "🔬 알고리즘": "settings.tab.algorithm",
    "💧 워터마크": "settings.section.watermark",
    "📐 리사이즈": "settings.section.resize",
    "🔧 고급 처리": "settings.section.advanced",
    "🔧 처리": "settings.tab.processing",
    "👁️ 폴더 감시 모드": "settings.section.watch",
    "⏰ 스케줄러": "settings.section.scheduler",
    "🖼️ 멀티포토": "settings.section.multi_photo",
    "📂 파일 관리": "settings.section.file_management",
    "⚡ 성능": "settings.section.performance",
    "🌐 언어 설정": "settings.section.language",
    "📂 관리": "settings.tab.management",
    "🤖 AI": "settings.tab.ai",
    "자동 대비 향상 (CLAHE)": "settings.auto_contrast",
    "흑백으로 변환": "settings.grayscale",
    "선명도 향상": "settings.sharpen",
    "강도:": "settings.strength",
    "노이즈 제거": "settings.denoise",
    "파일 형식:": "settings.output_format",
    "JPG/WEBP 품질:": "settings.jpg_quality",
    "PNG 압축 레벨:": "settings.png_compression",
    "타임스탬프 추가": "settings.add_timestamp",
    "메타데이터 보존 (가능한 경우)": "settings.preserve_metadata",
    "원본 백업": "settings.backup_original",
    "작은 이미지 건너뛰기": "settings.skip_small",
    "최소 크기 (px):": "settings.min_size",
    "이미 처리된 파일 건너뛰기": "settings.skip_processed",
    "테마:": "settings.theme",
    "설정 변경 시 자동 미리보기": "settings.auto_preview",
    "검출 영역 오버레이 표시": "settings.contour_overlay",
    "간단 모드 (고급 탭 숨기기)": "settings.simple_mode",
    "최소 임계값:": "settings.canny_min",
    "최대 임계값:": "settings.canny_max",
    "다중 스케일 엣지 검출": "settings.multi_scale",
    "CLAHE 사용:": "settings.use_clahe",
    "클립 제한:": "settings.clahe_clip",
    "그리드 크기:": "settings.clahe_grid",
    "컨투어 스코어링:": "settings.contour_scoring",
    "Harris 코너 검출 사용 (4단계)": "settings.corner_detection",
    "검출 모드:": "settings.detect_mode",
    "검출 디버그 저장 (_debug 폴더)": "settings.debug_detect",
    "디버그 폴더:": "settings.debug_output_dir",
    (
        "💡 조정 가이드:\n"
        "• 흰색/밝은 배경: 기본값 (50-150) 권장\n"
        "• 어두운 배경: 최소값 ↓ (30-120)\n"
        "• 복잡한 무늬: 최대값 ↑ (70-200)"
    ): "settings.algorithm_hint",
    "워터마크 사용": "settings.watermark_enable",
    "텍스트:": "settings.watermark_text",
    "폰트 파일:": "settings.watermark_font",
    "글꼴 크기:": "settings.watermark_font_scale",
    "투명도 (%):": "settings.watermark_opacity",
    "위치:": "settings.watermark_position",
    "그림자 효과": "settings.watermark_shadow",
    "타일 패턴으로 반복": "settings.watermark_tiled",
    "타일 간격:": "settings.watermark_spacing",
    "리사이즈 사용": "settings.resize_enable",
    "모드:": "settings.resize_mode",
    "너비 (px):": "settings.resize_width",
    "높이 (px):": "settings.resize_height",
    "비율 (%):": "settings.resize_percentage",
    "최대 크기:": "settings.resize_max_dimension",
    "원본보다 큰 크기로 확대 허용": "settings.resize_upscale",
    "가로세로 비율 유지": "settings.resize_aspect",
    "자동 기울기 보정": "settings.auto_deskew",
    "자동 색상 보정": "settings.auto_color",
    "보정 방식:": "settings.color_method",
    "자동 원근 교정": "settings.perspective",
    "강화된 노이즈 제거": "settings.enhanced_denoise",
    "오래된 사진 복원": "settings.restore_old",
    "강화된 선명도": "settings.enhanced_sharpen",
    "자동 테두리 제거": "settings.auto_crop_border",
    "Watch Mode 사용": "settings.watch_enable",
    "하위 폴더도 감시": "settings.watch_recursive",
    "감지 지연 (ms):": "settings.watch_delay",
    "최대 대기 시간(s):": "settings.watch_max_wait",
    "스케줄러 사용": "settings.scheduler_enable",
    "스케줄 유형:": "settings.schedule_type",
    "시간:": "settings.schedule_time",
    "간격 (분):": "settings.schedule_interval",
    "멀티포토 감지 사용": "settings.multi_photo_enable",
    "중복 병합 거리(px):": "settings.multi_photo_merge_distance",
    "파일별 하위폴더(<원본파일명>_photos)로 저장": "settings.multi_photo_separate",
    "각 사진 ROI를 단일 탐지로 재정제 (권장)": "settings.multi_photo_refine",
    "장면:": "settings.scene_preset",
    (
        "프리셋을 고르면 Canny·CLAHE·면적 비율 등이 자동 조정됩니다. "
        "세부 값은 아래에서 다시 수정할 수 있습니다."
    ): "settings.scene_preset.hint",
    "하위 폴더 포함 (재귀 처리)": "settings.recursive",
    "파일명 규칙 사용:": "settings.naming_rules",
    "접두사:": "settings.naming_prefix",
    "접미사:": "settings.naming_suffix",
    "일련번호 추가": "settings.naming_counter",
    "날짜 추가": "settings.naming_date",
    "실패 파일 별도 폴더로 이동": "settings.move_failed",
    "이동 대신 복사": "settings.copy_failed",
    "처리 로그 저장:": "settings.enable_log",
    "로그 형식:": "settings.log_format",
    "파일명 충돌 시:": "settings.conflict",
    "정렬 기준:": "settings.sort_by",
    "역순 정렬": "settings.sort_reverse",
    "처리 전 중복 파일 검사": "settings.detect_duplicates",
    "최대 스레드 수:": "settings.max_threads",
    "저사양 모드 (메모리 절약)": "settings.low_mem",
    "언어:": "settings.language",
    "💡 언어 변경은 앱 재시작 후 완전히 적용됩니다.": "settings.language.info",
    "자동 분류 사용": "settings.classification_enable",
    "분류 모델:": "settings.classification_model",
    "분류된 하위 폴더에 저장": "settings.classification_subfolders",
    "얼굴 감지 사용": "settings.face_enable",
    "DNN 얼굴 감지 사용 (초기 모델 다운로드)": "settings.face_use_dnn",
    "얼굴 기준 자동 회전": "settings.face_auto_orient",
    "얼굴 영역 보정 적용": "settings.face_enhance",
    "최소 얼굴 크기 (px):": "settings.face_min_size",
    "스마트 보정 사용": "settings.smart_enable",
    "노출 자동 조정": "settings.smart_exposure",
    "색상 균형 자동 조정": "settings.smart_color_balance",
    "보정 강도:": "settings.smart_strength",
    "시스템 알림 사용": "settings.notification_enable",
    "알림 소리 재생": "settings.notification_sound",
    "오류 시에만 알림": "settings.notification_error_only",
}

TITLE_BINDINGS = {
    "장면 프리셋 (빠른 설정)": "settings.scene_preset.group",
    "🔍 Canny 엣지 검출": "settings.canny",
    "🎛️ CLAHE 대비 향상": "settings.clahe",
    "➰ 윤곽선 처리": "settings.contour",
    "검출 모드 / 디버그": "settings.detect_mode_group",
    "📊 이미지 자동 분류": "settings.section.classification",
    "👤 얼굴 감지": "settings.section.face",
    "✨ 스마트 보정": "settings.section.smart",
    "🔔 알림 설정": "settings.section.notification",
}

PLACEHOLDER_BINDINGS = {
    "예: © 2026 My Studio": "settings.watermark_text.placeholder",
    "예: scan_": "settings.naming_prefix.placeholder",
    "예: _cropped": "settings.naming_suffix.placeholder",
    "HH:MM (예: 09:00)": "settings.schedule_time.placeholder",
    (
        r"(선택) 디버그 폴더. 비우면 출력폴더/_debug 또는 "
        r"%TEMP%/PhotoCropper/_debug"
    ): "settings.debug_output_dir.placeholder",
}

TOOLTIP_BINDINGS = {
    (
        "켜면 알고리즘/처리/관리/AI 탭을 숨기고 기본 작업에 집중합니다. "
        "장면 프리셋은 워크벤치 상단에서 사용할 수 있습니다."
    ): "settings.simple_mode.tooltip",
    "CLAHE 알고리즘으로 이미지 대비를 자동 향상합니다": "settings.auto_contrast.tooltip",
    "이미지 노이즈를 줄입니다 (처리 시간 증가)": "settings.denoise.tooltip",
    (
        "EXIF/ICC 메타데이터를 best-effort로 복사합니다. "
        "실패해도 저장은 계속됩니다."
    ): "settings.preserve_metadata.tooltip",
    "처리 전 원본 파일을 backup 폴더에 복사합니다": "settings.backup_original.tooltip",
    "파일명에 '_cropped'가 포함된 파일 제외": "settings.skip_processed.tooltip",
    "여러 스케일에서 엣지를 검출하여 정확도 향상": "settings.multi_scale.tooltip",
    "다른 방법 실패 시 코너 검출로 시도": "settings.corner_detection.tooltip",
    (
        "엣지/마스크/후보 오버레이 등 중간 결과를 저장해서 "
        "실패 원인 분석에 사용합니다."
    ): "settings.debug_detect.tooltip",
    "Hough 변환으로 기울기를 감지하고 자동 교정": "settings.auto_deskew.tooltip",
    "Gray World 알고리즘으로 화이트밸런스 보정": "settings.auto_color.tooltip",
    "감지된 사각형을 기준으로 원근 왜곡 교정": "settings.perspective.tooltip",
    "고급 비지역 평균 필터 적용": "settings.enhanced_denoise.tooltip",
    "색바램, 얼룩 보정 및 대비 향상": "settings.restore_old.tooltip",
    "스캔 테두리 자동 감지 및 제거": "settings.auto_crop_border.tooltip",
    "새 이미지가 추가되면 자동으로 처리": "settings.watch_enable.tooltip",
    "파일 쓰기 완료를 기다리는 시간": "settings.watch_delay.tooltip",
    "파일 준비 대기 최대 시간": "settings.watch_max_wait.tooltip",
    "예약된 시간에 자동으로 배치 처리": "settings.scheduler_enable.tooltip",
    "once는 날짜 지정 없이 다음 도래 HH:MM에 한 번만 실행됩니다.": "settings.schedule_type.tooltip",
    (
        "daily/once에서 사용합니다. "
        "once는 날짜 없는 다음 도래 시각 1회 실행입니다."
    ): "settings.schedule_time.tooltip",
    "한 장의 스캔 이미지에서 여러 사진을 분리 저장합니다.": "settings.multi_photo_enable.tooltip",
    "값이 클수록 가까운 검출 결과를 같은 사진으로 병합합니다.": "settings.multi_photo_merge_distance.tooltip",
    "멀티포토로 찾은 영역마다 단일 사진 탐지를 한 번 더 돌려 경계를 다듬습니다.": "settings.multi_photo_refine.tooltip",
    "선택한 폴더와 모든 하위 폴더의 이미지를 처리": "settings.recursive.tooltip",
    "동시에 처리할 이미지 수 (CPU 코어 수 권장)": "settings.max_threads.tooltip",
    "처리 속도가 느려질 수 있지만 메모리 사용량을 줄입니다.": "settings.low_mem.tooltip",
    "이미지를 유형별로 자동 분류하여 저장": "settings.classification_enable.tooltip",
    "인물 사진에서 얼굴을 감지하여 최적화": "settings.face_enable.tooltip",
    (
        "활성화 시 더 정확한 얼굴 감지를 시도합니다. "
        "네트워크 실패 시 기본(Haar) 방식으로 자동 전환됩니다."
    ): "settings.face_use_dnn.tooltip",
    "이미지 특성에 맞는 자동 보정 적용": "settings.smart_enable.tooltip",
    "배치 처리 완료 시 시스템 알림 표시": "settings.notification_enable.tooltip",
}

COMBO_ITEM_BINDINGS = {
    "conflict_combo": (
        "settings.conflict.rename",
        "settings.conflict.overwrite",
        "settings.conflict.skip",
    ),
    "sort_by_combo": (
        "settings.sort.name",
        "settings.sort.date",
        "settings.sort.size",
    ),
}

COMBO_LITERAL_BINDINGS = {
    "자동 이름 변경 (숫자 추가)": "settings.conflict.rename",
    "덮어쓰기": "settings.conflict.overwrite",
    "건너뛰기": "settings.conflict.skip",
    "이름순": "settings.sort.name",
    "날짜순": "settings.sort.date",
    "크기순": "settings.sort.size",
}

ALLOWED_SETTINGS_KOREAN_LITERALS = {"한국어"}

_TEXT_KEY_PROPERTY = "_photo_cropper_i18n_text_key"
_TITLE_KEY_PROPERTY = "_photo_cropper_i18n_title_key"
_PLACEHOLDER_KEY_PROPERTY = "_photo_cropper_i18n_placeholder_key"
_TOOLTIP_KEY_PROPERTY = "_photo_cropper_i18n_tooltip_key"


def all_settings_i18n_binding_keys() -> set[str]:
    keys = set(TEXT_BINDINGS.values())
    keys.update(TITLE_BINDINGS.values())
    keys.update(PLACEHOLDER_BINDINGS.values())
    keys.update(TOOLTIP_BINDINGS.values())
    for combo_keys in COMBO_ITEM_BINDINGS.values():
        keys.update(combo_keys)
    return keys


def all_bound_settings_literals() -> set[str]:
    literals = set(TEXT_BINDINGS)
    literals.update(TITLE_BINDINGS)
    literals.update(PLACEHOLDER_BINDINGS)
    literals.update(TOOLTIP_BINDINGS)
    literals.update(COMBO_LITERAL_BINDINGS)
    literals.update(ALLOWED_SETTINGS_KOREAN_LITERALS)
    return literals


def _resolve_binding(
    widget: QWidget,
    property_name: str,
    current_value: str,
    bindings: dict[str, str],
) -> str:
    existing = widget.property(property_name)
    if isinstance(existing, str) and existing:
        return existing
    key = bindings.get(current_value)
    if key:
        widget.setProperty(property_name, key)
    return key or ""


def _set_combo_items(combo: Any, keys: Iterable[str]) -> None:
    if not isinstance(combo, QComboBox):
        return
    current_index = combo.currentIndex()
    was_blocked = combo.blockSignals(True)
    try:
        for index, key in enumerate(keys):
            if index >= combo.count():
                break
            combo.setItemText(index, t(key))
        if 0 <= current_index < combo.count():
            combo.setCurrentIndex(current_index)
    finally:
        combo.blockSignals(was_blocked)


def apply_settings_i18n_bindings(root: QWidget) -> None:
    """Bind legacy settings-tab literals to catalog keys and reapply translations."""
    for label in root.findChildren(QLabel):
        key = _resolve_binding(label, _TEXT_KEY_PROPERTY, label.text(), TEXT_BINDINGS)
        if key:
            label.setText(t(key))

    for button in root.findChildren(QAbstractButton):
        key = _resolve_binding(button, _TEXT_KEY_PROPERTY, button.text(), TEXT_BINDINGS)
        if key:
            button.setText(t(key))

    for group in root.findChildren(QGroupBox):
        key = _resolve_binding(group, _TITLE_KEY_PROPERTY, group.title(), TITLE_BINDINGS)
        if key:
            group.setTitle(t(key))

    for line_edit in root.findChildren(QLineEdit):
        key = _resolve_binding(
            line_edit,
            _PLACEHOLDER_KEY_PROPERTY,
            line_edit.placeholderText(),
            PLACEHOLDER_BINDINGS,
        )
        if key:
            line_edit.setPlaceholderText(t(key))

    for widget in root.findChildren(QWidget):
        key = _resolve_binding(
            widget,
            _TOOLTIP_KEY_PROPERTY,
            widget.toolTip(),
            TOOLTIP_BINDINGS,
        )
        if key:
            widget.setToolTip(t(key))

    for attribute_name, keys in COMBO_ITEM_BINDINGS.items():
        _set_combo_items(getattr(root, attribute_name, None), keys)
