"""Before/After Compare Widget for Photo Cropper.

Compatibility facade: the implementation now lives in focused modules
(`compare_conversions`, `compare_modes`, `compare_views`,
`compare_panel`). All public names are re-exported here.
"""

from .compare_conversions import numpy_to_qpixmap
from .compare_modes import CompareMode
from .compare_panel import BeforeAfterCompareWidget
from .compare_views import (
    CompareGraphicsView,
    OverlayCompareWidget,
    SliderCompareWidget,
)

__all__ = [
    "numpy_to_qpixmap",
    "CompareMode",
    "CompareGraphicsView",
    "SliderCompareWidget",
    "OverlayCompareWidget",
    "BeforeAfterCompareWidget",
]
