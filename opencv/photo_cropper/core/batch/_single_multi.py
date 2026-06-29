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


class BatchProcessorMultiPhotoMixin:
    def _process_multi_photo(
        self: Any,
        input_path: str,
        output_dir: str,
        filename: str,
        current: int,
        total: int,
        start_time: float,
        processor: ImageProcessor,
        input_root: Optional[str] = None,
    ) -> FileResult:
        """
        Process a single file with multi-photo detection.
        Detects multiple photos in a single scan and saves each separately.
        """
        detector = self._get_multi_photo_detector()

        # Reuse the shared loader so EXIF orientation normalization stays
        # consistent across single-photo, multi-photo, and manual paths.
        image = processor.load_image(input_path)

        if image is None:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message="이미지 로드 실패",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Detect multiple photos
        detection_result = detector.detect(image)

        if not detection_result.success or detection_result.total_found == 0:
            self._log(f"  멀티포토: 사진 감지 안됨, 단일 모드로 처리", "info")
            # Fall through to standard processing
            debug_base = output_dir if self.settings.debug.enabled else None
            result = processor.process_image(
                input_path,
                debug_dir=debug_base,
                debug_tag="multi_photo_fallback",
            )
            processing_time = (time.time() - start_time) * 1000

            if result.success and result.image is not None:
                return self._save_single_result(
                    result,
                    input_path,
                    output_dir,
                    filename,
                    processing_time,
                    processor,
                    input_root=input_root,
                )
            else:
                return FileResult(
                    filename=filename,
                    status=ProcessStatus.FAILED,
                    message=result.message,
                    processing_time_ms=processing_time,
                )

        # Crop and save each detected photo
        self._log(f"  📷 멀티포토: {detection_result.total_found}개 사진 감지", "info")

        cropped_photos = detector.crop_photos(
            image, detection_result.photos, padding=10
        )

        saved_count = 0
        failed_count = 0
        saved_outputs: List[str] = []
        multi_output_root = self._resolve_multi_photo_output_dir(
            input_path,
            output_dir,
            input_root=input_root,
        )
        target_total = max(int(detection_result.total_found or 0), len(cropped_photos))
        cancelled_midway = False

        for idx, (cropped_img, photo_info) in enumerate(cropped_photos, 1):
            if self._is_stop_requested():
                cancelled_midway = True
                break

            processed_img, resolved_output_dir = self._run_post_pipeline(
                cropped_img,
                multi_output_root,
            )
            output_path = self._build_output_path(
                input_path,
                resolved_output_dir,
                suffix=f"_photo{idx:02d}",
            )

            # Save
            success, msg, file_size = processor.save_image(
                processed_img,
                output_path,
                self.settings.output.output_format,
                self.settings.output.jpg_quality,
                self.settings.output.png_compression,
                self.settings.output.webp_quality,
                source_path=input_path,
                preserve_metadata=self.settings.output.preserve_metadata,
            )

            if success:
                saved_count += 1
                saved_outputs.append(output_path)
                self._log(
                    f"    ✓ 사진 {idx}: {os.path.basename(output_path)}", "success"
                )
            else:
                failed_count += 1
                self._log(f"    Multi-photo save {idx} failed: {msg}", "warning")

        processing_time = (time.time() - start_time) * 1000

        if self._is_stop_requested() and saved_count == 0:
            return FileResult(
                filename=filename,
                status=ProcessStatus.CANCELLED,
                message="작업 취소됨",
                processing_time_ms=processing_time,
            )

        if target_total <= 0:
            target_total = len(cropped_photos)

        total_size_kb = sum(
            (os.path.getsize(path) / 1024.0)
            for path in saved_outputs
            if os.path.exists(path)
        )

        if (
            saved_count > 0
            and failed_count == 0
            and not cancelled_midway
            and saved_count >= target_total
        ):
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"멀티포토: {saved_count}/{detection_result.total_found}개 저장",
                output_path=saved_outputs[0] if saved_outputs else "",
                output_paths=saved_outputs,
                file_size_kb=total_size_kb,
                processing_time_ms=processing_time,
            )
        if saved_count > 0:
            partial_reason = "cancelled" if cancelled_midway else "incomplete"
            return FileResult(
                filename=filename,
                status=ProcessStatus.PARTIAL_SUCCESS,
                message=(
                    f"Multi-photo partial success: {saved_count}/{target_total} saved "
                    f"(failed={failed_count}, status={partial_reason})"
                ),
                output_path=saved_outputs[0] if saved_outputs else "",
                output_paths=saved_outputs,
                file_size_kb=total_size_kb,
                processing_time_ms=processing_time,
            )

        return FileResult(
            filename=filename,
            status=ProcessStatus.FAILED,
            message="멀티포토 저장 실패",
            processing_time_ms=processing_time,
        )
    def _save_single_result(
        self: Any,
        result: CropResult,
        input_path: str,
        output_dir: str,
        filename: str,
        processing_time: float,
        processor: Optional[ImageProcessor] = None,
        input_root: Optional[str] = None,
    ) -> FileResult:
        """Save a single processed result."""
        active_processor = processor or self.processor
        if result.image is None:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message="저장할 이미지가 없습니다",
                processing_time_ms=processing_time,
            )
        base_output_dir = self._resolve_base_output_dir(
            input_path,
            output_dir,
            input_root=input_root,
        )
        processed_image, resolved_output_dir = self._run_post_pipeline(
            result.image,
            base_output_dir,
        )
        output_path = self._build_output_path(
            input_path,
            resolved_output_dir,
            suffix="_cropped",
        )

        success, msg, file_size = active_processor.save_image(
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
            output_paths = [output_path]
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                output_path=output_path,
                output_paths=output_paths,
                file_size_kb=file_size,
                processing_time_ms=processing_time,
            )
        else:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message=f"저장 실패: {msg}",
                processing_time_ms=processing_time,
            )
