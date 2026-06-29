#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility wrapper for the unified recipe manager."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .recipes import RecipeRecord, get_recipe_manager
from .settings_model import AppSettings

logger = logging.getLogger(__name__)

_LEGACY_SETTINGS_KEY_ALIASES = {
    "advanced_processing": "advanced",
}


@dataclass
class BatchProfile:
    name: str
    description: str = ""
    settings: Optional[Dict[str, Any]] = None
    category_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = ""
    modified_at: str = ""
    version: str = "10.0"

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at
        if self.settings is None:
            self.settings = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "settings": self.settings or {},
            "category_rules": self.category_rules or {},
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchProfile":
        return cls(
            name=str(data.get("name", "Unknown")),
            description=str(data.get("description", "")),
            settings=dict(data.get("settings", {}) or {}),
            category_rules=dict(data.get("category_rules", {}) or {}),
            created_at=str(data.get("created_at", "")),
            modified_at=str(data.get("modified_at", "")),
            version=str(data.get("version", "10.0")),
        )


DEFAULT_PROFILES: Dict[str, BatchProfile] = {}


class BatchProfileManager:
    EXPORT_EXTENSION = ".photocropper"

    def __init__(self, profiles_dir: Optional[str] = None):
        self._profiles_dir = profiles_dir or ""
        self._recipe_manager = get_recipe_manager()
        self._profiles: Dict[str, BatchProfile] = {}
        self._current_profile: Optional[str] = (
            self._recipe_manager.get_current_recipe_name() or None
        )
        self._sync_from_recipes()

    @classmethod
    def _normalize_settings_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            normalized: Dict[str, Any] = {}
            for key, value in data.items():
                key_str = str(key)
                mapped_key = _LEGACY_SETTINGS_KEY_ALIASES.get(key_str, key_str)
                normalized_value = cls._normalize_settings_dict(value)
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
            return [cls._normalize_settings_dict(item) for item in data]
        return data

    @classmethod
    def _deep_merge_settings_dict(
        cls,
        base: Dict[str, Any],
        override: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = copy.deepcopy(base)
        for key, value in (override or {}).items():
            resolved_key = _LEGACY_SETTINGS_KEY_ALIASES.get(str(key), str(key))
            if (
                resolved_key in merged
                and isinstance(merged[resolved_key], dict)
                and isinstance(value, dict)
            ):
                merged[resolved_key] = cls._deep_merge_settings_dict(
                    merged[resolved_key], value
                )
            else:
                merged[resolved_key] = copy.deepcopy(value)
        return merged

    def _profile_from_recipe(self, recipe: RecipeRecord) -> BatchProfile:
        return BatchProfile(
            name=recipe.name,
            description=recipe.description,
            settings=self._normalize_settings_dict(
                dict(recipe.settings_snapshot or {})
            ),
            category_rules=self._normalize_settings_dict(
                dict(recipe.category_rules or {})
            ),
            created_at=recipe.created_at,
            modified_at=recipe.updated_at or recipe.created_at,
        )

    def _sync_from_recipes(self) -> None:
        recipe_profiles = {
            recipe.name: self._profile_from_recipe(recipe)
            for recipe in self._recipe_manager.list_recipes()
        }
        for name, profile in list(self._profiles.items()):
            if name not in recipe_profiles:
                recipe_profiles[name] = profile
        self._profiles = recipe_profiles

    def list_profiles(self) -> List[str]:
        self._sync_from_recipes()
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[BatchProfile]:
        self._sync_from_recipes()
        return self._profiles.get(name)

    def get_current_profile(self) -> Optional[BatchProfile]:
        if self._current_profile:
            return self.get_profile(self._current_profile)
        return None

    def set_current_profile(self, name: str) -> bool:
        if name not in self.list_profiles():
            return False
        self._current_profile = name
        return True

    def is_default_profile(self, name: str) -> bool:
        return self._recipe_manager.is_default_profile(name)

    def create_profile(
        self,
        name: str,
        settings: AppSettings,
        description: str = "",
        category_rules: Optional[Dict] = None,
    ) -> bool:
        ok = self._recipe_manager.create_profile(
            name,
            settings,
            description=description,
            category_rules=self._normalize_settings_dict(category_rules or {}),
        )
        self._sync_from_recipes()
        return ok

    def update_profile(
        self,
        name: str,
        settings: Optional[AppSettings] = None,
        description: Optional[str] = None,
        category_rules: Optional[Dict] = None,
    ) -> bool:
        if name in self._profiles and self._recipe_manager.get_profile(name) is None:
            profile = self._profiles[name]
            if settings is not None:
                profile.settings = self._normalize_settings_dict(settings.to_dict())
            if description is not None:
                profile.description = description
            if category_rules is not None:
                profile.category_rules = self._normalize_settings_dict(category_rules or {})
            profile.modified_at = datetime.now().isoformat()
            return True

        ok = self._recipe_manager.update_profile(
            name,
            settings=settings,
            description=description,
            category_rules=self._normalize_settings_dict(category_rules or {})
            if category_rules is not None
            else None,
        )
        self._sync_from_recipes()
        return ok

    def delete_profile(self, name: str) -> bool:
        if name in self._profiles and self._recipe_manager.get_profile(name) is None:
            if self.is_default_profile(name):
                return False
            del self._profiles[name]
            return True
        ok = self._recipe_manager.delete_profile(name)
        if ok:
            self._profiles.pop(name, None)
        return ok

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        if old_name in self._profiles and self._recipe_manager.get_profile(old_name) is None:
            if self.is_default_profile(old_name) or new_name in self._profiles:
                return False
            profile = self._profiles.pop(old_name)
            profile.name = new_name
            profile.modified_at = datetime.now().isoformat()
            self._profiles[new_name] = profile
            if self._current_profile == old_name:
                self._current_profile = new_name
            return True
        ok = self._recipe_manager.rename_profile(old_name, new_name)
        self._sync_from_recipes()
        if ok and self._current_profile == old_name:
            self._current_profile = new_name
        return ok

    def apply_profile(self, name: str, settings: AppSettings) -> bool:
        profile = self.get_profile(name)
        if profile is None:
            return False

        if self._recipe_manager.get_profile(name) is not None:
            ok = self._recipe_manager.apply_profile(name, settings)
        else:
            base_data = self._normalize_settings_dict(settings.to_dict())
            override_data = self._normalize_settings_dict(profile.settings or {})
            merged = self._deep_merge_settings_dict(base_data, override_data)
            rebuilt = AppSettings.from_dict(merged)
            for field_name in settings.__dataclass_fields__:
                setattr(settings, field_name, getattr(rebuilt, field_name))
            ok = True

        if ok:
            self._current_profile = name
        return ok

    def apply_category_rules(
        self,
        name: str,
        category: str,
        settings: AppSettings,
    ) -> bool:
        profile = self.get_profile(name)
        if profile is None or not profile.category_rules:
            return False
        rules = dict((profile.category_rules or {}).get(str(category or "").lower(), {}) or {})
        if not rules:
            return False
        base_data = self._normalize_settings_dict(settings.to_dict())
        merged = self._deep_merge_settings_dict(base_data, self._normalize_settings_dict(rules))
        rebuilt = AppSettings.from_dict(merged)
        for field_name in settings.__dataclass_fields__:
            setattr(settings, field_name, getattr(rebuilt, field_name))
        return True

    def export_profile(self, name: str, export_path: str) -> bool:
        return self._recipe_manager.export_profile(name, export_path)

    def import_profile(
        self,
        import_path: str,
        new_name: Optional[str] = None,
    ) -> Optional[BatchProfile]:
        recipe = self._recipe_manager.import_profile(import_path, new_name=new_name)
        self._sync_from_recipes()
        if recipe is None:
            return None
        return self._profiles.get(recipe.name)

    def get_quick_profiles(self) -> List[str]:
        self._sync_from_recipes()
        return self._recipe_manager.get_quick_profiles()

    def duplicate_profile(self, name: str, new_name: str) -> bool:
        if name in self._profiles and self._recipe_manager.get_profile(name) is None:
            profile = self.get_profile(name)
            if profile is None or new_name in self._profiles:
                return False
            self._profiles[new_name] = BatchProfile(
                name=new_name,
                description=f"{profile.description} (Copy)",
                settings=self._normalize_settings_dict(profile.settings or {}),
                category_rules=self._normalize_settings_dict(profile.category_rules or {}),
            )
            return True
        ok = self._recipe_manager.duplicate_profile(name, new_name)
        self._sync_from_recipes()
        return ok


_manager_instance: Optional[BatchProfileManager] = None


def get_batch_profile_manager() -> BatchProfileManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = BatchProfileManager()
    return _manager_instance
