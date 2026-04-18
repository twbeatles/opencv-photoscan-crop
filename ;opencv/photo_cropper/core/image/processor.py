#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Image Processor for Photo Cropper v9.0.

Provides advanced CV algorithms for automatic photo detection and cropping:
- Multi-scale Canny edge detection
- CLAHE contrast enhancement
- Adaptive threshold for textured backgrounds
- Gradient analysis (Sobel)
- Enhanced contour scoring
- v8.0: Advanced processing (deskew, color correct, perspective, etc.)
"""

import os
import cv2
import numpy as np
import logging
import traceback
import json
import time
import math
from typing import Optional, Tuple, List, Dict, Any

from ..settings_model import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
    DebugSettings,
)
from ..advanced import AdvancedImageProcessor, GPUAccelerator
from .types import CropResult, DetectionStage, PreviewProcessResult
from .debug_io import ImageDebugMixin
from .detect import ImageDetectionMixin
from .geometry import ImageGeometryMixin
from .postprocess import ImagePostprocessMixin
from .save_io import ImageSaveMixin

logger = logging.getLogger(__name__)

class ImageProcessor(
    ImageGeometryMixin,
    ImageDebugMixin,
    ImageDetectionMixin,
    ImagePostprocessMixin,
    ImageSaveMixin,
):
    """
    Advanced image processor for automatic photo detection and cropping.

    Features:
        - 3+ stage intelligent photo detection
        - CLAHE for improved contrast handling
        - Multi-scale edge detection
        - Enhanced contour scoring algorithm
        - Perspective transform for skewed photos
    """

    # Constants
    SUPPORTED_FORMATS = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".webp",
    )
    MIN_IMAGE_SIZE = 100
    RESIZE_TARGET_DIM = 1000
    RESIZE_THRESHOLD = 1500
    DEFAULT_BILATERAL_D = 9
    DEFAULT_BILATERAL_SIGMA = 75
    MIN_CONTOUR_AREA = 100
    MIN_CROP_SIZE = 50
    PREVIEW_DETECTION_MAX_MP = 8.0

    def __init__(
        self: Any,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
        debug_settings: Optional[DebugSettings] = None,
    ):
        """
        Initialize image processor.

        Args:
            algorithm_settings: Algorithm configuration
            processing_settings: Post-processing configuration
            advanced_settings: v8.0 Advanced processing settings
        """
        self.algo = algorithm_settings or AlgorithmSettings()
        self.proc = processing_settings or ProcessingSettings()
        self.advanced = advanced_settings or AdvancedProcessingSettings()
        self.performance = performance_settings or PerformanceSettings()
        self.debug = debug_settings or DebugSettings()

        # v8.0: Advanced processor
        self._advanced_processor = AdvancedImageProcessor(
            use_gpu=self.performance.use_gpu
        )

        # Performance: Cached CLAHE objects
        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_custom = None  # Lazy initialized with custom settings
        self._clahe_settings_cache = (None, None)  # (clip_limit, grid_size)

        # Performance: Cached kernels
        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_5x5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        self._kernel_morph_21x21 = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))

    def update_settings(
        self: Any,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
        debug_settings: Optional[DebugSettings] = None,
    ):
        """Update processor settings."""
        if algorithm_settings:
            self.algo = algorithm_settings
        if processing_settings:
            self.proc = processing_settings
        if advanced_settings:
            self.advanced = advanced_settings
        if performance_settings:
            gpu_changed = self.performance.use_gpu != performance_settings.use_gpu
            self.performance = performance_settings
            if gpu_changed:
                self._advanced_processor = AdvancedImageProcessor(
                    use_gpu=self.performance.use_gpu
                )
        if debug_settings:
            self.debug = debug_settings











































