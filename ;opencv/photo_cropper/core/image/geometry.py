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


class ImageGeometryMixin:
    @staticmethod
    def rotate_image(image: np.ndarray, angle: int) -> np.ndarray:
        """
        Rotate image by 90 degree increments.

        Args:
            image: Input image array
            angle: Rotation angle (90, 180, 270 or -90)

        Returns:
            Rotated image array
        """
        angle = angle % 360
        if angle == 90 or angle == -270:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180 or angle == -180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270 or angle == -90:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image
    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order four points in consistent order: TL, TR, BR, BL.

        Args:
            pts: Array of 4 points

        Returns:
            Ordered points array
        """
        rect = np.zeros((4, 2), dtype="float32")

        # Sum: smallest = TL, largest = BR
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # Top-left
        rect[2] = pts[np.argmax(s)]  # Bottom-right

        # Diff: smallest = TR, largest = BL
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # Top-right
        rect[3] = pts[np.argmax(diff)]  # Bottom-left

        return rect
    def _quad_is_convex(self: Any, quad: np.ndarray) -> bool:
        try:
            cnt = quad.reshape((-1, 1, 2)).astype(np.int32)
            return bool(cv2.isContourConvex(cnt))
        except Exception:
            return False
    def _quad_area(self: Any, quad: np.ndarray) -> float:
        try:
            return float(cv2.contourArea(quad.reshape((-1, 1, 2)).astype(np.float32)))
        except Exception:
            return 0.0
    def _quad_min_side(self: Any, quad: np.ndarray) -> float:
        q = quad.reshape((4, 2)).astype(np.float32)
        d = []
        for i in range(4):
            p1 = q[i]
            p2 = q[(i + 1) % 4]
            d.append(float(np.linalg.norm(p1 - p2)))
        return min(d) if d else 0.0
    def _quad_aspect_ratio(self: Any, quad: np.ndarray) -> float:
        """Estimate aspect ratio from quad side lengths (orientation invariant)."""
        q = self.order_points(quad.reshape((4, 2)).astype(np.float32))
        w_top = float(np.linalg.norm(q[1] - q[0]))
        w_bottom = float(np.linalg.norm(q[2] - q[3]))
        h_left = float(np.linalg.norm(q[3] - q[0]))
        h_right = float(np.linalg.norm(q[2] - q[1]))
        width = max(1e-6, (w_top + w_bottom) * 0.5)
        height = max(1e-6, (h_left + h_right) * 0.5)
        return float(width / height)
    @staticmethod
    def _angle_diff_deg(a: float, b: float) -> float:
        """Smallest difference between two undirected angles in degrees (0..90)."""
        d = abs((a - b) % 180.0)
        return float(d if d <= 90.0 else 180.0 - d)
    def _area_score(self: Any, area_ratio: float, min_ratio: float, max_ratio: float) -> float:
        """
        Area prior with a central plateau and smooth edge falloff.
        Returns 0..1.
        """
        if area_ratio < min_ratio or area_ratio > max_ratio:
            return 0.0

        span = max(1e-6, max_ratio - min_ratio)
        plateau_margin = span * 0.20
        plateau_low = min_ratio + plateau_margin
        plateau_high = max_ratio - plateau_margin

        # Very narrow span fallback: symmetric center score.
        if plateau_high <= plateau_low:
            mid = (min_ratio + max_ratio) * 0.5
            half = max(1e-6, span * 0.5)
            return float(max(0.0, 1.0 - abs(area_ratio - mid) / half))

        if plateau_low <= area_ratio <= plateau_high:
            return 1.0

        if area_ratio < plateau_low:
            dist = plateau_low - area_ratio
            denom = max(1e-6, plateau_low - min_ratio)
        else:
            dist = area_ratio - plateau_high
            denom = max(1e-6, max_ratio - plateau_high)

        linear = max(0.0, 1.0 - dist / denom)
        # Gentle decay near bounds.
        return float(linear**0.6)
    def _angle_score(self: Any, quad: np.ndarray) -> float:
        """
        Score how close the quad's corner angles are to 90 degrees.
        Returns 0..1.
        """
        q = quad.reshape((4, 2)).astype(np.float32)
        q = self.order_points(q)
        scores = []
        for i in range(4):
            p = q[i]
            p_prev = q[(i - 1) % 4]
            p_next = q[(i + 1) % 4]
            v1 = p_prev - p
            v2 = p_next - p
            n1 = float(np.linalg.norm(v1))
            n2 = float(np.linalg.norm(v2))
            if n1 == 0 or n2 == 0:
                scores.append(0.0)
                continue
            cosang = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
            ang = math.degrees(math.acos(cosang))
            # 90deg -> 1.0, 45/135deg -> 0.0
            scores.append(max(0.0, 1.0 - min(abs(ang - 90.0) / 45.0, 1.0)))
        return float(sum(scores) / len(scores)) if scores else 0.0
    def _edge_support_score(self: Any, quad: np.ndarray, edge_image: Optional[np.ndarray]) -> float:
        """
        Sample points along quad edges and measure how often they land on an edge pixel.
        Returns 0..1.
        """
        if edge_image is None:
            return 0.0
        if edge_image.ndim != 2:
            return 0.0

        h, w = edge_image.shape[:2]
        q = self.order_points(quad.reshape((4, 2)).astype(np.float32))

        # Total samples are kept small for performance; accurate mode increases count.
        samples_per_edge = 12 if self.algo.detection_mode == "fast" else (18 if self.algo.detection_mode == "balanced" else 28)
        radius = 1 if self.algo.detection_mode != "accurate" else 2

        hits = 0
        total = 0

        for i in range(4):
            p1 = q[i]
            p2 = q[(i + 1) % 4]
            for t in np.linspace(0.0, 1.0, samples_per_edge, endpoint=True):
                x = int(round(p1[0] + (p2[0] - p1[0]) * float(t)))
                y = int(round(p1[1] + (p2[1] - p1[1]) * float(t)))
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                total += 1
                x1 = max(0, x - radius)
                y1 = max(0, y - radius)
                x2 = min(w - 1, x + radius)
                y2 = min(h - 1, y + radius)
                if int(edge_image[y1 : y2 + 1, x1 : x2 + 1].max()) > 0:
                    hits += 1

        if total == 0:
            return 0.0
        return float(hits / total)
    def _border_penalty(self: Any, quad: np.ndarray, image_shape: Tuple[int, int]) -> float:
        """
        Penalize quads that sit too close to the outer border (common false positive: scanner frame).
        Returns 0..1 (higher = worse).
        """
        h, w = image_shape[:2]
        q = quad.reshape((4, 2)).astype(np.float32)
        min_dist = float("inf")
        for x, y in q:
            min_dist = min(min_dist, float(x), float(y), float(w - 1 - x), float(h - 1 - y))
        if not math.isfinite(min_dist):
            return 0.0
        margin = max(4.0, min(h, w) * 0.02)  # 2% of min dim
        if min_dist >= margin:
            return 0.0
        return float(min(1.0, (margin - min_dist) / margin))
    def _score_quad(
        self: Any,
        quad: np.ndarray,
        image_area: int,
        edge_image: Optional[np.ndarray] = None,
        image_shape: Optional[Tuple[int, int]] = None,
    ) -> float:
        """
        Score a quad (4 points) based on geometry + edge support.
        Returns 0..1.
        """
        if quad is None or quad.size == 0:
            return 0.0

        quad = quad.reshape((4, 2)).astype(np.float32)
        if not self._quad_is_convex(quad):
            return 0.0

        area = self._quad_area(quad)
        if area <= 0:
            return 0.0

        area_ratio = area / float(image_area) if image_area > 0 else 0.0
        if area_ratio <= 0:
            return 0.0

        # Area score respects min/max settings.
        min_ratio = float(self.algo.min_area_ratio)
        max_ratio = float(self.algo.max_area_ratio)
        if not (min_ratio <= area_ratio <= max_ratio):
            return 0.0
        area_score = self._area_score(area_ratio, min_ratio, max_ratio)

        # Aspect score from ordered side lengths (less sensitive to perspective tilt).
        aspect = self._quad_aspect_ratio(quad)
        if 0.45 <= aspect <= 2.2:
            aspect_score = 1.0 - min(
                1.0, abs(math.log(max(aspect, 1e-6))) / math.log(2.2)
            ) * 0.45
        elif 0.30 <= aspect <= 3.2:
            aspect_score = 0.55
        else:
            aspect_score = 0.18

        angle_score = self._angle_score(quad)
        edge_support = self._edge_support_score(quad, edge_image)
        if image_shape is not None:
            border_shape = image_shape
        elif edge_image is not None:
            border_shape = edge_image.shape[:2]
        else:
            border_shape = (1, 1)
        border_penalty = self._border_penalty(quad, border_shape)

        # Penalize tiny quads.
        min_side = self._quad_min_side(quad)
        min_side_score = 1.0 if min_side >= 20 else max(0.0, min_side / 20.0)

        # Weights depend on detection mode & scoring strictness.
        mode = self.algo.detection_mode
        if mode == "fast":
            weights = {"area": 0.40, "aspect": 0.35, "angle": 0.15, "edge": 0.10}
        elif mode == "accurate":
            weights = {"area": 0.25, "aspect": 0.15, "angle": 0.30, "edge": 0.30}
        else:  # balanced
            weights = {"area": 0.30, "aspect": 0.20, "angle": 0.25, "edge": 0.25}

        # Existing contour_scoring knob still matters; strict penalizes angle/edge failures harder.
        if self.algo.contour_scoring == "strict":
            border_weight = 0.20
        elif self.algo.contour_scoring == "enhanced":
            border_weight = 0.12
        else:
            border_weight = 0.08

        base = (
            area_score * weights["area"]
            + aspect_score * weights["aspect"]
            + angle_score * weights["angle"]
            + edge_support * weights["edge"]
        )

        base *= (0.70 + 0.30 * min_side_score)
        base *= (1.0 - border_weight * border_penalty)
        base *= (0.85 + 0.15 * min_side_score if mode != "fast" else 1.0)

        return float(max(0.0, min(1.0, base)))
    @staticmethod
    def _line_abc(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float]:
        # Ax + By = C
        a = y2 - y1
        b = x1 - x2
        c = a * x1 + b * y1
        return a, b, c
    @staticmethod
    def _intersect(l1: Tuple[float, float, float], l2: Tuple[float, float, float]) -> Optional[Tuple[float, float]]:
        a1, b1, c1 = l1
        a2, b2, c2 = l2
        det = a1 * b2 - a2 * b1
        if abs(det) < 1e-6:
            return None
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        return float(x), float(y)
