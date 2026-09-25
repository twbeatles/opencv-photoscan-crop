from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from ..settings_model import AppSettings

_LEGACY_KEY_ALIASES = {
    "advanced_processing": "advanced",
}
_RECIPE_PRESERVED_KEYS = (
    "ui",
    "notification",
    "last_input_path",
    "last_output_path",
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_settings_dict(data: Any) -> Any:
    if isinstance(data, dict):
        normalized: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key)
            mapped_key = _LEGACY_KEY_ALIASES.get(key_str, key_str)
            normalized_value = _normalize_settings_dict(value)
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
        return [_normalize_settings_dict(item) for item in data]
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in dict(override or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(dict(merged[key]), dict(value))
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _default_settings_snapshot() -> dict[str, Any]:
    return _normalize_settings_dict(AppSettings().to_dict())


def _normalize_recipe_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return _deep_merge(_default_settings_snapshot(), _normalize_settings_dict(snapshot))


def _extract_preserved_state(settings: AppSettings) -> dict[str, Any]:
    current = _normalize_settings_dict(settings.to_dict())
    preserved: dict[str, Any] = {}
    for key in _RECIPE_PRESERVED_KEYS:
        if key in current:
            preserved[key] = copy.deepcopy(current[key])
    return preserved


__all__ = [
    "_normalize_settings_dict",
    "_deep_merge",
    "_default_settings_snapshot",
    "_normalize_recipe_snapshot",
    "_extract_preserved_state",
    "_now_iso",
]
