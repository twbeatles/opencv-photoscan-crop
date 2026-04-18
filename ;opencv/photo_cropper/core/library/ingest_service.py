from __future__ import annotations

from typing import Optional, Sequence

from ...utils.file_helpers import get_image_files
from .duplicate_service import DuplicateService
from .repository import LibraryRepository
from .thumbnail_service import ThumbnailService


class LibraryIngestService:
    def __init__(
        self,
        repository: LibraryRepository,
        thumbnail_service: Optional[ThumbnailService] = None,
        duplicate_service: Optional[DuplicateService] = None,
    ):
        self.repository = repository
        self.thumbnail_service = thumbnail_service or ThumbnailService()
        self.duplicate_service = duplicate_service or DuplicateService(repository)

    def ingest_file(self, file_path: str) -> dict:
        record = self.repository.upsert_source(file_path)
        ingest_state = str(record.get("ingest_state", "") or "")
        self.thumbnail_service.ensure_thumbnail(file_path)
        if ingest_state == "ambiguous_relink":
            self.repository.create_review_item(
                asset_id=None,
                source_id=None,
                variant_id=None,
                job_id=None,
                job_item_id=None,
                status="new",
                reason="source_relink_required",
                action_context={
                    "pending_source_path": str(record.get("source_path", "") or ""),
                    "pending_source_hash": str(record.get("source_hash", "") or ""),
                    "candidate_source_ids": list(record.get("candidate_source_ids", []) or []),
                    "candidate_asset_ids": list(record.get("candidate_asset_ids", []) or []),
                },
            )
        return record

    def import_directory(
        self,
        directory: str,
        *,
        recursive: bool = True,
        excluded_roots: Optional[Sequence[str]] = None,
    ) -> int:
        files = get_image_files(
            directory,
            recursive=recursive,
            excluded_roots=excluded_roots,
        )
        count = 0
        for path in files:
            record = self.ingest_file(path)
            if str(record.get("ingest_state", "") or "") != "ambiguous_relink":
                count += 1
        self.duplicate_service.rebuild_exact_groups()
        return count

    def scan_missing_sources(self) -> dict:
        return self.repository.scan_missing_sources()
