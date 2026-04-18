# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import json
import os
from typing import Any, Optional

from ...utils.file_helpers import compute_file_hash, get_image_dimensions
from .types import AssetQuery, AssetTimelineEvent
from ._repository_shared import compute_perceptual_hash, now_iso, safe_json_loads


class LibraryRepositoryQueryMixin:
    def _build_asset_query_sql(
        self: Any,
        asset_query: AssetQuery,
        *,
        with_limit: bool,
    ) -> tuple[str, list[Any]]:
        latest_review_sql = (
            "SELECT status FROM review_items r "
            "WHERE r.asset_id = a.id ORDER BY r.updated_at DESC, r.id DESC LIMIT 1"
        )
        search_ids = self.search_asset_ids(asset_query.search_text) if asset_query.search_text else []
        clauses: list[str] = []
        params: list[Any] = []
        if asset_query.collection_id is not None:
            clauses.append(
                "a.id IN (SELECT asset_id FROM collection_assets WHERE collection_id = ?)"
            )
            params.append(int(asset_query.collection_id))
        tag_names = [str(item).strip() for item in asset_query.tag_names if str(item).strip()]
        if tag_names:
            placeholders = ", ".join("?" for _ in tag_names)
            clauses.append(
                f"""
                a.id IN (
                    SELECT at.asset_id
                    FROM asset_tags at
                    JOIN tags t ON t.id = at.tag_id
                    WHERE t.name IN ({placeholders})
                    GROUP BY at.asset_id
                    HAVING COUNT(DISTINCT t.name) >= ?
                )
                """
            )
            params.extend(tag_names)
            params.append(len(tag_names))
        if asset_query.review_status:
            clauses.append(f"COALESCE(({latest_review_sql}), '') = ?")
            params.append(str(asset_query.review_status))
        if search_ids:
            placeholders = ", ".join("?" for _ in search_ids)
            clauses.append(f"a.id IN ({placeholders})")
            params.extend(int(item) for item in search_ids)
        elif asset_query.search_text:
            clauses.append("1 = 0")

        sort_map = {
            "updated": "a.updated_at DESC, a.id DESC",
            "name": "lower(a.display_name) ASC, a.id DESC",
            "created": "a.created_at DESC, a.id DESC",
        }
        order_sql = sort_map.get(str(asset_query.sort_by or "updated"), sort_map["updated"])

        sql = [
            """
            SELECT
                a.id,
                a.display_name,
                a.note,
                a.exact_hash,
                a.perceptual_hash,
                a.primary_source_path,
                a.created_at,
                a.updated_at,
                COALESCE((
                    SELECT s.width
                    FROM asset_sources s
                    WHERE s.asset_id = a.id
                    ORDER BY s.last_seen_at DESC, s.id DESC
                    LIMIT 1
                ), 0) AS width,
                COALESCE((
                    SELECT s.height
                    FROM asset_sources s
                    WHERE s.asset_id = a.id
                    ORDER BY s.last_seen_at DESC, s.id DESC
                    LIMIT 1
                ), 0) AS height,
                (
                    SELECT COUNT(*)
                    FROM asset_variants v
                    WHERE v.asset_id = a.id
                ) AS variant_count,
                COALESCE((
                    """
            + latest_review_sql +
            """
                ), '') AS review_status
            FROM assets a
            """
        ]
        if clauses:
            sql.append("WHERE " + " AND ".join(clauses))
        sql.append(f"ORDER BY {order_sql}")
        if with_limit:
            sql.append("LIMIT ? OFFSET ?")
            params.extend([asset_query.normalized_page_size, asset_query.offset])
        return "\n".join(sql), params
    def count_assets(self: Any, asset_query: Optional[AssetQuery] = None) -> int:
        query = asset_query or AssetQuery()
        sql, params = self._build_asset_query_sql(query, with_limit=False)
        count_sql = f"SELECT COUNT(*) AS total FROM ({sql}) AS asset_rows"
        with self.store.connect() as conn:
            row = conn.execute(count_sql, params).fetchone()
            return int(row["total"] or 0) if row is not None else 0
    def list_assets(
        self: Any,
        asset_query: Optional[AssetQuery] = None,
        *,
        search_text: str = "",
        collection_id: Optional[int] = None,
        tag_names: Optional[list[str] | tuple[str, ...]] = None,
        review_status: str = "",
        sort_by: str = "updated",
        page: int = 1,
        page_size: int = 200,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        query = asset_query or AssetQuery(
            search_text=search_text,
            collection_id=collection_id,
            tag_names=tuple(tag_names or ()),
            review_status=review_status,
            sort_by=sort_by,
            page=1 if limit is not None else page,
            page_size=int(limit or page_size),
        )
        sql, params = self._build_asset_query_sql(query, with_limit=True)
        with self.store.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                asset_id = int(row["id"])
                tags = [
                    str(tag["name"])
                    for tag in conn.execute(
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
                result.append(
                    {
                        "id": asset_id,
                        "display_name": str(row["display_name"] or ""),
                        "note": str(row["note"] or ""),
                        "exact_hash": str(row["exact_hash"] or ""),
                        "perceptual_hash": str(row["perceptual_hash"] or ""),
                        "primary_source_path": str(row["primary_source_path"] or ""),
                        "created_at": str(row["created_at"] or ""),
                        "updated_at": str(row["updated_at"] or ""),
                        "width": int(row["width"] or 0),
                        "height": int(row["height"] or 0),
                        "variant_count": int(row["variant_count"] or 0),
                        "review_status": str(row["review_status"] or ""),
                        "tags": tags,
                        "collections": collections,
                    }
                )
            return result
    def get_asset_detail(self: Any, asset_id: int) -> Optional[dict[str, Any]]:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT * FROM assets WHERE id = ?",
                (int(asset_id),),
            ).fetchone()
            if row is None:
                return None
            sources = [
                dict(item)
                for item in conn.execute(
                    """
                    SELECT id, source_path, source_hash, file_size, width, height, last_seen_at, is_missing
                    FROM asset_sources
                    WHERE asset_id = ?
                    ORDER BY id DESC
                    """,
                    (int(asset_id),),
                ).fetchall()
            ]
            variants = [
                dict(item)
                for item in conn.execute(
                    """
                    SELECT id, variant_kind, file_path, recipe_name, file_size_kb, created_at
                    FROM asset_variants
                    WHERE asset_id = ?
                    ORDER BY id DESC
                    """,
                    (int(asset_id),),
                ).fetchall()
            ]
            collections = self.list_collections_for_asset(asset_id)
            tags = self.list_tags_for_asset(asset_id)
            ocr_documents = self.list_ocr_documents(asset_id)
            faces = self.list_faces_for_asset(asset_id)
            people = self.list_people_for_asset(asset_id)
            return {
                "id": int(row["id"]),
                "display_name": str(row["display_name"] or ""),
                "note": str(row["note"] or ""),
                "exact_hash": str(row["exact_hash"] or ""),
                "perceptual_hash": str(row["perceptual_hash"] or ""),
                "primary_source_path": str(row["primary_source_path"] or ""),
                "created_at": str(row["created_at"] or ""),
                "updated_at": str(row["updated_at"] or ""),
                "sources": sources,
                "variants": variants,
                "collections": collections,
                "tags": tags,
                "ocr_documents": ocr_documents,
                "faces": faces,
                "people": people,
            }
    def get_asset_visual_path(self: Any, asset_id: int) -> str:
        with self.store.connect() as conn:
            variant = conn.execute(
                """
                SELECT file_path
                FROM asset_variants
                WHERE asset_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (int(asset_id),),
            ).fetchone()
            if variant is not None and os.path.exists(str(variant["file_path"] or "")):
                return str(variant["file_path"] or "")
            row = conn.execute(
                "SELECT primary_source_path FROM assets WHERE id = ?",
                (int(asset_id),),
            ).fetchone()
            return str(row["primary_source_path"] or "") if row is not None else ""
    def get_asset_timeline(self: Any, asset_id: int) -> list[AssetTimelineEvent]:
        events: list[AssetTimelineEvent] = []
        detail = self.get_asset_detail(asset_id)
        if detail is None:
            return events
        for source in detail.get("sources", []):
            events.append(
                AssetTimelineEvent(
                    event_type="source",
                    timestamp=str(source.get("last_seen_at", "")),
                    asset_id=int(asset_id),
                    source_id=int(source.get("id", 0) or 0),
                    label=str(source.get("source_path", "") or ""),
                    metadata={"is_missing": int(source.get("is_missing", 0) or 0)},
                )
            )
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, variant_kind, file_path, recipe_name, created_at
                FROM asset_variants
                WHERE asset_id = ?
                ORDER BY id DESC
                """,
                (int(asset_id),),
            ).fetchall()
            for row in rows:
                events.append(
                    AssetTimelineEvent(
                        event_type="variant",
                        timestamp=str(row["created_at"] or ""),
                        asset_id=int(asset_id),
                        variant_id=int(row["id"]),
                        label=str(row["file_path"] or ""),
                        metadata={
                            "variant_kind": str(row["variant_kind"] or ""),
                            "recipe_name": str(row["recipe_name"] or ""),
                        },
                    )
                )
        for review in self.list_review_items(limit=5000):
            if int(review.get("asset_id", 0) or 0) == int(asset_id):
                events.append(
                    AssetTimelineEvent(
                        event_type="review",
                        timestamp=str(review.get("updated_at", "")),
                        asset_id=int(asset_id),
                        source_id=int(review.get("source_id", 0) or 0) or None,
                        variant_id=int(review.get("variant_id", 0) or 0) or None,
                        job_id=int(review.get("job_id", 0) or 0) or None,
                        label=str(review.get("status", "") or ""),
                        metadata={
                            "reason": str(review.get("reason", "") or ""),
                            "notes": str(review.get("notes", "") or ""),
                        },
                    )
                )
        for item in self.list_job_items_for_asset(asset_id):
            events.append(
                AssetTimelineEvent(
                    event_type="job_item",
                    timestamp=str(item.get("created_at", "")),
                    asset_id=int(asset_id),
                    source_id=int(item.get("source_id", 0) or 0) or None,
                    job_id=int(item.get("job_id", 0) or 0) or None,
                    label=str(item.get("status", "") or ""),
                    metadata={
                        "message": str(item.get("message", "") or ""),
                        "job_kind": str(item.get("job_kind", "") or ""),
                    },
                )
            )
        return sorted(events, key=lambda item: (item.timestamp, item.event_type), reverse=True)
