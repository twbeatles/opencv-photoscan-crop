#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File helper utilities for Photo Cropper.

Compatibility facade: the implementation now lives in focused modules
(:mod:`.paths`, :mod:`.scanning`, :mod:`.hashing`, :mod:`.file_ops`).
Every public name historically imported from this module is re-exported
here, so existing ``from ...utils.file_helpers import ...`` imports keep
working unchanged.
"""

import logging

from .file_ops import (
    classify_failed_files,
    format_file_size,
    get_file_size,
    move_to_subfolder,
    open_file_explorer,
)
from .hashing import (
    compute_file_hash,
    detect_duplicates,
    get_image_dimensions,
)
from .paths import (
    is_output_inside_input,
    is_path_within,
    normalize_path,
    relative_display_path,
    relative_parent_dir,
)
from .scanning import (
    SUPPORTED_IMAGE_FORMATS,
    build_recursive_excluded_roots,
    ensure_directory,
    get_folder_stats,
    get_image_files,
    get_image_files_with_info,
    get_unique_filename,
    validate_directory,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SUPPORTED_IMAGE_FORMATS",
    "normalize_path",
    "is_path_within",
    "is_output_inside_input",
    "relative_parent_dir",
    "relative_display_path",
    "build_recursive_excluded_roots",
    "get_image_files",
    "ensure_directory",
    "get_unique_filename",
    "get_file_size",
    "format_file_size",
    "open_file_explorer",
    "validate_directory",
    "get_image_files_with_info",
    "compute_file_hash",
    "detect_duplicates",
    "get_image_dimensions",
    "move_to_subfolder",
    "classify_failed_files",
    "get_folder_stats",
]
