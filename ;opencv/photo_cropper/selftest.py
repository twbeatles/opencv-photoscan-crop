#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""
Lightweight self-tests for Photo Cropper.

Run:
  python -m photo_cropper.selftest
"""

from __future__ import annotations

import sys


class _SignalRecorder:
    def __init__(self) -> None:
        self.calls = []

    def emit(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def _ensure_qt_app(context: str):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for {context}: {e}")
        return None, False

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True
    return app, owned_app


def _test_crop_editor_import_smoke() -> None:
    try:
        from .ui.widgets.crop_editor_widget import CropEditorWidget
    except Exception as e:
        raise AssertionError(f"Crop editor import failed: {e}")

    assert CropEditorWidget is not None


def _test_preview_worker_import_smoke() -> None:
    try:
        from .ui.main.preview_worker import PreviewWorker
    except Exception as e:
        raise AssertionError(f"Preview worker import failed: {e}")

    assert PreviewWorker is not None


def _test_ui_action_modules_import_smoke() -> None:
    try:
        from .ui.main.batch_actions import BatchActions
        from .ui.main.preview_actions import PreviewActions
        from .ui.main.feature_actions import FeatureActions
        from .ui.main.navigation_actions import NavigationActions
        from .ui.main.dialog_actions import DialogActions
        from .ui.main.io_actions import InputActions
        from .ui.main.settings_actions import SettingsActions
        from .ui.main.watch_actions import WatchActions
    except Exception as e:
        raise AssertionError(f"UI action modules import failed: {e}")

    assert BatchActions is not None
    assert PreviewActions is not None
    assert FeatureActions is not None
    assert NavigationActions is not None
    assert DialogActions is not None
    assert InputActions is not None
    assert SettingsActions is not None
    assert WatchActions is not None


def _test_ui_canonical_package_import_smoke() -> None:
    try:
        from .ui.main.actions import (
            BatchActions,
            DialogActions,
            FeatureActions,
            InputActions,
            LifecycleActions,
            NavigationActions,
            PreviewActions,
            PreviewWorkerHost,
            SettingsActions,
            ToolActions,
            WatchActions,
        )
        from .ui.main.builders import (
            build_central_widget,
            build_fab,
            build_menu,
            build_statusbar,
            build_toolbar,
        )
        from .ui.main.models import WindowRefs, WindowServices, WindowSignals, WindowState
    except Exception as e:
        raise AssertionError(f"UI canonical package import failed: {e}")

    assert BatchActions is not None
    assert DialogActions is not None
    assert FeatureActions is not None
    assert InputActions is not None
    assert LifecycleActions is not None
    assert NavigationActions is not None
    assert PreviewActions is not None
    assert PreviewWorkerHost is not None
    assert SettingsActions is not None
    assert ToolActions is not None
    assert WatchActions is not None
    assert build_central_widget is not None
    assert build_fab is not None
    assert build_menu is not None
    assert build_statusbar is not None
    assert build_toolbar is not None
    assert WindowRefs is not None
    assert WindowServices is not None
    assert WindowSignals is not None
    assert WindowState is not None


def _test_main_window_import_smoke() -> None:
    try:
        from .ui.main import MainWindow
    except Exception as e:
        raise AssertionError(f"MainWindow import failed: {e}")

    assert MainWindow is not None


def _test_manual_extract_service_import_smoke() -> None:
    try:
        from .core.manual_extract import ManualExtractProcessor, ManualExtractOutcome
    except Exception as e:
        raise AssertionError(f"Manual extract service import failed: {e}")

    assert ManualExtractProcessor is not None
    assert ManualExtractOutcome is not None


def _test_image_save_io_module_smoke() -> None:
    try:
        from .core.image.save_io import resolve_save_codec, save_image_unicode
    except Exception as e:
        raise AssertionError(f"Image save IO module import failed: {e}")

    ext, fmt = resolve_save_codec("out", "PNG")
    assert ext == ".png"
    assert fmt == "PNG"
    assert save_image_unicode is not None


def _test_watch_mode_coordinator_import_smoke() -> None:
    try:
        from .core.watch_mode import WatchModeCoordinator, WatchStartResult
    except Exception as e:
        raise AssertionError(f"Watch mode coordinator import failed: {e}")

    assert WatchModeCoordinator is not None
    assert WatchStartResult is not None


def _test_watch_mode_coordinator_invalid_input() -> None:
    from .core.settings_model import AppSettings
    from .core.watch_mode import WatchModeCoordinator

    coordinator = WatchModeCoordinator(settings=AppSettings())
    result = coordinator.start(input_path="", output_path="")
    assert result.success is False
    assert result.error_code == "invalid_input"
    coordinator.stop()
    coordinator.deleteLater()


def _test_watch_mode_coordinator_recursive_output_guard() -> None:
    import os
    import tempfile

    from .core.settings_model import AppSettings
    from .core.watch_mode import WatchModeCoordinator

    settings = AppSettings()
    settings.watch_mode.recursive = True
    coordinator = WatchModeCoordinator(settings=settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_guard_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(input_dir, "output_cropped")
        os.makedirs(output_dir, exist_ok=True)

        result = coordinator.start(
            input_path=input_dir,
            output_path=output_dir,
            watch_settings=settings.watch_mode,
        )

        assert result.success is False
        assert result.error_code == "unsafe_output"
        assert os.path.abspath(result.output_path) == os.path.abspath(output_dir)

    coordinator.stop()
    coordinator.deleteLater()


def _test_watch_mode_processing_disables_failed_file_move() -> None:
    from types import SimpleNamespace

    from .core.batch import ProcessStatus
    from .core.settings_model import AppSettings
    from .core.watch_mode import WatchModeCoordinator

    settings = AppSettings()
    settings.file_management.move_failed_files = True
    coordinator = WatchModeCoordinator(settings=settings)

    class FakeBatchProcessor:
        def __init__(self) -> None:
            self.updated_settings = []
            self.process_calls = []

        def update_settings(self, updated_settings) -> None:
            self.updated_settings.append(updated_settings)

        def process_single(
            self,
            input_path: str,
            output_path: str,
            input_root: str | None = None,
        ):
            snapshot = self.updated_settings[-1]
            self.process_calls.append(
                (
                    input_path,
                    output_path,
                    snapshot.file_management.move_failed_files,
                    input_root,
                )
            )
            return SimpleNamespace(status=ProcessStatus.SUCCESS, message="ok")

    fake_batch = FakeBatchProcessor()
    coordinator._batch_processor = fake_batch
    coordinator._watch_input_root = "watch-root"

    result = coordinator._process_watched_file("input.jpg", "output")
    assert result["success"] is True
    assert result["status"] == "success"
    assert settings.file_management.move_failed_files is True
    assert len(fake_batch.updated_settings) == 1
    assert fake_batch.updated_settings[0] is not settings
    assert fake_batch.updated_settings[0].file_management.move_failed_files is False
    assert fake_batch.process_calls == [("input.jpg", "output", False, "watch-root")]

    coordinator.deleteLater()


def _test_batch_session_service_smoke() -> None:
    from .core.batch import BatchSessionService

    service = BatchSessionService()
    assert service.processor is None
    assert service.failed_files == []
    service.request_stop()
    service.cleanup()


def _test_batch_session_service_reentry_guard() -> None:
    from .core.batch import BatchSessionService
    from .core.settings_model import AppSettings

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


def _test_manual_extract_session_runner_empty() -> None:
    import tempfile
    from threading import Event

    from .core.manual_extract import ManualExtractSessionRunner

    calls = {"progress": 0, "log": 0, "completed": 0, "results": None}

    def on_progress(_progress):
        calls["progress"] += 1

    def on_log(_message: str, _level: str):
        calls["log"] += 1

    def on_complete(_progress, results):
        calls["completed"] += 1
        calls["results"] = results

    runner = ManualExtractSessionRunner()
    with tempfile.TemporaryDirectory(prefix="photocropper_manual_runner_") as td:
        runner.run(
            output_path=td,
            input_root=td,
            files=[],
            contours_norm={},
            settings_snapshot={},
            stop_event=Event(),
            on_progress=on_progress,
            on_log=on_log,
            on_complete=on_complete,
        )

    assert calls["progress"] >= 2
    assert calls["log"] == 0
    assert calls["completed"] == 1
    assert calls["results"] == []


def _test_contour_utils_roundtrip() -> None:
    import numpy as np

    from .core.manual_extract import (
        normalize_contour_points,
        denormalize_contour_points,
        scale_contour_to_preview,
    )
    from .core.image import CropResult

    pts = np.array([[10, 20], [90, 20], [90, 80], [10, 80]], dtype=np.float32)
    normalized = normalize_contour_points(pts, (100, 100, 3))
    assert normalized is not None
    restored = denormalize_contour_points(normalized, (100, 100, 3))
    assert restored is not None
    assert np.allclose(restored, pts, atol=1.0)

    preview = np.zeros((200, 300, 3), dtype=np.uint8)
    crop_result = CropResult(
        success=True,
        contour_points=pts,
        original_size=(100, 100),
    )
    scaled = scale_contour_to_preview(preview, crop_result)
    assert scaled is not None
    assert np.allclose(scaled[0], [30.0, 40.0], atol=1.0)


def _test_preview_widget_contour_redraw_variants() -> None:
    import numpy as np

    app, owned_app = _ensure_qt_app("preview widget redraw test")
    if app is None:
        return

    from .ui.widgets.preview_widget import ImagePreviewWidget

    widget = ImagePreviewWidget()
    try:
        image = np.zeros((90, 140, 3), dtype=np.uint8)
        contour = np.array(
            [[12, 10], [126, 14], [121, 78], [14, 74]],
            dtype=np.float32,
        )

        widget.set_original_image(image, image.copy(), contour)
        assert len(widget._contour_lines) == 4
        assert len(widget._contour_handles) == 4

        widget.set_original_image(image, image.copy(), None)
        widget._manual_seed_points = [[10.0, 12.0], [70.0, 12.0]]
        widget._redraw_contour_overlay()
        assert len(widget._contour_lines) == 1
        assert len(widget._contour_handles) == 2

        widget._manual_seed_points = [[10.0, 12.0], [70.0, 12.0], [70.0, 48.0]]
        widget._redraw_contour_overlay()
        assert len(widget._contour_lines) == 2
        assert len(widget._contour_handles) == 3
    finally:
        widget.deleteLater()
        if owned_app:
            app.quit()


def _test_manual_preview_shared_crop_mode() -> None:
    from types import SimpleNamespace

    import numpy as np

    from .core.manual_extract import crop_manual_contour
    from .core.settings_model import AppSettings
    from .ui.main.actions.preview import PreviewActions

    image = np.zeros((110, 140, 3), dtype=np.uint8)
    image[25:86, 35:96] = (15, 120, 240)
    contour = np.array(
        [[35, 25], [95, 25], [95, 85], [35, 85]],
        dtype=np.float32,
    )

    settings = AppSettings()
    settings.advanced.perspective_correct = False
    state = SimpleNamespace(
        settings=settings,
        last_original=image,
    )
    services = SimpleNamespace(
        image_processor=SimpleNamespace(_apply_post_processing=lambda img: img)
    )

    actions = PreviewActions(
        state=state,
        refs=SimpleNamespace(),
        services=services,
        signals=SimpleNamespace(),
    )

    preview_image = actions._build_manual_preview_image(contour)
    saved_image = crop_manual_contour(
        image,
        contour,
        perspective_correct=False,
        use_gpu=False,
    )

    assert preview_image is not None
    assert saved_image is not None
    assert preview_image.shape == saved_image.shape
    assert np.array_equal(preview_image, saved_image)


def _test_boundary_failed_file_collection_helper() -> None:
    import os
    import tempfile

    from .core.batch import ProcessStatus
    from .core.manual_extract import collect_boundary_failed_files

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

    from .core.batch import ProcessStatus
    from .core.manual_extract import collect_boundary_failed_files

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

    from .utils.file_helpers import build_recursive_excluded_roots, get_image_files

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

    from .utils.file_helpers import classify_failed_files

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

    from . import cli as cli_mod
    from .core.batch_profile_manager import BatchProfileManager
    from .core.settings_model import AppSettings

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


def _test_classification_settings_custom_alias_normalizes_to_advanced() -> None:
    from .core.settings_model import AppSettings, ClassificationSettings

    classification = ClassificationSettings(model="custom")
    assert classification.model == "advanced"

    loaded = AppSettings.from_dict({"classification": {"model": "custom"}})
    assert loaded.classification.model == "advanced"


def _test_recursive_watch_new_subdir_initial_scan() -> None:
    import os
    import shutil
    import tempfile
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for recursive watch test: {e}")
        return

    from .core.folder_watcher import FolderWatcher

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_") as td:
        watch_root = os.path.join(td, "watch")
        incoming_root = os.path.join(td, "incoming")
        os.makedirs(watch_root, exist_ok=True)
        os.makedirs(incoming_root, exist_ok=True)

        bundle = os.path.join(incoming_root, "bundle")
        os.makedirs(bundle, exist_ok=True)
        src_file = os.path.join(bundle, "sample.jpg")
        with open(src_file, "wb") as f:
            f.write(b"fakejpg")

        detected = []
        watcher = FolderWatcher(recursive=True, debounce_ms=80)
        watcher.new_file_detected.connect(lambda path: detected.append(path))
        assert watcher.start(watch_root)

        moved_dir = os.path.join(watch_root, "bundle")
        shutil.move(bundle, moved_dir)

        deadline = time.time() + 3.0
        while time.time() < deadline and not detected:
            app.processEvents()
            time.sleep(0.02)

        watcher.stop()
        expected = os.path.join(moved_dir, "sample.jpg")
        assert any(os.path.abspath(p) == os.path.abspath(expected) for p in detected), (
            f"Expected initial scan detection for {expected}, got: {detected}"
        )

    if owned_app:
        app.quit()


def _test_folder_watcher_file_changed_requeues_only_on_signature_change() -> None:
    import os
    import tempfile

    app, owned_app = _ensure_qt_app("watch fileChanged signature test")
    if app is None:
        return

    from .core.folder_watcher import FolderWatcher

    watcher = FolderWatcher(debounce_ms=10)
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_watch_changed_") as td:
            sample = os.path.join(td, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"seed")

            watcher._track_known_file(sample)
            initial_signature = watcher._file_signatures.get(sample)
            assert initial_signature is not None

            watcher._on_file_changed(sample)
            assert sample not in watcher._pending_files

            with open(sample, "ab") as f:
                f.write(b"-updated")

            watcher._on_file_changed(sample)
            assert sample in watcher._pending_files
            changed_signature = watcher._file_signatures.get(sample)
            assert changed_signature is not None
            assert changed_signature != initial_signature

            watcher._pending_files.clear()
            watcher._on_file_changed(sample)
            assert sample not in watcher._pending_files
    finally:
        watcher.deleteLater()
        if owned_app:
            app.quit()


def _test_watch_max_wait_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch max wait test: {e}")
        return

    from .core.folder_watcher import AutoProcessor
    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    panel = SettingsPanel(AppSettings())
    panel.watch_max_wait_spin.setValue(47.5)
    built = panel._build_settings()
    assert abs(float(built.watch_mode.max_wait_seconds) - 47.5) < 1e-6

    panel.settings = built
    rebuilt = panel._build_settings()
    assert abs(float(rebuilt.watch_mode.max_wait_seconds) - 47.5) < 1e-6

    auto = AutoProcessor(max_wait_seconds=rebuilt.watch_mode.max_wait_seconds)
    assert abs(float(auto._max_wait_s) - 47.5) < 1e-6
    assert hasattr(auto._queue, "popleft"), "Watch queue must support O(1) front pop"

    panel.deleteLater()
    auto.stop()
    auto.deleteLater()
    if owned_app:
        app.quit()


def _test_watch_callback_runs_on_background_worker() -> None:
    import os
    import tempfile
    import threading
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch worker thread test: {e}")
        return

    from .core.folder_watcher import AutoProcessor

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    auto = None
    try:
        main_thread_id = threading.get_ident()
        state = {"done": False, "callback_thread": None}

        with tempfile.TemporaryDirectory(prefix="photocropper_watch_worker_") as td:
            watch_root = os.path.join(td, "watch")
            output_root = os.path.join(td, "out")
            os.makedirs(watch_root, exist_ok=True)
            os.makedirs(output_root, exist_ok=True)

            sample = os.path.join(watch_root, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"watch-worker")

            def callback(input_path: str, output_path: str):
                assert os.path.exists(input_path)
                assert os.path.isdir(output_path)
                state["callback_thread"] = threading.get_ident()
                return {"success": True, "status": "success", "message": "ok"}

            auto = AutoProcessor(
                watch_path=watch_root,
                output_path=output_root,
                debounce_ms=10,
                process_callback=callback,
            )
            auto._stable_window_s = 0.0
            auto._retry_interval_ms = 10
            auto.processing_completed_detailed.connect(
                lambda *_args: state.__setitem__("done", True)
            )

            assert auto.start()
            auto._on_new_file(sample)

            deadline = time.time() + 3.0
            while time.time() < deadline and not state["done"]:
                app.processEvents()
                time.sleep(0.01)

            assert state["done"], "Expected watch callback to finish"
            assert state["callback_thread"] is not None
            assert state["callback_thread"] != main_thread_id
    finally:
        if auto is not None:
            auto.stop()
            auto.deleteLater()
        if owned_app:
            app.quit()


def _test_watch_readiness_is_owned_by_auto_processor() -> None:
    import os
    import tempfile
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch readiness ownership test: {e}")
        return

    from .core.folder_watcher import AutoProcessor

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    auto = None
    try:
        state = {"done": False, "callback_calls": 0, "readiness_checks": 0}

        with tempfile.TemporaryDirectory(prefix="photocropper_watch_ready_") as td:
            watch_root = os.path.join(td, "watch")
            output_root = os.path.join(td, "out")
            os.makedirs(watch_root, exist_ok=True)
            os.makedirs(output_root, exist_ok=True)

            sample = os.path.join(watch_root, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"watch-ready")

            def callback(_input_path: str, _output_path: str):
                state["callback_calls"] += 1
                return {"success": True, "status": "success", "message": "ok"}

            auto = AutoProcessor(
                watch_path=watch_root,
                output_path=output_root,
                debounce_ms=10,
                process_callback=callback,
            )
            auto._stable_window_s = 0.0
            auto._retry_interval_ms = 10

            def fake_check(filepath: str):
                assert os.path.abspath(filepath) == os.path.abspath(sample)
                state["readiness_checks"] += 1
                if state["readiness_checks"] < 3:
                    return False, False, "not yet stable"
                return True, False, "ready"

            auto._check_file_ready = fake_check
            auto.processing_completed_detailed.connect(
                lambda *_args: state.__setitem__("done", True)
            )

            assert auto.start()
            auto._on_new_file(sample)

            deadline = time.time() + 3.0
            while time.time() < deadline and not state["done"]:
                app.processEvents()
                time.sleep(0.01)

            assert state["done"], "Expected watch processing to complete"
            assert state["callback_calls"] == 1
            assert state["readiness_checks"] >= 3
    finally:
        if auto is not None:
            auto.stop()
            auto.deleteLater()
        if owned_app:
            app.quit()


def _test_settings_forward_compat() -> None:
    from .core.settings_model import AppSettings

    data = {
        "algorithm": {"canny_min": 12, "canny_max": 200, "new_field_future": 123},
        "watermark": {"enabled": True, "text": "짤 2026", "unknown": "x"},
        "unknown_root": {"a": 1},
    }
    s = AppSettings.from_dict(data)
    assert s.algorithm.canny_min == 12
    assert s.algorithm.canny_max == 200
    assert s.watermark.enabled is True
    assert s.watermark.text == "짤 2026"


def _test_unicode_text_watermark() -> None:
    import numpy as np

    from .core.watermark_processor import WatermarkProcessor, TextWatermarkSettings

    img = np.full((240, 360, 3), 255, dtype=np.uint8)  # white background
    wm = WatermarkProcessor()
    out = wm.apply_text_watermark(
        img,
        TextWatermarkSettings(
            text="짤 2026",
            font_scale=1.0,
            color=(0, 0, 255),  # red in BGR
            opacity=0.8,
        ),
    )
    assert out is not None
    assert out.shape == img.shape

    # Best-effort: watermark should usually change pixels, but avoid hard failure
    # if font fallback can't render the glyphs on this machine.
    if (out == img).all():
        print("WARN: Unicode watermark produced no pixel changes (font fallback?)")


def _test_preview_single_pass() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.image import ImageProcessor
    from .core.settings_model import AppSettings

    settings = AppSettings()
    processor = ImageProcessor(
        settings.algorithm,
        settings.processing,
        settings.advanced,
        settings.performance,
        settings.debug,
    )

    calls = {"count": 0}
    original_impl = processor._process_loaded_image

    def wrapped(*args, **kwargs):
        calls["count"] += 1
        return original_impl(*args, **kwargs)

    processor._process_loaded_image = wrapped

    img = np.full((720, 960, 3), 240, dtype=np.uint8)
    cv2.rectangle(img, (120, 120), (840, 620), (30, 30, 30), 6)
    cv2.rectangle(img, (126, 126), (834, 614), (200, 200, 200), -1)

    with tempfile.TemporaryDirectory(prefix="photocropper_preview_") as td:
        path = os.path.join(td, "sample.png")
        ok, buf = cv2.imencode(".png", img)
        assert ok
        buf.tofile(path)

        preview = processor.process_preview(path, max_size=800)
        assert preview.original_preview is not None
        assert preview.overlay_preview is not None
        assert preview.crop_result is not None
        assert calls["count"] == 1, f"Expected single pass, got {calls['count']}"

        # Preview fast path: force low detection cap, while preserving source metadata.
        preview_fast = processor.process_preview(
            path,
            max_size=256,
            fast_preview=True,
            preview_detection_max_mp=1.0,
        )
        assert preview_fast.crop_result.original_size == (960, 720)
        if preview_fast.crop_result.image is not None:
            ph, pw = preview_fast.crop_result.image.shape[:2]
            assert max(pw, ph) <= 256


def _test_batch_thread_local_reuse() -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from .core.batch import BatchProcessor
    from .core.settings_model import AppSettings

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


def _test_settings_panel_performance_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for settings panel test: {e}")
        return

    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    panel = SettingsPanel(AppSettings())
    panel.max_threads_spin.setValue(7)
    panel.low_mem_check.setChecked(True)

    s1 = panel._build_settings()
    assert s1.performance.thread_count == 7
    assert s1.performance.enable_multithreading is True
    assert s1.performance.max_image_size_mb == 50
    assert s1.performance.downscale_large_images is True
    assert abs(s1.performance.downscale_threshold_mp - 24.0) < 1e-6

    panel.settings = s1
    s2 = panel._build_settings()
    assert s2.performance.thread_count == 7
    assert s2.performance.max_image_size_mb == 50
    assert abs(s2.performance.downscale_threshold_mp - 24.0) < 1e-6

    panel.max_threads_spin.setValue(2)
    panel.low_mem_check.setChecked(False)
    s3 = panel._build_settings()
    assert s3.performance.thread_count == 2
    assert s3.performance.max_image_size_mb == 100
    assert abs(s3.performance.downscale_threshold_mp - 50.0) < 1e-6

    panel.deleteLater()
    if owned_app:
        app.quit()


def _test_crop_accuracy_synthetic() -> None:
    import os
    import random
    import tempfile

    import cv2
    import numpy as np

    from .core.image import ImageProcessor
    from .core.settings_model import AlgorithmSettings, ProcessingSettings, DebugSettings

    random.seed(0)
    np.random.seed(0)

    def save_png(path: str, img: np.ndarray) -> None:
        ok, buf = cv2.imencode(".png", img)
        assert ok
        buf.tofile(path)

    def quad_iou(q1: np.ndarray, q2: np.ndarray, shape) -> float:
        h, w = shape
        m1 = np.zeros((h, w), dtype=np.uint8)
        m2 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(m1, [q1.astype(np.int32)], 255)
        cv2.fillPoly(m2, [q2.astype(np.int32)], 255)
        inter = np.logical_and(m1 > 0, m2 > 0).sum()
        union = np.logical_or(m1 > 0, m2 > 0).sum()
        return float(inter) / float(union) if union else 0.0

    algo = AlgorithmSettings(
        detection_mode="accurate",
        canny_min=40,
        canny_max=140,
        use_clahe=True,
        multi_scale_edge=True,
        use_corner_detection=False,
        min_area_ratio=0.05,
        max_area_ratio=0.98,
        contour_scoring="enhanced",
    )
    proc = ProcessingSettings(auto_contrast=False)
    dbg = DebugSettings(enabled=False)
    ip = ImageProcessor(algo, proc, debug_settings=dbg)

    n = 20
    successes = 0
    ious = []

    with tempfile.TemporaryDirectory(prefix="photocropper_selftest_") as td:
        for i in range(n):
            h, w = 720, 960
            bg_white = (i % 2) == 0
            bg = 245 if bg_white else 20
            img = np.full((h, w, 3), bg, dtype=np.uint8)

            # Base rectangle near center
            rect_w = random.randint(int(w * 0.45), int(w * 0.75))
            rect_h = random.randint(int(h * 0.45), int(h * 0.75))
            cx = w // 2 + random.randint(-40, 40)
            cy = h // 2 + random.randint(-30, 30)
            x0 = cx - rect_w // 2
            y0 = cy - rect_h // 2
            x1 = cx + rect_w // 2
            y1 = cy + rect_h // 2
            quad = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)

            # Perspective jitter
            jitter = 50
            quad += np.array(
                [
                    [random.randint(-jitter, jitter), random.randint(-jitter, jitter)],
                    [random.randint(-jitter, jitter), random.randint(-jitter, jitter)],
                    [random.randint(-jitter, jitter), random.randint(-jitter, jitter)],
                    [random.randint(-jitter, jitter), random.randint(-jitter, jitter)],
                ],
                dtype=np.float32,
            )
            quad[:, 0] = np.clip(quad[:, 0], 10, w - 10)
            quad[:, 1] = np.clip(quad[:, 1], 10, h - 10)

            # Fill "photo" region with texture
            fill = 180 if bg_white else 220
            cv2.fillPoly(img, [quad.astype(np.int32)], (fill, fill, fill))
            noise = (np.random.randn(h, w, 1) * 6).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            # Draw a strong border (helps edges)
            border_color = (50, 50, 50) if bg_white else (240, 240, 240)
            cv2.polylines(img, [quad.astype(np.int32)], True, border_color, 6)

            # Break one edge occasionally
            if i % 5 == 0:
                p1 = quad[0].astype(int)
                p2 = quad[1].astype(int)
                mid = ((p1 + p2) // 2).astype(int)
                cv2.line(img, tuple(p1), tuple(mid), (bg, bg, bg), 10)

            # Save and run processor
            path = os.path.join(td, f"sample_{i:02d}.png")
            save_png(path, img)

            res = ip.process_image(path)
            if res.success and res.contour_points is not None:
                successes += 1
                ious.append(quad_iou(quad, res.contour_points.astype(np.float32), (h, w)))
            else:
                ious.append(0.0)

    success_rate = successes / n
    mean_iou = sum(ious) / len(ious)
    assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
    assert mean_iou >= 0.75, f"Mean IoU too low: {mean_iou:.3f}"


def _test_no_photo_false_positive_regression() -> None:
    import os
    import random
    import tempfile

    import cv2
    import numpy as np

    from .core.image import ImageProcessor
    from .core.settings_model import AlgorithmSettings, ProcessingSettings, DebugSettings

    random.seed(1)
    np.random.seed(1)

    algo = AlgorithmSettings(
        detection_mode="accurate",
        canny_min=40,
        canny_max=140,
        use_clahe=True,
        multi_scale_edge=True,
        contour_scoring="enhanced",
    )
    proc = ProcessingSettings(auto_contrast=False)
    dbg = DebugSettings(enabled=False)
    ip = ImageProcessor(algo, proc, debug_settings=dbg)

    samples = 25
    false_positive = 0

    with tempfile.TemporaryDirectory(prefix="photocropper_fp_") as td:
        for i in range(samples):
            h, w = 720, 960
            base = np.random.randint(80, 175)
            img = np.full((h, w, 3), base, dtype=np.uint8)

            # Textured but non-rectangular synthetic background.
            noise = np.random.normal(0, 18, (h, w, 1)).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            for _ in range(40):
                x1 = random.randint(0, w - 1)
                y1 = random.randint(0, h - 1)
                x2 = random.randint(0, w - 1)
                y2 = random.randint(0, h - 1)
                color = int(random.randint(70, 190))
                cv2.line(img, (x1, y1), (x2, y2), (color, color, color), 1)

            for _ in range(20):
                cx = random.randint(0, w - 1)
                cy = random.randint(0, h - 1)
                r = random.randint(8, 40)
                color = int(random.randint(70, 200))
                cv2.circle(img, (cx, cy), r, (color, color, color), 1)

            path = os.path.join(td, f"noise_{i:02d}.png")
            ok, buf = cv2.imencode(".png", img)
            assert ok
            buf.tofile(path)

            res = ip.process_image(path)
            if res.success:
                false_positive += 1

    fp_rate = false_positive / samples
    assert fp_rate <= 0.12, f"False positive rate too high: {fp_rate:.2%}"


def _test_multi_photo_close_gap_split() -> None:
    import cv2
    import numpy as np

    from .core.multi_photo_detector import MultiPhotoDetector

    h, w = 700, 1100
    img = np.full((h, w, 3), 25, dtype=np.uint8)

    # Two nearby photos with small gap.
    cv2.rectangle(img, (120, 120), (500, 580), (230, 230, 230), -1)
    cv2.rectangle(img, (510, 120), (890, 580), (210, 210, 210), -1)
    cv2.rectangle(img, (120, 120), (500, 580), (15, 15, 15), 6)
    cv2.rectangle(img, (510, 120), (890, 580), (15, 15, 15), 6)

    detector = MultiPhotoDetector(
        min_area_ratio=0.05,
        max_area_ratio=0.7,
        min_photos=2,
        max_photos=5,
        merge_distance=50,
    )
    result = detector.detect(img)
    assert result.success, result.message
    assert result.total_found >= 2, f"Expected >=2 photos, got {result.total_found}"


def _test_grayscale_image_watermark_regression() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.watermark_processor import WatermarkProcessor, ImageWatermarkSettings

    img = np.full((180, 260), 170, dtype=np.uint8)  # 2D grayscale
    wm_rgba = np.zeros((40, 40, 4), dtype=np.uint8)
    wm_rgba[:, :, 2] = 255  # red-ish in BGR(A)
    wm_rgba[:, :, 3] = 180

    with tempfile.TemporaryDirectory(prefix="photocropper_wm_") as td:
        wm_path = os.path.join(td, "wm.png")
        ok, buf = cv2.imencode(".png", wm_rgba)
        assert ok
        buf.tofile(wm_path)

        processor = WatermarkProcessor()
        out = processor.apply_image_watermark(
            img,
            ImageWatermarkSettings(
                image_path=wm_path,
                scale=0.3,
                opacity=0.7,
            ),
        )

    assert out is not None
    assert out.shape == img.shape
    assert out.ndim == 2


def _test_max_image_size_limit_applied() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.batch import BatchProcessor, ProcessStatus
    from .core.settings_model import AppSettings

    settings = AppSettings()
    settings.performance.max_image_size_mb = 1

    processor = BatchProcessor(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_size_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # BMP is uncompressed and reliably larger than limit.
        img = np.random.randint(0, 256, (1300, 1300, 3), dtype=np.uint8)
        src = os.path.join(in_dir, "big.bmp")
        ok, buf = cv2.imencode(".bmp", img)
        assert ok
        buf.tofile(src)
        assert os.path.getsize(src) > 1 * 1024 * 1024

        result = processor.process_single(src, out_dir)
        assert result.status == ProcessStatus.SKIPPED, result.message
        assert "크기" in result.message or "제한" in result.message


def _test_face_dnn_fallback_when_download_fails() -> None:
    import numpy as np

    from .core.face import detector as fd_mod

    original = fd_mod.FaceDetector._ensure_dnn_models

    def _fail_models(cls):  # type: ignore[override]
        raise RuntimeError("forced model download failure")

    fd_mod.FaceDetector._ensure_dnn_models = classmethod(_fail_models)
    try:
        detector = fd_mod.FaceDetector(use_dnn=True, min_face_size=30)
        assert detector.use_dnn is True
        assert detector._dnn_net is None  # Fallback path expected

        img = np.full((240, 240, 3), 127, dtype=np.uint8)
        result = detector.detect(img, detect_eyes=False, suggest_crop=False)
        assert result is not None
        assert isinstance(result.faces, list)
    finally:
        fd_mod.FaceDetector._ensure_dnn_models = original


def _test_settings_panel_ai_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for AI roundtrip test: {e}")
        return

    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    s = AppSettings()
    s.classification.enabled = True
    s.classification.model = "advanced"
    s.face_detection.enabled = True
    s.face_detection.use_dnn = True
    s.face_detection.min_face_size = 42
    s.smart_enhancement.enabled = True
    s.smart_enhancement.adjust_exposure = False
    s.smart_enhancement.adjust_color_balance = True
    s.smart_enhancement.strength = 73

    panel = SettingsPanel(s)
    panel._load_settings(s)
    out = panel._build_settings()

    assert out.classification.model == "advanced"
    assert out.face_detection.use_dnn is True
    assert out.face_detection.min_face_size == 42
    assert out.smart_enhancement.adjust_exposure is False
    assert out.smart_enhancement.adjust_color_balance is True
    assert out.smart_enhancement.strength == 73

    panel.deleteLater()
    if owned_app:
        app.quit()


def _test_batch_post_pipeline_order() -> None:
    import numpy as np

    from .core.batch import BatchProcessor
    from .core.settings_model import AppSettings

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

    from .core.batch import BatchProcessor, ProcessStatus
    from .core.image_classifier import ClassificationResult, ImageCategory
    from .core.image import CropResult, DetectionStage
    from .core.settings_model import AppSettings

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


def _test_perspective_toggle_warp_vs_axis_crop() -> None:
    import numpy as np

    from .core.image import ImageProcessor
    from .core.settings_model import (
        AlgorithmSettings,
        ProcessingSettings,
        AdvancedProcessingSettings,
    )

    image = np.full((220, 260, 3), 240, dtype=np.uint8)
    quad = np.array(
        [[30, 35], [220, 20], [210, 180], [50, 190]],
        dtype=np.float32,
    )

    def fake_find_best_contour(
        _edge,
        _area,
        min_area_ratio=None,
        max_area_ratio=None,
        score_edge_map=None,
        **_kwargs,
    ):
        del min_area_ratio, max_area_ratio, score_edge_map, _kwargs
        return quad.copy(), 0.99, [{"quad": quad.copy(), "score": 0.99}]

    algo = AlgorithmSettings(
        detection_mode="fast",
        canny_min=30,
        canny_max=120,
        use_clahe=False,
        multi_scale_edge=False,
    )
    proc = ProcessingSettings(auto_contrast=False)

    ip_on = ImageProcessor(algo, proc, AdvancedProcessingSettings(perspective_correct=True))
    ip_off = ImageProcessor(
        algo, proc, AdvancedProcessingSettings(perspective_correct=False)
    )
    ip_on.find_best_contour = fake_find_best_contour
    ip_off.find_best_contour = fake_find_best_contour

    res_on = ip_on._process_loaded_image(image, "synthetic_on")
    res_off = ip_off._process_loaded_image(image, "synthetic_off")

    assert res_on.success and res_on.image is not None, res_on.message
    assert res_off.success and res_off.image is not None, res_off.message
    assert res_on.cropped_size != res_off.cropped_size, (
        f"Expected different sizes for perspective on/off, got {res_on.cropped_size}"
    )

    bbox_w = int(np.ceil(np.max(quad[:, 0])) - np.floor(np.min(quad[:, 0])))
    bbox_h = int(np.ceil(np.max(quad[:, 1])) - np.floor(np.min(quad[:, 1])))
    assert res_off.cropped_size == (bbox_w, bbox_h), res_off.cropped_size


def _test_save_image_fallback_and_metadata_best_effort() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.image import ImageProcessor

    image = np.full((120, 160, 3), 190, dtype=np.uint8)

    with tempfile.TemporaryDirectory(prefix="photocropper_save_") as td:
        no_ext_path = os.path.join(td, "no_extension")
        ok, msg, _ = ImageProcessor.save_image(image, no_ext_path, output_format="PNG")
        assert ok, msg
        assert os.path.exists(no_ext_path)
        assert os.path.getsize(no_ext_path) > 0

        invalid_ext_path = os.path.join(td, "bad.ext")
        ok, msg, _ = ImageProcessor.save_image(
            image, invalid_ext_path, output_format="WEBP"
        )
        assert ok, msg
        assert os.path.exists(invalid_ext_path)
        assert os.path.getsize(invalid_ext_path) > 0

        # Metadata copy failure must not fail the save.
        missing_source_out = os.path.join(td, "missing_source.jpg")
        ok, msg, _ = ImageProcessor.save_image(
            image,
            missing_source_out,
            output_format="JPG",
            source_path=os.path.join(td, "missing.jpg"),
            preserve_metadata=True,
        )
        assert ok, msg

        try:
            from PIL import Image
        except Exception:
            return

        source_path = os.path.join(td, "source_with_exif.jpg")
        output_path = os.path.join(td, "copied_meta.jpg")
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        src_img = Image.fromarray(rgb)
        exif = Image.Exif()
        exif[0x010F] = "PhotoCropperSelfTest"  # Make
        exif[0x0112] = 6  # Orientation
        src_img.save(source_path, format="JPEG", exif=exif.tobytes())

        ok, msg, _ = ImageProcessor.save_image(
            image,
            output_path,
            output_format="JPG",
            source_path=source_path,
            preserve_metadata=True,
        )
        assert ok, msg
        with Image.open(output_path) as out_img:
            out_exif = out_img.getexif()
            assert out_exif is not None and len(out_exif) > 0
            assert out_exif.get(0x010F) == "PhotoCropperSelfTest"
            assert out_exif.get(0x0112) == 1


def _test_resize_fill_no_upscale_boundary() -> None:
    import numpy as np

    from .core.resize_processor import ResizeProcessor, ResizeSettings, ResizeMode

    image = np.full((80, 100, 3), 120, dtype=np.uint8)
    processor = ResizeProcessor()
    settings = ResizeSettings(
        enabled=True,
        mode=ResizeMode.FILL,
        width=300,
        height=240,
        upscale_allowed=False,
    )
    result = processor.resize(image, settings)
    assert result.success, result.message
    assert result.image is not None
    h, w = result.image.shape[:2]
    assert w > 0 and h > 0
    assert w <= 100 and h <= 80
    assert result.new_size == (w, h)


def _test_multi_photo_merge_distance_and_separate_folders() -> None:
    import os
    import tempfile

    import numpy as np

    from .core.batch import BatchProcessor
    from .core.multi_photo_detector import MultiPhotoDetector, DetectedPhoto
    from .core.settings_model import AppSettings

    def make_box(x: int, y: int, w: int, h: int) -> np.ndarray:
        return np.array(
            [[[x, y]], [[x + w, y]], [[x + w, y + h]], [[x, y + h]]],
            dtype=np.int32,
        )

    photo_a = DetectedPhoto(
        bounding_box=(100, 120, 320, 220),
        contour=make_box(100, 120, 320, 220),
        confidence=0.8,
        area=320 * 220,
        aspect_ratio=320 / 220,
    )
    photo_b = DetectedPhoto(
        bounding_box=(125, 130, 315, 215),
        contour=make_box(125, 130, 315, 215),
        confidence=0.79,
        area=315 * 215,
        aspect_ratio=315 / 215,
    )

    detector_small = MultiPhotoDetector(merge_distance=5)
    detector_large = MultiPhotoDetector(merge_distance=80)
    merged_small = detector_small._merge_overlapping([photo_a, photo_b])
    merged_large = detector_large._merge_overlapping([photo_a, photo_b])
    assert len(merged_small) >= len(merged_large)
    assert len(merged_large) == 1

    settings = AppSettings()
    settings.multi_photo.enabled = True
    settings.multi_photo.separate_output_folders = True
    batch = BatchProcessor(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_mp_folder_") as td:
        src = os.path.join(td, "scan_a.jpg")
        out_root = os.path.join(td, "out")
        os.makedirs(out_root, exist_ok=True)

        output_path = batch.build_output_path(src, out_root, "_photo01")
        expected_dir = os.path.join(out_root, "scan_a_photos")
        assert os.path.dirname(output_path) == expected_dir

        with open(output_path, "wb") as f:
            f.write(b"dummy")

        found = batch.find_existing_output(
            "scan_a",
            ".jpg",
            out_root,
            multi_photo=True,
            input_path=src,
        )
        assert found is not None
        assert os.path.abspath(found) == os.path.abspath(output_path)


def _test_recursive_output_paths_preserve_relative_dirs() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    import numpy as np

    from .core.batch import BatchProcessor, ProcessStatus
    from .core.image import CropResult, DetectionStage
    from .core.settings_model import AppSettings

    settings = AppSettings()
    batch = BatchProcessor(settings)

    class FakeProcessor:
        @staticmethod
        def get_image_info(_path):
            return (320, 240, 3)

        @staticmethod
        def process_image(_path, **_kwargs):
            img = np.full((60, 90, 3), 180, dtype=np.uint8)
            return CropResult(
                success=True,
                image=img,
                message="ok",
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
            del image
            del output_format, jpg_quality, png_compression, webp_quality
            del source_path, preserve_metadata
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"saved")
            return True, "ok", 1.0

    batch._get_worker_processor = lambda: FakeProcessor()
    batch._run_post_pipeline = lambda image, output_dir: (image, output_dir)

    with tempfile.TemporaryDirectory(prefix="photocropper_recursive_out_") as td:
        input_root = os.path.join(td, "input")
        output_root = os.path.join(td, "output")
        nested_dir = os.path.join(input_root, "album", "set1")
        os.makedirs(nested_dir, exist_ok=True)
        os.makedirs(output_root, exist_ok=True)

        src = os.path.join(nested_dir, "sample.jpg")
        with open(src, "wb") as f:
            f.write(b"src")

        result = batch.process_single(src, output_root, input_root=input_root)
        expected = os.path.join(output_root, "album", "set1", "sample_cropped.jpg")
        assert result.status == ProcessStatus.SUCCESS, result.message
        assert os.path.abspath(result.output_path) == os.path.abspath(expected)
        assert os.path.exists(expected)


def _test_multi_photo_uses_shared_loader() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    import numpy as np

    from .core.batch import BatchProcessor, ProcessStatus
    from .core.settings_model import AppSettings

    settings = AppSettings()
    settings.multi_photo.enabled = True
    batch = BatchProcessor(settings)
    calls = {"load_paths": []}

    class FakeProcessor:
        def load_image(self, path):
            calls["load_paths"].append(path)
            return np.full((24, 36, 3), 180, dtype=np.uint8)

        def process_image(self, *_args, **_kwargs):
            raise AssertionError("Fallback single-photo path should not be used")

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
            del image
            del output_format, jpg_quality, png_compression, webp_quality
            del source_path, preserve_metadata
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"multi-photo-shared-loader")
            return True, "ok", 1.0

    class FakeDetector:
        def detect(self, image):
            assert image is not None
            return SimpleNamespace(success=True, total_found=1, photos=[object()])

        def crop_photos(self, image, photos, padding=10):
            del padding
            return [(image.copy(), photos[0])]

    batch._get_worker_processor = lambda: FakeProcessor()
    batch._get_multi_photo_detector = lambda: FakeDetector()

    with tempfile.TemporaryDirectory(prefix="photocropper_mp_loader_") as td:
        src = os.path.join(td, "scan.jpg")
        out_dir = os.path.join(td, "out")
        os.makedirs(out_dir, exist_ok=True)
        with open(src, "wb") as f:
            f.write(b"scan")

        result = batch.process_single(src, out_dir)
        assert result.status == ProcessStatus.SUCCESS, result.message
        assert calls["load_paths"] == [src]


def _test_multi_photo_status_variants_and_partial_index_behavior() -> None:
    import os
    import tempfile
    from types import SimpleNamespace
    from typing import Optional

    import numpy as np

    from .core.batch import BatchProcessor, ProcessStatus
    from .core.settings_model import AppSettings

    def run_case(save_plan, *, stop_on_check: Optional[int] = None, repeat: bool = False):
        settings = AppSettings()
        settings.multi_photo.enabled = True
        settings.filter.skip_processed = True
        batch = BatchProcessor(settings)
        state = {"save_calls": 0, "stop_checks": 0}
        logs = []

        class FakeProcessor:
            def load_image(self, _path):
                return np.full((20, 20, 3), 160, dtype=np.uint8)

            def process_image(self, *_args, **_kwargs):
                raise AssertionError("Fallback single-photo path should not be used")

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
                del image
                del output_format, jpg_quality, png_compression, webp_quality
                del source_path, preserve_metadata
                plan_index = state["save_calls"]
                state["save_calls"] += 1
                should_succeed = (
                    save_plan[plan_index] if plan_index < len(save_plan) else False
                )
                if not should_succeed:
                    return False, "save failed", 0.0
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(f"saved-{plan_index}".encode("ascii"))
                return True, "ok", 1.0

        class FakeDetector:
            def detect(self, image):
                assert image is not None
                return SimpleNamespace(success=True, total_found=2, photos=[object(), object()])

            def crop_photos(self, image, photos, padding=10):
                del padding
                return [(image.copy(), photos[0]), (image.copy(), photos[1])]

        batch._get_worker_processor = lambda: FakeProcessor()
        batch._get_multi_photo_detector = lambda: FakeDetector()
        batch.set_callbacks(on_log=lambda message, level: logs.append((message, level)))

        if stop_on_check is not None:
            def fake_stop_requested():
                state["stop_checks"] += 1
                return state["stop_checks"] >= stop_on_check

            batch._is_stop_requested = fake_stop_requested

        with tempfile.TemporaryDirectory(prefix="photocropper_mp_status_") as td:
            src = os.path.join(td, "scan.jpg")
            out_dir = os.path.join(td, "out")
            os.makedirs(out_dir, exist_ok=True)
            with open(src, "wb") as f:
                f.write(b"scan")

            result = batch.process_single(src, out_dir)
            matched, usable, record_status = batch.lookup_processed_outputs_from_index(
                src, out_dir
            )
            repeat_result = None
            if repeat:
                repeat_result = batch.process_single(src, out_dir)
            return result, matched, usable, record_status, repeat_result, state, logs

    (
        success_result,
        success_outputs,
        success_usable,
        success_status,
        _success_repeat,
        _success_state,
        _success_logs,
    ) = run_case([True, True])
    assert success_result.status == ProcessStatus.SUCCESS, success_result.message
    assert success_usable is True
    assert success_status == "success"
    assert success_outputs is not None and len(success_outputs) == 2

    (
        partial_result,
        partial_outputs,
        partial_usable,
        partial_status,
        partial_retry_result,
        partial_state,
        partial_logs,
    ) = run_case([True, False, True, True], repeat=True)
    assert partial_result.status == ProcessStatus.PARTIAL_SUCCESS, partial_result.message
    assert partial_usable is True
    assert partial_status == "partial"
    assert partial_outputs is not None and len(partial_outputs) == 1
    assert partial_retry_result is not None
    assert partial_retry_result.status != ProcessStatus.SKIPPED
    assert partial_state["save_calls"] >= 4
    assert any("부분 저장 이력" in message for message, _level in partial_logs)

    (
        failed_result,
        failed_outputs,
        _failed_usable,
        failed_status,
        _failed_repeat,
        _failed_state,
        _failed_logs,
    ) = run_case([False, False])
    assert failed_result.status == ProcessStatus.FAILED, failed_result.message
    assert failed_status == ""
    assert failed_outputs is None

    (
        cancelled_result,
        cancelled_outputs,
        _cancelled_usable,
        cancelled_status,
        _cancelled_repeat,
        _cancelled_state,
        _cancelled_logs,
    ) = run_case(
        [True, True],
        stop_on_check=2,
    )
    assert cancelled_result.status == ProcessStatus.CANCELLED, cancelled_result.message
    assert cancelled_status == ""
    assert cancelled_outputs is None


def _test_cli_new_crop_options() -> None:
    from . import cli as cli_mod

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

    from .core.batch import BatchProcessor
    from .core.settings_model import AppSettings

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

    from .core.processed_index import (
        INDEX_DIRNAME,
        INDEX_FILENAME,
        RECORD_STATUS_PARTIAL,
        ProcessedIndexStore,
        build_pipeline_signature,
    )
    from .core.settings_model import AppSettings

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


def _test_watch_actions_block_while_batch_or_manual_running() -> None:
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("watch action guard test")
    if app is None:
        return

    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QLabel, QLineEdit, QMainWindow, QMessageBox

    from .core.settings_model import AppSettings
    from .ui.main.actions.watch import WatchActions

    class FakeProcessor:
        def __init__(self) -> None:
            self.is_running = False

    class FakeBatchSession:
        def __init__(self) -> None:
            self.processor = FakeProcessor()

    class FakeWatchCoordinator:
        def __init__(self) -> None:
            self.is_active = False
            self.start_calls = []

        def start(self, **kwargs):
            self.start_calls.append(kwargs)
            raise AssertionError("Watch coordinator start should have been blocked")

    host_window = QMainWindow()
    refs = SimpleNamespace(
        input_path_edit=QLineEdit(),
        output_path_edit=QLineEdit(),
        watch_mode_action=QAction(host_window),
        status_label=QLabel(),
    )
    refs.watch_mode_action.setCheckable(True)
    refs.watch_mode_action.setChecked(True)

    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=FakeWatchCoordinator(),
        scheduler=SimpleNamespace(),
    )
    state = SimpleNamespace(
        settings=AppSettings(),
        manual_extract_running=False,
    )
    actions = WatchActions(state=state, refs=refs, services=services)

    warnings = []
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        services.batch_session.processor.is_running = True
        actions.start_watch_mode()
        assert refs.watch_mode_action.isChecked() is False
        assert len(warnings) == 1
        assert services.watch_mode_coordinator.start_calls == []

        refs.watch_mode_action.setChecked(True)
        services.batch_session.processor.is_running = False
        state.manual_extract_running = True
        actions.start_watch_mode()
        assert refs.watch_mode_action.isChecked() is False
        assert len(warnings) == 2
        assert services.watch_mode_coordinator.start_calls == []
    finally:
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        refs.status_label.deleteLater()
        if owned_app:
            app.quit()


def _test_batch_actions_block_when_watch_running() -> None:
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("batch action watch guard test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLineEdit, QMainWindow, QMessageBox

    from .core.settings_model import AppSettings
    from .i18n.catalog import t
    from .ui.main.actions.batch import BatchActions

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
    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=SimpleNamespace(is_active=True),
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

    warnings = []
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        actions.start_processing()
        actions.retry_failed_files()
        assert len(warnings) == 2
        assert services.batch_session.create_calls == 0
    finally:
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        if owned_app:
            app.quit()


def _test_retry_failed_files_normalizes_empty_output_path() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("retry failed output normalization test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLineEdit, QMainWindow, QMessageBox

    from .core.settings_model import AppSettings
    from .i18n.catalog import t
    from .ui.main.actions.batch import BatchActions

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
            failed_a = os.path.join(input_dir, "failed_a.jpg")
            failed_b = os.path.join(input_dir, "failed_b.jpg")
            open(failed_a, "wb").close()
            open(failed_b, "wb").close()
            services.batch_session.failed_files = [failed_a, failed_b]
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
                    [failed_a, failed_b],
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

    from .core.settings_model import AppSettings
    from .i18n.catalog import t
    from .ui.main.actions.batch import BatchActions

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

    from .core.batch_profile_manager import BatchProfile, BatchProfileManager
    from .core.settings_model import AppSettings

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


def _test_settings_panel_classification_folder_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for classification folder roundtrip test: {e}")
        return

    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    settings = AppSettings()
    settings.classification.category_folders["portrait"] = "프로필"
    settings.classification.category_folders["other"] = "기타커스텀"

    panel = SettingsPanel(settings)
    panel._load_settings(settings)
    assert panel.classification_folder_inputs["portrait"].text() == "프로필"
    assert panel.classification_folder_inputs["other"].text() == "기타커스텀"

    panel.classification_folder_inputs["portrait"].setText("인물새폴더")
    panel.classification_folder_inputs["other"].setText("")
    out = panel._build_settings()
    assert out.classification.category_folders["portrait"] == "인물새폴더"
    assert out.classification.category_folders["other"] == ""

    panel.deleteLater()
    if owned_app:
        app.quit()


def _test_classification_folder_default_sentinel_migration() -> None:
    from .core.settings_model import AppSettings
    from .utils.path_validation import resolve_category_folder_map

    settings = AppSettings.from_dict(
        {
            "ui": {"language": "en"},
            "classification": {
                "category_folders": {
                    "portrait": "인물",
                    "landscape": "풍경",
                    "document": "문서",
                    "blackwhite": "흑백",
                    "other": "기타",
                }
            },
        }
    )

    assert settings.classification.category_folders["portrait"] == ""
    resolved = resolve_category_folder_map(
        settings.classification.category_folders,
        language=settings.ui.language,
    )
    assert resolved["portrait"] == "Portrait"
    assert resolved["other"] == "Other"


def _test_settings_path_validation_blocks_invalid_segments() -> None:
    from .core.settings_model import AppSettings
    from .utils.path_validation import validate_settings_path_segments

    settings = AppSettings()
    settings.file_management.naming_prefix = "scan/2026"
    settings.classification.category_folders["portrait"] = "CON"

    issues = validate_settings_path_segments(settings)
    fields = {issue.field for issue in issues}
    assert "file_management.naming_prefix" in fields
    assert "classification.category_folders.portrait" in fields


def _test_settings_panel_legacy_custom_alias_and_schedule_once_hint() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for settings alias/hint test: {e}")
        return

    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    settings = AppSettings.from_dict({"classification": {"model": "custom"}})
    panel = SettingsPanel(settings)
    panel._load_settings(settings)

    model_options = [
        panel.classification_model_combo.itemText(i)
        for i in range(panel.classification_model_combo.count())
    ]
    assert model_options == ["basic", "advanced"]
    assert panel.classification_model_combo.currentText() == "advanced"

    panel.schedule_type_combo.setCurrentText("once")
    assert "다음 도래" in panel.schedule_hint_label.text()

    out = panel._build_settings()
    assert out.classification.model == "advanced"

    panel.deleteLater()
    if owned_app:
        app.quit()


def _test_cli_cancel_exit_code_130() -> None:
    import os
    import tempfile

    from . import cli as cli_mod
    from .core import batch as batch_mod

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

    from . import cli as cli_mod
    from .core import batch as batch_mod

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

    from . import cli as cli_mod

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


def _test_multi_photo_merge_distance_effect() -> None:
    import numpy as np

    from .core.multi_photo_detector import DetectedPhoto, MultiPhotoDetector

    contour = np.array([[[0, 0]], [[10, 0]], [[10, 10]], [[0, 10]]], dtype=np.int32)
    a = DetectedPhoto((0, 0, 200, 200), contour, 0.80, 40000, 1.0)
    b = DetectedPhoto((90, 0, 200, 200), contour, 0.79, 40000, 1.0)

    d_low = MultiPhotoDetector(merge_distance=20)
    d_high = MultiPhotoDetector(merge_distance=160)

    kept_low = d_low._merge_overlapping([a, b])
    kept_high = d_high._merge_overlapping([a, b])

    assert len(kept_low) == 2, f"Expected 2 with low merge distance, got {len(kept_low)}"
    assert len(kept_high) == 1, f"Expected 1 with high merge distance, got {len(kept_high)}"


def _test_multi_photo_perspective_crop_path() -> None:
    import cv2
    import numpy as np

    from .core.multi_photo_detector import DetectedPhoto, MultiPhotoDetector

    img = np.full((700, 900, 3), 20, dtype=np.uint8)
    center = (450, 350)
    rect = ((center[0], center[1]), (420, 260), -18.0)
    box = cv2.boxPoints(rect).astype(np.float32)
    cv2.fillPoly(img, [box.astype(np.int32)], (220, 220, 220))
    cv2.polylines(img, [box.astype(np.int32)], True, (15, 15, 15), 6)

    x, y, w, h = cv2.boundingRect(box.astype(np.int32))
    contour = box.astype(np.int32).reshape((-1, 1, 2))
    photo = DetectedPhoto(
        bounding_box=(x, y, w, h),
        contour=contour,
        confidence=0.95,
        area=int(w * h),
        aspect_ratio=float(w / max(1, h)),
        quad=box,
    )

    detector = MultiPhotoDetector()
    crops = detector.crop_photos(img, [photo], padding=0)
    assert len(crops) == 1
    crop = crops[0][0]
    assert crop is not None

    exp_w, exp_h = detector._quad_dimensions(box)
    assert abs(crop.shape[1] - int(round(exp_w))) <= 40
    assert abs(crop.shape[0] - int(round(exp_h))) <= 40


def _test_accurate_mode_global_rerank_prefers_best_stage() -> None:
    import numpy as np

    from .core.image import ImageProcessor, DetectionStage
    from .core.settings_model import AlgorithmSettings, ProcessingSettings

    algo = AlgorithmSettings(detection_mode="accurate", use_clahe=False)
    proc = ProcessingSettings(auto_contrast=False)
    ip = ImageProcessor(algo, proc)

    img = np.full((300, 420, 3), 180, dtype=np.uint8)
    quad = np.array([[40, 40], [380, 50], [370, 250], [45, 260]], dtype=np.float32)

    stage_scores = [0.80, 0.83, 0.85, 0.86, 0.95]
    call_state = {"idx": 0}

    ip._accept_stage_candidate = lambda stage, score: True
    ip.detect_edges_multiscale = lambda gray: np.zeros_like(gray)

    def _find_best_contour(*_args, **_kwargs):
        i = call_state["idx"]
        call_state["idx"] += 1
        if i < len(stage_scores):
            score = stage_scores[i]
            return quad.copy(), score, [{"quad": quad.copy(), "score": score}]
        return None, 0.0, []

    ip.find_best_contour = _find_best_contour
    ip._detect_rectangle_by_hough = lambda _edges: quad.copy()
    ip._score_quad = lambda *_args, **_kwargs: 0.90
    ip._apply_post_processing = lambda image: image

    result = ip._process_loaded_image(img, "synthetic.png")
    assert result.success
    assert result.detection_stage == DetectionStage.CORNER_HARRIS


def _test_find_best_contour_uses_score_edge_map() -> None:
    import cv2
    import numpy as np

    from .core.image import ImageProcessor
    from .core.settings_model import AlgorithmSettings

    ip = ImageProcessor(AlgorithmSettings(use_clahe=False))
    mask = np.zeros((220, 220), dtype=np.uint8)
    cv2.rectangle(mask, (30, 30), (190, 190), 255, -1)
    score_map = np.zeros_like(mask)

    captured = {"edge": None}
    original_score = ip._score_quad

    def _spy_score(quad, image_area, edge_image=None, image_shape=None):
        captured["edge"] = edge_image
        return original_score(quad, image_area, edge_image=edge_image, image_shape=image_shape)

    ip._score_quad = _spy_score
    _, score_default, _ = ip.find_best_contour(mask, mask.size)
    _, score_ref, _ = ip.find_best_contour(mask, mask.size, score_edge_map=score_map)
    assert captured["edge"] is score_map, "Expected dedicated score edge map to be used"
    assert score_ref < score_default, (
        "Expected lower score when edge support comes from empty reference edge map"
    )


def _test_exif_orientation_normalization() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    try:
        from PIL import Image
    except Exception as e:
        print(f"WARN: Pillow unavailable for EXIF orientation test: {e}")
        return

    from .core.image import ImageProcessor

    # EXIF tag: 274 (Orientation), value 6 = rotate 90 CW for display.
    exif_orientation_tag = 274

    rgb = np.full((30, 60, 3), 255, dtype=np.uint8)
    rgb[:, :30] = (255, 0, 0)
    pil = Image.fromarray(rgb, mode="RGB")
    exif = pil.getexif()
    exif[exif_orientation_tag] = 6

    with tempfile.TemporaryDirectory(prefix="photocropper_exif_") as td:
        path = os.path.join(td, "exif_oriented.jpg")
        pil.save(path, exif=exif)
        loaded = ImageProcessor.load_image(path)
        assert loaded is not None
        assert loaded.shape[0] > loaded.shape[1], f"Expected portrait after EXIF transpose: {loaded.shape}"


def _test_processing_logger_partial_summary() -> None:
    import tempfile

    from .utils.processing_log import ProcessingLogger

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


def _test_face_rotation_uses_primary_face() -> None:
    import numpy as np

    from .core.face.detector import FaceDetector, FaceRect, EyeRect

    detector = FaceDetector(use_dnn=False)
    detector._detect_faces_cascade = lambda _img: [
        FaceRect(x=10, y=10, width=40, height=40),
        FaceRect(x=120, y=80, width=120, height=120),
    ]

    def _fake_eyes(_gray, face):
        if face.width < 100:
            # angled eyes for the small (non-primary) face
            return [EyeRect(15, 15, 8, 8), EyeRect(30, 28, 8, 8)]
        # almost horizontal eyes for primary face
        return [EyeRect(140, 120, 10, 10), EyeRect(200, 121, 10, 10)]

    detector._detect_eyes = _fake_eyes
    img = np.full((280, 320, 3), 180, dtype=np.uint8)
    result = detector.detect(img, detect_eyes=True, suggest_crop=False)
    assert result.has_faces
    assert abs(float(result.rotation_angle)) < 2.0, result.rotation_angle


def _test_settings_panel_algorithm_tuning_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for algorithm tuning roundtrip test: {e}")
        return

    from .core.settings_model import AppSettings
    from .ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    s = AppSettings()
    s.algorithm.min_area_ratio = 0.14
    s.algorithm.max_area_ratio = 0.92
    s.algorithm.bg_mask_delta = 44.0
    s.algorithm.adaptive_block_size = 19
    s.algorithm.adaptive_c = 2.5

    panel = SettingsPanel(s)
    panel._load_settings(s)
    out = panel._build_settings()

    assert abs(float(out.algorithm.min_area_ratio) - 0.14) < 1e-6
    assert abs(float(out.algorithm.max_area_ratio) - 0.92) < 1e-6
    assert abs(float(out.algorithm.bg_mask_delta) - 44.0) < 1e-6
    assert int(out.algorithm.adaptive_block_size) == 19
    assert abs(float(out.algorithm.adaptive_c) - 2.5) < 1e-6

    panel.deleteLater()
    if owned_app:
        app.quit()


def _test_benchmark_harness_report_contract() -> None:
    import json
    import os
    import tempfile

    import cv2
    import numpy as np

    from .benchmark import run_benchmark
    from .core.image import CropResult, DetectionStage

    class FakeProcessor:
        def __init__(self):
            self._calls = 0

        def load_image(self, image_path: str) -> np.ndarray | None:
            arr = np.fromfile(image_path, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        def process_image(self, _image_path: str) -> CropResult:
            self._calls += 1
            if self._calls == 1:
                quad = np.array([[20, 20], [180, 20], [180, 180], [20, 180]], dtype=np.float32)
                return CropResult(
                    success=True,
                    contour_points=quad,
                    detection_stage=DetectionStage.CANNY,
                    confidence=0.9,
                )
            return CropResult(
                success=False,
                contour_points=None,
                detection_stage=None,
                confidence=0.0,
            )

    with tempfile.TemporaryDirectory(prefix="photocropper_bench_") as td:
        img_dir = os.path.join(td, "images")
        os.makedirs(img_dir, exist_ok=True)
        for name in ("a.jpg", "b.jpg"):
            img = np.full((220, 220, 3), 150, dtype=np.uint8)
            ok, buf = cv2.imencode(".jpg", img)
            assert ok
            buf.tofile(os.path.join(img_dir, name))

        labels = {
            "version": 1,
            "items": [
                {"file": "a.jpg", "has_photo": True, "quad": [[20, 20], [180, 20], [180, 180], [20, 180]]},
                {"file": "b.jpg", "has_photo": False},
            ],
        }
        labels_path = os.path.join(td, "labels.json")
        with open(labels_path, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)

        report_path = os.path.join(td, "report.json")
        report = run_benchmark(
            img_dir,
            labels_path,
            report_path=report_path,
            processor_factory=lambda: FakeProcessor(),
        )

        assert os.path.exists(report_path)
        assert "metrics" in report
        metrics = report["metrics"]
        for key in (
            "success_rate",
            "mean_iou",
            "median_iou",
            "p90_iou",
            "false_positive_rate",
            "stage_distribution",
        ):
            assert key in metrics


def _test_library_catalog_import_and_duplicates() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.library import DuplicateService, LibraryIngestService, ThumbnailService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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


def _test_job_orchestrator_records_variants_and_review_queue() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.batch import BatchProgress, FileResult, ProcessStatus
    from .core.jobs import JobOrchestrator
    from .core.library import DuplicateService, ThumbnailService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore
    from .core.settings_model import AppSettings

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


def _test_library_search_and_collections() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.library.query_service import QueryService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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

    from .core.library.duplicate_service import DuplicateService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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

    from .core.library.duplicate_service import DuplicateService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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

    from .core.library import LibraryIngestService, ThumbnailService
    from .core.library.duplicate_service import DuplicateService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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


def _test_recipe_determinism_and_preserved_global_state() -> None:
    import os
    import tempfile

    from .core.recipes.manager import RecipeManager, RecipeRecord
    from .core.settings_model import AppSettings

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

    from .core.jobs import JobOrchestrator
    from .core.library import DuplicateService, ReviewService, ThumbnailService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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


def _test_asset_query_filters_and_timeline() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.library import AssetQuery
    from .core.library.query_service import QueryService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

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


def _test_management_preflight_file_batch_guard() -> None:
    import os
    import tempfile

    from .ui.main.services.batch_flow import BatchRuntimeFlow

    with tempfile.TemporaryDirectory(prefix="photocropper_preflight_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(input_dir, "output_cropped")
        os.makedirs(input_dir, exist_ok=True)
        source = os.path.join(input_dir, "source.jpg")
        with open(source, "wb") as f:
            f.write(b"not a real image but present")

        flow = BatchRuntimeFlow()
        blocked = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=output_dir,
            files=[source],
            recursive=True,
            failed_folder_name="_failed",
        )
        assert blocked.ok is False
        allowed = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=os.path.join(td, "out"),
            files=[source],
            recursive=True,
            failed_folder_name="_failed",
        )
        assert allowed.ok is True
        missing = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=os.path.join(td, "out2"),
            files=[os.path.join(input_dir, "missing.jpg")],
            recursive=False,
            failed_folder_name="_failed",
        )
        assert missing.ok is False


def _test_library_sqlite_pragmas_and_invalid_sources() -> None:
    import os
    import tempfile

    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_sqlite_pragmas_") as td:
        store = LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        repository = LibraryRepository(store)
        with store.connect() as conn:
            foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()
            assert foreign_keys is not None and int(foreign_keys[0]) == 1
            assert busy_timeout is not None and int(busy_timeout[0]) >= 5000

        assert repository.upsert_source("")["ingest_state"] == "invalid_source"
        assert repository.upsert_source(os.path.join(td, "missing.jpg"))["ingest_state"] == "invalid_source"
        assert repository.upsert_source(td)["ingest_state"] == "invalid_source"
        text_path = os.path.join(td, "note.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("hello")
        assert repository.upsert_source(text_path)["ingest_state"] == "invalid_source"
        assert repository.list_assets(limit=10) == []


def _test_search_index_dirty_and_rebuild() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_search_dirty_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        image = np.full((80, 120, 3), 180, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        path = os.path.join(td, "asset.jpg")
        encoded.tofile(path)
        record = repository.upsert_source(path)
        asset_id = int(record["asset_id"])
        repository.store._fts_enabled = False
        repository.refresh_search_index(asset_id)
        assert repository.get_search_index_dirty() is True
        repository.store._fts_enabled = True
        assert repository.rebuild_search_index() >= 1
        assert repository.get_search_index_dirty() is False


def _test_timeline_review_query_not_limited_to_5000() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.library.query_service import QueryService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_timeline_many_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        image = np.full((80, 120, 3), 190, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        target_path = os.path.join(td, "target.jpg")
        encoded.tofile(target_path)
        target = repository.upsert_source(target_path)
        target_asset_id = int(target["asset_id"])
        repository.create_review_item(
            asset_id=target_asset_id,
            source_id=int(target["source_id"]),
            variant_id=None,
            job_id=None,
            job_item_id=None,
            status="new",
            reason="target_review",
        )
        with repository.store.write_connect() as conn:
            for idx in range(5005):
                stamp = f"2099-01-01T00:{idx // 60:02d}:{idx % 60:02d}"
                conn.execute(
                    """
                    INSERT INTO review_items(
                        asset_id, source_id, variant_id, job_id, job_item_id,
                        status, reason, notes, action_context_json, created_at, updated_at
                    )
                    VALUES (NULL, NULL, NULL, NULL, NULL, 'new', 'other', '', '{}', ?, ?)
                    """,
                    (stamp, stamp),
                )
            conn.commit()
        timeline = QueryService(repository).get_asset_timeline(target_asset_id)
        assert any(
            event.event_type == "review" and event.metadata.get("reason") == "target_review"
            for event in timeline
        )


def _test_job_summary_metadata_warnings_and_near_summary() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from .core.batch import BatchProgress, FileResult, ProcessStatus
    from .core.jobs import JobOrchestrator
    from .core.library import DuplicateService, ThumbnailService
    from .core.library.repository import LibraryRepository
    from .core.library.sqlite_store import LibrarySqliteStore
    from .core.settings_model import AppSettings

    class FailingThumbnailService(ThumbnailService):
        def ensure_thumbnail(self, file_path: str) -> str:
            return ""

    with tempfile.TemporaryDirectory(prefix="photocropper_job_warnings_") as td:
        repository = LibraryRepository(
            LibrarySqliteStore(db_path=os.path.join(td, "library.db"))
        )
        image = np.full((100, 140, 3), 200, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        src = os.path.join(td, "source.jpg")
        out = os.path.join(td, "out.jpg")
        encoded.tofile(src)
        encoded.tofile(out)
        duplicate_service = DuplicateService(repository)
        orchestrator = JobOrchestrator(
            repository,
            thumbnail_service=FailingThumbnailService(thumbnails_dir=os.path.join(td, "thumbs")),
            duplicate_service=duplicate_service,
        )
        job_id = orchestrator.create_job(job_kind="selftest_warning", input_path=td)
        orchestrator.finalize_job(
            job_id=job_id,
            progress=BatchProgress(total=1, processed=1, success=1, is_running=False),
            results=[
                FileResult(
                    filename="source.jpg",
                    status=ProcessStatus.SUCCESS,
                    source_path=src,
                    output_path=out,
                    output_paths=[out],
                )
            ],
            settings=AppSettings(),
            job_kind="selftest_warning",
        )
        job = repository.get_job(job_id)
        assert job is not None
        assert int(job["summary"]["thumbnail_failed_count"]) >= 1

        duplicate_service.rebuild_near_groups(limit=1)
        assert "scanned_assets" in duplicate_service.last_near_summary
        assert "limited" in duplicate_service.last_near_summary


def main() -> int:
    try:
        _test_crop_editor_import_smoke()
        _test_preview_worker_import_smoke()
        _test_ui_action_modules_import_smoke()
        _test_ui_canonical_package_import_smoke()
        _test_main_window_import_smoke()
        _test_manual_extract_service_import_smoke()
        _test_batch_session_service_smoke()
        _test_batch_session_service_reentry_guard()
        _test_manual_extract_session_runner_empty()
        _test_image_save_io_module_smoke()
        _test_watch_mode_coordinator_import_smoke()
        _test_watch_mode_coordinator_invalid_input()
        _test_watch_mode_coordinator_recursive_output_guard()
        _test_watch_mode_processing_disables_failed_file_move()
        _test_contour_utils_roundtrip()
        _test_preview_widget_contour_redraw_variants()
        _test_manual_preview_shared_crop_mode()
        _test_boundary_failed_file_collection_helper()
        _test_boundary_failed_file_collection_prefers_relative_paths()
        _test_recursive_scan_excludes_internal_generated_dirs()
        _test_classify_failed_files_preserves_relative_dirs()
        _test_cli_settings_merge_priority()
        _test_classification_settings_custom_alias_normalizes_to_advanced()
        _test_settings_forward_compat()
        _test_unicode_text_watermark()
        _test_preview_single_pass()
        _test_batch_thread_local_reuse()
        _test_settings_panel_performance_roundtrip()
        _test_recursive_watch_new_subdir_initial_scan()
        _test_folder_watcher_file_changed_requeues_only_on_signature_change()
        _test_watch_max_wait_roundtrip()
        _test_watch_callback_runs_on_background_worker()
        _test_watch_readiness_is_owned_by_auto_processor()
        _test_batch_post_pipeline_order()
        _test_skip_processed_with_classification_subfolder()
        _test_perspective_toggle_warp_vs_axis_crop()
        _test_save_image_fallback_and_metadata_best_effort()
        _test_resize_fill_no_upscale_boundary()
        _test_multi_photo_merge_distance_and_separate_folders()
        _test_recursive_output_paths_preserve_relative_dirs()
        _test_multi_photo_uses_shared_loader()
        _test_multi_photo_status_variants_and_partial_index_behavior()
        _test_cli_new_crop_options()
        _test_processed_index_roundtrip_and_source_change()
        _test_processed_index_backward_compat_and_partial_status()
        _test_watch_actions_block_while_batch_or_manual_running()
        _test_batch_actions_block_when_watch_running()
        _test_retry_failed_files_normalizes_empty_output_path()
        _test_batch_actions_recursive_output_guard()
        _test_profile_apply_rebuild_validation()
        _test_settings_panel_classification_folder_roundtrip()
        _test_classification_folder_default_sentinel_migration()
        _test_settings_path_validation_blocks_invalid_segments()
        _test_settings_panel_legacy_custom_alias_and_schedule_once_hint()
        _test_cli_cancel_exit_code_130()
        _test_cli_partial_exit_code_rules()
        _test_cli_recursive_output_guard()
        _test_crop_accuracy_synthetic()
        _test_no_photo_false_positive_regression()
        _test_multi_photo_close_gap_split()
        _test_multi_photo_merge_distance_effect()
        _test_multi_photo_perspective_crop_path()
        _test_grayscale_image_watermark_regression()
        _test_max_image_size_limit_applied()
        _test_face_dnn_fallback_when_download_fails()
        _test_face_rotation_uses_primary_face()
        _test_find_best_contour_uses_score_edge_map()
        _test_accurate_mode_global_rerank_prefers_best_stage()
        _test_exif_orientation_normalization()
        _test_processing_logger_partial_summary()
        _test_settings_panel_ai_roundtrip()
        _test_settings_panel_algorithm_tuning_roundtrip()
        _test_benchmark_harness_report_contract()
        _test_library_catalog_import_and_duplicates()
        _test_job_orchestrator_records_variants_and_review_queue()
        _test_library_search_and_collections()
        _test_duplicate_service_near_groups()
        _test_duplicate_preferences_preserved_on_rebuild()
        _test_source_relink_unique_and_ambiguous()
        _test_recipe_determinism_and_preserved_global_state()
        _test_review_service_guard_and_reprocess_queue()
        _test_asset_query_filters_and_timeline()
        _test_management_preflight_file_batch_guard()
        _test_library_sqlite_pragmas_and_invalid_sources()
        _test_search_index_dirty_and_rebuild()
        _test_timeline_review_query_not_limited_to_5000()
        _test_job_summary_metadata_warnings_and_near_summary()
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
