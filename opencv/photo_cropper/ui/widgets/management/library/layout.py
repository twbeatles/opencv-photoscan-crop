#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI assembly for LibraryPage."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..shared import _stretch_table


def build_library_page_ui(page) -> None:
    self = page
    layout = QVBoxLayout(self)

    controls = QHBoxLayout()
    self.import_btn = QPushButton()
    self.import_btn.clicked.connect(self._import_folder)
    controls.addWidget(self.import_btn)

    self.recursive_checkbox = QCheckBox()
    self.recursive_checkbox.setChecked(True)
    controls.addWidget(self.recursive_checkbox)

    self.search_label = QLabel()
    controls.addWidget(self.search_label)
    controls.addWidget(self._build_search_widget())

    self.collection_label = QLabel()
    controls.addWidget(self.collection_label)
    controls.addWidget(self._build_collection_selector())

    self.tag_label_widget = QLabel()
    controls.addWidget(self.tag_label_widget)
    self.tag_filter = QComboBox()
    self.tag_filter.currentIndexChanged.connect(self._reset_to_first_page)
    controls.addWidget(self.tag_filter)

    self.review_label_widget = QLabel()
    controls.addWidget(self.review_label_widget)
    self.review_filter = QComboBox()
    self.review_filter.currentIndexChanged.connect(self._reset_to_first_page)
    controls.addWidget(self.review_filter)

    self.sort_label_widget = QLabel()
    controls.addWidget(self.sort_label_widget)
    self.sort_filter = QComboBox()
    self.sort_filter.currentIndexChanged.connect(self._reset_to_first_page)
    controls.addWidget(self.sort_filter)

    self.refresh_btn = QPushButton()
    self.refresh_btn.clicked.connect(self.refresh)
    controls.addWidget(self.refresh_btn)
    controls.addStretch()
    layout.addLayout(controls)

    actions = QHBoxLayout()
    self.prev_page_btn = QPushButton()
    self.prev_page_btn.clicked.connect(self._go_prev_page)
    actions.addWidget(self.prev_page_btn)
    self.page_label = QLabel()
    actions.addWidget(self.page_label)
    self.next_page_btn = QPushButton()
    self.next_page_btn.clicked.connect(self._go_next_page)
    actions.addWidget(self.next_page_btn)
    self.bulk_collection_btn = QPushButton()
    self.bulk_collection_btn.clicked.connect(self._add_selected_to_collection)
    actions.addWidget(self.bulk_collection_btn)
    self.add_tag_btn = QPushButton()
    self.add_tag_btn.clicked.connect(self._add_tag)
    actions.addWidget(self.add_tag_btn)
    self.remove_tag_btn = QPushButton()
    self.remove_tag_btn.clicked.connect(self._remove_tag)
    actions.addWidget(self.remove_tag_btn)
    self.open_btn = QPushButton()
    self.open_btn.clicked.connect(self._open_selected_asset)
    actions.addWidget(self.open_btn)
    actions.addStretch()
    layout.addLayout(actions)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    layout.addWidget(splitter, 1)

    self.asset_list = QListWidget()
    self.asset_list.setViewMode(QListWidget.ViewMode.IconMode)
    icon_size = int(getattr(self.thumbnail_service, "size", 192) or 192)
    self.asset_list.setIconSize(QSize(icon_size, icon_size))
    self.asset_list.setResizeMode(QListWidget.ResizeMode.Adjust)
    self.asset_list.setMovement(QListWidget.Movement.Static)
    self.asset_list.setSpacing(12)
    self.asset_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    self.asset_list.currentItemChanged.connect(self._on_asset_selected)
    self.asset_list.itemDoubleClicked.connect(self._open_selected_asset)
    splitter.addWidget(self.asset_list)

    detail_widget = QWidget()
    detail_layout = QVBoxLayout(detail_widget)

    self.detail_tabs = QTabWidget()
    detail_layout.addWidget(self.detail_tabs, 1)

    overview_tab = QWidget()
    overview_layout = QVBoxLayout(overview_tab)

    self.meta_group = QGroupBox()
    self.meta_layout = QFormLayout(self.meta_group)
    self.name_label = QLabel("-")
    self.path_label = QLabel("-")
    self.path_label.setWordWrap(True)
    self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    self.size_label = QLabel("-")
    self.tag_label = QLabel("-")
    self.collections_label = QLabel("-")
    self.review_label = QLabel("-")
    self.meta_layout.addRow("", self.name_label)
    self.meta_layout.addRow("", self.path_label)
    self.meta_layout.addRow("", self.size_label)
    self.meta_layout.addRow("", self.tag_label)
    self.meta_layout.addRow("", self.collections_label)
    self.meta_layout.addRow("", self.review_label)
    overview_layout.addWidget(self.meta_group)

    self.note_group = QGroupBox()
    note_layout = QVBoxLayout(self.note_group)
    self.note_edit = QTextEdit()
    note_layout.addWidget(self.note_edit)
    overview_layout.addWidget(self.note_group, 1)

    action_row = QHBoxLayout()
    self.save_note_btn = QPushButton()
    self.save_note_btn.clicked.connect(self._save_note)
    action_row.addWidget(self.save_note_btn)
    self.add_collection_btn = QPushButton()
    self.add_collection_btn.clicked.connect(self._add_to_collection)
    action_row.addWidget(self.add_collection_btn)
    action_row.addStretch()
    overview_layout.addLayout(action_row)
    self.detail_tabs.addTab(overview_tab, "")

    timeline_tab = QWidget()
    timeline_layout = QVBoxLayout(timeline_tab)
    self.timeline_table = QTableWidget(0, 3)
    self.timeline_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.timeline_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    _stretch_table(self.timeline_table)
    timeline_layout.addWidget(self.timeline_table, 1)
    self.detail_tabs.addTab(timeline_tab, "")

    ocr_tab = QWidget()
    ocr_layout = QVBoxLayout(ocr_tab)
    self.ocr_status_label = QLabel()
    ocr_layout.addWidget(self.ocr_status_label)
    self.ocr_text = QTextEdit()
    self.ocr_text.setReadOnly(True)
    ocr_layout.addWidget(self.ocr_text, 1)
    self.detail_tabs.addTab(ocr_tab, "")

    people_tab = QWidget()
    people_layout = QVBoxLayout(people_tab)
    self.people_status_label = QLabel()
    people_layout.addWidget(self.people_status_label)
    self.faces_table = QTableWidget(0, 5)
    self.faces_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.faces_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    _stretch_table(self.faces_table)
    people_layout.addWidget(self.faces_table, 1)
    self.people_table = QTableWidget(0, 4)
    self.people_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.people_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    _stretch_table(self.people_table)
    people_layout.addWidget(self.people_table, 1)
    self.detail_tabs.addTab(people_tab, "")

    splitter.addWidget(detail_widget)
    splitter.setSizes([820, 360])

    self.retranslate_ui()


__all__ = ["build_library_page_ui"]
