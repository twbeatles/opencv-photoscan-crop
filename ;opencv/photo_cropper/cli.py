#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for Photo Cropper.

Configuration merge priority:
    CLI > config file > preset profile > defaults
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, Optional, Tuple

try:
    from .core.batch_profile_manager import get_batch_profile_manager
    from .core.settings_model import AppSettings
except ImportError:
    # Support direct execution: python photo_cropper/cli.py
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from photo_cropper.core.batch_profile_manager import get_batch_profile_manager
    from photo_cropper.core.settings_model import AppSettings


logger = logging.getLogger(__name__)

_LEGACY_KEY_ALIASES = {
    "advanced_processing": "advanced",
}

_RESIZE_PRESETS: Dict[str, Tuple[str, int, int]] = {
    "instagram_square": ("fit", 1080, 1080),
    "instagram_story": ("fit", 1080, 1920),
    "facebook_cover": ("fit", 820, 312),
    "a4": ("fit", 2480, 3508),
}


def _int_in_range(min_value: int, max_value: int):
    def _parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Expected integer, got: {value}") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"Expected value in range [{min_value}, {max_value}], got: {parsed}"
            )
        return parsed

    return _parse


def _float_in_range(min_value: float, max_value: float):
    def _parse(value: str) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Expected float, got: {value}") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"Expected value in range [{min_value}, {max_value}], got: {parsed}"
            )
        return parsed

    return _parse


def _normalize_legacy_keys(data: Any) -> Any:
    if isinstance(data, dict):
        normalized: Dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key)
            mapped_key = _LEGACY_KEY_ALIASES.get(key_str, key_str)
            normalized_value = _normalize_legacy_keys(value)
            if (
                mapped_key in normalized
                and isinstance(normalized[mapped_key], dict)
                and isinstance(normalized_value, dict)
            ):
                normalized[mapped_key].update(normalized_value)
            else:
                normalized[mapped_key] = normalized_value
        return normalized
    if isinstance(data, list):
        return [_normalize_legacy_keys(item) for item in data]
    return data


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _set_nested(data: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = data
    for key in parts[:-1]:
        child = cursor.get(key)
        if not isinstance(child, dict):
            child = {}
            cursor[key] = child
        cursor = child
    cursor[parts[-1]] = value


def _read_json_file(path: str) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError("Config root must be a JSON object")
            return loaded
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Failed to read JSON file '{path}': {last_error}")


def _parse_resize_spec(value: str) -> Dict[str, Any]:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Resize spec is empty")

    key = raw.lower()
    if key in _RESIZE_PRESETS:
        mode, width, height = _RESIZE_PRESETS[key]
        return {
            "enabled": True,
            "mode": mode,
            "width": int(width),
            "height": int(height),
        }

    if key.endswith("%"):
        number = key[:-1].strip()
        try:
            percentage = float(number)
        except ValueError as exc:
            raise ValueError(f"Invalid percentage resize spec: {raw}") from exc
        if percentage <= 0:
            raise ValueError("Resize percentage must be > 0")
        return {
            "enabled": True,
            "mode": "percentage",
            "percentage": percentage,
        }

    match = re.fullmatch(r"(\d+)x(\d+)", key)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        if width <= 0 or height <= 0:
            raise ValueError("Resize dimensions must be > 0")
        return {
            "enabled": True,
            "mode": "fit",
            "width": width,
            "height": height,
        }

    if key.isdigit():
        max_dimension = int(key)
        if max_dimension <= 0:
            raise ValueError("Max dimension must be > 0")
        return {
            "enabled": True,
            "mode": "max_dimension",
            "max_dimension": max_dimension,
        }

    raise ValueError(
        "Invalid resize spec. Use one of: '50%%', '1200x900', integer max size, or preset name."
    )


def _load_preset_settings(preset_name: str) -> Dict[str, Any]:
    manager = get_batch_profile_manager()
    profile = manager.get_profile(preset_name)
    if profile is None:
        available = ", ".join(sorted(manager.list_profiles()))
        raise ValueError(
            f"Preset not found: '{preset_name}'. Available presets: {available}"
        )
    return _normalize_legacy_keys(profile.settings or {})


def _load_config_settings(config_path: str) -> Dict[str, Any]:
    loaded = _read_json_file(config_path)

    # Accept either AppSettings-style root or exported profile-like envelope.
    if "settings" in loaded and isinstance(loaded.get("settings"), dict):
        loaded = loaded["settings"]

    return _normalize_legacy_keys(loaded)


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
        _set_nested(settings_data, "classification.model", args.classify_model)

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


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _validate_io_paths(input_dir: str, output_dir: str) -> None:
    if not input_dir:
        raise ValueError("Input directory is required")
    if not output_dir:
        raise ValueError("Output directory is required")
    if not os.path.isdir(input_dir):
        raise ValueError(f"Input directory does not exist: {input_dir}")


def _list_presets() -> int:
    manager = get_batch_profile_manager()
    names = sorted(manager.list_profiles())
    if not names:
        print("No presets available")
        return 0
    print("Available presets:")
    for name in names:
        print(f"- {name}")
    return 0


def process_batch(args: argparse.Namespace) -> int:
    try:
        from .core.batch import BatchProcessor
    except ImportError:
        from photo_cropper.core.batch import BatchProcessor

    try:
        _validate_io_paths(args.input, args.output)
        os.makedirs(args.output, exist_ok=True)

        settings = build_settings_from_args(args)
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    processor = BatchProcessor(settings)

    def on_log(message: str, level: str) -> None:
        level = str(level or "info").lower()
        if level in {"error", "warning"}:
            print(message, file=sys.stderr)
        else:
            print(message)

    processor.set_callbacks(on_log=on_log)

    if not processor.start_async(args.input, args.output):
        print("ERROR: Failed to start batch processing", file=sys.stderr)
        return 2

    cancelled = False
    try:
        while processor.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Cancellation requested...")
        processor.request_stop()
        processor.wait_for_completion(timeout=10.0)
        cancelled = True

    progress = processor.progress
    if progress.is_cancelled:
        cancelled = True
    print(
        "Summary: "
        f"processed={progress.processed}, "
        f"success={progress.success}, "
        f"failed={progress.failed}, "
        f"skipped={progress.skipped}"
    )

    if cancelled:
        return 130
    if progress.failed > 0:
        return 1
    return 0


def create_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python -m photo_cropper.cli -i ./scans -o ./out --preset '문서 스캔'\n"
        "  python -m photo_cropper.cli -i ./scans -o ./out --config ./settings.json --skip-processed\n"
        "  python -m photo_cropper.cli -i ./scans -o ./out --classify --face-detect --smart-enhance"
    )

    parser = argparse.ArgumentParser(
        prog="photo_cropper.cli",
        description="Batch photo cropper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    # Core I/O
    parser.add_argument("-i", "--input", help="Input directory")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--list-presets", action="store_true", help="List available preset names")

    # Merge sources
    parser.add_argument("--preset", help="Preset profile name (applied before --config)")
    parser.add_argument("--config", help="JSON settings file path")

    # General processing
    parser.add_argument("--recursive", action="store_true", help="Enable recursive input search")
    parser.add_argument("--skip-processed", action="store_true", help="Skip already processed files")
    parser.add_argument("--jobs", type=_int_in_range(1, 64), help="Worker thread count")
    parser.add_argument(
        "--detect-mode",
        choices=["fast", "balanced", "accurate"],
        help="Detection mode",
    )
    parser.add_argument("--canny-min", type=_int_in_range(0, 255), help="Canny minimum threshold")
    parser.add_argument("--canny-max", type=_int_in_range(1, 255), help="Canny maximum threshold")
    parser.add_argument(
        "--min-area-ratio",
        type=_float_in_range(0.01, 0.9),
        help="Minimum detected area ratio",
    )
    parser.add_argument(
        "--max-area-ratio",
        type=_float_in_range(0.1, 1.0),
        help="Maximum detected area ratio",
    )
    parser.add_argument(
        "--bg-mask-delta",
        type=_float_in_range(5.0, 80.0),
        help="Background-mask threshold delta",
    )
    parser.add_argument(
        "--adaptive-block-size",
        type=_int_in_range(3, 61),
        help="Adaptive threshold block size (odd values recommended)",
    )
    parser.add_argument(
        "--adaptive-c",
        type=_float_in_range(-20.0, 20.0),
        help="Adaptive threshold C offset",
    )
    parser.add_argument("--debug-detect", action="store_true", help="Enable detection debug outputs")

    # Output / post
    parser.add_argument("--format", choices=["JPG", "PNG", "WEBP"], help="Output format")
    parser.add_argument("--quality", type=_int_in_range(1, 100), help="JPG/WEBP quality")
    parser.add_argument(
        "--png-compression",
        type=_int_in_range(0, 9),
        help="PNG compression level",
    )
    parser.add_argument(
        "--preserve-metadata",
        action="store_true",
        help="Best-effort preserve EXIF/ICC metadata",
    )
    perspective_group = parser.add_mutually_exclusive_group()
    perspective_group.add_argument(
        "--perspective-correct",
        dest="perspective_correct",
        action="store_true",
        default=None,
        help="Enable perspective correction (warp)",
    )
    perspective_group.add_argument(
        "--no-perspective-correct",
        dest="perspective_correct",
        action="store_false",
        default=None,
        help="Disable perspective warp and use axis-aligned crop",
    )
    parser.add_argument("--watermark", help="Text watermark")
    parser.add_argument("--watermark-image", help="Image watermark path")
    parser.add_argument("--resize", help="Resize spec (50%%, 1200x900, 1920, instagram_square)")
    parser.add_argument("--max-size", type=_int_in_range(1, 20000), help="Resize max dimension")
    parser.add_argument("--multi-photo", action="store_true", help="Enable multi-photo split mode")
    parser.add_argument(
        "--multi-photo-merge-distance",
        type=_int_in_range(0, 1000),
        help="Distance threshold for multi-photo duplicate merge",
    )
    parser.add_argument(
        "--multi-photo-separate-folders",
        action="store_true",
        help="Store multi-photo outputs in <input>_photos subfolder",
    )
    parser.add_argument("--backup", action="store_true", help="Create backups")

    # AI core toggles
    parser.add_argument("--classify", action="store_true", help="Enable image classification")
    parser.add_argument(
        "--classify-model",
        choices=["basic", "advanced", "custom"],
        help="Classification model",
    )
    parser.add_argument(
        "--classify-min-confidence",
        type=_float_in_range(0.0, 1.0),
        help="Minimum classification confidence",
    )
    classify_folder_group = parser.add_mutually_exclusive_group()
    classify_folder_group.add_argument(
        "--classify-auto-folder",
        dest="classify_auto_folder",
        action="store_true",
        default=None,
        help="Enable auto-folder routing for classification",
    )
    classify_folder_group.add_argument(
        "--no-classify-auto-folder",
        dest="classify_auto_folder",
        action="store_false",
        default=None,
        help="Disable auto-folder routing for classification",
    )

    parser.add_argument("--face-detect", action="store_true", help="Enable face detection")
    parser.add_argument("--face-dnn", action="store_true", help="Use DNN face detector")
    parser.add_argument(
        "--face-min-size",
        type=_int_in_range(20, 500),
        help="Minimum face size in pixels",
    )
    parser.add_argument(
        "--face-auto-center-crop",
        action="store_true",
        help="Center crop around faces",
    )
    parser.add_argument(
        "--face-auto-rotate",
        action="store_true",
        help="Auto-rotate using eye alignment",
    )

    parser.add_argument("--smart-enhance", action="store_true", help="Enable smart enhancement")
    parser.add_argument(
        "--smart-strength",
        type=_int_in_range(0, 100),
        help="Smart enhancement strength",
    )
    parser.add_argument(
        "--smart-no-exposure",
        action="store_true",
        help="Disable smart exposure adjustment",
    )
    parser.add_argument(
        "--smart-no-color-balance",
        action="store_true",
        help="Disable smart color-balance adjustment",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    if args.list_presets:
        return _list_presets()

    if not args.input or not args.output:
        parser.error("--input and --output are required unless --list-presets is used")

    return process_batch(args)


if __name__ == "__main__":
    raise SystemExit(main())
