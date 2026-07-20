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


class BatchProcessorContextMixin:
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
        self: Any,
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
    def update_settings(self: Any, settings: AppSettings):
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
        self._pipeline_signature_cache = None
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
    def _get_worker_processor(self: Any) -> ImageProcessor:
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
    def _build_multi_photo_detector(self) -> MultiPhotoDetector:
        """Build detector with explicit typed kwargs (avoid mixed dict for pyright)."""
        algo = self.settings.algorithm
        mp = self.settings.multi_photo
        return MultiPhotoDetector(
            min_area_ratio=float(mp.min_area_ratio),
            max_area_ratio=float(mp.max_area_ratio),
            min_photos=int(mp.min_photos),
            max_photos=int(mp.max_photos),
            merge_distance=int(mp.merge_distance),
            canny_min=int(getattr(algo, "canny_min", 50)),
            canny_max=int(getattr(algo, "canny_max", 150)),
            adaptive_block_size=int(getattr(algo, "adaptive_block_size", 11)),
            adaptive_c=float(getattr(algo, "adaptive_c", 2.0)),
        )

    def _get_multi_photo_detector(self) -> MultiPhotoDetector:
        if not self._use_thread_local_context():
            if self._multi_photo_detector is None:
                self._multi_photo_detector = self._build_multi_photo_detector()
            return self._multi_photo_detector

        context = self._get_worker_context()
        detector = context.get("multi_photo_detector")
        if detector is None:
            detector = self._build_multi_photo_detector()
            context["multi_photo_detector"] = detector
        return detector
    def _log(self: Any, message: str, level: str = "info"):
        """Send log message through callback."""
        # Validate log level
        valid_levels = {"info", "error", "warning", "success", "skip", "partial"}
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
