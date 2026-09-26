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
