#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Batch session service self-tests."""

from __future__ import annotations


def _test_batch_session_service_smoke() -> None:
    from ..core.batch import BatchSessionService

    service = BatchSessionService()
    assert service.processor is None
    assert service.failed_files == []
    service.request_stop()
    service.cleanup()


def _test_batch_session_service_reentry_guard() -> None:
    from ..core.batch import BatchSessionService
    from ..core.settings_model import AppSettings

    class DummyProcessor:
        def __init__(self) -> None:
            self.is_running = True
            self.cleaned = False

        def cleanup(self) -> None:
            self.cleaned = True

    service = BatchSessionService()
    dummy = DummyProcessor()
    service._processor = dummy

    try:
        service.create_processor(AppSettings())
    except RuntimeError as exc:
        assert "already running" in str(exc)
    else:
        raise AssertionError("Expected batch session reentry guard to raise RuntimeError")

    assert service.processor is dummy
    assert dummy.cleaned is False
    service._processor = None


def _test_batch_thread_local_reuse() -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    settings.performance.enable_multithreading = True
    settings.performance.thread_count = 4
    settings.face_detection.enabled = True
    settings.classification.enabled = True
    settings.classification.auto_folder = True

    processor = BatchProcessor(settings)

    def worker_probe():
        samples = []
        for _ in range(3):
            samples.append(
                (
                    id(processor._get_worker_processor()),
                    id(processor._get_face_detector()),
                    id(processor._get_classifier()),
                    id(processor._get_smart_enhancer()),
                )
            )
        first = samples[0]
        assert all(item == first for item in samples), "Thread-local object churn detected"
        return threading.get_ident(), first

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker_probe) for _ in range(8)]
        results = [f.result() for f in futures]

    unique_processor_ids = {item[1][0] for item in results}
    unique_face_ids = {item[1][1] for item in results}
    unique_classifier_ids = {item[1][2] for item in results}
    unique_smart_ids = {item[1][3] for item in results}

    assert len(unique_processor_ids) <= settings.performance.thread_count
    assert len(unique_face_ids) <= settings.performance.thread_count
    assert len(unique_classifier_ids) <= settings.performance.thread_count
    assert len(unique_smart_ids) <= settings.performance.thread_count


def _test_batch_post_pipeline_order() -> None:
    import numpy as np

    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    processor = BatchProcessor(settings)

    calls = []

    def _face(img):
        calls.append("face")
        return img

    def _smart(img):
        calls.append("smart")
        return img

    def _resize(img):
        calls.append("resize")
        return img

    def _classify(img, out_dir):
        calls.append("classify")
        return out_dir

    def _watermark(img):
        calls.append("watermark")
        return img

    processor._maybe_apply_face_adjustments = _face
    processor._maybe_apply_smart_enhancement = _smart
    processor._maybe_apply_resize = _resize
    processor._resolve_output_dir_for_classification = _classify
    processor._maybe_apply_watermark = _watermark

    img = np.full((64, 64, 3), 127, dtype=np.uint8)
    out_img, out_dir = processor._run_post_pipeline(img, "out")

    assert out_img is not None
    assert out_dir == "out"
    assert calls == ["face", "smart", "resize", "classify", "watermark"], calls


def _test_output_reservation_is_thread_safe() -> None:
    import os
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    processor = BatchProcessor(AppSettings())
    with tempfile.TemporaryDirectory(prefix="photocropper_reserve_") as td:
        target = os.path.join(td, "same.jpg")
        with ThreadPoolExecutor(max_workers=8) as executor:
            paths = list(executor.map(lambda _idx: processor._ensure_unique_output_path(target), range(8)))
        assert len(set(paths)) == 8
        assert paths[0] == target


def _test_processing_logger_partial_summary() -> None:
    import tempfile

    from ..utils.processing_log import ProcessingLogger

    with tempfile.TemporaryDirectory(prefix="photocropper_log_partial_") as td:
        logger = ProcessingLogger(log_directory=td)
        logger.start_session("input", "output", 1)
        logger.log_partial(
            input_file="input/sample.jpg",
            output_file="output/sample_photo01.jpg",
            detail_message="partial save",
            processing_time_ms=12.5,
            file_size_before_kb=10.0,
            file_size_after_kb=5.0,
        )
        summary = logger.get_summary()
        assert summary["partial_success"] == 1
        assert summary["success_rate"] == 100.0
        session = logger.end_session()
        assert session is not None
        assert session.partial_count == 1
