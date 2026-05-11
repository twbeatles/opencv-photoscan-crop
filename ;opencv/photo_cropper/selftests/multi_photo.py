#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Multi Photo self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_multi_photo_close_gap_split() -> None:
    import cv2
    import numpy as np

    from ..core.multi_photo_detector import MultiPhotoDetector

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

def _test_multi_photo_merge_distance_and_separate_folders() -> None:
    import os
    import tempfile

    import numpy as np

    from ..core.batch import BatchProcessor
    from ..core.multi_photo_detector import MultiPhotoDetector, DetectedPhoto
    from ..core.settings_model import AppSettings

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

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.settings_model import AppSettings

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

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.settings_model import AppSettings

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

def _test_multi_photo_merge_distance_effect() -> None:
    import numpy as np

    from ..core.multi_photo_detector import DetectedPhoto, MultiPhotoDetector

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

    from ..core.multi_photo_detector import DetectedPhoto, MultiPhotoDetector

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

__all__ = [
    "_test_multi_photo_close_gap_split",
    "_test_multi_photo_merge_distance_and_separate_folders",
    "_test_multi_photo_uses_shared_loader",
    "_test_multi_photo_status_variants_and_partial_index_behavior",
    "_test_multi_photo_merge_distance_effect",
    "_test_multi_photo_perspective_crop_path",
]
