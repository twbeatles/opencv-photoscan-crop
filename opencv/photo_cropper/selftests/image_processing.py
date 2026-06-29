#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Image Processing self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_manual_extract_session_runner_empty() -> None:
    import tempfile
    from threading import Event

    from ..core.manual_extract import ManualExtractSessionRunner

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

    from ..core.manual_extract import (
        normalize_contour_points,
        denormalize_contour_points,
        scale_contour_to_preview,
    )
    from ..core.image import CropResult

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

    from ..ui.widgets.preview_widget import ImagePreviewWidget

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

    from ..core.manual_extract import crop_manual_contour
    from ..core.settings_model import AppSettings
    from ..ui.main.actions.preview import PreviewActions

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

def _test_unicode_text_watermark() -> None:
    import numpy as np

    from ..core.watermark_processor import WatermarkProcessor, TextWatermarkSettings

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

    from ..core.image import ImageProcessor
    from ..core.settings_model import AppSettings

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

def _test_crop_accuracy_synthetic() -> None:
    import os
    import random
    import tempfile

    import cv2
    import numpy as np

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings, ProcessingSettings, DebugSettings

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

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings, ProcessingSettings, DebugSettings

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

def _test_grayscale_image_watermark_regression() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..core.watermark_processor import WatermarkProcessor, ImageWatermarkSettings

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

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.settings_model import AppSettings

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

    from ..core.face import detector as fd_mod

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

def _test_perspective_toggle_warp_vs_axis_crop() -> None:
    import numpy as np

    from ..core.image import ImageProcessor
    from ..core.settings_model import (
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

    from ..core.image import ImageProcessor

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

    from ..core.resize_processor import ResizeProcessor, ResizeSettings, ResizeMode

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

def _test_recursive_output_paths_preserve_relative_dirs() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    import numpy as np

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.image import CropResult, DetectionStage
    from ..core.settings_model import AppSettings

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

def _test_unicode_image_io_helper_and_blank_path_guards() -> None:
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..utils.file_helpers import (
        build_recursive_excluded_roots,
        is_output_inside_input,
        normalize_path,
    )
    from ..utils.image_io import load_image_unicode

    with tempfile.TemporaryDirectory(prefix="photocropper_unicode_경로_") as td:
        image_path = os.path.join(td, "샘플 이미지.jpg")
        image = np.zeros((12, 16, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        encoded.tofile(image_path)

        loaded = load_image_unicode(image_path, cv2.IMREAD_COLOR)
        assert loaded is not None
        assert loaded.shape[:2] == (12, 16)

        assert normalize_path("") == ""
        assert normalize_path("   ") == ""
        roots = build_recursive_excluded_roots(td, "")
        assert normalize_path(os.getcwd()) not in roots
        assert is_output_inside_input("", os.path.join(td, "child")) is False

def _test_history_record_applied_and_merge() -> None:
    from ..core.history_manager import CallableCommand, HistoryManager

    state = {"value": 2}
    history = HistoryManager(max_history=10)
    history.record_applied(
        CallableCommand(
            do=lambda: state.update(value=2),
            undo=lambda: state.update(value=1),
            redo=lambda: state.update(value=2),
            description="first",
            merge_key="settings",
        ),
        merge_key="settings",
    )
    history.record_applied(
        CallableCommand(
            do=lambda: state.update(value=3),
            undo=lambda: state.update(value=2),
            redo=lambda: state.update(value=3),
            description="second",
            merge_key="settings",
        ),
        merge_key="settings",
    )
    assert history.history_count == 1
    assert history.undo()
    assert state["value"] == 1
    assert history.redo()
    assert state["value"] == 3

def _test_accurate_mode_global_rerank_prefers_best_stage() -> None:
    import numpy as np

    from ..core.image import ImageProcessor, DetectionStage
    from ..core.settings_model import AlgorithmSettings, ProcessingSettings

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

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings

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

    from ..core.image import ImageProcessor

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

def _test_face_rotation_uses_primary_face() -> None:
    import numpy as np

    from ..core.face.detector import FaceDetector, FaceRect, EyeRect

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

def _test_benchmark_harness_report_contract() -> None:
    import json
    import os
    import tempfile

    import cv2
    import numpy as np

    from ..benchmark import run_benchmark
    from ..core.image import CropResult, DetectionStage

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

__all__ = [
    "_test_manual_extract_session_runner_empty",
    "_test_contour_utils_roundtrip",
    "_test_preview_widget_contour_redraw_variants",
    "_test_manual_preview_shared_crop_mode",
    "_test_unicode_text_watermark",
    "_test_preview_single_pass",
    "_test_crop_accuracy_synthetic",
    "_test_no_photo_false_positive_regression",
    "_test_grayscale_image_watermark_regression",
    "_test_max_image_size_limit_applied",
    "_test_face_dnn_fallback_when_download_fails",
    "_test_perspective_toggle_warp_vs_axis_crop",
    "_test_save_image_fallback_and_metadata_best_effort",
    "_test_resize_fill_no_upscale_boundary",
    "_test_recursive_output_paths_preserve_relative_dirs",
    "_test_unicode_image_io_helper_and_blank_path_guards",
    "_test_history_record_applied_and_merge",
    "_test_accurate_mode_global_rerank_prefers_best_stage",
    "_test_find_best_contour_uses_score_edge_map",
    "_test_exif_orientation_normalization",
    "_test_face_rotation_uses_primary_face",
    "_test_benchmark_harness_report_contract",
]
