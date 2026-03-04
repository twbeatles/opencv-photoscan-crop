#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Processor for Photo Cropper v9.0.

Handles batch image processing with:
- Multithreading support (ThreadPoolExecutor)
- Progress tracking and cancellation
- Processing log integration
- Advanced image processing features
"""

import os
import shutil
import logging
import threading
import traceback
import time
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
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
    get_image_files,
    classify_failed_files,
    get_unique_filename,
)
from ...utils.processing_log import ProcessingLogger, get_processing_logger
from ...utils.naming_rules import NamingRule, NamingRuleEngine

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class FileResult:
    """Result for individual file processing."""

    filename: str
    status: ProcessStatus
    message: str = ""
    output_path: str = ""
    file_size_kb: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class BatchProgress:
    """Batch processing progress information."""

    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    current_file: str = ""
    is_running: bool = False
    is_cancelled: bool = False
    avg_time_per_file_ms: float = 0.0
    total_time_ms: float = 0.0

    @property
    def percent(self) -> float:
        """Get progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.processed / self.total) * 100

    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        if self.processed == 0:
            return 0.0
        return (self.success / self.processed) * 100

    @property
    def eta_seconds(self) -> float:
        """Estimated time remaining in seconds."""
        if self.processed == 0 or self.avg_time_per_file_ms == 0:
            return 0.0
        remaining = self.total - self.processed
        return (remaining * self.avg_time_per_file_ms) / 1000


class BatchProcessor:
    """
    Batch image processor with threading support.

    Features:
        - Background thread processing
        - Progress callbacks for UI updates
        - Cancellation support
        - Retry failed files
        - Backup creation
    """

    def __init__(self, settings: Optional[AppSettings] = None):
        """
        Initialize batch processor.

        Args:
            settings: Application settings
        """
        self.settings = settings or AppSettings()
        self.processor = ImageProcessor(
            self.settings.algorithm,
            self.settings.processing,
            self.settings.advanced,  # v9.0: Include advanced processing settings
            self.settings.performance,
            debug_settings=self.settings.debug,
        )

        self._progress = BatchProgress()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._processing_thread: Optional[threading.Thread] = None

        # Results tracking
        self._results: List[FileResult] = []
        self._failed_files: List[str] = []

        # Processing logger
        self._processing_logger: Optional[ProcessingLogger] = None

        # Naming rule engine
        self._naming_engine: Optional[NamingRuleEngine] = None
        self._naming_lock = threading.Lock()
        self._skip_processed_notice_shown = False

        # Thread pool for multithreading - dynamic based on CPU cores
        self._executor: Optional[ThreadPoolExecutor] = None
        self._thread_count = self._calculate_optimal_threads()
        self._worker_local = threading.local()

        # Time tracking for ETA
        self._processing_times: List[float] = []
        self._start_time: Optional[float] = None

        # Advanced processor (lazy init)
        self._advanced_processor = None

        # v9.0: Watermark and Resize processors (lazy init)
        self._watermark_processor: Optional[WatermarkProcessor] = None
        self._resize_processor: Optional[ResizeProcessor] = None
        self._multi_photo_detector: Optional[MultiPhotoDetector] = None
        self._face_detector: Optional[FaceDetector] = None
        self._classifier: Optional[ImageClassifier] = None
        self._smart_enhancer: Optional[SmartEnhancer] = None

        # Callbacks
        self._on_progress: Optional[Callable[[BatchProgress], None]] = None
        self._on_file_complete: Optional[Callable[[FileResult], None]] = None
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_complete: Optional[
            Callable[[BatchProgress, List[FileResult]], None]
        ] = None

    def _calculate_optimal_threads(self) -> int:
        """Calculate optimal thread count based on CPU cores and settings."""
        # Get configured thread count from settings
        if (
            hasattr(self.settings, "performance")
            and self.settings.performance.thread_count > 0
        ):
            return min(self.settings.performance.thread_count, os.cpu_count() or 4)

        # Auto-calculate: use CPU count but cap at 8 for I/O bound operations
        cpu_count = os.cpu_count() or 4
        return min(max(2, cpu_count - 1), 8)  # Leave one core free, max 8

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[BatchProgress], None]] = None,
        on_file_complete: Optional[Callable[[FileResult], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[BatchProgress, List[FileResult]], None]] = None,
    ):
        """Set callback functions for progress updates."""
        self._on_progress = on_progress
        self._on_file_complete = on_file_complete
        self._on_log = on_log
        self._on_complete = on_complete

    def update_settings(self, settings: AppSettings):
        """Update processor settings."""
        self.settings = settings
        self.processor.update_settings(
            settings.algorithm,
            settings.processing,
            settings.advanced,  # v9.0: Include advanced processing settings
            settings.performance,
            settings.debug,
        )

        # v9.0: Reset lazy-initialized processors so they use new settings
        self._multi_photo_detector = None
        self._watermark_processor = None
        self._resize_processor = None
        self._face_detector = None
        self._classifier = None
        self._smart_enhancer = None
        self._naming_engine = None
        self._thread_count = self._calculate_optimal_threads()
        self._worker_local = threading.local()

    def _use_thread_local_context(self) -> bool:
        """Check if per-thread processor context should be used."""
        return (
            self.settings.performance.enable_multithreading and self._thread_count > 1
        )

    def _get_worker_context(self) -> Dict[str, Any]:
        """Get or create thread-local worker context."""
        context = getattr(self._worker_local, "context", None)
        if context is None:
            context = {}
            self._worker_local.context = context
        return context

    def _get_worker_processor(self) -> ImageProcessor:
        if not self._use_thread_local_context():
            return self.processor

        context = self._get_worker_context()
        processor = context.get("processor")
        if processor is None:
            processor = ImageProcessor(
                self.settings.algorithm,
                self.settings.processing,
                self.settings.advanced,
                self.settings.performance,
                debug_settings=self.settings.debug,
            )
            context["processor"] = processor
        return processor

    def _get_resize_processor(self) -> ResizeProcessor:
        if not self._use_thread_local_context():
            if self._resize_processor is None:
                self._resize_processor = ResizeProcessor()
            return self._resize_processor

        context = self._get_worker_context()
        processor = context.get("resize_processor")
        if processor is None:
            processor = ResizeProcessor()
            context["resize_processor"] = processor
        return processor

    def _get_watermark_processor(self) -> WatermarkProcessor:
        if not self._use_thread_local_context():
            if self._watermark_processor is None:
                self._watermark_processor = WatermarkProcessor()
            return self._watermark_processor

        context = self._get_worker_context()
        processor = context.get("watermark_processor")
        if processor is None:
            processor = WatermarkProcessor()
            context["watermark_processor"] = processor
        return processor

    def _get_face_detector(self) -> FaceDetector:
        use_dnn = self.settings.face_detection.use_dnn
        min_face_size = int(getattr(self.settings.face_detection, "min_face_size", 30))
        if not self._use_thread_local_context():
            if (
                self._face_detector is None
                or self._face_detector.use_dnn != use_dnn
                or int(getattr(self._face_detector, "min_face_size", 30)) != min_face_size
            ):
                self._face_detector = FaceDetector(
                    use_dnn=use_dnn, min_face_size=min_face_size
                )
            return self._face_detector

        context = self._get_worker_context()
        detector = context.get("face_detector")
        if (
            detector is None
            or detector.use_dnn != use_dnn
            or int(getattr(detector, "min_face_size", 30)) != min_face_size
        ):
            detector = FaceDetector(use_dnn=use_dnn, min_face_size=min_face_size)
            context["face_detector"] = detector
        return detector

    def _get_classifier(self) -> ImageClassifier:
        if not self._use_thread_local_context():
            if self._classifier is None:
                self._classifier = get_classifier()
            return self._classifier

        context = self._get_worker_context()
        classifier = context.get("classifier")
        if classifier is None:
            classifier = ImageClassifier()
            context["classifier"] = classifier
        return classifier

    def _get_smart_enhancer(self) -> SmartEnhancer:
        if not self._use_thread_local_context():
            if self._smart_enhancer is None:
                self._smart_enhancer = SmartEnhancer()
            return self._smart_enhancer

        context = self._get_worker_context()
        enhancer = context.get("smart_enhancer")
        if enhancer is None:
            enhancer = SmartEnhancer()
            context["smart_enhancer"] = enhancer
        return enhancer

    def _get_multi_photo_detector(self) -> MultiPhotoDetector:
        if not self._use_thread_local_context():
            if self._multi_photo_detector is None:
                self._multi_photo_detector = MultiPhotoDetector(
                    min_area_ratio=self.settings.multi_photo.min_area_ratio,
                    max_area_ratio=self.settings.multi_photo.max_area_ratio,
                    min_photos=self.settings.multi_photo.min_photos,
                    max_photos=self.settings.multi_photo.max_photos,
                    merge_distance=self.settings.multi_photo.merge_distance,
                )
            return self._multi_photo_detector

        context = self._get_worker_context()
        detector = context.get("multi_photo_detector")
        if detector is None:
            detector = MultiPhotoDetector(
                min_area_ratio=self.settings.multi_photo.min_area_ratio,
                max_area_ratio=self.settings.multi_photo.max_area_ratio,
                min_photos=self.settings.multi_photo.min_photos,
                max_photos=self.settings.multi_photo.max_photos,
                merge_distance=self.settings.multi_photo.merge_distance,
            )
            context["multi_photo_detector"] = detector
        return detector

    def _log(self, message: str, level: str = "info"):
        """Send log message through callback."""
        # Validate log level
        valid_levels = {"info", "error", "warning", "success", "skip"}
        level = level if level in valid_levels else "info"

        # v9.0: Thread-safe callback invocation
        with self._lock:
            callback = self._on_log
        self._safe_callback(callback, message, level)

        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def _resolve_input_path(self, input_dir: str, file_entry: str) -> Tuple[str, str]:
        """
        Resolve a file entry to an absolute input path and display name.

        Args:
            input_dir: Base input directory
            file_entry: Filename or full/relative path

        Returns:
            Tuple of (input_path, display_name)
        """
        if os.path.isabs(file_entry):
            return file_entry, os.path.basename(file_entry)

        candidate = os.path.join(input_dir, file_entry)
        if os.path.exists(candidate):
            return candidate, os.path.basename(candidate)

        if os.path.exists(file_entry):
            return file_entry, os.path.basename(file_entry)

        return candidate, os.path.basename(candidate)

    def _ensure_naming_engine(self) -> Optional[NamingRuleEngine]:
        """Initialize naming engine if enabled in settings."""
        if not self.settings.file_management.use_naming_rules:
            self._naming_engine = None
            return None

        if self._naming_engine is None:
            rule = NamingRule(
                prefix=self.settings.file_management.naming_prefix,
                suffix=self.settings.file_management.naming_suffix,
                use_counter=self.settings.file_management.naming_use_counter,
                counter_padding=self.settings.file_management.naming_counter_padding,
                use_date=self.settings.file_management.naming_use_date,
                date_format=self.settings.file_management.naming_date_format,
                preserve_original_name=self.settings.file_management.naming_preserve_original,
            )
            self._naming_engine = NamingRuleEngine(rule)

        return self._naming_engine

    def _resolve_multi_photo_output_dir(self, input_path: str, output_dir: str) -> str:
        """Resolve per-input subfolder for multi-photo outputs when enabled."""
        if not (
            self.settings.multi_photo.enabled
            and self.settings.multi_photo.separate_output_folders
        ):
            return output_dir

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        folder_name = f"{base_name}_photos"

        # Avoid duplicate nesting if caller already passed the per-input folder.
        if os.path.basename(os.path.normpath(output_dir)) == folder_name:
            resolved = output_dir
        else:
            resolved = os.path.join(output_dir, folder_name)

        os.makedirs(resolved, exist_ok=True)
        return resolved

    def _build_output_path(self, input_path: str, output_dir: str, suffix: str) -> str:
        """Build output path using naming rules or default scheme."""
        effective_output_dir = output_dir
        if suffix.startswith("_photo"):
            effective_output_dir = self._resolve_multi_photo_output_dir(
                input_path, output_dir
            )

        os.makedirs(effective_output_dir, exist_ok=True)

        output_format = self.settings.output.output_format
        if self.settings.file_management.use_naming_rules:
            engine = self._ensure_naming_engine()
            if engine:
                with self._naming_lock:
                    path = engine.generate_name(
                        input_path,
                        output_dir=effective_output_dir,
                        output_format=output_format,
                    )
                if suffix and suffix != "_cropped":
                    base, ext = os.path.splitext(path)
                    path = self._ensure_unique_output_path(base + suffix + ext)
                return path

        base_name = os.path.splitext(os.path.basename(input_path))[0] + suffix
        extension = "." + output_format.lower()
        return get_unique_filename(
            effective_output_dir,
            base_name,
            extension,
            add_timestamp=self.settings.output.add_timestamp,
        )

    def _build_resize_settings(self) -> ResizeProcessorSettings:
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

    def _maybe_apply_resize(self, image: np.ndarray) -> np.ndarray:
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
        self, path: str, reserved: Optional[set] = None
    ) -> str:
        """Ensure output path is unique against disk and reserved set."""
        reserved = reserved or set()
        if not os.path.exists(path) and path not in reserved:
            return path

        base, ext = os.path.splitext(path)
        counter = 1
        candidate = f"{base}_{counter}{ext}"
        while os.path.exists(candidate) or candidate in reserved:
            counter += 1
            candidate = f"{base}_{counter}{ext}"
        return candidate

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

    def _maybe_apply_smart_enhancement(self, image: np.ndarray) -> np.ndarray:
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

    def _run_post_pipeline(self, image: np.ndarray, output_dir: str) -> Tuple[np.ndarray, str]:
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
        self, image: np.ndarray, output_dir: str
    ) -> Tuple[np.ndarray, str]:
        """
        Public wrapper for unified post-processing pipeline.

        Kept for parity with manual extraction / external reuse.
        """
        return self._run_post_pipeline(image, output_dir)

    def build_output_path(self, input_path: str, output_dir: str, suffix: str) -> str:
        """Public wrapper for output path generation."""
        return self._build_output_path(input_path, output_dir, suffix)

    def _maybe_apply_watermark(self, image: np.ndarray) -> np.ndarray:
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

    def _maybe_apply_face_adjustments(self, image: np.ndarray) -> np.ndarray:
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

    def _resolve_output_dir_for_classification(
        self,
        image: np.ndarray,
        output_dir: str,
    ) -> str:
        """Resolve category subfolder output when classification is enabled."""
        cls_settings = self.settings.classification
        if not cls_settings.enabled or not cls_settings.auto_folder:
            return output_dir

        try:
            classifier = self._get_classifier()
            model = getattr(cls_settings, "model", "basic")
            classify_input, _ = self._to_bgr(image)
            classify_result = classifier.classify(classify_input, model=model)
            category_key = classify_result.category.value
            min_conf = max(0.0, min(1.0, cls_settings.min_confidence))

            if classify_result.confidence < min_conf:
                return output_dir

            enabled_map = cls_settings.categories_enabled or {}
            if not enabled_map.get(category_key, True):
                return output_dir

            category_dir_name = classifier.get_output_folder(classify_result.category)
            classified_output_dir = os.path.join(output_dir, category_dir_name)
            os.makedirs(classified_output_dir, exist_ok=True)
            self._log(
                f"  🤖 분류: {category_key} ({classify_result.confidence:.2f})",
                "info",
            )
            return classified_output_dir
        except Exception as e:
            self._log(f"  이미지 분류 오류: {e}", "warning")
            return output_dir

    def _iter_candidate_output_dirs(
        self,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
    ) -> List[str]:
        """
        Candidate output directories for duplicate probing.

        Includes classification category folders when auto-folder routing is enabled.
        """
        roots: List[str] = [output_dir]
        if multi_photo and input_path:
            roots.append(self._resolve_multi_photo_output_dir(input_path, output_dir))

        dirs: List[str] = []
        for root in roots:
            dirs.append(root)
        cls_settings = self.settings.classification
        if not cls_settings.enabled or not cls_settings.auto_folder:
            return list(dict.fromkeys(dirs))

        try:
            classifier = self._get_classifier()
            enabled_map = cls_settings.categories_enabled or {}
            for category in ImageCategory:
                if enabled_map.get(category.value, True):
                    for root in roots:
                        dirs.append(
                            os.path.join(root, classifier.get_output_folder(category))
                        )
        except Exception:
            # Best-effort: keep base output_dir only.
            pass

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(dirs))

    def _find_existing_output(
        self,
        base_name: str,
        ext: str,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find existing output path for skip-processed checks across candidate dirs.
        """
        for candidate_dir in self._iter_candidate_output_dirs(
            output_dir,
            multi_photo=multi_photo,
            input_path=input_path,
        ):
            expected = os.path.join(candidate_dir, f"{base_name}_cropped{ext}")
            if os.path.exists(expected):
                return expected

            if multi_photo:
                try:
                    prefix = f"{base_name}_photo"
                    if os.path.isdir(candidate_dir):
                        for entry in os.listdir(candidate_dir):
                            if not entry.startswith(prefix):
                                continue
                            candidate_path = os.path.join(candidate_dir, entry)
                            if not os.path.isfile(candidate_path):
                                continue
                            if ext and not entry.lower().endswith(ext.lower()):
                                continue
                            return candidate_path
                except Exception:
                    pass
        return None

    def find_existing_output(
        self,
        base_name: str,
        ext: str,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
    ) -> Optional[str]:
        """Public wrapper for skip-processed duplicate probing."""
        return self._find_existing_output(
            base_name,
            ext,
            output_dir,
            multi_photo=multi_photo,
            input_path=input_path,
        )

    def _safe_callback(self, callback: Optional[Callable], *args, **kwargs):
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
        self, result: FileResult, input_dir: str, filename: str, processed_index: int
    ):
        """Handle result updates, logging, and callbacks."""
        input_file_path = (
            filename if os.path.isabs(filename) else os.path.join(input_dir, filename)
        )
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

    def cleanup(self):
        """Clean up resources and stop threads."""
        self.request_stop()
        if self._executor:
            self._executor.shutdown(wait=False)
        if self._processing_thread and self._processing_thread.is_alive():
            # Thread join is blocking, avoid if calling from UI thread
            pass

    def _update_progress(self):
        """Send progress update through callback."""
        with self._lock:
            progress_copy = BatchProgress(**self._progress.__dict__)
        self._safe_callback(self._on_progress, progress_copy)

    @property
    def is_running(self) -> bool:
        """Check if processing is in progress."""
        with self._lock:
            return self._progress.is_running

    @property
    def progress(self) -> BatchProgress:
        """Get current progress."""
        with self._lock:
            return BatchProgress(**self._progress.__dict__)

    @property
    def failed_files(self) -> List[str]:
        """Get list of failed files."""
        return self._failed_files.copy()

    @property
    def results(self) -> List[FileResult]:
        """Get all processing results."""
        return self._results.copy()

    def request_stop(self):
        """Request processing to stop."""
        self._stop_event.set()
        with self._lock:
            self._progress.is_cancelled = True
        self._log("작업 중단 요청됨", "warning")

    def _is_stop_requested(self) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()

    def get_image_files(self, input_dir: str) -> List[str]:
        """
        Get list of image files in directory.

        Args:
            input_dir: Input directory path

        Returns:
            List of image filenames
        """
        try:
            files = [
                f
                for f in os.listdir(input_dir)
                if f.lower().endswith(SUPPORTED_IMAGE_FORMATS)
            ]
            return sorted(files)
        except Exception as e:
            self._log(f"폴더 읽기 오류: {e}", "error")
            return []

    def start_async(
        self, input_dir: str, output_dir: str, file_list: Optional[List[str]] = None
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

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
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

    def process_single(self, input_path: str, output_dir: str) -> FileResult:
        """Process one file synchronously using the same pipeline as batch mode."""
        if not input_path or not os.path.exists(input_path):
            return FileResult(
                filename=os.path.basename(input_path) if input_path else "",
                status=ProcessStatus.FAILED,
                message="입력 파일이 존재하지 않습니다",
            )

        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return FileResult(
                filename=os.path.basename(input_path),
                status=ProcessStatus.FAILED,
                message=f"출력 폴더 생성 실패: {e}",
            )

        self._stop_event.clear()
        backup_dir = None
        if self.settings.create_backup:
            backup_dir = os.path.join(output_dir, "backup")
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception:
                backup_dir = None

        result = self._process_single_file(
            os.path.dirname(input_path),
            output_dir,
            input_path,
            backup_dir,
            1,
            1,
            None,
        )

        if (
            result.status == ProcessStatus.FAILED
            and self.settings.file_management.move_failed_files
        ):
            try:
                classify_failed_files(
                    [input_path],
                    os.path.dirname(input_path),
                    failed_folder_name=self.settings.file_management.failed_folder_name,
                    copy_mode=self.settings.file_management.copy_failed_instead_of_move,
                )
            except Exception as e:
                self._log(f"실패 파일 분류 중 오류: {e}", "warning")

        return result

    def _process_batch(
        self, input_dir: str, output_dir: str, file_list: Optional[List[str]] = None
    ):
        """Internal batch processing method (runs in thread)."""
        try:
            # Get file list
            if file_list is None:
                if self.settings.file_management.recursive_search:
                    file_list = get_image_files(input_dir, recursive=True)
                else:
                    file_list = self.get_image_files(input_dir)

            if not file_list:
                self._log("처리할 이미지 파일이 없습니다", "warning")
                return

            # Create output directory
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self._log(f"출력 폴더 생성 실패: {e}", "error")
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

            # Initialize naming engine for this batch if enabled
            if self.settings.file_management.use_naming_rules:
                engine = self._ensure_naming_engine()
                if engine:
                    engine.reset_counter()

            # Process each file
            work_items = []
            reserved_outputs = set()
            preview_engine = None

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
                input_path, _ = self._resolve_input_path(input_dir, filename)
                output_path_override = None
                classification_routing = (
                    self.settings.classification.enabled
                    and self.settings.classification.auto_folder
                )
                if not self.settings.multi_photo.enabled and not classification_routing:
                    if preview_engine:
                        output_path_override = preview_engine.generate_name(
                            input_path,
                            output_dir=output_dir,
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
                        output_path_override = os.path.join(output_dir, filename_out)

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
                        )
                        futures[future] = (filename, item_index)
                        pending.add(future)
                        return True

                    while (
                        not self._is_stop_requested()
                        and len(pending) < max_in_flight
                        and submit_next()
                    ):
                        pass

                    processed = 0
                    while pending:
                        done, pending = wait(
                            pending,
                            timeout=0.2,
                            return_when=FIRST_COMPLETED,
                        )

                        if not done:
                            if self._is_stop_requested():
                                for pending_future in pending:
                                    pending_future.cancel()
                                break
                            continue

                        for future in done:
                            processed += 1
                            filename, _ = futures.pop(future, ("", 0))
                            try:
                                result = future.result()
                            except Exception as e:
                                result = FileResult(
                                    filename=os.path.basename(filename),
                                    status=ProcessStatus.FAILED,
                                    message=str(e),
                                )
                            self._handle_result(result, input_dir, filename, processed)

                        while (
                            not self._is_stop_requested()
                            and len(pending) < max_in_flight
                            and submit_next()
                        ):
                            pass

                        if self._is_stop_requested():
                            for pending_future in pending:
                                pending_future.cancel()
                            break
                finally:
                    for pending_future in pending:
                        pending_future.cancel()
                    if self._executor is not None:
                        self._executor.shutdown(wait=True)
                        self._executor = None
            else:
                for i, (filename, output_path_override) in enumerate(work_items, 1):
                    if self._is_stop_requested():
                        self._log("작업이 중단되었습니다", "warning")
                        break

                    result = self._process_single_file(
                        input_dir,
                        output_dir,
                        filename,
                        backup_dir,
                        i,
                        total,
                        output_path_override,
                    )
                    self._handle_result(result, input_dir, filename, i)

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
                f"실패: {progress.failed}, 건너뜀: {progress.skipped}",
                "info",
            )

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
                    )
                    if moved_count > 0:
                        self._log(f"실패 파일 {moved_count}개 분류 완료", "info")
                    if errors:
                        self._log(f"실패 파일 분류 오류: {len(errors)}건", "warning")
                except Exception as e:
                    self._log(f"실패 파일 분류 중 오류: {e}", "warning")

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self._log(f"배치 처리 오류: {e}", "error")
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

    def _process_single_file(
        self,
        input_dir: str,
        output_dir: str,
        filename: str,
        backup_dir: Optional[str],
        current: int,
        total: int,
        output_path_override: Optional[str] = None,
    ) -> FileResult:
        """Process a single file."""
        start_time = time.time()

        if self._is_stop_requested():
            return FileResult(
                filename=os.path.basename(filename),
                status=ProcessStatus.CANCELLED,
                message="작업 취소됨",
            )

        input_path, display_name = self._resolve_input_path(input_dir, filename)

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
            if output_path_override is not None:
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
            elif (
                self.settings.file_management.use_naming_rules
                or self.settings.output.add_timestamp
            ):
                if not self._skip_processed_notice_shown:
                    self._log(
                        "현재 파일명 규칙/타임스탬프 설정으로는 정확한 중복 여부 판별이 어렵습니다.",
                        "warning",
                    )
                    self._skip_processed_notice_shown = True
            else:
                base_name = os.path.splitext(display_name)[0]
                ext = "." + self.settings.output.output_format.lower()
                existing = self._find_existing_output(
                    base_name,
                    ext,
                    output_dir,
                    multi_photo=self.settings.multi_photo.enabled,
                    input_path=input_path,
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
                backup_path = os.path.join(backup_dir, display_name)
                shutil.copy2(input_path, backup_path)
            except Exception as e:
                self._log(f"  백업 실패: {e}", "warning")

        # v9.0: Multi-photo detection mode
        if self.settings.multi_photo.enabled:
            try:
                return self._process_multi_photo(
                    input_path,
                    output_dir,
                    display_name,
                    current,
                    total,
                    start_time,
                    processor,
                )
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
                output_dir,
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
                return FileResult(
                    filename=display_name,
                    status=ProcessStatus.SUCCESS,
                    message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                    output_path=output_path,
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

    def _process_multi_photo(
        self,
        input_path: str,
        output_dir: str,
        filename: str,
        current: int,
        total: int,
        start_time: float,
        processor: ImageProcessor,
    ) -> FileResult:
        """
        Process a single file with multi-photo detection.
        Detects multiple photos in a single scan and saves each separately.
        """
        import cv2
        import numpy as np

        detector = self._get_multi_photo_detector()

        # Load image with Unicode support
        img_array = np.fromfile(input_path, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

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
        multi_output_root = self._resolve_multi_photo_output_dir(input_path, output_dir)

        for idx, (cropped_img, photo_info) in enumerate(cropped_photos, 1):
            if self._is_stop_requested():
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
                self._log(
                    f"    ✓ 사진 {idx}: {os.path.basename(output_path)}", "success"
                )

        processing_time = (time.time() - start_time) * 1000

        if self._is_stop_requested() and saved_count == 0:
            return FileResult(
                filename=filename,
                status=ProcessStatus.CANCELLED,
                message="작업 취소됨",
                processing_time_ms=processing_time,
            )

        if saved_count > 0:
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"멀티포토: {saved_count}/{detection_result.total_found}개 저장",
                processing_time_ms=processing_time,
            )
        else:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message="멀티포토 저장 실패",
                processing_time_ms=processing_time,
            )

    def _save_single_result(
        self,
        result: CropResult,
        input_path: str,
        output_dir: str,
        filename: str,
        processing_time: float,
        processor: Optional[ImageProcessor] = None,
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
        processed_image, resolved_output_dir = self._run_post_pipeline(
            result.image,
            output_dir,
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
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                output_path=output_path,
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
