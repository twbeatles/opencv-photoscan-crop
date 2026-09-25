from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from ..app_paths import get_recipes_fallback_file
from ..library import get_library_repository
from ..settings_model import AppSettings
from .defaults import DEFAULT_RECIPES
from .migration import RecipeManagerMigrationMixin
from .record import RecipeRecord
from .snapshot import (
    _deep_merge,
    _default_settings_snapshot,
    _extract_preserved_state,
    _normalize_recipe_snapshot,
    _normalize_settings_dict,
    _now_iso,
)

logger = logging.getLogger(__name__)


class RecipeManager(RecipeManagerMigrationMixin):
    EXPORT_EXTENSION = ".photocropper"

    def __init__(self):
        self._repository = None
        self._fallback_path = get_recipes_fallback_file()
        self._fallback_cache: dict[str, dict[str, Any]] = {}
        self._current_recipe_name: str = ""

        try:
            self._repository = get_library_repository()
        except Exception as exc:
            logger.warning("Recipe repository unavailable, using JSON fallback: %s", exc)
            self._repository = None

        self._load_fallback_cache()
        self._ensure_defaults()
        self._migrate_legacy_sources()

    @property
    def repository_available(self) -> bool:
        return self._repository is not None

    def _load_fallback_cache(self) -> None:
        self._fallback_cache = {}
        if not os.path.exists(self._fallback_path):
            return
        try:
            with open(self._fallback_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            recipes = dict(payload.get("recipes", {}) or {})
            self._current_recipe_name = str(payload.get("current_recipe", "") or "")
            for name, recipe_payload in recipes.items():
                recipe = RecipeRecord.from_payload(recipe_payload)
                if not recipe.name:
                    recipe.name = str(name)
                self._fallback_cache[recipe.name] = recipe.to_dict()
        except Exception as exc:
            logger.warning("Failed to load fallback recipes: %s", exc)

    def _save_fallback_cache(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._fallback_path) or ".", exist_ok=True)
            with open(self._fallback_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "recipes": self._fallback_cache,
                        "current_recipe": self._current_recipe_name,
                        "saved_at": _now_iso(),
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as exc:
            logger.warning("Failed to persist fallback recipes: %s", exc)

    def _set_current_recipe(self, name: str) -> None:
        self._current_recipe_name = str(name or "")
        if self._repository is not None:
            try:
                self._repository.set_app_state("current_recipe", self._current_recipe_name)
            except Exception:
                logger.debug("Failed to persist current recipe to repository", exc_info=True)
        self._save_fallback_cache()

    def _get_current_recipe(self) -> str:
        if self._current_recipe_name:
            return self._current_recipe_name
        if self._repository is not None:
            try:
                self._current_recipe_name = self._repository.get_app_state(
                    "current_recipe", ""
                )
            except Exception:
                logger.debug("Failed to read current recipe from repository", exc_info=True)
        return self._current_recipe_name

    def _ensure_defaults(self) -> None:
        for recipe in DEFAULT_RECIPES.values():
            if self.get_recipe(recipe.name) is None:
                self.save_recipe(recipe)

    def _list_fallback_recipes(self) -> list[RecipeRecord]:
        result: list[RecipeRecord] = []
        for name, payload in self._fallback_cache.items():
            if name == "__meta__":
                continue
            result.append(RecipeRecord.from_payload(payload))
        result.sort(key=lambda recipe: (recipe.origin != "default", recipe.name.lower()))
        return result

    def list_recipes(self) -> list[RecipeRecord]:
        if self._repository is not None:
            try:
                rows = self._repository.list_recipes()
                return [RecipeRecord.from_payload(row) for row in rows]
            except Exception as exc:
                logger.warning("Recipe repository read failed, using fallback: %s", exc)
                self._repository = None
        return self._list_fallback_recipes()

    def list_profiles(self) -> list[str]:
        return [recipe.name for recipe in self.list_recipes()]

    def list_presets(self) -> list[str]:
        return self.list_profiles()

    def get_recipe(self, name: str) -> Optional[RecipeRecord]:
        if self._repository is not None:
            try:
                row = self._repository.get_recipe(name)
                if row is not None:
                    return RecipeRecord.from_payload(row)
            except Exception as exc:
                logger.warning("Recipe repository lookup failed, using fallback: %s", exc)
                self._repository = None
        payload = self._fallback_cache.get(str(name or ""))
        if payload is None:
            return None
        return RecipeRecord.from_payload(payload)

    def get_profile(self, name: str) -> Optional[RecipeRecord]:
        return self.get_recipe(name)

    def get_preset(self, name: str) -> Optional[dict[str, Any]]:
        recipe = self.get_recipe(name)
        if recipe is None:
            return None
        payload = dict(recipe.settings_snapshot or {})
        payload["description"] = recipe.description
        return payload

    def get_preset_description(self, name: str) -> str:
        recipe = self.get_recipe(name)
        return recipe.description if recipe is not None else ""

    def is_default_recipe(self, name: str) -> bool:
        recipe = self.get_recipe(name)
        return bool(recipe and recipe.origin == "default")

    def is_default_profile(self, name: str) -> bool:
        return self.is_default_recipe(name)

    def is_default_preset(self, name: str) -> bool:
        return self.is_default_recipe(name)

    def save_recipe(self, recipe: RecipeRecord) -> bool:
        record = RecipeRecord.from_payload(recipe.to_dict())
        record.settings_snapshot = _normalize_recipe_snapshot(
            dict(record.settings_snapshot or {})
        )
        now = _now_iso()
        if not record.created_at:
            record.created_at = now
        record.updated_at = now

        if self._repository is not None:
            try:
                self._repository.upsert_recipe(
                    name=record.name,
                    description=record.description,
                    settings_snapshot=dict(record.settings_snapshot or {}),
                    category_rules=dict(record.category_rules or {}),
                    origin=record.origin or "user",
                )
            except Exception as exc:
                logger.warning("Recipe repository save failed, switching to fallback: %s", exc)
                self._repository = None

        self._fallback_cache[record.name] = record.to_dict()
        self._save_fallback_cache()
        return True

    def create_profile(
        self,
        name: str,
        settings: AppSettings,
        description: str = "",
        category_rules: Optional[dict] = None,
    ) -> bool:
        if not str(name or "").strip():
            return False
        return self.save_recipe(
            RecipeRecord(
                name=str(name).strip(),
                description=description,
                settings_snapshot=_normalize_settings_dict(settings.to_dict()),
                category_rules=_normalize_settings_dict(dict(category_rules or {})),
                origin="user",
            )
        )

    def update_profile(
        self,
        name: str,
        settings: Optional[AppSettings] = None,
        description: Optional[str] = None,
        category_rules: Optional[dict] = None,
    ) -> bool:
        recipe = self.get_recipe(name)
        if recipe is None or recipe.origin == "default":
            return False
        if settings is not None:
            recipe.settings_snapshot = _normalize_settings_dict(settings.to_dict())
        if description is not None:
            recipe.description = description
        if category_rules is not None:
            recipe.category_rules = _normalize_settings_dict(dict(category_rules or {}))
        return self.save_recipe(recipe)

    def save_preset(self, name: str, settings: AppSettings, description: str = "") -> bool:
        return self.create_profile(name, settings, description=description)

    def _apply_snapshot(self, snapshot: dict[str, Any], settings: AppSettings) -> bool:
        base = _default_settings_snapshot()
        merged = _deep_merge(base, _normalize_recipe_snapshot(snapshot))
        merged = _deep_merge(merged, _extract_preserved_state(settings))
        rebuilt = AppSettings.from_dict(merged)
        for field_name in settings.__dataclass_fields__:
            setattr(settings, field_name, getattr(rebuilt, field_name))
        return True

    def apply_recipe(self, name: str, settings: AppSettings) -> bool:
        recipe = self.get_recipe(name)
        if recipe is None:
            return False
        applied = self._apply_snapshot(dict(recipe.settings_snapshot or {}), settings)
        if applied:
            self._set_current_recipe(name)
        return applied

    def apply_profile(self, name: str, settings: AppSettings) -> bool:
        return self.apply_recipe(name, settings)

    def apply_preset(self, name: str, settings: AppSettings) -> bool:
        return self.apply_recipe(name, settings)

    def apply_category_rules(self, name: str, category: str, settings: AppSettings) -> bool:
        recipe = self.get_recipe(name)
        if recipe is None:
            return False
        rules = dict((recipe.category_rules or {}).get(str(category or "").lower(), {}) or {})
        if not rules:
            return False
        base = _normalize_settings_dict(settings.to_dict())
        merged = _deep_merge(base, _normalize_settings_dict(rules))
        merged = _deep_merge(merged, _extract_preserved_state(settings))
        rebuilt = AppSettings.from_dict(merged)
        for field_name in settings.__dataclass_fields__:
            setattr(settings, field_name, getattr(rebuilt, field_name))
        return True

    def delete_recipe(self, name: str) -> bool:
        if self.is_default_recipe(name):
            return False
        if self._repository is not None:
            try:
                self._repository.delete_recipe(name)
            except Exception:
                logger.debug("Failed to delete recipe from repository", exc_info=True)
        self._fallback_cache.pop(name, None)
        if self._get_current_recipe() == name:
            self._set_current_recipe("")
        self._save_fallback_cache()
        return True

    def delete_profile(self, name: str) -> bool:
        return self.delete_recipe(name)

    def delete_preset(self, name: str) -> bool:
        return self.delete_recipe(name)

    def rename_recipe(self, old_name: str, new_name: str) -> bool:
        if self.is_default_recipe(old_name):
            return False
        new_name = str(new_name or "").strip()
        if not new_name or self.get_recipe(new_name) is not None:
            return False
        recipe = self.get_recipe(old_name)
        if recipe is None:
            return False
        if self._repository is not None:
            try:
                renamed = self._repository.rename_recipe(old_name, new_name)
                if not renamed:
                    return False
            except Exception:
                logger.debug("Failed to rename recipe in repository", exc_info=True)
        self._fallback_cache.pop(old_name, None)
        recipe.name = new_name
        self._fallback_cache[new_name] = recipe.to_dict()
        if self._get_current_recipe() == old_name:
            self._set_current_recipe(new_name)
        self._save_fallback_cache()
        return True

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        return self.rename_recipe(old_name, new_name)

    def export_recipe(self, name: str, export_path: str) -> bool:
        recipe = self.get_recipe(name)
        if recipe is None:
            return False
        output_path = export_path
        if not output_path.endswith(self.EXPORT_EXTENSION):
            output_path += self.EXPORT_EXTENSION
        payload = {
            "type": "photo_cropper_recipe",
            "version": "10.0",
            "recipe": recipe.to_dict(),
            "exported_at": _now_iso(),
        }
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return True

    def export_profile(self, name: str, export_path: str) -> bool:
        return self.export_recipe(name, export_path)

    def import_recipe(
        self,
        import_path: str,
        new_name: Optional[str] = None,
    ) -> Optional[RecipeRecord]:
        try:
            with open(import_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if payload.get("type") not in {"photo_cropper_profile", "photo_cropper_recipe"}:
                return None
            recipe = RecipeRecord.from_payload(payload.get("recipe") or payload.get("profile") or {})
            if new_name:
                recipe.name = str(new_name)
            base_name = recipe.name
            counter = 1
            while self.get_recipe(recipe.name) is not None:
                recipe.name = f"{base_name} ({counter})"
                counter += 1
            recipe.origin = "imported"
            self.save_recipe(recipe)
            return recipe
        except Exception as exc:
            logger.error("Recipe import failed: %s", exc)
            return None

    def import_profile(self, import_path: str, new_name: Optional[str] = None) -> Optional[RecipeRecord]:
        return self.import_recipe(import_path, new_name=new_name)

    def duplicate_profile(self, name: str, new_name: str) -> bool:
        recipe = self.get_recipe(name)
        if recipe is None or self.get_recipe(new_name) is not None:
            return False
        recipe.name = str(new_name)
        recipe.origin = "user"
        recipe.created_at = ""
        recipe.updated_at = ""
        return self.save_recipe(recipe)

    def get_quick_profiles(self) -> list[str]:
        return [recipe.name for recipe in self.list_recipes()[:8]]

    def get_current_recipe_name(self) -> str:
        return self._get_current_recipe()


_recipe_manager_instance: Optional[RecipeManager] = None


def get_recipe_manager() -> RecipeManager:
    global _recipe_manager_instance
    if _recipe_manager_instance is None:
        _recipe_manager_instance = RecipeManager()
    return _recipe_manager_instance


__all__ = ["RecipeManager", "RecipeRecord", "DEFAULT_RECIPES", "get_recipe_manager"]
