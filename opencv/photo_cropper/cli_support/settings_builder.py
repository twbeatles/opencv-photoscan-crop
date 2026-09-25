#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI-to-settings merge for the Photo Cropper CLI.

Single responsibility: apply the highest-priority layer (CLI flags)
onto the merged settings dict and build the final ``AppSettings``.

Merge priority: CLI > config file > preset profile > defaults.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict

try:
    from ..core.settings_model import AppSettings
except ImportError:  # Support direct execution: python photo_cropper/cli.py
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from photo_cropper.core.settings_model import AppSettings

from .settings_sources import (
    _deep_merge,
    _load_config_settings,
    _load_preset_settings,
    _parse_resize_spec,
    _set_nested,
)

logger = logging.getLogger(__name__)


def _apply_cli_overrides(settings_data: Dict[str, Any], args: argparse.Namespace) -> None:
    if args.recursive:
        _set_nested(settings_data, "file_management.recursive_search", True)

    if args.skip_processed:
        _set_nested(settings_data, "filter.skip_processed", True)

    if args.jobs is not None:
        thread_count = max(1, int(args.jobs))
        _set_nested(settings_data, "performance.thread_count", thread_count)
        _set_nested(settings_data, "performance.enable_multithreading", thread_count > 1)

    if args.detect_mode is not None:
        _set_nested(settings_data, "algorithm.detection_mode", args.detect_mode)

    if args.canny_min is not None:
        _set_nested(settings_data, "algorithm.canny_min", int(args.canny_min))

    if args.canny_max is not None:
        _set_nested(settings_data, "algorithm.canny_max", int(args.canny_max))

    if args.min_area_ratio is not None:
        _set_nested(settings_data, "algorithm.min_area_ratio", float(args.min_area_ratio))

    if args.max_area_ratio is not None:
        _set_nested(settings_data, "algorithm.max_area_ratio", float(args.max_area_ratio))

    if args.bg_mask_delta is not None:
        _set_nested(settings_data, "algorithm.bg_mask_delta", float(args.bg_mask_delta))

    if args.adaptive_block_size is not None:
        _set_nested(
            settings_data,
            "algorithm.adaptive_block_size",
            int(args.adaptive_block_size),
        )

    if args.adaptive_c is not None:
        _set_nested(settings_data, "algorithm.adaptive_c", float(args.adaptive_c))

    if args.debug_detect:
        _set_nested(settings_data, "debug.enabled", True)

    if args.format is not None:
        _set_nested(settings_data, "output.output_format", args.format.upper())

    if args.quality is not None:
        _set_nested(settings_data, "output.jpg_quality", int(args.quality))
        _set_nested(settings_data, "output.webp_quality", int(args.quality))

    if args.png_compression is not None:
        _set_nested(settings_data, "output.png_compression", int(args.png_compression))

    if args.preserve_metadata:
        _set_nested(settings_data, "output.preserve_metadata", True)

    if args.perspective_correct is not None:
        _set_nested(
            settings_data,
            "advanced.perspective_correct",
            bool(args.perspective_correct),
        )

    if args.watermark is not None:
        _set_nested(settings_data, "watermark.enabled", True)
        _set_nested(settings_data, "watermark.text", args.watermark)

    if args.watermark_image is not None:
        _set_nested(settings_data, "watermark.enabled", True)
        _set_nested(settings_data, "watermark.image_path", args.watermark_image)

    scene_preset = getattr(args, "scene_preset", None)
    if scene_preset:
        try:
            from ..core.scene_presets import apply_scene_preset
            from ..core.settings_model import AppSettings as _AS

            # Apply scene preset on current merged dict via AppSettings round-trip.
            tmp = _AS.from_dict(settings_data)
            apply_scene_preset(tmp, str(scene_preset))
            settings_data.clear()
            settings_data.update(tmp.to_dict())
        except Exception as exc:
            logger.warning("Failed to apply scene preset '%s': %s", scene_preset, exc)

    if args.multi_photo:
        _set_nested(settings_data, "multi_photo.enabled", True)

    if args.multi_photo_merge_distance is not None:
        _set_nested(settings_data, "multi_photo.enabled", True)
        _set_nested(
            settings_data,
            "multi_photo.merge_distance",
            int(args.multi_photo_merge_distance),
        )

    if args.multi_photo_separate_folders:
        _set_nested(settings_data, "multi_photo.enabled", True)
        _set_nested(settings_data, "multi_photo.separate_output_folders", True)

    refine_flag = getattr(args, "multi_photo_refine", None)
    if refine_flag is not None:
        _set_nested(settings_data, "multi_photo.refine_with_single", bool(refine_flag))

    if args.max_size is not None:
        _set_nested(settings_data, "resize.enabled", True)
        _set_nested(settings_data, "resize.mode", "max_dimension")
        _set_nested(settings_data, "resize.max_dimension", int(args.max_size))

    if args.resize is not None:
        resize_patch = _parse_resize_spec(args.resize)
        resize_root = settings_data.get("resize")
        if not isinstance(resize_root, dict):
            resize_root = {}
            settings_data["resize"] = resize_root
        _deep_merge(resize_root, resize_patch)

    if args.backup:
        _set_nested(settings_data, "create_backup", True)

    # AI options (core toggle set)
    if args.classify:
        _set_nested(settings_data, "classification.enabled", True)

    if args.classify_model is not None:
        classify_model = str(args.classify_model or "").strip().lower()
        if classify_model == "custom":
            logger.warning(
                "CLI classify model 'custom' is deprecated and will be treated as 'advanced'."
            )
            classify_model = "advanced"
        _set_nested(settings_data, "classification.model", classify_model)

    if args.classify_min_confidence is not None:
        _set_nested(
            settings_data,
            "classification.min_confidence",
            float(args.classify_min_confidence),
        )

    if args.classify_auto_folder is not None:
        _set_nested(
            settings_data,
            "classification.auto_folder",
            bool(args.classify_auto_folder),
        )

    if args.face_detect:
        _set_nested(settings_data, "face_detection.enabled", True)

    if args.face_dnn:
        _set_nested(settings_data, "face_detection.enabled", True)
        _set_nested(settings_data, "face_detection.use_dnn", True)

    if args.face_min_size is not None:
        _set_nested(settings_data, "face_detection.min_face_size", int(args.face_min_size))

    if args.face_auto_center_crop:
        _set_nested(settings_data, "face_detection.auto_center_crop", True)

    if args.face_auto_rotate:
        _set_nested(settings_data, "face_detection.auto_rotate", True)

    if args.smart_enhance:
        _set_nested(settings_data, "smart_enhancement.enabled", True)

    if args.smart_strength is not None:
        _set_nested(settings_data, "smart_enhancement.strength", int(args.smart_strength))

    if args.smart_no_exposure:
        _set_nested(settings_data, "smart_enhancement.adjust_exposure", False)

    if args.smart_no_color_balance:
        _set_nested(settings_data, "smart_enhancement.adjust_color_balance", False)


def build_settings_from_args(args: argparse.Namespace) -> AppSettings:
    # 1) defaults
    merged = AppSettings().to_dict()

    # 2) preset
    if args.preset:
        preset_data = _load_preset_settings(args.preset)
        _deep_merge(merged, preset_data)

    # 3) config
    if args.config:
        config_data = _load_config_settings(args.config)
        _deep_merge(merged, config_data)

    # 4) cli overrides
    _apply_cli_overrides(merged, args)

    return AppSettings.from_dict(merged)


__all__ = ["_apply_cli_overrides", "build_settings_from_args"]
