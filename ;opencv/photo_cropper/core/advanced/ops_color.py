#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Automatic color correction operations."""

import cv2
import numpy as np

class ColorOpsMixin:
    """Color operations for AdvancedImageProcessor."""

    @staticmethod
    def auto_color_correct(image: np.ndarray,
                          method: str = "gray_world") -> np.ndarray:
        """
        Automatic color correction.

        Args:
            image: Input image (BGR)
            method: Correction method ('gray_world', 'white_patch', 'histogram')

        Returns:
            Color-corrected image
        """
        if len(image.shape) != 3:
            return image.copy()

        if method == "gray_world":
            return ColorOpsMixin._gray_world_correction(image)
        elif method == "white_patch":
            return ColorOpsMixin._white_patch_correction(image)
        elif method == "histogram":
            return ColorOpsMixin._histogram_correction(image)
        else:
            return image.copy()
    @staticmethod
    def _gray_world_correction(image: np.ndarray) -> np.ndarray:
        """Gray World white balance algorithm."""
        result = image.copy().astype(np.float32)

        # Calculate mean of each channel
        avg_b = np.mean(result[:, :, 0])
        avg_g = np.mean(result[:, :, 1])
        avg_r = np.mean(result[:, :, 2])

        # Calculate overall average
        avg_gray = (avg_b + avg_g + avg_r) / 3

        # Scale factors
        if avg_b > 0:
            result[:, :, 0] *= avg_gray / avg_b
        if avg_g > 0:
            result[:, :, 1] *= avg_gray / avg_g
        if avg_r > 0:
            result[:, :, 2] *= avg_gray / avg_r

        return np.clip(result, 0, 255).astype(np.uint8)
    @staticmethod
    def _white_patch_correction(image: np.ndarray) -> np.ndarray:
        """White Patch (Max-RGB) white balance algorithm."""
        result = image.copy().astype(np.float32)

        # Find maximum values in each channel
        max_b = np.percentile(result[:, :, 0], 99)
        max_g = np.percentile(result[:, :, 1], 99)
        max_r = np.percentile(result[:, :, 2], 99)

        # Scale to white
        if max_b > 0:
            result[:, :, 0] *= 255.0 / max_b
        if max_g > 0:
            result[:, :, 1] *= 255.0 / max_g
        if max_r > 0:
            result[:, :, 2] *= 255.0 / max_r

        return np.clip(result, 0, 255).astype(np.uint8)
    @staticmethod
    def _histogram_correction(image: np.ndarray) -> np.ndarray:
        """Histogram-based color correction."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

auto_color_correct = ColorOpsMixin.auto_color_correct

__all__ = ["ColorOpsMixin", "auto_color_correct"]
