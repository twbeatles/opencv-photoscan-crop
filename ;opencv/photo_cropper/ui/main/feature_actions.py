#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature-level UI action coordinator (history/crop-apply)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QDialog

from ..widgets.toast_notification import ToastManager

if TYPE_CHECKING:
    from .window import MainWindow


class FeatureActions:
    """Encapsulate small feature actions that mutate UI/history state."""

    def __init__(self, window: "MainWindow"):
        self.window = window

    def undo(self) -> None:
        w = self.window
        if w.history_manager.can_undo:
            if w.history_manager.undo():
                w.status_label.setText("실행 취소됨")
                ToastManager.info("↩️ 실행 취소")
        else:
            w.status_label.setText("실행 취소할 항목이 없습니다")

    def redo(self) -> None:
        w = self.window
        if w.history_manager.can_redo:
            if w.history_manager.redo():
                w.status_label.setText("다시 실행됨")
                ToastManager.info("↪️ 다시 실행")
        else:
            w.status_label.setText("다시 실행할 항목이 없습니다")

    def on_crop_applied(
        self, cropped_image, dialog: Optional[QDialog] = None
    ) -> None:
        w = self.window
        w.preview_widget.set_processed_image(cropped_image)
        w._last_processed = cropped_image.copy()
        w.status_label.setText("수동 크롭이 적용되었습니다")
        if dialog is not None:
            dialog.close()
        ToastManager.success("✂️ 수동 크롭 적용됨")
