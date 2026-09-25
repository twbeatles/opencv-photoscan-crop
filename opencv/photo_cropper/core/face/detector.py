#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Face Detector for Photo Cropper v9.0.

Orchestrator: owns backend selection (Haar vs DNN), classifier loading,
and the public ``detect()`` pipeline. The work itself lives in focused
modules — :mod:`.types` (values), :mod:`.model_store` (DNN downloads),
:mod:`.detect_haar` / :mod:`.detect_dnn` (backends), :mod:`.geometry`
(crop/rotation/visualization) — and the singleton in :mod:`.factory`.
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List

from .detect_dnn import detect_faces_dnn
from .detect_haar import detect_eyes, detect_faces_cascade
from .geometry import (
    calculate_crop_region,
    calculate_rotation_angle,
    draw_detections as _draw_detections,
    rotate_to_align_eyes as _rotate_to_align_eyes,
)
from .factory import get_face_detector, reset_face_detector_for_tests
from .model_store import (
    _sha256_file as _hash_file,
    DNN_CONFIDENCE_THRESHOLD,
    DNN_MODEL_FILENAME,
    DNN_MODEL_SHA256,
    DNN_MODEL_URL,
    DNN_PROTOTXT_FILENAME,
    DNN_PROTOTXT_SHA256,
    DNN_PROTOTXT_URL,
    download_file_atomic,
    ensure_dnn_models,
    ensure_model_file,
    get_model_cache_dir,
    is_valid_model_file,
)
from .types import EyeRect, FaceDetectionResult, FaceRect

logger = logging.getLogger(__name__)


class FaceDetector:
    """
    OpenCV-based face detector.

    Features:
    - Haar cascade detection (fast)
    - DNN detection (accurate, optional)
    - Eye detection for rotation correction
    - Face-centered crop suggestion
    """

    # Cascade paths (bundled with OpenCV)
    _cv2_data = getattr(cv2, "data", None)
    _haarcascades = getattr(_cv2_data, "haarcascades", "")
    FACE_CASCADE = _haarcascades + 'haarcascade_frontalface_default.xml'
    FACE_CASCADE_ALT = _haarcascades + 'haarcascade_frontalface_alt2.xml'
    EYE_CASCADE = _haarcascades + 'haarcascade_eye.xml'
    PROFILE_CASCADE = _haarcascades + 'haarcascade_profileface.xml'

    # DNN model metadata (canonical values live in model_store)
    DNN_PROTOTXT_URL = DNN_PROTOTXT_URL
    DNN_MODEL_URL = DNN_MODEL_URL
    DNN_PROTOTXT_SHA256 = DNN_PROTOTXT_SHA256
    DNN_MODEL_SHA256 = DNN_MODEL_SHA256
    DNN_PROTOTXT_FILENAME = DNN_PROTOTXT_FILENAME
    DNN_MODEL_FILENAME = DNN_MODEL_FILENAME
    DNN_CONFIDENCE_THRESHOLD = DNN_CONFIDENCE_THRESHOLD

    # Detection parameters
    SCALE_FACTOR = 1.1
    MIN_NEIGHBORS = 5
    MIN_FACE_SIZE = (30, 30)

    # Crop parameters
    FACE_PADDING_RATIO = 0.5  # Extra space around face
    MIN_CROP_RATIO = 0.3  # Minimum crop size relative to image

    def __init__(self, use_dnn: bool = False, min_face_size: int = 30):
        """
        Initialize face detector.

        Args:
            use_dnn: Whether to use DNN for face detection
            min_face_size: Minimum detected face size in pixels
        """
        self.use_dnn = bool(use_dnn)
        self.min_face_size = max(20, min(500, int(min_face_size)))
        self._face_cascade = None
        self._face_cascade_alt = None
        self._eye_cascade = None
        self._profile_cascade = None
        self._dnn_net = None

        self._load_classifiers()

    def _load_classifiers(self):
        """Load OpenCV cascade classifiers."""
        try:
            self._face_cascade = cv2.CascadeClassifier(self.FACE_CASCADE)
            self._face_cascade_alt = cv2.CascadeClassifier(self.FACE_CASCADE_ALT)
            self._eye_cascade = cv2.CascadeClassifier(self.EYE_CASCADE)
            self._profile_cascade = cv2.CascadeClassifier(self.PROFILE_CASCADE)

            if self._face_cascade.empty():
                logger.warning("Failed to load primary face cascade")
                self._face_cascade = None

            if self.use_dnn:
                self._load_dnn_detector()

            logger.debug("Face detection classifiers loaded successfully")
        except Exception as e:
            logger.error(f"Error loading face classifiers: {e}")

    @staticmethod
    def _get_model_cache_dir() -> str:
        """Get OS-specific model cache directory."""
        return get_model_cache_dir()

    @staticmethod
    def _sha256_file(path: str) -> Optional[str]:
        return _hash_file(path)

    @classmethod
    def _is_valid_model_file(cls, path: str, expected_sha256: str) -> bool:
        return is_valid_model_file(path, expected_sha256)

    @classmethod
    def _download_file_atomic(
        cls,
        url: str,
        dest_path: str,
        expected_sha256: str,
        timeout: int = 20,
    ) -> None:
        """Download and atomically replace target file after checksum validation."""
        download_file_atomic(url, dest_path, expected_sha256, timeout=timeout)

    @classmethod
    def _ensure_model_file(
        cls,
        dest_path: str,
        url: str,
        expected_sha256: str,
    ) -> str:
        """Ensure model file exists and checksum is valid."""
        return ensure_model_file(dest_path, url, expected_sha256)

    @classmethod
    def _ensure_dnn_models(cls) -> Tuple[str, str]:
        """Ensure DNN model files are available locally."""
        return ensure_dnn_models()

    def _load_dnn_detector(self) -> None:
        """Load DNN detector with automatic download and fallback safety."""
        try:
            prototxt_path, model_path = self._ensure_dnn_models()
            self._dnn_net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
            logger.info("DNN face detector loaded")
        except Exception as e:
            self._dnn_net = None
            logger.warning(
                "DNN face detector unavailable, falling back to Haar cascade: %s",
                e,
            )

    def detect(self, image: np.ndarray,
               detect_eyes: bool = True,
               suggest_crop: bool = True) -> FaceDetectionResult:
        """
        Detect faces in image.

        Args:
            image: Input BGR image
            detect_eyes: Whether to detect eyes within faces
            suggest_crop: Whether to suggest face-centered crop

        Returns:
            FaceDetectionResult with all detected faces
        """
        if image is None or image.size == 0:
            return FaceDetectionResult(faces=[], image_size=(0, 0))

        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 1:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        h, w = image.shape[:2]

        # Detect faces
        faces = []
        if self.use_dnn and self._dnn_net is not None:
            try:
                faces = self._detect_faces_dnn(image)
            except Exception as e:
                logger.debug(f"DNN detection failed, using Haar fallback: {e}")
                faces = []

        if not faces:
            faces = self._detect_faces_cascade(image)

        # Detect eyes if requested
        if detect_eyes and faces:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            for face in faces:
                face.eyes = self._detect_eyes(gray, face)

        # Create result
        result = FaceDetectionResult(
            faces=faces,
            image_size=(w, h)
        )

        # Calculate rotation angle from the primary face for stability.
        primary = result.primary_face
        if primary is not None and primary.eyes:
            result.rotation_angle = self._calculate_rotation_angle(primary.eyes)

        # Suggest crop if requested
        if suggest_crop and faces:
            result.suggested_crop = self._calculate_crop_region(faces, (w, h))

        return result

    def _detect_faces_dnn(self, image: np.ndarray) -> List[FaceRect]:
        """Detect faces using OpenCV DNN (SSD/Caffe)."""
        return detect_faces_dnn(
            image,
            self._dnn_net,
            min_face_size=self.min_face_size,
            confidence_threshold=self.DNN_CONFIDENCE_THRESHOLD,
        )

    def _detect_faces_cascade(self, image: np.ndarray) -> List[FaceRect]:
        """
        Detect faces using Haar cascade.

        Args:
            image: Input BGR image

        Returns:
            List of FaceRect objects
        """
        return detect_faces_cascade(
            image,
            self._face_cascade,
            self._face_cascade_alt,
            self._profile_cascade,
            scale_factor=self.SCALE_FACTOR,
            min_neighbors=self.MIN_NEIGHBORS,
            min_face_size=self.min_face_size,
        )

    def _detect_eyes(self, gray: np.ndarray, face: FaceRect) -> List[EyeRect]:
        """
        Detect eyes within a face region.

        Args:
            gray: Grayscale image
            face: Face region

        Returns:
            List of EyeRect objects
        """
        return detect_eyes(gray, face, self._eye_cascade)

    def _calculate_rotation_angle(self, eyes: List[EyeRect]) -> float:
        """
        Calculate face rotation angle from eye positions.

        Args:
            eyes: List of detected eyes

        Returns:
            Rotation angle in degrees
        """
        return calculate_rotation_angle(eyes)

    def _calculate_crop_region(self, faces: List[FaceRect],
                               image_size: Tuple[int, int]) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculate optimal crop region centered on faces.

        Args:
            faces: List of detected faces
            image_size: (width, height) of image

        Returns:
            Crop region as (x, y, width, height)
        """
        return calculate_crop_region(
            faces,
            image_size,
            padding_ratio=self.FACE_PADDING_RATIO,
            min_crop_ratio=self.MIN_CROP_RATIO,
        )

    def rotate_to_align_eyes(self, image: np.ndarray,
                             angle: float,
                             background: Tuple[int, int, int] = (255, 255, 255)
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
        return _rotate_to_align_eyes(image, angle, background)

    def draw_detections(self, image: np.ndarray,
                        result: FaceDetectionResult,
                        draw_eyes: bool = True,
                        draw_crop: bool = True) -> np.ndarray:
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
        return _draw_detections(
            image, result, draw_eyes=draw_eyes, draw_crop=draw_crop
        )


# `get_face_detector` / `reset_face_detector_for_tests` are imported at the
# top (from .factory) so `face.detector` remains a complete import surface.
__all__ = [
    'FaceRect',
    'EyeRect',
    'FaceDetectionResult',
    'FaceDetector',
    'get_face_detector',
    'reset_face_detector_for_tests',
]
