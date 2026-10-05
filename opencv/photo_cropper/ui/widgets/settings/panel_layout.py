#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SettingsPanel tab layout helpers."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from ...design_tokens import SPACE_XS
from ..toggle_switch import ModernToggleSwitch

def setup_ui(panel):
    self = panel
    """Setup the UI components with 5 consolidated tabs."""
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACE_XS)

    # Always-visible switch between the everyday options and every option.
    self.simple_mode_check = ModernToggleSwitch("간단 모드 (고급 탭 숨기기)")
    self.simple_mode_check.setChecked(True)
    self.simple_mode_check.toggled.connect(self._on_simple_mode_toggled)
    layout.addWidget(self.simple_mode_check)

    # Tab widget
    self.tab_widget = QTabWidget()
    self.tab_widget.setDocumentMode(True)
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

    # Let the tab pane background show through the scroll viewport.
    # (Scoped selectors: a bare "background" rule would also blank out the
    # check box and other control indicators inside the tab.)
    scroll.setStyleSheet(
        "QScrollArea { background: transparent; }"
        " QScrollArea > QWidget > QWidget { background: transparent; }"
    )

    return scroll


__all__ = ["setup_ui", "make_scrollable_tab"]
