#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facade for advanced image processing operations."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .gpu import GPUAccelerator
from .ops_color import ColorOpsMixin
from .ops_deskew import DeskewOpsMixin
from .ops_perspective import PerspectiveOpsMixin
from .ops_restore import RestorationOpsMixin
from .ops_rotate import RotateOpsMixin
from .types import DeskewResult, PerspectiveResult


class AdvancedImageProcessor(
    RotateOpsMixin,
    DeskewOpsMixin,
    PerspectiveOpsMixin,
    ColorOpsMixin,
    RestorationOpsMixin,
):
    """Advanced image processing algorithms composed from focused mixins."""

    def __init__(self, use_gpu: bool = False):
        """Initialize processor.
        
        Args:
            use_gpu: Whether to use GPU acceleration when available
        """
        self._use_gpu = use_gpu
        self._gpu: Optional[GPUAccelerator] = GPUAccelerator() if use_gpu else None
        
        # Performance: Cached CLAHE objects
        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_strong = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Performance: Cached morphology kernels
        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_line_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        self._kernel_line_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))

    def gpu_available(self) -> bool:
        """Check if GPU is available."""
        return self._gpu is not None and self._gpu.is_available


# Convenience singleton instance
_processor: Optional[AdvancedImageProcessor] = None


def get_advanced_processor(use_gpu: bool = False) -> AdvancedImageProcessor:
    """Get or create advanced processor instance."""
    global _processor
    if _processor is None or _processor._use_gpu != use_gpu:
        _processor = AdvancedImageProcessor(use_gpu=use_gpu)
    return _processor


__all__ = [
    "AdvancedImageProcessor",
    "DeskewResult",
    "GPUAccelerator",
    "PerspectiveResult",
    "get_advanced_processor",
]
