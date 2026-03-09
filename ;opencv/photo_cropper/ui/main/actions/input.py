#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Input, drag-drop, and keyboard actions."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ....utils.file_helpers import SUPPORTED_IMAGE_FORMATS, get_image_files, open_file_explorer
from ..models import WindowRefs, WindowServices, WindowState


class InputActions:
    """Handle folder selection, drag-drop, and keyboard dispatch."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._reconfigure_scheduler: Optional[Callable[[], None]] = None
        self._update_image_list: Optional[Callable[[], None]] = None
        self._update_batch_edit_controls: Optional[Callable[[], None]] = None
        self._request_preview: Optional[Callable[[], None]] = None
        self._navigate_prev: Optional[Callable[[], None]] = None
        self._navigate_next: Optional[Callable[[], None]] = None
        self._start_processing: Optional[Callable[[], None]] = None
        self._rotate_preview: Optional[Callable[[], None]] = None
        self._show_compare_dialog: Optional[Callable[[], None]] = None
        self._show_fullscreen: Optional[Callable[[], None]] = None
        self._undo: Optional[Callable[[], None]] = None
        self._redo: Optional[Callable[[], None]] = None

    def bind(
        self,
        *,
        reconfigure_scheduler: Callable[[], None],
        update_image_list: Callable[[], None],
        update_batch_edit_controls: Callable[[], None],
        request_preview: Callable[[], None],
        navigate_prev: Callable[[], None],
        navigate_next: Callable[[], None],
        start_processing: Callable[[], None],
        rotate_preview: Callable[[], None],
        show_compare_dialog: Callable[[], None],
        show_fullscreen: Callable[[], None],
        undo: Callable[[], None],
        redo: Callable[[], None],
    ) -> None:
        self._reconfigure_scheduler = reconfigure_scheduler
        self._update_image_list = update_image_list
        self._update_batch_edit_controls = update_batch_edit_controls
        self._request_preview = request_preview
        self._navigate_prev = navigate_prev
        self._navigate_next = navigate_next
        self._start_processing = start_processing
        self._rotate_preview = rotate_preview
        self._show_compare_dialog = show_compare_dialog
        self._show_fullscreen = show_fullscreen
        self._undo = undo
        self._redo = redo

    def select_input_folder(self) -> None:
        start_dir = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        path = QFileDialog.getExistingDirectory(self.services.host_window, "입력 폴더 선택", start_dir)
        if path and self.refs.input_path_edit is not None:
            self.refs.input_path_edit.setText(path)
            if self.refs.output_path_edit is not None and not self.refs.output_path_edit.text():
                self.refs.output_path_edit.setText(os.path.join(path, "output_cropped"))

    def select_output_folder(self) -> None:
        start_dir = self.refs.output_path_edit.text() if self.refs.output_path_edit else ""
        path = QFileDialog.getExistingDirectory(self.services.host_window, "출력 폴더 선택", start_dir)
        if path and self.refs.output_path_edit is not None:
            self.refs.output_path_edit.setText(path)

    def on_input_path_changed(self, path: str) -> None:
        self.state.pending_input_path = path or ""
        if self.services.input_path_scan_timer is not None:
            self.services.input_path_scan_timer.start(250)
        if self._reconfigure_scheduler is not None:
            self._reconfigure_scheduler()

    def on_output_path_changed(self, _path: str) -> None:
        if self._reconfigure_scheduler is not None:
            self._reconfigure_scheduler()

    def flush_input_path_change(self) -> None:
        path = self.state.pending_input_path
        if os.path.isdir(path):
            normalized = os.path.abspath(path)
            if normalized != self.state.active_input_root:
                self.state.active_input_root = normalized
                self.state.batch_contours_norm.clear()
                self.state.batch_contours_edited.clear()
                self.state.failed_boundary_files = []
                self.state.last_detected_contour = None
            files = get_image_files(path)
            if self.refs.file_count_badge is not None:
                self.refs.file_count_badge.setText(f" 파일: {len(files)}개 ")
                self.refs.file_count_badge.setStyleSheet(
                    """
                background-color: rgba(46, 160, 67, 0.2);
                color: #3fb950;
                border-radius: 4px;
                padding: 2px 8px;
                margin: 0 4px;
                font-weight: bold;
            """
                )
            if self._update_image_list is not None:
                self._update_image_list()
        else:
            if self.refs.file_count_badge is not None:
                self.refs.file_count_badge.setText(" 파일: 0개 ")
                self.refs.file_count_badge.setStyleSheet(
                    """
                background-color: rgba(128, 128, 128, 0.2);
                color: #8b949e;
                border-radius: 4px;
                padding: 2px 8px;
                margin: 0 4px;
            """
                )
            self.state.active_input_root = ""
            self.state.image_list = []
            self.state.current_image_index = -1
            self.state.current_image_path = None
            self.state.failed_boundary_files = []
        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()

    def open_output_folder(self) -> None:
        path = self.refs.output_path_edit.text() if self.refs.output_path_edit else ""
        if path and os.path.exists(path):
            open_file_explorer(path)
        else:
            QMessageBox.warning(self.services.host_window, "경고", "출력 폴더가 존재하지 않습니다.")

    def open_single_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.services.host_window,
            "이미지 선택",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;모든 파일 (*.*)",
        )
        if path:
            self.state.current_image_path = path
            if self._request_preview is not None:
                self._request_preview()

    def refresh_file_list(self) -> None:
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        if input_path and os.path.isdir(input_path):
            files = get_image_files(input_path)
            if self.refs.file_count_badge is not None:
                self.refs.file_count_badge.setText(f" 파일: {len(files)}개 ")
            if self.refs.status_label is not None:
                self.refs.status_label.setText(f"파일 목록 새로고침 완료: {len(files)}개 파일")
            if files:
                self.state.current_image_path = files[0]
                if self._request_preview is not None:
                    self._request_preview()

    def drag_enter_event(self, event: Optional[QDragEnterEvent]) -> None:
        if event is None:
            return
        mime_data = event.mimeData()
        if mime_data is not None and mime_data.hasUrls():
            event.acceptProposedAction()

    def drop_event(self, event: Optional[QDropEvent]) -> None:
        if event is None:
            return
        mime_data = event.mimeData()
        urls = mime_data.urls() if mime_data is not None else []
        if not urls:
            return

        path = urls[0].toLocalFile()
        if os.path.isdir(path):
            if self.refs.input_path_edit is not None:
                self.refs.input_path_edit.setText(path)
        elif os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_IMAGE_FORMATS:
                self.state.current_image_path = path
                if self._request_preview is not None:
                    self._request_preview()

    def handle_key_press(self, event: Optional[QKeyEvent]) -> bool:
        if event is None:
            return False
        key = event.key()

        if key == Qt.Key.Key_Left and self._navigate_prev is not None:
            self._navigate_prev()
            event.accept()
            return True
        if key == Qt.Key.Key_Right and self._navigate_next is not None:
            self._navigate_next()
            event.accept()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._request_preview is not None:
            self._request_preview()
            event.accept()
            return True
        if key == Qt.Key.Key_Space and self._start_processing is not None:
            processor = self.services.batch_session.processor
            if not (processor and processor.is_running) and not self.state.manual_extract_running:
                self._start_processing()
            event.accept()
            return True
        if key == Qt.Key.Key_R and not event.modifiers() and self._rotate_preview is not None:
            self._rotate_preview()
            event.accept()
            return True
        if key == Qt.Key.Key_C and not event.modifiers() and self._show_compare_dialog is not None:
            self._show_compare_dialog()
            event.accept()
            return True
        if key == Qt.Key.Key_F11 and self._show_fullscreen is not None:
            self._show_fullscreen()
            event.accept()
            return True
        if (
            key == Qt.Key.Key_Z
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
            and self._undo is not None
        ):
            self._undo()
            event.accept()
            return True
        if (
            key == Qt.Key.Key_Y
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
            and self._redo is not None
        ):
            self._redo()
            event.accept()
            return True
        return False
