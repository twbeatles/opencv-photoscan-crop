#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haar-cascade face/eye detection backend.

Single responsibility: cascade-based detection given pre-loaded
classifiers. Classifier loading and model downloading live elsewhere;
orchestration lives in :mod:`.detector`.
"""

from typing import Any, List

import cv2
import numpy as np

from .types import EyeRect, FaceRect


def _empty_detections(detections: Any) -> bool:
    try:
        return len(detections) == 0
    except Exception:
        return True


def detect_faces_cascade(
    image: np.ndarray,
    face_cascade: Any,
    face_cascade_alt: Any,
    profile_cascade: Any,
    *,
    scale_factor: float = 1.1,
    min_neighbors: int = 5,
    min_face_size: int = 30,
) -> List[FaceRect]:
    """
    Detect faces using Haar cascades.

    Args:
        image: Input BGR image
        face_cascade: Primary frontal-face classifier (or None)
        face_cascade_alt: Alternate frontal-face classifier (or None)
        profile_cascade: Profile-face classifier (or None)

    Returns:
        List of FaceRect objects
    """
    if face_cascade is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply histogram equalization for better detection
    gray = cv2.equalizeHist(gray)

    # Resize for faster detection
    max_dim = 800
    h, w = gray.shape[:2]
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        gray_resized = cv2.resize(gray, None, fx=scale, fy=scale)
    else:
        gray_resized = gray

    # Detect with primary cascade
    detections = face_cascade.detectMultiScale(
        gray_resized,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        minSize=(min_face_size, min_face_size),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    # Try alternate cascade if no detections
    if _empty_detections(detections) and face_cascade_alt is not None:
        detections = face_cascade_alt.detectMultiScale(
            gray_resized,
            scaleFactor=1.15,
            minNeighbors=4,
            minSize=(min_face_size, min_face_size)
        )

    # Try profile face if still no detections
    if _empty_detections(detections) and profile_cascade is not None:
        detections = profile_cascade.detectMultiScale(
            gray_resized,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(min_face_size, min_face_size)
        )

    # Convert to FaceRect objects and scale back
    faces = []
    for (x, y, w_face, h_face) in detections:
        if scale != 1.0:
            x = int(x / scale)
            y = int(y / scale)
            w_face = int(w_face / scale)
            h_face = int(h_face / scale)

        faces.append(FaceRect(
            x=x, y=y,
            width=w_face, height=h_face,
            confidence=0.9  # Cascade doesn't provide confidence
        ))

    return faces


def detect_eyes(gray: np.ndarray, face: FaceRect, eye_cascade: Any) -> List[EyeRect]:
    """
    Detect eyes within a face region.

    Args:
        gray: Grayscale image
        face: Face region
        eye_cascade: Eye classifier (or None)

    Returns:
        List of EyeRect objects
    """
    if eye_cascade is None:
        return []

    # Extract face ROI (upper half where eyes are)
    y_start = face.y
    y_end = face.y + int(face.height * 0.6)
    x_start = face.x
    x_end = face.x + face.width

    # Bounds check
    h, w = gray.shape[:2]
    y_start = max(0, y_start)
    y_end = min(h, y_end)
    x_start = max(0, x_start)
    x_end = min(w, x_end)

    if y_end <= y_start or x_end <= x_start:
        return []

    roi = gray[y_start:y_end, x_start:x_end]

    # Detect eyes
    eye_detections = eye_cascade.detectMultiScale(
        roi,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(20, 20)
    )

    eyes = []
    for (ex, ey, ew, eh) in eye_detections[:2]:  # Max 2 eyes
        eyes.append(EyeRect(
            x=x_start + ex,
            y=y_start + ey,
            width=ew,
            height=eh
        ))

    return eyes


__all__ = ['detect_faces_cascade', 'detect_eyes']
