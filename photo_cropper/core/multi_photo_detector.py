#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Photo Detector for Photo Cropper v8.5.

Detects and separates multiple photos from a single scanned image.
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedPhoto:
    """Represents a detected photo region."""
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    contour: np.ndarray
    confidence: float
    area: int
    aspect_ratio: float


@dataclass
class MultiPhotoResult:
    """Result of multi-photo detection."""
    success: bool
    photos: List[DetectedPhoto]
    message: str = ""
    total_found: int = 0


class MultiPhotoDetector:
    """
    Detects multiple photos in a single scanned image.
    
    Uses contour analysis with adaptive thresholding to identify
    independent photo regions.
    """
    
    def __init__(
        self,
        min_area_ratio: float = 0.02,
        max_area_ratio: float = 0.8,
        min_photos: int = 1,
        max_photos: int = 20,
        merge_distance: int = 50,
        min_aspect_ratio: float = 0.2,
        max_aspect_ratio: float = 5.0
    ):
        """
        Initialize detector.
        
        Args:
            min_area_ratio: Minimum photo area as ratio of image area
            max_area_ratio: Maximum photo area as ratio of image area
            min_photos: Minimum number of photos to detect
            max_photos: Maximum number of photos to detect
            merge_distance: Distance threshold for merging nearby contours
            min_aspect_ratio: Minimum width/height ratio
            max_aspect_ratio: Maximum width/height ratio
        """
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.min_photos = min_photos
        self.max_photos = max_photos
        self.merge_distance = merge_distance
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
    
    def detect(self, image: np.ndarray) -> MultiPhotoResult:
        """
        Detect multiple photos in the image.
        
        Args:
            image: Input image (BGR format)
            
        Returns:
            MultiPhotoResult with detected photos
        """
        if image is None or image.size == 0:
            return MultiPhotoResult(
                success=False,
                photos=[],
                message="Invalid image"
            )
        
        try:
            height, width = image.shape[:2]
            image_area = height * width
            min_area = int(image_area * self.min_area_ratio)
            max_area = int(image_area * self.max_area_ratio)
            
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply multiple detection methods and combine results
            all_contours = []
            
            # Method 1: Adaptive threshold
            contours1 = self._detect_adaptive_threshold(gray)
            all_contours.extend(contours1)
            
            # Method 2: Canny edge detection
            contours2 = self._detect_canny_edges(gray)
            all_contours.extend(contours2)
            
            # Method 3: Color-based segmentation (for color images)
            if len(image.shape) == 3:
                contours3 = self._detect_color_segmentation(image)
                all_contours.extend(contours3)
            
            # Filter and score contours
            detected_photos = []
            for contour in all_contours:
                area = cv2.contourArea(contour)
                if area < min_area or area > max_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                    continue
                
                # Calculate confidence based on shape regularity
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                
                # Prefer rectangular shapes
                rect_area = w * h
                rectangularity = area / rect_area if rect_area > 0 else 0
                
                confidence = (solidity * 0.4 + rectangularity * 0.6)
                
                if confidence < 0.3:
                    continue
                
                detected_photos.append(DetectedPhoto(
                    bounding_box=(x, y, w, h),
                    contour=contour,
                    confidence=confidence,
                    area=area,
                    aspect_ratio=aspect_ratio
                ))
            
            # Remove duplicates and merge overlapping regions
            detected_photos = self._merge_overlapping(detected_photos)
            
            # Sort by area (largest first) and limit count
            detected_photos.sort(key=lambda p: p.area, reverse=True)
            detected_photos = detected_photos[:self.max_photos]
            
            if len(detected_photos) < self.min_photos:
                return MultiPhotoResult(
                    success=False,
                    photos=detected_photos,
                    message=f"Found {len(detected_photos)} photos, minimum required: {self.min_photos}",
                    total_found=len(detected_photos)
                )
            
            return MultiPhotoResult(
                success=True,
                photos=detected_photos,
                message=f"Detected {len(detected_photos)} photos",
                total_found=len(detected_photos)
            )
            
        except Exception as e:
            logger.error(f"Multi-photo detection failed: {e}")
            return MultiPhotoResult(
                success=False,
                photos=[],
                message=str(e)
            )
    
    def _detect_adaptive_threshold(self, gray: np.ndarray) -> List[np.ndarray]:
        """Detect contours using adaptive thresholding."""
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        return list(contours)
    
    def _detect_canny_edges(self, gray: np.ndarray) -> List[np.ndarray]:
        """Detect contours using Canny edge detection."""
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Multi-scale Canny
        edges_list = []
        for scale in [0.5, 1.0, 1.5]:
            low = int(50 * scale)
            high = int(150 * scale)
            edges = cv2.Canny(blurred, low, high)
            edges_list.append(edges)
        
        # Combine edges
        combined = np.zeros_like(gray)
        for edges in edges_list:
            combined = cv2.bitwise_or(combined, edges)
        
        # Dilate to connect nearby edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined = cv2.dilate(combined, kernel, iterations=2)
        
        contours, _ = cv2.findContours(
            combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        return list(contours)
    
    def _detect_color_segmentation(self, image: np.ndarray) -> List[np.ndarray]:
        """Detect contours using color-based segmentation."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Threshold based on luminance variation
        _, thresh = cv2.threshold(l_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        return list(contours)
    
    def _merge_overlapping(self, photos: List[DetectedPhoto]) -> List[DetectedPhoto]:
        """Merge overlapping or nearby photo regions."""
        if len(photos) <= 1:
            return photos
        
        # Sort by area
        photos.sort(key=lambda p: p.area, reverse=True)
        
        merged = []
        used = set()
        
        for i, photo1 in enumerate(photos):
            if i in used:
                continue
            
            x1, y1, w1, h1 = photo1.bounding_box
            
            # Check overlap with other photos
            merge_candidates = [i]
            for j, photo2 in enumerate(photos[i+1:], i+1):
                if j in used:
                    continue
                
                x2, y2, w2, h2 = photo2.bounding_box
                
                # Calculate overlap or distance
                overlap_x = max(0, min(x1+w1, x2+w2) - max(x1, x2))
                overlap_y = max(0, min(y1+h1, y2+h2) - max(y1, y2))
                
                if overlap_x > 0 and overlap_y > 0:
                    # Regions overlap
                    merge_candidates.append(j)
                    used.add(j)
                else:
                    # Check if nearby
                    dist_x = min(abs(x1 - (x2+w2)), abs(x2 - (x1+w1)))
                    dist_y = min(abs(y1 - (y2+h2)), abs(y2 - (y1+h1)))
                    
                    if dist_x < self.merge_distance and dist_y < self.merge_distance:
                        merge_candidates.append(j)
                        used.add(j)
            
            # Keep the largest from merge candidates
            used.add(i)
            merged.append(photo1)
        
        return merged
    
    def crop_photos(
        self,
        image: np.ndarray,
        photos: List[DetectedPhoto],
        padding: int = 10
    ) -> List[Tuple[np.ndarray, DetectedPhoto]]:
        """
        Crop individual photos from the image.
        
        Args:
            image: Source image
            photos: List of detected photos
            padding: Padding around each photo
            
        Returns:
            List of (cropped_image, photo_info) tuples
        """
        height, width = image.shape[:2]
        results = []
        
        for photo in photos:
            x, y, w, h = photo.bounding_box
            
            # Apply padding
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(width, x + w + padding)
            y2 = min(height, y + h + padding)
            
            cropped = image[y1:y2, x1:x2].copy()
            results.append((cropped, photo))
        
        return results
    
    def visualize_detection(
        self,
        image: np.ndarray,
        photos: List[DetectedPhoto],
        show_labels: bool = True
    ) -> np.ndarray:
        """
        Create visualization of detected photos.
        
        Args:
            image: Source image
            photos: List of detected photos
            show_labels: Whether to show labels
            
        Returns:
            Image with detection visualization
        """
        result = image.copy()
        
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
        
        for i, photo in enumerate(photos):
            color = colors[i % len(colors)]
            x, y, w, h = photo.bounding_box
            
            # Draw rectangle
            cv2.rectangle(result, (x, y), (x+w, y+h), color, 3)
            
            # Draw contour
            cv2.drawContours(result, [photo.contour], -1, color, 2)
            
            if show_labels:
                # Draw label
                label = f"Photo {i+1} ({photo.confidence:.2f})"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                
                (text_w, text_h), _ = cv2.getTextSize(label, font, font_scale, thickness)
                
                # Background for text
                cv2.rectangle(result, (x, y-text_h-10), (x+text_w+10, y), color, -1)
                cv2.putText(result, label, (x+5, y-5), font, font_scale, (255, 255, 255), thickness)
        
        return result
