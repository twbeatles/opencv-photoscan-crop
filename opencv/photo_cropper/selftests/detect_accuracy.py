#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Detection accuracy self-tests."""

from __future__ import annotations


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
    # Raised after order_points / soft gates / morph-LSD stages (plan target ≥0.85 long-term).
    assert mean_iou >= 0.80, f"Mean IoU too low: {mean_iou:.3f}"


def _test_order_points_rotated_quad_stable() -> None:
    import numpy as np

    from ..core.image.geometry import ImageGeometryMixin

    # Rotated rectangle corners (not axis-aligned).
    pts = np.array(
        [[120.0, 40.0], [220.0, 90.0], [170.0, 190.0], [70.0, 140.0]],
        dtype=np.float32,
    )
    ordered = ImageGeometryMixin.order_points(pts)
    assert ordered.shape == (4, 2)
    # TL should have smallest x+y among ordered starts.
    assert float(ordered[0].sum()) <= float(ordered[1].sum()) + 1e-3
    # Convex and non-zero area.
    import cv2

    area = float(cv2.contourArea(ordered.reshape((-1, 1, 2))))
    assert area > 100.0


def _test_scene_preset_album_enables_multi() -> None:
    from ..core.scene_presets import apply_scene_preset, build_algorithm_for_scene
    from ..core.settings_model import AppSettings

    algo = build_algorithm_for_scene("scanner_white")
    assert algo.detection_mode in ("fast", "balanced", "accurate")
    assert algo.canny_min < algo.canny_max

    settings = AppSettings()
    settings.multi_photo.enabled = False
    apply_scene_preset(settings, "album_multi")
    assert settings.multi_photo.enabled is True
    assert settings.multi_photo.refine_with_single is True
    assert settings.algorithm.detection_mode == "accurate"


def _test_crop_accuracy_hard_scenarios() -> None:
    """Harder synthetic cases: weak border, edge contact, textured bed."""
    import os
    import random
    import tempfile

    import cv2
    import numpy as np

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings, DebugSettings, ProcessingSettings

    random.seed(7)
    np.random.seed(7)

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
        min_area_ratio=0.05,
        max_area_ratio=0.98,
        contour_scoring="enhanced",
    )
    ip = ImageProcessor(
        algo,
        ProcessingSettings(auto_contrast=False),
        debug_settings=DebugSettings(enabled=False),
    )

    successes = 0
    ious = []
    n = 12
    with tempfile.TemporaryDirectory(prefix="photocropper_hard_") as td:
        for i in range(n):
            h, w = 640, 800
            # Textured background
            bg = np.random.randint(180, 230, (h, w, 3), dtype=np.uint8)
            noise = (np.random.randn(h, w, 1) * 8).astype(np.int16)
            img = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            if i % 3 == 0:
                # Edge-contacting photo (touches left border)
                quad = np.array(
                    [[2, 80], [520, 70], [530, 520], [5, 530]], dtype=np.float32
                )
            elif i % 3 == 1:
                # Weak border + perspective
                quad = np.array(
                    [[90, 60], [700, 90], [680, 540], [110, 510]], dtype=np.float32
                )
            else:
                # Centered strong photo
                quad = np.array(
                    [[140, 100], [640, 95], [650, 500], [130, 510]], dtype=np.float32
                )

            fill = int(np.random.randint(40, 90))
            cv2.fillPoly(img, [quad.astype(np.int32)], (fill, fill + 10, fill + 5))
            border_w = 2 if i % 3 == 1 else 5
            cv2.polylines(
                img, [quad.astype(np.int32)], True, (30, 30, 30), border_w
            )

            path = os.path.join(td, f"hard_{i:02d}.png")
            save_png(path, img)
            res = ip.process_image(path)
            if res.success and res.contour_points is not None:
                successes += 1
                ious.append(
                    quad_iou(
                        quad,
                        res.contour_points.astype(np.float32),
                        (h, w),
                    )
                )
            else:
                ious.append(0.0)

    success_rate = successes / n
    mean_iou = sum(ious) / len(ious)
    # Hard set: allow lower bar than clean synthetic suite.
    assert success_rate >= 0.75, f"Hard success rate too low: {success_rate:.2%}"
    assert mean_iou >= 0.55, f"Hard mean IoU too low: {mean_iou:.3f}"


def _test_detection_pipeline_composition() -> None:
    from ..core.image import DetectionPipeline, ImageProcessor
    from ..core.settings_model import AlgorithmSettings

    ip = ImageProcessor(AlgorithmSettings())
    assert isinstance(ip.detection, DetectionPipeline)
    assert ip.detection.algo is ip.algo
    assert ip.load_image is not None


def _test_nms_and_snap_helpers() -> None:
    import cv2
    import numpy as np

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings

    ip = ImageProcessor(AlgorithmSettings())
    q1 = np.array([[10, 10], [100, 10], [100, 80], [10, 80]], dtype=np.float32)
    q2 = q1 + np.array([[2, 1], [1, 0], [0, 2], [1, 1]], dtype=np.float32)
    iou = ip._quad_iou(q1, q2, (120, 120))
    assert iou > 0.8

    edges = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(edges, (20, 20), (80, 80), 255, 1)
    rough = np.array([[18, 18], [82, 19], [81, 82], [19, 81]], dtype=np.float32)
    snapped = ip._snap_quad_to_edges(rough, edges, search_radius=4)
    assert snapped.shape == (4, 2)

    cands = [
        {"quad": q1, "score": 0.9, "stage_rank": 0},
        {"quad": q2, "score": 0.8, "stage_rank": 1},
        {
            "quad": np.array([[5, 5], [40, 5], [40, 40], [5, 40]], dtype=np.float32),
            "score": 0.7,
            "stage_rank": 2,
        },
    ]
    kept = ip._nms_stage_candidates(cands, (120, 120), iou_threshold=0.7)
    assert len(kept) == 2


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
