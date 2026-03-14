#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watch mode coordinator that encapsulates auto-watching and per-file processing."""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..batch import BatchProcessor
from ..folder_watcher import AutoProcessor
from ..settings_model import AppSettings, WatchModeSettings
from .types import WatchStartResult

logger = logging.getLogger(__name__)


class WatchModeCoordinator(QObject):
    """Stateful coordinator for watch mode lifecycle and file processing."""

    processing_started = pyqtSignal(str)
    processing_completed = pyqtSignal(str, bool)
    processing_completed_detailed = pyqtSignal(str, bool, str, str, int)
    queue_metrics_updated = pyqtSignal(int, int)

    def __init__(
        self,
        settings: AppSettings,
        on_log: Optional[Callable[[str, str], None]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._settings = settings
        self._on_log = on_log
        self._batch_processor: Optional[BatchProcessor] = None
        self._auto_processor: Optional[AutoProcessor] = None

    @property
    def is_active(self) -> bool:
        return self._auto_processor is not None

    def update_settings(self, settings: AppSettings) -> None:
        self._settings = settings
        if self._batch_processor is not None:
            self._batch_processor.update_settings(settings)

    def start(
        self,
        input_path: str,
        output_path: str,
        watch_settings: Optional[WatchModeSettings] = None,
    ) -> WatchStartResult:
        """Start watch mode using current settings and return normalized start result."""
        normalized_input = str(input_path or "").strip()
        if not normalized_input or not os.path.isdir(normalized_input):
            return WatchStartResult(
                success=False,
                error_code="invalid_input",
                message="Invalid input directory",
            )

        normalized_output = str(output_path or "").strip()
        if not normalized_output:
            normalized_output = os.path.join(normalized_input, "output_cropped")

        try:
            os.makedirs(normalized_output, exist_ok=True)
        except Exception as exc:
            return WatchStartResult(
                success=False,
                output_path=normalized_output,
                error_code="invalid_output",
                message=str(exc),
            )

        self.stop()
        self._ensure_batch_processor()

        recursive = bool(watch_settings and watch_settings.recursive)
        debounce_ms = int(watch_settings.debounce_ms if watch_settings else 500)
        max_wait_seconds = float(
            getattr(watch_settings, "max_wait_seconds", 30.0)
            if watch_settings is not None
            else 30.0
        )

        self._auto_processor = AutoProcessor(
            watch_path=normalized_input,
            output_path=normalized_output,
            recursive=recursive,
            debounce_ms=debounce_ms,
            max_wait_seconds=max_wait_seconds,
            process_callback=self._process_watched_file,
            parent=self,
        )
        self._bind_signals(self._auto_processor)

        if not self._auto_processor.start():
            self.stop()
            return WatchStartResult(
                success=False,
                output_path=normalized_output,
                error_code="start_failed",
                message="Failed to start watcher",
            )

        return WatchStartResult(success=True, output_path=normalized_output)

    def stop(self) -> None:
        if self._batch_processor is not None:
            try:
                self._batch_processor.request_stop()
            except Exception:
                logger.debug("Failed to request watch batch stop", exc_info=True)

        if self._auto_processor is not None:
            self._auto_processor.stop()
            self._auto_processor.deleteLater()
            self._auto_processor = None

        self._batch_processor = None

    def _bind_signals(self, auto_processor: AutoProcessor) -> None:
        auto_processor.processing_started.connect(self.processing_started)
        auto_processor.processing_completed.connect(self.processing_completed)
        auto_processor.processing_completed_detailed.connect(
            self.processing_completed_detailed
        )
        auto_processor.queue_metrics_updated.connect(self.queue_metrics_updated)

    def _ensure_batch_processor(self) -> None:
        if self._batch_processor is None:
            self._batch_processor = BatchProcessor(self._settings)
            if self._on_log is not None:
                self._batch_processor.set_callbacks(on_log=self._on_log)

    def _process_watched_file(self, input_path: str, output_path: str) -> dict:
        """Process one watched file and normalize callback response for AutoProcessor."""
        self._ensure_batch_processor()

        try:
            processor = self._batch_processor
            assert processor is not None
            processor.update_settings(self._settings)
            result = processor.process_single(input_path, output_path)
            raw_status = ""
            if hasattr(result, "status") and result.status is not None:
                raw_status = (
                    str(getattr(result.status, "value", "") or "").strip()
                    or str(getattr(result.status, "name", "") or "").strip().lower()
                )
            status = (raw_status or "failed").lower()
            success = status in {"success", "skipped", "partial_success"}
            return {
                "success": success,
                "status": status,
                "message": str(getattr(result, "message", "") or ""),
            }
        except Exception as exc:
            logger.error("Watch mode processing error: %s", exc)
            return {
                "success": False,
                "status": "process_exception",
                "message": str(exc),
            }

