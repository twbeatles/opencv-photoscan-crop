from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class DetectionStage(Enum):
    """Detection stage enumeration for tracking which algorithm succeeded."""

    CANNY = "Canny Edge"
    MULTI_SCALE_CANNY = "Multi-Scale Canny"
    BACKGROUND_MASK = "Background Mask"
    ADAPTIVE_THRESHOLD = "Adaptive Threshold"
    GRADIENT_SOBEL = "Gradient (Sobel)"
    CORNER_HARRIS = "Harris Corners"
    HOUGH_RECT = "Hough Rectangle"
    MORPH_GRADIENT = "Morphology Gradient"
    LSD_RECT = "LSD Rectangle"


class FailureReason(Enum):
    """Machine-readable failure causes for UI/debug diagnostics."""

    NONE = "none"
    LOAD_FAILED = "load_failed"
    TOO_SMALL = "too_small"
    NO_BOUNDARY = "no_boundary"
    INVALID_REGION = "invalid_region"
    OUT_OF_MEMORY = "out_of_memory"
    ERROR = "error"


@dataclass
class CropResult:
    """Result of image cropping operation."""

    success: bool
    image: Optional[np.ndarray] = None
    message: str = ""
    detection_stage: Optional[DetectionStage] = None
    contour_points: Optional[np.ndarray] = None
    confidence: float = 0.0
    debug_dir: Optional[str] = None
    original_size: Tuple[int, int] = (0, 0)
    cropped_size: Tuple[int, int] = (0, 0)
    failure_reason: FailureReason = FailureReason.NONE
    stage_scores: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PreviewProcessResult:
    """Result bundle for preview rendering."""

    original_preview: Optional[np.ndarray]
    overlay_preview: Optional[np.ndarray]
    crop_result: CropResult
    message: str = ""


__all__ = [
    "DetectionStage",
    "FailureReason",
    "CropResult",
    "PreviewProcessResult",
]
