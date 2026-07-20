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


class ImageContourSelectionMixin:
    def _contour_to_quad_candidates(self: Any, contour: np.ndarray) -> List[np.ndarray]:
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
        self: Any,
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
                    gray_image=getattr(self, "_score_gray_ref", None),
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
    def _min_accept_score_for_stage(self: Any, stage: DetectionStage) -> float:
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
                # Soft floors: accurate relies on full-pass global re-rank, so
                # hard gates only filter obvious junk (0.97+ previously caused misses).
                DetectionStage.CANNY: 0.55,
                DetectionStage.MULTI_SCALE_CANNY: 0.55,
                DetectionStage.BACKGROUND_MASK: 0.60,
                DetectionStage.ADAPTIVE_THRESHOLD: 0.62,
                DetectionStage.GRADIENT_SOBEL: 0.62,
                DetectionStage.CORNER_HARRIS: 0.65,
                DetectionStage.HOUGH_RECT: 0.68,
                DetectionStage.MORPH_GRADIENT: 0.60,
                DetectionStage.LSD_RECT: 0.66,
            },
        }
        for mode_key in ("fast", "balanced"):
            stage_thresholds[mode_key].setdefault(DetectionStage.MORPH_GRADIENT, 0.50)
            stage_thresholds[mode_key].setdefault(DetectionStage.LSD_RECT, 0.58)
        stage_thresholds["fast"][DetectionStage.MORPH_GRADIENT] = 0.40
        stage_thresholds["fast"][DetectionStage.LSD_RECT] = 0.50

        threshold = stage_thresholds.get(mode, stage_thresholds["balanced"]).get(
            stage, 0.60
        )

        scoring_delta = {
            "basic": -0.03,
            "enhanced": 0.00,
            "strict": 0.04,
        }.get(self.algo.contour_scoring, 0.0)

        return float(max(0.15, min(0.995, threshold + scoring_delta)))
    def _accept_stage_candidate(self: Any, stage: DetectionStage, score: float) -> bool:
        """Check whether a candidate score passes stage-specific gate."""
        return float(score) >= self._min_accept_score_for_stage(stage)
    def _candidate_passes_stage_filters(
        self: Any,
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
    def _stage_rank(self: Any, stage: DetectionStage) -> int:
        """Stable rank used for tie-breaking during global stage re-ranking."""
        rank_map = {
            DetectionStage.CANNY: 0,
            DetectionStage.MULTI_SCALE_CANNY: 0,
            DetectionStage.BACKGROUND_MASK: 1,
            DetectionStage.MORPH_GRADIENT: 1,
            DetectionStage.ADAPTIVE_THRESHOLD: 2,
            DetectionStage.GRADIENT_SOBEL: 3,
            DetectionStage.CORNER_HARRIS: 4,
            DetectionStage.HOUGH_RECT: 5,
            DetectionStage.LSD_RECT: 5,
        }
        return int(rank_map.get(stage, 9))
    def _quad_iou(self: Any, a: np.ndarray, b: np.ndarray, shape: Tuple[int, int]) -> float:
        """Mask IoU between two quads on a discrete canvas."""
        h, w = int(shape[0]), int(shape[1])
        if h <= 0 or w <= 0:
            return 0.0
        ma = np.zeros((h, w), dtype=np.uint8)
        mb = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(ma, [np.asarray(a, dtype=np.int32).reshape((-1, 1, 2))], 255)
        cv2.fillPoly(mb, [np.asarray(b, dtype=np.int32).reshape((-1, 1, 2))], 255)
        inter = int(np.logical_and(ma > 0, mb > 0).sum())
        union = int(np.logical_or(ma > 0, mb > 0).sum())
        if union <= 0:
            return 0.0
        return float(inter) / float(union)

    def _nms_stage_candidates(
        self: Any,
        stage_candidates: List[Dict[str, Any]],
        image_shape: Tuple[int, int],
        *,
        iou_threshold: float = 0.72,
    ) -> List[Dict[str, Any]]:
        """Suppress near-duplicate quads across stages, keeping higher scores."""
        if len(stage_candidates) <= 1:
            return list(stage_candidates)

        ordered = sorted(
            stage_candidates,
            key=lambda c: (
                -float(c.get("score", 0.0)),
                int(c.get("stage_rank", 9)),
            ),
        )
        kept: List[Dict[str, Any]] = []
        for cand in ordered:
            quad = cand.get("quad")
            if quad is None:
                continue
            q = np.asarray(quad, dtype=np.float32).reshape((4, 2))
            drop = False
            for existing in kept:
                eq = np.asarray(existing.get("quad"), dtype=np.float32).reshape((4, 2))
                if self._quad_iou(q, eq, image_shape) >= iou_threshold:
                    drop = True
                    break
            if not drop:
                kept.append(cand)
        return kept

    def _refine_quad_with_grabcut(
        self: Any,
        bgr_image: np.ndarray,
        quad: np.ndarray,
        *,
        iterations: int = 2,
    ) -> Optional[np.ndarray]:
        """
        Refine a quad using GrabCut on a ROI (accurate mode, cost-guarded).

        Returns refined ordered quad in the same coordinate space, or None.
        """
        if bgr_image is None or bgr_image.size == 0 or bgr_image.ndim != 3:
            return None
        q = self.order_points(np.asarray(quad, dtype=np.float32).reshape((4, 2)))
        h, w = bgr_image.shape[:2]
        # Skip GrabCut on very large canvases (CPU).
        if h * w > 4_000_000:
            return None

        xs = q[:, 0]
        ys = q[:, 1]
        x1 = max(0, int(np.floor(float(np.min(xs)))) - 8)
        y1 = max(0, int(np.floor(float(np.min(ys)))) - 8)
        x2 = min(w, int(np.ceil(float(np.max(xs)))) + 8)
        y2 = min(h, int(np.ceil(float(np.max(ys)))) + 8)
        if x2 - x1 < 40 or y2 - y1 < 40:
            return None

        roi = bgr_image[y1:y2, x1:x2].copy()
        rh, rw = roi.shape[:2]
        mask = np.full((rh, rw), cv2.GC_PR_BGD, dtype=np.uint8)
        local = q.copy()
        local[:, 0] -= float(x1)
        local[:, 1] -= float(y1)
        cv2.fillPoly(mask, [local.astype(np.int32)], int(cv2.GC_PR_FGD))
        # Seed a shrunken interior as definite foreground.
        try:
            center = local.mean(axis=0)
            shrink = center + (local - center) * 0.72
            cv2.fillPoly(mask, [shrink.astype(np.int32)], int(cv2.GC_FGD))
        except Exception:
            pass

        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        # GC_INIT_WITH_MASK ignores rect at runtime; stubs still require a Rect.
        dummy_rect = (0, 0, max(1, rw), max(1, rh))
        try:
            cv2.grabCut(
                roi,
                mask,
                dummy_rect,
                bgd,
                fgd,
                max(1, int(iterations)),
                cv2.GC_INIT_WITH_MASK,
            )
        except Exception:
            return None

        fg = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, self._kernel_5x5, iterations=1)
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        best = max(contours, key=cv2.contourArea)
        if cv2.contourArea(best) < 100:
            return None
        quads = self._contour_to_quad_candidates(best)
        if not quads:
            return None
        refined = self.order_points(np.asarray(quads[0], dtype=np.float32).reshape((4, 2)))
        refined[:, 0] += float(x1)
        refined[:, 1] += float(y1)
        return refined

    def _snap_quad_to_edges(
        self: Any,
        quad: np.ndarray,
        edge_image: Optional[np.ndarray],
        *,
        search_radius: int = 4,
    ) -> np.ndarray:
        """Nudge each corner toward the strongest nearby edge pixel."""
        q = np.asarray(quad, dtype=np.float32).reshape((4, 2)).copy()
        if edge_image is None or edge_image.ndim != 2:
            return q
        h, w = edge_image.shape[:2]
        r = max(1, int(search_radius))
        for i in range(4):
            cx, cy = int(round(float(q[i, 0]))), int(round(float(q[i, 1])))
            x1, x2 = max(0, cx - r), min(w - 1, cx + r)
            y1, y2 = max(0, cy - r), min(h - 1, cy + r)
            patch = edge_image[y1 : y2 + 1, x1 : x2 + 1]
            if patch.size == 0:
                continue
            # Prefer non-zero edge; if all zero keep original.
            if int(patch.max()) <= 0:
                continue
            yy, xx = np.unravel_index(int(np.argmax(patch)), patch.shape)
            q[i, 0] = float(x1 + xx)
            q[i, 1] = float(y1 + yy)
        return self.order_points(q)

    def _select_best_stage_candidate(
        self: Any, stage_candidates: List[Dict[str, Any]], image_area: int
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
