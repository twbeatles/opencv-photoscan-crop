#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Photo Detector for Photo Cropper v9.0.

Detects and separates multiple photos from a single scanned image.
"""

import cv2
import numpy as np
import logging
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedPhoto:
    """Represents a detected photo region."""
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    contour: np.ndarray
    confidence: float
    area: float
    aspect_ratio: float
    quad: Optional[np.ndarray] = None


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
        max_aspect_ratio: float = 5.0,
        canny_min: int = 50,
        canny_max: int = 150,
        adaptive_block_size: int = 11,
        adaptive_c: float = 2.0,
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
            canny_min/canny_max: Shared with AlgorithmSettings when provided
            adaptive_block_size/adaptive_c: Adaptive threshold params
        """
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.min_photos = min_photos
        self.max_photos = max_photos
        self.merge_distance = merge_distance
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.canny_min = int(canny_min)
        self.canny_max = int(canny_max)
        self.adaptive_block_size = int(adaptive_block_size)
        self.adaptive_c = float(adaptive_c)

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Order points as TL, TR, BR, BL (shared robust geometry)."""
        from .image.geometry import ImageGeometryMixin

        return ImageGeometryMixin.order_points(pts)

    def _quad_from_contour(self, contour: np.ndarray) -> Optional[np.ndarray]:
        """Convert contour into a best-effort quad candidate."""
        if contour is None or len(contour) < 3:
            return None

        hull = cv2.convexHull(contour)
        peri = cv2.arcLength(hull, True)
        if peri <= 0:
            return None

        for eps_factor in (0.01, 0.015, 0.02, 0.03, 0.04):
            approx = cv2.approxPolyDP(hull, eps_factor * peri, True)
            if approx is not None and len(approx) == 4:
                return self._order_points(approx.reshape((4, 2)).astype(np.float32))

        try:
            rect = cv2.minAreaRect(hull)
            box = cv2.boxPoints(rect)
            if box is not None and len(box) == 4:
                return self._order_points(np.array(box, dtype=np.float32))
        except Exception:
            pass

        return None

    @staticmethod
    def _quad_dimensions(quad: np.ndarray) -> Tuple[float, float]:
        q = MultiPhotoDetector._order_points(quad.reshape((4, 2)).astype(np.float32))
        w_top = float(np.linalg.norm(q[1] - q[0]))
        w_bottom = float(np.linalg.norm(q[2] - q[3]))
        h_left = float(np.linalg.norm(q[3] - q[0]))
        h_right = float(np.linalg.norm(q[2] - q[1]))
        width = max(1.0, (w_top + w_bottom) * 0.5)
        height = max(1.0, (h_left + h_right) * 0.5)
        return width, height

    @staticmethod
    def _bbox_gap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2, ay2 = ax + aw, ay + ah
        bx2, by2 = bx + bw, by + bh

        gap_x = max(0.0, max(ax, bx) - min(ax2, bx2))
        gap_y = max(0.0, max(ay, by) - min(ay2, by2))
        return float(math.hypot(gap_x, gap_y))

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
            
            # Decompose overly connected candidates to reduce over-merge.
            expanded_contours: List[np.ndarray] = []
            for contour in all_contours:
                expanded_contours.extend(
                    self._split_connected_candidates(contour, gray, min_area)
                )

            # Filter and score contours
            detected_photos = []
            for contour in expanded_contours:
                area = cv2.contourArea(contour)
                if area < min_area or area > max_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                quad = self._quad_from_contour(contour)
                if quad is not None:
                    q_width, q_height = self._quad_dimensions(quad)
                    aspect_ratio = q_width / q_height if q_height > 0 else 0.0
                    area = float(q_width * q_height)
                else:
                    aspect_ratio = w / h if h > 0 else 0.0
                
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
                    area=int(area),
                    aspect_ratio=float(aspect_ratio),
                    quad=quad,
                ))
            
            # Remove duplicates and near-identical regions (IoU-based)
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
        
        block = int(self.adaptive_block_size)
        if block < 3:
            block = 3
        if block % 2 == 0:
            block += 1
        max_block = max(3, min(blurred.shape[:2]) - 1)
        if max_block % 2 == 0:
            max_block -= 1
        block = min(block, max_block)

        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, block, float(self.adaptive_c)
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
        
        # Multi-scale Canny (thresholds shared with AlgorithmSettings when set)
        base_low = max(1, int(self.canny_min))
        base_high = max(base_low + 1, int(self.canny_max))
        edges_list = []
        for scale in [0.5, 1.0, 1.5]:
            low = max(1, int(base_low * scale))
            high = max(low + 1, int(base_high * scale))
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

    def _split_connected_candidates(
        self, contour: np.ndarray, gray: np.ndarray, min_area: int
    ) -> List[np.ndarray]:
        """
        Try splitting connected regions caused by thin bridges/noise.

        Uses morphological opening + connected components inside contour ROI.
        """
        if contour is None or len(contour) < 3:
            return []

        x, y, w, h = cv2.boundingRect(contour)
        if w <= 4 or h <= 4:
            return [contour]

        roi_mask = np.zeros((h, w), dtype=np.uint8)
        shifted = contour - np.array([[[x, y]]], dtype=contour.dtype)
        cv2.drawContours(roi_mask, [shifted], -1, 255, thickness=-1)

        kernel_size = max(3, min(11, int(min(w, h) * 0.04)))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        opened = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            opened,
            connectivity=8,
        )
        if num_labels <= 2:
            return [contour]

        min_component_area = max(200, int(min_area * 0.35))
        parts: List[np.ndarray] = []
        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < min_component_area:
                continue

            component = (labels == label).astype(np.uint8) * 255
            cnts, _ = cv2.findContours(
                component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not cnts:
                continue
            c = max(cnts, key=cv2.contourArea)
            c = c + np.array([[[x, y]]], dtype=c.dtype)
            parts.append(c)

        if len(parts) >= 2:
            return parts
        return [contour]

    @staticmethod
    def _bbox_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2, ay2 = ax + aw, ay + ah
        bx2, by2 = bx + bw, by + bh

        inter_w = max(0, min(ax2, bx2) - max(ax, bx))
        inter_h = max(0, min(ay2, by2) - max(ay, by))
        inter = inter_w * inter_h
        if inter <= 0:
            return 0.0

        union = aw * ah + bw * bh - inter
        if union <= 0:
            return 0.0
        return float(inter) / float(union)

    @staticmethod
    def _bbox_contains(
        outer: Tuple[int, int, int, int], inner: Tuple[int, int, int, int], margin: int = 3
    ) -> bool:
        ox, oy, ow, oh = outer
        ix, iy, iw, ih = inner
        return (
            ix >= ox - margin
            and iy >= oy - margin
            and ix + iw <= ox + ow + margin
            and iy + ih <= oy + oh + margin
        )

    @staticmethod
    def _bbox_center_distance(
        a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]
    ) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        acx = ax + aw * 0.5
        acy = ay + ah * 0.5
        bcx = bx + bw * 0.5
        bcy = by + bh * 0.5
        return float(((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5)

    @staticmethod
    def _bbox_gap_distance(
        a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]
    ) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2, ay2 = ax + aw, ay + ah
        bx2, by2 = bx + bw, by + bh

        dx = max(0, max(ax, bx) - min(ax2, bx2))
        dy = max(0, max(ay, by) - min(ay2, by2))
        return float((dx * dx + dy * dy) ** 0.5)

    def _merge_overlapping(self, photos: List[DetectedPhoto]) -> List[DetectedPhoto]:
        """Deduplicate highly-overlapping detections without proximity over-merge."""
        if len(photos) <= 1:
            return photos

        candidates = sorted(
            photos,
            key=lambda p: (float(p.confidence), int(p.area)),
            reverse=True,
        )

        kept: List[DetectedPhoto] = []
        for photo in candidates:
            drop = False
            replace_index = -1
            for idx, existing in enumerate(kept):
                iou = self._bbox_iou(photo.bounding_box, existing.bounding_box)
                center_dist = self._bbox_center_distance(
                    photo.bounding_box, existing.bounding_box
                )
                edge_gap = self._bbox_gap(photo.bounding_box, existing.bounding_box)

                if iou >= 0.55:
                    # Keep the higher-confidence one for near-duplicate regions.
                    drop = True
                    if (
                        photo.confidence > existing.confidence + 0.03
                        or (
                            abs(photo.confidence - existing.confidence) <= 0.03
                            and photo.area > existing.area
                        )
                    ):
                        replace_index = idx
                    break

                near_duplicate = (
                    center_dist <= float(max(1, self.merge_distance)) * 0.65
                    and edge_gap <= float(max(3, int(self.merge_distance * 0.25)))
                )
                if near_duplicate:
                    drop = True
                    if (
                        photo.confidence > existing.confidence + 0.03
                        or (
                            abs(photo.confidence - existing.confidence) <= 0.03
                            and photo.area > existing.area
                        )
                    ):
                        replace_index = idx
                    break

                if self._bbox_contains(existing.bounding_box, photo.bounding_box):
                    drop = True
                    break

                # Distance-based duplicate suppression for nearby, similarly sized boxes.
                if self.merge_distance > 0:
                    center_dist = self._bbox_center_distance(
                        photo.bounding_box, existing.bounding_box
                    )
                    gap_dist = self._bbox_gap_distance(
                        photo.bounding_box, existing.bounding_box
                    )
                    area_small = max(1, min(photo.area, existing.area))
                    area_ratio = max(photo.area, existing.area) / float(area_small)

                    near_duplicate = (
                        gap_dist <= float(self.merge_distance)
                        and center_dist <= float(self.merge_distance * 2)
                        and area_ratio <= 1.6
                        and iou >= 0.15
                    )

                    if near_duplicate:
                        drop = True
                        if (
                            photo.confidence > existing.confidence + 0.03
                            or (
                                abs(photo.confidence - existing.confidence) <= 0.03
                                and photo.area > existing.area
                            )
                        ):
                            replace_index = idx
                        break

            if replace_index >= 0:
                kept[replace_index] = photo
            elif not drop:
                kept.append(photo)

        return kept
    
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
            cropped = None
            quad = photo.quad

            # Perspective crop first when quad is available.
            if quad is not None and np.array(quad).size >= 8:
                try:
                    q = self._order_points(np.array(quad, dtype=np.float32))

                    # Optional outward expansion for padding.
                    if padding > 0:
                        center = np.mean(q, axis=0)
                        vectors = q - center
                        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
                        scale = (lengths + float(padding)) / np.maximum(lengths, 1e-6)
                        q = center + vectors * scale
                        q[:, 0] = np.clip(q[:, 0], 0, width - 1)
                        q[:, 1] = np.clip(q[:, 1], 0, height - 1)

                    q_width, q_height = self._quad_dimensions(q)
                    out_w = max(1, int(round(q_width)))
                    out_h = max(1, int(round(q_height)))

                    if out_w >= 20 and out_h >= 20:
                        dst = np.array(
                            [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
                            dtype=np.float32,
                        )
                        matrix = cv2.getPerspectiveTransform(q, dst)
                        cropped = cv2.warpPerspective(image, matrix, (out_w, out_h))
                except Exception:
                    cropped = None

            # Fallback: axis-aligned bounding-box crop.
            if cropped is None:
                x, y, w, h = photo.bounding_box
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
            if photo.quad is not None and np.array(photo.quad).size >= 8:
                q = self._order_points(np.array(photo.quad, dtype=np.float32)).astype(
                    np.int32
                )
                cv2.polylines(result, [q.reshape((-1, 1, 2))], True, color, 2)
            
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
