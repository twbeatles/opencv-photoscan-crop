#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Toolbar builder for the main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QPushButton, QSizePolicy, QToolBar, QWidget

from ....i18n.catalog import t
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
    toolbar = QToolBar(t("toolbar.main"))
    toolbar.setObjectName("mainToolBar")
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(24, 24))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    window.addToolBar(toolbar)
    refs.toolbar = toolbar

    open_action = QAction(t("toolbar.open_folder"), window)
    open_action.setToolTip(t("toolbar.open_folder.tooltip"))
    open_action.triggered.connect(input_actions.select_input_folder)
    toolbar.addAction(open_action)
    refs.actions["toolbar.open_folder"] = open_action

    output_action = QAction(t("toolbar.output_folder"), window)
    output_action.setToolTip(t("toolbar.output_folder.tooltip"))
    output_action.triggered.connect(input_actions.open_output_folder)
    toolbar.addAction(output_action)
    refs.actions["toolbar.output_folder"] = output_action
    toolbar.addSeparator()

    preview_action = QAction(t("toolbar.preview"), window)
    preview_action.setToolTip(t("toolbar.preview.tooltip"))
    preview_action.triggered.connect(preview_actions.request_preview)
    toolbar.addAction(preview_action)
    refs.actions["toolbar.preview"] = preview_action

    rotate_action = QAction(t("toolbar.rotate"), window)
    rotate_action.setToolTip(t("toolbar.rotate.tooltip"))
    rotate_action.triggered.connect(tool_actions.rotate_preview)
    toolbar.addAction(rotate_action)
    refs.actions["toolbar.rotate"] = rotate_action

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    toolbar.addWidget(spacer)

    preset_label = QLabel(t("toolbar.preset"))
    preset_label.setStyleSheet("color: #8b949e; margin-right: 8px; font-weight: bold;")
    toolbar.addWidget(preset_label)
    refs.labels["toolbar.preset"] = preset_label

    refs.preset_combo = PresetComboBox()
    refs.preset_combo.setMinimumWidth(140)
    refs.preset_combo.preset_selected.connect(tool_actions.on_preset_selected)
    toolbar.addWidget(refs.preset_combo)
    toolbar.addSeparator()

    refs.process_btn = QPushButton(t("toolbar.start"))
    refs.process_btn.setObjectName("primaryButton")
    refs.process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.process_btn.setToolTip(t("toolbar.start.tooltip"))
    refs.process_btn.clicked.connect(batch_actions.start_processing)
    toolbar.addWidget(refs.process_btn)
    refs.buttons["toolbar.start"] = refs.process_btn
