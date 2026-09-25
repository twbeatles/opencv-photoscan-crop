"""Crop Editor Widget for Photo Cropper.

Compatibility facade: the implementation now lives in focused modules
(`crop_editor_modes`, `crop_editor_conversions`, `crop_editor_view`,
`crop_editor_panel`, `rotation_widget`). All public names are
re-exported here.
"""

from .crop_editor_conversions import numpy_to_qpixmap
from .crop_editor_modes import EditMode, HandlePosition
from .crop_editor_panel import CropEditorWidget
from .crop_editor_view import CropEditorView
from .rotation_widget import RotationWidget

__all__ = [
    "numpy_to_qpixmap",
    "EditMode",
    "HandlePosition",
    "CropEditorView",
    "CropEditorWidget",
    "RotationWidget",
]
