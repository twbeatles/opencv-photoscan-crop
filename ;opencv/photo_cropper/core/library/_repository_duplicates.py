from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads
from ._repository_protocol import LibraryRepositoryProtocol


class LibraryRepositoryDuplicateMixin:
    def replace_duplicate_group(
        self: LibraryRepositoryProtocol,
        *,
        kind: str,
        signature: str,
        representative_asset_id: Optional[int],
        asset_ids: list[int],
    ) -> int:
        now = now_iso()
        unique_ids = sorted({int(item) for item in asset_ids})
        with self.store.write_connect() as conn:
            preferences = self.get_duplicate_member_preferences(kind)
            existing = conn.execute(
                "SELECT id FROM duplicate_groups WHERE signature = ?",
                (signature,),
            ).fetchone()
            if existing is None:
                cur = conn.execute(
                    """
                    INSERT INTO duplicate_groups(kind, signature, representative_asset_id, status, created_at, updated_at)
                    VALUES (?, ?, ?, 'active', ?, ?)
                    """,
                    (kind, signature, representative_asset_id, now, now),
                )
                group_id = int(cur.lastrowid or 0)
            else:
                group_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE duplicate_groups
                    SET kind = ?, representative_asset_id = ?, status = 'active', updated_at = ?
                    WHERE id = ?
                    """,
                    (kind, representative_asset_id, now, group_id),
                )
            existing_members = {
                int(row["asset_id"]): dict(row)
                for row in conn.execute(
                    "SELECT asset_id, is_excluded FROM duplicate_group_members WHERE group_id = ?",
                    (group_id,),
                ).fetchall()
            }
            conn.execute("DELETE FROM duplicate_group_members WHERE group_id = ?", (group_id,))
            for asset_id in unique_ids:
                old = existing_members.get(asset_id, {})
                preference = preferences.get(asset_id, {})
                excluded = int(
                    preference.get(
                        "is_excluded",
                        int(old.get("is_excluded", 0) or 0),
                    )
                    or 0
                )
                role = "representative" if representative_asset_id == asset_id else "member"
                conn.execute(
                    """
                    INSERT INTO duplicate_group_members(group_id, asset_id, role, is_excluded)
                    VALUES (?, ?, ?, ?)
                    """,
                    (group_id, asset_id, role, excluded),
                )
            conn.commit()
            return group_id
    def clear_duplicate_groups_by_kind(self: LibraryRepositoryProtocol, kind: str) -> None:
        with self.store.write_connect() as conn:
            group_ids = [
                int(row["id"])
                for row in conn.execute(
                    "SELECT id FROM duplicate_groups WHERE kind = ?",
                    (kind,),
                ).fetchall()
            ]
            if group_ids:
                placeholders = ", ".join("?" for _ in group_ids)
                conn.execute(
                    f"DELETE FROM duplicate_group_members WHERE group_id IN ({placeholders})",
                    group_ids,
                )
                conn.execute(
                    f"DELETE FROM duplicate_groups WHERE id IN ({placeholders})",
                    group_ids,
                )
            conn.commit()
    def prune_duplicate_groups(self: LibraryRepositoryProtocol, kind: str, keep_signatures: list[str]) -> int:
        signatures = sorted({str(item or "") for item in keep_signatures if str(item or "").strip()})
        with self.store.write_connect() as conn:
            if signatures:
                placeholders = ", ".join("?" for _ in signatures)
                rows = conn.execute(
                    f"""
                    SELECT id
                    FROM duplicate_groups
                    WHERE kind = ? AND signature NOT IN ({placeholders})
                    """,
                    [str(kind)] + signatures,
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM duplicate_groups WHERE kind = ?",
                    (str(kind),),
                ).fetchall()
            group_ids = [int(row["id"]) for row in rows]
            if group_ids:
                placeholders = ", ".join("?" for _ in group_ids)
                conn.execute(
                    f"DELETE FROM duplicate_group_members WHERE group_id IN ({placeholders})",
                    group_ids,
                )
                conn.execute(
                    f"DELETE FROM duplicate_groups WHERE id IN ({placeholders})",
                    group_ids,
                )
            conn.commit()
            return len(group_ids)
    def get_duplicate_member_preferences(
        self: LibraryRepositoryProtocol,
        kind: str,
    ) -> dict[int, dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, is_excluded, prefer_representative, updated_at
                FROM duplicate_member_preferences
                WHERE kind = ?
                """,
                (str(kind),),
            ).fetchall()
            return {int(row["asset_id"]): dict(row) for row in rows}
    def set_duplicate_member_preference(
        self: LibraryRepositoryProtocol,
        kind: str,
        asset_id: int,
        *,
        excluded: Optional[bool] = None,
        prefer_representative: Optional[bool] = None,
    ) -> None:
        current = self.get_duplicate_member_preferences(kind).get(int(asset_id), {})
        with self.store.write_connect() as conn:
            conn.execute(
                """
                INSERT INTO duplicate_member_preferences(
                    kind, asset_id, is_excluded, prefer_representative, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(kind, asset_id) DO UPDATE SET
                    is_excluded = excluded.is_excluded,
                    prefer_representative = excluded.prefer_representative,
                    updated_at = excluded.updated_at
                """,
                (
                    str(kind),
                    int(asset_id),
                    int(
                        excluded
                        if excluded is not None
                        else bool(int(current.get("is_excluded", 0) or 0))
                    ),
                    int(
                        prefer_representative
                        if prefer_representative is not None
                        else bool(int(current.get("prefer_representative", 0) or 0))
                    ),
                    now_iso(),
                ),
            )
            conn.commit()
    def list_duplicate_groups(self: LibraryRepositoryProtocol, *, kind: Optional[str] = None) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            if kind:
                rows = conn.execute(
                    """
                    SELECT
                        g.*,
                        (
                            SELECT COUNT(*)
                            FROM duplicate_group_members m
                            WHERE m.group_id = g.id
                        ) AS member_count,
                        a.display_name AS representative_name
                    FROM duplicate_groups g
                    LEFT JOIN assets a ON a.id = g.representative_asset_id
                    WHERE g.kind = ?
                    ORDER BY g.updated_at DESC, g.id DESC
                    """,
                    (kind,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        g.*,
                        (
                            SELECT COUNT(*)
                            FROM duplicate_group_members m
                            WHERE m.group_id = g.id
                        ) AS member_count,
                        a.display_name AS representative_name
                    FROM duplicate_groups g
                    LEFT JOIN assets a ON a.id = g.representative_asset_id
                    ORDER BY g.updated_at DESC, g.id DESC
                    """
                ).fetchall()
            return [dict(row) for row in rows]
    def list_duplicate_group_members(self: LibraryRepositoryProtocol, group_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.group_id,
                    m.asset_id,
                    m.role,
                    m.is_excluded,
                    a.display_name,
                    a.primary_source_path,
                    a.exact_hash
                FROM duplicate_group_members m
                JOIN assets a ON a.id = m.asset_id
                WHERE m.group_id = ?
                ORDER BY m.role DESC, a.display_name
                """,
                (int(group_id),),
            ).fetchall()
            return [dict(row) for row in rows]
    def set_duplicate_representative(self: LibraryRepositoryProtocol, group_id: int, asset_id: int) -> None:
        with self.store.write_connect() as conn:
            group = conn.execute(
                "SELECT kind FROM duplicate_groups WHERE id = ?",
                (int(group_id),),
            ).fetchone()
            conn.execute(
                "UPDATE duplicate_groups SET representative_asset_id = ?, updated_at = ? WHERE id = ?",
                (int(asset_id), now_iso(), int(group_id)),
            )
            conn.execute(
                "UPDATE duplicate_group_members SET role = 'member' WHERE group_id = ?",
                (int(group_id),),
            )
            conn.execute(
                "UPDATE duplicate_group_members SET role = 'representative' WHERE group_id = ? AND asset_id = ?",
                (int(group_id), int(asset_id)),
            )
            conn.commit()
        if group is not None:
            group_kind = str(group["kind"] or "")
            for member in self.list_duplicate_group_members(group_id):
                self.set_duplicate_member_preference(
                    group_kind,
                    int(member["asset_id"]),
                    prefer_representative=int(member["asset_id"]) == int(asset_id),
                )
    def set_duplicate_member_excluded(self: LibraryRepositoryProtocol, group_id: int, asset_id: int, excluded: bool) -> None:
        with self.store.write_connect() as conn:
            group = conn.execute(
                "SELECT kind FROM duplicate_groups WHERE id = ?",
                (int(group_id),),
            ).fetchone()
            conn.execute(
                """
                UPDATE duplicate_group_members
                SET is_excluded = ?
                WHERE group_id = ? AND asset_id = ?
                """,
                (1 if excluded else 0, int(group_id), int(asset_id)),
            )
            conn.execute(
                "UPDATE duplicate_groups SET updated_at = ? WHERE id = ?",
                (now_iso(), int(group_id)),
            )
            conn.commit()
        if group is not None:
            self.set_duplicate_member_preference(
                str(group["kind"] or ""),
                int(asset_id),
                excluded=excluded,
            )
