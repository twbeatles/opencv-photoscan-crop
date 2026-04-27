from __future__ import annotations

import os
from typing import Optional

from ..face import FaceDetector
from ..image_classifier import ImageClassifier
from ..settings_model import AppSettings
from ..smart_enhancer import SmartEnhancer
from ..batch import BatchProgress, FileResult, ProcessStatus
from ..library import (
    DuplicateService,
    LibraryIngestService,
    LibraryRepository,
    ThumbnailService,
    get_ocr_provider,
    get_person_provider,
)


class JobOrchestrator:
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

            last_variant_id: Optional[int] = None
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
        final_status = "cancelled" if progress.is_cancelled else (
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
                "metadata_warnings": list(dict.fromkeys(self._metadata_warnings)),
                "ai_errors": list(dict.fromkeys(self._ai_errors)),
                "thumbnail_failed_count": self._thumbnail_failed_count,
            },
        )
        self.duplicate_service.rebuild_exact_groups()

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
        source_paths = [
            str(item.get("source_path", "") or item.get("primary_source_path", "") or "")
            for item in items
            if str(item.get("source_path", "") or item.get("primary_source_path", "") or "").strip()
        ]
        if failed_only and not source_paths:
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
            "origin_job_kind": str(origin_job.get("job_kind", "") or ""),
            "input_path": str(origin_job.get("input_path", "") or ""),
            "output_path": str(origin_job.get("output_path", "") or ""),
            "recipe_name": str(origin_job.get("recipe_name", "") or ""),
            "source_paths": source_paths,
        }

    def run_maintenance_job(
        self,
        job_kind: str,
        *,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
        input_path: str = "",
        recursive: bool = True,
    ) -> int:
        normalized_asset_ids = [int(item) for item in list(asset_ids or []) if int(item) > 0]
        job_id = self.create_job(
            job_kind=job_kind,
            input_path=input_path or "library",
            output_path="",
            recipe_name="",
        )
        summary = {}
        status = "success"
        processed_items = 0
        try:
            if job_kind == "maintenance_missing_sources":
                summary = self.repository.scan_missing_sources()
                processed_items = int(summary.get("updated", 0) or 0)
            elif job_kind == "maintenance_library_import":
                ingest = LibraryIngestService(
                    self.repository,
                    thumbnail_service=self.thumbnail_service,
                    duplicate_service=self.duplicate_service,
                )
                processed_items = ingest.import_directory(input_path, recursive=recursive)
                summary = {
                    "imported": processed_items,
                    "input_path": input_path,
                    "recursive": bool(recursive),
                }
            elif job_kind == "maintenance_thumbnails":
                processed_items = self._run_thumbnail_refresh(asset_ids=normalized_asset_ids)
                summary = {"updated": processed_items}
            elif job_kind == "maintenance_exact_duplicates":
                processed_items = self.duplicate_service.rebuild_exact_groups()
                summary = {"groups": processed_items}
            elif job_kind == "maintenance_near_duplicates":
                hash_updates = self.duplicate_service.refresh_perceptual_hashes(
                    normalized_asset_ids or None
                )
                processed_items = self.duplicate_service.rebuild_near_groups()
                summary = {
                    "groups": processed_items,
                    "hash_updates": hash_updates,
                    **self.duplicate_service.last_near_summary,
                }
            elif job_kind == "maintenance_search_index":
                processed_items = self.repository.rebuild_search_index()
                summary = {
                    "indexed_assets": processed_items,
                    "fts_enabled": self.repository.fts_enabled,
                    "search_index_dirty": self.repository.get_search_index_dirty(),
                }
            elif job_kind == "maintenance_ocr_refresh":
                processed_items = self._run_ocr_refresh(asset_ids=normalized_asset_ids)
                summary = {"documents": processed_items}
            elif job_kind == "maintenance_people_refresh":
                processed_items = self._run_people_refresh(asset_ids=normalized_asset_ids)
                summary = {"assignments": processed_items}
            else:
                status = "failed"
                summary = {"error": f"Unsupported maintenance job: {job_kind}"}
        except Exception as exc:
            status = "failed"
            summary = {"error": str(exc)}

        self.repository.finalize_job(
            job_id,
            status=status,
            total_items=max(processed_items, len(normalized_asset_ids)),
            processed_items=processed_items,
            success_count=processed_items if status == "success" else 0,
            partial_count=0,
            failed_count=0 if status == "success" else 1,
            skipped_count=0,
            summary=summary,
        )
        return job_id

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

    def _record_ai_metadata(
        self,
        *,
        asset_id: int,
        source_id: Optional[int],
        variant_id: Optional[int],
        image_path: str,
        settings: AppSettings,
    ) -> None:
        if settings.classification.enabled:
            try:
                if self._classifier is None:
                    self._classifier = ImageClassifier()
                image = self._load_image_for_ai(image_path)
                if image is not None:
                    result = self._classifier.classify(image, model=settings.classification.model)
                    self.repository.clear_asset_tags(asset_id, source="classification")
                    self.repository.add_asset_tag(
                        asset_id,
                        result.category.value,
                        source="classification",
                        confidence=result.confidence,
                        kind="classification",
                    )
                    if result.is_grayscale:
                        self.repository.add_asset_tag(
                            asset_id,
                            "grayscale",
                            source="classification",
                            confidence=1.0,
                            kind="classification",
                        )
            except Exception:
                self._ai_errors.append("classification_failed")

        if settings.face_detection.enabled:
            try:
                if self._face_detector is None:
                    self._face_detector = FaceDetector(
                        use_dnn=settings.face_detection.use_dnn,
                        min_face_size=settings.face_detection.min_face_size,
                    )
                image = self._load_image_for_ai(image_path)
                if image is not None:
                    detection = self._face_detector.detect(
                        image,
                        detect_eyes=settings.face_detection.detect_eyes,
                        suggest_crop=False,
                    )
                    self.repository.clear_faces(asset_id, variant_id=variant_id)
                    self.repository.clear_person_links(asset_id, variant_id=variant_id)
                    face_entries: list[dict] = []
                    for face in detection.faces:
                        face_id = self.repository.add_face(
                            asset_id=asset_id,
                            source_id=source_id,
                            variant_id=variant_id,
                            x=int(face.x),
                            y=int(face.y),
                            w=int(face.width),
                            h=int(face.height),
                            confidence=float(getattr(face, "confidence", 0.0) or 0.0),
                            metadata={"kind": "face"},
                        )
                        face_entries.append(
                            {
                                "face_id": face_id,
                                "asset_id": asset_id,
                                "source_id": source_id,
                                "variant_id": variant_id,
                                "image_path": image_path,
                                "x": int(face.x),
                                "y": int(face.y),
                                "w": int(face.width),
                                "h": int(face.height),
                                "confidence": float(getattr(face, "confidence", 0.0) or 0.0),
                            }
                        )
                    person_provider = get_person_provider()
                    if person_provider is not None and face_entries:
                        try:
                            assignments = person_provider.assign_people(face_entries)
                            provider_name = getattr(person_provider, "name", "plugin")
                            for assignment in list(assignments or []):
                                face_id = int(assignment.get("face_id", 0) or 0)
                                if face_id <= 0:
                                    continue
                                person_id = self.repository.upsert_person(
                                    provider=provider_name,
                                    external_id=str(
                                        assignment.get("external_id")
                                        or assignment.get("person_key")
                                        or face_id
                                    ),
                                    name=str(assignment.get("name", "") or ""),
                                )
                                self.repository.link_person_face(
                                    face_id=face_id,
                                    person_id=person_id,
                                    confidence=float(assignment.get("confidence", 1.0) or 1.0),
                                )
                        except Exception:
                            self._ai_errors.append("person_provider_failed")
            except Exception:
                self._ai_errors.append("face_detection_failed")

        ocr_provider = get_ocr_provider()
        if ocr_provider is not None:
            try:
                text, metadata = ocr_provider.extract_text(image_path)
                if str(text or "").strip():
                    self.repository.add_ocr_document(
                        asset_id=asset_id,
                        source_id=source_id,
                        variant_id=variant_id,
                        provider=getattr(ocr_provider, "name", "plugin"),
                        text=text,
                        metadata=metadata,
                    )
            except Exception:
                self._ai_errors.append("ocr_provider_failed")

    def _load_image_for_ai(self, image_path: str):
        try:
            import cv2
            import numpy as np

            data = np.fromfile(image_path, dtype=np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def _iter_target_assets(
        self,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
    ) -> list[dict]:
        if asset_ids:
            wanted = {int(item) for item in asset_ids if int(item) > 0}
            assets = self.repository.list_assets(limit=5000)
            return [
                asset
                for asset in assets
                if int(asset.get("id", 0) or 0) in wanted
            ]
        return self.repository.list_assets(limit=5000)

    def _run_thumbnail_refresh(
        self,
        *,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
    ) -> int:
        updated = 0
        for asset in self._iter_target_assets(asset_ids):
            asset_id = int(asset.get("id", 0) or 0)
            if asset_id <= 0:
                continue
            path = self.repository.get_asset_visual_path(asset_id)
            if path and os.path.exists(path):
                self.thumbnail_service.ensure_thumbnail(path)
                updated += 1
        return updated

    def _run_ocr_refresh(
        self,
        *,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
    ) -> int:
        provider = get_ocr_provider()
        if provider is None:
            return 0
        created = 0
        for asset in self._iter_target_assets(asset_ids):
            asset_id = int(asset.get("id", 0) or 0)
            if asset_id <= 0:
                continue
            path = self.repository.get_asset_visual_path(asset_id)
            if not path or not os.path.exists(path):
                continue
            self.repository.clear_ocr_documents(asset_id)
            text, metadata = provider.extract_text(path)
            if not str(text or "").strip():
                continue
            source_id = None
            detail = self.repository.get_asset_detail(asset_id)
            sources = list(detail.get("sources", []) or []) if detail else []
            if sources:
                source_id = int(sources[0].get("id", 0) or 0) or None
            self.repository.add_ocr_document(
                asset_id=asset_id,
                source_id=source_id,
                variant_id=None,
                provider=getattr(provider, "name", "plugin"),
                text=text,
                metadata=metadata,
            )
            created += 1
        return created

    def _run_people_refresh(
        self,
        *,
        asset_ids: Optional[list[int] | tuple[int, ...]] = None,
    ) -> int:
        provider = get_person_provider()
        if provider is None:
            return 0
        assignments_total = 0
        for asset in self._iter_target_assets(asset_ids):
            asset_id = int(asset.get("id", 0) or 0)
            if asset_id <= 0:
                continue
            detail = self.repository.get_asset_detail(asset_id)
            if not detail:
                continue
            faces = list(detail.get("faces", []) or [])
            if not faces:
                continue
            self.repository.clear_person_links(asset_id)
            path = self.repository.get_asset_visual_path(asset_id)
            face_entries = []
            for face in faces:
                face_entries.append(
                    {
                        "face_id": int(face.get("id", 0) or 0),
                        "asset_id": asset_id,
                        "source_id": int(face.get("source_id", 0) or 0) or None,
                        "variant_id": int(face.get("variant_id", 0) or 0) or None,
                        "image_path": path,
                        "x": int(face.get("x", 0) or 0),
                        "y": int(face.get("y", 0) or 0),
                        "w": int(face.get("w", 0) or 0),
                        "h": int(face.get("h", 0) or 0),
                        "confidence": float(face.get("confidence", 0.0) or 0.0),
                    }
                )
            assignments = provider.assign_people(face_entries)
            provider_name = getattr(provider, "name", "plugin")
            for assignment in list(assignments or []):
                face_id = int(assignment.get("face_id", 0) or 0)
                if face_id <= 0:
                    continue
                person_id = self.repository.upsert_person(
                    provider=provider_name,
                    external_id=str(
                        assignment.get("external_id")
                        or assignment.get("person_key")
                        or face_id
                    ),
                    name=str(assignment.get("name", "") or ""),
                )
                self.repository.link_person_face(
                    face_id=face_id,
                    person_id=person_id,
                    confidence=float(assignment.get("confidence", 1.0) or 1.0),
                )
                assignments_total += 1
        return assignments_total
