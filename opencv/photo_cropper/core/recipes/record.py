from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .snapshot import _normalize_recipe_snapshot, _normalize_settings_dict


@dataclass
class RecipeRecord:
    name: str
    description: str = ""
    settings_snapshot: dict[str, Any] | None = None
    category_rules: dict[str, Any] | None = None
    origin: str = "user"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "settings_snapshot": self.settings_snapshot or {},
            "category_rules": self.category_rules or {},
            "origin": self.origin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RecipeRecord":
        raw_snapshot = payload.get("settings_snapshot", {})
        if isinstance(raw_snapshot, str):
            try:
                raw_snapshot = json.loads(raw_snapshot)
            except Exception:
                raw_snapshot = {}
        raw_rules = payload.get("category_rules", {})
        if isinstance(raw_rules, str):
            try:
                raw_rules = json.loads(raw_rules)
            except Exception:
                raw_rules = {}
        return cls(
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            settings_snapshot=_normalize_recipe_snapshot(dict(raw_snapshot or {})),
            category_rules=_normalize_settings_dict(dict(raw_rules or {})),
            origin=str(payload.get("origin", "user") or "user"),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )


__all__ = ["RecipeRecord"]
