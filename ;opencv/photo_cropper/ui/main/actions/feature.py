#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature-level UI actions."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import QDialog

from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowState


class FeatureActions:
    """Encapsulate small feature actions that mutate UI/history state."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services

    def show_fullscreen(self) -> None:
        images: list[str] = []
        if (
            isinstance(self.state.current_image_path, str)
            and self.state.current_image_path
            and os.path.isfile(self.state.current_image_path)
        ):
            images = [self.state.current_image_path]
        else:
            images = [path for path in self.state.image_list if os.path.isfile(path)]

        if not images:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("전체화면으로 표시할 이미지가 없습니다")
            return

        current_index = 0
        if self.state.current_image_path in images:
            current_index = images.index(self.state.current_image_path)
        self.services.fullscreen_manager.show(
            images,
            current_index=current_index,
            parent=self.services.host_window,
        )

    def undo(self) -> None:
        if self.refs.status_label is None:
            return
        if self.services.history_manager.can_undo:
            if self.services.history_manager.undo():
                self.refs.status_label.setText("실행 취소됨")
                ToastManager.info("↩️ 실행 취소")
        else:
            self.refs.status_label.setText("실행 취소할 항목이 없습니다")

    def redo(self) -> None:
        if self.refs.status_label is None:
            return
        if self.services.history_manager.can_redo:
            if self.services.history_manager.redo():
                self.refs.status_label.setText("다시 실행됨")
                ToastManager.info("↪️ 다시 실행")
        else:
            self.refs.status_label.setText("다시 실행할 항목이 없습니다")

    def on_crop_applied(self, cropped_image, dialog: QDialog | None = None) -> None:
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_processed_image(cropped_image)
        self.state.last_processed = cropped_image.copy()
        if self.refs.status_label is not None:
            self.refs.status_label.setText("수동 크롭이 적용되었습니다")
        if dialog is not None:
            dialog.close()
        ToastManager.success("✂️ 수동 크롭 적용됨")
