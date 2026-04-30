#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unicode-safe image I/O helpers."""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _pil_to_cv_array(image, flags: int) -> Optional[np.ndarray]:
    """Convert a Pillow image to an OpenCV-compatible numpy array."""
    try:
        if flags == cv2.IMREAD_GRAYSCALE:
            return np.array(image.convert("L"))

        if flags == cv2.IMREAD_UNCHANGED:
            if image.mode in {"RGBA", "LA"}:
                rgba = np.array(image.convert("RGBA"))
                return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
            if image.mode == "L":
                return np.array(image)

        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        logger.debug("Pillow to OpenCV conversion failed: %s", exc)
        return None


def load_image_unicode(
    path: str,
    flags: int = cv2.IMREAD_COLOR,
    *,
    normalize_exif: bool = False,
) -> Optional[np.ndarray]:
    """
    Load an image from a filesystem path that may contain non-ASCII characters.

    OpenCV's ``cv2.imread`` is unreliable for some Unicode paths on Windows.
    This helper reads bytes via numpy and decodes them with OpenCV. When
    ``normalize_exif`` is true, Pillow is tried first so EXIF orientation can be
    applied before returning an OpenCV-style array.
    """
    image_path = str(path or "").strip()
    if not image_path:
        return None

    if normalize_exif:
        try:
            from PIL import Image, ImageOps

            with Image.open(image_path) as pil_image:
                converted = _pil_to_cv_array(ImageOps.exif_transpose(pil_image), flags)
                if converted is not None:
                    return converted
        except Exception as exc:
            logger.debug("Pillow image load fallback for '%s': %s", image_path, exc)

    try:
        data = np.fromfile(image_path, dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, flags)
    except Exception as exc:
        logger.debug("Unicode-safe image load failed for '%s': %s", image_path, exc)
        return None
