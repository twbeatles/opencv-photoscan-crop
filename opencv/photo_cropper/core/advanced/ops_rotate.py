#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Free-angle rotation operations."""

from typing import Tuple

import cv2
import numpy as np

class RotateOpsMixin:
    """Rotation operations for AdvancedImageProcessor."""

    @staticmethod
    def rotate_free(image: np.ndarray, angle: float,
                    background_color: Tuple[int, int, int] = (255, 255, 255),
                    expand: bool = True) -> np.ndarray:
        """
        Rotate image by arbitrary angle.

        Args:
            image: Input image
            angle: Rotation angle in degrees (positive = counter-clockwise)
            background_color: Background fill color (BGR)
            expand: If True, expand canvas to fit rotated image

        Returns:
            Rotated image
        """
        if abs(angle) < 0.01:
            return image.copy()

        h, w = image.shape[:2]
        center = (w / 2, h / 2)

        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        if expand:
            # Calculate new bounding box size
            cos = np.abs(rotation_matrix[0, 0])
            sin = np.abs(rotation_matrix[0, 1])
            new_w = int(h * sin + w * cos)
            new_h = int(h * cos + w * sin)

            # Adjust rotation matrix for new center
            rotation_matrix[0, 2] += (new_w - w) / 2
            rotation_matrix[1, 2] += (new_h - h) / 2

            output_size = (new_w, new_h)
        else:
            output_size = (w, h)

        # Perform rotation
        rotated = cv2.warpAffine(
            image, rotation_matrix, output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=background_color
        )

        return rotated


rotate_free = RotateOpsMixin.rotate_free

__all__ = ["RotateOpsMixin", "rotate_free"]
