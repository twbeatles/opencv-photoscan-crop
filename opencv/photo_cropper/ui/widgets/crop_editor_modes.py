"""Edit-mode enumerations for the crop editor."""

from enum import Enum

class EditMode(Enum):
    """Editing mode enumeration."""
    NONE = "none"
    RECTANGLE = "rectangle"
    PERSPECTIVE = "perspective"
    ROTATE = "rotate"


class HandlePosition(Enum):
    """Corner handle position."""
    TOP_LEFT = 0
    TOP_RIGHT = 1
    BOTTOM_RIGHT = 2
    BOTTOM_LEFT = 3
    TOP = 4
    RIGHT = 5
    BOTTOM = 6
    LEFT = 7
