#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collapsible Section Widget for Photo Cropper v9.0.

Provides animated collapsible sections for settings panel organization.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QParallelAnimationGroup
from PyQt6.QtGui import QFont


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
        self._header.setStyleSheet("""
            QFrame#collapsibleHeader {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                padding: 6px 10px;
            }
            QFrame#collapsibleHeader:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border-color: rgba(255, 255, 255, 0.1);
            }
        """)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(8)

        self._arrow_label = QLabel("▼")
        self._arrow_label.setFixedWidth(16)
        self._arrow_label.setStyleSheet("color: #8b949e; font-size: 10px;")
        header_layout.addWidget(self._arrow_label)

        self._title_label = QLabel(title)
        font = self._title_label.font()
        font.setWeight(QFont.Weight.DemiBold)
        self._title_label.setFont(font)
        self._title_label.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        main_layout.addWidget(self._header)

        # Content area
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(4, 8, 4, 4)
        self._content_layout.setSpacing(8)

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
