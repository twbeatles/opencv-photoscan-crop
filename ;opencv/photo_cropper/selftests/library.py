#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Library self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_sqlite_pragmas_and_ingest_cancel_progress() -> None:
    import os
    import tempfile
    import threading

    import cv2
    import numpy as np

    from ..core.library import LibraryIngestService, LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    class NoopThumbnailService:
        def ensure_thumbnail(self, _path: str) -> str:
            return ""

    with tempfile.TemporaryDirectory(prefix="photocropper_library_pragmas_") as td:
        db_path = os.path.join(td, "library.db")
        store = LibrarySqliteStore(db_path=db_path)
        repository = LibraryRepository(store)
        with store.connect() as conn:
            assert int(conn.execute("PRAGMA foreign_keys").fetchone()[0]) == 1
            assert int(conn.execute("PRAGMA busy_timeout").fetchone()[0]) >= 30000

        image_dir = os.path.join(td, "images")
        os.makedirs(image_dir, exist_ok=True)
        for idx in range(2):
            image = np.zeros((8, 8, 3), dtype=np.uint8)
            ok, encoded = cv2.imencode(".jpg", image)
            assert ok
            encoded.tofile(os.path.join(image_dir, f"{idx}.jpg"))

        cancel_event = threading.Event()
        progress_calls: list[tuple[int, int]] = []

        def progress(processed: int, total: int, _path: str) -> None:
            progress_calls.append((processed, total))
            cancel_event.set()

        ingest = LibraryIngestService(
            repository,
            thumbnail_service=NoopThumbnailService(),
        )
        count = ingest.import_directory(
            image_dir,
            recursive=True,
            progress_callback=progress,
            cancel_event=cancel_event,
        )
        assert count == 1
        assert progress_calls and progress_calls[0][1] == 2

def _test_library_catalog_import_and_duplicates() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library import DuplicateService, LibraryIngestService, ThumbnailService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_library_catalog_") as td:
        image_dir = os.path.join(td, "images")
        os.makedirs(image_dir, exist_ok=True)
        sample = np.full((120, 180, 3), 190, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", sample)
        assert ok
        for name in ("a.jpg", "b.jpg"):
            encoded.tofile(os.path.join(image_dir, name))

        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        thumbnails = ThumbnailService(
            thumbnails_dir=os.path.join(td, "thumbs"),
            size=96,
        )
        duplicates = DuplicateService(repository)
        ingest = LibraryIngestService(
            repository,
            thumbnail_service=thumbnails,
            duplicate_service=duplicates,
        )

        assert ingest.import_directory(image_dir, recursive=True) == 2
        assert ingest.import_directory(image_dir, recursive=True) == 2

        assets = repository.list_assets(limit=10)
        assert len(assets) == 2
        duplicate_groups = repository.list_duplicate_groups(kind="exact")
        assert len(duplicate_groups) == 1
        for asset in assets:
            assert os.path.exists(asset["primary_source_path"])

def _test_library_search_and_collections() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library.query_service import QueryService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_library_search_") as td:
        input_dir = os.path.join(td, "input")
        os.makedirs(input_dir, exist_ok=True)
        image = np.full((100, 150, 3), 180, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        image_path = os.path.join(input_dir, "receipt.jpg")
        encoded.tofile(image_path)

        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        record = repository.upsert_source(image_path)
        asset_id = int(record["asset_id"])
        repository.set_asset_note(asset_id, "receipt from archive")
        collection_id = repository.create_collection("Archive")
        assert collection_id is not None
        repository.add_asset_to_collection(asset_id, int(collection_id))

        query = QueryService(repository)
        assets = query.list_assets(search_text="receipt", limit=10)
        assert len(assets) == 1
        filtered = query.list_assets(collection_id=int(collection_id), limit=10)
        assert len(filtered) == 1

def _test_duplicate_service_near_groups() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library.duplicate_service import DuplicateService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_near_dupes_") as td:
        image_a = np.full((220, 220, 3), 220, dtype=np.uint8)
        cv2.rectangle(image_a, (40, 50), (180, 170), (40, 40, 40), 4)
        cv2.line(image_a, (60, 60), (160, 160), (90, 90, 90), 3)
        image_b = image_a.copy()
        cv2.rectangle(image_b, (42, 52), (178, 168), (40, 40, 40), 4)
        cv2.circle(image_b, (110, 110), 8, (120, 120, 120), -1)

        path_a = os.path.join(td, "a.jpg")
        path_b = os.path.join(td, "b.jpg")
        ok, encoded_a = cv2.imencode(".jpg", image_a)
        assert ok
        ok, encoded_b = cv2.imencode(".jpg", image_b)
        assert ok
        encoded_a.tofile(path_a)
        encoded_b.tofile(path_b)

        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        repository.upsert_source(path_a)
        repository.upsert_source(path_b)

        duplicate_service = DuplicateService(repository)
        assert duplicate_service.rebuild_near_groups(max_distance=20) >= 1
        groups = duplicate_service.list_groups(kind="near")
        assert len(groups) >= 1

def _test_duplicate_preferences_preserved_on_rebuild() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library.duplicate_service import DuplicateService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_dupe_prefs_") as td:
        image = np.full((120, 180, 3), 160, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        path_a = os.path.join(td, "a.jpg")
        path_b = os.path.join(td, "b.jpg")
        encoded.tofile(path_a)
        encoded.tofile(path_b)

        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        record_a = repository.upsert_source(path_a)
        record_b = repository.upsert_source(path_b)
        duplicate_service = DuplicateService(repository)
        assert duplicate_service.rebuild_exact_groups() == 1
        group = repository.list_duplicate_groups(kind="exact")[0]
        group_id = int(group["id"])
        asset_a = int(record_a["asset_id"])
        asset_b = int(record_b["asset_id"])

        duplicate_service.set_representative(group_id, asset_b)
        duplicate_service.set_excluded(group_id, asset_a, True)
        duplicate_service.rebuild_exact_groups()

        rebuilt = repository.list_duplicate_groups(kind="exact")[0]
        assert int(rebuilt["representative_asset_id"]) == asset_b
        members = {
            int(item["asset_id"]): item
            for item in repository.list_duplicate_group_members(int(rebuilt["id"]))
        }
        assert int(members[asset_a]["is_excluded"]) == 1

def _test_source_relink_unique_and_ambiguous() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library import LibraryIngestService, ThumbnailService
    from ..core.library.duplicate_service import DuplicateService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_relink_unique_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        ingest = LibraryIngestService(
            repository,
            thumbnail_service=ThumbnailService(thumbnails_dir=os.path.join(td, "thumbs")),
            duplicate_service=DuplicateService(repository),
        )
        image = np.full((100, 140, 3), 220, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok

        original = os.path.join(td, "original.jpg")
        renamed = os.path.join(td, "renamed.jpg")
        encoded.tofile(original)
        first = repository.upsert_source(original)
        os.replace(original, renamed)
        stats = repository.scan_missing_sources()
        assert stats["missing"] == 1
        relinked = ingest.ingest_file(renamed)
        assert str(relinked["ingest_state"]) == "relinked"
        assert int(relinked["asset_id"]) == int(first["asset_id"])

    with tempfile.TemporaryDirectory(prefix="photocropper_relink_ambiguous_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        ingest = LibraryIngestService(
            repository,
            thumbnail_service=ThumbnailService(thumbnails_dir=os.path.join(td, "thumbs")),
            duplicate_service=DuplicateService(repository),
        )
        image = np.full((100, 140, 3), 210, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok

        path_a = os.path.join(td, "missing_a.jpg")
        path_b = os.path.join(td, "missing_b.jpg")
        pending = os.path.join(td, "pending.jpg")
        encoded.tofile(path_a)
        encoded.tofile(path_b)
        repository.upsert_source(path_a)
        repository.upsert_source(path_b)
        os.remove(path_a)
        os.remove(path_b)
        repository.scan_missing_sources()
        encoded.tofile(pending)
        record = ingest.ingest_file(pending)
        assert str(record["ingest_state"]) == "ambiguous_relink"
        review_items = repository.list_review_items(limit=10)
        assert review_items
        assert review_items[0]["reason"] == "source_relink_required"

def _test_asset_query_filters_and_timeline() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.library import AssetQuery
    from ..core.library.query_service import QueryService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_asset_query_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        image = np.full((100, 160, 3), 200, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        path = os.path.join(td, "receipt.jpg")
        variant_path = os.path.join(td, "receipt_variant.jpg")
        encoded.tofile(path)
        encoded.tofile(variant_path)

        record = repository.upsert_source(path)
        asset_id = int(record["asset_id"])
        source_id = int(record["source_id"])
        repository.set_asset_note(asset_id, "receipt archive note")
        repository.add_asset_tag(asset_id, "receipt")
        collection_id = repository.create_collection("Archive")
        assert collection_id is not None
        repository.add_asset_to_collection(asset_id, int(collection_id))
        job_id = repository.create_job(
            job_kind="selftest_batch",
            input_path=td,
            output_path=os.path.join(td, "output"),
            recipe_name="문서 스캔",
            status="success",
        )
        job_item_id = repository.add_job_item(
            job_id=job_id,
            source_path=path,
            asset_id=asset_id,
            source_id=source_id,
            status="success",
            message="done",
            output_paths=[variant_path],
            processing_time_ms=1.0,
        )
        repository.upsert_variant(
            asset_id=asset_id,
            source_id=source_id,
            file_path=variant_path,
            variant_kind="cropped",
            job_item_id=job_item_id,
        )
        repository.add_ocr_document(
            asset_id=asset_id,
            source_id=source_id,
            variant_id=None,
            provider="selftest",
            text="receipt archive text",
        )
        repository.create_review_item(
            asset_id=asset_id,
            source_id=source_id,
            variant_id=None,
            job_id=job_id,
            job_item_id=job_item_id,
            status="new",
            reason="check",
        )

        query_service = QueryService(repository)
        asset_query = AssetQuery(
            search_text="receipt",
            collection_id=int(collection_id),
            tag_names=("receipt",),
            review_status="new",
            sort_by="updated",
            page=1,
            page_size=1,
        )
        rows = query_service.list_assets(asset_query)
        assert len(rows) == 1
        assert query_service.count_assets(asset_query) == 1
        timeline = query_service.get_asset_timeline(asset_id)
        event_types = {getattr(event, "event_type", "") for event in timeline}
        assert "source" in event_types
        assert "review" in event_types
        assert "variant" in event_types

__all__ = [
    "_test_sqlite_pragmas_and_ingest_cancel_progress",
    "_test_library_catalog_import_and_duplicates",
    "_test_library_search_and_collections",
    "_test_duplicate_service_near_groups",
    "_test_duplicate_preferences_preserved_on_rebuild",
    "_test_source_relink_unique_and_ambiguous",
    "_test_asset_query_filters_and_timeline",
]
