#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Toolbar builder for the main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QPushButton, QSizePolicy, QToolBar, QWidget

from ...widgets.preset_manager import PresetComboBox
from ..models import WindowRefs


def build_toolbar(
    window,
    refs: WindowRefs,
    *,
    input_actions,
    preview_actions,
    batch_actions,
    tool_actions,
) -> None:
    toolbar = QToolBar("메인 도구모음")
    toolbar.setObjectName("mainToolBar")
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(24, 24))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    window.addToolBar(toolbar)
    refs.toolbar = toolbar

    open_action = QAction("📂 폴더 열기", window)
    open_action.setToolTip("입력 폴더 선택")
    open_action.triggered.connect(input_actions.select_input_folder)
    toolbar.addAction(open_action)

    output_action = QAction("📁 출력 폴더", window)
    output_action.setToolTip("결과물 저장 위치 확인")
    output_action.triggered.connect(input_actions.open_output_folder)
    toolbar.addAction(output_action)
    toolbar.addSeparator()

    preview_action = QAction("🔍 미리보기", window)
    preview_action.setToolTip("현재 이미지 미리보기 업데이트")
    preview_action.triggered.connect(preview_actions.request_preview)
    toolbar.addAction(preview_action)

    rotate_action = QAction("🔄 회전", window)
    rotate_action.setToolTip("시계방향 90도 회전 (Ctrl+R)")
    rotate_action.triggered.connect(tool_actions.rotate_preview)
    toolbar.addAction(rotate_action)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    toolbar.addWidget(spacer)

    preset_label = QLabel("프리셋:")
    preset_label.setStyleSheet("color: #8b949e; margin-right: 8px; font-weight: bold;")
    toolbar.addWidget(preset_label)

    refs.preset_combo = PresetComboBox()
    refs.preset_combo.setMinimumWidth(140)
    refs.preset_combo.preset_selected.connect(tool_actions.on_preset_selected)
    toolbar.addWidget(refs.preset_combo)
    toolbar.addSeparator()

    refs.process_btn = QPushButton("▶️ 변환 시작")
    refs.process_btn.setObjectName("primaryButton")
    refs.process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.process_btn.setToolTip("일괄 처리 시작 (Space)")
    refs.process_btn.clicked.connect(batch_actions.start_processing)
    toolbar.addWidget(refs.process_btn)
