#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preset UI wrapper backed by the shared recipe manager."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.recipes import get_recipe_manager
from ...core.settings_model import AppSettings
from ...i18n.catalog import t

logger = logging.getLogger(__name__)

DEFAULT_PRESETS: dict[str, dict[str, Any]] = {}


class PresetManager:
    """Compatibility wrapper around the shared recipe store."""

    def __init__(self, presets_dir: Optional[str] = None):
        self._presets_dir = presets_dir or ""
        self._recipe_manager = get_recipe_manager()

    def list_presets(self) -> List[str]:
        return self._recipe_manager.list_presets()

    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        return self._recipe_manager.get_preset(name)

    def get_preset_description(self, name: str) -> str:
        return self._recipe_manager.get_preset_description(name)

    def is_default_preset(self, name: str) -> bool:
        return self._recipe_manager.is_default_preset(name)

    def save_preset(self, name: str, settings: AppSettings, description: str = "") -> bool:
        return self._recipe_manager.save_preset(name, settings, description=description)

    def apply_preset(self, name: str, settings: AppSettings) -> bool:
        return self._recipe_manager.apply_preset(name, settings)

    def delete_preset(self, name: str) -> bool:
        return self._recipe_manager.delete_preset(name)

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        return self._recipe_manager.rename_recipe(old_name, new_name)


class PresetManagerWidget(QWidget):
    """Widget for managing presets."""

    preset_selected = pyqtSignal(str)
    preset_applied = pyqtSignal(str)

    def __init__(self, settings: Optional[AppSettings] = None, parent=None):
        super().__init__(parent)
        self._settings = settings or AppSettings()
        self._manager = get_preset_manager()

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self._list_group = QGroupBox(t("toolbar.preset"))
        list_layout = QVBoxLayout(self._list_group)

        self._preset_list = QListWidget()
        self._preset_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._preset_list.itemDoubleClicked.connect(self._on_apply)
        list_layout.addWidget(self._preset_list)

        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: gray; font-style: italic;")
        list_layout.addWidget(self._desc_label)
        layout.addWidget(self._list_group)

        button_row = QHBoxLayout()
        self._apply_btn = QPushButton(t("dialog.ok"))
        self._apply_btn.clicked.connect(self._on_apply)
        self._apply_btn.setEnabled(False)
        button_row.addWidget(self._apply_btn)

        self._save_btn = QPushButton(t("dialog.save"))
        self._save_btn.clicked.connect(self._on_save)
        button_row.addWidget(self._save_btn)

        self._delete_btn = QPushButton(t("dialog.delete"))
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setEnabled(False)
        button_row.addWidget(self._delete_btn)

        layout.addLayout(button_row)
        self.retranslate_ui()

    def _refresh_list(self) -> None:
        self._preset_list.clear()
        for name in self._manager.list_presets():
            item = QListWidgetItem(name)
            item.setIcon(
                QIcon.fromTheme("folder")
                if self._manager.is_default_preset(name)
                else QIcon.fromTheme("document")
            )
            self._preset_list.addItem(item)

    def _on_selection_changed(self) -> None:
        item = self._preset_list.currentItem()
        if item is None:
            self._desc_label.setText("")
            self._apply_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            return

        name = item.text()
        self._desc_label.setText(self._manager.get_preset_description(name) or "-")
        self._apply_btn.setEnabled(True)
        self._delete_btn.setEnabled(not self._manager.is_default_preset(name))
        self.preset_selected.emit(name)

    def _on_apply(self) -> None:
        item = self._preset_list.currentItem()
        if item is None:
            return
        name = item.text()
        if self._manager.apply_preset(name, self._settings):
            self.preset_applied.emit(name)
            QMessageBox.information(
                self,
                t("toolbar.preset"),
                t("management.presets.applied", name=name),
            )

    def _on_save(self) -> None:
        name, ok = QInputDialog.getText(self, t("dialog.save"), t("toolbar.preset"))
        if not ok or not name.strip():
            return
        description, _ = QInputDialog.getText(
            self,
            t("dialog.save"),
            t("management.common.description"),
        )
        if self._manager.save_preset(name.strip(), self._settings, description):
            self._refresh_list()

    def _on_delete(self) -> None:
        item = self._preset_list.currentItem()
        if item is None:
            return
        name = item.text()
        if self._manager.is_default_preset(name):
            QMessageBox.warning(
                self,
                t("dialog.warning"),
                t("management.presets.default_delete_forbidden"),
            )
            return
        reply = QMessageBox.question(
            self,
            t("dialog.delete"),
            t("management.presets.delete_confirm", name=name),
        )
        if reply == QMessageBox.StandardButton.Yes and self._manager.delete_preset(name):
            self._refresh_list()

    def set_settings(self, settings: AppSettings) -> None:
        self._settings = settings

    def get_manager(self) -> PresetManager:
        return self._manager

    def retranslate_ui(self) -> None:
        self._list_group.setTitle(t("toolbar.preset"))
        self._apply_btn.setText(t("dialog.ok"))
        self._save_btn.setText(t("dialog.save"))
        self._delete_btn.setText(t("dialog.delete"))
        item = self._preset_list.currentItem()
        if item is not None:
            self._desc_label.setText(self._manager.get_preset_description(item.text()) or "-")


class PresetComboBox(QComboBox):
    """Combo box for quick preset selection."""

    preset_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = get_preset_manager()
        self._refresh()
        self.currentTextChanged.connect(self._on_changed)

    def _refresh(self) -> None:
        self.clear()
        self.addItem(f"-- {t('toolbar.preset')} --")
        self.addItems(self._manager.list_presets())

    def _on_changed(self, text: str) -> None:
        if text and not text.startswith("--"):
            self.preset_selected.emit(text)

    def apply_to_settings(self, settings: AppSettings) -> bool:
        text = self.currentText()
        if text and not text.startswith("--"):
            return self._manager.apply_preset(text, settings)
        return False

    def retranslate_ui(self) -> None:
        current_text = self.currentText()
        self._refresh()
        index = self.findText(current_text)
        if index >= 0:
            self.setCurrentIndex(index)


_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager
