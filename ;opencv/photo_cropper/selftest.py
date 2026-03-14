#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Lightweight self-tests for Photo Cropper.

Run:
  python -m photo_cropper.selftest
"""

from __future__ import annotations

import sys


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
        assert merged.classification.model == "custom"  # CLI overrides config
        assert abs(merged.classification.min_confidence - 0.65) < 1e-6
        assert merged.advanced.auto_deskew is True  # legacy alias mapped


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

    def run_case(save_plan, *, stop_on_check: Optional[int] = None):
        settings = AppSettings()
        settings.multi_photo.enabled = True
        settings.filter.skip_processed = True
        batch = BatchProcessor(settings)
        state = {"save_calls": 0, "stop_checks": 0}

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
            matched, usable = batch.lookup_processed_outputs_from_index(src, out_dir)
            return result, matched, usable

    success_result, success_outputs, success_usable = run_case([True, True])
    assert success_result.status == ProcessStatus.SUCCESS, success_result.message
    assert success_usable is True
    assert success_outputs is not None and len(success_outputs) == 2

    partial_result, partial_outputs, partial_usable = run_case([True, False])
    assert partial_result.status == ProcessStatus.PARTIAL_SUCCESS, partial_result.message
    assert partial_usable is True
    assert partial_outputs is None

    failed_result, failed_outputs, _failed_usable = run_case([False, False])
    assert failed_result.status == ProcessStatus.FAILED, failed_result.message
    assert failed_outputs is None

    cancelled_result, cancelled_outputs, _cancelled_usable = run_case(
        [True, True],
        stop_on_check=2,
    )
    assert cancelled_result.status == ProcessStatus.CANCELLED, cancelled_result.message
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
        matched, usable = processor.lookup_processed_outputs_from_index(src, out_dir)
        assert usable is True
        assert matched is not None and len(matched) == 1
        assert os.path.normcase(os.path.abspath(matched[0])) == os.path.normcase(
            os.path.abspath(out)
        )

        time.sleep(0.01)
        with open(src, "ab") as f:
            f.write(b"-changed")

        matched_changed, usable_changed = processor.lookup_processed_outputs_from_index(
            src, out_dir
        )
        assert usable_changed is True
        assert matched_changed is None


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
    assert out.classification.category_folders["other"] == "기타"

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

        def load_image(self, image_path):
            arr = np.fromfile(image_path, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)

        def process_image(self, _image_path):
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
        _test_contour_utils_roundtrip()
        _test_boundary_failed_file_collection_helper()
        _test_cli_settings_merge_priority()
        _test_settings_forward_compat()
        _test_unicode_text_watermark()
        _test_preview_single_pass()
        _test_batch_thread_local_reuse()
        _test_settings_panel_performance_roundtrip()
        _test_recursive_watch_new_subdir_initial_scan()
        _test_watch_max_wait_roundtrip()
        _test_watch_callback_runs_on_background_worker()
        _test_watch_readiness_is_owned_by_auto_processor()
        _test_batch_post_pipeline_order()
        _test_skip_processed_with_classification_subfolder()
        _test_perspective_toggle_warp_vs_axis_crop()
        _test_save_image_fallback_and_metadata_best_effort()
        _test_resize_fill_no_upscale_boundary()
        _test_multi_photo_merge_distance_and_separate_folders()
        _test_multi_photo_uses_shared_loader()
        _test_multi_photo_status_variants_and_partial_index_behavior()
        _test_cli_new_crop_options()
        _test_processed_index_roundtrip_and_source_change()
        _test_profile_apply_rebuild_validation()
        _test_settings_panel_classification_folder_roundtrip()
        _test_cli_cancel_exit_code_130()
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
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
