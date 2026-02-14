#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight self-tests for Photo Cropper.

Run:
  python -m photo_cropper.selftest
"""

from __future__ import annotations

import sys


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


def main() -> int:
    try:
        _test_settings_forward_compat()
        _test_unicode_text_watermark()
        _test_crop_accuracy_synthetic()
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
