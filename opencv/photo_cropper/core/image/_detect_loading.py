from __future__ import annotations

import logging
from typing import Any, Optional

import cv2
import numpy as np

from ...utils.image_io import load_image_unicode

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
            return load_image_unicode(
                image_path,
                cv2.IMREAD_COLOR,
                normalize_exif=True,
            )
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
        l_ch, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        l_ch = clahe.apply(l_ch)

        # Merge and convert back
        lab = cv2.merge([l_ch, a, b])
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
