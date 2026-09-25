#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Preview/face/benchmark self-tests."""

from __future__ import annotations

from .helpers import _ensure_qt_app


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
