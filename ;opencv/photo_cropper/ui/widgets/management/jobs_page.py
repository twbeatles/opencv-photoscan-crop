from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....i18n.catalog import t
from ....utils.file_helpers import open_file_explorer
from .shared import (
    _selected_row_payload,
    _stretch_table,
    _translate_summary_key,
    _translated_bool,
    _translated_job_kind,
    _translated_job_status,
)

class JobsPage(QWidget):
    rerun_requested = pyqtSignal(int, bool)
    open_review_requested = pyqtSignal(int)

    def __init__(self, query_service, parent=None):
        super().__init__(parent)
        self.query_service = query_service

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        self.rerun_btn = QPushButton()
        self.rerun_btn.clicked.connect(lambda: self._emit_rerun(False))
        controls.addWidget(self.rerun_btn)
        self.retry_failed_btn = QPushButton()
        self.retry_failed_btn.clicked.connect(lambda: self._emit_rerun(True))
        controls.addWidget(self.retry_failed_btn)
        self.open_output_btn = QPushButton()
        self.open_output_btn.clicked.connect(self._open_output)
        controls.addWidget(self.open_output_btn)
        self.open_review_btn = QPushButton()
        self.open_review_btn.clicked.connect(self._open_review_subset)
        controls.addWidget(self.open_review_btn)
        self.summary_btn = QPushButton()
        self.summary_btn.clicked.connect(self._show_summary)
        controls.addWidget(self.summary_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.table = QTableWidget(0, 9)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        _stretch_table(self.table)
        layout.addWidget(self.table, 1)
        self.retranslate_ui()

    def refresh(self) -> None:
        rows = self.query_service.list_jobs(limit=400)
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("id", "")),
                _translated_job_kind(row.get("job_kind", "")),
                _translated_job_status(row.get("status", "")),
                str(row.get("processed_items", "")),
                str(row.get("success_count", "")),
                str(row.get("partial_count", "")),
                str(row.get("failed_count", "")),
                str(row.get("started_at", "")),
                str(row.get("recipe_name", "")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)

    def _selected_job(self) -> Optional[dict]:
        return _selected_row_payload(self.table)

    def _emit_rerun(self, failed_only: bool) -> None:
        row = self._selected_job()
        if row is None:
            return
        self.rerun_requested.emit(int(row["id"]), bool(failed_only))

    def _open_output(self) -> None:
        row = self._selected_job()
        if row is None:
            return
        output_path = str(row.get("output_path", "") or "")
        if not output_path:
            return
        target = output_path if os.path.isdir(output_path) else os.path.dirname(output_path)
        if target and os.path.exists(target):
            open_file_explorer(target)

    def _open_review_subset(self) -> None:
        row = self._selected_job()
        if row is None:
            return
        self.open_review_requested.emit(int(row["id"]))

    def _show_summary(self) -> None:
        row = self._selected_job()
        if row is None:
            return
        summary = dict(row.get("summary", {}) or {})
        body_lines = []
        for key, value in summary.items():
            rendered = _translated_bool(bool(value)) if key == "cancelled" else value
            body_lines.append(f"{_translate_summary_key(key)}: {rendered}")
        body = "\n".join(body_lines) or t("management.jobs.summary.empty")
        QMessageBox.information(self, t("management.jobs.summary.title"), body)

    def retranslate_ui(self) -> None:
        self.refresh_btn.setText(t("management.common.refresh"))
        self.rerun_btn.setText(t("management.jobs.rerun"))
        self.retry_failed_btn.setText(t("management.jobs.retry_failed_only"))
        self.open_output_btn.setText(t("management.jobs.open_output"))
        self.open_review_btn.setText(t("management.jobs.open_review_subset"))
        self.summary_btn.setText(t("management.jobs.view_summary"))
        self.table.setHorizontalHeaderLabels(
            [
                t("management.review.header.id"),
                t("management.jobs.header.kind"),
                t("management.jobs.header.status"),
                t("management.jobs.header.processed"),
                t("management.jobs.header.success"),
                t("management.jobs.header.partial"),
                t("management.jobs.header.failed"),
                t("management.jobs.header.started"),
                t("management.jobs.header.recipe"),
            ]
        )
        self.refresh()
