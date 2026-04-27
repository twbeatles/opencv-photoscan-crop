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


class BatchProcessorSingleFileMixin:
    def _process_single_file(
        self: Any,
        input_dir: str,
        output_dir: str,
        filename: str,
        backup_dir: Optional[str],
        current: int,
        total: int,
        output_path_override: Optional[str] = None,
        input_root: Optional[str] = None,
    ) -> FileResult:
        """Process a single file."""
        start_time = time.time()
        effective_input_root = input_root or input_dir

        if self._is_stop_requested():
            return FileResult(
                filename=os.path.basename(filename),
                status=ProcessStatus.CANCELLED,
                message="작업 취소됨",
            )

        input_path, display_name = self._resolve_input_path(
            input_dir,
            filename,
            input_root=effective_input_root,
        )
        base_output_dir = self._resolve_base_output_dir(
            input_path,
            output_dir,
            input_root=effective_input_root,
        )

        self._log(f"[{current}/{total}] 처리 중: {display_name}", "info")

        processor = self._get_worker_processor()

        # Size filtering
        if self.settings.filter.skip_small_images:
            min_size = int(self.settings.filter.min_image_size or 0)
            # Core processing already rejects tiny images (<100x100),
            # so avoid additional header I/O for the default threshold.
            if min_size > 100:
                info = processor.get_image_info(input_path)
                if info:
                    w, h, _ = info
                    if w < min_size or h < min_size:
                        self._log(f"  건너뜀: 크기 {w}x{h} < {min_size}px", "skip")
                        return FileResult(
                            filename=display_name,
                            status=ProcessStatus.SKIPPED,
                            message=f"크기 미달 ({w}x{h})",
                        )

        # File-size filtering (performance guard)
        max_size_mb = int(getattr(self.settings.performance, "max_image_size_mb", 0) or 0)
        if max_size_mb > 0:
            try:
                size_mb = os.path.getsize(input_path) / (1024 * 1024)
                if size_mb > max_size_mb:
                    self._log(
                        f"  건너뜀: 파일 크기 {size_mb:.1f}MB > 제한 {max_size_mb}MB",
                        "skip",
                    )
                    return FileResult(
                        filename=display_name,
                        status=ProcessStatus.SKIPPED,
                        message=f"파일 크기 제한 초과 ({size_mb:.1f}MB)",
                    )
            except Exception:
                pass

        # Skip already processed files
        if self.settings.filter.skip_processed:
            index_outputs, index_usable, index_status = self.lookup_processed_outputs_from_index(
                input_path,
                output_dir,
            )
            if index_outputs:
                if index_status == RECORD_STATUS_PARTIAL:
                    self._log(
                        "  부분 저장 이력이 있어 재처리를 계속 진행합니다.",
                        "warning",
                    )
                else:
                    self._log(
                        f"  건너뜀: 처리 이력 일치 - {os.path.basename(index_outputs[0])}",
                        "skip",
                    )
                    return FileResult(
                        filename=display_name,
                        status=ProcessStatus.SKIPPED,
                        message="이미 처리됨(인덱스)",
                    )

            naming_or_timestamp = (
                self.settings.file_management.use_naming_rules
                or self.settings.output.add_timestamp
            )
            if naming_or_timestamp and (not index_usable) and (
                not self._skip_processed_notice_shown
            ):
                self._log(
                    "현재 파일명 규칙/타임스탬프 설정으로는 정확한 중복 여부 판별이 어렵습니다.",
                    "warning",
                )
                self._skip_processed_notice_shown = True

            if output_path_override is not None and index_status != RECORD_STATUS_PARTIAL:
                if os.path.exists(output_path_override):
                    self._log(
                        f"  건너뜀: 이미 처리됨 - {os.path.basename(output_path_override)}",
                        "skip",
                    )
                    return FileResult(
                        filename=display_name,
                        status=ProcessStatus.SKIPPED,
                        message="이미 처리됨",
                    )
            elif not naming_or_timestamp and index_status != RECORD_STATUS_PARTIAL:
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                ext = "." + self.settings.output.output_format.lower()
                existing = self._find_existing_output(
                    base_name,
                    ext,
                    output_dir,
                    multi_photo=self.settings.multi_photo.enabled,
                    input_path=input_path,
                    input_root=effective_input_root,
                )
                if existing:
                    self._log(
                        f"  건너뜀: 이미 처리됨 - {os.path.basename(existing)}", "skip"
                    )
                    return FileResult(
                        filename=display_name,
                        status=ProcessStatus.SKIPPED,
                        message="이미 처리됨",
                    )

        # Backup
        if backup_dir:
            try:
                rel_parent = relative_parent_dir(input_path, effective_input_root)
                backup_target_dir = (
                    os.path.join(backup_dir, rel_parent) if rel_parent else backup_dir
                )
                os.makedirs(backup_target_dir, exist_ok=True)
                backup_path = os.path.join(backup_target_dir, os.path.basename(input_path))
                shutil.copy2(input_path, backup_path)
            except Exception as e:
                self._log(f"  백업 실패: {e}", "warning")

        # v9.0: Multi-photo detection mode
        if self.settings.multi_photo.enabled:
            try:
                multi_result = self._process_multi_photo(
                    input_path,
                    output_dir,
                    display_name,
                    current,
                    total,
                    start_time,
                    processor,
                    input_root=effective_input_root,
                )
                if multi_result.status == ProcessStatus.SUCCESS:
                    outputs = list(multi_result.output_paths or [])
                    if not outputs and multi_result.output_path:
                        outputs = [multi_result.output_path]
                    if outputs:
                        self.record_processed_outputs(input_path, output_dir, outputs)
                elif multi_result.status == ProcessStatus.PARTIAL_SUCCESS:
                    outputs = list(multi_result.output_paths or [])
                    if not outputs and multi_result.output_path:
                        outputs = [multi_result.output_path]
                    if outputs:
                        self.record_processed_outputs(
                            input_path,
                            output_dir,
                            outputs,
                            status=RECORD_STATUS_PARTIAL,
                        )
                return multi_result
            except Exception as e:
                self._log(f"  멀티포토 처리 오류: {e}, 단일 모드로 전환", "warning")

        # Process image (standard single-photo mode)
        debug_base = output_dir if self.settings.debug.enabled else None
        result = processor.process_image(
            input_path,
            debug_dir=debug_base,
            debug_tag="batch",
        )

        processing_time = (time.time() - start_time) * 1000

        if result.success and result.image is not None:
            processed_image, resolved_output_dir = self._run_post_pipeline(
                result.image,
                base_output_dir,
            )

            # Generate output filename
            output_path = output_path_override or self._build_output_path(
                input_path,
                resolved_output_dir,
                suffix="_cropped",
            )

            # Save (use processed_image which may have watermark/resize applied)
            success, msg, file_size = processor.save_image(
                processed_image,
                output_path,
                self.settings.output.output_format,
                self.settings.output.jpg_quality,
                self.settings.output.png_compression,
                self.settings.output.webp_quality,
                source_path=input_path,
                preserve_metadata=self.settings.output.preserve_metadata,
            )

            if success:
                output_filename = os.path.basename(output_path)
                self._log(
                    f"  ✓ 성공: {output_filename} ({file_size:.1f} KB)", "success"
                )
                output_paths = [output_path]
                self.record_processed_outputs(input_path, output_dir, output_paths)
                return FileResult(
                    filename=display_name,
                    status=ProcessStatus.SUCCESS,
                    message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                    output_path=output_path,
                    output_paths=output_paths,
                    file_size_kb=file_size,
                    processing_time_ms=processing_time,
                )
            else:
                self._log(f"  ✗ 저장 실패: {msg}", "error")
                return FileResult(
                    filename=display_name,
                    status=ProcessStatus.FAILED,
                    message=f"저장 실패: {msg}",
                    processing_time_ms=processing_time,
                )
        else:
            self._log(f"  ✗ 실패: {result.message}", "error")
            return FileResult(
                filename=display_name,
                status=ProcessStatus.FAILED,
                message=result.message,
                processing_time_ms=processing_time,
            )
