from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryMetadataMixin:
    def create_collection(self: LibraryRepositoryProtocol, name: str, description: str = "") -> Optional[int]:
        text = str(name or "").strip()
        if not text:
            return None
        now = now_iso()
        with self.store.write_connect() as conn:
            existing = conn.execute(
                "SELECT id FROM collections WHERE name = ?",
                (text,),
            ).fetchone()
            if existing is not None:
                return int(existing["id"])
            cur = conn.execute(
                """
                INSERT INTO collections(name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (text, str(description or ""), now, now),
            )
            conn.commit()
            return int(cur.lastrowid or 0)
    def delete_collection(self: LibraryRepositoryProtocol, collection_id: int) -> None:
        with self.store.write_connect() as conn:
            conn.execute("DELETE FROM collection_assets WHERE collection_id = ?", (int(collection_id),))
            conn.execute("DELETE FROM collections WHERE id = ?", (int(collection_id),))
            conn.commit()
    def list_collections(self: LibraryRepositoryProtocol) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.*,
                    (
                        SELECT COUNT(*)
                        FROM collection_assets ca
                        WHERE ca.collection_id = c.id
                    ) AS asset_count
                FROM collections c
                ORDER BY c.name
                """
            ).fetchall()
            return [dict(row) for row in rows]
    def list_collections_for_asset(self: LibraryRepositoryProtocol, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*
                FROM collections c
                JOIN collection_assets ca ON ca.collection_id = c.id
                WHERE ca.asset_id = ?
                ORDER BY c.name
                """,
                (int(asset_id),),
            ).fetchall()
            return [dict(row) for row in rows]
    def add_asset_to_collection(self: LibraryRepositoryProtocol, asset_id: int, collection_id: int) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO collection_assets(collection_id, asset_id, created_at)
                VALUES (?, ?, ?)
                """,
                (int(collection_id), int(asset_id), now_iso()),
            )
            conn.execute(
                "UPDATE collections SET updated_at = ? WHERE id = ?",
                (now_iso(), int(collection_id)),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
    def add_assets_to_collection(self: LibraryRepositoryProtocol, asset_ids: list[int], collection_id: int) -> int:
        unique_ids = sorted({int(item) for item in asset_ids if int(item) > 0})
        if not unique_ids:
            return 0
        with self.store.write_connect() as conn:
            for asset_id in unique_ids:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO collection_assets(collection_id, asset_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (int(collection_id), asset_id, now_iso()),
                )
            conn.execute(
                "UPDATE collections SET updated_at = ? WHERE id = ?",
                (now_iso(), int(collection_id)),
            )
            conn.commit()
        for asset_id in unique_ids:
            self.refresh_search_index(asset_id)
        return len(unique_ids)
    def remove_asset_from_collection(self: LibraryRepositoryProtocol, asset_id: int, collection_id: int) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                "DELETE FROM collection_assets WHERE collection_id = ? AND asset_id = ?",
                (int(collection_id), int(asset_id)),
            )
            conn.execute(
                "UPDATE collections SET updated_at = ? WHERE id = ?",
                (now_iso(), int(collection_id)),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
    def ensure_tag(self: LibraryRepositoryProtocol, name: str, *, kind: str = "user") -> Optional[int]:
        text = str(name or "").strip()
        if not text:
            return None
        with self.store.write_connect() as conn:
            existing = conn.execute("SELECT id FROM tags WHERE name = ?", (text,)).fetchone()
            if existing is not None:
                return int(existing["id"])
            cur = conn.execute(
                "INSERT INTO tags(name, kind, created_at) VALUES (?, ?, ?)",
                (text, kind, now_iso()),
            )
            conn.commit()
            return int(cur.lastrowid or 0)
    def list_tags_for_asset(self: LibraryRepositoryProtocol, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.id, t.name, t.kind, at.source, at.confidence
                FROM tags t
                JOIN asset_tags at ON at.tag_id = t.id
                WHERE at.asset_id = ?
                ORDER BY t.name
                """,
                (int(asset_id),),
            ).fetchall()
            return [dict(row) for row in rows]
    def list_tags(self: LibraryRepositoryProtocol) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.id,
                    t.name,
                    t.kind,
                    (
                        SELECT COUNT(*)
                        FROM asset_tags at
                        WHERE at.tag_id = t.id
                    ) AS asset_count
                FROM tags t
                ORDER BY t.name
                """
            ).fetchall()
            return [dict(row) for row in rows]
    def clear_asset_tags(self: LibraryRepositoryProtocol, asset_id: int, *, source: Optional[str] = None) -> None:
        with self.store.write_connect() as conn:
            if source is None:
                conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (int(asset_id),))
            else:
                conn.execute(
                    "DELETE FROM asset_tags WHERE asset_id = ? AND source = ?",
                    (int(asset_id), source),
                )
            conn.commit()
        self.refresh_search_index(asset_id)
    def add_asset_tag(
        self: LibraryRepositoryProtocol,
        asset_id: int,
        name: str,
        *,
        source: str = "user",
        confidence: float = 1.0,
        kind: str = "user",
    ) -> None:
        tag_id = self.ensure_tag(name, kind=kind)
        if tag_id is None:
            return
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO asset_tags(asset_id, tag_id, source, confidence, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (int(asset_id), int(tag_id), source, float(confidence), now_iso()),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
    def remove_asset_tag(self: LibraryRepositoryProtocol, asset_id: int, tag_name: str) -> None:
        text = str(tag_name or "").strip()
        if not text:
            return
        with self.store.write_connect() as conn:
            conn.execute(
                """
                DELETE FROM asset_tags
                WHERE asset_id = ? AND tag_id IN (
                    SELECT id FROM tags WHERE name = ?
                )
                """,
                (int(asset_id), text),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
    def clear_faces(self: LibraryRepositoryProtocol, asset_id: int, *, variant_id: Optional[int] = None) -> None:
        with self.store.write_connect() as conn:
            if variant_id is None:
                conn.execute("DELETE FROM faces WHERE asset_id = ?", (int(asset_id),))
            else:
                conn.execute(
                    "DELETE FROM faces WHERE asset_id = ? AND variant_id = ?",
                    (int(asset_id), int(variant_id)),
                )
            conn.commit()
    def clear_person_links(self: LibraryRepositoryProtocol, asset_id: int, *, variant_id: Optional[int] = None) -> None:
        with self.store.write_connect() as conn:
            if variant_id is None:
                conn.execute(
                    """
                    DELETE FROM person_faces
                    WHERE face_id IN (
                        SELECT id FROM faces WHERE asset_id = ?
                    )
                    """,
                    (int(asset_id),),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM person_faces
                    WHERE face_id IN (
                        SELECT id FROM faces WHERE asset_id = ? AND variant_id = ?
                    )
                    """,
                    (int(asset_id), int(variant_id)),
                )
            conn.commit()
    def add_face(
        self: LibraryRepositoryProtocol,
        *,
        asset_id: int,
        source_id: Optional[int],
        variant_id: Optional[int],
        x: int,
        y: int,
        w: int,
        h: int,
        confidence: float = 0.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        with self.store.write_connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO faces(
                    asset_id, source_id, variant_id, x, y, w, h, confidence, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(asset_id),
                    int(source_id) if source_id is not None else None,
                    int(variant_id) if variant_id is not None else None,
                    int(x),
                    int(y),
                    int(w),
                    int(h),
                    float(confidence),
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                    now_iso(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid or 0)
    def upsert_person(
        self: LibraryRepositoryProtocol,
        *,
        provider: str,
        external_id: str,
        name: str = "",
    ) -> int:
        provider_name = str(provider or "")
        external_key = str(external_id or "")
        person_name = str(name or "")
        now = now_iso()
        with self.store.write_connect() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM people
                WHERE provider = ? AND external_id = ?
                """,
                (provider_name, external_key),
            ).fetchone()
            if existing is not None:
                person_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE people
                    SET name = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (person_name, now, person_id),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO people(name, provider, external_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (person_name, provider_name, external_key, now, now),
                )
                person_id = int(cur.lastrowid or 0)
            conn.commit()
            return person_id
    def link_person_face(
        self: LibraryRepositoryProtocol,
        *,
        face_id: int,
        person_id: int,
        confidence: float = 1.0,
    ) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO person_faces(face_id, person_id, confidence, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (int(face_id), int(person_id), float(confidence), now_iso()),
            )
            conn.commit()
    def add_ocr_document(
        self: LibraryRepositoryProtocol,
        *,
        asset_id: int,
        source_id: Optional[int],
        variant_id: Optional[int],
        provider: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        with self.store.write_connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO ocr_documents(asset_id, source_id, variant_id, provider, text, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(asset_id),
                    int(source_id) if source_id is not None else None,
                    int(variant_id) if variant_id is not None else None,
                    provider,
                    str(text or ""),
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                    now_iso(),
                ),
            )
            conn.commit()
            document_id = int(cur.lastrowid or 0)
        self.refresh_search_index(asset_id)
        return document_id
    def clear_ocr_documents(self: LibraryRepositoryProtocol, asset_id: int) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                "DELETE FROM ocr_documents WHERE asset_id = ?",
                (int(asset_id),),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
    def list_ocr_documents(self: LibraryRepositoryProtocol, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_id, variant_id, provider, text, metadata_json, created_at
                FROM ocr_documents
                WHERE asset_id = ?
                ORDER BY id DESC
                """,
                (int(asset_id),),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                payload["metadata"] = safe_json_loads(payload.get("metadata_json"), {})
                result.append(payload)
            return result
    def list_faces_for_asset(self: LibraryRepositoryProtocol, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    f.id,
                    f.source_id,
                    f.variant_id,
                    f.x,
                    f.y,
                    f.w,
                    f.h,
                    f.confidence,
                    f.metadata_json,
                    f.created_at
                FROM faces f
                WHERE f.asset_id = ?
                ORDER BY f.id DESC
                """,
                (int(asset_id),),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                payload["metadata"] = safe_json_loads(payload.get("metadata_json"), {})
                result.append(payload)
            return result
    def list_people_for_asset(self: LibraryRepositoryProtocol, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.provider,
                    p.external_id,
                    MAX(pf.confidence) AS confidence,
                    COUNT(*) AS face_count
                FROM people p
                JOIN person_faces pf ON pf.person_id = p.id
                JOIN faces f ON f.id = pf.face_id
                WHERE f.asset_id = ?
                GROUP BY p.id, p.name, p.provider, p.external_id
                ORDER BY p.name, p.id
                """,
                (int(asset_id),),
            ).fetchall()
            return [dict(row) for row in rows]
