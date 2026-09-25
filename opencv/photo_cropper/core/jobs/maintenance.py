from __future__ import annotations

import os
from typing import Any, Optional

from ..library import (
    LibraryIngestService,
    get_ocr_provider,
    get_person_provider,
)


class JobMaintenanceMixin:
    """Library maintenance jobs (thumbnails, duplicates, search index, OCR, people)."""

    repository: Any
    thumbnail_service: Any
    duplicate_service: Any

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


__all__ = ["JobMaintenanceMixin"]
