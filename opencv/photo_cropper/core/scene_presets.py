#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scene presets for common scan / photo layouts.

Presets update AlgorithmSettings (and optionally MultiPhotoSettings flags)
so beginners can skip low-level Canny/Adaptive knobs.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Dict, Optional, Tuple

from .settings_model import AlgorithmSettings, AppSettings, MultiPhotoSettings


# id -> (display_key, description_key) — UI resolves via i18n or fallback labels
SCENE_PRESET_META: Dict[str, Tuple[str, str]] = {
    "scanner_white": ("Scanner (white bed)", "Bright scanner background, single photo"),
    "desk_photo": ("Desk / table", "Photo on a desk or mixed surface"),
    "dark_background": ("Dark background", "Dark cloth or low-key background"),
    "album_multi": ("Album page (multi)", "Multiple photos on one page"),
    "document": ("Document / paper", "Documents and flat paper sheets"),
    "custom": ("Custom (keep current)", "Do not change algorithm values"),
}


def build_algorithm_for_scene(scene_id: str, base: Optional[AlgorithmSettings] = None) -> AlgorithmSettings:
    """Return AlgorithmSettings tuned for a scene preset."""
    algo = deepcopy(base) if base is not None else AlgorithmSettings()
    sid = (scene_id or "custom").strip().lower()

    if sid == "custom":
        return algo

    if sid == "scanner_white":
        return replace(
            algo,
            detection_mode="balanced",
            canny_min=50,
            canny_max=150,
            use_clahe=True,
            multi_scale_edge=True,
            bg_mask_delta=28.0,
            adaptive_block_size=15,
            adaptive_c=4.0,
            min_area_ratio=0.08,
            max_area_ratio=0.96,
            contour_scoring="enhanced",
        )

    if sid == "desk_photo":
        return replace(
            algo,
            detection_mode="accurate",
            canny_min=40,
            canny_max=140,
            use_clahe=True,
            multi_scale_edge=True,
            bg_mask_delta=35.0,
            adaptive_block_size=17,
            adaptive_c=3.0,
            min_area_ratio=0.06,
            max_area_ratio=0.95,
            contour_scoring="enhanced",
        )

    if sid == "dark_background":
        return replace(
            algo,
            detection_mode="balanced",
            canny_min=35,
            canny_max=120,
            use_clahe=True,
            multi_scale_edge=True,
            bg_mask_delta=25.0,
            adaptive_block_size=15,
            adaptive_c=5.0,
            min_area_ratio=0.08,
            max_area_ratio=0.96,
            contour_scoring="enhanced",
        )

    if sid == "album_multi":
        return replace(
            algo,
            detection_mode="accurate",
            canny_min=45,
            canny_max=145,
            use_clahe=True,
            multi_scale_edge=True,
            bg_mask_delta=30.0,
            adaptive_block_size=13,
            adaptive_c=3.5,
            min_area_ratio=0.04,
            max_area_ratio=0.90,
            contour_scoring="enhanced",
        )

    if sid == "document":
        return replace(
            algo,
            detection_mode="accurate",
            canny_min=60,
            canny_max=180,
            use_clahe=True,
            multi_scale_edge=True,
            bg_mask_delta=22.0,
            adaptive_block_size=21,
            adaptive_c=6.0,
            min_area_ratio=0.15,
            max_area_ratio=0.98,
            contour_scoring="strict",
        )

    return algo


def apply_scene_preset(settings: AppSettings, scene_id: str) -> AppSettings:
    """
    Apply a scene preset onto a full AppSettings object (mutates + returns).
    """
    sid = (scene_id or "custom").strip().lower()
    if sid == "custom":
        return settings

    settings.algorithm = build_algorithm_for_scene(sid, settings.algorithm)

    multi = settings.multi_photo if isinstance(settings.multi_photo, MultiPhotoSettings) else MultiPhotoSettings()
    if sid == "album_multi":
        multi.enabled = True
        multi.refine_with_single = True
        multi.min_area_ratio = min(multi.min_area_ratio, 0.02)
        multi.max_area_ratio = max(multi.max_area_ratio, 0.55)
    elif sid in ("scanner_white", "desk_photo", "dark_background", "document"):
        # Keep multi as-is except ensure refine is on for quality when multi later enabled.
        multi.refine_with_single = True
    settings.multi_photo = multi
    return settings


__all__ = [
    "SCENE_PRESET_META",
    "build_algorithm_for_scene",
    "apply_scene_preset",
]
