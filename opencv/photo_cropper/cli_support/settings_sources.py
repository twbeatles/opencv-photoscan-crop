#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration sources for the Photo Cropper CLI.

Single responsibility: load and normalize the lower-priority settings
layers (preset profiles, JSON config files, legacy keys, resize specs)
and merge them into plain dicts.

The batch-profile manager is resolved through the ``runtime`` facade
instead of a direct import, so tests can keep patching
``cli_support.runtime.get_batch_profile_manager`` as a seam.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, Tuple


_LEGACY_KEY_ALIASES = {
    "advanced_processing": "advanced",
}

_RESIZE_PRESETS: Dict[str, Tuple[str, int, int]] = {
    "instagram_square": ("fit", 1080, 1080),
    "instagram_story": ("fit", 1080, 1920),
    "facebook_cover": ("fit", 820, 312),
    "a4": ("fit", 2480, 3508),
}


def _resolve_profile_manager():
    """Return the batch-profile manager via the runtime facade (patchable seam)."""
    from . import runtime

    return runtime.get_batch_profile_manager()


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
    last_error: Exception | None = None
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
    manager = _resolve_profile_manager()
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


__all__ = [
    "_normalize_legacy_keys",
    "_deep_merge",
    "_set_nested",
    "_read_json_file",
    "_parse_resize_spec",
    "_load_preset_settings",
    "_load_config_settings",
]
