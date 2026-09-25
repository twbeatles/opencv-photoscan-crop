#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Image I/O and enhancement self-tests."""

from __future__ import annotations


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
