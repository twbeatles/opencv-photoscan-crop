#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collapsible Section Widget for Photo Cropper v9.0.

Provides animated collapsible sections for settings panel organization.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..components import make_secondary
from ..design_tokens import COLLAPSIBLE_HEADER_QSS, SPACE_SM, SPACE_XS, SPACE_XXS


class CollapsibleSection(QWidget):
    """A collapsible section widget with animated expand/collapse.

    Usage:
        section = CollapsibleSection("Title")
        section.add_widget(some_widget)
        layout.addWidget(section)
    """

    def __init__(self, title: str = "", parent=None, initially_expanded: bool = True):
        super().__init__(parent)
        self._is_expanded = initially_expanded
        self._content_height = 0

        self._setup_ui(title)
        # Set initial state without animation
        if not initially_expanded:
            self._content_area.setMaximumHeight(0)
            self._arrow_label.setText("▶")
        else:
            self._arrow_label.setText("▼")

    def _setup_ui(self, title: str):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header button area
        self._header = QFrame()
        self._header.setObjectName("collapsibleHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(COLLAPSIBLE_HEADER_QSS)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(SPACE_XXS, SPACE_XS, SPACE_XXS, SPACE_XS)
        header_layout.setSpacing(SPACE_XS)

        self._arrow_label = QLabel("▼")
        self._arrow_label.setFixedWidth(16)
        make_secondary(self._arrow_label)
        header_layout.addWidget(self._arrow_label)

        self._title_label = QLabel(title)
        font = self._title_label.font()
        font.setWeight(QFont.Weight.DemiBold)
        self._title_label.setFont(font)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        main_layout.addWidget(self._header)

        # Content area
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(SPACE_XXS, SPACE_XS, SPACE_XXS, SPACE_SM)
        self._content_layout.setSpacing(SPACE_XS)

        main_layout.addWidget(self._content_area)

    def mousePressEvent(self, event):
        """Toggle on click anywhere in the header."""
        header_rect = self._header.geometry()
        if header_rect.contains(event.pos()):
            self.toggle()
        super().mousePressEvent(event)

    def toggle(self):
        """Toggle expand/collapse state."""
        self._is_expanded = not self._is_expanded
        if self._is_expanded:
            self._arrow_label.setText("▼")
            self._content_area.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self._content_area.show()
        else:
            self._arrow_label.setText("▶")
            self._content_area.setMaximumHeight(0)
            self._content_area.hide()

    def add_widget(self, widget: QWidget):
        """Add a widget to the content area."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a layout to the content area."""
        self._content_layout.addLayout(layout)

    @property
    def is_expanded(self) -> bool:
        return self._is_expanded

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout
