from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.history_manager import CallableCommand, CommandType, HistoryManager
from ....i18n.catalog import t
from .shared import _selected_row_payload, _stretch_table

class CollectionsPage(QWidget):
    open_requested = pyqtSignal(str)

    def __init__(self, query_service, repository, history_manager: HistoryManager | None = None, parent=None):
        super().__init__(parent)
        self.query_service = query_service
        self.repository = repository
        self.history_manager = history_manager

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.create_btn = QPushButton()
        self.create_btn.clicked.connect(self._create_collection)
        controls.addWidget(self.create_btn)
        self.delete_btn = QPushButton()
        self.delete_btn.clicked.connect(self._delete_collection)
        controls.addWidget(self.delete_btn)
        self.remove_btn = QPushButton()
        self.remove_btn.clicked.connect(self._remove_asset)
        controls.addWidget(self.remove_btn)
        self.open_btn = QPushButton()
        self.open_btn.clicked.connect(self._open_selected_asset)
        controls.addWidget(self.open_btn)
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        self.collection_table = QTableWidget(0, 3)
        self.collection_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.collection_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.collection_table.itemSelectionChanged.connect(self._load_assets)
        _stretch_table(self.collection_table)
        splitter.addWidget(self.collection_table)

        self.asset_table = QTableWidget(0, 4)
        self.asset_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        _stretch_table(self.asset_table)
        splitter.addWidget(self.asset_table)
        splitter.setSizes([280, 780])
        self.retranslate_ui()

    def _record_history(self, description: str, undo, redo) -> None:
        if self.history_manager is None:
            return
        self.history_manager.record_applied(
            CallableCommand(
                do=redo,
                undo=undo,
                redo=redo,
                description=description,
                command_type=CommandType.LIBRARY,
            )
        )

    def _selected_collection(self):
        return _selected_row_payload(self.collection_table)

    def _selected_asset(self):
        return _selected_row_payload(self.asset_table)

    def refresh(self) -> None:
        collections = self.query_service.list_collections()
        self.collection_table.setRowCount(len(collections))
        for row_index, collection in enumerate(collections):
            values = [
                str(collection.get("id", "")),
                str(collection.get("name", "")),
                str(collection.get("asset_count", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, collection)
                self.collection_table.setItem(row_index, column, item)
        self.asset_table.setRowCount(0)
        if collections:
            self.collection_table.selectRow(0)

    def _create_collection(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            t("management.collections.create_dialog.title"),
            t("management.common.name"),
        )
        if not ok or not name.strip():
            return
        description, _ = QInputDialog.getText(
            self,
            t("management.collections.create_dialog.title"),
            t("management.common.description"),
        )
        collection_name = name.strip()
        self.repository.create_collection(collection_name, description)
        self._record_history(
            t("history.collections.create"),
            undo=lambda collection_name=collection_name: self._delete_collection_by_name(collection_name),
            redo=lambda collection_name=collection_name, description=description: (
                self.repository.create_collection(collection_name, description)
                or self.refresh()
                or True
            ),
        )
        self.refresh()

    def _delete_collection(self) -> None:
        collection = self._selected_collection()
        if collection is None:
            return
        reply = QMessageBox.question(
            self,
            t("management.collections.delete_dialog.title"),
            t("management.collections.delete_dialog.body", name=collection["name"]),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        collection_id = int(collection["id"])
        collection_snapshot = dict(collection)
        assets = self.query_service.list_assets(collection_id=collection_id, limit=5000)
        asset_ids = [int(asset.get("id", 0) or 0) for asset in assets if int(asset.get("id", 0) or 0) > 0]
        self.repository.delete_collection(collection_id)
        self._record_history(
            t("history.collections.delete"),
            undo=lambda snapshot=collection_snapshot, asset_ids=asset_ids: self._restore_collection(snapshot, asset_ids),
            redo=lambda name=str(collection_snapshot.get("name", "")): self._delete_collection_by_name(name),
        )
        self.refresh()

    def _delete_collection_by_name(self, name: str) -> bool:
        for collection in self.query_service.list_collections():
            if str(collection.get("name", "")) == str(name):
                self.repository.delete_collection(int(collection["id"]))
                self.refresh()
                return True
        self.refresh()
        return True

    def _restore_collection(self, snapshot: dict, asset_ids: list[int]) -> bool:
        name = str(snapshot.get("name", "") or "")
        description = str(snapshot.get("description", "") or "")
        collection_id = self.repository.create_collection(name, description)
        if collection_id is not None:
            self.repository.add_assets_to_collection(asset_ids, int(collection_id))
        self.refresh()
        return True

    def _load_assets(self) -> None:
        collection = self._selected_collection()
        if collection is None:
            self.asset_table.setRowCount(0)
            return
        assets = self.query_service.list_assets(
            collection_id=int(collection["id"]),
            limit=800,
        )
        self.asset_table.setRowCount(len(assets))
        for row_index, asset in enumerate(assets):
            values = [
                str(asset.get("id", "")),
                str(asset.get("display_name", "")),
                str(asset.get("primary_source_path", "")),
                str(asset.get("updated_at", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, asset)
                self.asset_table.setItem(row_index, column, item)
        if assets:
            self.asset_table.selectRow(0)

    def _remove_asset(self) -> None:
        collection = self._selected_collection()
        asset = self._selected_asset()
        if collection is None or asset is None:
            return
        asset_id = int(asset["id"])
        collection_id = int(collection["id"])
        self.repository.remove_asset_from_collection(asset_id, collection_id)
        self._record_history(
            t("history.collections.remove_asset"),
            undo=lambda asset_id=asset_id, collection_id=collection_id: (
                self.repository.add_asset_to_collection(asset_id, collection_id)
                or self.refresh()
                or True
            ),
            redo=lambda asset_id=asset_id, collection_id=collection_id: (
                self.repository.remove_asset_from_collection(asset_id, collection_id)
                or self.refresh()
                or True
            ),
        )
        self._load_assets()
        self.refresh()

    def _open_selected_asset(self) -> None:
        asset = self._selected_asset()
        if asset and asset.get("primary_source_path"):
            self.open_requested.emit(str(asset["primary_source_path"]))

    def retranslate_ui(self) -> None:
        self.create_btn.setText(t("management.collections.create"))
        self.delete_btn.setText(t("management.collections.delete"))
        self.remove_btn.setText(t("management.collections.remove_asset"))
        self.open_btn.setText(t("management.common.open_asset"))
        self.refresh_btn.setText(t("management.common.refresh"))
        self.collection_table.setHorizontalHeaderLabels(
            [
                t("management.review.header.id"),
                t("management.common.name"),
                t("management.collections.header.assets"),
            ]
        )
        self.asset_table.setHorizontalHeaderLabels(
            [
                t("management.collections.asset_header.asset"),
                t("management.common.name"),
                t("management.common.path"),
                t("management.common.updated"),
            ]
        )
        self.refresh()
