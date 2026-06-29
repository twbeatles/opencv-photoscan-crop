#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature-level UI actions."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import QDialog

from ....core.history_manager import CallableCommand, CommandType
from ....i18n.catalog import t
from ...widgets.toast_notification import ToastManager
from ..services import UiMessageFactory
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
        self.messages = UiMessageFactory()

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
                self.refs.status_label.setText(t("feature.fullscreen.empty"))
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
                self.refs.status_label.setText(t("feature.undo.done"))
                ToastManager.info(t("feature.undo.toast"))
        else:
            self.refs.status_label.setText(t("feature.undo.empty"))

    def redo(self) -> None:
        if self.refs.status_label is None:
            return
        if self.services.history_manager.can_redo:
            if self.services.history_manager.redo():
                self.refs.status_label.setText(t("feature.redo.done"))
                ToastManager.info(t("feature.redo.toast"))
        else:
            self.refs.status_label.setText(t("feature.redo.empty"))

    def on_crop_applied(self, cropped_image, dialog: QDialog | None = None) -> None:
        previous_image = self.state.last_processed
        previous = previous_image.copy() if previous_image is not None else None
        next_image = cropped_image.copy()

        def apply_image(image) -> bool:
            if image is None:
                return False
            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_processed_image(image)
            self.state.last_processed = image.copy()
            return True

        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_processed_image(cropped_image)
        self.state.last_processed = next_image.copy()
        self.services.history_manager.record_applied(
            CallableCommand(
                do=lambda: apply_image(next_image),
                undo=lambda: apply_image(previous) if previous is not None else True,
                redo=lambda: apply_image(next_image),
                description=t("history.manual_crop"),
                command_type=CommandType.CROP,
            )
        )
        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("feature.manual_crop.done"))
        if dialog is not None:
            dialog.close()
        ToastManager.success(t("feature.manual_crop.toast"))
