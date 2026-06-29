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


class ImageDetectionStageMixin:
    def _create_background_mask(self: Any, gray: np.ndarray) -> np.ndarray:
        """
        Create a foreground mask based on corner background estimation.
        Returns a binary image (uint8 0/255) where foreground is 255.
        """
        h, w = gray.shape[:2]
        patch = max(10, min(20, min(h, w) // 20))

        corners = [
            gray[0:patch, 0:patch],
            gray[0:patch, w - patch : w],
            gray[h - patch : h, 0:patch],
            gray[h - patch : h, w - patch : w],
        ]
        corner_mean = float(np.mean([np.mean(c) for c in corners]))
        is_bright_bg = corner_mean >= 127.0

        k = max(0.0, float(getattr(self.algo, "bg_mask_delta", 30.0)))
        if is_bright_bg:
            thr = max(0.0, corner_mean - k)
            mask = (gray < thr).astype(np.uint8) * 255
        else:
            thr = min(255.0, corner_mean + k)
            mask = (gray > thr).astype(np.uint8) * 255

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel_5x5, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_5x5, iterations=1)
        return mask
    def _build_hough_quad_from_groups(
        self: Any,
        group_a: List[Dict[str, Any]],
        group_b: List[Dict[str, Any]],
        h: int,
        w: int,
        theta_a: float,
        theta_b: float,
    ) -> Optional[np.ndarray]:
        """Build quad from two near-orthogonal Hough line groups."""

        def _line_position(line: Dict[str, Any], theta_deg: float) -> float:
            rad = math.radians(theta_deg)
            nx = -math.sin(rad)
            ny = math.cos(rad)
            x1, y1, x2, y2 = line["segment"]
            mx = (x1 + x2) * 0.5
            my = (y1 + y2) * 0.5
            return float(mx * nx + my * ny)

        if len(group_a) < 2 or len(group_b) < 2:
            return None

        group_a = sorted(group_a, key=lambda ln: ln["length"], reverse=True)[:80]
        group_b = sorted(group_b, key=lambda ln: ln["length"], reverse=True)[:80]

        pos_a = [(float(_line_position(ln, theta_a)), ln) for ln in group_a]
        pos_b = [(float(_line_position(ln, theta_b)), ln) for ln in group_b]
        if len(pos_a) < 2 or len(pos_b) < 2:
            return None

        top = min(pos_a, key=lambda t: t[0])
        bottom = max(pos_a, key=lambda t: t[0])
        left = min(pos_b, key=lambda t: t[0])
        right = max(pos_b, key=lambda t: t[0])

        # Reject degenerate selections.
        if abs(top[0] - bottom[0]) < min(h, w) * 0.18:
            return None
        if abs(left[0] - right[0]) < min(h, w) * 0.18:
            return None

        lt = self._intersect(left[1]["abc"], top[1]["abc"])
        rt = self._intersect(right[1]["abc"], top[1]["abc"])
        rb = self._intersect(right[1]["abc"], bottom[1]["abc"])
        lb = self._intersect(left[1]["abc"], bottom[1]["abc"])
        if not all([lt, rt, rb, lb]):
            return None

        quad = np.array([lt, rt, rb, lb], dtype=np.float32)
        if np.any(np.isnan(quad)):
            return None
        return quad
    def _detect_rectangle_by_hough(self: Any, edges: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect a rectangle using Hough lines as a fallback when contours are broken.
        Returns quad points (4x2) or None.
        """
        if edges is None or edges.size == 0:
            return None

        h, w = edges.shape[:2]
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180.0,
            threshold=80 if self.algo.detection_mode == "accurate" else 120,
            minLineLength=max(30, min(h, w) // 6),
            maxLineGap=15,
        )
        if lines is None or len(lines) == 0:
            return None

        parsed: List[Dict[str, Any]] = []
        for l in lines[:500]:
            x1, y1, x2, y2 = l[0]
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length < 30:
                continue
            ang = math.degrees(math.atan2(dy, dx))
            if ang < 0:
                ang += 180.0
            parsed.append(
                {
                    "segment": (x1, y1, x2, y2),
                    "length": float(length),
                    "angle": float(ang),
                    "abc": self._line_abc(x1, y1, x2, y2),
                }
            )

        if len(parsed) < 4:
            return None

        bin_size = 10.0
        bin_count = int(180 / bin_size)
        bins = [0.0] * bin_count
        for ln in parsed:
            idx = int(ln["angle"] // bin_size) % bin_count
            bins[idx] += float(ln["length"])

        ranked_bins = sorted(range(bin_count), key=lambda i: bins[i], reverse=True)
        for idx in ranked_bins[:4]:
            if bins[idx] <= 0:
                continue

            theta_a = (idx + 0.5) * bin_size
            theta_b = (theta_a + 90.0) % 180.0
            group_a = [
                ln for ln in parsed if self._angle_diff_deg(float(ln["angle"]), theta_a) <= 18.0
            ]
            group_b = [
                ln for ln in parsed if self._angle_diff_deg(float(ln["angle"]), theta_b) <= 18.0
            ]

            quad = self._build_hough_quad_from_groups(
                group_a, group_b, h, w, theta_a, theta_b
            )
            if quad is not None:
                return quad

        return None
    def detect_edges_multiscale(self: Any, gray: np.ndarray) -> np.ndarray:
        """
        Multi-scale Canny edge detection.

        Args:
            gray: Grayscale image

        Returns:
            Combined edge image
        """
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.algo.multi_scale_edge:
            # Low threshold edges (more sensitive)
            edges_low = cv2.Canny(
                blurred, int(self.algo.canny_min * 0.5), int(self.algo.canny_max * 0.5)
            )

            # Normal edges
            edges_normal = cv2.Canny(blurred, self.algo.canny_min, self.algo.canny_max)

            # High threshold edges (less noise)
            edges_high = cv2.Canny(
                blurred, int(self.algo.canny_min * 1.5), int(self.algo.canny_max * 1.5)
            )

            # Combine: prioritize normal, fill with low, validate with high
            edges = cv2.bitwise_or(edges_normal, edges_low)
            edges = cv2.bitwise_and(
                edges, cv2.dilate(edges_high, self._kernel_3x3, iterations=2)
            )

            # If combined is too sparse, use normal
            if cv2.countNonZero(edges) < cv2.countNonZero(edges_normal) * 0.3:
                edges = edges_normal
        else:
            edges = cv2.Canny(blurred, self.algo.canny_min, self.algo.canny_max)

        # Dilate to connect edges
        edges = cv2.dilate(edges, self._kernel_3x3, iterations=1)

        return edges
    def _prepare_detection_image(
        self: Any, image: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Prepare an image for detection-only stages.

        Downscaling affects only contour detection; final crop still uses the
        original full-resolution image.
        """
        if image is None or image.size == 0:
            return image, 1.0

        h, w = image.shape[:2]
        if h <= 0 or w <= 0:
            return image, 1.0

        if not self.performance.downscale_large_images:
            return image, 1.0

        threshold_mp = float(self.performance.downscale_threshold_mp or 50.0)
        threshold_mp = max(1.0, threshold_mp)
        current_mp = (h * w) / 1_000_000.0

        if current_mp <= threshold_mp:
            return image, 1.0

        scale = math.sqrt(threshold_mp / current_mp)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        if new_w >= w and new_h >= h:
            return image, 1.0

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        ratio = w / float(new_w)
        return resized, ratio
