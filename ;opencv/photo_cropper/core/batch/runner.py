from __future__ import annotations

import os
import shutil
import logging
import threading
import traceback
import time
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, CancelledError
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from queue import Queue

from ..image import ImageProcessor, CropResult
from ..settings_model import AppSettings
from ..face import FaceDetector
from ..image_classifier import ImageClassifier, ImageCategory, get_classifier
from ..smart_enhancer import SmartEnhancer, EnhancementPreset
from ..watermark_processor import (
    WatermarkProcessor,
    TextWatermarkSettings,
    ImageWatermarkSettings,
    WatermarkPosition,
)
from ..resize_processor import (
    ResizeProcessor,
    ResizeSettings as ResizeProcessorSettings,
    ResizeMode,
)
from ..multi_photo_detector import MultiPhotoDetector
from ...utils.file_helpers import (
    SUPPORTED_IMAGE_FORMATS,
    build_recursive_excluded_roots,
    get_image_files,
    classify_failed_files,
    get_unique_filename,
    relative_display_path,
    relative_parent_dir,
)
from ...utils.processing_log import ProcessingLogger, get_processing_logger
from ...utils.naming_rules import NamingRule, NamingRuleEngine
from ...utils.path_validation import resolve_category_folder_map
from ..processed_index import (
    ProcessedIndexStore,
    RECORD_STATUS_PARTIAL,
    RECORD_STATUS_SUCCESS,
    build_pipeline_signature,
)
from .types import BatchProgress, FileResult, ProcessStatus

logger = logging.getLogger(__name__)


class BatchProcessorRunnerMixin:
    def _safe_callback(self: Any, callback: Optional[Callable], *args, **kwargs):
        """
        Safely invoke a callback with exception handling.

        Args:
            callback: Callback function to call
            *args: Arguments to pass to callback
            **kwargs: Keyword arguments to pass to callback
        """
        if callback is None:
            return
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            logger.debug(traceback.format_exc())
    def _handle_result(
        self: Any, result: FileResult, input_dir: str, filename: str, processed_index: int
    ):
        """Handle result updates, logging, and callbacks."""
        input_file_path = (
            filename if os.path.isabs(filename) else os.path.join(input_dir, filename)
        )
        if not result.source_path:
            result.source_path = os.path.abspath(input_file_path)
        # Thread-safe list operations
        with self._lock:
            self._results.append(result)

            if result.status == ProcessStatus.FAILED:
                self._failed_files.append(filename)

            # Track processing times for accurate ETA
            if result.processing_time_ms > 0:
                self._processing_times.append(result.processing_time_ms)

        # Update progress
        with self._lock:
            self._progress.processed = processed_index
            self._progress.current_file = result.filename

            if result.status == ProcessStatus.SUCCESS:
                self._progress.success += 1
            elif result.status == ProcessStatus.PARTIAL_SUCCESS:
                self._progress.partial_success += 1
            elif result.status == ProcessStatus.FAILED:
                self._progress.failed += 1
            elif result.status in (ProcessStatus.SKIPPED, ProcessStatus.CANCELLED):
                self._progress.skipped += 1

            if self._processing_times:
                self._progress.avg_time_per_file_ms = sum(self._processing_times) / len(
                    self._processing_times
                )
            if self._start_time:
                self._progress.total_time_ms = (time.time() - self._start_time) * 1000

        # Log processing result to file
        if self._processing_logger is not None:
            try:
                if result.status == ProcessStatus.SUCCESS:
                    self._processing_logger.log_success(
                        input_file=input_file_path,
                        output_file=result.output_path,
                        detection_stage=result.message.replace("탐지: ", "")
                        if "탐지" in result.message
                        else "Unknown",
                        processing_time_ms=result.processing_time_ms,
                        file_size_before_kb=0.0,
                        file_size_after_kb=result.file_size_kb,
                    )
                elif result.status == ProcessStatus.PARTIAL_SUCCESS:
                    self._processing_logger.log_partial(
                        input_file=input_file_path,
                        output_file=result.output_path,
                        detail_message=result.message,
                        processing_time_ms=result.processing_time_ms,
                        file_size_before_kb=0.0,
                        file_size_after_kb=result.file_size_kb,
                    )
                elif result.status == ProcessStatus.FAILED:
                    self._processing_logger.log_failure(
                        input_file=input_file_path,
                        error_message=result.message,
                        processing_time_ms=result.processing_time_ms,
                    )
                elif result.status == ProcessStatus.SKIPPED:
                    self._processing_logger.log_skipped(
                        input_file=input_file_path, reason=result.message
                    )
            except Exception as log_err:
                logger.debug(f"Failed to log processing result: {log_err}")

        self._update_progress()
        self._safe_callback(self._on_file_complete, result)
    def cleanup(self: Any):
        """Clean up resources and stop threads."""
        self.request_stop()
        if self._executor:
            self._executor.shutdown(wait=False)
        if self._processing_thread and self._processing_thread.is_alive():
            # Thread join is blocking, avoid if calling from UI thread
            pass
    def _update_progress(self: Any):
        """Send progress update through callback."""
        with self._lock:
            progress_copy = BatchProgress(**self._progress.__dict__)
        self._safe_callback(self._on_progress, progress_copy)
    @property
    def is_running(self: Any) -> bool:
        """Check if processing is in progress."""
        with self._lock:
            return self._progress.is_running
    @property
    def progress(self: Any) -> BatchProgress:
        """Get current progress."""
        with self._lock:
            return BatchProgress(**self._progress.__dict__)
    @property
    def failed_files(self: Any) -> List[str]:
        """Get list of failed files."""
        return self._failed_files.copy()
    @property
    def results(self: Any) -> List[FileResult]:
        """Get all processing results."""
        return self._results.copy()
    def request_stop(self: Any):
        """Request processing to stop."""
        self._stop_event.set()
        with self._lock:
            self._progress.is_cancelled = True
        self._log("작업 중단 요청됨", "warning")
    def _is_stop_requested(self: Any) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()
    def start_async(
        self: Any, input_dir: str, output_dir: str, file_list: Optional[List[str]] = None
    ) -> bool:
        """
        Start batch processing in background thread.

        Args:
            input_dir: Input directory
            output_dir: Output directory
            file_list: Specific files to process (None = all)

        Returns:
            True if started, False if already running
        """
        if self.is_running:
            self._log("이미 처리 중입니다", "warning")
            return False

        # Reset state
        self._stop_event.clear()
        self._results = []
        self._failed_files = []
        self._processing_times = []  # v9.0: Reset timing data
        self._start_time = time.time()  # v9.0: Track start time
        self._worker_local = threading.local()

        with self._lock:
            self._progress = BatchProgress(is_running=True)

        # Start thread
        self._processing_thread = threading.Thread(
            target=self._process_batch,
            args=(input_dir, output_dir, file_list),
            daemon=True,
        )
        self._processing_thread.start()

        return True
    def wait_for_completion(self: Any, timeout: Optional[float] = None) -> bool:
        """
        Wait for processing to complete.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            True if completed, False if timeout
        """
        if self._processing_thread:
            self._processing_thread.join(timeout)
            return not self._processing_thread.is_alive()
        return True
