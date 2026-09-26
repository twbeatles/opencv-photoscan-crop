#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fluent component bridge with plain-Qt fallbacks.

All helpers work whether or not a PyQt6-backed ``qfluentwidgets`` is
installed, so the app and its tests never depend on the Fluent package.
A PySide6-backed edition (same import namespace, incompatible Qt objects)
is treated as unavailable: the project binding is PyQt6 and bindings must
never be mixed (DESKTOP_UI_DESIGN_RULES Sec 1.1).
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _load_fluent_widgets() -> Optional[tuple[Any, ...]]:
    """Import qfluentwidgets, or return None when unusable in this app."""
    try:
        from qfluentwidgets import FluentIcon as FIF
        from qfluentwidgets import InfoBar, InfoBarPosition, MessageBox
        from qfluentwidgets import PrimaryPushButton, PushButton
    except Exception:
        logger.debug("qfluentwidgets unavailable", exc_info=True)
        return None
    try:
        import PyQt6.QtCore  # noqa: F401  (project binding must exist)
    except Exception:
        return None
    if "PySide6.QtCore" in sys.modules:
        logger.debug("qfluentwidgets PySide6 edition ignored in a PyQt6 app")
        return None
    if "PyQt6.QtCore" not in sys.modules:  # pragma: no cover - defensive
        return None
    return (FIF, InfoBar, InfoBarPosition, MessageBox, PrimaryPushButton, PushButton)


_FIF: Any = None
_InfoBar: Any = None
_InfoBarPosition: Any = None
_MessageBox: Any = None
_PrimaryPushButton: Any = None
_PushButton: Any = None

_loaded = _load_fluent_widgets()
if _loaded is not None:
    (_FIF, _InfoBar, _InfoBarPosition, _MessageBox, _PrimaryPushButton, _PushButton) = _loaded
    FLUENT_AVAILABLE = True
else:
    FLUENT_AVAILABLE = False

NOTIFY_KINDS = ("success", "error", "warning", "info")

# Duration defaults (ms) — errors stay longer than confirmations.
NOTIFY_DURATION = {"success": 3000, "info": 3000, "warning": 4500, "error": 6000}


def notify(
    kind: str,
    message: str,
    *,
    title: str = "",
    parent=None,
    duration: Optional[int] = None,
) -> bool:
    """Show a non-blocking InfoBar notification.

    Returns True when the Fluent InfoBar was used, False when the caller
    should fall back (legacy toast). Never raises for UI reasons.
    """
    normalized = str(kind or "info").lower()
    if normalized not in NOTIFY_KINDS:
        normalized = "info"
    if not FLUENT_AVAILABLE or parent is None or not message:
        return False
    try:
        show = getattr(_InfoBar, normalized)
        show(
            title,
            str(message),
            duration=int(duration if duration is not None else NOTIFY_DURATION[normalized]),
            position=_InfoBarPosition.TOP,
            parent=parent,
        )
        return True
    except Exception:
        logger.debug("Fluent InfoBar notify failed", exc_info=True)
        return False


def confirm(
    parent,
    title: str,
    content: str,
    *,
    yes_text: str = "",
    no_text: str = "",
) -> Optional[bool]:
    """Blocking yes/no confirmation via Fluent MessageBox.

    Returns True/False on user choice, None when Fluent is unavailable
    (caller falls back to QMessageBox).
    """
    if not FLUENT_AVAILABLE:
        return None
    try:
        box = _MessageBox(title, content, parent)
        if yes_text:
            box.yesButton.setText(yes_text)
        if no_text:
            box.cancelButton.setText(no_text)
        return bool(box.exec())
    except Exception:
        logger.debug("Fluent MessageBox confirm failed", exc_info=True)
        return None


def confirm_qt(parent, title: str, content: str, *args, **kwargs) -> bool:
    """Drop-in replacement for ``QMessageBox.question(...) == Yes``.

    Uses the Fluent MessageBox when available, plain QMessageBox otherwise.
    Extra positional/keyword args (StandardButton flags) are accepted and
    ignored so existing call sites keep working unchanged.
    """
    decided = confirm(parent, title, content)
    if decided is not None:
        return decided
    from PyQt6.QtWidgets import QMessageBox

    reply = QMessageBox.question(
        parent,
        title,
        content,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def new_button(text: str = "", parent=None):
    """Neutral action button (Fluent PushButton when available)."""
    from PyQt6.QtWidgets import QPushButton

    button: QPushButton
    if FLUENT_AVAILABLE:
        try:
            button = _PushButton(text, parent)
            return button
        except Exception:
            logger.debug("Fluent PushButton unavailable, using QPushButton", exc_info=True)
    button = QPushButton(text, parent)
    return button


def new_primary_button(text: str = "", parent=None):
    """Single primary action button (Fluent PrimaryPushButton when available)."""
    from PyQt6.QtWidgets import QPushButton

    button: QPushButton
    if FLUENT_AVAILABLE:
        try:
            button = _PrimaryPushButton(text, parent)
            return button
        except Exception:
            logger.debug(
                "Fluent PrimaryPushButton unavailable, using QPushButton",
                exc_info=True,
            )
    button = QPushButton(text, parent)
    button.setDefault(True)
    return button


# Navigation icons for the 8 shell pages (FluentIcon priority, RULES Sec 19).
NAV_ICONS = {
    "library": "LIBRARY",
    "workbench": "PHOTO",
    "review": "SEARCH",
    "duplicates": "SYNC",
    "jobs": "HISTORY",
    "collections": "FOLDER",
    "recipes": "DOCUMENT",
    "settings": "SETTING",
}


def nav_icon(page_key: str):
    """QIcon for a shell page, or None when Fluent icons are unavailable."""
    if not FLUENT_AVAILABLE:
        return None
    icon_name = NAV_ICONS.get(str(page_key or ""))
    if not icon_name:
        return None
    try:
        return getattr(_FIF, icon_name).icon()
    except Exception:
        logger.debug("FluentIcon %s unavailable", icon_name, exc_info=True)
        return None


__all__ = [
    "FLUENT_AVAILABLE",
    "NOTIFY_KINDS",
    "NOTIFY_DURATION",
    "NAV_ICONS",
    "notify",
    "confirm",
    "confirm_qt",
    "new_button",
    "new_primary_button",
    "nav_icon",
]
