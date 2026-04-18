# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads


class LibraryRepositoryJobMixin:
    def create_job(
        self: Any,
        *,
        job_kind: str,
        input_path: str = "",
        output_path: str = "",
        recipe_name: str = "",
        status: str = "running",
    ) -> int:
        now = now_iso()
        with self.store.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO process_jobs(
                    job_kind, status, input_path, output_path, recipe_name,
                    started_at, finished_at, summary_json
                )
                VALUES (?, ?, ?, ?, ?, ?, '', '{}')
                """,
                (job_kind, status, input_path, output_path, recipe_name, now),
            )
            conn.commit()
            return int(cur.lastrowid)
    def finalize_job(
        self: Any,
        job_id: int,
        *,
        status: str,
        total_items: int,
        processed_items: int,
        success_count: int,
        partial_count: int,
        failed_count: int,
        skipped_count: int,
        summary: Optional[dict[str, Any]] = None,
    ) -> None:
        with self.store.connect() as conn:
            conn.execute(
                """
                UPDATE process_jobs
                SET status = ?, total_items = ?, processed_items = ?, success_count = ?,
                    partial_count = ?, failed_count = ?, skipped_count = ?,
                    finished_at = ?, summary_json = ?
                WHERE id = ?
                """,
                (
                    status,
                    int(total_items),
                    int(processed_items),
                    int(success_count),
                    int(partial_count),
                    int(failed_count),
                    int(skipped_count),
                    now_iso(),
                    json.dumps(summary or {}, ensure_ascii=False, sort_keys=True),
                    int(job_id),
                ),
            )
            conn.commit()
    def add_job_item(
        self: Any,
        *,
        job_id: int,
        source_path: str,
        asset_id: Optional[int],
        source_id: Optional[int],
        status: str,
        message: str,
        output_paths: list[str],
        processing_time_ms: float,
    ) -> int:
        with self.store.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO process_job_items(
                    job_id, source_path, asset_id, source_id, status, message,
                    output_paths_json, processing_time_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(job_id),
                    os.path.abspath(str(source_path or "")),
                    int(asset_id) if asset_id is not None else None,
                    int(source_id) if source_id is not None else None,
                    status,
                    str(message or ""),
                    json.dumps(list(output_paths or []), ensure_ascii=False),
                    float(processing_time_ms or 0.0),
                    now_iso(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
    def upsert_variant(
        self: Any,
        *,
        asset_id: int,
        source_id: Optional[int],
        file_path: str,
        variant_kind: str,
        recipe_name: str = "",
        job_item_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        normalized = os.path.abspath(str(file_path or ""))
        size_kb = 0.0
        try:
            size_kb = os.path.getsize(normalized) / 1024.0
        except Exception:
            pass
        payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        now = now_iso()
        with self.store.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM asset_variants WHERE file_path = ?",
                (normalized,),
            ).fetchone()
            if existing is None:
                cur = conn.execute(
                    """
                    INSERT INTO asset_variants(
                        asset_id, source_id, variant_kind, file_path, recipe_name,
                        job_item_id, file_size_kb, metadata_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(asset_id),
                        int(source_id) if source_id is not None else None,
                        variant_kind,
                        normalized,
                        recipe_name,
                        int(job_item_id) if job_item_id is not None else None,
                        size_kb,
                        payload,
                        now,
                    ),
                )
                variant_id = int(cur.lastrowid)
            else:
                variant_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE asset_variants
                    SET asset_id = ?, source_id = ?, variant_kind = ?, recipe_name = ?,
                        job_item_id = ?, file_size_kb = ?, metadata_json = ?
                    WHERE id = ?
                    """,
                    (
                        int(asset_id),
                        int(source_id) if source_id is not None else None,
                        variant_kind,
                        recipe_name,
                        int(job_item_id) if job_item_id is not None else None,
                        size_kb,
                        payload,
                        variant_id,
                    ),
                )
            conn.commit()
        return variant_id
    def create_review_item(
        self: Any,
        *,
        asset_id: Optional[int],
        source_id: Optional[int],
        variant_id: Optional[int],
        job_id: Optional[int],
        job_item_id: Optional[int],
        status: str,
        reason: str,
        action_context: Optional[dict[str, Any]] = None,
    ) -> int:
        now = now_iso()
        with self.store.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO review_items(
                    asset_id, source_id, variant_id, job_id, job_item_id,
                    status, reason, notes, action_context_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?)
                """,
                (
                    int(asset_id) if asset_id is not None else None,
                    int(source_id) if source_id is not None else None,
                    int(variant_id) if variant_id is not None else None,
                    int(job_id) if job_id is not None else None,
                    int(job_item_id) if job_item_id is not None else None,
                    status,
                    reason,
                    json.dumps(action_context or {}, ensure_ascii=False, sort_keys=True),
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
    def update_review_status(
        self: Any,
        review_id: int,
        status: str,
        notes: Optional[str] = None,
        *,
        variant_id: Optional[int] = None,
        action_context: Optional[dict[str, Any]] = None,
    ) -> None:
        with self.store.connect() as conn:
            existing = conn.execute(
                "SELECT notes, action_context_json FROM review_items WHERE id = ?",
                (int(review_id),),
            ).fetchone()
            existing_notes = str(existing["notes"] or "") if existing is not None else ""
            existing_context = (
                safe_json_loads(existing["action_context_json"], {})
                if existing is not None
                else {}
            )
            merged_context = dict(existing_context or {})
            if action_context:
                merged_context.update(dict(action_context))
            conn.execute(
                """
                UPDATE review_items
                SET status = ?, notes = ?, variant_id = COALESCE(?, variant_id),
                    action_context_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    existing_notes if notes is None else str(notes or ""),
                    int(variant_id) if variant_id is not None else None,
                    json.dumps(merged_context, ensure_ascii=False, sort_keys=True),
                    now_iso(),
                    int(review_id),
                ),
            )
            conn.commit()
    def get_review_item(self: Any, review_id: int) -> Optional[dict[str, Any]]:
        rows = self.list_review_items(limit=2000)
        for row in rows:
            if int(row.get("id", 0) or 0) == int(review_id):
                return row
        return None
    def get_latest_variant_for_source(self: Any, source_path: str) -> Optional[dict[str, Any]]:
        normalized = os.path.abspath(str(source_path or ""))
        with self.store.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    v.id,
                    v.asset_id,
                    v.source_id,
                    v.variant_kind,
                    v.file_path,
                    v.recipe_name,
                    v.created_at
                FROM asset_variants v
                JOIN asset_sources s ON s.id = v.source_id
                WHERE s.source_path = ?
                ORDER BY v.id DESC
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            return dict(row) if row is not None else None
    def approve_reviews_for_source(self: Any, source_path: str, *, variant_id: Optional[int] = None) -> None:
        normalized = os.path.abspath(str(source_path or ""))
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT id FROM asset_sources WHERE source_path = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return
            source_id = int(row["id"])
            if variant_id is None:
                conn.execute(
                    """
                    UPDATE review_items
                    SET status = 'needs_review', updated_at = ?
                    WHERE source_id = ? AND status IN ('new', 'needs_review', 'reprocess_requested')
                    """,
                    (now_iso(), source_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE review_items
                    SET status = 'needs_review', variant_id = ?, updated_at = ?
                    WHERE source_id = ? AND status IN ('new', 'needs_review', 'reprocess_requested')
                    """,
                    (int(variant_id), now_iso(), source_id),
                )
            conn.commit()
    def list_jobs(self: Any, *, limit: int = 200) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM process_jobs
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                payload["summary"] = safe_json_loads(payload.get("summary_json"), {})
                result.append(payload)
            return result
    def get_job(self: Any, job_id: int) -> Optional[dict[str, Any]]:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT * FROM process_jobs WHERE id = ?",
                (int(job_id),),
            ).fetchone()
            if row is None:
                return None
            payload = dict(row)
            payload["summary"] = safe_json_loads(payload.get("summary_json"), {})
            return payload
    def list_job_items(
        self: Any,
        job_id: int,
        *,
        statuses: Optional[list[str] | tuple[str, ...]] = None,
    ) -> list[dict[str, Any]]:
        query = [
            """
            SELECT
                i.*,
                a.display_name,
                a.primary_source_path
            FROM process_job_items i
            LEFT JOIN assets a ON a.id = i.asset_id
            WHERE i.job_id = ?
            """
        ]
        params: list[Any] = [int(job_id)]
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            query.append(f"AND i.status IN ({placeholders})")
            params.extend(str(item) for item in statuses)
        query.append("ORDER BY i.id ASC")
        with self.store.connect() as conn:
            rows = conn.execute("\n".join(query), params).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                payload["output_paths"] = safe_json_loads(
                    payload.get("output_paths_json"), []
                )
                result.append(payload)
            return result
    def list_review_items(self: Any, *, limit: int = 500) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.id,
                    r.status,
                    r.reason,
                    r.notes,
                    r.action_context_json,
                    r.created_at,
                    r.updated_at,
                    a.id AS asset_id,
                    a.display_name,
                    a.primary_source_path,
                    r.source_id,
                    r.variant_id,
                    j.job_kind,
                    j.id AS job_id
                FROM review_items r
                LEFT JOIN assets a ON a.id = r.asset_id
                LEFT JOIN process_jobs j ON j.id = r.job_id
                ORDER BY r.updated_at DESC, r.id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                action_context = safe_json_loads(payload.get("action_context_json"), {})
                payload["action_context"] = action_context
                if not payload.get("primary_source_path"):
                    payload["primary_source_path"] = str(
                        action_context.get("pending_source_path", "") or ""
                    )
                payload["candidate_source_ids"] = list(
                    action_context.get("candidate_source_ids", []) or []
                )
                result.append(payload)
            return result
    def list_job_items_for_asset(self: Any, asset_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    i.*,
                    j.job_kind
                FROM process_job_items i
                JOIN process_jobs j ON j.id = i.job_id
                WHERE i.asset_id = ?
                ORDER BY i.id DESC
                """,
                (int(asset_id),),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                payload["output_paths"] = safe_json_loads(
                    payload.get("output_paths_json"), []
                )
                result.append(payload)
            return result
