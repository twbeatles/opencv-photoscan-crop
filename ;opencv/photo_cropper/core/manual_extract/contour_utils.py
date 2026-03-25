#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contour and boundary-failure helper utilities for manual extraction."""

from __future__ import annotations

import os
import logging
from typing import Any, Callable, Iterable, List, Optional

import numpy as np


def scale_contour_to_preview(
    preview_image: Any,
    crop_result: Any,
) -> Optional[np.ndarray]:
    """Scale contour points from source coordinates to preview coordinates."""
    if preview_image is None or crop_result is None:
        return None
    contour = getattr(crop_result, "contour_points", None)
    if contour is None:
        return None
    original_size = getattr(crop_result, "original_size", None)
    if not original_size or len(original_size) < 2:
        return None

    orig_w = float(original_size[0] or 0)
    orig_h = float(original_size[1] or 0)
    if orig_w <= 0 or orig_h <= 0:
        return None

    preview_h, preview_w = preview_image.shape[:2]
    sx = float(preview_w) / orig_w
    sy = float(preview_h) / orig_h
    points = np.array(contour, dtype=np.float32).reshape((-1, 2)).copy()
    points[:, 0] *= sx
    points[:, 1] *= sy
    return points


def normalize_contour_points(
    points: Any,
    image_shape: Any,
) -> Optional[np.ndarray]:
    """Normalize contour points to [0, 1] coordinates."""
    if points is None or image_shape is None:
        return None
    try:
        pts = np.array(points, dtype=np.float32).reshape((-1, 2)).copy()
        if len(pts) != 4:
            return None
        h, w = image_shape[:2]
        if w <= 0 or h <= 0:
            return None
        pts[:, 0] = np.clip(pts[:, 0] / float(w), 0.0, 1.0)
        pts[:, 1] = np.clip(pts[:, 1] / float(h), 0.0, 1.0)
        return pts
    except Exception:
        return None


def denormalize_contour_points(
    normalized_points: Any,
    image_shape: Any,
) -> Optional[np.ndarray]:
    """Convert normalized contour points back to pixel coordinates."""
    if normalized_points is None or image_shape is None:
        return None
    try:
        pts = np.array(normalized_points, dtype=np.float32).reshape((-1, 2)).copy()
        if len(pts) != 4:
            return None
        h, w = image_shape[:2]
        if w <= 0 or h <= 0:
            return None
        pts[:, 0] = np.clip(pts[:, 0] * float(w), 0.0, float(max(0, w - 1)))
        pts[:, 1] = np.clip(pts[:, 1] * float(h), 0.0, float(max(0, h - 1)))
        return pts
    except Exception:
        return None


def axis_aligned_crop(
    image: np.ndarray,
    contour_points: Any,
) -> Optional[np.ndarray]:
    """Crop an image using the axis-aligned bounding box of a 4-point contour."""
    if image is None or contour_points is None:
        return None
    try:
        pts = np.array(contour_points, dtype=np.float32).reshape((-1, 2))
    except Exception:
        return None
    if len(pts) != 4:
        return None

    x_min = int(np.floor(float(np.min(pts[:, 0]))))
    y_min = int(np.floor(float(np.min(pts[:, 1]))))
    x_max = int(np.ceil(float(np.max(pts[:, 0]))))
    y_max = int(np.ceil(float(np.max(pts[:, 1]))))

    img_h, img_w = image.shape[:2]
    x_min = max(0, min(x_min, max(0, img_w - 1)))
    y_min = max(0, min(y_min, max(0, img_h - 1)))
    x_max = max(x_min + 1, min(x_max, img_w))
    y_max = max(y_min + 1, min(y_max, img_h))

    if x_max <= x_min or y_max <= y_min:
        return None
    return image[y_min:y_max, x_min:x_max].copy()


def crop_manual_contour(
    image: np.ndarray,
    contour_points: Any,
    *,
    perspective_correct: bool,
    use_gpu: bool = False,
) -> Optional[np.ndarray]:
    """
    Crop an image from a manually edited contour using the same crop-mode
    decision as the manual-save path.
    """
    if image is None or contour_points is None:
        return None
    try:
        pts = np.array(contour_points, dtype=np.float32).reshape((-1, 2))
    except Exception:
        return None
    if len(pts) != 4:
        return None

    if not perspective_correct:
        return axis_aligned_crop(image, pts)

    from ..advanced import AdvancedImageProcessor

    processor = AdvancedImageProcessor(use_gpu=use_gpu)
    result = processor.correct_perspective(
        image,
        pts.astype(np.float32),
        auto_detect=False,
    )
    if not result.success or result.image is None:
        return None
    return result.image


def is_boundary_detection_failure(message: str) -> bool:
    """Return True when message indicates boundary detection failure."""
    if not message:
        return False
    msg = str(message).strip()
    msg_lower = msg.lower()
    if "failed to detect photo boundary" in msg_lower:
        return True
    if "boundary" in msg_lower and ("detect" in msg_lower or "failed" in msg_lower):
        return True
    if "외곽선" in msg and ("탐지" in msg or "실패" in msg):
        return True
    if "경계" in msg and ("탐지" in msg or "실패" in msg):
        return True
    return False


def collect_boundary_failed_files(
    results: Iterable[Any],
    input_root: str,
    image_list: Iterable[str],
    batch_failed_entries: Iterable[str],
    recursive_search: bool,
    get_image_files_fn: Callable[[str, bool], List[str]],
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    """Collect absolute file paths failed due to boundary-detection errors."""
    failed_names: List[str] = []
    for result in results or []:
        if str(getattr(result, "status", None)) != "ProcessStatus.FAILED":
            # Keep compatibility with enum-like values from caller.
            status = getattr(result, "status", None)
            if getattr(status, "name", "") != "FAILED":
                continue
        message = str(getattr(result, "message", "") or "")
        if not is_boundary_detection_failure(message):
            continue
        filename = str(getattr(result, "filename", "") or "").strip()
        if filename:
            failed_names.append(filename)

    if not failed_names:
        return []

    candidate_paths: List[str] = []

    for entry in batch_failed_entries or []:
        if not entry:
            continue
        if os.path.isabs(entry):
            candidate_paths.append(os.path.normpath(entry))
        elif input_root:
            candidate_paths.append(os.path.normpath(os.path.join(input_root, entry)))

    for path in image_list or []:
        if path:
            candidate_paths.append(os.path.normpath(path))

    if input_root and os.path.isdir(input_root):
        for path in get_image_files_fn(input_root, recursive_search):
            candidate_paths.append(os.path.normpath(path))

    candidates_by_name: dict[str, List[str]] = {}
    for path in candidate_paths:
        key = os.path.basename(path).lower()
        if not key:
            continue
        bucket = candidates_by_name.setdefault(key, [])
        if path not in bucket:
            bucket.append(path)

    resolved: List[str] = []
    unresolved: List[str] = []
    for name in failed_names:
        chosen = None
        if os.path.isabs(name) and os.path.exists(name):
            chosen = os.path.normpath(name)
        else:
            key = os.path.basename(name).lower()
            bucket = candidates_by_name.get(key, [])
            if bucket:
                chosen = bucket.pop(0)
        if chosen and chosen not in resolved:
            resolved.append(chosen)
        else:
            unresolved.append(name)

    if unresolved and logger is not None:
        logger.warning(
            "Failed to resolve boundary-failed files: %s",
            ", ".join(unresolved[:10]),
        )

    return resolved
