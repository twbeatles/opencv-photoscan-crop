from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ....i18n.catalog import t
from .shared import (
    _selected_row_payload,
    _selected_row_payloads,
    _stretch_table,
    _translated_job_kind,
    _translated_review_reason,
    _translated_review_status,
)

class ReviewPage(QWidget):
    open_requested = pyqtSignal(str)
    reprocess_requested = pyqtSignal(int)

    def __init__(self, review_service, parent=None):
        super().__init__(parent)
        self.review_service = review_service
        self._job_filter_id: Optional[int] = None

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        self.clear_filter_btn = QPushButton()
        self.clear_filter_btn.clicked.connect(self._clear_job_filter)
        controls.addWidget(self.clear_filter_btn)
        self.open_btn = QPushButton()
        self.open_btn.clicked.connect(self._open_selected)
        controls.addWidget(self.open_btn)
        self.approve_btn = QPushButton()
        self.approve_btn.clicked.connect(self._approve_selected)
        controls.addWidget(self.approve_btn)
        self.reject_btn = QPushButton()
        self.reject_btn.clicked.connect(self._reject_selected)
        controls.addWidget(self.reject_btn)
        self.reprocess_btn = QPushButton()
        self.reprocess_btn.clicked.connect(self._request_reprocess)
        controls.addWidget(self.reprocess_btn)
        self.resolve_relink_btn = QPushButton()
        self.resolve_relink_btn.clicked.connect(self._resolve_relink)
        controls.addWidget(self.resolve_relink_btn)
        self.add_collection_btn = QPushButton()
        self.add_collection_btn.clicked.connect(self._add_to_collection)
        controls.addWidget(self.add_collection_btn)
        self.next_btn = QPushButton()
        self.next_btn.clicked.connect(self._select_next)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.itemSelectionChanged.connect(self._load_selected_notes)
        _stretch_table(self.table)
        layout.addWidget(self.table, 1)
        self.notes_edit = QTextEdit()
        layout.addWidget(self.notes_edit)
        self.retranslate_ui()

    def focus_job(self, job_id: int) -> None:
        self._job_filter_id = int(job_id)
        self.refresh()

    def _clear_job_filter(self) -> None:
        self._job_filter_id = None
        self.refresh()

    def refresh(self) -> None:
        rows = self.review_service.list_items(limit=800)
        if self._job_filter_id is not None:
            rows = [
                row for row in rows if int(row.get("job_id", 0) or 0) == int(self._job_filter_id)
            ]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("id", "")),
                _translated_review_status(row.get("status", "")),
                _translated_review_reason(row.get("reason", "")),
                str(row.get("display_name", "")),
                _translated_job_kind(row.get("job_kind", "")),
                str(row.get("updated_at", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)
        else:
            self.notes_edit.setPlainText("")

    def _selected_reviews(self) -> list[dict]:
        return _selected_row_payloads(self.table)

    def _selected_review(self) -> Optional[dict]:
        row = _selected_row_payload(self.table)
        return row if row is not None else None

    def _load_selected_notes(self) -> None:
        row = self._selected_review()
        self.notes_edit.setPlainText(str(row.get("notes", "") or "") if row else "")

    def _approve_selected(self) -> None:
        row = _selected_row_payload(self.table)
        if row is None:
            return
        review_id = int(row["id"])
        approved = self.review_service.approve(
            review_id,
            notes=self.notes_edit.toPlainText(),
        )
        if not approved:
            QMessageBox.warning(
                self,
                t("management.review.title"),
                t("management.review.approve_requires_variant"),
            )
        self.refresh()

    def _reject_selected(self) -> None:
        row = self._selected_review()
        if row is None:
            return
        self.review_service.reject(
            int(row["id"]),
            notes=self.notes_edit.toPlainText(),
        )
        self.refresh()

    def _request_reprocess(self) -> None:
        row = self._selected_review()
        if row is None:
            return
        self.reprocess_requested.emit(int(row["id"]))

    def _resolve_relink(self) -> None:
        row = self._selected_review()
        if row is None:
            return
        review_id = int(row["id"])
        candidates = self.review_service.get_relink_candidates(review_id)
        target_source_id = None
        if len(candidates) > 1:
            labels = [
                f"{item.get('display_name', '')} :: {item.get('source_path', '')}"
                for item in candidates
            ]
            choice, ok = QInputDialog.getItem(
                self,
                t("management.review.resolve_relink.title"),
                t("management.review.resolve_relink.label"),
                labels,
                0,
                False,
            )
            if not ok or not choice:
                return
            target = candidates[labels.index(choice)]
            target_source_id = int(target.get("source_id", 0) or 0)
        elif len(candidates) == 1:
            target_source_id = int(candidates[0].get("source_id", 0) or 0)
        result = self.review_service.resolve_relink(
            review_id,
            target_source_id=target_source_id,
        )
        if result is None:
            QMessageBox.warning(
                self,
                t("management.review.title"),
                t("management.review.resolve_relink.failed"),
            )
        self.refresh()

    def _open_selected(self) -> None:
        row = _selected_row_payload(self.table)
        if row and row.get("primary_source_path"):
            self.open_requested.emit(str(row["primary_source_path"]))

    def _add_to_collection(self) -> None:
        rows = self._selected_reviews()
        asset_ids = sorted(
            {
                int(row.get("asset_id", 0) or 0)
                for row in rows
                if int(row.get("asset_id", 0) or 0) > 0
            }
        )
        if not asset_ids:
            return
        collections = self.review_service.repository.list_collections()
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
        self.review_service.repository.add_assets_to_collection(asset_ids, int(target["id"]))
        self.refresh()

    def _select_next(self) -> None:
        current = self.table.currentRow()
        if current < 0 or current + 1 >= self.table.rowCount():
            return
        self.table.selectRow(current + 1)

    def retranslate_ui(self) -> None:
        self.refresh_btn.setText(t("management.common.refresh"))
        self.clear_filter_btn.setText(t("management.review.clear_job_filter"))
        self.open_btn.setText(t("management.common.open_in_workbench"))
        self.approve_btn.setText(t("management.review.approve"))
        self.reject_btn.setText(t("management.review.reject"))
        self.reprocess_btn.setText(t("management.review.reprocess"))
        self.resolve_relink_btn.setText(t("management.review.resolve_relink.button"))
        self.add_collection_btn.setText(t("management.common.add_to_collection"))
        self.next_btn.setText(t("management.common.next"))
        self.table.setHorizontalHeaderLabels(
            [
                t("management.review.header.id"),
                t("management.review.header.status"),
                t("management.review.header.reason"),
                t("management.review.header.file"),
                t("management.review.header.job"),
                t("management.review.header.updated"),
            ]
        )
        self.notes_edit.setPlaceholderText(t("management.review.notes_placeholder"))
        self.refresh()
