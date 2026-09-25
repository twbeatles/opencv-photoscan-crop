from __future__ import annotations

import os
from typing import Optional

from ..batch import BatchProgress, FileResult, ProcessStatus
from ..face import FaceDetector
from ..image_classifier import ImageClassifier
from ..library import (
    DuplicateService,
    LibraryRepository,
    ThumbnailService,
)
from ..settings_model import AppSettings
from ..smart_enhancer import SmartEnhancer
from .ai_metadata import JobAIMetadataMixin
from .finalization import JobFinalizationMixin
from .maintenance import JobMaintenanceMixin


class JobOrchestrator(
    JobFinalizationMixin,
    JobAIMetadataMixin,
    JobMaintenanceMixin,
):
    """Job lifecycle coordinator: creation, rerun preparation, watch recording.

    Result persistence lives in :class:`JobFinalizationMixin`, AI
    enrichment in :class:`JobAIMetadataMixin`, and library maintenance
    in :class:`JobMaintenanceMixin`.
    """

    def __init__(
        self,
        repository: LibraryRepository,
        thumbnail_service: Optional[ThumbnailService] = None,
        duplicate_service: Optional[DuplicateService] = None,
    ):
        self.repository = repository
        self.thumbnail_service = thumbnail_service or ThumbnailService()
        self.duplicate_service = duplicate_service or DuplicateService(repository)
        self._classifier: Optional[ImageClassifier] = None
        self._face_detector: Optional[FaceDetector] = None
        self._enhancer: Optional[SmartEnhancer] = None
        self._metadata_warnings: list[str] = []
        self._ai_errors: list[str] = []
        self._thumbnail_failed_count = 0

    def create_job(
        self,
        *,
        job_kind: str,
        input_path: str = "",
        output_path: str = "",
        recipe_name: str = "",
        status: str = "running",
    ) -> int:
        return self.repository.create_job(
            job_kind=job_kind,
            input_path=input_path,
            output_path=output_path,
            recipe_name=recipe_name,
            status=status,
        )

    def prepare_review_reprocess(self, payload: dict) -> Optional[int]:
        review = dict(payload.get("review") or {})
        origin_job = dict(payload.get("origin_job") or {})
        source_path = str(payload.get("source_path", "") or review.get("primary_source_path", "") or "")
        if not source_path:
            return None
        return self.create_job(
            job_kind="review_reprocess",
            input_path=source_path,
            output_path=str(origin_job.get("output_path", "") or ""),
            recipe_name=str(origin_job.get("recipe_name", "") or ""),
            status="queued",
        )

    def prepare_job_rerun(self, job_id: int, *, failed_only: bool = False) -> Optional[dict]:
        origin_job = self.repository.get_job(job_id)
        if origin_job is None:
            return None
        statuses = ("failed", "partial_success") if failed_only else None
        items = self.repository.list_job_items(job_id, statuses=list(statuses) if statuses else None)
        source_paths: list[str] = []
        seen_sources: set[str] = set()
        for item in items:
            source_path = str(
                item.get("source_path", "") or item.get("primary_source_path", "") or ""
            ).strip()
            if not source_path or source_path in seen_sources:
                continue
            source_paths.append(source_path)
            seen_sources.add(source_path)

        origin_job_kind = str(origin_job.get("job_kind", "") or "")
        origin_input_path = str(origin_job.get("input_path", "") or "")
        if not source_paths and origin_input_path and os.path.isfile(origin_input_path):
            source_paths.append(origin_input_path)

        if origin_job_kind.startswith("maintenance_") and not source_paths:
            return {
                "job_id": 0,
                "job_kind": origin_job_kind,
                "origin_job_id": int(origin_job.get("id", 0) or 0),
                "origin_job_kind": origin_job_kind,
                "input_path": origin_input_path,
                "output_path": str(origin_job.get("output_path", "") or ""),
                "recipe_name": str(origin_job.get("recipe_name", "") or ""),
                "source_paths": [],
            }

        if not source_paths:
            return None
        queued_job_id = self.create_job(
            job_kind="batch_retry" if failed_only else "batch_rerun",
            input_path=str(origin_job.get("input_path", "") or ""),
            output_path=str(origin_job.get("output_path", "") or ""),
            recipe_name=str(origin_job.get("recipe_name", "") or ""),
            status="queued",
        )
        return {
            "job_id": queued_job_id,
            "job_kind": "batch_retry" if failed_only else "batch_rerun",
            "origin_job_id": int(origin_job.get("id", 0) or 0),
            "origin_job_kind": origin_job_kind,
            "input_path": str(origin_job.get("input_path", "") or ""),
            "output_path": str(origin_job.get("output_path", "") or ""),
            "recipe_name": str(origin_job.get("recipe_name", "") or ""),
            "source_paths": source_paths,
        }

    def record_watch_file(
        self,
        *,
        source_path: str,
        output_path: str,
        result: FileResult,
        settings: AppSettings,
        recipe_name: str = "",
    ) -> int:
        job_id = self.create_job(
            job_kind="watch_file",
            input_path=source_path,
            output_path=output_path,
            recipe_name=recipe_name,
        )
        progress = BatchProgress(
            total=1,
            processed=1,
            success=1 if result.status == ProcessStatus.SUCCESS else 0,
            partial_success=1 if result.status == ProcessStatus.PARTIAL_SUCCESS else 0,
            failed=1 if result.status == ProcessStatus.FAILED else 0,
            skipped=1 if result.status == ProcessStatus.SKIPPED else 0,
            is_running=False,
            is_cancelled=result.status == ProcessStatus.CANCELLED,
        )
        self.finalize_job(
            job_id=job_id,
            progress=progress,
            results=[result],
            settings=settings,
            recipe_name=recipe_name,
            job_kind="watch_file",
        )
        return job_id


__all__ = ["JobOrchestrator"]
