from __future__ import annotations

from typing import Any

from ..batch import BatchProgress, FileResult, ProcessStatus
from ..settings_model import AppSettings


class JobFinalizationMixin:
    """Per-result ingest/variant/review recording and job final status."""

    repository: Any
    thumbnail_service: Any
    duplicate_service: Any
    _metadata_warnings: list[str]
    _ai_errors: list[str]
    _thumbnail_failed_count: int

    def finalize_job(
        self,
        *,
        job_id: int,
        progress: BatchProgress,
        results: list[FileResult],
        settings: AppSettings,
        recipe_name: str = "",
        job_kind: str = "",
    ) -> None:
        review_candidates = 0
        self._metadata_warnings = []
        self._ai_errors = []
        self._thumbnail_failed_count = 0
        for result in results:
            ingest_record = None
            ingest_state = ""
            source_action_context = {}
            if result.source_path:
                ingest_record = self.repository.upsert_source(result.source_path)
                ingest_state = str(ingest_record.get("ingest_state", "") or "")
                thumb_path = self.thumbnail_service.ensure_thumbnail(result.source_path)
                if not thumb_path:
                    self._thumbnail_failed_count += 1
                    self._metadata_warnings.append(f"thumbnail_failed:{result.source_path}")
                if ingest_state == "invalid_source":
                    asset_id = None
                    source_id = None
                    source_action_context = {
                        "source_path": str(ingest_record.get("source_path", "") or result.source_path),
                        "error": str(ingest_record.get("error", "") or "invalid_source"),
                    }
                elif ingest_state == "ambiguous_relink":
                    asset_id = None
                    source_id = None
                    source_action_context = {
                        "pending_source_path": str(
                            ingest_record.get("source_path", "") or ""
                        ),
                        "pending_source_hash": str(
                            ingest_record.get("source_hash", "") or ""
                        ),
                        "candidate_source_ids": list(
                            ingest_record.get("candidate_source_ids", []) or []
                        ),
                        "candidate_asset_ids": list(
                            ingest_record.get("candidate_asset_ids", []) or []
                        ),
                    }
                else:
                    asset_id = int(ingest_record["asset_id"])
                    source_id = int(ingest_record["source_id"])
            else:
                asset_id = None
                source_id = None

            output_paths = list(result.output_paths or [])
            if not output_paths and result.output_path:
                output_paths = [result.output_path]

            item_id = self.repository.add_job_item(
                job_id=job_id,
                source_path=result.source_path or "",
                asset_id=asset_id,
                source_id=source_id,
                status=result.status.value,
                message=result.message,
                output_paths=output_paths,
                processing_time_ms=result.processing_time_ms,
            )

            last_variant_id = None
            if asset_id is not None and output_paths:
                variant_kind = self._variant_kind_for_result(result, settings, job_kind=job_kind)
                for path in output_paths:
                    last_variant_id = self.repository.upsert_variant(
                        asset_id=asset_id,
                        source_id=source_id,
                        file_path=path,
                        variant_kind=variant_kind,
                        recipe_name=recipe_name,
                        job_item_id=item_id,
                        metadata={"message": result.message},
                    )
                    if not self.thumbnail_service.ensure_thumbnail(path):
                        self._thumbnail_failed_count += 1
                        self._metadata_warnings.append(f"thumbnail_failed:{path}")
                    self.repository.refresh_asset_perceptual_hash(asset_id, path)
                    self._record_ai_metadata(
                        asset_id=asset_id,
                        source_id=source_id,
                        variant_id=last_variant_id,
                        image_path=path,
                        settings=settings,
                    )

            if ingest_state == "invalid_source":
                review_candidates += 1
                self.repository.create_review_item(
                    asset_id=None,
                    source_id=None,
                    variant_id=None,
                    job_id=job_id,
                    job_item_id=item_id,
                    status="new",
                    reason="invalid_source",
                    action_context=source_action_context,
                )
            elif ingest_state == "ambiguous_relink":
                review_candidates += 1
                self.repository.create_review_item(
                    asset_id=None,
                    source_id=None,
                    variant_id=None,
                    job_id=job_id,
                    job_item_id=item_id,
                    status="new",
                    reason="source_relink_required",
                    action_context=source_action_context,
                )
            elif result.status in (ProcessStatus.FAILED, ProcessStatus.PARTIAL_SUCCESS):
                review_candidates += 1
                self.repository.create_review_item(
                    asset_id=asset_id,
                    source_id=source_id,
                    variant_id=last_variant_id,
                    job_id=job_id,
                    job_item_id=item_id,
                    status="new",
                    reason=result.message or result.status.value,
                    action_context={
                        "source_path": str(result.source_path or ""),
                        "output_paths": list(output_paths or []),
                        "process_status": result.status.value,
                    },
                )
            elif job_kind == "manual_extract" and result.status == ProcessStatus.SUCCESS and result.source_path:
                self.repository.approve_reviews_for_source(
                    result.source_path,
                    variant_id=last_variant_id,
                )

        partial_count = int(getattr(progress, "partial_success", 0) or 0)
        fatal_error = bool(getattr(progress, "fatal_error", False))
        final_status = "failed" if fatal_error else (
            "cancelled" if progress.is_cancelled else
            "failed" if progress.failed > 0 and progress.success == 0 and partial_count == 0 else
            "partial_success" if partial_count > 0 or (progress.failed > 0 and progress.success > 0) else
            "success"
        )
        self.repository.finalize_job(
            job_id,
            status=final_status,
            total_items=progress.total,
            processed_items=progress.processed,
            success_count=progress.success,
            partial_count=partial_count,
            failed_count=progress.failed,
            skipped_count=progress.skipped,
            summary={
                "review_candidates": review_candidates,
                "cancelled": bool(progress.is_cancelled),
                "fatal_error": fatal_error,
                "fatal_message": str(getattr(progress, "fatal_message", "") or ""),
                "metadata_warnings": list(dict.fromkeys(self._metadata_warnings)),
                "ai_errors": list(dict.fromkeys(self._ai_errors)),
                "thumbnail_failed_count": self._thumbnail_failed_count,
            },
        )
        self.duplicate_service.rebuild_exact_groups()

    def _variant_kind_for_result(
        self,
        result: FileResult,
        settings: AppSettings,
        *,
        job_kind: str,
    ) -> str:
        if job_kind == "manual_extract":
            return "manual_fix"
        if settings.watermark.enabled:
            return "watermarked"
        if settings.resize.enabled:
            return "resized"
        if settings.smart_enhancement.enabled or settings.face_detection.enabled:
            return "enhanced"
        return "cropped"


__all__ = ["JobFinalizationMixin"]
