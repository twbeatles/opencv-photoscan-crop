from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import SUPPORTED_IMAGE_FORMATS, compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryAssetSourceMixin:
    def _invalid_source_record(self, source_path: str, error: str) -> dict[str, Any]:
        raw_path = str(source_path or "")
        normalized = os.path.abspath(raw_path) if raw_path.strip() else ""
        return {
            "asset_id": None,
            "source_id": None,
            "source_hash": "",
            "display_name": os.path.basename(normalized) or normalized,
            "source_path": normalized,
            "width": 0,
            "height": 0,
            "perceptual_hash": "",
            "ingest_state": "invalid_source",
            "error": error,
        }
    def upsert_source(self: LibraryRepositoryProtocol, source_path: str, *, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        raw_path = str(source_path or "").strip()
        if not raw_path:
            return self._invalid_source_record(source_path, "empty_path")
        normalized = os.path.abspath(raw_path)
        if not os.path.exists(normalized):
            return self._invalid_source_record(source_path, "missing_file")
        if not os.path.isfile(normalized):
            return self._invalid_source_record(source_path, "not_file")
        if not normalized.lower().endswith(SUPPORTED_IMAGE_FORMATS):
            return self._invalid_source_record(source_path, "unsupported_image_format")
        now = now_iso()
        source_hash = compute_file_hash(normalized, algorithm="sha256") or ""
        if not source_hash:
            return self._invalid_source_record(source_path, "unreadable_file")
        perceptual_hash = compute_perceptual_hash(normalized)
        width = 0
        height = 0
        size = 0
        mtime_ns = 0
        try:
            stat = os.stat(normalized)
            size = int(stat.st_size)
            mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
        except Exception:
            pass
        dims = get_image_dimensions(normalized)
        if dims:
            width, height = int(dims[0]), int(dims[1])
        payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        display_name = os.path.basename(normalized) or normalized

        with self.store.write_connect() as conn:
            existing = conn.execute(
                """
                SELECT s.id AS source_id, s.asset_id AS asset_id
                FROM asset_sources s
                WHERE s.source_path = ?
                """,
                (normalized,),
            ).fetchone()
            ingest_state = "existing"
            if existing is None:
                missing_matches = self._source_candidates_by_hash(
                    conn,
                    source_hash,
                    missing_only=True,
                )
                if len(missing_matches) == 1:
                    source_id = int(missing_matches[0]["source_id"])
                    asset_id = int(missing_matches[0]["asset_id"])
                    conn.execute(
                        """
                        UPDATE asset_sources
                        SET source_path = ?, source_hash = ?, file_size = ?, mtime_ns = ?,
                            width = ?, height = ?, metadata_json = ?, last_seen_at = ?,
                            is_missing = 0
                        WHERE id = ?
                        """,
                        (
                            normalized,
                            source_hash,
                            size,
                            mtime_ns,
                            width,
                            height,
                            payload,
                            now,
                            source_id,
                        ),
                    )
                    conn.execute(
                        """
                        UPDATE assets
                        SET display_name = ?, exact_hash = ?, perceptual_hash = ?,
                            perceptual_hash_updated_at = ?, primary_source_path = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            display_name,
                            source_hash,
                            perceptual_hash,
                            now if perceptual_hash else "",
                            normalized,
                            now,
                            asset_id,
                        ),
                    )
                    ingest_state = "relinked"
                elif len(missing_matches) > 1:
                    return {
                        "asset_id": None,
                        "source_id": None,
                        "source_hash": source_hash,
                        "display_name": display_name,
                        "source_path": normalized,
                        "width": width,
                        "height": height,
                        "perceptual_hash": perceptual_hash,
                        "ingest_state": "ambiguous_relink",
                        "candidate_source_ids": [
                            int(item["source_id"]) for item in missing_matches
                        ],
                        "candidate_asset_ids": [
                            int(item["asset_id"]) for item in missing_matches
                        ],
                    }
                else:
                    asset_cur = conn.execute(
                        """
                        INSERT INTO assets(
                            display_name, note, exact_hash, perceptual_hash,
                            perceptual_hash_updated_at, primary_source_path, created_at, updated_at
                        )
                        VALUES (?, '', ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            display_name,
                            source_hash,
                            perceptual_hash,
                            now if perceptual_hash else "",
                            normalized,
                            now,
                            now,
                        ),
                    )
                    asset_id = int(asset_cur.lastrowid or 0)
                    source_cur = conn.execute(
                        """
                        INSERT INTO asset_sources(
                            asset_id, source_path, source_hash, file_size, mtime_ns,
                            width, height, metadata_json, ingested_at, last_seen_at, is_missing
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (
                            asset_id,
                            normalized,
                            source_hash,
                            size,
                            mtime_ns,
                            width,
                            height,
                            payload,
                            now,
                            now,
                        ),
                    )
                    source_id = int(source_cur.lastrowid or 0)
                    ingest_state = "created"
            else:
                asset_id = int(existing["asset_id"])
                source_id = int(existing["source_id"])
                conn.execute(
                    """
                    UPDATE asset_sources
                    SET source_hash = ?, file_size = ?, mtime_ns = ?, width = ?, height = ?,
                        metadata_json = ?, last_seen_at = ?, is_missing = 0
                    WHERE id = ?
                    """,
                    (source_hash, size, mtime_ns, width, height, payload, now, source_id),
                )
                conn.execute(
                    """
                    UPDATE assets
                    SET display_name = ?, exact_hash = ?, perceptual_hash = ?,
                        perceptual_hash_updated_at = ?, primary_source_path = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        display_name,
                        source_hash,
                        perceptual_hash,
                        now if perceptual_hash else "",
                        normalized,
                        now,
                        asset_id,
                    ),
                )
            conn.commit()
        self.refresh_search_index(asset_id)
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "source_hash": source_hash,
            "display_name": display_name,
            "source_path": normalized,
            "width": width,
            "height": height,
            "perceptual_hash": perceptual_hash,
            "ingest_state": ingest_state,
        }
    def relink_source(self: LibraryRepositoryProtocol, source_id: int, new_path: str) -> Optional[dict[str, Any]]:
        normalized = os.path.abspath(str(new_path or ""))
        if (
            not normalized
            or not os.path.isfile(normalized)
            or not normalized.lower().endswith(SUPPORTED_IMAGE_FORMATS)
        ):
            return None
        source_hash = compute_file_hash(normalized, algorithm="sha256") or ""
        perceptual_hash = compute_perceptual_hash(normalized)
        dims = get_image_dimensions(normalized)
        width, height = (int(dims[0]), int(dims[1])) if dims else (0, 0)
        try:
            stat = os.stat(normalized)
            file_size = int(stat.st_size)
            mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
        except Exception:
            file_size = 0
            mtime_ns = 0
        now = now_iso()
        with self.store.write_connect() as conn:
            row = conn.execute(
                "SELECT asset_id FROM asset_sources WHERE id = ?",
                (int(source_id),),
            ).fetchone()
            if row is None:
                return None
            asset_id = int(row["asset_id"])
            conn.execute(
                """
                UPDATE asset_sources
                SET source_path = ?, source_hash = ?, file_size = ?, mtime_ns = ?,
                    width = ?, height = ?, last_seen_at = ?, is_missing = 0
                WHERE id = ?
                """,
                (
                    normalized,
                    source_hash,
                    file_size,
                    mtime_ns,
                    width,
                    height,
                    now,
                    int(source_id),
                ),
            )
            conn.execute(
                """
                UPDATE assets
                SET display_name = ?, exact_hash = ?, perceptual_hash = ?,
                    perceptual_hash_updated_at = ?, primary_source_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    os.path.basename(normalized) or normalized,
                    source_hash,
                    perceptual_hash,
                    now if perceptual_hash else "",
                    normalized,
                    now,
                    asset_id,
                ),
            )
            conn.commit()
        self.refresh_search_index(asset_id)
        return {
            "asset_id": asset_id,
            "source_id": int(source_id),
            "source_path": normalized,
            "source_hash": source_hash,
        }
    def list_sources_by_ids(self: LibraryRepositoryProtocol, source_ids: list[int]) -> list[dict[str, Any]]:
        unique_ids = sorted({int(item) for item in source_ids if int(item) > 0})
        if not unique_ids:
            return []
        placeholders = ", ".join("?" for _ in unique_ids)
        with self.store.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    s.id AS source_id,
                    s.asset_id,
                    s.source_path,
                    s.source_hash,
                    s.is_missing,
                    a.display_name
                FROM asset_sources s
                JOIN assets a ON a.id = s.asset_id
                WHERE s.id IN ({placeholders})
                ORDER BY a.display_name, s.id
                """,
                unique_ids,
            ).fetchall()
            return [dict(row) for row in rows]
    def scan_missing_sources(self: LibraryRepositoryProtocol) -> dict[str, Any]:
        updated = 0
        missing = 0
        restored = 0
        affected_asset_ids: set[int] = set()
        with self.store.write_connect() as conn:
            rows = conn.execute(
                "SELECT id, asset_id, source_path, is_missing FROM asset_sources"
            ).fetchall()
            for row in rows:
                exists = os.path.exists(str(row["source_path"] or ""))
                new_flag = 0 if exists else 1
                old_flag = int(row["is_missing"] or 0)
                if new_flag != old_flag:
                    conn.execute(
                        """
                        UPDATE asset_sources
                        SET is_missing = ?, last_seen_at = ?
                        WHERE id = ?
                        """,
                        (new_flag, now_iso(), int(row["id"])),
                    )
                    affected_asset_ids.add(int(row["asset_id"]))
                    updated += 1
                    if new_flag:
                        missing += 1
                    else:
                        restored += 1
            for asset_id in affected_asset_ids:
                self._refresh_asset_primary_source(conn, asset_id)
            conn.commit()
        for asset_id in affected_asset_ids:
            self.refresh_search_index(asset_id)
        return {
            "updated": updated,
            "missing": missing,
            "restored": restored,
        }
