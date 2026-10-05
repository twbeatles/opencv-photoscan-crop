"""Fluent redesign foundation tests (no QApplication required)."""

from __future__ import annotations

import pytest

from photo_cropper.ui import design_tokens as tokens
from photo_cropper.ui import fluent
from photo_cropper.ui import theme_fluent


def test_spacing_scale_is_ordered() -> None:
    assert [
        tokens.SPACE_XXS,
        tokens.SPACE_XS,
        tokens.SPACE_SM,
        tokens.SPACE_MD,
        tokens.SPACE_LG,
        tokens.SPACE_XL,
    ] == [4, 8, 12, 16, 24, 32]
    assert tokens.PAGE_MARGIN == 24
    assert tokens.SECTION_GAP == 24
    assert tokens.CARD_RADIUS == 8


def test_preferred_window_size_clamps_to_screen() -> None:
    assert tokens.preferred_window_size(2000, 1400) == (1100, 800)
    assert tokens.preferred_window_size(800, 600) == (760, 560)
    assert tokens.preferred_window_size(300, 300) == (640, 560)


def test_status_badge_has_no_hardcoded_accent() -> None:
    qss = tokens.status_badge_qss()
    assert "border-radius" in qss
    assert "#58a6ff" not in qss
    assert "rgba(9, 105, 218" not in qss


def test_normalize_theme_name() -> None:
    assert theme_fluent.normalize_theme_name("Dark") == "dark"
    assert theme_fluent.normalize_theme_name("LIGHT") == "light"
    assert theme_fluent.normalize_theme_name("system") == "auto"
    assert theme_fluent.normalize_theme_name("auto") == "auto"
    with pytest.raises(ValueError):
        theme_fluent.normalize_theme_name("glassmorphism")


def test_apply_fluent_theme_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        theme_fluent.apply_fluent_theme("neon")


def test_notify_without_parent_never_raises() -> None:
    assert fluent.notify("success", "done", parent=None) is False
    assert fluent.notify("bogus-kind", "done", parent=None) is False
    assert fluent.notify("error", "", parent=None) is False


def test_confirm_qt_uses_fluent_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fluent, "confirm", lambda *args, **kwargs: True)
    assert fluent.confirm_qt(None, "t", "c") is True
    monkeypatch.setattr(fluent, "confirm", lambda *args, **kwargs: False)
    assert fluent.confirm_qt(None, "t", "c") is False


def test_nav_icons_cover_all_shell_pages() -> None:
    assert set(fluent.NAV_ICONS) == {
        "library",
        "workbench",
        "review",
        "duplicates",
        "jobs",
        "collections",
        "recipes",
        "settings",
    }


def test_toast_manager_without_parent_is_noop() -> None:
    from photo_cropper.ui.widgets.toast_notification import ToastManager

    ToastManager._parent = None
    assert ToastManager.show("hello") is None


def test_legacy_theme_fallback_still_available() -> None:
    from photo_cropper.ui.styles.themes import get_available_themes, get_theme

    assert set(get_available_themes()) == {"dark", "light"}
    assert "QMainWindow" in get_theme("dark")


def test_workbench_is_first_shell_page() -> None:
    from photo_cropper.ui.main.builders import PAGE_ORDER

    assert PAGE_ORDER[0] == "workbench"
    assert set(PAGE_ORDER) == set(fluent.NAV_ICONS)


def test_status_badge_kinds() -> None:
    assert tokens.STATUS_SUCCESS in tokens.status_badge_qss("success")
    assert tokens.STATUS_SUCCESS not in tokens.status_badge_qss()


def test_scene_preset_picker_leads_with_keep_current() -> None:
    from photo_cropper.core.scene_presets import SCENE_PRESET_META
    from photo_cropper.i18n.catalog import t
    from photo_cropper.ui.widgets.settings.controls import scene_preset_ids

    ids = scene_preset_ids()
    assert ids[0] == "custom"
    assert set(ids) == set(SCENE_PRESET_META)
    for sid in ids:
        assert t(f"scene.{sid}") != f"scene.{sid}"


def test_theme_choices_cover_every_theme() -> None:
    from photo_cropper.ui.widgets.settings.controls import THEME_CHOICES

    assert set(THEME_CHOICES) == set(theme_fluent.AVAILABLE_THEMES)


def test_explicit_theme_is_not_overridden_by_os_watcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(theme_fluent, "FLUENT_AVAILABLE", True)
    monkeypatch.setattr(theme_fluent, "_set_theme", calls.append)
    monkeypatch.setattr(theme_fluent, "_active_mode", theme_fluent.THEME_DARK)
    theme_fluent.sync_system_theme()
    assert calls == []


def test_image_list_reload_keeps_current_selection(tmp_path) -> None:
    from types import SimpleNamespace

    import cv2
    import numpy as np

    from photo_cropper.core.settings_model import AppSettings
    from photo_cropper.ui.main.actions import NavigationActions

    paths = []
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        path = tmp_path / name
        cv2.imwrite(str(path), np.zeros((8, 8, 3), np.uint8))
        paths.append(str(path))

    state = SimpleNamespace(
        settings=AppSettings(),
        image_list=[],
        current_image_index=-1,
        current_image_path=paths[1],
        review_list_active=True,
    )
    refs = SimpleNamespace(
        input_path_edit=SimpleNamespace(text=lambda: str(tmp_path)),
        output_path_edit=None,
        file_count_badge=None,
    )
    actions = NavigationActions(state, refs)  # type: ignore[arg-type]
    actions.update_image_list()

    assert len(state.image_list) == 3
    assert state.current_image_path == paths[1]
    assert state.current_image_index == state.image_list.index(paths[1])
    assert state.review_list_active is False
