#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Perspective correction operations."""

from typing import Optional, Tuple

import cv2
import numpy as np

from .types import PerspectiveResult

class PerspectiveOpsMixin:
    """Perspective operations for AdvancedImageProcessor."""

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order points in consistent order: TL, TR, BR, BL.

        Args:
            pts: Array of 4 points

        Returns:
            Ordered points array
        """
        rect = np.zeros((4, 2), dtype=np.float32)

        # Sum and diff for corner detection
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        rect[0] = pts[np.argmin(s)]      # Top-left
        rect[2] = pts[np.argmax(s)]      # Bottom-right
        rect[1] = pts[np.argmin(diff)]   # Top-right
        rect[3] = pts[np.argmax(diff)]   # Bottom-left

        return rect
    @staticmethod
    def _validate_perspective_points(
        points: np.ndarray,
        image_shape: Tuple[int, int],
    ) -> Tuple[bool, str]:
        """Validate 4-point perspective geometry."""
        if points is None:
            return False, "원근 교정할 포인트가 없습니다"

        try:
            pts = np.array(points, dtype=np.float32).reshape((4, 2))
        except Exception:
            return False, "원근 교정 포인트 형식이 올바르지 않습니다"

        if not np.all(np.isfinite(pts)):
            return False, "원근 교정 포인트에 유효하지 않은 값이 포함되어 있습니다"

        h, w = image_shape[:2]
        if h <= 0 or w <= 0:
            return False, "이미지 크기가 올바르지 않습니다"

        # Duplicate/near-duplicate points.
        for i in range(4):
            for j in range(i + 1, 4):
                if float(np.linalg.norm(pts[i] - pts[j])) < 2.0:
                    return False, "원근 교정 포인트가 서로 너무 가깝거나 중복됩니다"

        # Convexity check.
        contour = pts.reshape((-1, 1, 2)).astype(np.float32)
        if not bool(cv2.isContourConvex(contour)):
            return False, "원근 교정 포인트가 비볼록 사각형입니다"

        # Degenerate polygon area check.
        area = float(cv2.contourArea(contour))
        min_area = max(64.0, (float(w) * float(h)) * 0.0002)
        if area < min_area:
            return False, "원근 교정 영역이 너무 작거나 퇴화되었습니다"

        # Minimum side length check.
        ordered = PerspectiveOpsMixin.order_points(pts)
        side_lengths = []
        for i in range(4):
            p1 = ordered[i]
            p2 = ordered[(i + 1) % 4]
            side_lengths.append(float(np.linalg.norm(p1 - p2)))
        if min(side_lengths) < 5.0:
            return False, "원근 교정 영역의 변 길이가 너무 짧습니다"

        return True, ""
    def correct_perspective(self, image: np.ndarray,
                           src_points: Optional[np.ndarray] = None,
                           auto_detect: bool = True) -> PerspectiveResult:
        """
        Correct perspective distortion.

        Args:
            image: Input image
            src_points: Source corner points (4x2 array). If None, auto-detect.
            auto_detect: Whether to auto-detect corners if src_points is None

        Returns:
            PerspectiveResult with corrected image
        """
        h, w = image.shape[:2]

        if src_points is None and auto_detect:
            # Auto-detect document corners
            src_points = self._detect_document_corners(image)

            if src_points is None:
                return PerspectiveResult(
                    image=image.copy(),
                    src_points=np.array([]),
                    dst_points=np.array([]),
                    success=False,
                    message="문서 코너를 감지할 수 없습니다"
                )

        if src_points is None:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message="원근 교정할 포인트가 지정되지 않았습니다"
            )

        # Order points
        src_points = self.order_points(src_points.astype(np.float32))

        valid, invalid_reason = self._validate_perspective_points(
            src_points, image.shape[:2]
        )
        if not valid:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message=invalid_reason
            )

        # Calculate output dimensions
        width_a = np.linalg.norm(src_points[2] - src_points[3])
        width_b = np.linalg.norm(src_points[1] - src_points[0])
        max_width = int(max(width_a, width_b))

        height_a = np.linalg.norm(src_points[1] - src_points[2])
        height_b = np.linalg.norm(src_points[0] - src_points[3])
        max_height = int(max(height_a, height_b))
        if max_width <= 0 or max_height <= 0:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message="원근 교정 결과 크기가 올바르지 않습니다"
            )

        # Destination points
        dst_points = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)

        # Get perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)

        # Apply transform
        warped = cv2.warpPerspective(
            image, matrix, (max_width, max_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )

        return PerspectiveResult(
            image=warped,
            src_points=src_points,
            dst_points=dst_points,
            success=True,
            message="원근 교정 완료"
        )
    def _detect_document_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Auto-detect document corners for perspective correction.

        Args:
            image: Input image

        Returns:
            4x2 array of corner points or None if detection fails
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape[:2]

        # Blur and edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Find largest contour with 4 corners
        image_area = h * w

        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(contour)

            # Skip if too small or too large
            if area < image_area * 0.1 or area > image_area * 0.98:
                continue

            # Approximate polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            if len(approx) == 4:
                return approx.reshape(4, 2)

        return None

order_points = PerspectiveOpsMixin.order_points
correct_perspective = PerspectiveOpsMixin.correct_perspective

__all__ = ["PerspectiveOpsMixin", "order_points", "correct_perspective"]
