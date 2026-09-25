#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Argument parser definition for the Photo Cropper CLI.

Single responsibility: declare every CLI flag (I/O, merge sources,
detection, output/post-processing, multi-photo, AI toggles, logging).
No settings logic and no execution here.
"""

from __future__ import annotations

import argparse

from .arg_types import _float_in_range, _int_in_range


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
    parser.add_argument(
        "--strict-partial",
        action="store_true",
        help="Return exit code 1 when any partial_success result occurs",
    )
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
    parser.add_argument(
        "--scene-preset",
        choices=[
            "scanner_white",
            "desk_photo",
            "dark_background",
            "album_multi",
            "document",
        ],
        help="Apply scene-tuned algorithm defaults (before other CLI overrides)",
    )
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
    refine_group = parser.add_mutually_exclusive_group()
    refine_group.add_argument(
        "--multi-photo-refine",
        dest="multi_photo_refine",
        action="store_true",
        default=None,
        help="Refine each multi-photo ROI with single-photo detection",
    )
    refine_group.add_argument(
        "--no-multi-photo-refine",
        dest="multi_photo_refine",
        action="store_false",
        help="Disable multi-photo ROI refine",
    )
    parser.add_argument("--backup", action="store_true", help="Create backups")

    # AI core toggles
    parser.add_argument("--classify", action="store_true", help="Enable image classification")
    parser.add_argument(
        "--classify-model",
        choices=["basic", "advanced", "custom"],
        help="Classification model ('custom' is a deprecated alias of 'advanced')",
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


__all__ = ["create_parser"]
