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


class BatchProcessorBatchLoopMixin:
    def _process_batch(
        self: Any, input_dir: str, output_dir: str, file_list: Optional[List[str]] = None
    ):
        """Internal batch processing method (runs in thread)."""
        try:
            # Get file list
            if file_list is None:
                if self.settings.file_management.recursive_search:
                    excluded_roots = build_recursive_excluded_roots(
                        input_dir,
                        output_dir,
                        failed_folder_name=self.settings.file_management.failed_folder_name,
                    )
                    file_list = get_image_files(
                        input_dir,
                        recursive=True,
                        excluded_roots=excluded_roots,
                        raise_errors=True,
                    )
                else:
                    file_list = self.get_image_files(input_dir, raise_errors=True)

            if not file_list:
                self._log("처리할 이미지 파일이 없습니다", "warning")
                return

            # Create output directory
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                message = f"출력 폴더 생성 실패: {e}"
                self._log(message, "error")
                with self._lock:
                    self._progress.fatal_error = True
                    self._progress.fatal_message = message
                return

            # Create backup directory if needed
            backup_dir = None
            if self.settings.create_backup:
                backup_dir = os.path.join(output_dir, "backup")
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    self._log(f"백업 폴더 생성: {backup_dir}", "info")
                except Exception as e:
                    self._log(f"백업 폴더 생성 실패: {e}", "warning")
                    backup_dir = None

            total = len(file_list)
            with self._lock:
                self._progress.total = total
                self._progress.processed = 0

            # v9.0: Start logging session if enabled
            if self.settings.file_management.enable_logging:
                try:
                    self._processing_logger = get_processing_logger(
                        self.settings.file_management.log_directory or output_dir
                    )
                    self._processing_logger.start_session(input_dir, output_dir, total)
                except Exception as e:
                    logger.warning(f"Failed to start processing logger: {e}")

            self._log(f"총 {total}개 파일 처리 시작", "info")
            self._update_progress()
            self._reset_output_reservations()

            # Initialize naming engine for this batch if enabled
            if self.settings.file_management.use_naming_rules:
                engine = self._ensure_naming_engine()
                if engine:
                    engine.reset_counter()

            # Process each file
            work_items = []
            reserved_outputs = set()
            preview_engine = None
            input_root = input_dir

            if (
                not self.settings.multi_photo.enabled
                and not (
                    self.settings.classification.enabled
                    and self.settings.classification.auto_folder
                )
                and self.settings.file_management.use_naming_rules
            ):
                preview_engine = NamingRuleEngine(
                    NamingRule(
                        prefix=self.settings.file_management.naming_prefix,
                        suffix=self.settings.file_management.naming_suffix,
                        use_counter=self.settings.file_management.naming_use_counter,
                        counter_padding=self.settings.file_management.naming_counter_padding,
                        use_date=self.settings.file_management.naming_use_date,
                        date_format=self.settings.file_management.naming_date_format,
                        preserve_original_name=self.settings.file_management.naming_preserve_original,
                    )
                )
                preview_engine.reset_counter()

            for filename in file_list:
                input_path, _ = self._resolve_input_path(
                    input_dir,
                    filename,
                    input_root=input_root,
                )
                base_output_dir = self._resolve_base_output_dir(
                    input_path,
                    output_dir,
                    input_root=input_root,
                )
                output_path_override = None
                classification_routing = (
                    self.settings.classification.enabled
                    and self.settings.classification.auto_folder
                )
                if not self.settings.multi_photo.enabled and not classification_routing:
                    if preview_engine:
                        output_path_override = preview_engine.generate_name(
                            input_path,
                            output_dir=base_output_dir,
                            output_format=self.settings.output.output_format,
                            ensure_unique=not self.settings.filter.skip_processed,
                        )
                    else:
                        base_name = (
                            os.path.splitext(os.path.basename(input_path))[0]
                            + "_cropped"
                        )
                        extension = "." + self.settings.output.output_format.lower()
                        if self.settings.output.add_timestamp:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename_out = f"{base_name}_{timestamp}{extension}"
                        else:
                            filename_out = f"{base_name}{extension}"
                        output_path_override = os.path.join(base_output_dir, filename_out)

                    if not (
                        self.settings.filter.skip_processed
                        and os.path.exists(output_path_override)
                    ):
                        output_path_override = self._ensure_unique_output_path(
                            output_path_override, reserved=reserved_outputs
                        )
                    reserved_outputs.add(output_path_override)

                work_items.append((filename, output_path_override))

            use_threads = (
                self.settings.performance.enable_multithreading
                and self._thread_count > 1
            )

            if use_threads:
                futures = {}
                pending = set()
                try:
                    executor = ThreadPoolExecutor(max_workers=self._thread_count)
                    self._executor = executor
                    max_in_flight = max(self._thread_count * 3, self._thread_count)
                    work_iter = iter(enumerate(work_items, 1))
                    cancel_requested = False

                    def submit_next() -> bool:
                        try:
                            item_index, (filename, output_path_override) = next(work_iter)
                        except StopIteration:
                            return False
                        future = executor.submit(
                            self._process_single_file,
                            input_dir,
                            output_dir,
                            filename,
                            backup_dir,
                            item_index,
                            total,
                            output_path_override,
                            input_root,
                        )
                        futures[future] = (filename, item_index)
                        pending.add(future)
                        return True

                    while (
                        not cancel_requested
                        and not self._is_stop_requested()
                        and len(pending) < max_in_flight
                        and submit_next()
                    ):
                        pass

                    processed = 0
                    while pending:
                        done, still_pending = wait(
                            pending,
                            timeout=0.2,
                            return_when=FIRST_COMPLETED,
                        )
                        pending = set(still_pending)

                        if self._is_stop_requested() and not cancel_requested:
                            cancel_requested = True
                            for pending_future in list(pending):
                                pending_future.cancel()

                        if not done:
                            continue

                        for future in done:
                            processed += 1
                            filename, _ = futures.pop(future, ("", 0))
                            if future.cancelled():
                                result = FileResult(
                                    filename=os.path.basename(filename),
                                    status=ProcessStatus.CANCELLED,
                                    message="작업 취소됨",
                                )
                            else:
                                try:
                                    result = future.result()
                                except CancelledError:
                                    result = FileResult(
                                        filename=os.path.basename(filename),
                                        status=ProcessStatus.CANCELLED,
                                        message="작업 취소됨",
                                    )
                                except Exception as e:
                                    result = FileResult(
                                        filename=os.path.basename(filename),
                                        status=ProcessStatus.FAILED,
                                        message=str(e),
                                    )
                            self._handle_result(result, input_dir, filename, processed)

                        while (
                            not cancel_requested
                            and not self._is_stop_requested()
                            and len(pending) < max_in_flight
                            and submit_next()
                        ):
                            pass

                        if self._is_stop_requested() and not cancel_requested:
                            cancel_requested = True
                            for pending_future in list(pending):
                                pending_future.cancel()

                    if self._is_stop_requested():
                        for item_index, (filename, _output_path_override) in work_iter:
                            processed += 1
                            cancelled = FileResult(
                                filename=os.path.basename(filename),
                                status=ProcessStatus.CANCELLED,
                                message="작업 취소됨",
                            )
                            self._handle_result(cancelled, input_dir, filename, processed)
                finally:
                    for pending_future in list(pending):
                        pending_future.cancel()
                    if self._executor is not None:
                        self._executor.shutdown(wait=True)
                        self._executor = None
            else:
                processed = 0
                cancelled_tail: List[Tuple[str, Optional[str]]] = []
                for i, (filename, output_path_override) in enumerate(work_items, 1):
                    if self._is_stop_requested():
                        self._log("작업이 중단되었습니다", "warning")
                        cancelled_tail = work_items[i - 1 :]
                        break

                    result = self._process_single_file(
                        input_dir,
                        output_dir,
                        filename,
                        backup_dir,
                        i,
                        total,
                        output_path_override,
                        input_dir,
                    )
                    processed = i
                    self._handle_result(result, input_dir, filename, i)

                if self._is_stop_requested() and cancelled_tail:
                    for filename, _output_path_override in cancelled_tail:
                        processed += 1
                        cancelled = FileResult(
                            filename=os.path.basename(filename),
                            status=ProcessStatus.CANCELLED,
                            message="작업 취소됨",
                        )
                        self._handle_result(cancelled, input_dir, filename, processed)

            # Completion
            self._log("=" * 50, "info")
            if self._is_stop_requested():
                self._log("작업이 중단되었습니다", "warning")
            else:
                self._log("모든 작업 완료!", "success")

            with self._lock:
                progress = BatchProgress(**self._progress.__dict__)
            self._log(
                f"최종 통계 - 총: {progress.processed}, 성공: {progress.success}, "
                f"부분 성공: {progress.partial_success}, 실패: {progress.failed}, 건너뜀: {progress.skipped}",
                "info",
            )

            if progress.partial_success > 0:
                self._log(f"Partial success files: {progress.partial_success}", "partial")

            if self._failed_files:
                self._log(f"실패한 파일: {len(self._failed_files)}개", "warning")

            if self._failed_files and self.settings.file_management.move_failed_files:
                try:
                    failed_paths = [
                        f if os.path.isabs(f) else os.path.join(input_dir, f)
                        for f in self._failed_files
                    ]
                    moved_count, errors = classify_failed_files(
                        failed_paths,
                        input_dir,
                        failed_folder_name=self.settings.file_management.failed_folder_name,
                        copy_mode=self.settings.file_management.copy_failed_instead_of_move,
                        input_root=input_dir,
                    )
                    if moved_count > 0:
                        self._log(f"실패 파일 {moved_count}개 분류 완료", "info")
                    if errors:
                        self._log(f"실패 파일 분류 오류: {len(errors)}건", "warning")
                except Exception as e:
                    self._log(f"실패 파일 분류 중 오류: {e}", "warning")

        except Exception as e:
            message = f"배치 처리 오류: {e}"
            logger.error(f"Batch processing error: {e}")
            self._log(message, "error")
            with self._lock:
                self._progress.fatal_error = True
                self._progress.fatal_message = message
        finally:
            with self._lock:
                self._progress.is_running = False

            # v9.0: Save processing log if enabled
            if self._processing_logger is not None:
                try:
                    session = self._processing_logger.end_session()
                    if session:
                        log_format = self.settings.file_management.log_format.lower()
                        if log_format == "csv":
                            self._processing_logger.save_to_csv()
                        else:
                            self._processing_logger.save_to_json()
                        self._log("📋 처리 로그 저장 완료", "info")
                except Exception as e:
                    logger.warning(f"Failed to save processing log: {e}")

            self._safe_callback(self._on_complete, self.progress, self._results)
