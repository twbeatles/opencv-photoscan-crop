#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Classifier for Photo Cropper v9.0.

Provides OpenCV-based automatic image classification:
- Portrait detection (face ratio analysis)
- Document detection (edge/line analysis)
- Landscape detection (color/texture analysis)
- Black & white detection (color histogram)
"""

import cv2
import numpy as np
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ImageCategory(Enum):
    """Image category enumeration."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    DOCUMENT = "document"
    BLACKWHITE = "blackwhite"
    OTHER = "other"


@dataclass
class ClassificationResult:
    """Result of image classification."""
    category: ImageCategory
    confidence: float
    face_count: int = 0
    is_grayscale: bool = False
    document_score: float = 0.0
    details: Dict[str, float] = field(default_factory=dict)


class ImageClassifier:
    """
    OpenCV-based image classifier.
    
    Uses multiple heuristics to classify images:
    - Face detection for portraits
    - Edge/line detection for documents
    - Color histogram analysis for B&W photos
    - Texture/color distribution for landscapes
    """
    
    # Cascade classifier paths (bundled with OpenCV)
    _cv2_data = getattr(cv2, "data", None)
    _haarcascades = getattr(_cv2_data, "haarcascades", "")
    FACE_CASCADE_PATH = _haarcascades + 'haarcascade_frontalface_default.xml'
    EYE_CASCADE_PATH = _haarcascades + 'haarcascade_eye.xml'
    
    # Classification thresholds
    FACE_AREA_THRESHOLD = 0.03  # Face area > 3% of image = likely portrait
    DOCUMENT_EDGE_THRESHOLD = 0.15  # Edge density threshold
    GRAYSCALE_SATURATION_THRESHOLD = 15  # Low saturation = B&W
    LINE_DENSITY_THRESHOLD = 0.1  # For document detection
    
    def __init__(self, use_dnn: bool = False):
        """
        Initialize classifier.
        
        Args:
            use_dnn: Whether to use DNN for face detection (more accurate but slower)
        """
        self.use_dnn = use_dnn
        self._face_cascade = None
        self._eye_cascade = None
        self._dnn_net = None
        self._custom_model_notice_logged = False
        
        self._load_classifiers()
    
    def _load_classifiers(self):
        """Load OpenCV classifiers."""
        try:
            self._face_cascade = cv2.CascadeClassifier(self.FACE_CASCADE_PATH)
            self._eye_cascade = cv2.CascadeClassifier(self.EYE_CASCADE_PATH)
            
            if self._face_cascade.empty():
                logger.warning("Failed to load face cascade classifier")
                self._face_cascade = None
                
        except Exception as e:
            logger.error(f"Error loading classifiers: {e}")
    
    @staticmethod
    def _normalize_model(model: str) -> str:
        """Normalize classification model name, keeping legacy aliases compatible."""
        mode = str(model or "basic").lower()
        if mode not in ("basic", "advanced", "custom"):
            mode = "basic"
        return mode

    @staticmethod
    def _normalize_input_image(image: np.ndarray) -> np.ndarray:
        """Normalize input image into BGR layout."""
        if image is None:
            return image
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 1:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image

    def classify(self, image: np.ndarray, model: str = "basic") -> ClassificationResult:
        """
        Classify an image into categories.
        
        Args:
            image: Input image (BGR/Gray)
            model: Classification profile ("basic", "advanced", legacy "custom" alias)
            
        Returns:
            ClassificationResult with category and confidence
        """
        if image is None or image.size == 0:
            return ClassificationResult(
                category=ImageCategory.OTHER,
                confidence=0.0
            )

        model = self._normalize_model(model)
        if model == "custom":
            if not self._custom_model_notice_logged:
                logger.info(
                    "Classification model 'custom' currently maps to 'advanced' profile."
                )
                self._custom_model_notice_logged = True
            model = "advanced"

        image = self._normalize_input_image(image)
        
        # Collect all metrics
        metrics: Dict[str, float] = {}
        
        # 1. Check if grayscale
        is_grayscale, saturation_mean = self._analyze_color(image)
        metrics['saturation'] = saturation_mean
        
        # 2. Detect faces
        faces = self._detect_faces(image, model=model)
        face_area_ratio = self._calculate_face_area_ratio(faces, image.shape)
        metrics['face_area_ratio'] = face_area_ratio
        metrics['face_count'] = len(faces)
        
        # 3. Analyze document features
        doc_score = self._analyze_document_features(image, model=model)
        metrics['document_score'] = doc_score
        
        # 4. Analyze scene/texture
        scene_score = self._analyze_scene(image, model=model)
        metrics['scene_score'] = scene_score
        
        # Classification logic
        if model == "advanced":
            category, confidence = self._determine_category_advanced(
                is_grayscale=is_grayscale,
                face_area_ratio=face_area_ratio,
                face_count=len(faces),
                doc_score=doc_score,
                scene_score=scene_score,
            )
        else:
            category, confidence = self._determine_category_basic(
                is_grayscale=is_grayscale,
                face_area_ratio=face_area_ratio,
                face_count=len(faces),
                doc_score=doc_score,
                scene_score=scene_score,
            )
        
        return ClassificationResult(
            category=category,
            confidence=confidence,
            face_count=len(faces),
            is_grayscale=is_grayscale,
            document_score=doc_score,
            details=metrics
        )
    
    def _analyze_color(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Analyze if image is grayscale/B&W.
        
        Args:
            image: Input BGR image
            
        Returns:
            Tuple of (is_grayscale, mean_saturation)
        """
        if len(image.shape) < 3:
            return True, 0.0
        
        # Convert to HSV and analyze saturation
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        mean_saturation = float(np.mean(np.asarray(saturation, dtype=np.float32)))
        
        # Low saturation indicates grayscale
        is_grayscale = mean_saturation < self.GRAYSCALE_SATURATION_THRESHOLD
        
        return is_grayscale, mean_saturation
    
    def _detect_faces(
        self, image: np.ndarray, model: str = "basic"
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in image using Haar cascade.
        
        Args:
            image: Input BGR image
            model: Classification model profile
            
        Returns:
            List of face rectangles (x, y, w, h)
        """
        if self._face_cascade is None:
            return []

        # Convert to grayscale for detection
        if image.ndim == 2:
            gray = image
        elif image.ndim == 3 and image.shape[2] == 1:
            gray = image[:, :, 0]
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize for faster detection if image is large
        max_dim = 800
        h, w = gray.shape[:2]
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            gray = cv2.resize(gray, None, fx=scale, fy=scale)
        
        # Detect faces
        min_neighbors = 6 if model == "advanced" else 5
        detected_faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=min_neighbors,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        faces: List[Tuple[int, int, int, int]] = []
        for face in detected_faces:
            coords = np.asarray(face).reshape(-1)
            if coords.size < 4:
                continue
            x, y, w_face, h_face = [int(v) for v in coords[:4]]
            if scale != 1.0:
                x = int(x / scale)
                y = int(y / scale)
                w_face = int(w_face / scale)
                h_face = int(h_face / scale)
            faces.append((x, y, w_face, h_face))

        return faces
    
    def _calculate_face_area_ratio(
        self,
        faces: List[Tuple[int, int, int, int]],
        image_shape: Tuple[int, ...],
    ) -> float:
        """
        Calculate total face area as ratio of image area.
        
        Args:
            faces: List of face rectangles
            image_shape: Image shape (h, w, c)
            
        Returns:
            Face area ratio (0.0 to 1.0)
        """
        if not faces:
            return 0.0
        
        image_area = image_shape[0] * image_shape[1]
        face_area = sum(w * h for (x, y, w, h) in faces)
        
        return min(1.0, face_area / image_area)
    
    def _analyze_document_features(
        self, image: np.ndarray, model: str = "basic"
    ) -> float:
        """
        Analyze if image has document-like features.
        
        Checks for:
        - High edge density
        - Horizontal/vertical line dominance
        - Text-like patterns
        
        Args:
            image: Input BGR image
            
        Returns:
            Document score (0.0 to 1.0)
        """
        # Convert to grayscale
        if image.ndim == 2:
            gray = image
        elif image.ndim == 3 and image.shape[2] == 1:
            gray = image[:, :, 0]
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize for faster processing
        max_dim = 500
        h, w = gray.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            gray = cv2.resize(gray, None, fx=scale, fy=scale)
        
        # Edge detection
        if model == "advanced":
            edges = cv2.Canny(gray, 40, 120)
        else:
            edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        
        # Line detection using Hough transform
        line_threshold = 45 if model == "advanced" else 50
        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            line_threshold,
            minLineLength=30,
            maxLineGap=10,
        )
        
        line_score = 0.0
        if lines is not None:
            # Calculate horizontal/vertical line ratio
            h_lines = 0
            v_lines = 0
            for line in lines:
                line_points = np.asarray(line).reshape(-1)
                if line_points.size < 4:
                    continue
                x1, y1, x2, y2 = [float(v) for v in line_points[:4]]
                angle = abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
                if angle < 15 or angle > 165:
                    h_lines += 1
                elif 75 < angle < 105:
                    v_lines += 1
            
            total_lines = len(lines)
            hv_ratio = (h_lines + v_lines) / total_lines if total_lines > 0 else 0
            line_score = min(1.0, hv_ratio * (total_lines / 50))
        
        # Combine scores
        doc_score = (edge_density * 2 + line_score) / 3
        return min(1.0, doc_score)
    
    def _analyze_scene(self, image: np.ndarray, model: str = "basic") -> float:
        """
        Analyze scene characteristics for landscape detection.
        
        Checks for:
        - Color variety
        - Large homogeneous regions (sky, ground)
        - Natural textures
        
        Args:
            image: Input BGR image
            
        Returns:
            Landscape score (0.0 to 1.0)
        """
        # Resize for faster processing
        image = self._normalize_input_image(image)
        small = cv2.resize(image, (200, 200))
        
        # Convert to LAB for better color analysis
        lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
        
        # Calculate color variance
        color_std = np.std(np.asarray(lab, dtype=np.float32), axis=(0, 1))
        color_variety = float(np.mean(np.asarray(color_std, dtype=np.float32)) / 50.0)
        
        # Check for sky-like regions (blue hue, high brightness)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        sky_mask = cv2.inRange(
            hsv,
            np.array([90, 30, 100], dtype=np.uint8),
            np.array([130, 255, 255], dtype=np.uint8),
        )
        sky_ratio = np.count_nonzero(sky_mask) / sky_mask.size
        
        # Check for green regions (nature)
        green_mask = cv2.inRange(
            hsv,
            np.array([35, 40, 40], dtype=np.uint8),
            np.array([85, 255, 255], dtype=np.uint8),
        )
        green_ratio = np.count_nonzero(green_mask) / green_mask.size
        
        # Combine scores
        if model == "advanced":
            scene_score = (
                color_variety * 0.45
                + sky_ratio * 0.30
                + green_ratio * 0.25
            )
        else:
            scene_score = (
                color_variety * 0.4
                + sky_ratio * 0.3
                + green_ratio * 0.3
            )
        
        return min(1.0, scene_score)
    
    def _determine_category_basic(
        self,
        is_grayscale: bool,
        face_area_ratio: float,
        face_count: int,
        doc_score: float,
        scene_score: float,
    ) -> Tuple[ImageCategory, float]:
        """
        Determine final category based on all metrics.
        
        Args:
            is_grayscale: Whether image is B&W
            face_area_ratio: Face area as ratio of image
            face_count: Number of faces detected
            doc_score: Document feature score
            scene_score: Landscape/scene score
            
        Returns:
            Tuple of (category, confidence)
        """
        scores: Dict[ImageCategory, float] = {}
        
        # Portrait scoring
        if face_count > 0:
            if face_area_ratio > 0.1:
                scores[ImageCategory.PORTRAIT] = 0.9
            elif face_area_ratio > self.FACE_AREA_THRESHOLD:
                scores[ImageCategory.PORTRAIT] = 0.7
            else:
                scores[ImageCategory.PORTRAIT] = 0.4
        else:
            scores[ImageCategory.PORTRAIT] = 0.0
        
        # Document scoring
        if doc_score > 0.3:
            scores[ImageCategory.DOCUMENT] = min(0.9, doc_score * 1.5)
        else:
            scores[ImageCategory.DOCUMENT] = doc_score
        
        # B&W scoring (only if actually grayscale and not document)
        if is_grayscale and doc_score < 0.3:
            scores[ImageCategory.BLACKWHITE] = 0.8
        else:
            scores[ImageCategory.BLACKWHITE] = 0.0
        
        # Landscape scoring
        if scene_score > 0.3 and face_count == 0 and doc_score < 0.2:
            scores[ImageCategory.LANDSCAPE] = min(0.85, scene_score * 1.3)
        else:
            scores[ImageCategory.LANDSCAPE] = scene_score * 0.5
        
        # Other as fallback
        scores[ImageCategory.OTHER] = 0.3
        
        # Determine winner
        best_category = max(scores, key=lambda category: scores[category])
        confidence = scores[best_category]
        
        # If confidence is too low, default to OTHER
        if confidence < 0.4:
            best_category = ImageCategory.OTHER
            confidence = 1.0 - max(scores.values())
        
        return best_category, confidence

    def _determine_category_advanced(
        self,
        is_grayscale: bool,
        face_area_ratio: float,
        face_count: int,
        doc_score: float,
        scene_score: float,
    ) -> Tuple[ImageCategory, float]:
        """
        Advanced category scoring profile.

        This profile is slightly stricter against false positives and uses
        smoother weighted scores.
        """
        portrait_score = 0.0
        if face_count > 0:
            portrait_score = min(
                0.95,
                face_count * 0.25 + min(1.0, face_area_ratio * 3.5) * 0.70,
            )

        document_score = float(np.clip(doc_score * 1.35 - face_count * 0.05, 0.0, 1.0))

        if is_grayscale:
            bw_score = 0.86 if doc_score < 0.35 else 0.48
        else:
            bw_score = 0.0

        landscape_score = float(np.clip(scene_score * 1.30, 0.0, 1.0))
        if face_count > 0:
            landscape_score *= 0.45
        if doc_score > 0.35:
            landscape_score *= 0.65

        scores = {
            ImageCategory.PORTRAIT: portrait_score,
            ImageCategory.DOCUMENT: document_score,
            ImageCategory.BLACKWHITE: bw_score,
            ImageCategory.LANDSCAPE: landscape_score,
            ImageCategory.OTHER: 0.28,
        }

        best_category = max(scores, key=lambda category: scores[category])
        confidence = float(scores[best_category])

        if confidence < 0.46:
            best_category = ImageCategory.OTHER
            confidence = float(max(0.0, 1.0 - max(scores.values())))

        return best_category, confidence
    
    def get_output_folder(self, category: ImageCategory) -> str:
        """
        Get output folder name for category.
        
        Args:
            category: Image category
            
        Returns:
            Folder name string
        """
        folder_map = {
            ImageCategory.PORTRAIT: "인물",
            ImageCategory.LANDSCAPE: "풍경",
            ImageCategory.DOCUMENT: "문서",
            ImageCategory.BLACKWHITE: "흑백",
            ImageCategory.OTHER: "기타"
        }
        return folder_map.get(category, "기타")


# Singleton instance
_classifier_instance: Optional[ImageClassifier] = None


def get_classifier() -> ImageClassifier:
    """Get global classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ImageClassifier()
    return _classifier_instance


def reset_classifier_for_tests() -> None:
    global _classifier_instance
    _classifier_instance = None
