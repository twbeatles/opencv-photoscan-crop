#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Face detection value types for Photo Cropper.

Single responsibility: plain data holders shared by the detector,
its Haar/DNN backends, and geometry helpers. No OpenCV, no I/O.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class FaceRect:
    """Face detection result."""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    eyes: List['EyeRect'] = field(default_factory=list)

    @property
    def center(self) -> Tuple[int, int]:
        """Get face center point."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Get face area."""
        return self.width * self.height

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to (x, y, w, h) tuple."""
        return (self.x, self.y, self.width, self.height)


@dataclass
class EyeRect:
    """Eye detection result."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        """Get eye center point."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class FaceDetectionResult:
    """Complete face detection result."""
    faces: List[FaceRect]
    image_size: Tuple[int, int]
    suggested_crop: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    rotation_angle: float = 0.0

    @property
    def has_faces(self) -> bool:
        """Check if any faces were detected."""
        return len(self.faces) > 0

    @property
    def primary_face(self) -> Optional[FaceRect]:
        """Get the largest/primary face."""
        if not self.faces:
            return None
        return max(self.faces, key=lambda f: f.area)


__all__ = ['FaceRect', 'EyeRect', 'FaceDetectionResult']
