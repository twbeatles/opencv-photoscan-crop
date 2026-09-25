from __future__ import annotations

import json
import logging
import os
from typing import Any

from ..app_paths import get_legacy_presets_file, get_legacy_profiles_dir
from .record import RecipeRecord
from .snapshot import _normalize_settings_dict

logger = logging.getLogger(__name__)


class RecipeManagerMigrationMixin:
    """Legacy (batch-profile/preset) one-shot migration for RecipeManager."""

    _repository: Any
    _fallback_cache: dict[str, dict[str, Any]]

    def save_recipe(self, recipe: RecipeRecord) -> bool:
        raise NotImplementedError

    def _save_fallback_cache(self) -> None:
        raise NotImplementedError

    def _migrate_legacy_sources(self) -> None:
        migrated_flag = self._get_migration_flag()
        if migrated_flag == "1":
            return

        profiles_path = os.path.join(get_legacy_profiles_dir(), "batch_profiles.json")
        self._migrate_legacy_profiles(profiles_path)
        self._migrate_legacy_presets(get_legacy_presets_file())
        self._set_migration_flag("1")

    def _get_migration_flag(self) -> str:
        if self._repository is not None:
            try:
                return self._repository.get_app_state("recipes_legacy_migrated", "")
            except Exception:
                logger.debug("Failed to read recipe migration flag", exc_info=True)
        return self._fallback_cache.get("__meta__", {}).get("recipes_legacy_migrated", "")

    def _set_migration_flag(self, value: str) -> None:
        if self._repository is not None:
            try:
                self._repository.set_app_state("recipes_legacy_migrated", value)
            except Exception:
                logger.debug("Failed to persist recipe migration flag", exc_info=True)
        meta = dict(self._fallback_cache.get("__meta__", {}) or {})
        meta["recipes_legacy_migrated"] = value
        self._fallback_cache["__meta__"] = meta
        self._save_fallback_cache()

    def _migrate_legacy_profiles(self, profiles_path: str) -> None:
        if not os.path.exists(profiles_path):
            return
        try:
            with open(profiles_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for name, data in dict(payload.get("profiles", {}) or {}).items():
                self.save_recipe(
                    RecipeRecord(
                        name=str(name),
                        description=str(data.get("description", "")),
                        settings_snapshot=_normalize_settings_dict(
                            dict(data.get("settings", {}) or {})
                        ),
                        category_rules=_normalize_settings_dict(
                            dict(data.get("category_rules", {}) or {})
                        ),
                        origin="legacy_profile",
                    )
                )
        except Exception as exc:
            logger.warning("Legacy profile migration failed: %s", exc)

    def _migrate_legacy_presets(self, presets_path: str) -> None:
        if not os.path.exists(presets_path):
            return
        try:
            with open(presets_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for name, data in dict(payload or {}).items():
                snapshot = {
                    key: value
                    for key, value in dict(data or {}).items()
                    if key
                    in {
                        "algorithm",
                        "processing",
                        "advanced",
                        "output",
                        "filter",
                        "performance",
                        "classification",
                        "face_detection",
                        "smart_enhancement",
                        "resize",
                        "watermark",
                    }
                }
                self.save_recipe(
                    RecipeRecord(
                        name=str(name),
                        description=str(data.get("description", "")),
                        settings_snapshot=_normalize_settings_dict(snapshot),
                        origin="legacy_preset",
                    )
                )
        except Exception as exc:
            logger.warning("Legacy preset migration failed: %s", exc)


__all__ = ["RecipeManagerMigrationMixin"]
