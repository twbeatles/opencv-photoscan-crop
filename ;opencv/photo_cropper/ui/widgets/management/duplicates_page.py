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

from ....i18n.catalog import t
from .shared import (
    _selected_row_payload,
    _selected_row_payloads,
    _stretch_table,
    _translated_bool,
    _translated_duplicate_kind,
    _translated_duplicate_role,
)

class DuplicatesPage(QWidget):
    open_requested = pyqtSignal(str)
    maintenance_requested = pyqtSignal(str)

    def __init__(self, duplicate_service, parent=None):
        super().__init__(parent)
        self.duplicate_service = duplicate_service
        self._busy = False

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self._rebuild)
        controls.addWidget(self.refresh_btn)
        self.rebuild_near_btn = QPushButton()
        self.rebuild_near_btn.clicked.connect(self._rebuild_near)
        controls.addWidget(self.rebuild_near_btn)
        self.open_btn = QPushButton()
        self.open_btn.clicked.connect(self._open_selected_member)
        controls.addWidget(self.open_btn)
        self.representative_btn = QPushButton()
        self.representative_btn.clicked.connect(self._set_representative)
        controls.addWidget(self.representative_btn)
        self.exclude_btn = QPushButton()
        self.exclude_btn.clicked.connect(self._toggle_excluded)
        controls.addWidget(self.exclude_btn)
        self.add_collection_btn = QPushButton()
        self.add_collection_btn.clicked.connect(self._add_to_collection)
        controls.addWidget(self.add_collection_btn)
        controls.addStretch()
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, 1)

        self.group_table = QTableWidget(0, 5)
        self.group_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.group_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.group_table.itemSelectionChanged.connect(self._load_members)
        _stretch_table(self.group_table)
        splitter.addWidget(self.group_table)

        self.member_table = QTableWidget(0, 5)
        self.member_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.member_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        _stretch_table(self.member_table)
        splitter.addWidget(self.member_table)
        splitter.setSizes([260, 320])
        self.retranslate_ui()

    def refresh(self) -> None:
        groups = self.duplicate_service.list_groups(kind=None)
        self.group_table.setRowCount(len(groups))
        for row_index, group in enumerate(groups):
            values = [
                str(group.get("id", "")),
                _translated_duplicate_kind(group.get("kind", "")),
                str(group.get("representative_name", "")),
                str(group.get("member_count", "")),
                str(group.get("updated_at", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, group)
                self.group_table.setItem(row_index, column, item)
        self.member_table.setRowCount(0)
        if groups:
            self.group_table.selectRow(0)

    def _rebuild(self) -> None:
        self.maintenance_requested.emit("maintenance_exact_duplicates")

    def _rebuild_near(self) -> None:
        self.maintenance_requested.emit("maintenance_near_duplicates")

    def set_busy(self, busy: bool) -> None:
        self._busy = bool(busy)
        for button in (
            self.refresh_btn,
            self.rebuild_near_btn,
            self.representative_btn,
            self.exclude_btn,
            self.add_collection_btn,
        ):
            button.setEnabled(not self._busy)

    def _selected_group(self):
        return _selected_row_payload(self.group_table)

    def _selected_member(self):
        return _selected_row_payload(self.member_table)

    def _load_members(self) -> None:
        group = self._selected_group()
        if group is None:
            self.member_table.setRowCount(0)
            return
        members = self.duplicate_service.list_members(int(group["id"]))
        self.member_table.setRowCount(len(members))
        for row_index, member in enumerate(members):
            values = [
                str(member.get("asset_id", "")),
                _translated_duplicate_role(member.get("role", "")),
                _translated_bool(bool(int(member.get("is_excluded", 0) or 0))),
                str(member.get("display_name", "")),
                str(member.get("primary_source_path", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, member)
                self.member_table.setItem(row_index, column, item)
        if members:
            self.member_table.selectRow(0)

    def _open_selected_member(self) -> None:
        member = self._selected_member()
        if member and member.get("primary_source_path"):
            self.open_requested.emit(str(member["primary_source_path"]))

    def _set_representative(self) -> None:
        group = self._selected_group()
        member = self._selected_member()
        if group is None or member is None:
            return
        self.duplicate_service.set_representative(
            int(group["id"]),
            int(member["asset_id"]),
        )
        self.refresh()

    def _toggle_excluded(self) -> None:
        group = self._selected_group()
        member = self._selected_member()
        if group is None or member is None:
            return
        excluded = not bool(int(member.get("is_excluded", 0) or 0))
        self.duplicate_service.set_excluded(
            int(group["id"]),
            int(member["asset_id"]),
            excluded,
        )
        self._load_members()

    def _add_to_collection(self) -> None:
        members = _selected_row_payloads(self.member_table)
        asset_ids = sorted(
            {
                int(member.get("asset_id", 0) or 0)
                for member in members
                if int(member.get("asset_id", 0) or 0) > 0
            }
        )
        if not asset_ids:
            member = self._selected_member()
            if member is not None and int(member.get("asset_id", 0) or 0) > 0:
                asset_ids = [int(member["asset_id"])]
        if not asset_ids:
            return
        collections = self.duplicate_service.repository.list_collections()
        if not collections:
            QMessageBox.information(
                self,
                t("management.collections.title"),
                t("management.collections.create_first"),
            )
            return
        names = [str(collection["name"]) for collection in collections]
        choice, ok = QInputDialog.getItem(
            self,
            t("management.collections.add_dialog.title"),
            t("management.common.collection"),
            names,
            0,
            False,
        )
        if not ok or not choice:
            return
        target = next((item for item in collections if str(item["name"]) == str(choice)), None)
        if target is None:
            return
        self.duplicate_service.repository.add_assets_to_collection(asset_ids, int(target["id"]))

    def retranslate_ui(self) -> None:
        self.refresh_btn.setText(t("management.duplicates.rebuild_exact"))
        self.rebuild_near_btn.setText(t("management.duplicates.rebuild_near"))
        self.open_btn.setText(t("management.duplicates.open_member"))
        self.representative_btn.setText(t("management.duplicates.set_representative"))
        self.exclude_btn.setText(t("management.duplicates.toggle_exclude"))
        self.add_collection_btn.setText(t("management.common.add_to_collection"))
        self.group_table.setHorizontalHeaderLabels(
            [
                t("management.duplicates.header.group"),
                t("management.duplicates.header.kind"),
                t("management.duplicates.header.representative"),
                t("management.duplicates.header.members"),
                t("management.common.updated"),
            ]
        )
        self.member_table.setHorizontalHeaderLabels(
            [
                t("management.duplicates.member.asset"),
                t("management.duplicates.member.role"),
                t("management.duplicates.member.excluded"),
                t("management.common.name"),
                t("management.common.path"),
            ]
        )
        self.refresh()
