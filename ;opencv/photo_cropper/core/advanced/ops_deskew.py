#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Deskew detection and correction operations."""

import logging

import cv2
import numpy as np

from .ops_rotate import RotateOpsMixin
from .types import DeskewResult

logger = logging.getLogger(__name__)

class DeskewOpsMixin:
    """Deskew operations for AdvancedImageProcessor."""

    def auto_deskew(self, image: np.ndarray,
                    max_angle: float = 45.0,
                    min_confidence: float = 0.3) -> DeskewResult:
        """
        Automatically detect and correct image skew.

        Optimization: Detects angle on downscaled image for performance.

        Args:
            image: Input image
            max_angle: Maximum allowed skew angle
            min_confidence: Minimum confidence threshold

        Returns:
            DeskewResult with corrected image and detected angle
        """
        h, w = image.shape[:2]

        # Optimization: Downscale for detection if image is large
        # This significantly speeds up Hough Transform
        max_dim = 1000
        scale = 1.0

        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            detect_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            detect_img = image

        # Convert to grayscale
        if len(detect_img.shape) == 3:
            gray = cv2.cvtColor(detect_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = detect_img.copy()

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Dilate to connect broken edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Hough Line Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=min(gray.shape) // 10,
            maxLineGap=10
        )

        if lines is None or len(lines) == 0:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)

        # Calculate angles of detected lines
        angles = []
        weights = []  # Line length as weight

        for line in lines:
            line_points = np.asarray(line).reshape(-1)
            if line_points.size < 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in line_points[:4]]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            if x2 - x1 == 0:
                angle = 90.0
            else:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

            # Normalize angle to -45 to 45 range
            while angle > 45:
                angle -= 90
            while angle < -45:
                angle += 90

            if abs(angle) <= max_angle:
                angles.append(angle)
                weights.append(length)

        if not angles:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)

        # Calculate weighted average angle
        weights = np.array(weights)
        angles = np.array(angles)
        total_weight = np.sum(weights)

        if total_weight == 0:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)

        avg_angle = np.sum(angles * weights) / total_weight

        # Calculate confidence based on angle consistency
        angle_std = np.sqrt(np.sum(weights * (angles - avg_angle) ** 2) / total_weight)
        confidence = max(0.0, 1.0 - angle_std / 15.0)

        # Skip if angle is too small or confidence is low
        if abs(avg_angle) < 0.5 or confidence < min_confidence:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=confidence)

        # Rotate original full-resolution image
        # Use simple rotation for speed if GPU not available
        corrected = RotateOpsMixin.rotate_free(image, avg_angle, expand=True)

        logger.info(f"Auto deskew: {avg_angle:.2f}° (confidence: {confidence:.2f})")

        return DeskewResult(
            image=corrected,
            angle=avg_angle,
            confidence=confidence
        )


auto_deskew = DeskewOpsMixin.auto_deskew

__all__ = ["DeskewOpsMixin", "auto_deskew"]
