from __future__ import annotations

import logging

from ._detect_contours import ImageContourSelectionMixin
from ._detect_loading import ImageLoadAndClaheMixin
from ._detect_pipeline import ImageDetectionPipelineMixin
from ._detect_stages import ImageDetectionStageMixin

logger = logging.getLogger(__name__)


class ImageDetectionMixin(
    ImageLoadAndClaheMixin,
    ImageContourSelectionMixin,
    ImageDetectionStageMixin,
    ImageDetectionPipelineMixin,
):
    """Legacy combined mixin (prefer ``DetectionPipeline`` composition)."""

    pass
