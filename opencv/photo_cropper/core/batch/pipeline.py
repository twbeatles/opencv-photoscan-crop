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


class BatchProcessorPipelineMixin:
    def _build_resize_settings(self: Any) -> ResizeProcessorSettings:
        """Build resize processor settings from app settings."""
        try:
            mode = ResizeMode(self.settings.resize.mode)
        except Exception:
            mode = ResizeMode.NONE

        return ResizeProcessorSettings(
            enabled=True,
            mode=mode if self.settings.resize.mode != "none" else ResizeMode.NONE,
            width=self.settings.resize.width,
            height=self.settings.resize.height,
            percentage=self.settings.resize.percentage,
            max_dimension=self.settings.resize.max_dimension,
            upscale_allowed=self.settings.resize.upscale_allowed,
            maintain_aspect=self.settings.resize.maintain_aspect,
            jpeg_compatible=self.settings.resize.jpeg_compatible,
        )
    def _maybe_apply_resize(self: Any, image: np.ndarray) -> np.ndarray:
        """Apply resize settings if enabled."""
        if not self.settings.resize.enabled:
            return image

        try:
            resize_processor = self._get_resize_processor()

            resize_settings = self._build_resize_settings()
            resize_result = resize_processor.resize(image, resize_settings)
            if resize_result.success and resize_result.image is not None:
                self._log(
                    f"  ↔️ 리사이즈 적용: {resize_result.original_size} → {resize_result.new_size}",
                    "info",
                )
                return resize_result.image
        except Exception as e:
            self._log(f"  리사이즈 오류: {e}", "warning")

        return image
    def _ensure_unique_output_path(
        self: Any, path: str, reserved: Optional[set] = None
    ) -> str:
        """Ensure output path is unique against disk and in-flight reservations."""
        lock = getattr(self, "_output_reservation_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._output_reservation_lock = lock
        if not hasattr(self, "_reserved_output_paths"):
            self._reserved_output_paths = set()

        def _key(value: str) -> str:
            return os.path.normcase(os.path.abspath(str(value or "")))

        local_reserved = {_key(item) for item in (reserved or set())}
        with lock:
            reserved_keys = set(getattr(self, "_reserved_output_paths", set()))
            reserved_keys.update(local_reserved)

            candidate = path
            base, ext = os.path.splitext(path)
            counter = 1
            while os.path.exists(candidate) or _key(candidate) in reserved_keys:
                candidate = f"{base}_{counter}{ext}"
                counter += 1

            self._reserved_output_paths.add(_key(candidate))
            return candidate

    def _reset_output_reservations(self: Any) -> None:
        """Clear per-run output reservations."""
        lock = getattr(self, "_output_reservation_lock", None)
        if lock is None:
            self._reserved_output_paths = set()
            return
        with lock:
            self._reserved_output_paths.clear()
    @staticmethod
    def _to_bgr(image: np.ndarray) -> Tuple[np.ndarray, str]:
        """
        Normalize image to BGR for processors that expect 3-channel input.

        Returns:
            (bgr_image, layout) where layout is one of: bgr, gray2d, gray1ch.
        """
        if image is None:
            return image, "bgr"
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), "gray2d"
        if image.ndim == 3 and image.shape[2] == 1:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), "gray1ch"
        return image, "bgr"
    @staticmethod
    def _from_bgr_layout(image_bgr: np.ndarray, layout: str) -> np.ndarray:
        """Restore the channel layout captured by _to_bgr."""
        if image_bgr is None:
            return image_bgr
        if layout == "gray2d":
            return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        if layout == "gray1ch":
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            return gray[:, :, None]
        return image_bgr
    def _maybe_apply_smart_enhancement(self: Any, image: np.ndarray) -> np.ndarray:
        """Apply smart enhancement in batch/watch pipelines if enabled."""
        se = self.settings.smart_enhancement
        if not se.enabled or not se.apply_to_batch:
            return image

        try:
            enhancer = self._get_smart_enhancer()
            working, layout = self._to_bgr(image)
            if working is None:
                return image

            preset = EnhancementPreset.NONE
            if se.auto_preset:
                classifier = self._get_classifier()
                cls_model = getattr(self.settings.classification, "model", "basic")
                classify_result = classifier.classify(working, model=cls_model)
                category_key = classify_result.category.value
                preset = enhancer.recommend_preset(category_key)
            else:
                preset_name = str(getattr(se, "default_preset", "none") or "none").lower()
                try:
                    preset = EnhancementPreset(preset_name)
                except Exception:
                    preset = EnhancementPreset.NONE

            enhanced = enhancer.apply_preset(working, preset).image
            enhanced = enhancer.apply_runtime_adjustments(
                enhanced,
                adjust_exposure=bool(getattr(se, "adjust_exposure", True)),
                adjust_color_balance=bool(getattr(se, "adjust_color_balance", True)),
                strength=int(getattr(se, "strength", 50)),
            )
            self._log(f"  ✨ 스마트 보정 적용: {preset.value}", "info")
            return self._from_bgr_layout(enhanced, layout)
        except Exception as e:
            self._log(f"  스마트 보정 오류: {e}", "warning")
            return image
    def _run_post_pipeline(self: Any, image: np.ndarray, output_dir: str) -> Tuple[np.ndarray, str]:
        """
        Unified post-processing pipeline.

        Order:
            face adjust -> smart enhance -> resize -> classification routing -> watermark.
        """
        processed = self._maybe_apply_face_adjustments(image)
        processed = self._maybe_apply_smart_enhancement(processed)
        processed = self._maybe_apply_resize(processed)

        # Classification should use pre-watermark pixels.
        resolved_output_dir = self._resolve_output_dir_for_classification(
            processed,
            output_dir,
        )

        processed = self._maybe_apply_watermark(processed)
        return processed, resolved_output_dir
    def apply_post_pipeline(
        self: Any, image: np.ndarray, output_dir: str
    ) -> Tuple[np.ndarray, str]:
        """
        Public wrapper for unified post-processing pipeline.

        Kept for parity with manual extraction / external reuse.
        """
        return self._run_post_pipeline(image, output_dir)
    def resolve_base_output_dir(
        self: Any,
        input_path: str,
        output_dir: str,
        *,
        input_root: Optional[str] = None,
    ) -> str:
        """Public wrapper for input-root-aware base output directory resolution."""
        return self._resolve_base_output_dir(
            input_path,
            output_dir,
            input_root=input_root,
        )
    def build_output_path_in_resolved_dir(
        self: Any,
        input_path: str,
        output_dir: str,
        suffix: str,
    ) -> str:
        """Build an output path in an already-resolved directory."""
        return self._build_output_path(input_path, output_dir, suffix)
    def build_output_path(
        self: Any,
        input_path: str,
        output_dir: str,
        suffix: str,
        *,
        input_root: Optional[str] = None,
    ) -> str:
        """Public wrapper for output path generation."""
        if (
            self.settings.multi_photo.enabled
            and str(suffix or "").startswith("_photo")
        ):
            effective_output_dir = self._resolve_multi_photo_output_dir(
                input_path,
                output_dir,
                input_root=input_root,
            )
        else:
            effective_output_dir = self._resolve_base_output_dir(
                input_path,
                output_dir,
                input_root=input_root,
            )
        return self._build_output_path(input_path, effective_output_dir, suffix)
    def _maybe_apply_watermark(self: Any, image: np.ndarray) -> np.ndarray:
        """Apply watermark settings if enabled."""
        if not self.settings.watermark.enabled:
            return image

        try:
            watermark_processor = self._get_watermark_processor()
            working, layout = self._to_bgr(image)
            if working is None:
                return image

            # Settings store colors as RGB; OpenCV functions use BGR.
            r = int(getattr(self.settings.watermark, "text_color_r", 255))
            g = int(getattr(self.settings.watermark, "text_color_g", 255))
            b = int(getattr(self.settings.watermark, "text_color_b", 255))
            color_bgr = (b, g, r)
            font_path = getattr(self.settings.watermark, "text_font_path", "") or ""

            # Tiled watermark takes precedence
            if self.settings.watermark.tiled and self.settings.watermark.text:
                working = watermark_processor.create_tiled_watermark(
                    working,
                    self.settings.watermark.text,
                    spacing=self.settings.watermark.tile_spacing,
                    angle=self.settings.watermark.tile_angle,
                    font_scale=self.settings.watermark.text_font_scale,
                    font_path=font_path,
                    color=color_bgr,
                    opacity=self.settings.watermark.opacity,
                )
                self._log("  타일 워터마크 적용", "info")
                return self._from_bgr_layout(working, layout)

            # Image watermark
            if self.settings.watermark.image_path:
                image_settings = ImageWatermarkSettings(
                    image_path=self.settings.watermark.image_path,
                    scale=self.settings.watermark.image_scale,
                    opacity=self.settings.watermark.opacity,
                    position=WatermarkPosition(self.settings.watermark.position),
                    margin=self.settings.watermark.margin,
                )
                working = watermark_processor.apply_image_watermark(
                    working, image_settings
                )
                self._log("  이미지 워터마크 적용", "info")

            # Text watermark
            if self.settings.watermark.text:
                text_settings = TextWatermarkSettings(
                    text=self.settings.watermark.text,
                    font_path=font_path,
                    font_scale=self.settings.watermark.text_font_scale,
                    color=color_bgr,
                    opacity=self.settings.watermark.opacity,
                    position=WatermarkPosition(self.settings.watermark.position),
                    margin=self.settings.watermark.margin,
                    shadow=self.settings.watermark.text_shadow,
                )
                working = watermark_processor.apply_text_watermark(working, text_settings)
                self._log(
                    f"  텍스트 워터마크 적용: '{self.settings.watermark.text}'",
                    "info",
                )

        except Exception as e:
            self._log(f"  워터마크 오류: {e}", "warning")
            return image

        return self._from_bgr_layout(working, layout)
    def _maybe_apply_face_adjustments(self: Any, image: np.ndarray) -> np.ndarray:
        """Apply face-based auto crop/rotate if enabled."""
        if not self.settings.face_detection.enabled:
            return image

        try:
            detector = self._get_face_detector()
            working, layout = self._to_bgr(image)
            if working is None:
                return image

            detect_eyes = self.settings.face_detection.detect_eyes
            detect_result = detector.detect(
                working,
                detect_eyes=detect_eyes,
                suggest_crop=self.settings.face_detection.auto_center_crop,
            )

            if not detect_result.has_faces:
                return image

            adjusted = working
            if (
                self.settings.face_detection.auto_center_crop
                and detect_result.suggested_crop is not None
            ):
                x, y, w, h = detect_result.suggested_crop
                if w > 0 and h > 0:
                    adjusted = adjusted[y : y + h, x : x + w].copy()

            if self.settings.face_detection.auto_rotate and detect_eyes:
                rotate_result = detector.detect(
                    adjusted,
                    detect_eyes=True,
                    suggest_crop=False,
                )
                if abs(rotate_result.rotation_angle) > 0.5:
                    adjusted = detector.rotate_to_align_eyes(
                        adjusted,
                        -rotate_result.rotation_angle,
                    )

            self._log(f"  👤 얼굴 보정 적용: {len(detect_result.faces)}개 얼굴", "info")
            return self._from_bgr_layout(adjusted, layout)

        except Exception as e:
            self._log(f"  얼굴 보정 오류: {e}", "warning")
            return image
