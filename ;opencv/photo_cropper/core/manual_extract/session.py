#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manual extract session runner."""

from __future__ import annotations

import os
import time
from threading import Event
from typing import Callable, Dict, List, Optional

import numpy as np

from ..batch import BatchProgress, FileResult, ProcessStatus
from ..settings_model import AppSettings
from .contour_utils import denormalize_contour_points
from .service import ManualExtractProcessor


class ManualExtractSessionRunner:
    """Run manual extract batch loop independently from UI code."""

    def __init__(self):
        self._denormalize_contour = denormalize_contour_points

    def run(
        self,
        output_path: str,
        input_root: str,
        files: List[str],
        contours_norm: Dict[str, np.ndarray],
        settings_snapshot: dict,
        stop_event: Event,
        on_progress: Callable[[BatchProgress], None],
        on_log: Callable[[str, str], None],
        on_complete: Callable[[BatchProgress, List[FileResult]], None],
    ) -> None:
        start = time.time()
        results: List[FileResult] = []
        total = len(files)

        settings = AppSettings.from_dict(settings_snapshot or {})
        extractor = ManualExtractProcessor(
            settings=settings,
            output_path=output_path,
            input_root=input_root,
            denormalize_contour_fn=self._denormalize_contour,
        )

        progress = BatchProgress(total=total, is_running=True, is_cancelled=False)
        on_progress(progress)

        for index, path in enumerate(files, 1):
            filename = os.path.basename(path)
            progress.current_file = filename
            on_progress(progress)

            if stop_event.is_set():
                progress.is_cancelled = True
                break

            outcome = extractor.process_file(path, contours_norm.get(path))
            file_result = outcome.result
            if outcome.notice_message:
                on_log(outcome.notice_message, outcome.notice_level or "warning")

            if file_result.status == ProcessStatus.SUCCESS:
                mode_label = outcome.mode_label or "자동"
                on_log(f"[{index}/{total}] 완료: {filename} ({mode_label})", "success")
            elif file_result.status == ProcessStatus.SKIPPED:
                on_log(
                    f"[{index}/{total}] 건너뜀: {filename} - {file_result.message}",
                    "skip",
                )
            else:
                on_log(
                    f"[{index}/{total}] 실패: {filename} - {file_result.message}",
                    "error",
                )

            results.append(file_result)
            progress.processed = len(results)
            if file_result.status == ProcessStatus.SUCCESS:
                progress.success += 1
            elif file_result.status == ProcessStatus.SKIPPED:
                progress.skipped += 1
            else:
                progress.failed += 1

            elapsed_ms = (time.time() - start) * 1000.0
            progress.total_time_ms = elapsed_ms
            progress.avg_time_per_file_ms = (
                elapsed_ms / progress.processed if progress.processed > 0 else 0.0
            )
            on_progress(progress)

        progress.is_running = False
        progress.current_file = ""
        on_progress(progress)
        on_complete(progress, results)
