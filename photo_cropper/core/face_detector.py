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
    FACE_CASCADE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    FACE_CASCADE_ALT = cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
    EYE_CASCADE = cv2.data.haarcascades + 'haarcascade_eye.xml'
    PROFILE_CASCADE = cv2.data.haarcascades + 'haarcascade_profileface.xml'
    
    # Detection parameters
    SCALE_FACTOR = 1.1
    MIN_NEIGHBORS = 5
    MIN_FACE_SIZE = (30, 30)
    
    # Crop parameters
    FACE_PADDING_RATIO = 0.5  # Extra space around face
    MIN_CROP_RATIO = 0.3  # Minimum crop size relative to image
    
    def __init__(self, use_dnn: bool = False):
        """
        Initialize face detector.
        
        Args:
            use_dnn: Whether to use DNN for face detection
        """
        self.use_dnn = use_dnn
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
            
            logger.debug("Face detection classifiers loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading face classifiers: {e}")
    
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
        
        h, w = image.shape[:2]
        
        # Detect faces
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
        
        # Calculate rotation angle from eyes
        if faces and faces[0].eyes:
            result.rotation_angle = self._calculate_rotation_angle(faces[0].eyes)
        
        # Suggest crop if requested
        if suggest_crop and faces:
            result.suggested_crop = self._calculate_crop_region(faces, (w, h))
        
        return result
    
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
            minSize=self.MIN_FACE_SIZE,
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Try alternate cascade if no detections
        if len(detections) == 0 and self._face_cascade_alt is not None:
            detections = self._face_cascade_alt.detectMultiScale(
                gray_resized,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=self.MIN_FACE_SIZE
            )
        
        # Try profile face if still no detections
        if len(detections) == 0 and self._profile_cascade is not None:
            detections = self._profile_cascade.detectMultiScale(
                gray_resized,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=self.MIN_FACE_SIZE
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
                               image_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
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


def get_face_detector() -> FaceDetector:
    """Get global face detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = FaceDetector()
    return _detector_instance
