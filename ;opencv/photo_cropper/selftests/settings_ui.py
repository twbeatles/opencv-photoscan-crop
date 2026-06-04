#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Settings Ui self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_classification_settings_custom_alias_normalizes_to_advanced() -> None:
    from ..core.settings_model import AppSettings, ClassificationSettings

    classification = ClassificationSettings(model="custom")
    assert classification.model == "advanced"

    loaded = AppSettings.from_dict({"classification": {"model": "custom"}})
    assert loaded.classification.model == "advanced"

def _test_settings_forward_compat() -> None:
    from ..core.settings_model import AppSettings

    data = {
        "algorithm": {"canny_min": 12, "canny_max": 200, "new_field_future": 123},
        "watermark": {"enabled": True, "text": "짤 2026", "unknown": "x"},
        "unknown_root": {"a": 1},
    }
    s = AppSettings.from_dict(data)
    assert s.algorithm.canny_min == 12
    assert s.algorithm.canny_max == 200
    assert s.watermark.enabled is True
    assert s.watermark.text == "짤 2026"

def _test_settings_panel_performance_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for settings panel test: {e}")
        return

    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    panel = SettingsPanel(AppSettings())
    panel.max_threads_spin.setValue(7)
    panel.low_mem_check.setChecked(True)

    s1 = panel._build_settings()
    assert s1.performance.thread_count == 7
    assert s1.performance.enable_multithreading is True
    assert s1.performance.max_image_size_mb == 50
    assert s1.performance.downscale_large_images is True
    assert abs(s1.performance.downscale_threshold_mp - 24.0) < 1e-6

    panel.settings = s1
    s2 = panel._build_settings()
    assert s2.performance.thread_count == 7
    assert s2.performance.max_image_size_mb == 50
    assert abs(s2.performance.downscale_threshold_mp - 24.0) < 1e-6

    panel.max_threads_spin.setValue(2)
    panel.low_mem_check.setChecked(False)
    s3 = panel._build_settings()
    assert s3.performance.thread_count == 2
    assert s3.performance.max_image_size_mb == 100
    assert abs(s3.performance.downscale_threshold_mp - 50.0) < 1e-6

    panel.deleteLater()
    if owned_app:
        app.quit()

def _test_settings_panel_ai_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for AI roundtrip test: {e}")
        return

    from ..core.settings_model import AppSettings
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    s = AppSettings()
    s.classification.enabled = True
    s.classification.model = "advanced"
    s.face_detection.enabled = True
    s.face_detection.use_dnn = True
    s.face_detection.min_face_size = 42
    s.smart_enhancement.enabled = True
    s.smart_enhancement.adjust_exposure = False
    s.smart_enhancement.adjust_color_balance = True
    s.smart_enhancement.strength = 73

    panel = SettingsPanel(s)
    panel._load_settings(s)
    out = panel._build_settings()

    assert out.classification.model == "advanced"
    assert out.face_detection.use_dnn is True
    assert out.face_detection.min_face_size == 42
    assert out.smart_enhancement.adjust_exposure is False
    assert out.smart_enhancement.adjust_color_balance is True
    assert out.smart_enhancement.strength == 73

    panel.deleteLater()
    if owned_app:
        app.quit()

def _test_settings_panel_classification_folder_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for classification folder roundtrip test: {e}")
        return

    from ..core.settings_model import AppSettings
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    settings = AppSettings()
    settings.classification.category_folders["portrait"] = "프로필"
    settings.classification.category_folders["other"] = "기타커스텀"

    panel = SettingsPanel(settings)
    panel._load_settings(settings)
    assert panel.classification_folder_inputs["portrait"].text() == "프로필"
    assert panel.classification_folder_inputs["other"].text() == "기타커스텀"

    panel.classification_folder_inputs["portrait"].setText("인물새폴더")
    panel.classification_folder_inputs["other"].setText("")
    out = panel._build_settings()
    assert out.classification.category_folders["portrait"] == "인물새폴더"
    assert out.classification.category_folders["other"] == ""

    panel.deleteLater()
    if owned_app:
        app.quit()

def _test_classification_folder_default_sentinel_migration() -> None:
    from ..core.settings_model import AppSettings
    from ..utils.path_validation import resolve_category_folder_map

    settings = AppSettings.from_dict(
        {
            "ui": {"language": "en"},
            "classification": {
                "category_folders": {
                    "portrait": "인물",
                    "landscape": "풍경",
                    "document": "문서",
                    "blackwhite": "흑백",
                    "other": "기타",
                }
            },
        }
    )

    assert settings.classification.category_folders["portrait"] == ""
    resolved = resolve_category_folder_map(
        settings.classification.category_folders,
        language=settings.ui.language,
    )
    assert resolved["portrait"] == "Portrait"
    assert resolved["other"] == "Other"

def _test_settings_path_validation_blocks_invalid_segments() -> None:
    from ..core.settings_model import AppSettings
    from ..utils.path_validation import validate_settings_path_segments

    settings = AppSettings()
    settings.file_management.naming_prefix = "scan/2026"
    settings.file_management.failed_folder_name = ".."
    settings.classification.category_folders["portrait"] = "CON"

    issues = validate_settings_path_segments(settings)
    fields = {issue.field for issue in issues}
    assert "file_management.naming_prefix" in fields
    assert "file_management.failed_folder_name" in fields
    assert "classification.category_folders.portrait" in fields

def _test_settings_panel_legacy_custom_alias_and_schedule_once_hint() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for settings alias/hint test: {e}")
        return

    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    settings = AppSettings.from_dict({"classification": {"model": "custom"}})
    panel = SettingsPanel(settings)
    panel._load_settings(settings)

    model_options = [
        panel.classification_model_combo.itemText(i)
        for i in range(panel.classification_model_combo.count())
    ]
    assert model_options == ["basic", "advanced"]
    assert panel.classification_model_combo.currentText() == "advanced"

    panel.schedule_type_combo.setCurrentText("once")
    assert panel.schedule_hint_label.text() == t("settings.schedule_hint.once")

    out = panel._build_settings()
    assert out.classification.model == "advanced"

    panel.deleteLater()
    if owned_app:
        app.quit()

def _test_i18n_catalog_placeholder_consistency() -> None:
    import string

    from ..i18n.catalog.manager import get_translator

    formatter = string.Formatter()

    def fields(text: str) -> set[str]:
        return {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _literal, field_name, _format_spec, _conversion in formatter.parse(text)
            if field_name
        }

    translator = get_translator()
    translations = translator._translations
    base_keys = set(translations["en"].keys())
    for language, mapping in translations.items():
        assert set(mapping.keys()) == base_keys, language
        for key in base_keys:
            assert fields(mapping[key]) == fields(translations["en"][key]), (language, key)

def _test_settings_i18n_literal_binding_coverage() -> None:
    import ast
    import re
    from pathlib import Path

    from ..i18n.catalog.manager import get_translator
    from ..ui.widgets.settings.i18n_bindings import (
        all_bound_settings_literals,
        all_settings_i18n_binding_keys,
    )

    translator = get_translator()
    base_keys = set(translator._translations["en"].keys())
    missing_keys = sorted(all_settings_i18n_binding_keys() - base_keys)
    assert not missing_keys, missing_keys

    bound_literals = all_bound_settings_literals()
    korean_literal_re = re.compile(r"[가-힣]")
    settings_dir = Path(__file__).resolve().parents[1] / "ui" / "widgets" / "settings"
    source_files = [settings_dir / "panel.py", *sorted(settings_dir.glob("tab_*.py"))]
    uncovered: list[tuple[str, int, str]] = []
    for source_path in source_files:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value
            if not korean_literal_re.search(value):
                continue
            if value not in bound_literals:
                uncovered.append((source_path.name, int(getattr(node, "lineno", 0)), value))
    assert not uncovered, uncovered

def _test_settings_panel_algorithm_tuning_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for algorithm tuning roundtrip test: {e}")
        return

    from ..core.settings_model import AppSettings
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    s = AppSettings()
    s.algorithm.min_area_ratio = 0.14
    s.algorithm.max_area_ratio = 0.92
    s.algorithm.bg_mask_delta = 44.0
    s.algorithm.adaptive_block_size = 19
    s.algorithm.adaptive_c = 2.5

    panel = SettingsPanel(s)
    panel._load_settings(s)
    out = panel._build_settings()

    assert abs(float(out.algorithm.min_area_ratio) - 0.14) < 1e-6
    assert abs(float(out.algorithm.max_area_ratio) - 0.92) < 1e-6
    assert abs(float(out.algorithm.bg_mask_delta) - 44.0) < 1e-6
    assert int(out.algorithm.adaptive_block_size) == 19
    assert abs(float(out.algorithm.adaptive_c) - 2.5) < 1e-6

    panel.deleteLater()
    if owned_app:
        app.quit()

__all__ = [
    "_test_classification_settings_custom_alias_normalizes_to_advanced",
    "_test_settings_forward_compat",
    "_test_settings_panel_performance_roundtrip",
    "_test_settings_panel_ai_roundtrip",
    "_test_settings_panel_classification_folder_roundtrip",
    "_test_classification_folder_default_sentinel_migration",
    "_test_settings_path_validation_blocks_invalid_segments",
    "_test_settings_panel_legacy_custom_alias_and_schedule_once_hint",
    "_test_i18n_catalog_placeholder_consistency",
    "_test_settings_i18n_literal_binding_coverage",
    "_test_settings_panel_algorithm_tuning_roundtrip",
]
