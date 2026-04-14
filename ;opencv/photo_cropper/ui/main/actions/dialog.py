#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog actions for the main window."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ....core.manual_extract import scale_contour_to_preview
from ....i18n.catalog import t
from ..models import WindowRefs, WindowServices, WindowState
from ..services import build_editor_position_label, build_editor_title
from ...widgets.compare_widget import BeforeAfterCompareWidget
from ...widgets.crop_editor_widget import CropEditorWidget


class DialogActions:
    """Encapsulate compare/help/about/crop-editor dialogs."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._resolve_preview_path: Optional[Callable[[], Optional[str]]] = None
        self._update_image_list: Optional[Callable[[], None]] = None
        self._on_crop_applied: Optional[Callable[..., None]] = None

    def bind(
        self,
        *,
        resolve_preview_path: Callable[[], Optional[str]],
        update_image_list: Callable[[], None],
        on_crop_applied: Callable[..., None],
    ) -> None:
        self._resolve_preview_path = resolve_preview_path
        self._update_image_list = update_image_list
        self._on_crop_applied = on_crop_applied

    def show_compare_dialog(self) -> None:
        if self.state.last_original is None or self.state.last_processed is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    t("msg.no_compare_image")
                )
            return

        dialog = QDialog(self.services.host_window)
        dialog.setWindowTitle(t("menu.tools.compare"))
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        compare_widget = BeforeAfterCompareWidget()
        compare_widget.set_images(self.state.last_original, self.state.last_processed)
        layout.addWidget(compare_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dialog.close)
        layout.addWidget(btn_box)
        dialog.exec()

    def _set_detected_contour(
        self, crop_editor: CropEditorWidget, contour_points
    ) -> None:
        if contour_points is None:
            crop_editor.set_rectangle_mode()
            return
        try:
            points = []
            for point in contour_points:
                if point is None or len(point) < 2:
                    continue
                points.append((float(point[0]), float(point[1])))
            if len(points) != 4:
                crop_editor.set_rectangle_mode()
                return
            crop_editor.set_perspective_points(points)
        except Exception:
            crop_editor.set_rectangle_mode()

    def show_crop_editor(self) -> None:
        source_path = self._resolve_preview_path() if self._resolve_preview_path else None
        if source_path is None and self.state.last_original is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    t("msg.no_edit_image")
                )
            return

        if not self.state.image_list and self._update_image_list is not None:
            self._update_image_list()

        dialog = QDialog(self.services.host_window)
        dialog.setWindowTitle(t("menu.tools.crop_editor"))
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout(dialog)
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton(t("dialog.crop_editor.prev"))
        next_btn = QPushButton(t("dialog.crop_editor.next"))
        nav_hint = QLabel(t("dialog.crop_editor.hint"))
        nav_hint.setObjectName("subtitleLabel")
        nav_pos_label = QLabel("")
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        nav_layout.addWidget(nav_hint)
        nav_layout.addStretch()
        nav_layout.addWidget(nav_pos_label)
        layout.addLayout(nav_layout)

        crop_editor = CropEditorWidget()
        crop_editor.crop_applied.connect(
            lambda img: self._on_crop_applied(img, None)
            if self._on_crop_applied is not None
            else None
        )
        crop_editor.crop_cancelled.connect(dialog.close)
        layout.addWidget(crop_editor)

        state = {"index": self.state.current_image_index}

        def update_editor_title(path: Optional[str]) -> None:
            filename = os.path.basename(path) if path else t("dialog.crop_editor.current_image")
            if self.state.image_list and state["index"] >= 0:
                nav_pos_label.setText(
                    build_editor_position_label(
                        state["index"] + 1, len(self.state.image_list)
                    )
                )
            else:
                nav_pos_label.setText(build_editor_position_label(0, 0))
            dialog.setWindowTitle(build_editor_title(filename))

        def load_editor_image(path: Optional[str]) -> bool:
            if not path or not os.path.exists(path):
                return False
            try:
                preview_result = self.services.image_processor.process_preview(
                    path,
                    max_size=1200,
                    debug_tag="editor",
                )
            except Exception as exc:
                QMessageBox.warning(
                    dialog,
                    t("dialog.warning"),
                    t(
                        "msg.cannot_load_image",
                        filename=os.path.basename(path),
                        error=exc,
                    ),
                )
                return False

            if preview_result is None or preview_result.original_preview is None:
                return False

            crop_editor.set_image(preview_result.original_preview)
            crop_result = preview_result.crop_result
            contour = scale_contour_to_preview(
                preview_result.original_preview,
                crop_result,
            )
            self.state.last_detected_contour = (
                contour.copy() if contour is not None else None
            )
            self._set_detected_contour(crop_editor, contour)

            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_original_image(
                    preview_result.original_preview,
                    preview_result.overlay_preview,
                    contour,
                )
            if crop_result and crop_result.success and crop_result.image is not None:
                if self.refs.preview_widget is not None:
                    self.refs.preview_widget.set_processed_image(crop_result.image)
                self.state.last_processed = crop_result.image.copy()
            else:
                if self.refs.preview_widget is not None:
                    self.refs.preview_widget.set_processed_image(None)
                self.state.last_processed = None

            self.state.last_original = preview_result.original_preview
            self.state.current_image_path = path

            if self.state.image_list:
                try:
                    state["index"] = self.state.image_list.index(path)
                    self.state.current_image_index = state["index"]
                except ValueError:
                    pass

            update_editor_title(path)
            return True

        def navigate_editor(delta: int) -> None:
            if not self.state.image_list and self._update_image_list is not None:
                self._update_image_list()
            if not self.state.image_list:
                return

            idx = state["index"]
            if idx < 0:
                if self.state.current_image_path in self.state.image_list:
                    idx = self.state.image_list.index(self.state.current_image_path)
                else:
                    idx = 0
            idx = (idx + delta) % len(self.state.image_list)
            state["index"] = idx
            load_editor_image(self.state.image_list[idx])

        prev_btn.clicked.connect(lambda: navigate_editor(-1))
        next_btn.clicked.connect(lambda: navigate_editor(1))
        prev_btn.setEnabled(len(self.state.image_list) > 1)
        next_btn.setEnabled(len(self.state.image_list) > 1)

        shortcut_prev = QShortcut(QKeySequence("Left"), dialog)
        shortcut_next = QShortcut(QKeySequence("Right"), dialog)
        shortcut_prev.activated.connect(lambda: navigate_editor(-1))
        shortcut_next.activated.connect(lambda: navigate_editor(1))

        loaded = False
        if source_path:
            loaded = load_editor_image(source_path)
        if not loaded and self.state.last_original is not None:
            crop_editor.set_image(self.state.last_original)
            self._set_detected_contour(crop_editor, self.state.last_detected_contour)
            update_editor_title(self.state.current_image_path)

        dialog.exec()

    def show_help(self) -> None:
        QMessageBox.information(
            self.services.host_window,
            t("msg.help.title"),
            t("msg.help.body"),
        )

    def show_about(self) -> None:
        version = getattr(self.services.host_window, "VERSION", "9.0")
        QMessageBox.about(
            self.services.host_window,
            t("msg.about.title"),
            t(
                "msg.about.body",
                app_name=t("app.name"),
                version=version,
            ),
        )
