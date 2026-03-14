#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch session lifecycle service."""

from __future__ import annotations

from typing import Callable, List, Optional

from .processor import BatchProcessor
from .types import BatchProgress
from ..settings_model import AppSettings


class BatchSessionService:
    """Manage `BatchProcessor` lifetime and callback wiring."""

    def __init__(self) -> None:
        self._processor: Optional[BatchProcessor] = None

    @property
    def processor(self) -> Optional[BatchProcessor]:
        return self._processor

    @property
    def failed_files(self) -> List[str]:
        if self._processor is None:
            return []
        return list(self._processor.failed_files or [])

    def create_processor(
        self,
        settings: AppSettings,
        on_progress: Optional[Callable[[BatchProgress], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[BatchProgress, list], None]] = None,
    ) -> BatchProcessor:
        if self._processor is not None and self._processor.is_running:
            raise RuntimeError("Batch processing is already running")
        self.cleanup()
        processor = BatchProcessor(settings)
        processor.set_callbacks(
            on_progress=on_progress,
            on_log=on_log,
            on_complete=on_complete,
        )
        self._processor = processor
        return processor

    def start_async(
        self,
        settings: AppSettings,
        input_path: str,
        output_path: str,
        files: List[str],
        on_progress: Optional[Callable[[BatchProgress], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[BatchProgress, list], None]] = None,
    ) -> BatchProcessor:
        processor = self.create_processor(
            settings=settings,
            on_progress=on_progress,
            on_log=on_log,
            on_complete=on_complete,
        )
        processor.start_async(input_path, output_path, files)
        return processor

    def request_stop(self) -> None:
        if self._processor is not None:
            self._processor.request_stop()

    def cleanup(self) -> None:
        if self._processor is not None:
            self._processor.cleanup()
            self._processor = None

