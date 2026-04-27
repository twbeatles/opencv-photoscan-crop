from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryAssetCoreMixin:
    def _refresh_asset_primary_source(self: LibraryRepositoryProtocol, conn: Any, asset_id: int) -> None:
        primary = conn.execute(
            """
            SELECT source_path, source_hash
            FROM asset_sources
            WHERE asset_id = ? AND is_missing = 0
            ORDER BY last_seen_at DESC, id DESC
            LIMIT 1
            """,
            (int(asset_id),),
        ).fetchone()
        if primary is None:
            primary = conn.execute(
                """
                SELECT source_path, source_hash
                FROM asset_sources
                WHERE asset_id = ?
                ORDER BY last_seen_at DESC, id DESC
                LIMIT 1
                """,
                (int(asset_id),),
            ).fetchone()
        primary_path = str(primary["source_path"] or "") if primary is not None else ""
        exact_hash = str(primary["source_hash"] or "") if primary is not None else ""
        conn.execute(
            """
            UPDATE assets
            SET primary_source_path = ?, exact_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (primary_path, exact_hash, now_iso(), int(asset_id)),
        )
    def _source_candidates_by_hash(
        self: LibraryRepositoryProtocol,
        conn,
        source_hash: str,
        *,
        missing_only: bool = False,
    ) -> list[dict[str, Any]]:
        if not source_hash:
            return []
        query = [
            """
            SELECT
                s.id AS source_id,
                s.asset_id,
                s.source_path,
                s.source_hash,
                s.is_missing,
                a.display_name
            FROM asset_sources s
            JOIN assets a ON a.id = s.asset_id
            WHERE s.source_hash = ?
            """
        ]
        params: list[Any] = [source_hash]
        if missing_only:
            query.append("AND s.is_missing = 1")
        query.append("ORDER BY s.is_missing DESC, s.last_seen_at DESC, s.id DESC")
        rows = conn.execute("\n".join(query), params).fetchall()
        return [dict(row) for row in rows]
    def set_asset_perceptual_hash(self: LibraryRepositoryProtocol, asset_id: int, value: str) -> None:
        with self.store.write_connect() as conn:
            conn.execute(
                """
                UPDATE assets
                SET perceptual_hash = ?, perceptual_hash_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (str(value or ""), now_iso(), now_iso(), int(asset_id)),
            )
            conn.commit()
    def refresh_asset_perceptual_hash(self: LibraryRepositoryProtocol, asset_id: int, file_path: str) -> str:
        perceptual_hash = compute_perceptual_hash(file_path)
        self.set_asset_perceptual_hash(asset_id, perceptual_hash)
        return perceptual_hash
