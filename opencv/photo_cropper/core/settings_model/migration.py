from __future__ import annotations

from typing import Iterable, Mapping


def normalize_category_folder_map(
    incoming: Mapping[str, object] | None,
    *,
    category_keys: Iterable[str],
    legacy_defaults: Mapping[str, str],
) -> dict[str, str]:
    """Normalize stored category folders and migrate legacy defaults to sentinels."""
    raw_map = dict(incoming or {})
    normalized: dict[str, str] = {}
    for key in category_keys:
        raw_name = str(raw_map.get(key, "") or "").strip()
        if not raw_name or raw_name == legacy_defaults.get(key, ""):
            normalized[key] = ""
        else:
            normalized[key] = raw_name
    return normalized


__all__ = ["normalize_category_folder_map"]
