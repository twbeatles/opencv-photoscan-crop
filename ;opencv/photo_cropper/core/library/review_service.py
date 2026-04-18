from __future__ import annotations

import os
from typing import Callable, Optional

from .repository import LibraryRepository


class ReviewService:
    def __init__(
        self,
        repository: LibraryRepository,
        *,
        create_reprocess_job: Optional[Callable[[dict], Optional[int]]] = None,
    ):
        self.repository = repository
        self._create_reprocess_job = create_reprocess_job

    def list_items(self, *, limit: int = 500) -> list[dict]:
        return self.repository.list_review_items(limit=limit)

    def get_item(self, review_id: int) -> Optional[dict]:
        return self.repository.get_review_item(review_id)

    def get_relink_candidates(self, review_id: int) -> list[dict]:
        row = self.repository.get_review_item(review_id)
        if row is None:
            return []
        action_context = dict(row.get("action_context", {}) or {})
        candidate_source_ids = [
            int(item)
            for item in list(action_context.get("candidate_source_ids", []) or [])
            if int(item) > 0
        ]
        return self.repository.list_sources_by_ids(candidate_source_ids)

    def approve(
        self,
        review_id: int,
        *,
        variant_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        row = self.repository.get_review_item(review_id)
        if row is None:
            return False
        resolved_variant_id = int(
            variant_id
            or row.get("variant_id", 0)
            or 0
        )
        if resolved_variant_id <= 0:
            source_path = str(row.get("primary_source_path", "") or "")
            latest_variant = (
                self.repository.get_latest_variant_for_source(source_path)
                if source_path
                else None
            )
            if latest_variant is not None:
                resolved_variant_id = int(latest_variant.get("id", 0) or 0)
        if resolved_variant_id <= 0:
            return False
        self.repository.update_review_status(
            review_id,
            "approved",
            notes=notes,
            variant_id=resolved_variant_id,
        )
        return True

    def reject(self, review_id: int, *, notes: Optional[str] = None) -> bool:
        self.repository.update_review_status(review_id, "rejected", notes=notes)
        return True

    def enqueue_reprocess(self, review_id: int, *, notes: Optional[str] = None) -> Optional[int]:
        row = self.repository.get_review_item(review_id)
        if row is None:
            return None
        source_path = str(row.get("primary_source_path", "") or "")
        if not source_path:
            return None
        origin_job = (
            self.repository.get_job(int(row.get("job_id", 0) or 0))
            if int(row.get("job_id", 0) or 0) > 0
            else None
        )
        action_context = dict(row.get("action_context", {}) or {})
        action_context["reprocess_source_path"] = source_path
        action_context["retry_scope"] = "single_review_item"
        if origin_job is not None:
            action_context["origin_job_id"] = int(origin_job.get("id", 0) or 0)
        if self._create_reprocess_job is not None:
            job_id = self._create_reprocess_job(
                {
                    "review": row,
                    "origin_job": origin_job,
                    "source_path": source_path,
                    "notes": notes or "",
                }
            )
        else:
            job_id = self.repository.create_job(
                job_kind="review_reprocess",
                input_path=source_path,
                output_path=str(origin_job.get("output_path", "") or "") if origin_job else "",
                recipe_name=str(origin_job.get("recipe_name", "") or "") if origin_job else "",
                status="queued",
            )
        action_context["reprocess_job_id"] = int(job_id) if job_id else None
        self.repository.update_review_status(
            review_id,
            "reprocess_requested",
            notes=notes,
            action_context=action_context,
        )
        return int(job_id) if job_id else None

    def request_reprocess(self, review_id: int, *, notes: Optional[str] = None) -> Optional[int]:
        return self.enqueue_reprocess(review_id, notes=notes)

    def resolve_relink(
        self,
        review_id: int,
        *,
        target_source_id: Optional[int] = None,
        new_path: Optional[str] = None,
    ) -> Optional[dict]:
        row = self.repository.get_review_item(review_id)
        if row is None:
            return None
        action_context = dict(row.get("action_context", {}) or {})
        pending_path = str(
            new_path
            or action_context.get("pending_source_path")
            or row.get("primary_source_path")
            or ""
        )
        if not pending_path:
            return None
        if target_source_id is None:
            candidate_source_ids = [
                int(item)
                for item in list(action_context.get("candidate_source_ids", []) or [])
                if int(item) > 0
            ]
            if int(row.get("source_id", 0) or 0) > 0:
                candidate_source_ids.append(int(row["source_id"]))
            candidate_source_ids = sorted(set(candidate_source_ids))
            if len(candidate_source_ids) != 1:
                return None
            target_source_id = candidate_source_ids[0]
        record = self.repository.relink_source(int(target_source_id), pending_path)
        if record is None:
            return None
        self.repository.update_review_status(
            review_id,
            "approved",
            notes=row.get("notes") or "",
            action_context={
                "resolved_source_id": int(target_source_id),
                "resolved_source_path": os.path.abspath(pending_path),
            },
        )
        return record
