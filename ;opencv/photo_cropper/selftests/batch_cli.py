#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Batch Cli self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

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

def _test_boundary_failed_file_collection_helper() -> None:
    import os
    import tempfile

    from ..core.batch import ProcessStatus
    from ..core.manual_extract import collect_boundary_failed_files

    class _Result:
        def __init__(self, status, message, filename):
            self.status = status
            self.message = message
            self.filename = filename

    with tempfile.TemporaryDirectory(prefix="photocropper_boundary_fail_") as td:
        in_dir = os.path.join(td, "in")
        os.makedirs(in_dir, exist_ok=True)
        f1 = os.path.join(in_dir, "a.jpg")
        f2 = os.path.join(in_dir, "b.jpg")
        with open(f1, "wb") as f:
            f.write(b"x")
        with open(f2, "wb") as f:
            f.write(b"y")

        results = [
            _Result(ProcessStatus.FAILED, "Failed to detect photo boundary.", "a.jpg"),
            _Result(ProcessStatus.FAILED, "other error", "b.jpg"),
        ]

        resolved = collect_boundary_failed_files(
            results=results,
            input_root=in_dir,
            image_list=[f1, f2],
            batch_failed_entries=["a.jpg", "b.jpg"],
            recursive_search=False,
            get_image_files_fn=lambda root, recursive=False: [f1, f2],
            logger=None,
        )
        assert len(resolved) == 1
        assert os.path.basename(resolved[0]).lower() == "a.jpg"

def _test_boundary_failed_file_collection_prefers_relative_paths() -> None:
    import os
    import tempfile

    from ..core.batch import ProcessStatus
    from ..core.manual_extract import collect_boundary_failed_files

    class _Result:
        def __init__(self, status, message, filename):
            self.status = status
            self.message = message
            self.filename = filename

    with tempfile.TemporaryDirectory(prefix="photocropper_boundary_relative_") as td:
        in_dir = os.path.join(td, "input_root")
        left_dir = os.path.join(in_dir, "left_group")
        right_dir = os.path.join(in_dir, "right_group")
        os.makedirs(left_dir, exist_ok=True)
        os.makedirs(right_dir, exist_ok=True)
        left_file = os.path.join(left_dir, "photo.jpg")
        right_file = os.path.join(right_dir, "photo.jpg")
        with open(left_file, "wb") as f:
            f.write(b"left")
        with open(right_file, "wb") as f:
            f.write(b"right")

        results = [
            _Result(
                ProcessStatus.FAILED,
                "Failed to detect photo boundary.",
                os.path.join("right_group", "photo.jpg"),
            ),
        ]

        resolved = collect_boundary_failed_files(
            results=results,
            input_root=in_dir,
            image_list=[left_file, right_file],
            batch_failed_entries=["photo.jpg"],
            recursive_search=True,
            get_image_files_fn=lambda root, recursive=False: [left_file, right_file],
            logger=None,
        )
        assert resolved == [os.path.normpath(right_file)]

def _test_recursive_scan_excludes_internal_generated_dirs() -> None:
    import os
    import tempfile

    from ..utils.file_helpers import build_recursive_excluded_roots, get_image_files

    with tempfile.TemporaryDirectory(prefix="photocropper_recursive_scan_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(input_dir, "output_cropped")
        keep_dir = os.path.join(input_dir, "keep", "nested")
        failed_dir = os.path.join(input_dir, "_failed", "nested")
        backup_dir = os.path.join(input_dir, "backup")
        hidden_dir = os.path.join(input_dir, "misc", ".photocropper")

        for directory in (output_dir, keep_dir, failed_dir, backup_dir, hidden_dir):
            os.makedirs(directory, exist_ok=True)

        file_map = {
            os.path.join(input_dir, "root.jpg"): b"root",
            os.path.join(keep_dir, "keep.jpg"): b"keep",
            os.path.join(output_dir, "out.jpg"): b"out",
            os.path.join(failed_dir, "failed.jpg"): b"failed",
            os.path.join(backup_dir, "backup.jpg"): b"backup",
            os.path.join(hidden_dir, "index.jpg"): b"index",
        }
        for path, payload in file_map.items():
            with open(path, "wb") as f:
                f.write(payload)

        excluded = build_recursive_excluded_roots(
            input_dir,
            output_dir,
            failed_folder_name="_failed",
        )
        scanned = get_image_files(
            input_dir,
            recursive=True,
            excluded_roots=excluded,
        )
        rel_paths = {
            os.path.relpath(path, input_dir).replace("\\", "/")
            for path in scanned
        }
        assert rel_paths == {"root.jpg", "keep/nested/keep.jpg"}

def _test_classify_failed_files_preserves_relative_dirs() -> None:
    import os
    import tempfile

    from ..utils.file_helpers import classify_failed_files

    with tempfile.TemporaryDirectory(prefix="photocropper_failed_relative_") as td:
        input_dir = os.path.join(td, "input")
        source_dir = os.path.join(input_dir, "nested", "deep")
        os.makedirs(source_dir, exist_ok=True)
        source_file = os.path.join(source_dir, "sample.jpg")
        with open(source_file, "wb") as f:
            f.write(b"sample")

        moved_count, errors = classify_failed_files(
            [source_file],
            input_dir,
            failed_folder_name="_failed",
            copy_mode=True,
            input_root=input_dir,
        )
        failed_copy = os.path.join(input_dir, "_failed", "nested", "deep", "sample.jpg")
        assert moved_count == 1
        assert errors == []
        assert os.path.exists(source_file)
        assert os.path.exists(failed_copy)

def _test_cli_settings_merge_priority() -> None:
    import json
    import os
    import tempfile

    from .. import cli as cli_mod
    from ..core.batch_profile_manager import BatchProfileManager
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_merge_") as td:
        profiles_dir = os.path.join(td, "profiles")
        manager = BatchProfileManager(profiles_dir=profiles_dir)

        preset_settings = AppSettings()
        preset_settings.algorithm.canny_min = 11
        preset_settings.algorithm.canny_max = 111
        preset_settings.output.jpg_quality = 88
        preset_settings.classification.model = "basic"
        created = manager.create_profile("selftest-merge", preset_settings)
        assert created

        config_path = os.path.join(td, "config.json")
        config_data = {
            "algorithm": {"canny_min": 22, "canny_max": 44},
            "advanced_processing": {"auto_deskew": True},
            "classification": {"model": "advanced", "min_confidence": 0.65},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        parser = cli_mod.create_parser()
        args = parser.parse_args(
            [
                "--preset",
                "selftest-merge",
                "--config",
                config_path,
                "--canny-min",
                "33",
                "--min-area-ratio",
                "0.12",
                "--max-area-ratio",
                "0.91",
                "--bg-mask-delta",
                "41",
                "--adaptive-block-size",
                "21",
                "--adaptive-c",
                "3.5",
                "--classify-model",
                "custom",
            ]
        )

        original_get_manager = cli_mod.get_batch_profile_manager
        cli_mod.get_batch_profile_manager = lambda: manager
        try:
            merged = cli_mod.build_settings_from_args(args)
        finally:
            cli_mod.get_batch_profile_manager = original_get_manager

        assert merged.algorithm.canny_min == 33  # CLI overrides config/preset
        assert merged.algorithm.canny_max == 44  # config overrides preset
        assert abs(float(merged.algorithm.min_area_ratio) - 0.12) < 1e-6
        assert abs(float(merged.algorithm.max_area_ratio) - 0.91) < 1e-6
        assert abs(float(merged.algorithm.bg_mask_delta) - 41.0) < 1e-6
        assert int(merged.algorithm.adaptive_block_size) == 21
        assert abs(float(merged.algorithm.adaptive_c) - 3.5) < 1e-6
        assert merged.output.jpg_quality == 88  # preset applied
        assert merged.classification.model == "advanced"  # CLI alias normalized
        assert abs(merged.classification.min_confidence - 0.65) < 1e-6
        assert merged.advanced.auto_deskew is True  # legacy alias mapped

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

def _test_skip_processed_with_classification_subfolder() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.image_classifier import ClassificationResult, ImageCategory
    from ..core.image import CropResult, DetectionStage
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    settings.classification.enabled = True
    settings.classification.auto_folder = True
    settings.classification.category_folders["portrait"] = "인물커스텀"
    settings.filter.skip_processed = True
    settings.filter.skip_small_images = False
    settings.output.output_format = "JPG"

    processor = BatchProcessor(settings)

    class FakeClassifier:
        def classify(self, image, model="basic"):
            return ClassificationResult(
                category=ImageCategory.PORTRAIT,
                confidence=0.99,
            )

        def get_output_folder(self, category):
            return {
                ImageCategory.PORTRAIT: "인물",
                ImageCategory.LANDSCAPE: "풍경",
                ImageCategory.DOCUMENT: "문서",
                ImageCategory.BLACKWHITE: "흑백",
                ImageCategory.OTHER: "기타",
            }.get(category, "기타")

    class FakeProcessor:
        @staticmethod
        def get_image_info(_path):
            return (1024, 768, 3)

        @staticmethod
        def process_image(_path, **_kwargs):
            img = np.full((240, 320, 3), 180, dtype=np.uint8)
            return CropResult(
                success=True,
                image=img,
                message="OK",
                detection_stage=DetectionStage.CANNY,
            )

        @staticmethod
        def save_image(
            image,
            output_path,
            output_format="JPG",
            jpg_quality=95,
            png_compression=6,
            webp_quality=90,
            source_path=None,
            preserve_metadata=False,
        ):
            del output_format, png_compression, webp_quality, source_path, preserve_metadata
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(jpg_quality)])
            if not ok:
                return False, "encode failed", 0.0
            buf.tofile(output_path)
            return True, "ok", os.path.getsize(output_path) / 1024.0

    fake_classifier = FakeClassifier()
    fake_worker = FakeProcessor()
    processor._get_classifier = lambda: fake_classifier
    processor._get_worker_processor = lambda: fake_worker

    with tempfile.TemporaryDirectory(prefix="photocropper_skipcls_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        src = os.path.join(in_dir, "sample.jpg")
        base = np.full((240, 320, 3), 150, dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", base)
        assert ok
        buf.tofile(src)

        r1 = processor.process_single(src, out_dir)
        assert r1.status == ProcessStatus.SUCCESS, r1.message
        assert r1.output_path
        assert os.path.isdir(os.path.join(out_dir, "인물커스텀"))
        assert os.path.exists(r1.output_path)

        r2 = processor.process_single(src, out_dir)
        assert r2.status == ProcessStatus.SKIPPED, r2.message

def _test_cli_new_crop_options() -> None:
    from .. import cli as cli_mod

    parser = cli_mod.create_parser()
    args = parser.parse_args(
        [
            "--preserve-metadata",
            "--no-perspective-correct",
            "--multi-photo-merge-distance",
            "77",
            "--multi-photo-separate-folders",
        ]
    )
    settings = cli_mod.build_settings_from_args(args)
    assert settings.output.preserve_metadata is True
    assert settings.advanced.perspective_correct is False
    assert settings.multi_photo.enabled is True
    assert settings.multi_photo.merge_distance == 77
    assert settings.multi_photo.separate_output_folders is True

    args_on = parser.parse_args(["--perspective-correct"])
    settings_on = cli_mod.build_settings_from_args(args_on)
    assert settings_on.advanced.perspective_correct is True

def _test_processed_index_roundtrip_and_source_change() -> None:
    import os
    import tempfile
    import time

    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    settings.filter.skip_processed = True
    settings.file_management.use_naming_rules = True
    processor = BatchProcessor(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_index_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        src = os.path.join(in_dir, "sample.jpg")
        out = os.path.join(out_dir, "sample_cropped.jpg")
        with open(src, "wb") as f:
            f.write(b"source-v1")
        with open(out, "wb") as f:
            f.write(b"result-v1")

        processor.record_processed_outputs(src, out_dir, [out])
        matched, usable, status = processor.lookup_processed_outputs_from_index(
            src, out_dir
        )
        assert usable is True
        assert status == "success"
        assert matched is not None and len(matched) == 1
        assert os.path.normcase(os.path.abspath(matched[0])) == os.path.normcase(
            os.path.abspath(out)
        )

        time.sleep(0.01)
        with open(src, "ab") as f:
            f.write(b"-changed")

        matched_changed, usable_changed, status_changed = (
            processor.lookup_processed_outputs_from_index(src, out_dir)
        )
        assert usable_changed is True
        assert status_changed == ""
        assert matched_changed is None

def _test_processed_index_backward_compat_and_partial_status() -> None:
    import json
    import os
    import tempfile

    from ..core.processed_index import (
        INDEX_DIRNAME,
        INDEX_FILENAME,
        RECORD_STATUS_PARTIAL,
        ProcessedIndexStore,
        build_pipeline_signature,
    )
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    pipeline_signature = build_pipeline_signature(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_index_compat_") as td:
        output_dir = os.path.join(td, "out")
        os.makedirs(output_dir, exist_ok=True)
        index_root = os.path.join(output_dir, INDEX_DIRNAME)
        os.makedirs(index_root, exist_ok=True)

        src = os.path.join(td, "source.jpg")
        out = os.path.join(output_dir, "source_cropped.jpg")
        with open(src, "wb") as f:
            f.write(b"source")
        with open(out, "wb") as f:
            f.write(b"output")

        st = os.stat(src)
        legacy_payload = {
            "version": 1,
            "updated_at": "2026-03-25T00:00:00Z",
            "records": [
                {
                    "source_path": src,
                    "size": int(st.st_size),
                    "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                    "outputs": [out],
                    "pipeline_signature": pipeline_signature,
                }
            ],
        }
        with open(
            os.path.join(index_root, INDEX_FILENAME),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(legacy_payload, f, ensure_ascii=False)

        store = ProcessedIndexStore(output_dir)
        matched, usable, status = store.lookup_outputs(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            pipeline_signature=pipeline_signature,
        )
        assert usable is True
        assert status == "success"
        assert matched is not None and len(matched) == 1

        assert store.upsert_record(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            outputs=[out],
            pipeline_signature=pipeline_signature,
            status=RECORD_STATUS_PARTIAL,
        )
        partial_outputs, partial_usable, partial_status = store.lookup_outputs(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            pipeline_signature=pipeline_signature,
        )
        assert partial_usable is True
        assert partial_status == "partial"
        assert partial_outputs is not None and len(partial_outputs) == 1

def _test_retry_failed_files_normalizes_empty_output_path() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("retry failed output normalization test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLineEdit, QMainWindow, QMessageBox

    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.main.actions.batch import BatchActions

    class FakeProcessor:
        def __init__(self) -> None:
            self.is_running = False
            self.start_calls = []

        def start_async(self, input_path: str, output_path: str, files) -> None:
            self.start_calls.append((input_path, output_path, list(files)))

    class FakeBatchSession:
        def __init__(self) -> None:
            self._processor = None
            self.failed_files = ["failed_a.jpg", "failed_b.jpg"]
            self.create_calls = 0

        @property
        def processor(self):
            return self._processor

        def create_processor(self, **_kwargs):
            self.create_calls += 1
            self._processor = FakeProcessor()
            return self._processor

    host_window = QMainWindow()
    refs = SimpleNamespace(
        input_path_edit=QLineEdit(),
        output_path_edit=QLineEdit(),
        progress_dialog=None,
        status_label=None,
        batch_prev_btn=None,
        batch_next_btn=None,
        batch_save_edits_btn=None,
        batch_failed_btn=None,
        batch_load_btn=None,
        batch_edit_status_label=None,
    )
    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=SimpleNamespace(is_active=False),
    )
    state = SimpleNamespace(
        settings=AppSettings(),
        image_list=[],
        current_image_index=-1,
        batch_contours_edited=set(),
        failed_boundary_files=[],
        manual_extract_running=False,
    )
    signals = SimpleNamespace(
        batch_progress_received=_SignalRecorder(),
        batch_log_received=_SignalRecorder(),
        batch_complete_received=_SignalRecorder(),
    )
    actions = BatchActions(state=state, refs=refs, services=services, signals=signals)
    progress_paths = []
    actions._create_progress_dialog = lambda output_path: progress_paths.append(output_path)

    original_question = QMessageBox.question
    original_warning = QMessageBox.warning
    original_information = QMessageBox.information
    QMessageBox.question = lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes
    QMessageBox.warning = lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok
    QMessageBox.information = lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_retry_failed_") as td:
            input_dir = os.path.join(td, "input")
            os.makedirs(input_dir, exist_ok=True)
            refs.input_path_edit.setText(input_dir)
            refs.output_path_edit.setText("")

            actions.retry_failed_files()

            default_output = os.path.join(input_dir, "output_cropped")
            assert refs.output_path_edit.text() == default_output
            assert os.path.isdir(default_output)
            assert services.batch_session.create_calls == 1
            assert progress_paths == [default_output]
            assert services.batch_session.processor is not None
            assert services.batch_session.processor.start_calls == [
                (
                    input_dir,
                    default_output,
                    ["failed_a.jpg", "failed_b.jpg"],
                )
            ]
    finally:
        QMessageBox.question = original_question
        QMessageBox.warning = original_warning
        QMessageBox.information = original_information
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        if owned_app:
            app.quit()

def _test_batch_actions_recursive_output_guard() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("batch action recursive output guard test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLineEdit, QMainWindow, QMessageBox

    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.main.actions.batch import BatchActions

    class FakeProcessor:
        is_running = False

    class FakeBatchSession:
        def __init__(self) -> None:
            self.processor = FakeProcessor()
            self.failed_files = ["failed.jpg"]
            self.create_calls = 0

        def create_processor(self, **_kwargs):
            self.create_calls += 1
            raise AssertionError("Batch processor creation should have been blocked")

    host_window = QMainWindow()
    refs = SimpleNamespace(
        input_path_edit=QLineEdit(),
        output_path_edit=QLineEdit(),
        progress_dialog=None,
        status_label=None,
        batch_prev_btn=None,
        batch_next_btn=None,
        batch_save_edits_btn=None,
        batch_failed_btn=None,
        batch_load_btn=None,
        batch_edit_status_label=None,
    )
    settings = AppSettings()
    settings.file_management.recursive_search = True
    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=SimpleNamespace(is_active=False),
    )
    state = SimpleNamespace(
        settings=settings,
        image_list=[],
        current_image_index=-1,
        batch_contours_edited=set(),
        failed_boundary_files=[],
        manual_extract_running=False,
    )
    signals = SimpleNamespace(
        batch_progress_received=_SignalRecorder(),
        batch_log_received=_SignalRecorder(),
        batch_complete_received=_SignalRecorder(),
    )
    actions = BatchActions(state=state, refs=refs, services=services, signals=signals)

    warnings = []
    original_question = QMessageBox.question
    original_warning = QMessageBox.warning
    QMessageBox.question = lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_batch_guard_") as td:
            input_dir = os.path.join(td, "input")
            output_dir = os.path.join(input_dir, "output_cropped")
            os.makedirs(output_dir, exist_ok=True)
            refs.input_path_edit.setText(input_dir)
            refs.output_path_edit.setText(output_dir)

            actions.start_processing()
            actions.retry_failed_files()

            assert len(warnings) == 2
            assert services.batch_session.create_calls == 0
            expected_message = t(
                "validation.recursive_output_guard",
                input=input_dir,
                output=output_dir,
            )
            assert all(args[2] == expected_message for args, _kwargs in warnings)
    finally:
        QMessageBox.question = original_question
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        if owned_app:
            app.quit()

def _test_profile_apply_rebuild_validation() -> None:
    import tempfile

    from ..core.batch_profile_manager import BatchProfile, BatchProfileManager
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_profile_apply_") as td:
        manager = BatchProfileManager(profiles_dir=td)
        manager._profiles["selftest-invalid"] = BatchProfile(
            name="selftest-invalid",
            settings={
                "advanced_processing": {"auto_deskew": True},
                "face_detection": {"min_face_size": 1},
                "classification": {"min_confidence": 5.0},
            },
        )

        settings = AppSettings()
        ok = manager.apply_profile("selftest-invalid", settings)
        assert ok is True
        assert settings.advanced.auto_deskew is True
        assert settings.face_detection.min_face_size == 20
        assert abs(settings.classification.min_confidence - 1.0) < 1e-6

def _test_cli_cancel_exit_code_130() -> None:
    import os
    import tempfile

    from .. import cli as cli_mod
    from ..core import batch as batch_mod

    class FakeProgress:
        processed = 0
        success = 0
        partial_success = 0
        failed = 0
        skipped = 0
        is_cancelled = True

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, on_log=None, **_kwargs):
            self._on_log = on_log

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return True

        def request_stop(self):
            return None

        def wait_for_completion(self, timeout=None):
            return True

        @property
        def progress(self):
            return self._progress

    original_batch_processor = batch_mod.BatchProcessor
    original_sleep = cli_mod.time.sleep
    batch_mod.BatchProcessor = FakeProcessor
    cli_mod.time.sleep = lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt())
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_cli_cancel_") as td:
            in_dir = os.path.join(td, "in")
            out_dir = os.path.join(td, "out")
            os.makedirs(in_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)

            parser = cli_mod.create_parser()
            args = parser.parse_args(["-i", in_dir, "-o", out_dir])
            code = cli_mod.process_batch(args)
            assert code == 130
    finally:
        batch_mod.BatchProcessor = original_batch_processor
        cli_mod.time.sleep = original_sleep

def _test_cli_partial_exit_code_rules() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stdout

    from .. import cli as cli_mod
    from ..core import batch as batch_mod

    class FakeProgress:
        processed = 1
        success = 0
        partial_success = 1
        failed = 0
        skipped = 0
        is_cancelled = False

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, on_log=None, **_kwargs):
            self._on_log = on_log

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return False

        @property
        def progress(self):
            return self._progress

    original_batch_processor = batch_mod.BatchProcessor
    batch_mod.BatchProcessor = FakeProcessor
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_cli_partial_") as td:
            in_dir = os.path.join(td, "in")
            out_dir = os.path.join(td, "out")
            os.makedirs(in_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)

            parser = cli_mod.create_parser()
            args = parser.parse_args(["-i", in_dir, "-o", out_dir])
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = cli_mod.process_batch(args)
            assert code == 0
            assert "partial_success=1" in buffer.getvalue()

            strict_args = parser.parse_args(
                ["-i", in_dir, "-o", out_dir, "--strict-partial"]
            )
            assert cli_mod.process_batch(strict_args) == 1
    finally:
        batch_mod.BatchProcessor = original_batch_processor

def _test_cli_recursive_output_guard() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stderr

    from .. import cli as cli_mod

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_guard_") as td:
        in_dir = os.path.join(td, "input")
        out_dir = os.path.join(in_dir, "output_cropped")
        os.makedirs(out_dir, exist_ok=True)

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir, "--recursive"])
        error_buffer = io.StringIO()
        with redirect_stderr(error_buffer):
            code = cli_mod.process_batch(args)
        assert code == 2
        assert "output directory inside the input directory" in error_buffer.getvalue()

def _test_cli_rejects_invalid_settings_segments() -> None:
    import io
    import json
    import os
    import tempfile
    from contextlib import redirect_stderr

    from .. import cli as cli_mod

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_invalid_") as td:
        in_dir = os.path.join(td, "input")
        out_dir = os.path.join(td, "output")
        os.makedirs(in_dir, exist_ok=True)
        config_path = os.path.join(td, "bad.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "file_management": {"naming_prefix": "../bad"},
                    "classification": {
                        "category_folders": {"portrait": "bad/folder"}
                    },
                },
                handle,
            )

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir, "--config", config_path])
        error_buffer = io.StringIO()
        with redirect_stderr(error_buffer):
            code = cli_mod.process_batch(args)
        assert code == 2
        assert "ERROR:" in error_buffer.getvalue()

def _test_processed_signature_includes_routing_and_backup() -> None:
    from ..core.processed_index import build_pipeline_signature
    from ..core.settings_model import AppSettings

    ko_settings = AppSettings()
    ko_settings.classification.enabled = True
    ko_settings.classification.auto_folder = True
    ko_settings.ui.language = "ko"

    en_settings = AppSettings.from_dict(ko_settings.to_dict())
    en_settings.ui.language = "en"

    backup_settings = AppSettings.from_dict(ko_settings.to_dict())
    backup_settings.create_backup = True

    assert build_pipeline_signature(ko_settings) != build_pipeline_signature(en_settings)
    assert build_pipeline_signature(ko_settings) != build_pipeline_signature(backup_settings)

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

__all__ = [
    "_test_batch_session_service_smoke",
    "_test_batch_session_service_reentry_guard",
    "_test_boundary_failed_file_collection_helper",
    "_test_boundary_failed_file_collection_prefers_relative_paths",
    "_test_recursive_scan_excludes_internal_generated_dirs",
    "_test_classify_failed_files_preserves_relative_dirs",
    "_test_cli_settings_merge_priority",
    "_test_batch_thread_local_reuse",
    "_test_batch_post_pipeline_order",
    "_test_skip_processed_with_classification_subfolder",
    "_test_cli_new_crop_options",
    "_test_processed_index_roundtrip_and_source_change",
    "_test_processed_index_backward_compat_and_partial_status",
    "_test_retry_failed_files_normalizes_empty_output_path",
    "_test_batch_actions_recursive_output_guard",
    "_test_profile_apply_rebuild_validation",
    "_test_cli_cancel_exit_code_130",
    "_test_cli_partial_exit_code_rules",
    "_test_cli_recursive_output_guard",
    "_test_cli_rejects_invalid_settings_segments",
    "_test_processed_signature_includes_routing_and_backup",
    "_test_output_reservation_is_thread_safe",
    "_test_processing_logger_partial_summary",
]
