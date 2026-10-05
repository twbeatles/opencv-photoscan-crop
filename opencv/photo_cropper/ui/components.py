#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small shared UI building blocks.

Keeps repeated presentation decisions (secondary text, splitters, form
labels) in one place so pages stay consistent in both themes without
per-widget QSS (see DESKTOP_UI_DESIGN_RULES Sec 9 and 24).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QLabel, QSplitter, QWidget

from .design_tokens import (
    PATH_LABEL_MIN_WIDTH,
    SPLITTER_HANDLE_QSS,
    SPLITTER_HANDLE_WIDTH,
)


def make_secondary(label: QLabel) -> QLabel:
    """Render a label as secondary text using the active palette."""
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
    return label


def secondary_label(text: str = "", parent: QWidget | None = None) -> QLabel:
    """Lower-emphasis helper text that follows the dark/light theme."""
    return make_secondary(QLabel(text, parent))


def field_label(text: str = "", parent: QWidget | None = None) -> QLabel:
    """Form label with a shared minimum width so rows line up."""
    label = QLabel(text, parent)
    label.setMinimumWidth(PATH_LABEL_MIN_WIDTH)
    return label


def themed_splitter(orientation: Qt.Orientation, parent: QWidget | None = None) -> QSplitter:
    """Splitter with an invisible, comfortably wide grab handle."""
    splitter = QSplitter(orientation, parent)
    splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)
    splitter.setChildrenCollapsible(False)
    splitter.setStyleSheet(SPLITTER_HANDLE_QSS)
    return splitter


__all__ = [
    "make_secondary",
    "secondary_label",
    "field_label",
    "themed_splitter",
]
