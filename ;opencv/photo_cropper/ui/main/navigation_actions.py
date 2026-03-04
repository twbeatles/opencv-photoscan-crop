#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Navigation action coordinator for MainWindow."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ...utils.file_helpers import get_image_files

if TYPE_CHECKING:
    from .window import MainWindow


class NavigationActions:
    """Encapsulate image list and previous/next navigation logic."""

    def __init__(self, window: "MainWindow"):
        self.window = window

    def update_image_list(self) -> None:
        w = self.window
        input_path = w.input_path_edit.text()
        if input_path and os.path.isdir(input_path):
            recursive = w._settings.file_management.recursive_search
            w._image_list = get_image_files(input_path, recursive=recursive)
            w.file_count_badge.setText(f" 파일: {len(w._image_list)}개 ")

            if w._image_list:
                w._current_image_index = 0
                w._current_image_path = w._image_list[0]
            else:
                w._current_image_index = -1
                w._current_image_path = None
        else:
            w._image_list = []
            w._current_image_index = -1
            w._current_image_path = None

        w._update_batch_edit_controls()

    def navigate_prev(self) -> None:
        w = self.window
        if w._manual_extract_running:
            return

        if not w._image_list:
            self.update_image_list()
        if not w._image_list:
            w.status_label.setText("탐색할 이미지가 없습니다")
            return

        if w._current_image_index > 0:
            w._current_image_index -= 1
        else:
            w._current_image_index = len(w._image_list) - 1

        w._current_image_path = w._image_list[w._current_image_index]
        w._request_preview()
        self.update_navigation_status()
        w._update_batch_edit_controls()

    def navigate_next(self) -> None:
        w = self.window
        if w._manual_extract_running:
            return

        if not w._image_list:
            self.update_image_list()
        if not w._image_list:
            w.status_label.setText("탐색할 이미지가 없습니다")
            return

        if w._current_image_index < len(w._image_list) - 1:
            w._current_image_index += 1
        else:
            w._current_image_index = 0

        w._current_image_path = w._image_list[w._current_image_index]
        w._request_preview()
        self.update_navigation_status()
        w._update_batch_edit_controls()

    def update_navigation_status(self) -> None:
        w = self.window
        if w._image_list and w._current_image_index >= 0:
            total = len(w._image_list)
            current = w._current_image_index + 1
            filename = os.path.basename(w._current_image_path) if w._current_image_path else ""
            w.status_label.setText(
                f"[{current}/{total}] {filename} (← → 탐색, Enter 미리보기, Space 처리)"
            )

