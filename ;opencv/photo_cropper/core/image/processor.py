#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Image Processor for Photo Cropper v9.0.

Provides advanced CV algorithms for automatic photo detection and cropping:
- Multi-scale Canny edge detection
- CLAHE contrast enhancement
- Adaptive threshold for textured backgrounds
- Gradient analysis (Sobel)
- Enhanced contour scoring
- v8.0: Advanced processing (deskew, color correct, perspective, etc.)
"""

import os
import cv2
import numpy as np
import logging
import traceback
import json
import time
import math
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..settings_model import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
    DebugSettings,
)
from ..advanced import AdvancedImageProcessor, GPUAccelerator
from .save_io import (
    resolve_save_codec as _resolve_save_codec_impl,
    copy_metadata_best_effort as _copy_metadata_best_effort_impl,
    save_image_unicode as _save_image_unicode_impl,
)

logger = logging.getLogger(__name__)


class DetectionStage(Enum):
    """Detection stage enumeration for tracking which algorithm succeeded."""

    CANNY = "Canny Edge"
    MULTI_SCALE_CANNY = "Multi-Scale Canny"
    BACKGROUND_MASK = "Background Mask"
    ADAPTIVE_THRESHOLD = "Adaptive Threshold"
    GRADIENT_SOBEL = "Gradient (Sobel)"
    CORNER_HARRIS = "Harris Corners"
    HOUGH_RECT = "Hough Rectangle"


@dataclass
class CropResult:
    """Result of image cropping operation."""

    success: bool
    image: Optional[np.ndarray] = None
    message: str = ""
    detection_stage: Optional[DetectionStage] = None
    contour_points: Optional[np.ndarray] = None
    confidence: float = 0.0
    debug_dir: Optional[str] = None
    original_size: Tuple[int, int] = (0, 0)
    cropped_size: Tuple[int, int] = (0, 0)


@dataclass
class PreviewProcessResult:
    """Result bundle for preview rendering."""

    original_preview: Optional[np.ndarray]
    overlay_preview: Optional[np.ndarray]
    crop_result: CropResult
    message: str = ""


class ImageProcessor:
    """
    Advanced image processor for automatic photo detection and cropping.

    Features:
        - 3+ stage intelligent photo detection
        - CLAHE for improved contrast handling
        - Multi-scale edge detection
        - Enhanced contour scoring algorithm
        - Perspective transform for skewed photos
    """

    # Constants
    SUPPORTED_FORMATS = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".webp",
    )
    MIN_IMAGE_SIZE = 100
    RESIZE_TARGET_DIM = 1000
    RESIZE_THRESHOLD = 1500
    DEFAULT_BILATERAL_D = 9
    DEFAULT_BILATERAL_SIGMA = 75
    MIN_CONTOUR_AREA = 100
    MIN_CROP_SIZE = 50
    PREVIEW_DETECTION_MAX_MP = 8.0

    def __init__(
        self,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
        debug_settings: Optional[DebugSettings] = None,
    ):
        """
        Initialize image processor.

        Args:
            algorithm_settings: Algorithm configuration
            processing_settings: Post-processing configuration
            advanced_settings: v8.0 Advanced processing settings
        """
        self.algo = algorithm_settings or AlgorithmSettings()
        self.proc = processing_settings or ProcessingSettings()
        self.advanced = advanced_settings or AdvancedProcessingSettings()
        self.performance = performance_settings or PerformanceSettings()
        self.debug = debug_settings or DebugSettings()

        # v8.0: Advanced processor
        self._advanced_processor = AdvancedImageProcessor(
            use_gpu=self.performance.use_gpu
        )

        # Performance: Cached CLAHE objects
        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_custom = None  # Lazy initialized with custom settings
        self._clahe_settings_cache = (None, None)  # (clip_limit, grid_size)

        # Performance: Cached kernels
        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_5x5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        self._kernel_morph_21x21 = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))

    def update_settings(
        self,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
        debug_settings: Optional[DebugSettings] = None,
    ):
        """Update processor settings."""
        if algorithm_settings:
            self.algo = algorithm_settings
        if processing_settings:
            self.proc = processing_settings
        if advanced_settings:
            self.advanced = advanced_settings
        if performance_settings:
            gpu_changed = self.performance.use_gpu != performance_settings.use_gpu
            self.performance = performance_settings
            if gpu_changed:
                self._advanced_processor = AdvancedImageProcessor(
                    use_gpu=self.performance.use_gpu
                )
        if debug_settings:
            self.debug = debug_settings

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

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
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

    def _get_clahe_with_settings(self, clip_limit: float, grid_size: int):
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

    def _quad_is_convex(self, quad: np.ndarray) -> bool:
        try:
            cnt = quad.reshape((-1, 1, 2)).astype(np.int32)
            return bool(cv2.isContourConvex(cnt))
        except Exception:
            return False

    def _quad_area(self, quad: np.ndarray) -> float:
        try:
            return float(cv2.contourArea(quad.reshape((-1, 1, 2)).astype(np.float32)))
        except Exception:
            return 0.0

    def _quad_min_side(self, quad: np.ndarray) -> float:
        q = quad.reshape((4, 2)).astype(np.float32)
        d = []
        for i in range(4):
            p1 = q[i]
            p2 = q[(i + 1) % 4]
            d.append(float(np.linalg.norm(p1 - p2)))
        return min(d) if d else 0.0

    def _quad_aspect_ratio(self, quad: np.ndarray) -> float:
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

    def _area_score(self, area_ratio: float, min_ratio: float, max_ratio: float) -> float:
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

    def _angle_score(self, quad: np.ndarray) -> float:
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

    def _edge_support_score(self, quad: np.ndarray, edge_image: Optional[np.ndarray]) -> float:
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

    def _border_penalty(self, quad: np.ndarray, image_shape: Tuple[int, int]) -> float:
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
        self,
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

    def _contour_to_quad_candidates(self, contour: np.ndarray) -> List[np.ndarray]:
        """
        Convert an arbitrary contour into one or more quad candidates.
        """
        if contour is None or len(contour) < 3:
            return []

        hull = cv2.convexHull(contour)
        peri = cv2.arcLength(hull, True)
        if peri <= 0:
            return []

        eps_factors = [0.01, 0.015, 0.02, 0.03, 0.04]
        candidates: List[np.ndarray] = []
        for f in eps_factors:
            approx = cv2.approxPolyDP(hull, f * peri, True)
            if approx is not None and len(approx) == 4:
                candidates.append(approx.reshape((4, 2)).astype(np.float32))

        # Rotated rectangle fallback
        try:
            rect = cv2.minAreaRect(hull)
            box = cv2.boxPoints(rect)  # 4x2
            if box is not None and len(box) == 4:
                candidates.append(np.array(box, dtype=np.float32))
        except Exception:
            pass

        # De-dup (rough)
        uniq: List[np.ndarray] = []
        for q in candidates:
            qn = np.round(self.order_points(q), 1)
            if not any(np.allclose(qn, np.round(self.order_points(u), 1)) for u in uniq):
                uniq.append(q)
        return uniq

    def find_best_contour(
        self,
        edge_image: np.ndarray,
        image_area: int,
        min_area_ratio: Optional[float] = None,
        max_area_ratio: Optional[float] = None,
        score_edge_map: Optional[np.ndarray] = None,
    ) -> Tuple[Optional[np.ndarray], float, List[dict]]:
        """
        Find the best quad candidate from a binary edge/mask image.

        Returns:
            (best_quad_points(4x2), best_score, candidates_for_debug)
        """
        if edge_image is None or edge_image.size == 0:
            return None, 0.0, []

        contours, _ = cv2.findContours(
            edge_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None, 0.0, []

        top_n = 10 if self.algo.detection_mode == "fast" else (20 if self.algo.detection_mode == "balanced" else 35)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:top_n]

        best_quad = None
        best_score = 0.0
        scored_candidates: List[dict] = []

        # Temporary area ratio overrides (do not mutate settings).
        orig_min = self.algo.min_area_ratio
        orig_max = self.algo.max_area_ratio
        if min_area_ratio is not None:
            self.algo.min_area_ratio = float(min_area_ratio)
        if max_area_ratio is not None:
            self.algo.max_area_ratio = float(max_area_ratio)

        score_map = score_edge_map if score_edge_map is not None else edge_image

        for contour in contours:
            # Skip tiny contours quickly.
            if cv2.contourArea(contour) < self.MIN_CONTOUR_AREA:
                continue

            for quad in self._contour_to_quad_candidates(contour):
                quad_points = self.order_points(quad.reshape((4, 2)).astype(np.float32))
                quad_area = self._quad_area(quad_points)
                if quad_area <= 0:
                    continue
                contour_area = float(cv2.contourArea(contour))
                hull = cv2.convexHull(contour)
                hull_area = float(cv2.contourArea(hull)) if hull is not None else 0.0
                xs = quad_points[:, 0]
                ys = quad_points[:, 1]
                span_x = (
                    float(np.max(xs) - np.min(xs)) / float(edge_image.shape[1])
                    if edge_image.shape[1] > 0
                    else 0.0
                )
                span_y = (
                    float(np.max(ys) - np.min(ys)) / float(edge_image.shape[0])
                    if edge_image.shape[0] > 0
                    else 0.0
                )
                area_ratio = float(quad_area / image_area) if image_area > 0 else 0.0
                contour_fill_ratio = max(0.0, contour_area / quad_area)
                hull_fill_ratio = max(0.0, hull_area / quad_area)
                border_penalty = self._border_penalty(quad_points, edge_image.shape[:2])
                score = self._score_quad(
                    quad_points,
                    image_area,
                    edge_image=score_map,
                    image_shape=edge_image.shape[:2],
                )
                if score <= 0:
                    continue
                scored_candidates.append(
                    {
                        "quad": quad_points,
                        "score": float(score),
                        "area_ratio": float(area_ratio),
                        "border_penalty": float(border_penalty),
                        "span_x": float(span_x),
                        "span_y": float(span_y),
                        "contour_fill_ratio": float(contour_fill_ratio),
                        "hull_fill_ratio": float(hull_fill_ratio),
                    }
                )
                if score > best_score:
                    best_score = score
                    best_quad = quad_points

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        # Restore settings
        self.algo.min_area_ratio = orig_min
        self.algo.max_area_ratio = orig_max
        return best_quad, float(best_score), scored_candidates[:10]

    def _min_accept_score_for_stage(self, stage: DetectionStage) -> float:
        """
        Conservative per-stage confidence gate.

        Higher-fallback stages require stronger evidence to reduce false positives.
        """
        mode = self.algo.detection_mode
        stage_thresholds = {
            "fast": {
                DetectionStage.CANNY: 0.30,
                DetectionStage.MULTI_SCALE_CANNY: 0.30,
                DetectionStage.BACKGROUND_MASK: 0.35,
                DetectionStage.ADAPTIVE_THRESHOLD: 0.45,
                DetectionStage.GRADIENT_SOBEL: 0.48,
                DetectionStage.CORNER_HARRIS: 0.52,
                DetectionStage.HOUGH_RECT: 0.60,
            },
            "balanced": {
                DetectionStage.CANNY: 0.45,
                DetectionStage.MULTI_SCALE_CANNY: 0.45,
                DetectionStage.BACKGROUND_MASK: 0.55,
                DetectionStage.ADAPTIVE_THRESHOLD: 0.72,
                DetectionStage.GRADIENT_SOBEL: 0.68,
                DetectionStage.CORNER_HARRIS: 0.70,
                DetectionStage.HOUGH_RECT: 0.82,
            },
            "accurate": {
                DetectionStage.CANNY: 0.72,
                DetectionStage.MULTI_SCALE_CANNY: 0.72,
                DetectionStage.BACKGROUND_MASK: 0.80,
                DetectionStage.ADAPTIVE_THRESHOLD: 0.97,
                DetectionStage.GRADIENT_SOBEL: 0.94,
                DetectionStage.CORNER_HARRIS: 0.92,
                DetectionStage.HOUGH_RECT: 0.98,
            },
        }
        threshold = stage_thresholds.get(mode, stage_thresholds["balanced"]).get(
            stage, 0.60
        )

        scoring_delta = {
            "basic": -0.03,
            "enhanced": 0.00,
            "strict": 0.04,
        }.get(self.algo.contour_scoring, 0.0)

        return float(max(0.15, min(0.995, threshold + scoring_delta)))

    def _accept_stage_candidate(self, stage: DetectionStage, score: float) -> bool:
        """Check whether a candidate score passes stage-specific gate."""
        return float(score) >= self._min_accept_score_for_stage(stage)

    def _candidate_passes_stage_filters(
        self,
        stage: DetectionStage,
        candidate: Dict[str, Any],
    ) -> bool:
        """Reject stage candidates that match common false-positive patterns."""
        area_ratio = float(candidate.get("area_ratio", 0.0) or 0.0)
        border_penalty = float(candidate.get("border_penalty", 0.0) or 0.0)
        span_x = float(candidate.get("span_x", 0.0) or 0.0)
        span_y = float(candidate.get("span_y", 0.0) or 0.0)
        contour_fill_ratio = float(candidate.get("contour_fill_ratio", 1.0) or 0.0)
        hull_fill_ratio = float(candidate.get("hull_fill_ratio", 1.0) or 0.0)
        max_span = max(span_x, span_y)

        if stage in (DetectionStage.CANNY, DetectionStage.MULTI_SCALE_CANNY):
            if max_span >= 0.88 and (area_ratio >= 0.60 or border_penalty >= 0.35):
                return False

        if stage in (
            DetectionStage.BACKGROUND_MASK,
            DetectionStage.ADAPTIVE_THRESHOLD,
            DetectionStage.GRADIENT_SOBEL,
        ):
            if contour_fill_ratio < 0.18 and hull_fill_ratio < 0.82:
                return False
            if (
                stage == DetectionStage.ADAPTIVE_THRESHOLD
                and contour_fill_ratio < 0.25
                and max_span >= 0.85
            ):
                return False

        return True

    def _stage_rank(self, stage: DetectionStage) -> int:
        """Stable rank used for tie-breaking during global stage re-ranking."""
        rank_map = {
            DetectionStage.CANNY: 0,
            DetectionStage.MULTI_SCALE_CANNY: 0,
            DetectionStage.BACKGROUND_MASK: 1,
            DetectionStage.ADAPTIVE_THRESHOLD: 2,
            DetectionStage.GRADIENT_SOBEL: 3,
            DetectionStage.CORNER_HARRIS: 4,
            DetectionStage.HOUGH_RECT: 5,
        }
        return int(rank_map.get(stage, 9))

    def _select_best_stage_candidate(
        self, stage_candidates: List[Dict[str, Any]], image_area: int
    ) -> Optional[Dict[str, Any]]:
        """
        Select best candidate across stages.

        Priority:
          1) score (desc)
          2) stage_rank (asc)
          3) area stability (distance from allowed area mid, asc)
        """
        if not stage_candidates:
            return None

        min_ratio = float(self.algo.min_area_ratio)
        max_ratio = float(self.algo.max_area_ratio)
        mid = (min_ratio + max_ratio) * 0.5

        def area_stability(candidate: Dict[str, Any]) -> float:
            quad = candidate.get("quad")
            if quad is None or image_area <= 0:
                return float("inf")
            area = self._quad_area(np.array(quad, dtype=np.float32))
            ratio = area / float(image_area)
            return abs(ratio - mid)

        ordered = sorted(
            stage_candidates,
            key=lambda c: (
                -float(c.get("score", 0.0)),
                int(c.get("stage_rank", 9)),
                area_stability(c),
            ),
        )
        return ordered[0] if ordered else None

    def _debug_enabled(self, debug_dir: Optional[str]) -> bool:
        return bool(self.debug.enabled and debug_dir is not None)

    def _resolve_debug_root(self, base_output_dir: Optional[str]) -> str:
        """
        Resolve debug root directory.

        If DebugSettings.output_dir is set, use it.
        Else if base_output_dir is a non-empty string, use {base_output_dir}/_debug.
        Else use %TEMP%/PhotoCropper/_debug.
        """
        if self.debug.output_dir:
            root = self.debug.output_dir
        elif base_output_dir:
            root = os.path.join(base_output_dir, "_debug")
        else:
            temp = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expanduser("~")
            root = os.path.join(temp, "PhotoCropper", "_debug")
        os.makedirs(root, exist_ok=True)
        return root

    def _prune_debug_root(self, root: str):
        """Best-effort pruning of debug folders under root based on mtime."""
        try:
            max_keep = int(self.debug.max_files) if self.debug.max_files else 0
            if max_keep <= 0:
                return
            entries = []
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if not os.path.isdir(path):
                    continue
                try:
                    mtime = os.path.getmtime(path)
                except Exception:
                    mtime = 0
                entries.append((mtime, path))
            if len(entries) <= max_keep:
                return
            entries.sort(key=lambda x: x[0])  # oldest first
            for _, path in entries[: max(0, len(entries) - max_keep)]:
                try:
                    # Remove directory recursively (best-effort)
                    for root_dir, dirs, files in os.walk(path, topdown=False):
                        for f in files:
                            try:
                                os.remove(os.path.join(root_dir, f))
                            except Exception:
                                pass
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root_dir, d))
                            except Exception:
                                pass
                    os.rmdir(path)
                except Exception:
                    pass
        except Exception:
            pass

    @staticmethod
    def _save_debug_image(path: str, image: np.ndarray) -> bool:
        """Save image to path with Unicode support (PNG)."""
        try:
            ext = os.path.splitext(path)[1].lower() or ".png"
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                ext = ".png"
                path = path + ext
            ok, buf = cv2.imencode(ext, image)
            if not ok:
                return False
            buf.tofile(path)
            return True
        except Exception:
            return False

    def _draw_candidates_overlay(
        self,
        base_bgr: np.ndarray,
        candidates: List[dict],
        final_quad: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        overlay = base_bgr.copy()
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
        ]
        for i, c in enumerate(candidates[:10]):
            quad = c.get("quad")
            if quad is None:
                continue
            pts = self.order_points(np.array(quad, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))
            color = colors[i % len(colors)]
            cv2.polylines(overlay, [pts], True, color, 2)
            cv2.putText(
                overlay,
                f"{i+1}:{c.get('score', 0.0):.2f}",
                tuple(pts[0][0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )
        if final_quad is not None:
            pts = self.order_points(np.array(final_quad, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [pts], True, (0, 180, 255), 3)
        return overlay

    def _create_background_mask(self, gray: np.ndarray) -> np.ndarray:
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

    def _build_hough_quad_from_groups(
        self,
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

    def _detect_rectangle_by_hough(self, edges: np.ndarray) -> Optional[np.ndarray]:
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

    def detect_edges_multiscale(self, gray: np.ndarray) -> np.ndarray:
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
        self, image: np.ndarray
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

    def _process_loaded_image(
        self,
        image: np.ndarray,
        image_path: str,
        *,
        debug_dir: Optional[str] = None,
        debug_tag: str = "",
    ) -> CropResult:
        """Process a pre-loaded image using the full detection/cropping pipeline."""
        try:
            debug_enabled = self._debug_enabled(debug_dir)
            debug_run_dir: Optional[str] = None

            height, width = image.shape[:2]
            original_size = (width, height)

            if height < 100 or width < 100:
                return CropResult(
                    False,
                    message="Image is too small (min 100x100).",
                    original_size=original_size,
                )

            orig = image.copy()

            if debug_enabled:
                root = self._resolve_debug_root(
                    debug_dir if isinstance(debug_dir, str) else None
                )
                self._prune_debug_root(root)
                base = os.path.splitext(os.path.basename(image_path))[0] or "image"
                debug_run_dir = os.path.join(root, base)
                os.makedirs(debug_run_dir, exist_ok=True)

            # Detection-only downscaling for performance.
            image_resized, ratio = self._prepare_detection_image(image)
            image_area = int(image_resized.shape[0] * image_resized.shape[1])

            # Apply CLAHE for better contrast
            if self.algo.use_clahe:
                image_resized = self.apply_clahe(image_resized)

            gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)

            best_quad: Optional[np.ndarray] = None
            best_score: float = 0.0
            best_candidates: List[dict] = []
            detection_stage: Optional[DetectionStage] = None

            # Shared edge reference for scoring (independent from stage masks).
            score_edges_reference = cv2.Canny(
                gray, int(self.algo.canny_min), int(self.algo.canny_max)
            )
            score_edges_reference = cv2.dilate(
                score_edges_reference, self._kernel_3x3, iterations=1
            )

            accurate_full_pass = self.algo.detection_mode == "accurate"
            stage_candidates: List[Dict[str, Any]] = []

            def _register_stage_candidate(
                stage: DetectionStage,
                quad: Optional[np.ndarray],
                score: float,
                candidates: Optional[List[dict]] = None,
            ) -> None:
                nonlocal best_quad, best_score, best_candidates, detection_stage

                if quad is None or not self._accept_stage_candidate(stage, score):
                    return
                ordered_quad = self.order_points(np.array(quad, dtype=np.float32))
                candidate_info: Dict[str, Any] = {
                    "quad": ordered_quad,
                    "score": float(score),
                }
                for candidate in candidates or []:
                    candidate_quad = candidate.get("quad")
                    if candidate_quad is None:
                        continue
                    if np.allclose(
                        self.order_points(np.array(candidate_quad, dtype=np.float32)),
                        ordered_quad,
                        atol=1.5,
                    ):
                        candidate_info = candidate
                        break
                if not self._candidate_passes_stage_filters(stage, candidate_info):
                    return

                entry = {
                    "stage": stage,
                    "quad": ordered_quad,
                    "score": float(score),
                    "stage_rank": self._stage_rank(stage),
                    "candidates": candidates or [{"quad": quad, "score": float(score)}],
                }
                stage_candidates.append(entry)
                if not accurate_full_pass and best_quad is None:
                    best_quad = entry["quad"]
                    best_score = entry["score"]
                    best_candidates = entry["candidates"]
                    detection_stage = stage

            # ==========================================
            # Stage 1: Multi-scale Canny Edge Detection
            # ==========================================
            edges = self.detect_edges_multiscale(gray)
            quad, score, candidates = self.find_best_contour(
                edges, image_area, score_edge_map=score_edges_reference
            )
            stage_1 = (
                DetectionStage.MULTI_SCALE_CANNY
                if self.algo.multi_scale_edge
                else DetectionStage.CANNY
            )
            _register_stage_candidate(stage_1, quad, score, candidates)

            if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                self._save_debug_image(
                    os.path.join(debug_run_dir, "stage_01_edges.png"), edges
                )

            # ==========================================
            # Stage 2: Background Mask (balanced/accurate)
            # ==========================================
            if (best_quad is None or accurate_full_pass) and self.algo.detection_mode in ("balanced", "accurate"):
                bgmask = self._create_background_mask(gray)
                quad, score, candidates = self.find_best_contour(
                    bgmask, image_area, score_edge_map=score_edges_reference
                )
                _register_stage_candidate(DetectionStage.BACKGROUND_MASK, quad, score, candidates)

                if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                    self._save_debug_image(
                        os.path.join(debug_run_dir, "stage_02_bgmask.png"), bgmask
                    )

            # ==========================================
            # Stage 3: Adaptive Threshold
            # ==========================================
            if best_quad is None or accurate_full_pass:
                blurred_bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
                adaptive_block_size = int(
                    getattr(self.algo, "adaptive_block_size", 15)
                )
                if adaptive_block_size < 3:
                    adaptive_block_size = 3
                if adaptive_block_size % 2 == 0:
                    adaptive_block_size += 1
                max_block = max(3, min(gray.shape[:2]) - 1)
                if max_block % 2 == 0:
                    max_block -= 1
                adaptive_block_size = min(adaptive_block_size, max_block)
                adaptive_c = float(getattr(self.algo, "adaptive_c", 4.0))
                thresh = cv2.adaptiveThreshold(
                    blurred_bilateral,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV,
                    adaptive_block_size,
                    adaptive_c,
                )
                quad, score, candidates = self.find_best_contour(
                    thresh, image_area, score_edge_map=score_edges_reference
                )
                _register_stage_candidate(DetectionStage.ADAPTIVE_THRESHOLD, quad, score, candidates)

                if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                    self._save_debug_image(
                        os.path.join(debug_run_dir, "stage_03_adaptive.png"), thresh
                    )

            # ==========================================
            # Stage 4: Gradient Analysis (Sobel)
            # ==========================================
            if best_quad is None or accurate_full_pass:
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                grad_x = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
                grad_y = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
                gradient = cv2.subtract(grad_x, grad_y)
                gradient = cv2.convertScaleAbs(gradient)

                _, thresh_grad = cv2.threshold(
                    gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                closed = cv2.morphologyEx(
                    thresh_grad, cv2.MORPH_CLOSE, self._kernel_morph_21x21
                )
                closed = cv2.erode(closed, self._kernel_3x3, iterations=4)
                closed = cv2.dilate(closed, self._kernel_3x3, iterations=4)

                quad, score, candidates = self.find_best_contour(
                    closed, image_area, score_edge_map=score_edges_reference
                )
                _register_stage_candidate(DetectionStage.GRADIENT_SOBEL, quad, score, candidates)

                if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                    self._save_debug_image(
                        os.path.join(debug_run_dir, "stage_04_sobel.png"), closed
                    )

            # ==========================================
            # Stage 5: Harris Corner Detection (optional/accurate)
            # ==========================================
            should_use_corner = bool(
                self.algo.use_corner_detection
                or self.algo.detection_mode == "accurate"
            )
            if (best_quad is None or accurate_full_pass) and should_use_corner:
                corners = cv2.cornerHarris(
                    gray, self.algo.corner_block_size, 3, self.algo.corner_k
                )
                corners = cv2.dilate(corners, np.ones((3, 3), dtype=np.uint8))
                threshold = 0.01 * corners.max()
                corner_mask = np.zeros_like(gray)
                corner_mask[corners > threshold] = 255

                quad, score, candidates = self.find_best_contour(
                    corner_mask, image_area, score_edge_map=score_edges_reference
                )
                _register_stage_candidate(DetectionStage.CORNER_HARRIS, quad, score, candidates)

                if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                    self._save_debug_image(
                        os.path.join(debug_run_dir, "stage_05_harris.png"), corner_mask
                    )

            # ==========================================
            # Stage 6: Hough Rectangle (accurate, or final fallback in balanced)
            # ==========================================
            if (best_quad is None or accurate_full_pass) and self.algo.detection_mode in ("balanced", "accurate"):
                hquad = self._detect_rectangle_by_hough(edges)
                if hquad is not None:
                    hscore = self._score_quad(
                        hquad,
                        image_area,
                        edge_image=score_edges_reference,
                        image_shape=edges.shape[:2],
                    )
                    if hscore > 0:
                        _register_stage_candidate(
                            DetectionStage.HOUGH_RECT,
                            hquad,
                            hscore,
                            [{"quad": hquad, "score": float(hscore)}],
                        )

            if accurate_full_pass and stage_candidates:
                selected = self._select_best_stage_candidate(stage_candidates, image_area)
                if selected is not None:
                    best_quad = np.array(selected["quad"], dtype=np.float32)
                    best_score = float(selected["score"])
                    best_candidates = list(selected.get("candidates", []))
                    detection_stage = selected.get("stage")
            if best_quad is None:
                return CropResult(
                    False,
                    message="Failed to detect photo boundary.",
                    original_size=original_size,
                    confidence=0.0,
                    debug_dir=debug_run_dir,
                )

            # Scale quad back to original size
            rect = self.order_points(best_quad.reshape(4, 2) * ratio)
            crop_mode = (
                "perspective"
                if bool(getattr(self.advanced, "perspective_correct", True))
                else "axis_aligned"
            )

            if crop_mode == "perspective":
                (tl, tr, br, bl) = rect

                # Calculate output dimensions
                width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                max_width = max(int(width_a), int(width_b))

                height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                max_height = max(int(height_a), int(height_b))

                if max_width <= 0 or max_height <= 0:
                    return CropResult(
                        False,
                        message="Detected region has invalid size.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                    )

                if max_width < 50 or max_height < 50:
                    return CropResult(
                        False,
                        message="Detected region is too small.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                    )

                # Perspective transform
                dst = np.array(
                    [
                        [0, 0],
                        [max_width - 1, 0],
                        [max_width - 1, max_height - 1],
                        [0, max_height - 1],
                    ],
                    dtype="float32",
                )

                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(orig, M, (max_width, max_height))
            else:
                x_min = int(np.floor(float(np.min(rect[:, 0]))))
                y_min = int(np.floor(float(np.min(rect[:, 1]))))
                x_max = int(np.ceil(float(np.max(rect[:, 0]))))
                y_max = int(np.ceil(float(np.max(rect[:, 1]))))

                img_h, img_w = orig.shape[:2]
                x_min = max(0, min(x_min, max(0, img_w - 1)))
                y_min = max(0, min(y_min, max(0, img_h - 1)))
                x_max = max(x_min + 1, min(x_max, img_w))
                y_max = max(y_min + 1, min(y_max, img_h))

                max_width = int(x_max - x_min)
                max_height = int(y_max - y_min)

                if max_width <= 0 or max_height <= 0:
                    return CropResult(
                        False,
                        message="Detected region has invalid size.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                    )

                if max_width < 50 or max_height < 50:
                    return CropResult(
                        False,
                        message="Detected region is too small.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                    )

                warped = orig[y_min:y_max, x_min:x_max].copy()

            # Apply post-processing
            warped = self._apply_post_processing(warped)
            cropped_size = (warped.shape[1], warped.shape[0])

            # Debug outputs (overlay + metadata)
            if debug_enabled and debug_run_dir:
                try:
                    if self.debug.save_candidate_overlays:
                        cand_overlay = self._draw_candidates_overlay(
                            image_resized, best_candidates, final_quad=best_quad
                        )
                        self._save_debug_image(
                            os.path.join(debug_run_dir, "candidates_overlay.png"),
                            cand_overlay,
                        )
                        final_overlay = self._draw_candidates_overlay(
                            image_resized, [], final_quad=best_quad
                        )
                        self._save_debug_image(
                            os.path.join(debug_run_dir, "final_overlay.png"),
                            final_overlay,
                        )

                    stage_candidate_meta: List[Dict[str, Any]] = []
                    for sc in stage_candidates or []:
                        stage_obj = sc.get("stage")
                        if isinstance(stage_obj, DetectionStage):
                            stage_name: Optional[str] = stage_obj.value
                        elif stage_obj is None:
                            stage_name = None
                        else:
                            stage_name = str(stage_obj)
                        stage_candidate_meta.append(
                            {
                                "stage": stage_name,
                                "score": float(sc.get("score", 0.0)),
                                "stage_rank": int(sc.get("stage_rank", 9)),
                            }
                        )

                    meta = {
                        "image": os.path.basename(image_path),
                        "debug_tag": debug_tag or "",
                        "detection_mode": self.algo.detection_mode,
                        "detection_stage": (
                            detection_stage.value if detection_stage else None
                        ),
                        "confidence": float(best_score),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "candidates": [
                            {"score": float(c.get("score", 0.0))}
                            for c in (best_candidates or [])
                        ],
                        "stage_candidates": stage_candidate_meta,
                        "algo": {
                            "canny_min": int(self.algo.canny_min),
                            "canny_max": int(self.algo.canny_max),
                            "use_clahe": bool(self.algo.use_clahe),
                            "multi_scale_edge": bool(self.algo.multi_scale_edge),
                            "min_area_ratio": float(self.algo.min_area_ratio),
                            "max_area_ratio": float(self.algo.max_area_ratio),
                            "bg_mask_delta": float(
                                getattr(self.algo, "bg_mask_delta", 30.0)
                            ),
                            "adaptive_block_size": int(
                                getattr(self.algo, "adaptive_block_size", 15)
                            ),
                            "adaptive_c": float(getattr(self.algo, "adaptive_c", 4.0)),
                            "perspective_correct": bool(
                                getattr(self.advanced, "perspective_correct", True)
                            ),
                            "crop_mode": crop_mode,
                        },
                    }
                    with open(
                        os.path.join(debug_run_dir, "meta.json"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(meta, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            return CropResult(
                success=True,
                image=warped,
                message="OK",
                detection_stage=detection_stage,
                contour_points=rect,
                confidence=float(best_score),
                debug_dir=debug_run_dir,
                original_size=original_size,
                cropped_size=cropped_size,
            )
        except MemoryError:
            # Force garbage collection on memory error
            import gc

            gc.collect()
            return CropResult(False, message="Out of memory.")
        except Exception as e:
            logger.error(f"Image processing error: {traceback.format_exc()}")
            return CropResult(False, message=f"Error: {str(e)}")

    def process_image(
        self,
        image_path: str,
        *,
        debug_dir: Optional[str] = None,
        debug_tag: str = "",
    ) -> CropResult:
        """
        Process image with multi-stage detection algorithm.

        Args:
            image_path: Path to input image
            debug_dir: Base output directory for debug artifacts. If empty string, a default is chosen.
            debug_tag: Optional tag recorded in debug meta.json.

        Returns:
            CropResult with processed image or error
        """
        image = self.load_image(image_path)
        if image is None:
            return CropResult(False, message="Failed to load image.")
        return self._process_loaded_image(
            image,
            image_path,
            debug_dir=debug_dir,
            debug_tag=debug_tag,
        )

    def process_preview(
        self,
        image_path: str,
        max_size: int = 800,
        debug_tag: str = "preview",
        fast_preview: bool = True,
        preview_detection_max_mp: float = PREVIEW_DETECTION_MAX_MP,
    ) -> PreviewProcessResult:
        """
        Build preview images and crop result in a single image-load pass.
        """
        image = self.load_image(image_path)
        if image is None:
            crop_result = CropResult(False, message="이미지를 불러올 수 없습니다.")
            return PreviewProcessResult(
                original_preview=None,
                overlay_preview=None,
                crop_result=crop_result,
                message=crop_result.message,
            )

        h, w = image.shape[:2]
        scale = min(max_size / w, max_size / h, 1.0)
        preview_size = (int(w * scale), int(h * scale))
        original_preview = cv2.resize(image, preview_size, interpolation=cv2.INTER_AREA)

        detection_image = image
        contour_scale_back = 1.0

        if fast_preview:
            max_mp = max(1.0, float(preview_detection_max_mp or self.PREVIEW_DETECTION_MAX_MP))
            current_mp = (h * w) / 1_000_000.0
            if current_mp > max_mp:
                detect_scale = math.sqrt(max_mp / current_mp)
                detect_w = max(1, int(w * detect_scale))
                detect_h = max(1, int(h * detect_scale))
                detection_image = cv2.resize(
                    image,
                    (detect_w, detect_h),
                    interpolation=cv2.INTER_AREA,
                )
                contour_scale_back = w / float(detect_w)

        debug_base = "" if self.debug.enabled else None
        crop_result = self._process_loaded_image(
            detection_image,
            image_path,
            debug_dir=debug_base,
            debug_tag=debug_tag,
        )

        if crop_result.contour_points is not None and contour_scale_back != 1.0:
            crop_result.contour_points = crop_result.contour_points * contour_scale_back

        # Keep preview metadata aligned to the source image dimensions.
        crop_result.original_size = (w, h)

        # Preview output is display-only; keep it bounded for UI responsiveness.
        if crop_result.image is not None:
            ch, cw = crop_result.image.shape[:2]
            display_scale = min(max_size / cw, max_size / ch, 1.0)
            if display_scale < 1.0:
                display_size = (
                    max(1, int(cw * display_scale)),
                    max(1, int(ch * display_scale)),
                )
                crop_result.image = cv2.resize(
                    crop_result.image,
                    display_size,
                    interpolation=cv2.INTER_AREA,
                )
                crop_result.cropped_size = (
                    crop_result.image.shape[1],
                    crop_result.image.shape[0],
                )

        if crop_result.success and crop_result.contour_points is not None:
            overlay = original_preview.copy()
            scaled_contour = (crop_result.contour_points * scale).astype(np.int32)
            cv2.polylines(overlay, [scaled_contour], True, (0, 255, 0), 2)
            for point in scaled_contour:
                cv2.circle(overlay, tuple(point), 5, (0, 0, 255), -1)
        else:
            overlay = original_preview.copy()

        return PreviewProcessResult(
            original_preview=original_preview,
            overlay_preview=overlay,
            crop_result=crop_result,
            message=crop_result.message,
        )

    def _apply_post_processing(self, image: np.ndarray) -> np.ndarray:
        """
        Apply post-processing effects to cropped image.

        Args:
            image: Cropped image

        Returns:
            Post-processed image
        """
        result = image.copy()

        # Grayscale conversion
        if self.proc.to_grayscale:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

        # Denoise
        if self.proc.denoise:
            denoise_strength = float(self.proc.denoise_strength)
            if len(result.shape) == 2:
                # Use positional args for broad OpenCV Python binding compatibility.
                result = cv2.fastNlMeansDenoising(
                    result, None, denoise_strength, 7, 21
                )
            else:
                # OpenCV 4.13+ rejects some keyword names in this API.
                result = cv2.fastNlMeansDenoisingColored(
                    result,
                    None,
                    denoise_strength,
                    denoise_strength,
                    7,
                    21,
                )

        # Auto contrast (CLAHE or histogram equalization)
        if self.proc.auto_contrast:
            if len(result.shape) == 2:
                # Grayscale - use cached CLAHE
                result = self._clahe_default.apply(result)
            else:
                # Color - apply CLAHE to L channel in LAB
                lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l = self._clahe_default.apply(l)
                lab = cv2.merge([l, a, b])
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Sharpening
        if self.proc.apply_sharpening:
            strength = self.proc.sharpening_strength
            if strength > 0:
                # Adjustable sharpening kernel
                kernel = np.array(
                    [
                        [-strength / 4, -strength / 4, -strength / 4],
                        [-strength / 4, 1 + 2 * strength, -strength / 4],
                        [-strength / 4, -strength / 4, -strength / 4],
                    ]
                )
                result = cv2.filter2D(result, -1, kernel)

        # ========================================
        # v8.0 Advanced Processing
        # ========================================

        # Auto deskew
        if self.advanced.auto_deskew:
            deskew_result = self._advanced_processor.auto_deskew(result)
            if deskew_result is not None and deskew_result.image is not None:
                result = deskew_result.image

        # Auto color correction
        if self.advanced.auto_color_correct:
            result = self._advanced_processor.auto_color_correct(
                result, method=self.advanced.color_correct_method
            )

        # Enhanced denoise
        if self.advanced.enhanced_denoise:
            result = self._advanced_processor.denoise_enhanced(
                result, strength=self.advanced.enhanced_denoise_strength
            )

        # Old photo restoration
        if self.advanced.restore_old_photo:
            result = self._advanced_processor.restore_old_photo(result)

        # Enhanced sharpening
        if self.advanced.enhanced_sharpen:
            result = self._advanced_processor.sharpen(result)

        # Auto crop borders
        if self.advanced.auto_crop_borders:
            result = self._advanced_processor.auto_crop_borders(result)

        return result

    @staticmethod
    def _resolve_save_codec(
        output_path: str,
        output_format: str,
    ) -> Tuple[str, str]:
        """Resolve encoder extension and format with extension fallback."""
        return _resolve_save_codec_impl(output_path, output_format)

    @staticmethod
    def _copy_metadata_best_effort(source_path: str, output_path: str) -> None:
        """Best-effort EXIF/ICC metadata copy via Pillow."""
        _copy_metadata_best_effort_impl(source_path, output_path)

    @staticmethod
    def save_image(
        image: np.ndarray,
        output_path: str,
        output_format: str = "JPG",
        jpg_quality: int = 95,
        png_compression: int = 6,
        webp_quality: int = 90,
        source_path: Optional[str] = None,
        preserve_metadata: bool = False,
    ) -> Tuple[bool, str, float]:
        """
        Save image to file with Unicode path support.

        Args:
            image: Image array to save
            output_path: Output file path
            output_format: Format (JPG, PNG, WEBP)
            jpg_quality: JPEG quality (1-100)
            png_compression: PNG compression (0-9)
            webp_quality: WebP quality (1-100)
            source_path: Source image path for metadata copy
            preserve_metadata: Best-effort EXIF/ICC preservation

        Returns:
            Tuple of (success, message, file_size_kb)
        """
        return _save_image_unicode_impl(
            image=image,
            output_path=output_path,
            output_format=output_format,
            jpg_quality=jpg_quality,
            png_compression=png_compression,
            webp_quality=webp_quality,
            source_path=source_path,
            preserve_metadata=preserve_metadata,
        )

    @staticmethod
    def get_image_info(image_path: str) -> Optional[Tuple[int, int, int]]:
        """
        Get image dimensions without fully loading.

        Args:
            image_path: Path to image

        Returns:
            Tuple of (width, height, channels) or None
        """
        # Try PIL first - only reads headers, much faster for large images
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                w, h = img.size
                # Determine channels from mode
                mode_channels = {
                    "L": 1,
                    "LA": 2,
                    "P": 1,
                    "RGB": 3,
                    "RGBA": 4,
                    "CMYK": 4,
                    "YCbCr": 3,
                    "LAB": 3,
                    "HSV": 3,
                }
                c = mode_channels.get(img.mode, 3)
                return w, h, c
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to OpenCV (loads full image)
        try:
            img_array = np.fromfile(image_path, np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if image is not None:
                h, w = image.shape[:2]
                c = image.shape[2] if len(image.shape) > 2 else 1
                return w, h, c
        except Exception:
            pass
        return None

    def get_preview_with_contour(
        self, image_path: str, max_size: int = 800
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
        """
        Get preview images with detected contour overlay.

        Args:
            image_path: Path to input image
            max_size: Maximum dimension for preview

        Returns:
            Tuple of (original_preview, contour_overlay, message)
        """
        try:
            preview_result = self.process_preview(
                image_path,
                max_size=max_size,
                debug_tag="preview_legacy",
            )
            return (
                preview_result.original_preview,
                preview_result.overlay_preview,
                preview_result.message,
            )
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return None, None, f"미리보기 오류: {str(e)}"
