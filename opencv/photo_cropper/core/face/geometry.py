#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Face-driven image geometry for Photo Cropper.

Single responsibility: pure geometric computations around detected
faces (eye-alignment angle, face-centered crop region, rotation, and
debug visualization). No detection and no model I/O.
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from .types import EyeRect, FaceDetectionResult, FaceRect


def calculate_rotation_angle(eyes: List[EyeRect]) -> float:
    """
    Calculate face rotation angle from eye positions.

    Args:
        eyes: List of detected eyes

    Returns:
        Rotation angle in degrees
    """
    if len(eyes) < 2:
        return 0.0

    # Sort by x coordinate (left eye first)
    eyes_sorted = sorted(eyes, key=lambda e: e.center[0])
    left_eye = eyes_sorted[0]
    right_eye = eyes_sorted[1]

    # Calculate angle
    dx = right_eye.center[0] - left_eye.center[0]
    dy = right_eye.center[1] - left_eye.center[1]

    angle = float(np.degrees(np.arctan2(dy, dx)))

    # Limit to reasonable range
    if abs(angle) > 30:
        return 0.0

    return angle


def calculate_crop_region(
    faces: List[FaceRect],
    image_size: Tuple[int, int],
    *,
    padding_ratio: float = 0.5,
    min_crop_ratio: float = 0.3,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate optimal crop region centered on faces.

    Args:
        faces: List of detected faces
        image_size: (width, height) of image

    Returns:
        Crop region as (x, y, width, height)
    """
    if not faces:
        return None

    img_w, img_h = image_size

    # Find bounding box of all faces
    min_x = min(f.x for f in faces)
    min_y = min(f.y for f in faces)
    max_x = max(f.x + f.width for f in faces)
    max_y = max(f.y + f.height for f in faces)

    # Calculate center of faces
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2

    # Face region dimensions
    face_w = max_x - min_x
    face_h = max_y - min_y

    # Add padding around faces
    padding_x = int(face_w * padding_ratio)
    padding_y = int(face_h * padding_ratio * 1.5)  # More vertical padding

    # Calculate crop size
    crop_w = face_w + padding_x * 2
    crop_h = face_h + padding_y * 2

    # Ensure minimum size
    min_size = int(min(img_w, img_h) * min_crop_ratio)
    crop_w = max(crop_w, min_size)
    crop_h = max(crop_h, min_size)

    # Maintain aspect ratio (use larger dimension)
    if crop_w > crop_h:
        crop_h = crop_w
    else:
        crop_w = crop_h

    # Calculate top-left corner (centered on faces)
    x = center_x - crop_w // 2
    y = center_y - crop_h // 2

    # Adjust to stay within image bounds
    x = max(0, min(x, img_w - crop_w))
    y = max(0, min(y, img_h - crop_h))

    # Final bounds check
    if x + crop_w > img_w:
        crop_w = img_w - x
    if y + crop_h > img_h:
        crop_h = img_h - y

    return (x, y, crop_w, crop_h)


def rotate_to_align_eyes(
    image: np.ndarray,
    angle: float,
    background: Tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """
    Rotate image to align eyes horizontally.

    Args:
        image: Input image
        angle: Rotation angle in degrees
        background: Background fill color

    Returns:
        Rotated image
    """
    if abs(angle) < 0.5:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Rotate
    rotated = cv2.warpAffine(
        image, M, (w, h),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=background
    )

    return rotated


def draw_detections(
    image: np.ndarray,
    result: FaceDetectionResult,
    draw_eyes: bool = True,
    draw_crop: bool = True,
) -> np.ndarray:
    """
    Draw detection results on image.

    Args:
        image: Input image
        result: Detection result
        draw_eyes: Whether to draw eye rectangles
        draw_crop: Whether to draw suggested crop

    Returns:
        Image with drawn detections
    """
    output = image.copy()

    # Draw faces
    for face in result.faces:
        # Face rectangle (green)
        cv2.rectangle(
            output,
            (face.x, face.y),
            (face.x + face.width, face.y + face.height),
            (0, 255, 0), 2
        )

        # Face center point
        cv2.circle(output, face.center, 5, (0, 255, 0), -1)

        # Eyes (blue)
        if draw_eyes:
            for eye in face.eyes:
                cv2.rectangle(
                    output,
                    (eye.x, eye.y),
                    (eye.x + eye.width, eye.y + eye.height),
                    (255, 0, 0), 1
                )

    # Draw suggested crop (red dashed)
    if draw_crop and result.suggested_crop:
        x, y, w, h = result.suggested_crop
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)

    return output


__all__ = [
    'calculate_rotation_angle',
    'calculate_crop_region',
    'rotate_to_align_eyes',
    'draw_detections',
]
