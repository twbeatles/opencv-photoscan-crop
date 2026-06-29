#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Background preview worker used by the main window."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ...core.image import ImageProcessor
from ...core.settings_model import AppSettings
from ...i18n.catalog import t


class PreviewWorker(QObject):
    """Background preview worker running in a dedicated QThread."""

    preview_ready = pyqtSignal(int, object)
    preview_failed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._processor: Optional[ImageProcessor] = None
        self._settings_revision: int = -1

    @pyqtSlot(int, str, int, object)
    def process_preview(
        self,
        request_id: int,
        image_path: str,
        settings_revision: int,
        settings_snapshot: object,
    ):
        try:
            if not image_path or not os.path.exists(image_path):
                self.preview_failed.emit(request_id, t("preview.error.no_file"))
                return

            if isinstance(settings_snapshot, AppSettings):
                app_settings = settings_snapshot
            elif isinstance(settings_snapshot, dict):
                app_settings = AppSettings.from_dict(settings_snapshot)
            else:
                app_settings = AppSettings()

            if self._processor is None:
                self._processor = ImageProcessor(
                    app_settings.algorithm,
                    app_settings.processing,
                    app_settings.advanced,
                    app_settings.performance,
                    debug_settings=app_settings.debug,
                )
                self._settings_revision = settings_revision
            elif settings_revision != self._settings_revision:
                self._processor.update_settings(
                    app_settings.algorithm,
                    app_settings.processing,
                    app_settings.advanced,
                    app_settings.performance,
                    app_settings.debug,
                )
                self._settings_revision = settings_revision

            preview_result = self._processor.process_preview(
                image_path,
                max_size=800,
                debug_tag="preview",
            )
            self.preview_ready.emit(request_id, preview_result)
        except Exception as e:
            self.preview_failed.emit(request_id, str(e))


__all__ = ["PreviewWorker"]
