#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Jobs Recipes self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_job_orchestrator_records_variants_and_review_queue() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.batch import BatchProgress, FileResult, ProcessStatus
    from ..core.jobs import JobOrchestrator
    from ..core.library import DuplicateService, ThumbnailService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_job_catalog_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(td, "output")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        image = np.full((140, 220, 3), 200, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        src_success = os.path.join(input_dir, "success.jpg")
        src_failed = os.path.join(input_dir, "failed.jpg")
        out_success = os.path.join(output_dir, "success_cropped.jpg")
        encoded.tofile(src_success)
        encoded.tofile(src_failed)
        encoded.tofile(out_success)

        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        thumbnails = ThumbnailService(
            thumbnails_dir=os.path.join(td, "thumbs"),
            size=96,
        )
        orchestrator = JobOrchestrator(
            repository,
            thumbnail_service=thumbnails,
            duplicate_service=DuplicateService(repository),
        )
        settings = AppSettings()
        job_id = orchestrator.create_job(
            job_kind="selftest_batch",
            input_path=input_dir,
            output_path=output_dir,
            recipe_name="문서 스캔",
        )

        progress = BatchProgress(
            total=2,
            processed=2,
            success=1,
            failed=1,
            is_running=False,
        )
        results = [
            FileResult(
                filename="success.jpg",
                status=ProcessStatus.SUCCESS,
                source_path=src_success,
                output_path=out_success,
                output_paths=[out_success],
            ),
            FileResult(
                filename="failed.jpg",
                status=ProcessStatus.FAILED,
                source_path=src_failed,
                message="synthetic failure",
            ),
        ]
        orchestrator.finalize_job(
            job_id=job_id,
            progress=progress,
            results=results,
            settings=settings,
            recipe_name="문서 스캔",
            job_kind="selftest_batch",
        )

        jobs = repository.list_jobs(limit=5)
        assert jobs
        assert jobs[0]["status"] == "partial_success"
        assets = repository.list_assets(limit=10)
        assert len(assets) == 2
        success_asset = next(
            asset for asset in assets if asset["primary_source_path"] == src_success
        )
        detail = repository.get_asset_detail(int(success_asset["id"]))
        assert detail is not None
        assert len(detail["variants"]) == 1
        review_items = repository.list_review_items(limit=10)
        assert len(review_items) == 1
        assert review_items[0]["primary_source_path"] == src_failed

def _test_recipe_determinism_and_preserved_global_state() -> None:
    import os
    import tempfile

    from ..core.recipes.manager import RecipeManager, RecipeRecord
    from ..core.settings_model import AppSettings

    original_env = {
        "APPDATA": os.environ.get("APPDATA"),
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA"),
        "HOME": os.environ.get("HOME"),
    }
    with tempfile.TemporaryDirectory(prefix="photocropper_recipe_det_") as td:
        os.environ["APPDATA"] = td
        os.environ["LOCALAPPDATA"] = td
        os.environ["HOME"] = td
        manager = RecipeManager()
        manager.save_recipe(
            RecipeRecord(
                name="Deterministic",
                settings_snapshot={
                    "algorithm": {"canny_min": 12},
                    "output": {"jpg_quality": 81},
                },
            )
        )

        settings_a = AppSettings()
        settings_a.algorithm.canny_min = 220
        settings_a.output.jpg_quality = 50
        settings_a.ui.theme = "light"
        settings_a.last_input_path = "A"

        settings_b = AppSettings()
        settings_b.algorithm.canny_min = 140
        settings_b.output.jpg_quality = 30
        settings_b.ui.theme = "dark"
        settings_b.last_input_path = "B"

        assert manager.apply_recipe("Deterministic", settings_a) is True
        assert manager.apply_recipe("Deterministic", settings_b) is True
        assert settings_a.algorithm.canny_min == 12
        assert settings_b.algorithm.canny_min == 12
        assert settings_a.output.jpg_quality == 81
        assert settings_b.output.jpg_quality == 81
        assert settings_a.ui.theme == "light"
        assert settings_b.ui.theme == "dark"
        assert settings_a.last_input_path == "A"
        assert settings_b.last_input_path == "B"
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

def _test_review_service_guard_and_reprocess_queue() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.jobs import JobOrchestrator
    from ..core.library import DuplicateService, ReviewService, ThumbnailService
    from ..core.library.repository import LibraryRepository
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_review_queue_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        thumbnails = ThumbnailService(thumbnails_dir=os.path.join(td, "thumbs"))
        orchestrator = JobOrchestrator(
            repository,
            thumbnail_service=thumbnails,
            duplicate_service=DuplicateService(repository),
        )
        review_service = ReviewService(
            repository,
            create_reprocess_job=orchestrator.prepare_review_reprocess,
        )
        image = np.full((120, 180, 3), 170, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        source_path = os.path.join(td, "source.jpg")
        variant_path = os.path.join(td, "variant.jpg")
        encoded.tofile(source_path)
        encoded.tofile(variant_path)

        record = repository.upsert_source(source_path)
        asset_id = int(record["asset_id"])
        source_id = int(record["source_id"])
        origin_job_id = repository.create_job(
            job_kind="selftest_batch",
            input_path=td,
            output_path=os.path.join(td, "output"),
            recipe_name="문서 스캔",
            status="success",
        )
        review_id = repository.create_review_item(
            asset_id=asset_id,
            source_id=source_id,
            variant_id=None,
            job_id=origin_job_id,
            job_item_id=None,
            status="new",
            reason="manual_review",
        )

        assert review_service.approve(review_id) is False
        variant_id = repository.upsert_variant(
            asset_id=asset_id,
            source_id=source_id,
            file_path=variant_path,
            variant_kind="manual_fix",
        )
        assert review_service.approve(review_id, variant_id=variant_id) is True
        approved = repository.get_review_item(review_id)
        assert approved is not None
        assert approved["status"] == "approved"

        review_id_2 = repository.create_review_item(
            asset_id=asset_id,
            source_id=source_id,
            variant_id=None,
            job_id=origin_job_id,
            job_item_id=None,
            status="new",
            reason="retry_needed",
        )
        queued_job_id = review_service.enqueue_reprocess(review_id_2)
        assert queued_job_id is not None
        queued_job = repository.get_job(int(queued_job_id))
        assert queued_job is not None
        assert queued_job["status"] == "queued"
        requested = repository.get_review_item(review_id_2)
        assert requested is not None
        assert requested["status"] == "reprocess_requested"

__all__ = [
    "_test_job_orchestrator_records_variants_and_review_queue",
    "_test_recipe_determinism_and_preserved_global_state",
    "_test_review_service_guard_and_reprocess_queue",
]
