"""Compare display modes."""

from enum import Enum

class CompareMode(Enum):
    """Comparison mode enumeration."""
    SLIDER = "slider"      # Horizontal slider divide
    SIDE_BY_SIDE = "side"  # Side by side
    OVERLAY = "overlay"    # Fade overlay
    SPLIT_V = "split_v"    # Vertical split
    TOGGLE = "toggle"      # Toggle between images
