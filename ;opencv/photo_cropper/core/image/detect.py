# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import os
import cv2
import numpy as np
import logging
import traceback
import json
import time
import math
from typing import Optional, Tuple, List, Dict, Any

from ..settings_model import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
    DebugSettings,
)
from ..advanced import AdvancedImageProcessor, GPUAccelerator
from .types import CropResult, DetectionStage, PreviewProcessResult

logger = logging.getLogger(__name__)


from ._detect_loading import ImageLoadAndClaheMixin
from ._detect_contours import ImageContourSelectionMixin
from ._detect_stages import ImageDetectionStageMixin
from ._detect_pipeline import ImageDetectionPipelineMixin


class ImageDetectionMixin(
    ImageLoadAndClaheMixin,
    ImageContourSelectionMixin,
    ImageDetectionStageMixin,
    ImageDetectionPipelineMixin,
):
    pass
