#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Face detector singleton factory.

Single responsibility: process-wide shared ``FaceDetector`` instance
lifecycle. The detector class itself lives in :mod:`.detector`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # Avoid a runtime import cycle; resolved lazily below.
    from .detector import FaceDetector


_detector_instance: Optional["FaceDetector"] = None


def get_face_detector(use_dnn: bool = False, min_face_size: int = 30) -> "FaceDetector":
    """Get global face detector instance."""
    from .detector import FaceDetector as _FaceDetector

    global _detector_instance
    normalized_size = max(20, min(500, int(min_face_size)))
    if (
        _detector_instance is None
        or _detector_instance.use_dnn != bool(use_dnn)
        or _detector_instance.min_face_size != normalized_size
    ):
        _detector_instance = _FaceDetector(
            use_dnn=bool(use_dnn),
            min_face_size=normalized_size,
        )
    return _detector_instance


def reset_face_detector_for_tests() -> None:
    global _detector_instance
    _detector_instance = None


__all__ = ['get_face_detector', 'reset_face_detector_for_tests']
