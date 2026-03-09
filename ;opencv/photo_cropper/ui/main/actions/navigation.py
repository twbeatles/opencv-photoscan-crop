#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Navigation actions for the main window."""

from __future__ import annotations

import os
from typing import Callable, Optional

from ....utils.file_helpers import get_image_files
from ..models import WindowRefs, WindowState


class NavigationActions:
    """Encapsulate image list and previous/next navigation logic."""

    def __init__(self, state: WindowState, refs: WindowRefs):
        self.state = state
        self.refs = refs
        self._request_preview: Optional[Callable[[], None]] = None
        self._update_batch_edit_controls: Optional[Callable[[], None]] = None

    def bind(
        self,
        *,
        request_preview: Callable[[], None],
        update_batch_edit_controls: Callable[[], None],
    ) -> None:
        self._request_preview = request_preview
        self._update_batch_edit_controls = update_batch_edit_controls

    def update_image_list(self) -> None:
        input_edit = self.refs.input_path_edit
        badge = self.refs.file_count_badge
        if input_edit is None:
            return
        input_path = input_edit.text()
        if input_path and os.path.isdir(input_path):
            recursive = self.state.settings.file_management.recursive_search
            self.state.image_list = get_image_files(input_path, recursive=recursive)
            if badge is not None:
                badge.setText(f" 파일: {len(self.state.image_list)}개 ")

            if self.state.image_list:
                self.state.current_image_index = 0
                self.state.current_image_path = self.state.image_list[0]
            else:
                self.state.current_image_index = -1
                self.state.current_image_path = None
        else:
            self.state.image_list = []
            self.state.current_image_index = -1
            self.state.current_image_path = None

        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()

    def navigate_prev(self) -> None:
        if self.state.manual_extract_running:
            return
        if not self.state.image_list:
            self.update_image_list()
        if not self.state.image_list:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("탐색할 이미지가 없습니다")
            return

        if self.state.current_image_index > 0:
            self.state.current_image_index -= 1
        else:
            self.state.current_image_index = len(self.state.image_list) - 1

        self.state.current_image_path = self.state.image_list[
            self.state.current_image_index
        ]
        if self._request_preview is not None:
            self._request_preview()
        self.update_navigation_status()
        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()

    def navigate_next(self) -> None:
        if self.state.manual_extract_running:
            return
        if not self.state.image_list:
            self.update_image_list()
        if not self.state.image_list:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("탐색할 이미지가 없습니다")
            return

        if self.state.current_image_index < len(self.state.image_list) - 1:
            self.state.current_image_index += 1
        else:
            self.state.current_image_index = 0

        self.state.current_image_path = self.state.image_list[
            self.state.current_image_index
        ]
        if self._request_preview is not None:
            self._request_preview()
        self.update_navigation_status()
        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()

    def update_navigation_status(self) -> None:
        if self.refs.status_label is None:
            return
        if self.state.image_list and self.state.current_image_index >= 0:
            total = len(self.state.image_list)
            current = self.state.current_image_index + 1
            filename = (
                os.path.basename(self.state.current_image_path)
                if self.state.current_image_path
                else ""
            )
            self.refs.status_label.setText(
                f"[{current}/{total}] {filename} (← → 탐색, Enter 미리보기, Space 처리)"
            )
