# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

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

logger = logging.getLogger(__name__)


class ImageLoadAndClaheMixin:
    @staticmethod
    def load_image(image_path: str) -> Optional[np.ndarray]:
        """
        Load image with Unicode path support.

        Args:
            image_path: Path to image file

        Returns:
            Loaded image array or None if failed
        """
        try:
            # Prefer Pillow path for EXIF orientation normalization.
            try:
                from PIL import Image, ImageOps

                with Image.open(image_path) as pil_image:
                    pil_image = ImageOps.exif_transpose(pil_image)
                    if pil_image.mode != "RGB":
                        pil_image = pil_image.convert("RGB")
                    rgb = np.array(pil_image)
                    if rgb.ndim == 3 and rgb.shape[2] == 3:
                        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            except Exception as pil_err:
                logger.debug("Pillow load fallback for '%s': %s", image_path, pil_err)

            # Fallback: Unicode-safe OpenCV loading.
            img_array = np.fromfile(image_path, np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None
    def apply_clahe(self: Any, image: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input BGR image

        Returns:
            Contrast-enhanced image
        """
        if not self.algo.use_clahe:
            return image

        # Get or create CLAHE object with current settings
        clahe = self._get_clahe_with_settings(
            self.algo.clahe_clip_limit, self.algo.clahe_grid_size
        )

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        l = clahe.apply(l)

        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    def _get_clahe_with_settings(self: Any, clip_limit: float, grid_size: int):
        """Get cached CLAHE object or create new one if settings changed."""
        if (
            self._clahe_settings_cache == (clip_limit, grid_size)
            and self._clahe_custom is not None
        ):
            return self._clahe_custom

        # Create new CLAHE with updated settings
        self._clahe_custom = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(grid_size, grid_size)
        )
        self._clahe_settings_cache = (clip_limit, grid_size)
        return self._clahe_custom
