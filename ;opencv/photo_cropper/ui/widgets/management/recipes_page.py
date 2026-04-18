from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
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

from ....core.recipes import RecipeManager
from ....core.settings_model import AppSettings
from ....i18n.catalog import t

class RecipesPage(QWidget):
    recipe_applied = pyqtSignal(str)

    def __init__(
        self,
        recipe_manager: RecipeManager,
        get_settings: Callable[[], AppSettings],
        parent=None,
    ):
        super().__init__(parent)
        self.recipe_manager = recipe_manager
        self.get_settings = get_settings

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.apply_btn = QPushButton()
        self.apply_btn.clicked.connect(self._apply_selected)
        controls.addWidget(self.apply_btn)
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self._save_current)
        controls.addWidget(self.save_btn)
        self.delete_btn = QPushButton()
        self.delete_btn.clicked.connect(self._delete_selected)
        controls.addWidget(self.delete_btn)
        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self._export_selected)
        controls.addWidget(self.export_btn)
        self.import_btn = QPushButton()
        self.import_btn.clicked.connect(self._import_recipe)
        controls.addWidget(self.import_btn)
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.recipe_list = QListWidget()
        self.recipe_list.currentItemChanged.connect(self._update_description)
        self.recipe_list.itemDoubleClicked.connect(self._apply_selected)
        layout.addWidget(self.recipe_list, 1)

        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        self.description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.description_label)
        self.retranslate_ui()

    def refresh(self) -> None:
        current_name = self.current_recipe_name()
        self.recipe_list.clear()
        for recipe in self.recipe_manager.list_recipes():
            label = recipe.name
            if recipe.origin == "default":
                label = f"{recipe.name} {t('management.recipes.default_suffix')}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, recipe.name)
            self.recipe_list.addItem(item)
        if self.recipe_list.count() > 0:
            index = 0
            for row in range(self.recipe_list.count()):
                item = self.recipe_list.item(row)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == current_name:
                    index = row
                    break
            self.recipe_list.setCurrentRow(index)
        else:
            self.description_label.setText("-")

    def current_recipe_name(self) -> str:
        return self.recipe_manager.get_current_recipe_name()

    def _selected_name(self) -> str:
        item = self.recipe_list.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _update_description(self) -> None:
        name = self._selected_name()
        recipe = self.recipe_manager.get_recipe(name) if name else None
        self.description_label.setText(recipe.description if recipe else "-")

    def _apply_selected(self) -> None:
        name = self._selected_name()
        if not name:
            return
        self.recipe_applied.emit(name)

    def _save_current(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            t("management.recipes.save_dialog.title"),
            t("management.recipes.save_dialog.name"),
        )
        if not ok or not name.strip():
            return
        description, _ = QInputDialog.getText(
            self,
            t("management.recipes.save_dialog.title"),
            t("management.common.description"),
        )
        if self.recipe_manager.save_preset(name.strip(), self.get_settings(), description):
            self.refresh()

    def _delete_selected(self) -> None:
        name = self._selected_name()
        if not name:
            return
        if self.recipe_manager.is_default_recipe(name):
            QMessageBox.warning(
                self,
                t("management.recipes.title"),
                t("management.recipes.default_delete_forbidden"),
            )
            return
        if self.recipe_manager.delete_recipe(name):
            self.refresh()

    def _export_selected(self) -> None:
        name = self._selected_name()
        if not name:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("management.recipes.export_dialog.title"),
            f"{name}.photocropper",
            t("management.recipes.file_filter"),
        )
        if path:
            self.recipe_manager.export_recipe(name, path)

    def _import_recipe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("management.recipes.import_dialog.title"),
            "",
            t("management.recipes.import_dialog.filter"),
        )
        if path:
            self.recipe_manager.import_recipe(path)
            self.refresh()

    def retranslate_ui(self) -> None:
        self.apply_btn.setText(t("management.recipes.apply"))
        self.save_btn.setText(t("management.recipes.save_current"))
        self.delete_btn.setText(t("dialog.delete"))
        self.export_btn.setText(t("management.recipes.export"))
        self.import_btn.setText(t("management.recipes.import"))
        self.refresh_btn.setText(t("management.common.refresh"))
        self.refresh()
