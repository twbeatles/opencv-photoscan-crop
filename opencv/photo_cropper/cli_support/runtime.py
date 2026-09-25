#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for Photo Cropper.

Configuration merge priority:
    CLI > config file > preset profile > defaults

Compatibility facade: the implementation now lives in focused modules
(:mod:`.arg_types`, :mod:`.settings_sources`, :mod:`.settings_builder`,
:mod:`.parser`, :mod:`.batch_runner`). Every public name historically
available on this module is re-exported here, so ``photo_cropper.cli``
(which aliases this module) and existing tests keep working unchanged.
"""

from __future__ import annotations

import logging
import os
import sys
import time  # Re-exported seam: tests patch `runtime.time.sleep` via this module.

try:
    from ..core.batch_profile_manager import get_batch_profile_manager
    from ..core.settings_model import AppSettings
    from ..core.settings_model.validation import build_validation_summary, validate_settings
    from ..utils.file_helpers import is_output_inside_input
except ImportError:
    # Support direct execution: python photo_cropper/cli.py
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from photo_cropper.core.batch_profile_manager import get_batch_profile_manager
    from photo_cropper.core.settings_model import AppSettings
    from photo_cropper.core.settings_model.validation import (
        build_validation_summary,
        validate_settings,
    )
    from photo_cropper.utils.file_helpers import is_output_inside_input


from .arg_types import _float_in_range, _int_in_range
from .batch_runner import (
    _configure_logging,
    _list_presets,
    _validate_io_paths,
    main,
    process_batch,
)
from .parser import create_parser
from .settings_builder import _apply_cli_overrides, build_settings_from_args
from .settings_sources import (
    _deep_merge,
    _load_config_settings,
    _load_preset_settings,
    _normalize_legacy_keys,
    _parse_resize_spec,
    _read_json_file,
    _set_nested,
)

logger = logging.getLogger(__name__)

__all__ = [
    "time",
    "get_batch_profile_manager",
    "AppSettings",
    "build_validation_summary",
    "validate_settings",
    "is_output_inside_input",
    "_int_in_range",
    "_float_in_range",
    "_normalize_legacy_keys",
    "_deep_merge",
    "_set_nested",
    "_read_json_file",
    "_parse_resize_spec",
    "_load_preset_settings",
    "_load_config_settings",
    "_apply_cli_overrides",
    "build_settings_from_args",
    "_configure_logging",
    "_validate_io_paths",
    "_list_presets",
    "process_batch",
    "create_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
