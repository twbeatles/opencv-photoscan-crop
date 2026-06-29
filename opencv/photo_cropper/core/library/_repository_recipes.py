from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryRecipeMixin:
    def upsert_recipe(
        self: LibraryRepositoryProtocol,
        *,
        name: str,
        description: str,
        settings_snapshot: dict[str, Any],
        category_rules: Optional[dict[str, Any]] = None,
        origin: str = "user",
    ) -> None:
        now = now_iso()
        payload = json.dumps(settings_snapshot or {}, ensure_ascii=False, sort_keys=True)
        rules = json.dumps(category_rules or {}, ensure_ascii=False, sort_keys=True)
        with self.store.write_connect() as conn:
            existing = conn.execute(
                "SELECT id, created_at FROM recipes WHERE name = ?",
                (name,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO recipes(name, description, settings_snapshot, category_rules, origin, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, description, payload, rules, origin, now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE recipes
                    SET description = ?, settings_snapshot = ?, category_rules = ?, origin = ?, updated_at = ?
                    WHERE name = ?
                    """,
                    (description, payload, rules, origin, now, name),
                )
            conn.commit()
    def list_recipes(self: LibraryRepositoryProtocol) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT name, description, settings_snapshot, category_rules, origin, created_at, updated_at
                FROM recipes
                ORDER BY name
                """
            ).fetchall()
            return [dict(row) for row in rows]
    def get_recipe(self: LibraryRepositoryProtocol, name: str) -> Optional[dict[str, Any]]:
        with self.store.connect() as conn:
            row = conn.execute(
                """
                SELECT name, description, settings_snapshot, category_rules, origin, created_at, updated_at
                FROM recipes
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
            return dict(row) if row is not None else None
    def delete_recipe(self: LibraryRepositoryProtocol, name: str) -> None:
        with self.store.write_connect() as conn:
            conn.execute("DELETE FROM recipes WHERE name = ?", (name,))
            conn.commit()
    def rename_recipe(self: LibraryRepositoryProtocol, old_name: str, new_name: str) -> bool:
        with self.store.write_connect() as conn:
            existing = conn.execute("SELECT 1 FROM recipes WHERE name = ?", (new_name,)).fetchone()
            if existing is not None:
                return False
            conn.execute(
                "UPDATE recipes SET name = ?, updated_at = ? WHERE name = ?",
                (new_name, now_iso(), old_name),
            )
            conn.commit()
            return True
    def set_app_state(self: LibraryRepositoryProtocol, key: str, value: str) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (str(key), str(value), now_iso()),
            )
            conn.commit()
    def get_app_state(self: LibraryRepositoryProtocol, key: str, default: str = "") -> str:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key = ?",
                (str(key),),
            ).fetchone()
            if row is None:
                return default
            return str(row["value"] or default)
