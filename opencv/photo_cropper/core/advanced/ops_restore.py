#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Restoration, denoise, border-crop, and sharpen operations."""

from typing import Any, cast

import cv2
import numpy as np

class RestorationOpsMixin:
    """Restoration operations for AdvancedImageProcessor."""

    def restore_old_photo(self, image: np.ndarray,
                         enhance_contrast: bool = True,
                         reduce_noise: bool = True,
                         restore_colors: bool = True,
                         remove_scratches: bool = True) -> np.ndarray:
        """
        Restore old/damaged photos.

        Apply multiple restoration techniques:
        - Contrast enhancement
        - Noise reduction
        - Color restoration
        - Scratch/damage removal

        Args:
            image: Input image
            enhance_contrast: Apply contrast enhancement
            reduce_noise: Apply noise reduction
            restore_colors: Apply color restoration
            remove_scratches: Attempt to remove scratches

        Returns:
            Restored image
        """
        result = image.copy()

        # Step 1: Noise reduction (before other processing)
        if reduce_noise:
            result = self.denoise_enhanced(result, strength=8)

        # Step 2: Contrast enhancement using CLAHE
        if enhance_contrast:
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Use cached CLAHE from the composed processor.
            l = getattr(self, "_clahe_strong").apply(l)

            lab = cv2.merge([l, a, b])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Step 3: Color restoration
        if restore_colors:
            # Reduce color cast
            result = getattr(self, "auto_color_correct")(result, method="gray_world")

            # Boost saturation slightly
            hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Step 4: Scratch removal using inpainting
        if remove_scratches:
            result = self._remove_scratches(result)

        return result
    def _remove_scratches(self, image: np.ndarray) -> np.ndarray:
        """
        Attempt to detect and remove scratches/damage.

        Uses morphological operations and inpainting.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect thin bright/dark lines (scratches)
        # Bright scratches
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        bright_lines = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)

        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        bright_lines += cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)

        # Threshold to create mask
        threshold_fn = cast(Any, cv2.threshold)
        _, mask = threshold_fn(
            np.asarray(bright_lines, dtype=np.uint8),
            30,
            255,
            cv2.THRESH_BINARY,
        )

        # Dilate mask slightly
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)

        # Check if mask has significant content
        if np.sum(mask) < image.shape[0] * image.shape[1] * 0.001:
            return image  # No significant scratches detected

        # Inpaint
        result = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        return result
    def denoise_enhanced(self, image: np.ndarray,
                        strength: int = 10,
                        preserve_details: bool = True) -> np.ndarray:
        """
        Enhanced denoising with detail preservation.

        Args:
            image: Input image
            strength: Denoising strength (1-20)
            preserve_details: Use bilateral filtering for edge preservation

        Returns:
            Denoised image
        """
        strength = max(1, min(20, strength))
        gpu = getattr(self, "_gpu", None)
        use_gpu = bool(getattr(self, "_use_gpu", False))

        if len(image.shape) != 3:
            # Grayscale
            if use_gpu and gpu is not None and gpu.is_available:
                return gpu.denoise_gpu(
                    cv2.cvtColor(image, cv2.COLOR_GRAY2BGR),
                    h=strength
                )[:, :, 0]
            return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)

        # Color image
        if use_gpu and gpu is not None and gpu.is_available:
            result = gpu.denoise_gpu(image, h=strength)
        else:
            result = cv2.fastNlMeansDenoisingColored(
                image, None, strength, strength, 7, 21
            )

        # Optional: Additional bilateral filtering for edge preservation
        if preserve_details:
            result = cv2.bilateralFilter(result, 5, 50, 50)

        return result
    @staticmethod
    def auto_crop_borders(image: np.ndarray,
                         border_color: str = "auto",
                         threshold: int = 20) -> np.ndarray:
        """
        Automatically crop uniform borders.

        Args:
            image: Input image
            border_color: 'white', 'black', or 'auto'
            threshold: Color difference threshold

        Returns:
            Cropped image
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape

        if border_color == "auto":
            # Detect border color from corners
            corners = [
                gray[0, 0], gray[0, -1],
                gray[-1, 0], gray[-1, -1]
            ]
            avg_corner = np.mean(corners)
            is_white = avg_corner > 127
        else:
            is_white = border_color == "white"

        if is_white:
            mask = gray < (255 - threshold)
        else:
            mask = gray > threshold

        # Find bounding box of non-border content
        coords = np.column_stack(np.where(mask))

        if len(coords) == 0:
            return image.copy()

        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)

        # Add small padding
        padding = 2
        y_min = max(0, y_min - padding)
        x_min = max(0, x_min - padding)
        y_max = min(h - 1, y_max + padding)
        x_max = min(w - 1, x_max + padding)

        return image[y_min:y_max+1, x_min:x_max+1]
    @staticmethod
    def sharpen(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Sharpen image.

        Args:
            image: Input image
            strength: Sharpening strength (0.5-3.0)

        Returns:
            Sharpened image
        """
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ]) * strength

        # Normalize kernel
        kernel[1, 1] = 9 * strength - 8 * strength + 8

        sharpened = cv2.filter2D(image, -1, kernel / kernel.sum() * strength)

        # Blend with original
        alpha = min(1.0, strength / 2)
        result = cv2.addWeighted(image, 1 - alpha, sharpened, alpha, 0)

        return result

restore_old_photo = RestorationOpsMixin.restore_old_photo
denoise_enhanced = RestorationOpsMixin.denoise_enhanced
auto_crop_borders = RestorationOpsMixin.auto_crop_borders
sharpen = RestorationOpsMixin.sharpen

__all__ = [
    "RestorationOpsMixin",
    "restore_old_photo",
    "denoise_enhanced",
    "auto_crop_borders",
    "sharpen",
]
