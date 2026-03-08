#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Face Detector for Photo Cropper v9.0.

Provides OpenCV-based face detection and auto-correction:
- Haar cascade face/eye detection
- DNN-based face detection (optional, more accurate)
- Face-centered crop adjustment
- Auto rotation based on eye positions
"""

import cv2
import numpy as np
import logging
import os
import platform
import hashlib
import tempfile
import urllib.request
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


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

    # DNN model metadata (OpenCV face detector, Caffe)
    DNN_PROTOTXT_URL = (
        "https://raw.githubusercontent.com/opencv/opencv/master/"
        "samples/dnn/face_detector/deploy.prototxt"
    )
    DNN_MODEL_URL = (
        "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
        "dnn_samples_face_detector_20180205_fp16/"
        "res10_300x300_ssd_iter_140000_fp16.caffemodel"
    )
    DNN_PROTOTXT_SHA256 = (
        "dcd661dc48fc9de0a341db1f666a2164ea63a67265c7f779bc12d6b3f2fa67e9"
    )
    DNN_MODEL_SHA256 = (
        "510ffd2471bd81e3fcc88a5beb4eae4fb445ccf8333ebc54e7302b83f4158a76"
    )
    DNN_PROTOTXT_FILENAME = "deploy.prototxt"
    DNN_MODEL_FILENAME = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
    DNN_CONFIDENCE_THRESHOLD = 0.55
    _DNN_CACHE: Optional[Tuple[str, str]] = None
    
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
        system = platform.system()
        home = os.path.expanduser("~")
        if system == "Windows":
            base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or home
        elif system == "Darwin":
            base = os.path.join(home, "Library", "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")

        model_dir = os.path.join(base, "PhotoCropper", "models")
        os.makedirs(model_dir, exist_ok=True)
        return model_dir

    @staticmethod
    def _sha256_file(path: str) -> Optional[str]:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest().lower()
        except Exception:
            return None

    @classmethod
    def _is_valid_model_file(cls, path: str, expected_sha256: str) -> bool:
        if not path or not os.path.exists(path):
            return False
        actual = cls._sha256_file(path)
        return actual == expected_sha256.lower()

    @classmethod
    def _download_file_atomic(
        cls,
        url: str,
        dest_path: str,
        expected_sha256: str,
        timeout: int = 20,
    ) -> None:
        """Download and atomically replace target file after checksum validation."""
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=os.path.basename(dest_path) + ".",
            suffix=".tmp",
            dir=os.path.dirname(dest_path),
        )
        os.close(fd)
        try:
            hasher = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=timeout) as response, open(
                tmp_path, "wb"
            ) as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    hasher.update(chunk)

            digest = hasher.hexdigest().lower()
            if digest != expected_sha256.lower():
                raise ValueError(
                    f"Checksum mismatch for {os.path.basename(dest_path)}: {digest}"
                )

            os.replace(tmp_path, dest_path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    @classmethod
    def _ensure_model_file(
        cls,
        dest_path: str,
        url: str,
        expected_sha256: str,
    ) -> str:
        """Ensure model file exists and checksum is valid."""
        if cls._is_valid_model_file(dest_path, expected_sha256):
            return dest_path

        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass

        cls._download_file_atomic(url, dest_path, expected_sha256)
        return dest_path

    @classmethod
    def _ensure_dnn_models(cls) -> Tuple[str, str]:
        """Ensure DNN model files are available locally."""
        if cls._DNN_CACHE:
            ptxt, pmodel = cls._DNN_CACHE
            if cls._is_valid_model_file(ptxt, cls.DNN_PROTOTXT_SHA256) and cls._is_valid_model_file(
                pmodel, cls.DNN_MODEL_SHA256
            ):
                return cls._DNN_CACHE

        model_dir = cls._get_model_cache_dir()
        prototxt_path = os.path.join(model_dir, cls.DNN_PROTOTXT_FILENAME)
        model_path = os.path.join(model_dir, cls.DNN_MODEL_FILENAME)

        prototxt_path = cls._ensure_model_file(
            prototxt_path,
            cls.DNN_PROTOTXT_URL,
            cls.DNN_PROTOTXT_SHA256,
        )
        model_path = cls._ensure_model_file(
            model_path,
            cls.DNN_MODEL_URL,
            cls.DNN_MODEL_SHA256,
        )
        cls._DNN_CACHE = (prototxt_path, model_path)
        return prototxt_path, model_path

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
        if self._dnn_net is None:
            return []

        src = image
        h, w = src.shape[:2]
        scale = 1.0
        max_dim = 1000
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            src = cv2.resize(src, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        sh, sw = src.shape[:2]
        blob = cv2.dnn.blobFromImage(
            src,
            scalefactor=1.0,
            size=(300, 300),
            mean=(104.0, 177.0, 123.0),
            swapRB=False,
            crop=False,
        )

        self._dnn_net.setInput(blob)
        detections = self._dnn_net.forward()
        if detections is None or detections.size == 0:
            return []

        faces: List[FaceRect] = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < self.DNN_CONFIDENCE_THRESHOLD:
                continue

            box = detections[0, 0, i, 3:7] * np.array([sw, sh, sw, sh], dtype=np.float32)
            x1, y1, x2, y2 = box.astype(np.int32)
            x1 = max(0, min(x1, sw - 1))
            y1 = max(0, min(y1, sh - 1))
            x2 = max(0, min(x2, sw))
            y2 = max(0, min(y2, sh))
            bw = max(0, x2 - x1)
            bh = max(0, y2 - y1)
            if bw < self.min_face_size or bh < self.min_face_size:
                continue

            if scale != 1.0:
                x1 = int(x1 / scale)
                y1 = int(y1 / scale)
                bw = int(bw / scale)
                bh = int(bh / scale)

            faces.append(
                FaceRect(
                    x=x1,
                    y=y1,
                    width=bw,
                    height=bh,
                    confidence=confidence,
                )
            )

        if len(faces) <= 1:
            return faces

        boxes = [[f.x, f.y, f.width, f.height] for f in faces]
        confidences = [float(f.confidence) for f in faces]
        idxs = cv2.dnn.NMSBoxes(
            boxes,
            confidences,
            score_threshold=self.DNN_CONFIDENCE_THRESHOLD,
            nms_threshold=0.3,
        )
        if idxs is None or len(idxs) == 0:
            return faces

        kept = []
        for idx in np.array(idxs).reshape(-1):
            if 0 <= int(idx) < len(faces):
                kept.append(faces[int(idx)])
        return kept
    
    def _detect_faces_cascade(self, image: np.ndarray) -> List[FaceRect]:
        """
        Detect faces using Haar cascade.
        
        Args:
            image: Input BGR image
            
        Returns:
            List of FaceRect objects
        """
        if self._face_cascade is None:
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
        detections = self._face_cascade.detectMultiScale(
            gray_resized,
            scaleFactor=self.SCALE_FACTOR,
            minNeighbors=self.MIN_NEIGHBORS,
            minSize=(self.min_face_size, self.min_face_size),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Try alternate cascade if no detections
        if len(detections) == 0 and self._face_cascade_alt is not None:
            detections = self._face_cascade_alt.detectMultiScale(
                gray_resized,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(self.min_face_size, self.min_face_size)
            )
        
        # Try profile face if still no detections
        if len(detections) == 0 and self._profile_cascade is not None:
            detections = self._profile_cascade.detectMultiScale(
                gray_resized,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(self.min_face_size, self.min_face_size)
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
    
    def _detect_eyes(self, gray: np.ndarray, face: FaceRect) -> List[EyeRect]:
        """
        Detect eyes within a face region.
        
        Args:
            gray: Grayscale image
            face: Face region
            
        Returns:
            List of EyeRect objects
        """
        if self._eye_cascade is None:
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
        eye_detections = self._eye_cascade.detectMultiScale(
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
    
    def _calculate_rotation_angle(self, eyes: List[EyeRect]) -> float:
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
        
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Limit to reasonable range
        if abs(angle) > 30:
            return 0.0
        
        return angle
    
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
        padding_x = int(face_w * self.FACE_PADDING_RATIO)
        padding_y = int(face_h * self.FACE_PADDING_RATIO * 1.5)  # More vertical padding
        
        # Calculate crop size
        crop_w = face_w + padding_x * 2
        crop_h = face_h + padding_y * 2
        
        # Ensure minimum size
        min_size = int(min(img_w, img_h) * self.MIN_CROP_RATIO)
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


# Singleton instance
_detector_instance: Optional[FaceDetector] = None


def get_face_detector(use_dnn: bool = False, min_face_size: int = 30) -> FaceDetector:
    """Get global face detector instance."""
    global _detector_instance
    normalized_size = max(20, min(500, int(min_face_size)))
    if (
        _detector_instance is None
        or _detector_instance.use_dnn != bool(use_dnn)
        or _detector_instance.min_face_size != normalized_size
    ):
        _detector_instance = FaceDetector(
            use_dnn=bool(use_dnn),
            min_face_size=normalized_size,
        )
    return _detector_instance
