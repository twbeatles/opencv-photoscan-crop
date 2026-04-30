from __future__ import annotations

import math
import threading
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ....core.history_manager import CallableCommand, CommandType, HistoryManager
from ....core.library import AssetQuery, get_provider_status
from ....i18n.catalog import t
from .shared import (
    _stretch_table,
    _translated_job_status,
    _translated_review_status,
    _translated_tag_kind,
    _translated_timeline_type,
    _translated_variant_kind,
)

class LibraryPage(QWidget):
    open_requested = pyqtSignal(str)
    import_progress = pyqtSignal(int, int)
    import_finished = pyqtSignal(int, str)

    def __init__(
        self,
        query_service,
        ingest_service,
        thumbnail_service,
        repository,
        history_manager: HistoryManager | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.query_service = query_service
        self.ingest_service = ingest_service
        self.thumbnail_service = thumbnail_service
        self.repository = repository
        self.history_manager = history_manager
        self._assets: list[dict] = []
        self._asset_detail: dict | None = None
        self._building_filters = False
        self._total_assets = 0
        self._current_page = 1
        self._page_size = 200
        self._import_thread: threading.Thread | None = None
        self._import_cancel_event: threading.Event | None = None
        self.import_progress.connect(self._on_import_progress)
        self.import_finished.connect(self._on_import_finished)

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

    def _build_search_widget(self) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.returnPressed.connect(self.refresh)
        layout.addWidget(self.search_input)
        return wrapper

    def _build_collection_selector(self) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        self.collection_filter = QComboBox()
        self.collection_filter.currentIndexChanged.connect(self._reset_to_first_page)
        layout.addWidget(self.collection_filter)
        return wrapper

    def _selected_asset(self) -> Optional[dict]:
        item = self.asset_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_assets(self) -> list[dict]:
        payloads = []
        for item in self.asset_list.selectedItems():
            payload = item.data(Qt.ItemDataRole.UserRole)
            if payload is not None:
                payloads.append(payload)
        return payloads

    def _selected_collection_id(self) -> Optional[int]:
        if not hasattr(self, "collection_filter"):
            return None
        data = self.collection_filter.currentData()
        return int(data) if data not in (None, "") else None

    def _current_search_text(self) -> str:
        return self.search_input.text().strip() if hasattr(self, "search_input") else ""

    def _current_query(self) -> AssetQuery:
        tag_name = str(self.tag_filter.currentData() or "").strip()
        return AssetQuery(
            search_text=self._current_search_text(),
            collection_id=self._selected_collection_id(),
            tag_names=(tag_name,) if tag_name else (),
            review_status=str(self.review_filter.currentData() or "").strip(),
            sort_by=str(self.sort_filter.currentData() or "updated"),
            page=self._current_page,
            page_size=self._page_size,
        )

    def refresh(self) -> None:
        current_asset_id = None
        current = self._selected_asset()
        if current is not None:
            current_asset_id = int(current["id"])
        current_collection_id = self._selected_collection_id()
        current_tag_name = str(self.tag_filter.currentData() or "").strip()

        collections = self.query_service.list_collections()
        tags = self.query_service.list_tags()
        self._building_filters = True
        self.collection_filter.blockSignals(True)
        self.collection_filter.clear()
        self.collection_filter.addItem(t("management.library.collection_filter.all"), None)
        for collection in collections:
            self.collection_filter.addItem(
                f"{collection['name']} ({collection['asset_count']})",
                int(collection["id"]),
            )
        if current_collection_id is not None:
            for index in range(self.collection_filter.count()):
                if self.collection_filter.itemData(index) == current_collection_id:
                    self.collection_filter.setCurrentIndex(index)
                    break
        self.collection_filter.blockSignals(False)
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem(t("management.library.tag_filter.all"), "")
        for tag in tags:
            self.tag_filter.addItem(
                f"{tag['name']} ({tag['asset_count']})",
                str(tag["name"]),
            )
        if current_tag_name:
            for index in range(self.tag_filter.count()):
                if self.tag_filter.itemData(index) == current_tag_name:
                    self.tag_filter.setCurrentIndex(index)
                    break
        self.tag_filter.blockSignals(False)
        self._building_filters = False

        query = self._current_query()
        self._total_assets = self.query_service.count_assets(query)
        total_pages = max(1, math.ceil(self._total_assets / max(query.normalized_page_size, 1)))
        if self._current_page > total_pages:
            self._current_page = total_pages
            query = self._current_query()

        self._assets = self.query_service.list_assets(query)
        self.asset_list.clear()
        for asset in self._assets:
            thumb_path = self.thumbnail_service.ensure_thumbnail(
                asset["primary_source_path"]
            ) if asset.get("primary_source_path") else ""
            item = QListWidgetItem(QIcon(thumb_path) if thumb_path else QIcon(), asset["display_name"])
            item.setToolTip(asset["primary_source_path"])
            item.setData(Qt.ItemDataRole.UserRole, asset)
            self.asset_list.addItem(item)

        if current_asset_id is not None:
            for row in range(self.asset_list.count()):
                item = self.asset_list.item(row)
                if item is None:
                    continue
                payload = item.data(Qt.ItemDataRole.UserRole)
                if payload and int(payload["id"]) == current_asset_id:
                    self.asset_list.setCurrentRow(row)
                    break
        elif self.asset_list.count() > 0:
            self.asset_list.setCurrentRow(0)
        else:
            self._clear_detail()
        self.page_label.setText(
            t("management.library.page", current=self._current_page, total=total_pages)
        )
        self.prev_page_btn.setEnabled(self._current_page > 1)
        self.next_page_btn.setEnabled(self._current_page < total_pages)

    def _clear_detail(self) -> None:
        self._asset_detail = None
        self.name_label.setText("-")
        self.path_label.setText("-")
        self.size_label.setText("-")
        self.tag_label.setText("-")
        self.collections_label.setText("-")
        self.review_label.setText("-")
        self.note_edit.setPlainText("")
        self.timeline_table.setRowCount(0)
        self.ocr_status_label.setText(t("management.library.ocr.none"))
        self.ocr_text.setPlainText("")
        self.faces_table.setRowCount(0)
        self.people_table.setRowCount(0)
        self.people_status_label.setText(t("management.library.people.none"))

    def _on_asset_selected(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            self._clear_detail()
            return
        detail = self.query_service.get_asset_detail(int(asset["id"]))
        if detail is None:
            self._clear_detail()
            return
        self._asset_detail = detail
        self.name_label.setText(str(detail.get("display_name", "-")))
        self.path_label.setText(str(detail.get("primary_source_path", "-")))
        source = detail.get("sources", [])
        if source:
            first = source[0]
            self.size_label.setText(f"{int(first.get('width', 0))} x {int(first.get('height', 0))}")
        else:
            self.size_label.setText("-")
        tags = [
            f"{tag.get('name', '')} [{_translated_tag_kind(tag.get('kind', 'user'))}]"
            for tag in detail.get("tags", [])
        ]
        self.tag_label.setText(", ".join(tag for tag in tags if tag) or "-")
        collections = [str(item.get("name", "")) for item in detail.get("collections", [])]
        self.collections_label.setText(", ".join(item for item in collections if item) or "-")
        self.review_label.setText(_translated_review_status(asset.get("review_status", "")))
        self.note_edit.setPlainText(str(detail.get("note", "")))
        self._render_timeline(detail)
        self._render_ocr(detail)
        self._render_people(detail)

    def _import_folder(self) -> None:
        if self._import_thread is not None and self._import_thread.is_alive():
            if self._import_cancel_event is not None:
                self._import_cancel_event.set()
            self.import_btn.setEnabled(False)
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            t("management.library.import_dialog.title"),
            "",
        )
        if not folder:
            return
        cancel_event = threading.Event()
        self._import_cancel_event = cancel_event
        self.import_btn.setEnabled(True)
        self.import_btn.setText(t("dialog.cancel"))

        def progress(processed: int, total: int, _path: str) -> None:
            self.import_progress.emit(int(processed), int(total))

        def worker() -> None:
            try:
                count = self.ingest_service.import_directory(
                    folder,
                    recursive=self.recursive_checkbox.isChecked(),
                    progress_callback=progress,
                    cancel_event=cancel_event,
                )
                status = "cancelled" if cancel_event.is_set() else "ok"
                self.import_finished.emit(int(count), status)
            except Exception as exc:
                self.import_finished.emit(0, f"error:{exc}")

        self._import_thread = threading.Thread(
            target=worker,
            name="photocropper-library-import",
            daemon=True,
        )
        self._import_thread.start()

    def _on_import_progress(self, processed: int, total: int) -> None:
        if total > 0:
            self.import_btn.setText(
                t("management.library.importing_progress", count=processed, total=total)
            )

    def _on_import_finished(self, count: int, status: str) -> None:
        self._import_thread = None
        self._import_cancel_event = None
        self.import_btn.setEnabled(True)
        self.import_btn.setText(t("management.library.import_button"))
        if str(status or "").startswith("error:"):
            QMessageBox.warning(
                self,
                t("management.library.import_result.title"),
                t("management.library.import_result.error", error=status[6:]),
            )
            return
        if status == "cancelled":
            QMessageBox.information(
                self,
                t("management.library.import_result.title"),
                t("management.library.import_result.cancelled", count=count),
            )
            self.refresh()
            return
        QMessageBox.information(
            self,
            t("management.library.import_result.title"),
            t("management.library.import_result.body", count=count),
        )
        self.refresh()

    def _go_prev_page(self) -> None:
        if self._current_page > 1:
            self._current_page -= 1
            self.refresh()

    def _go_next_page(self) -> None:
        self._current_page += 1
        self.refresh()

    def _reset_to_first_page(self) -> None:
        if self._building_filters:
            return
        self._current_page = 1
        self.refresh()

    def _save_note(self) -> None:
        if not self._asset_detail:
            return
        asset_id = int(self._asset_detail["id"])
        previous = str(self._asset_detail.get("note", "") or "")
        next_note = self.note_edit.toPlainText()
        self.repository.set_asset_note(
            asset_id,
            next_note,
        )
        if previous != next_note:
            self._record_history(
                t("history.library.note"),
                undo=lambda asset_id=asset_id, previous=previous: (
                    self.repository.set_asset_note(asset_id, previous) or self.refresh() or True
                ),
                redo=lambda asset_id=asset_id, next_note=next_note: (
                    self.repository.set_asset_note(asset_id, next_note) or self.refresh() or True
                ),
            )
        self.refresh()

    def _add_to_collection(self) -> None:
        if not self._asset_detail:
            return
        collections = self.query_service.list_collections()
        if not collections:
            QMessageBox.information(
                self,
                t("management.collections.title"),
                t("management.collections.create_first_from_page"),
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
        target = next(
            (item for item in collections if str(item["name"]) == str(choice)),
            None,
        )
        if target is None:
            return
        asset_id = int(self._asset_detail["id"])
        collection_id = int(target["id"])
        self.repository.add_asset_to_collection(asset_id, collection_id)
        self._record_history(
            t("history.library.collection_add"),
            undo=lambda asset_id=asset_id, collection_id=collection_id: (
                self.repository.remove_asset_from_collection(asset_id, collection_id)
                or self.refresh()
                or True
            ),
            redo=lambda asset_id=asset_id, collection_id=collection_id: (
                self.repository.add_asset_to_collection(asset_id, collection_id)
                or self.refresh()
                or True
            ),
        )
        self.refresh()

    def _add_selected_to_collection(self) -> None:
        selected_assets = self._selected_assets()
        asset_ids = [int(asset.get("id", 0) or 0) for asset in selected_assets if int(asset.get("id", 0) or 0) > 0]
        if not asset_ids and self._asset_detail is not None:
            asset_ids = [int(self._asset_detail["id"])]
        if not asset_ids:
            return
        collections = self.query_service.list_collections()
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
        collection_id = int(target["id"])
        added = self.repository.add_assets_to_collection(asset_ids, collection_id)
        if added:
            tracked_ids = list(asset_ids)
            self._record_history(
                t("history.library.collection_add"),
                undo=lambda tracked_ids=tracked_ids, collection_id=collection_id: (
                    [
                        self.repository.remove_asset_from_collection(asset_id, collection_id)
                        for asset_id in tracked_ids
                    ]
                    and self.refresh()
                    or True
                ),
                redo=lambda tracked_ids=tracked_ids, collection_id=collection_id: (
                    self.repository.add_assets_to_collection(tracked_ids, collection_id)
                    or self.refresh()
                    or True
                ),
            )
        QMessageBox.information(
            self,
            t("management.collections.title"),
            t("management.collections.added_result", count=added, name=target["name"]),
        )
        self.refresh()

    def _add_tag(self) -> None:
        if self._asset_detail is None:
            return
        tag_name, ok = QInputDialog.getText(
            self,
            t("management.library.tag_add_dialog.title"),
            t("management.common.tag"),
        )
        if not ok or not tag_name.strip():
            return
        asset_id = int(self._asset_detail["id"])
        tag_text = tag_name.strip()
        self.repository.add_asset_tag(asset_id, tag_text)
        self._record_history(
            t("history.library.tag_add"),
            undo=lambda asset_id=asset_id, tag_text=tag_text: (
                self.repository.remove_asset_tag(asset_id, tag_text) or self.refresh() or True
            ),
            redo=lambda asset_id=asset_id, tag_text=tag_text: (
                self.repository.add_asset_tag(asset_id, tag_text) or self.refresh() or True
            ),
        )
        self.refresh()

    def _remove_tag(self) -> None:
        if self._asset_detail is None:
            return
        tags = [tag for tag in self._asset_detail.get("tags", []) if str(tag.get("source", "user")) == "user"]
        if not tags:
            QMessageBox.information(
                self,
                t("management.library.tags.title"),
                t("management.library.tag_remove_none"),
            )
            return
        choices = [str(tag.get("name", "")) for tag in tags]
        choice, ok = QInputDialog.getItem(
            self,
            t("management.library.tag_remove_dialog.title"),
            t("management.common.tag"),
            choices,
            0,
            False,
        )
        if not ok or not choice:
            return
        asset_id = int(self._asset_detail["id"])
        self.repository.remove_asset_tag(asset_id, choice)
        self._record_history(
            t("history.library.tag_remove"),
            undo=lambda asset_id=asset_id, choice=choice: (
                self.repository.add_asset_tag(asset_id, choice) or self.refresh() or True
            ),
            redo=lambda asset_id=asset_id, choice=choice: (
                self.repository.remove_asset_tag(asset_id, choice) or self.refresh() or True
            ),
        )
        self.refresh()

    def _open_selected_asset(self) -> None:
        asset = self._selected_asset()
        if asset and asset.get("primary_source_path"):
            self.open_requested.emit(str(asset["primary_source_path"]))

    def _render_timeline(self, detail: dict) -> None:
        timeline = self.query_service.get_asset_timeline(int(detail["id"]))
        self.timeline_table.setRowCount(len(timeline))
        for row_index, event in enumerate(timeline):
            event_type = str(getattr(event, "event_type", "") or "")
            label = str(getattr(event, "label", "") or "")
            metadata = dict(getattr(event, "metadata", {}) or {})
            if event_type == "review":
                label = _translated_review_status(label)
            elif event_type == "job_item":
                label = _translated_job_status(label)
            elif event_type == "variant":
                variant_kind = str(metadata.get("variant_kind", "") or "")
                if variant_kind:
                    label = f"{_translated_variant_kind(variant_kind)} | {label}"
            values = [
                _translated_timeline_type(event_type),
                str(getattr(event, "timestamp", "") or ""),
                label,
            ]
            for column, value in enumerate(values):
                self.timeline_table.setItem(row_index, column, QTableWidgetItem(value))

    def _render_ocr(self, detail: dict) -> None:
        documents = list(detail.get("ocr_documents", []) or [])
        if not documents:
            providers = get_provider_status()
            self.ocr_status_label.setText(
                t("management.library.ocr.provider_disabled")
                if not providers.ocr_available
                else t("management.library.ocr.documents_none")
            )
            self.ocr_text.setPlainText("")
            return
        self.ocr_status_label.setText(
            t("management.library.ocr.documents_count", count=len(documents))
        )
        blocks = []
        for document in documents:
            provider = str(document.get("provider", "") or "provider")
            text = str(document.get("text", "") or "")
            blocks.append(f"[{provider}]\n{text}")
        self.ocr_text.setPlainText("\n\n".join(blocks))

    def _render_people(self, detail: dict) -> None:
        faces = list(detail.get("faces", []) or [])
        people = list(detail.get("people", []) or [])
        providers = get_provider_status()
        if not faces and not people:
            if not providers.person_available:
                self.people_status_label.setText(
                    t("management.library.people.provider_disabled")
                )
            else:
                self.people_status_label.setText(t("management.library.people.none"))
        else:
            self.people_status_label.setText(
                t("management.library.people.summary", faces=len(faces), people=len(people))
            )
        self.faces_table.setRowCount(len(faces))
        for row_index, face in enumerate(faces):
            values = [
                str(face.get("id", "")),
                str(face.get("x", "")),
                str(face.get("y", "")),
                str(face.get("w", "")),
                str(face.get("h", "")),
            ]
            for column, value in enumerate(values):
                self.faces_table.setItem(row_index, column, QTableWidgetItem(value))
        self.people_table.setRowCount(len(people))
        for row_index, person in enumerate(people):
            values = [
                str(person.get("name", "") or person.get("external_id", "")),
                str(person.get("provider", "")),
                f"{float(person.get('confidence', 0.0) or 0.0):.2f}",
                str(person.get("face_count", "")),
            ]
            for column, value in enumerate(values):
                self.people_table.setItem(row_index, column, QTableWidgetItem(value))

    def retranslate_ui(self) -> None:
        self.import_btn.setText(t("management.library.import_button"))
        self.recursive_checkbox.setText(t("management.library.recursive"))
        self.search_label.setText(t("management.common.search"))
        self.collection_label.setText(t("management.common.collection"))
        self.tag_label_widget.setText(t("management.common.tag"))
        self.review_label_widget.setText(t("management.common.review"))
        self.sort_label_widget.setText(t("management.common.sort"))
        self.refresh_btn.setText(t("management.common.refresh"))
        self.prev_page_btn.setText(t("management.common.previous"))
        self.next_page_btn.setText(t("management.common.next"))
        self.bulk_collection_btn.setText(t("management.library.add_selected_to_collection"))
        self.add_tag_btn.setText(t("management.library.add_tag"))
        self.remove_tag_btn.setText(t("management.library.remove_tag"))
        self.open_btn.setText(t("management.common.open_in_workbench"))
        self.search_input.setPlaceholderText(t("management.library.search_placeholder"))
        self.meta_group.setTitle(t("management.library.detail.overview"))
        self.note_group.setTitle(t("management.library.detail.notes"))
        self.note_edit.setPlaceholderText(t("management.library.note_placeholder"))
        self.save_note_btn.setText(t("management.library.save_note"))
        self.add_collection_btn.setText(t("management.common.add_to_collection"))
        self.detail_tabs.setTabText(0, t("management.library.detail.overview"))
        self.detail_tabs.setTabText(1, t("management.library.detail.timeline"))
        self.detail_tabs.setTabText(2, t("management.library.detail.ocr"))
        self.detail_tabs.setTabText(3, t("management.library.detail.people"))
        self.timeline_table.setHorizontalHeaderLabels(
            [
                t("management.timeline.header.type"),
                t("management.timeline.header.when"),
                t("management.timeline.header.label"),
            ]
        )
        self.faces_table.setHorizontalHeaderLabels(
            [
                t("management.library.people.header.face"),
                t("management.library.people.header.x"),
                t("management.library.people.header.y"),
                t("management.library.people.header.w"),
                t("management.library.people.header.h"),
            ]
        )
        self.people_table.setHorizontalHeaderLabels(
            [
                t("management.library.people.header.person"),
                t("management.library.people.header.provider"),
                t("management.library.people.header.confidence"),
                t("management.library.people.header.faces"),
            ]
        )

        review_options = [
            ("", t("management.common.all")),
            ("new", _translated_review_status("new")),
            ("needs_review", _translated_review_status("needs_review")),
            ("approved", _translated_review_status("approved")),
            ("rejected", _translated_review_status("rejected")),
            ("reprocess_requested", _translated_review_status("reprocess_requested")),
        ]
        current_review = self.review_filter.currentData()
        self.review_filter.blockSignals(True)
        self.review_filter.clear()
        for value, label in review_options:
            self.review_filter.addItem(label, value)
        index = max(0, self.review_filter.findData(current_review))
        self.review_filter.setCurrentIndex(index)
        self.review_filter.blockSignals(False)

        sort_options = [
            ("updated", t("management.library.sort.updated")),
            ("name", t("management.library.sort.name")),
            ("created", t("management.library.sort.created")),
        ]
        current_sort = self.sort_filter.currentData()
        self.sort_filter.blockSignals(True)
        self.sort_filter.clear()
        for value, label in sort_options:
            self.sort_filter.addItem(label, value)
        index = max(0, self.sort_filter.findData(current_sort))
        self.sort_filter.setCurrentIndex(index)
        self.sort_filter.blockSignals(False)

        for widget, key in (
            (self.name_label, "management.library.detail.name"),
            (self.path_label, "management.library.detail.path"),
            (self.size_label, "management.library.detail.size"),
            (self.tag_label, "management.library.detail.tags"),
            (self.collections_label, "management.library.detail.collections"),
            (self.review_label, "management.library.detail.review"),
        ):
            label_widget = self.meta_layout.labelForField(widget)
            if isinstance(label_widget, QLabel):
                label_widget.setText(t(key))

        self.refresh()
