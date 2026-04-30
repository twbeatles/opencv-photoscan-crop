#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tool and feature-toggle actions."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtWidgets import QInputDialog, QMessageBox

from ....core.batch_profile_manager import get_batch_profile_manager
from ....core.smart_enhancer import EnhancementPreset, get_smart_enhancer
from ....i18n.catalog import t
from ....utils.file_helpers import build_recursive_excluded_roots, get_image_files
from ....utils.image_io import load_image_unicode
from ...widgets.preset_manager import get_preset_manager
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowState
from ..services import UiMessageFactory


class ToolActions:
    """Handle toolbar/menu features outside the core preview/batch flows."""

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
        self._request_preview: Optional[Callable[[], None]] = None
        self._schedule_auto_save: Optional[Callable[[], None]] = None
        self._sync_current_settings: Optional[Callable[..., None]] = None

    def bind(
        self,
        *,
        request_preview: Callable[[], None],
        schedule_auto_save: Callable[[], None],
        sync_current_settings: Callable[..., None],
    ) -> None:
        self._request_preview = request_preview
        self._schedule_auto_save = schedule_auto_save
        self._sync_current_settings = sync_current_settings

    def rotate_preview(self) -> None:
        if not self.state.current_image_path or not os.path.exists(self.state.current_image_path):
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.rotate.empty"))
            return

        image = self.services.image_processor.load_image(self.state.current_image_path)
        if image is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.rotate.load_failed"))
            return

        rotated = self.services.image_processor.rotate_image(image, 90)
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_original_image(rotated)
            self.refs.preview_widget.set_processed_image(None)
        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("tools.rotate.done"))

    def detect_duplicates(self) -> None:
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        if not input_path or not os.path.isdir(input_path):
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("validation.input_invalid"),
            )
            return

        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("tools.duplicates.running"))

        from ....utils.file_helpers import detect_duplicates

        recursive = bool(self.state.settings.file_management.recursive_search)
        output_edit = getattr(self.refs, "output_path_edit", None)
        output_path = output_edit.text().strip() if output_edit is not None else ""
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
        excluded_roots = (
            build_recursive_excluded_roots(
                input_path,
                output_path,
                failed_folder_name=self.state.settings.file_management.failed_folder_name,
            )
            if recursive
            else None
        )
        files = get_image_files(
            input_path,
            recursive=recursive,
            excluded_roots=excluded_roots,
        )
        if not files:
            QMessageBox.information(
                self.services.host_window,
                self.messages.result_title,
                t("tools.duplicates.empty_files"),
            )
            return

        duplicates = detect_duplicates(files, method="size+hash")
        if not duplicates:
            QMessageBox.information(
                self.services.host_window,
                self.messages.result_title,
                t("tools.duplicates.none"),
            )
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.duplicates.none_status"))
            return

        dup_count, msg = self.messages.duplicate_summary(duplicates)
        QMessageBox.information(
            self.services.host_window,
            t("tools.duplicates.result_title"),
            msg,
        )
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t("tools.duplicates.found_status", count=dup_count)
            )

    def toggle_classification_settings(self) -> None:
        enabled = not self.state.settings.classification.enabled
        self.state.settings.classification.enabled = enabled
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=False)

        if enabled:
            ToastManager.success(t("tools.classification.toast_enabled"))
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.classification.enabled"))
        else:
            ToastManager.info(t("tools.classification.toast_disabled"))
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.classification.disabled"))

        if self._schedule_auto_save is not None:
            self._schedule_auto_save()

    def toggle_face_detection_settings(self) -> None:
        enabled = not self.state.settings.face_detection.enabled
        self.state.settings.face_detection.enabled = enabled
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=False)

        if enabled:
            ToastManager.success(t("tools.face.toast_enabled"))
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.face.enabled"))
            if self.state.current_image_path:
                self.do_preview_with_faces()
        else:
            ToastManager.info(t("tools.face.toast_disabled"))
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.face.disabled"))

        if self._schedule_auto_save is not None:
            self._schedule_auto_save()

    def do_preview_with_faces(self) -> None:
        if not self.state.current_image_path:
            return

        import cv2

        from ....core.face import get_face_detector

        detector = get_face_detector(
            use_dnn=getattr(self.state.settings.face_detection, "use_dnn", False),
            min_face_size=getattr(self.state.settings.face_detection, "min_face_size", 30),
        )
        image = load_image_unicode(
            self.state.current_image_path,
            cv2.IMREAD_COLOR,
            normalize_exif=True,
        )
        if image is None:
            return

        result = detector.detect(image, detect_eyes=True, suggest_crop=True)
        if result.has_faces:
            overlay = detector.draw_detections(image, result)
            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_original_image(image, overlay)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    t("tools.face.detected", count=len(result.faces))
                )
            ToastManager.info(t("tools.face.detected", count=len(result.faces)))
        elif self.refs.status_label is not None:
            self.refs.status_label.setText(t("tools.face.none"))

    def show_smart_enhancement(self) -> None:
        if self.state.last_original is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("tools.load_image_first"))
            return

        enhancer = get_smart_enhancer()
        preset_names = enhancer.get_preset_names()
        presets = [name for preset, name in preset_names.items() if preset != EnhancementPreset.NONE]
        preset, ok = QInputDialog.getItem(
            self.services.host_window,
            t("tools.smart.dialog_title"),
            t("tools.smart.dialog_body"),
            presets,
            0,
            False,
        )
        if not (ok and preset):
            return

        selected_preset = None
        for preset_enum, name in preset_names.items():
            if name == preset:
                selected_preset = preset_enum
                break
        if selected_preset is None:
            return

        result = enhancer.apply_preset(self.state.last_original, selected_preset)
        self.state.last_processed = result.image
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_processed_image(result.image)

        effects = ", ".join(result.applied_effects[:3])
        ToastManager.success(t("tools.smart.toast", preset=preset, effects=effects))
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t("tools.smart.status", preset=preset)
            )

    def show_multi_compare(self) -> None:
        from ...widgets.multi_compare_window import MultiCompareWindow

        if self.state.multi_compare_window is None:
            self.state.multi_compare_window = MultiCompareWindow(self.services.host_window)

        if self.state.last_original is not None:
            self.state.multi_compare_window.add_image(
                self.state.last_original,
                t("multi_compare.original"),
                slot=0,
            )
        if self.state.last_processed is not None:
            self.state.multi_compare_window.add_image(
                self.state.last_processed,
                t("compare.after"),
                slot=1,
            )

        self.state.multi_compare_window.show()
        self.state.multi_compare_window.raise_()
        self.state.multi_compare_window.activateWindow()

    def show_profile_manager(self) -> None:
        manager = get_batch_profile_manager()
        profiles = manager.list_profiles()
        if not profiles:
            ToastManager.warning(t("tools.profile.none"))
            return

        profile, ok = QInputDialog.getItem(
            self.services.host_window,
            t("tools.profile.dialog_title"),
            t("tools.profile.dialog_body"),
            profiles,
            0,
            False,
        )
        if not (ok and profile):
            return
        if not manager.apply_profile(profile, self.state.settings):
            return

        self.state.active_recipe_name = profile
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=True)
        ToastManager.success(t("tools.profile.toast", profile=profile))
        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("tools.profile.status", profile=profile))
        if self.state.settings.ui.auto_preview and self._request_preview is not None:
            self._request_preview()

    def on_preset_selected(self, preset_name: str) -> None:
        if not preset_name:
            return

        manager = get_preset_manager()
        if not manager.apply_preset(preset_name, self.state.settings):
            return

        self.state.active_recipe_name = preset_name
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=True)
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t("tools.preset.status", preset=preset_name)
            )
        ToastManager.success(t("tools.preset.toast", preset=preset_name))
        if self.state.settings.ui.auto_preview and self._request_preview is not None:
            self._request_preview()
