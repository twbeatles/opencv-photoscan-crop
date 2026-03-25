#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manual extract domain service.

Moves manual-save extraction behavior out of the UI layer so the MainWindow
focuses on orchestration while this service handles extraction policy.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import numpy as np

from ..batch import BatchProcessor, FileResult, ProcessStatus
from ..image import ImageProcessor
from ..settings_model import AppSettings
from .contour_utils import axis_aligned_crop, crop_manual_contour


ContourDenormalizeFn = Callable[[Any, Any], Optional[np.ndarray]]


@dataclass
class ManualExtractOutcome:
    """Single-file manual extract outcome."""

    result: FileResult
    mode_label: str = ""
    notice_message: str = ""
    notice_level: str = "info"


class ManualExtractProcessor:
    """Manual extraction processor with batch-equivalent save policy."""

    def __init__(
        self,
        settings: AppSettings,
        output_path: str,
        denormalize_contour_fn: ContourDenormalizeFn,
    ):
        self.settings = settings
        self.output_path = output_path
        self._denormalize_contour = denormalize_contour_fn

        self._image_processor = ImageProcessor(
            settings.algorithm,
            settings.processing,
            settings.advanced,
            settings.performance,
            debug_settings=settings.debug,
        )
        self._batch_processor = BatchProcessor(settings)
        self._skip_processed_notice_shown = False

    def _axis_aligned_crop(
        self, image: np.ndarray, contour_points: np.ndarray
    ) -> Optional[np.ndarray]:
        """Crop by axis-aligned bounding box of contour points."""
        return axis_aligned_crop(image, contour_points)

    def _check_skip_processed(
        self, path: str, started_at: float
    ) -> Tuple[Optional[FileResult], str]:
        """Return skip result + optional notice message."""
        if not self.settings.filter.skip_processed:
            return None, ""

        index_outputs, index_usable, index_status = self._batch_processor.lookup_processed_outputs_from_index(
            path,
            self.output_path,
        )
        if index_outputs:
            if index_status == "partial":
                return None, "부분 저장 이력이 있어 재처리를 계속 진행합니다."
            filename = os.path.basename(path)
            skip_result = FileResult(
                filename=filename,
                status=ProcessStatus.SKIPPED,
                message="이미 처리됨(인덱스)",
                processing_time_ms=(time.time() - started_at) * 1000.0,
            )
            return skip_result, ""

        if (
            self.settings.file_management.use_naming_rules
            or self.settings.output.add_timestamp
        ):
            if (not index_usable) and (not self._skip_processed_notice_shown):
                self._skip_processed_notice_shown = True
                return (
                    None,
                    "현재 파일명 규칙/타임스탬프 설정으로는 정확한 중복 여부 판별이 어렵습니다.",
                )
            return None, ""

        filename = os.path.basename(path)
        base_name = os.path.splitext(filename)[0]
        ext = "." + self.settings.output.output_format.lower()
        existing = self._batch_processor.find_existing_output(
            base_name,
            ext,
            self.output_path,
            multi_photo=self.settings.multi_photo.enabled,
            input_path=path,
        )
        if existing:
            skip_result = FileResult(
                filename=filename,
                status=ProcessStatus.SKIPPED,
                message="이미 처리됨",
                processing_time_ms=(time.time() - started_at) * 1000.0,
            )
            return skip_result, ""
        return None, ""

    def process_file(
        self,
        path: str,
        contour_norm: Optional[np.ndarray],
    ) -> ManualExtractOutcome:
        """Process one file using manual contour first, auto-detect fallback."""
        started_at = time.time()
        filename = os.path.basename(path)

        skip_result, notice = self._check_skip_processed(path, started_at)
        if skip_result is not None:
            return ManualExtractOutcome(
                result=skip_result,
                mode_label="skip",
                notice_message=notice,
                notice_level="warning" if notice else "info",
            )

        try:
            image = self._image_processor.load_image(path)
            if image is None:
                raise RuntimeError("이미지를 불러올 수 없습니다.")

            used_manual = False
            cropped = None

            contour_valid = False
            if contour_norm is not None:
                try:
                    contour_valid = (
                        len(np.array(contour_norm, dtype=np.float32).reshape((-1, 2)))
                        == 4
                    )
                except Exception:
                    contour_valid = False

            if contour_valid:
                contour_orig = self._denormalize_contour(contour_norm, image.shape)
                if contour_orig is not None:
                    cropped = crop_manual_contour(
                        image,
                        contour_orig,
                        perspective_correct=self.settings.advanced.perspective_correct,
                        use_gpu=self.settings.performance.use_gpu,
                    )
                    used_manual = cropped is not None

            if cropped is not None and used_manual:
                # Keep manual path behavior equivalent to auto path.
                cropped = self._image_processor._apply_post_processing(cropped)

            if cropped is None:
                auto_result = self._image_processor.process_image(path)
                if not auto_result.success or auto_result.image is None:
                    raise RuntimeError(auto_result.message or "외곽선 탐지 실패")
                cropped = auto_result.image

            processed_image, resolved_output_dir = self._batch_processor.apply_post_pipeline(
                cropped,
                self.output_path,
            )
            out_path = self._batch_processor.build_output_path(
                path,
                resolved_output_dir,
                suffix="_cropped",
            )

            ok, save_msg, size_kb = self._image_processor.save_image(
                processed_image,
                out_path,
                output_format=self.settings.output.output_format,
                jpg_quality=self.settings.output.jpg_quality,
                png_compression=self.settings.output.png_compression,
                webp_quality=self.settings.output.webp_quality,
                source_path=path,
                preserve_metadata=self.settings.output.preserve_metadata,
            )
            if not ok:
                raise RuntimeError(save_msg or "저장 실패")

            self._batch_processor.record_processed_outputs(path, self.output_path, [out_path])

            mode_label = "수동" if used_manual else "자동"
            result = FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"{mode_label} 외곽선 적용",
                output_path=out_path,
                output_paths=[out_path],
                file_size_kb=float(size_kb or 0.0),
                processing_time_ms=(time.time() - started_at) * 1000.0,
            )
            return ManualExtractOutcome(
                result=result,
                mode_label=mode_label,
                notice_message=notice,
                notice_level="warning" if notice else "info",
            )
        except Exception as e:
            result = FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message=str(e),
                processing_time_ms=(time.time() - started_at) * 1000.0,
            )
            return ManualExtractOutcome(
                result=result,
                mode_label="",
                notice_message=notice,
                notice_level="warning" if notice else "info",
            )
