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
from .types import CropResult, DetectionStage, FailureReason, PreviewProcessResult

logger = logging.getLogger(__name__)


class ImageDetectionPipelineMixin:
    def _process_loaded_image(
        self: Any,
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
                    failure_reason=FailureReason.TOO_SMALL,
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
            # Used by _score_quad content contrast (noise FP rejection).
            self._score_gray_ref = gray

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
            # Stage 6: Morphology Gradient (textured backgrounds)
            # ==========================================
            if (best_quad is None or accurate_full_pass) and self.algo.detection_mode in (
                "balanced",
                "accurate",
            ):
                morph_mask = self._create_morph_gradient_mask(gray)
                quad, score, candidates = self.find_best_contour(
                    morph_mask, image_area, score_edge_map=score_edges_reference
                )
                _register_stage_candidate(
                    DetectionStage.MORPH_GRADIENT, quad, score, candidates
                )
                if debug_enabled and debug_run_dir and self.debug.save_detection_stages:
                    self._save_debug_image(
                        os.path.join(debug_run_dir, "stage_06_morph_gradient.png"),
                        morph_mask,
                    )

            # ==========================================
            # Stage 7: Hough Rectangle (accurate, or final fallback in balanced)
            # ==========================================
            if (best_quad is None or accurate_full_pass) and self.algo.detection_mode in ("balanced", "accurate"):
                hquad = self._detect_rectangle_by_hough(edges)
                if hquad is not None:
                    hscore = self._score_quad(
                        hquad,
                        image_area,
                        edge_image=score_edges_reference,
                        image_shape=edges.shape[:2],
                        gray_image=gray,
                    )
                    if hscore > 0:
                        _register_stage_candidate(
                            DetectionStage.HOUGH_RECT,
                            hquad,
                            hscore,
                            [{"quad": hquad, "score": float(hscore)}],
                        )

            # ==========================================
            # Stage 8: LSD Rectangle (accurate only)
            # ==========================================
            if (best_quad is None or accurate_full_pass) and self.algo.detection_mode == "accurate":
                lquad = self._detect_rectangle_by_lsd(gray)
                if lquad is not None:
                    lscore = self._score_quad(
                        lquad,
                        image_area,
                        edge_image=score_edges_reference,
                        image_shape=gray.shape[:2],
                        gray_image=gray,
                    )
                    if lscore > 0:
                        _register_stage_candidate(
                            DetectionStage.LSD_RECT,
                            lquad,
                            lscore,
                            [{"quad": lquad, "score": float(lscore)}],
                        )

            stage_score_meta: List[Dict[str, Any]] = []
            for sc in stage_candidates or []:
                stage_obj = sc.get("stage")
                if isinstance(stage_obj, DetectionStage):
                    stage_name: Optional[str] = stage_obj.value
                elif stage_obj is None:
                    stage_name = None
                else:
                    stage_name = str(stage_obj)
                stage_score_meta.append(
                    {
                        "stage": stage_name,
                        "score": float(sc.get("score", 0.0)),
                        "stage_rank": int(sc.get("stage_rank", 9)),
                    }
                )

            # Cross-stage NMS to drop near-duplicate quads before re-rank / early pick.
            if stage_candidates:
                stage_candidates = self._nms_stage_candidates(
                    stage_candidates,
                    gray.shape[:2],
                    iou_threshold=0.72,
                )

            if accurate_full_pass and stage_candidates:
                selected = self._select_best_stage_candidate(stage_candidates, image_area)
                if selected is not None:
                    best_quad = np.array(selected["quad"], dtype=np.float32)
                    best_score = float(selected["score"])
                    best_candidates = list(selected.get("candidates", []))
                    detection_stage = selected.get("stage")
            elif best_quad is not None and stage_candidates:
                # Keep early-exit pick consistent with NMS survivor set.
                still_valid = any(
                    np.allclose(
                        self.order_points(np.array(sc["quad"], dtype=np.float32)),
                        self.order_points(np.array(best_quad, dtype=np.float32)),
                        atol=2.0,
                    )
                    for sc in stage_candidates
                    if sc.get("quad") is not None
                )
                if not still_valid:
                    selected = self._select_best_stage_candidate(
                        stage_candidates, image_area
                    )
                    if selected is not None:
                        best_quad = np.array(selected["quad"], dtype=np.float32)
                        best_score = float(selected["score"])
                        best_candidates = list(selected.get("candidates", []))
                        detection_stage = selected.get("stage")

            # Global final floor: soft per-stage gates collect candidates for re-rank,
            # but we still reject weak winners (noise textures / empty frames).
            final_floor = {
                "fast": 0.30,
                "balanced": 0.48,
                "accurate": 0.72,
            }.get(self.algo.detection_mode, 0.48)
            scoring_delta = {
                "basic": -0.03,
                "enhanced": 0.00,
                "strict": 0.04,
            }.get(self.algo.contour_scoring, 0.0)
            final_floor = float(max(0.20, min(0.95, final_floor + scoring_delta)))
            # Fallback stages need a slightly higher bar even after re-rank.
            if detection_stage in (
                DetectionStage.HOUGH_RECT,
                DetectionStage.LSD_RECT,
                DetectionStage.CORNER_HARRIS,
            ):
                final_floor = max(final_floor, 0.76 if accurate_full_pass else 0.55)

            if best_quad is not None and float(best_score) < final_floor:
                best_quad = None
                best_score = 0.0
                detection_stage = None

            # Snap corners to edge evidence (helps IoU on slightly offset quads).
            if best_quad is not None and score_edges_reference is not None:
                snapped = self._snap_quad_to_edges(
                    best_quad,
                    score_edges_reference,
                    search_radius=3 if self.algo.detection_mode == "fast" else 5,
                )
                snap_score = self._score_quad(
                    snapped,
                    image_area,
                    edge_image=score_edges_reference,
                    image_shape=gray.shape[:2],
                    gray_image=gray,
                )
                if snap_score >= float(best_score) * 0.97:
                    best_quad = snapped
                    best_score = max(float(best_score), float(snap_score))

            # GrabCut refine (accurate only) on detection-resolution BGR image.
            if best_quad is not None and accurate_full_pass:
                try:
                    refined = self._refine_quad_with_grabcut(
                        image_resized, best_quad, iterations=2
                    )
                    if refined is not None:
                        ref_score = self._score_quad(
                            refined,
                            image_area,
                            edge_image=score_edges_reference,
                            image_shape=gray.shape[:2],
                            gray_image=gray,
                        )
                        # Accept only if score does not collapse.
                        if ref_score >= float(best_score) * 0.92:
                            best_quad = refined
                            best_score = max(float(best_score), float(ref_score))
                except Exception:
                    pass

            if best_quad is None:
                return CropResult(
                    False,
                    message="Failed to detect photo boundary.",
                    original_size=original_size,
                    confidence=0.0,
                    debug_dir=debug_run_dir,
                    failure_reason=FailureReason.NO_BOUNDARY,
                    stage_scores=stage_score_meta,
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
                        failure_reason=FailureReason.INVALID_REGION,
                        stage_scores=stage_score_meta,
                    )

                if max_width < 50 or max_height < 50:
                    return CropResult(
                        False,
                        message="Detected region is too small.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                        failure_reason=FailureReason.INVALID_REGION,
                        stage_scores=stage_score_meta,
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
                        failure_reason=FailureReason.INVALID_REGION,
                        stage_scores=stage_score_meta,
                    )

                if max_width < 50 or max_height < 50:
                    return CropResult(
                        False,
                        message="Detected region is too small.",
                        original_size=original_size,
                        confidence=float(best_score),
                        debug_dir=debug_run_dir,
                        failure_reason=FailureReason.INVALID_REGION,
                        stage_scores=stage_score_meta,
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
                        "stage_candidates": stage_score_meta,
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
                failure_reason=FailureReason.NONE,
                stage_scores=stage_score_meta,
            )
        except MemoryError:
            # Force garbage collection on memory error
            import gc

            gc.collect()
            return CropResult(
                False,
                message="Out of memory.",
                failure_reason=FailureReason.OUT_OF_MEMORY,
            )
        except Exception as e:
            logger.error(f"Image processing error: {traceback.format_exc()}")
            return CropResult(
                False,
                message=f"Error: {str(e)}",
                failure_reason=FailureReason.ERROR,
            )
