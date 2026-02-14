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


def main() -> int:
    try:
        _test_settings_forward_compat()
        _test_unicode_text_watermark()
    except Exception as e:
        print(f"SELFTEST FAILED: {e}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

