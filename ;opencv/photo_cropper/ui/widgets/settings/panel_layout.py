#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SettingsPanel tab layout helpers."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

def setup_ui(panel):
    self = panel
    """Setup the UI components with 5 consolidated tabs."""
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)

    # Tab widget
    self.tab_widget = QTabWidget()
    layout.addWidget(self.tab_widget)

    # 5 consolidated tabs (was 11)
    self._create_basic_tab()          # 📷 기본 (후처리 + UI + 출력 + 필터)
    self._create_algorithm_tab()      # 🔬 알고리즘
    self._create_processing_tab()     # 🔧 처리 (워터마크 + 리사이즈 + 고급)
    self._create_management_tab()     # 📂 관리 (자동화 + 파일관리 + 성능)
    self._create_ai_settings_tab()    # 🤖 AI


def make_scrollable_tab(panel, content_widget: QWidget) -> QWidget:
    self = panel
    """Wrap widget in a scroll area for tab content."""
    scroll = QScrollArea()
    scroll.setWidget(content_widget)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # Style the scroll area to be transparent
    scroll.setStyleSheet("background: transparent;")

    return scroll


__all__ = ["setup_ui", "make_scrollable_tab"]
