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
from .context import BatchProcessorContextMixin
from .io_paths import BatchProcessorIoPathsMixin
from .pipeline import BatchProcessorPipelineMixin
from .runner import BatchProcessorRunnerMixin
from .single import BatchProcessorExecutionMixin

logger = logging.getLogger(__name__)


class BatchProcessor(
    BatchProcessorContextMixin,
    BatchProcessorIoPathsMixin,
    BatchProcessorPipelineMixin,
    BatchProcessorRunnerMixin,
    BatchProcessorExecutionMixin,
):
    """
    Batch image processor with threading support.

    Features:
        - Background thread processing
        - Progress callbacks for UI updates
        - Cancellation support
        - Retry failed files
        - Backup creation
    """

    def __init__(self: Any, settings: Optional[AppSettings] = None):
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
        self._output_reservation_lock = threading.Lock()
        self._reserved_output_paths: set[str] = set()
        self._skip_processed_notice_shown = False
        self._processed_index_stores: Dict[str, ProcessedIndexStore] = {}
        self._processed_index_warned_roots: set[str] = set()
        self._pipeline_signature_cache: Optional[str] = None

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










