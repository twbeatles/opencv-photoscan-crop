from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QTableWidget

from ....i18n.catalog import t


def _translated_code(prefix: str, value: object, *, empty: str = "-") -> str:
    text = str(value or "").strip()
    if not text:
        return empty
    return t(f"{prefix}.{text}", default=text)


def _translated_review_status(value: object) -> str:
    return _translated_code("management.review.status", value)


def _translated_review_reason(value: object) -> str:
    return _translated_code("management.review.reason", value)


def _translated_job_kind(value: object) -> str:
    return _translated_code("management.job.kind", value)


def _translated_job_status(value: object) -> str:
    return _translated_code("management.job.status", value)


def _translated_duplicate_kind(value: object) -> str:
    return _translated_code("management.duplicates.kind", value)


def _translated_duplicate_role(value: object) -> str:
    return _translated_code("management.duplicates.role", value)


def _translated_timeline_type(value: object) -> str:
    return _translated_code("management.timeline.event_type", value)


def _translated_variant_kind(value: object) -> str:
    return _translated_code("management.timeline.variant_kind", value)


def _translated_tag_kind(value: object) -> str:
    return _translated_code("management.library.tag_kind", value)


def _translated_bool(value: bool) -> str:
    return t("management.common.yes") if value else t("management.common.no")


def _translate_summary_key(key: object) -> str:
    text = str(key or "").strip()
    if not text:
        return "-"
    return t(f"management.jobs.summary_key.{text}", default=text)


def management_page_label(page_key: str) -> str:
    return t(f"shell.{page_key}", default=page_key.title())


def _stretch_table(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    if header is not None:
        header.setStretchLastSection(True)


def _selected_row_payload(table: QTableWidget):
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    if item is None:
        return None
    return item.data(Qt.ItemDataRole.UserRole)


def _selected_row_payloads(table: QTableWidget) -> list:
    payloads = []
    seen_rows: set[int] = set()
    for item in table.selectedItems():
        row = item.row()
        if row in seen_rows:
            continue
        seen_rows.add(row)
        payload = _selected_row_payload_for_row(table, row)
        if payload is not None:
            payloads.append(payload)
    return payloads


def _selected_row_payload_for_row(table: QTableWidget, row: int):
    if row < 0:
        return None
    item = table.item(row, 0)
    if item is None:
        return None
    return item.data(Qt.ItemDataRole.UserRole)
