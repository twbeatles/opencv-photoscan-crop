from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryAssetSearchMixin:
    def _asset_search_fields(self: LibraryRepositoryProtocol, conn: Any, asset_id: int) -> dict[str, str]:
        row = conn.execute(
            """
            SELECT
                COALESCE(a.note, '') AS note,
                COALESCE(a.display_name, '') AS display_name
            FROM assets a
            WHERE a.id = ?
            """,
            (asset_id,),
        ).fetchone()
        tags = [
            str(item["name"])
            for item in conn.execute(
                """
                SELECT t.name
                FROM tags t
                JOIN asset_tags at ON at.tag_id = t.id
                WHERE at.asset_id = ?
                ORDER BY t.name
                """,
                (asset_id,),
            ).fetchall()
        ]
        collections = [
            str(item["name"])
            for item in conn.execute(
                """
                SELECT c.name
                FROM collections c
                JOIN collection_assets ca ON ca.collection_id = c.id
                WHERE ca.asset_id = ?
                ORDER BY c.name
                """,
                (asset_id,),
            ).fetchall()
        ]
        ocr_text = "\n".join(
            str(item["text"])
            for item in conn.execute(
                """
                SELECT text
                FROM ocr_documents
                WHERE asset_id = ?
                ORDER BY id DESC
                """,
                (asset_id,),
            ).fetchall()
        )
        return {
            "file_name": str(row["display_name"]) if row else "",
            "note": str(row["note"]) if row else "",
            "tags": " ".join(tags),
            "collections": " ".join(collections),
            "ocr_text": ocr_text,
        }
    def refresh_search_index(self: LibraryRepositoryProtocol, asset_id: int) -> None:
        if not self.fts_enabled:
            self.mark_search_index_dirty()
            return
        try:
            with self.store.write_connect() as conn:
                fields = self._asset_search_fields(conn, asset_id)
                conn.execute("DELETE FROM asset_search WHERE asset_id = ?", (asset_id,))
                conn.execute(
                    """
                    INSERT INTO asset_search(asset_id, file_name, note, tags, collections, ocr_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(asset_id),
                        fields["file_name"],
                        fields["note"],
                        fields["tags"],
                        fields["collections"],
                        fields["ocr_text"],
                    ),
                )
                conn.commit()
        except Exception:
            self.mark_search_index_dirty()
    def mark_search_index_dirty(self: LibraryRepositoryProtocol) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES ('search_index_dirty', '1', ?)
                ON CONFLICT(key) DO UPDATE SET value = '1', updated_at = excluded.updated_at
                """,
                (now_iso(),),
            )
            conn.commit()
    def clear_search_index_dirty(self: LibraryRepositoryProtocol) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES ('search_index_dirty', '0', ?)
                ON CONFLICT(key) DO UPDATE SET value = '0', updated_at = excluded.updated_at
                """,
                (now_iso(),),
            )
            conn.commit()
    def get_search_index_dirty(self: LibraryRepositoryProtocol) -> bool:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key = 'search_index_dirty'"
            ).fetchone()
            return str(row["value"] or "") == "1" if row is not None else False
    def rebuild_search_index(self: LibraryRepositoryProtocol) -> int:
        if not self.fts_enabled:
            self.mark_search_index_dirty()
            return 0
        with self.store.write_connect() as conn:
            asset_ids = [
                int(row["id"])
                for row in conn.execute("SELECT id FROM assets ORDER BY id").fetchall()
            ]
            conn.execute("DELETE FROM asset_search")
            for asset_id in asset_ids:
                fields = self._asset_search_fields(conn, asset_id)
                conn.execute(
                    """
                    INSERT INTO asset_search(asset_id, file_name, note, tags, collections, ocr_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset_id,
                        fields["file_name"],
                        fields["note"],
                        fields["tags"],
                        fields["collections"],
                        fields["ocr_text"],
                    ),
                )
            conn.execute(
                """
                INSERT INTO app_state(key, value, updated_at)
                VALUES ('search_index_dirty', '0', ?)
                ON CONFLICT(key) DO UPDATE SET value = '0', updated_at = excluded.updated_at
                """,
                (now_iso(),),
            )
            conn.commit()
            return len(asset_ids)
    def search_asset_ids(self: LibraryRepositoryProtocol, text: str) -> list[int]:
        query = str(text or "").strip()
        if not query:
            return []
        with self.store.connect() as conn:
            if self.fts_enabled:
                try:
                    rows = conn.execute(
                        "SELECT asset_id FROM asset_search WHERE asset_search MATCH ?",
                        (query,),
                    ).fetchall()
                    return [int(row["asset_id"]) for row in rows]
                except Exception:
                    pass
            like = f"%{query.lower()}%"
            rows = conn.execute(
                """
                SELECT DISTINCT a.id AS asset_id
                FROM assets a
                LEFT JOIN asset_sources s ON s.asset_id = a.id
                LEFT JOIN asset_tags at ON at.asset_id = a.id
                LEFT JOIN tags t ON t.id = at.tag_id
                LEFT JOIN collection_assets ca ON ca.asset_id = a.id
                LEFT JOIN collections c ON c.id = ca.collection_id
                LEFT JOIN ocr_documents od ON od.asset_id = a.id
                WHERE lower(a.display_name) LIKE ?
                   OR lower(a.note) LIKE ?
                   OR lower(COALESCE(s.source_path, '')) LIKE ?
                   OR lower(COALESCE(t.name, '')) LIKE ?
                   OR lower(COALESCE(c.name, '')) LIKE ?
                   OR lower(COALESCE(od.text, '')) LIKE ?
                """,
                (like, like, like, like, like, like),
            ).fetchall()
            return [int(row["asset_id"]) for row in rows]
    def set_asset_note(self: LibraryRepositoryProtocol, asset_id: int, note: str) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                "UPDATE assets SET note = ?, updated_at = ? WHERE id = ?",
                (str(note or ""), now_iso(), int(asset_id)),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
