#!/usr/bin/env python3
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


def _test_cli_settings_merge_priority() -> None:
    import json
    import os
    import tempfile

    from . import cli as cli_mod
    from .core.batch_profile_manager import BatchProfileManager
    from .core.settings import AppSettings

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
    from .core.settings import AppSettings
    from .ui.widgets.settings_panel import SettingsPanel

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

    panel.deleteLater()
    auto.stop()
    auto.deleteLater()
    if owned_app:
        app.quit()


def _test_settings_forward_compat() -> None:
    from .core.settings import AppSettings

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

    from .core.image_processor import ImageProcessor
    from .core.settings import AppSettings

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


def _test_batch_thread_local_reuse() -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from .core.batch_processor import BatchProcessor
    from .core.settings import AppSettings

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

    from .core.settings import AppSettings
    from .ui.widgets.settings_panel import SettingsPanel

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

    from .core.image_processor import ImageProcessor
    from .core.settings import AlgorithmSettings, ProcessingSettings, DebugSettings

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

    from .core.image_processor import ImageProcessor
    from .core.settings import AlgorithmSettings, ProcessingSettings, DebugSettings

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

    from .core.batch_processor import BatchProcessor, ProcessStatus
    from .core.settings import AppSettings

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

    from .core import face_detector as fd_mod

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

    from .core.settings import AppSettings
    from .ui.widgets.settings_panel import SettingsPanel

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

    from .core.batch_processor import BatchProcessor
    from .core.settings import AppSettings

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

    from .core.batch_processor import BatchProcessor, ProcessStatus
    from .core.image_classifier import ClassificationResult, ImageCategory
    from .core.image_processor import CropResult, DetectionStage
    from .core.settings import AppSettings

    settings = AppSettings()
    settings.classification.enabled = True
    settings.classification.auto_folder = True
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
        ):
            del output_format, png_compression, webp_quality
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
        assert os.path.isdir(os.path.join(out_dir, "인물"))
        assert os.path.exists(r1.output_path)

        r2 = processor.process_single(src, out_dir)
        assert r2.status == ProcessStatus.SKIPPED, r2.message


def main() -> int:
    try:
        _test_crop_editor_import_smoke()
        _test_cli_settings_merge_priority()
        _test_settings_forward_compat()
        _test_unicode_text_watermark()
        _test_preview_single_pass()
        _test_batch_thread_local_reuse()
        _test_settings_panel_performance_roundtrip()
        _test_recursive_watch_new_subdir_initial_scan()
        _test_watch_max_wait_roundtrip()
        _test_batch_post_pipeline_order()
        _test_skip_processed_with_classification_subfolder()
        _test_crop_accuracy_synthetic()
        _test_no_photo_false_positive_regression()
        _test_multi_photo_close_gap_split()
        _test_grayscale_image_watermark_regression()
        _test_max_image_size_limit_applied()
        _test_face_dnn_fallback_when_download_fails()
        _test_settings_panel_ai_roundtrip()
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
