#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Central-widget builder for the main window."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ....i18n.catalog import t
from ...widgets.histogram_widget import HistogramWidget
from ...widgets.preview_widget import ImagePreviewWidget
from ...widgets.settings import SettingsPanel
from ..models import WindowRefs, WindowState


def build_central_widget(
    window,
    refs: WindowRefs,
    state: WindowState,
    *,
    input_actions,
    preview_actions,
    batch_actions,
    navigation_actions,
    settings_actions,
) -> None:
    central = QWidget()
    window.setCentralWidget(central)

    main_layout = QVBoxLayout(central)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(0)

    outer_splitter = QSplitter(Qt.Orientation.Vertical)
    outer_splitter.setHandleWidth(6)
    outer_splitter.setStyleSheet(
        """
        QSplitter::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5),
                stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
            height: 6px;
            margin: 2px 0;
        }
        QSplitter::handle:vertical:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8),
                stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
        }
    """
    )

    folder_card = QFrame()
    folder_card.setObjectName("statsFrame")
    folder_card_layout = QVBoxLayout(folder_card)
    folder_card_layout.setContentsMargins(10, 8, 10, 8)
    folder_card_layout.setSpacing(6)

    path_grid = QGridLayout()
    path_grid.setSpacing(6)
    path_grid.setContentsMargins(0, 0, 0, 0)
    path_grid.setColumnStretch(1, 1)

    input_label = QLabel(t("central.input_folder"))
    input_label.setStyleSheet("font-weight: bold;")
    path_grid.addWidget(input_label, 0, 0)
    refs.labels["central.input_label"] = input_label

    refs.input_path_edit = QLineEdit()
    refs.input_path_edit.setPlaceholderText(t("central.input_placeholder"))
    refs.input_path_edit.setMinimumHeight(32)
    refs.input_path_edit.setTextMargins(8, 0, 8, 0)
    refs.input_path_edit.textChanged.connect(input_actions.on_input_path_changed)
    path_grid.addWidget(refs.input_path_edit, 0, 1)

    input_browse_btn = QPushButton(t("central.browse"))
    input_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    input_browse_btn.setMinimumHeight(32)
    input_browse_btn.clicked.connect(input_actions.select_input_folder)
    path_grid.addWidget(input_browse_btn, 0, 2)
    refs.buttons["central.input_browse"] = input_browse_btn

    output_label = QLabel(t("central.output_folder"))
    output_label.setStyleSheet("font-weight: bold;")
    path_grid.addWidget(output_label, 1, 0)
    refs.labels["central.output_label"] = output_label

    refs.output_path_edit = QLineEdit()
    refs.output_path_edit.setPlaceholderText(t("central.output_placeholder"))
    refs.output_path_edit.setMinimumHeight(32)
    refs.output_path_edit.setTextMargins(8, 0, 8, 0)
    refs.output_path_edit.textChanged.connect(input_actions.on_output_path_changed)
    path_grid.addWidget(refs.output_path_edit, 1, 1)

    output_browse_btn = QPushButton(t("central.change"))
    output_browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    output_browse_btn.setMinimumHeight(32)
    output_browse_btn.clicked.connect(input_actions.select_output_folder)
    path_grid.addWidget(output_browse_btn, 1, 2)
    refs.buttons["central.output_browse"] = output_browse_btn

    output_open_btn = QPushButton(t("central.open_output_folder"))
    output_open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    output_open_btn.setMinimumHeight(32)
    output_open_btn.clicked.connect(input_actions.open_output_folder)
    path_grid.addWidget(output_open_btn, 1, 3)
    refs.buttons["central.output_open"] = output_open_btn
    folder_card_layout.addLayout(path_grid)

    hint_layout = QHBoxLayout()
    hint_layout.setContentsMargins(0, 0, 0, 0)
    hint_icon = QLabel("💡")
    hint_text = QLabel(t("central.drag_hint"))
    hint_text.setObjectName("subtitleLabel")
    hint_layout.addWidget(hint_icon)
    hint_layout.addWidget(hint_text)
    hint_layout.addStretch()
    folder_card_layout.addLayout(hint_layout)

    edit_nav_layout = QHBoxLayout()
    edit_nav_layout.setContentsMargins(0, 2, 0, 0)

    refs.batch_load_btn = QPushButton(t("central.load_batch"))
    refs.batch_load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_load_btn.setMinimumHeight(30)
    refs.batch_load_btn.clicked.connect(batch_actions.load_batch_images_for_edit)
    edit_nav_layout.addWidget(refs.batch_load_btn)

    refs.batch_failed_btn = QPushButton(t("central.load_failed"))
    refs.batch_failed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_failed_btn.setMinimumHeight(30)
    refs.batch_failed_btn.clicked.connect(batch_actions.load_failed_boundary_images_for_edit)
    edit_nav_layout.addWidget(refs.batch_failed_btn)

    refs.batch_prev_btn = QPushButton(t("central.prev"))
    refs.batch_prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_prev_btn.setMinimumHeight(30)
    refs.batch_prev_btn.clicked.connect(navigation_actions.navigate_prev)
    edit_nav_layout.addWidget(refs.batch_prev_btn)

    refs.batch_next_btn = QPushButton(t("central.next"))
    refs.batch_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_next_btn.setMinimumHeight(30)
    refs.batch_next_btn.clicked.connect(navigation_actions.navigate_next)
    edit_nav_layout.addWidget(refs.batch_next_btn)

    refs.batch_save_edits_btn = QPushButton(t("central.save_edits"))
    refs.batch_save_edits_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    refs.batch_save_edits_btn.setMinimumHeight(30)
    refs.batch_save_edits_btn.clicked.connect(batch_actions.save_batch_edited_crops)
    edit_nav_layout.addWidget(refs.batch_save_edits_btn)

    refs.batch_edit_status_label = QLabel(t("central.batch_status", current=0, total=0, edited=0, failed=0))
    refs.batch_edit_status_label.setObjectName("subtitleLabel")
    edit_nav_layout.addWidget(refs.batch_edit_status_label)
    edit_nav_layout.addStretch()
    folder_card_layout.addLayout(edit_nav_layout)
    refs.buttons["central.batch_load"] = refs.batch_load_btn
    refs.buttons["central.batch_failed"] = refs.batch_failed_btn
    refs.buttons["central.batch_prev"] = refs.batch_prev_btn
    refs.buttons["central.batch_next"] = refs.batch_next_btn
    refs.buttons["central.batch_save"] = refs.batch_save_edits_btn
    refs.labels["central.drag_hint"] = hint_text

    outer_splitter.addWidget(folder_card)

    main_splitter = QSplitter(Qt.Orientation.Horizontal)
    main_splitter.setHandleWidth(6)
    main_splitter.setStyleSheet(
        """
        QSplitter::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 transparent, stop:0.4 rgba(88, 166, 255, 0.5),
                stop:0.6 rgba(88, 166, 255, 0.5), stop:1 transparent);
            width: 6px;
            margin: 0 2px;
        }
        QSplitter::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 transparent, stop:0.3 rgba(88, 166, 255, 0.8),
                stop:0.7 rgba(88, 166, 255, 0.8), stop:1 transparent);
        }
    """
    )

    left_splitter = QSplitter(Qt.Orientation.Vertical)
    left_splitter.setHandleWidth(6)
    left_splitter.setStyleSheet(outer_splitter.styleSheet())

    refs.preview_widget = ImagePreviewWidget()
    refs.preview_widget.contour_edited.connect(preview_actions.on_preview_contour_edited)
    left_splitter.addWidget(refs.preview_widget)

    refs.histogram_widget = HistogramWidget()
    left_splitter.addWidget(refs.histogram_widget)
    left_splitter.setStretchFactor(0, 5)
    left_splitter.setStretchFactor(1, 1)
    left_splitter.setSizes([500, 100])
    main_splitter.addWidget(left_splitter)

    refs.settings_panel = SettingsPanel(state.settings)
    refs.settings_panel.settings_changed.connect(settings_actions.on_settings_changed)
    refs.settings_panel.preview_requested.connect(preview_actions.request_preview)
    refs.settings_panel.setMaximumWidth(400)
    main_splitter.addWidget(refs.settings_panel)
    main_splitter.setSizes([850, 320])
    outer_splitter.addWidget(main_splitter)

    outer_splitter.setStretchFactor(0, 0)
    outer_splitter.setStretchFactor(1, 1)
    outer_splitter.setSizes([110, 700])
    main_layout.addWidget(outer_splitter)
