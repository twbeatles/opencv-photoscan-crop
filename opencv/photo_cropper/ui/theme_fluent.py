#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fluent theme bootstrap for the Photo Cropper desktop UI (PyQt6).

qfluentwidgets owns dark/light rendering; this module only selects the
theme and keeps a few native Qt widgets readable in dark mode.
Port of the ktrain ``gui/theme.py`` pattern to the PyQt6 binding.
"""

from __future__ import annotations

import logging
from typing import Any

from .fluent import FLUENT_AVAILABLE

logger = logging.getLogger(__name__)

THEME_AUTO = "auto"
THEME_DARK = "dark"
THEME_LIGHT = "light"
AVAILABLE_THEMES = (THEME_AUTO, THEME_DARK, THEME_LIGHT)

_POLL_MS = 3000

_FluentTheme: Any = None
_is_dark_theme: Any = None
_set_theme: Any = None
_set_theme_color: Any = None
if FLUENT_AVAILABLE:
    from qfluentwidgets import Theme as _FluentTheme
    from qfluentwidgets import isDarkTheme as _is_dark_theme
    from qfluentwidgets import setTheme as _set_theme
    from qfluentwidgets import setThemeColor as _set_theme_color


def normalize_theme_name(theme_name: str) -> str:
    """Normalize a persisted theme name; raise ValueError when unknown."""
    normalized = str(theme_name or "").strip().lower()
    if normalized in ("system", "follow", "follow_system"):
        return THEME_AUTO
    if normalized not in AVAILABLE_THEMES:
        raise ValueError(f"Unknown theme: {theme_name!r}")
    return normalized


def setup_app_theme(app) -> None:
    """Call once right after QApplication creation, before MainWindow."""
    if not FLUENT_AVAILABLE:
        logger.debug("qfluentwidgets unavailable; skipping Fluent theme setup")
        return
    _set_theme(_FluentTheme.AUTO)
    try:
        from .design_tokens import BRAND_ACCENT

        _set_theme_color(BRAND_ACCENT)
    except Exception:
        logger.debug("Fluent accent color unavailable", exc_info=True)
    sync_system_theme()
    _install_theme_watcher(app)


def sync_system_theme() -> None:
    """Reflect the OS dark/light setting in qfluentwidgets."""
    if not FLUENT_AVAILABLE:
        return
    try:
        import darkdetect

        system = darkdetect.theme()
    except Exception:
        return
    if system == "Dark":
        _set_theme(_FluentTheme.DARK)
    elif system == "Light":
        _set_theme(_FluentTheme.LIGHT)


def _install_theme_watcher(app) -> None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QGuiApplication

    try:
        hints = QGuiApplication.styleHints()
        color_changed = getattr(hints, "colorSchemeChanged", None)
        if callable(color_changed) and hasattr(color_changed, "connect"):
            color_changed.connect(lambda _scheme: QTimer.singleShot(0, sync_system_theme))
    except Exception:
        logger.debug("Qt color-scheme watcher unavailable", exc_info=True)
    try:
        timer = QTimer(app)
        timer.timeout.connect(sync_system_theme)
        timer.start(_POLL_MS)
    except Exception:
        logger.debug("Theme polling watcher unavailable", exc_info=True)


def apply_fluent_theme(theme_name: str) -> str:
    """Apply a persisted theme choice. ``auto`` follows the OS setting."""
    normalized = normalize_theme_name(theme_name)
    if not FLUENT_AVAILABLE:
        return normalized
    if normalized == THEME_AUTO:
        _set_theme(_FluentTheme.AUTO)
        sync_system_theme()
    elif normalized == THEME_DARK:
        _set_theme(_FluentTheme.DARK)
    else:
        _set_theme(_FluentTheme.LIGHT)
    return normalized


def is_dark() -> bool:
    """Current effective dark mode; False when Fluent is unavailable."""
    if not FLUENT_AVAILABLE:
        return False
    try:
        return bool(_is_dark_theme())
    except Exception:
        return False


def configure_fluent_window(window) -> None:
    """Reduce Mica/background artifacts on Fluent-style windows."""
    set_mica = getattr(window, "setMicaEffectEnabled", None)
    if callable(set_mica):
        try:
            set_mica(False)
        except Exception:
            logger.debug("setMicaEffectEnabled failed", exc_info=True)


__all__ = [
    "THEME_AUTO",
    "THEME_DARK",
    "THEME_LIGHT",
    "AVAILABLE_THEMES",
    "FLUENT_AVAILABLE",
    "normalize_theme_name",
    "setup_app_theme",
    "sync_system_theme",
    "apply_fluent_theme",
    "is_dark",
    "configure_fluent_window",
]
