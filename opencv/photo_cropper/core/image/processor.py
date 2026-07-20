#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Image Processor for Photo Cropper v9.0.

Detection is delegated to ``DetectionPipeline`` (composition). Geometry,
debug I/O, post-process, and save mixins remain on the processor facade.
"""

from __future__ import annotations

from typing import Any, Optional

import cv2
import numpy as np

from ..advanced import AdvancedImageProcessor
from ..settings_model import (
    AdvancedProcessingSettings,
    AlgorithmSettings,
    DebugSettings,
    PerformanceSettings,
    ProcessingSettings,
)
from .debug_io import ImageDebugMixin
from .detection_pipeline import DetectionPipeline
from .geometry import ImageGeometryMixin
from .postprocess import ImagePostprocessMixin
from .save_io import ImageSaveMixin
from .types import CropResult, PreviewProcessResult

import logging

logger = logging.getLogger(__name__)


class ImageProcessor(
    ImageGeometryMixin,
    ImageDebugMixin,
    ImagePostprocessMixin,
    ImageSaveMixin,
):
    """
    Advanced image processor for automatic photo detection and cropping.

    Detection algorithms live in ``self.detection`` (``DetectionPipeline``).
    Public APIs remain stable for GUI/CLI/batch callers.
    """

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
        self.algo = algorithm_settings or AlgorithmSettings()
        self.proc = processing_settings or ProcessingSettings()
        self.advanced = advanced_settings or AdvancedProcessingSettings()
        self.performance = performance_settings or PerformanceSettings()
        self.debug = debug_settings or DebugSettings()

        self._advanced_processor = AdvancedImageProcessor(
            use_gpu=self.performance.use_gpu
        )

        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_custom = None
        self._clahe_settings_cache = (None, None)

        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_5x5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        self._kernel_morph_21x21 = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))

        # Composed detection engine (shares settings/kernels via host lookup).
        self.detection = DetectionPipeline(self)

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

    # --- Detection facade (stable public / internal API) ---

    @staticmethod
    def load_image(image_path: str) -> Optional[np.ndarray]:
        # Keep static API used by CLI/selftests: ImageProcessor.load_image(path)
        return DetectionPipeline.load_image(image_path)  # type: ignore[misc]

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        return self.detection.apply_clahe(image)

    def detect_edges_multiscale(self, gray: np.ndarray) -> np.ndarray:
        return self.detection.detect_edges_multiscale(gray)

    def find_best_contour(self, *args: Any, **kwargs: Any):
        return self.detection.find_best_contour(*args, **kwargs)

    def _process_loaded_image(self, *args: Any, **kwargs: Any) -> CropResult:
        return self.detection._process_loaded_image(*args, **kwargs)

    def _nms_stage_candidates(self, *args: Any, **kwargs: Any):
        return self.detection._nms_stage_candidates(*args, **kwargs)

    def _snap_quad_to_edges(self, *args: Any, **kwargs: Any):
        return self.detection._snap_quad_to_edges(*args, **kwargs)

    def _quad_iou(self, *args: Any, **kwargs: Any) -> float:
        return self.detection._quad_iou(*args, **kwargs)

    def _refine_quad_with_grabcut(self, *args: Any, **kwargs: Any):
        return self.detection._refine_quad_with_grabcut(*args, **kwargs)


__all__ = ["ImageProcessor", "CropResult", "PreviewProcessResult"]
