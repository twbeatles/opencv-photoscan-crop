#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Failed-file collection self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

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


def _test_classify_failed_files_rejects_invalid_failed_folder() -> None:
    import os
    import tempfile

    from ..utils.file_helpers import classify_failed_files

    with tempfile.TemporaryDirectory(prefix="photocropper_failed_guard_") as td:
        input_dir = os.path.join(td, "input")
        os.makedirs(input_dir, exist_ok=True)
        source_file = os.path.join(input_dir, "sample.jpg")
        with open(source_file, "wb") as f:
            f.write(b"sample")

        moved_count, errors = classify_failed_files(
            [source_file],
            input_dir,
            failed_folder_name="..\\outside",
            copy_mode=False,
            input_root=input_dir,
        )
        assert moved_count == 0
        assert errors and "Invalid failed folder name" in errors[0]
        assert os.path.exists(source_file)
        assert not os.path.exists(os.path.join(td, "outside"))


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
            for filename in ("failed_a.jpg", "failed_b.jpg"):
                with open(os.path.join(input_dir, filename), "wb") as f:
                    f.write(b"placeholder")
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
                    [
                        os.path.join(input_dir, "failed_a.jpg"),
                        os.path.join(input_dir, "failed_b.jpg"),
                    ],
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
