#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Image Processor for Photo Cropper v9.0.

Provides advanced CV algorithms for automatic photo detection and cropping:
- Multi-scale Canny edge detection
- CLAHE contrast enhancement
- Adaptive threshold for textured backgrounds
- Gradient analysis (Sobel)
- Enhanced contour scoring
- v8.0: Advanced processing (deskew, color correct, perspective, etc.)
"""

import os
import cv2
import numpy as np
import logging
import traceback
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from .settings import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
)
from .advanced_processing import AdvancedImageProcessor, GPUAccelerator

logger = logging.getLogger(__name__)


class DetectionStage(Enum):
    """Detection stage enumeration for tracking which algorithm succeeded."""

    CANNY = "Canny Edge"
    MULTI_SCALE_CANNY = "Multi-Scale Canny"
    ADAPTIVE_THRESHOLD = "Adaptive Threshold"
    GRADIENT_SOBEL = "Gradient (Sobel)"
    CORNER_HARRIS = "Harris Corners"


@dataclass
class CropResult:
    """Result of image cropping operation."""

    success: bool
    image: Optional[np.ndarray] = None
    message: str = ""
    detection_stage: Optional[DetectionStage] = None
    contour_points: Optional[np.ndarray] = None
    original_size: Tuple[int, int] = (0, 0)
    cropped_size: Tuple[int, int] = (0, 0)


class ImageProcessor:
    """
    Advanced image processor for automatic photo detection and cropping.

    Features:
        - 3+ stage intelligent photo detection
        - CLAHE for improved contrast handling
        - Multi-scale edge detection
        - Enhanced contour scoring algorithm
        - Perspective transform for skewed photos
    """

    # Constants
    SUPPORTED_FORMATS = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".webp",
    )
    MIN_IMAGE_SIZE = 100
    RESIZE_TARGET_DIM = 1000
    RESIZE_THRESHOLD = 1500
    DEFAULT_BILATERAL_D = 9
    DEFAULT_BILATERAL_SIGMA = 75
    MIN_CONTOUR_AREA = 100
    MIN_CROP_SIZE = 50

    def __init__(
        self,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
    ):
        """
        Initialize image processor.

        Args:
            algorithm_settings: Algorithm configuration
            processing_settings: Post-processing configuration
            advanced_settings: v8.0 Advanced processing settings
        """
        self.algo = algorithm_settings or AlgorithmSettings()
        self.proc = processing_settings or ProcessingSettings()
        self.advanced = advanced_settings or AdvancedProcessingSettings()
        self.performance = performance_settings or PerformanceSettings()

        # v8.0: Advanced processor
        self._advanced_processor = AdvancedImageProcessor(
            use_gpu=self.performance.use_gpu
        )

        # Performance: Cached CLAHE objects
        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_custom = None  # Lazy initialized with custom settings
        self._clahe_settings_cache = (None, None)  # (clip_limit, grid_size)

        # Performance: Cached kernels
        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_morph_21x21 = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))

    def update_settings(
        self,
        algorithm_settings: Optional[AlgorithmSettings] = None,
        processing_settings: Optional[ProcessingSettings] = None,
        advanced_settings: Optional[AdvancedProcessingSettings] = None,
        performance_settings: Optional[PerformanceSettings] = None,
    ):
        """Update processor settings."""
        if algorithm_settings:
            self.algo = algorithm_settings
        if processing_settings:
            self.proc = processing_settings
        if advanced_settings:
            self.advanced = advanced_settings
        if performance_settings:
            gpu_changed = self.performance.use_gpu != performance_settings.use_gpu
            self.performance = performance_settings
            if gpu_changed:
                self._advanced_processor = AdvancedImageProcessor(
                    use_gpu=self.performance.use_gpu
                )

    @staticmethod
    def rotate_image(image: np.ndarray, angle: int) -> np.ndarray:
        """
        Rotate image by 90 degree increments.

        Args:
            image: Input image array
            angle: Rotation angle (90, 180, 270 or -90)

        Returns:
            Rotated image array
        """
        angle = angle % 360
        if angle == 90 or angle == -270:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180 or angle == -180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270 or angle == -90:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    @staticmethod
    def load_image(image_path: str) -> Optional[np.ndarray]:
        """
        Load image with Unicode path support.

        Args:
            image_path: Path to image file

        Returns:
            Loaded image array or None if failed
        """
        try:
            # Handle Unicode paths (Korean, Japanese, etc.)
            img_array = np.fromfile(image_path, np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order four points in consistent order: TL, TR, BR, BL.

        Args:
            pts: Array of 4 points

        Returns:
            Ordered points array
        """
        rect = np.zeros((4, 2), dtype="float32")

        # Sum: smallest = TL, largest = BR
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # Top-left
        rect[2] = pts[np.argmax(s)]  # Bottom-right

        # Diff: smallest = TR, largest = BL
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # Top-right
        rect[3] = pts[np.argmax(diff)]  # Bottom-left

        return rect

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input BGR image

        Returns:
            Contrast-enhanced image
        """
        if not self.algo.use_clahe:
            return image

        # Get or create CLAHE object with current settings
        clahe = self._get_clahe_with_settings(
            self.algo.clahe_clip_limit, self.algo.clahe_grid_size
        )

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        l = clahe.apply(l)

        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _get_clahe_with_settings(self, clip_limit: float, grid_size: int):
        """Get cached CLAHE object or create new one if settings changed."""
        if (
            self._clahe_settings_cache == (clip_limit, grid_size)
            and self._clahe_custom is not None
        ):
            return self._clahe_custom

        # Create new CLAHE with updated settings
        self._clahe_custom = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(grid_size, grid_size)
        )
        self._clahe_settings_cache = (clip_limit, grid_size)
        return self._clahe_custom

    def score_contour(self, contour: np.ndarray, image_area: int) -> float:
        """
        Score a contour based on multiple criteria.

        Scoring criteria:
            - Shape (prefer rectangles)
            - Area ratio (prefer reasonable sizes)
            - Convexity (prefer convex shapes)
            - Aspect ratio (prefer photo-like ratios)

        Args:
            contour: Contour to score
            image_area: Total image area

        Returns:
            Score between 0.0 and 1.0
        """
        area = cv2.contourArea(contour)
        if area < 100:
            return 0.0

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        # Shape score (4 vertices = rectangle)
        if len(approx) == 4:
            shape_score = 1.0
        elif len(approx) in [3, 5, 6]:
            shape_score = 0.3
        else:
            shape_score = 0.0

        # Area ratio score (prefer 10-80% of image)
        area_ratio = area / image_area
        if 0.1 <= area_ratio <= 0.8:
            area_score = 1.0 - abs(0.4 - area_ratio)  # Prefer ~40%
        elif 0.05 <= area_ratio < 0.1:
            area_score = 0.5
        elif 0.8 < area_ratio <= 0.95:
            area_score = 0.3
        else:
            area_score = 0.0

        # Convexity score
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        convexity = area / hull_area if hull_area > 0 else 0
        convexity_score = convexity  # Higher is better

        # Aspect ratio score
        x, y, w, h = cv2.boundingRect(contour)
        aspect = w / h if h > 0 else 0
        # Prefer aspect ratios between 0.5 and 2.0 (typical photo ratios)
        if 0.5 <= aspect <= 2.0:
            aspect_score = 1.0 - abs(1.0 - aspect) * 0.5
        elif 0.3 <= aspect <= 3.0:
            aspect_score = 0.5
        else:
            aspect_score = 0.2

        # Weighted combination
        if self.algo.contour_scoring == "enhanced":
            weights = {"shape": 0.35, "area": 0.25, "convexity": 0.20, "aspect": 0.20}
        elif self.algo.contour_scoring == "strict":
            weights = {"shape": 0.50, "area": 0.20, "convexity": 0.15, "aspect": 0.15}
        else:  # basic
            weights = {"shape": 0.40, "area": 0.30, "convexity": 0.15, "aspect": 0.15}

        score = (
            shape_score * weights["shape"]
            + area_score * weights["area"]
            + convexity_score * weights["convexity"]
            + aspect_score * weights["aspect"]
        )

        return score

    def find_best_contour(
        self,
        edge_image: np.ndarray,
        image_area: int,
        min_area_ratio: Optional[float] = None,
        max_area_ratio: Optional[float] = None,
    ) -> Optional[np.ndarray]:
        """
        Find the best rectangular contour from edge image.

        Args:
            edge_image: Binary edge image
            image_area: Total image area
            min_area_ratio: Minimum area ratio
            max_area_ratio: Maximum area ratio

        Returns:
            Best contour (4 points) or None
        """
        min_ratio = min_area_ratio or self.algo.min_area_ratio
        max_ratio = max_area_ratio or self.algo.max_area_ratio

        contours, _ = cv2.findContours(
            edge_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Sort by area, take top 15
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]

        min_area = image_area * min_ratio
        max_area = image_area * max_ratio

        best_contour = None
        best_score = 0.0

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area
            if not (min_area < area < max_area):
                continue

            # Approximate to polygon
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            # Only consider quadrilaterals
            if len(approx) != 4:
                continue

            # Check aspect ratio
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / h if h > 0 else 0
            if not (0.1 < aspect_ratio < 10):
                continue

            # Score this contour
            score = self.score_contour(contour, image_area)

            if score > best_score:
                best_score = score
                best_contour = approx

        return best_contour

    def detect_edges_multiscale(self, gray: np.ndarray) -> np.ndarray:
        """
        Multi-scale Canny edge detection.

        Args:
            gray: Grayscale image

        Returns:
            Combined edge image
        """
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.algo.multi_scale_edge:
            # Low threshold edges (more sensitive)
            edges_low = cv2.Canny(
                blurred, int(self.algo.canny_min * 0.5), int(self.algo.canny_max * 0.5)
            )

            # Normal edges
            edges_normal = cv2.Canny(blurred, self.algo.canny_min, self.algo.canny_max)

            # High threshold edges (less noise)
            edges_high = cv2.Canny(
                blurred, int(self.algo.canny_min * 1.5), int(self.algo.canny_max * 1.5)
            )

            # Combine: prioritize normal, fill with low, validate with high
            edges = cv2.bitwise_or(edges_normal, edges_low)
            edges = cv2.bitwise_and(edges, cv2.dilate(edges_high, None, iterations=2))

            # If combined is too sparse, use normal
            if cv2.countNonZero(edges) < cv2.countNonZero(edges_normal) * 0.3:
                edges = edges_normal
        else:
            edges = cv2.Canny(blurred, self.algo.canny_min, self.algo.canny_max)

        # Dilate to connect edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        return edges

    def process_image(self, image_path: str) -> CropResult:
        """
        Process image with multi-stage detection algorithm.

        Args:
            image_path: Path to input image

        Returns:
            CropResult with processed image or error
        """
        try:
            # Load image
            image = self.load_image(image_path)
            if image is None:
                return CropResult(False, message="이미지를 불러올 수 없습니다.")

            height, width = image.shape[:2]
            original_size = (width, height)

            if height < 100 or width < 100:
                return CropResult(
                    False,
                    message="이미지 크기가 너무 작습니다 (최소 100x100).",
                    original_size=original_size,
                )

            orig = image.copy()

            # Resize for processing (performance optimization)
            # Use a fixed size for detection to ensure consistent performance regardless of input size
            target_dim = 1000
            max_dim = max(height, width)

            if max_dim > 1500:  # Only resize if significantly larger
                ratio = max_dim / target_dim
                new_width = int(width / ratio)
                new_height = int(height / ratio)
                image_resized = cv2.resize(
                    image, (new_width, new_height), interpolation=cv2.INTER_LINEAR
                )
            else:
                ratio = 1.0
                image_resized = image

            image_area = image_resized.shape[0] * image_resized.shape[1]

            # Apply CLAHE for better contrast
            if self.algo.use_clahe:
                image_resized = self.apply_clahe(image_resized)

            gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)

            screen_contour = None
            detection_stage = None

            # ==========================================
            # Stage 1: Multi-scale Canny Edge Detection
            # ==========================================
            edges = self.detect_edges_multiscale(gray)
            screen_contour = self.find_best_contour(edges, image_area)
            if screen_contour is not None:
                detection_stage = (
                    DetectionStage.MULTI_SCALE_CANNY
                    if self.algo.multi_scale_edge
                    else DetectionStage.CANNY
                )

            # ==========================================
            # Stage 2: Adaptive Threshold
            # ==========================================
            if screen_contour is None:
                blurred_bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
                thresh = cv2.adaptiveThreshold(
                    blurred_bilateral,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV,
                    15,
                    4,
                )
                screen_contour = self.find_best_contour(thresh, image_area)
                if screen_contour is not None:
                    detection_stage = DetectionStage.ADAPTIVE_THRESHOLD

            # ==========================================
            # Stage 3: Gradient Analysis (Sobel)
            # ==========================================
            if screen_contour is None:
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                grad_x = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
                grad_y = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
                gradient = cv2.subtract(grad_x, grad_y)
                gradient = cv2.convertScaleAbs(gradient)

                _, thresh_grad = cv2.threshold(
                    gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )

                kernel_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
                closed = cv2.morphologyEx(thresh_grad, cv2.MORPH_CLOSE, kernel_morph)
                closed = cv2.erode(closed, None, iterations=4)
                closed = cv2.dilate(closed, None, iterations=4)

                screen_contour = self.find_best_contour(closed, image_area)
                if screen_contour is not None:
                    detection_stage = DetectionStage.GRADIENT_SOBEL

            # ==========================================
            # Stage 4: Harris Corner Detection (optional)
            # ==========================================
            if screen_contour is None and self.algo.use_corner_detection:
                corners = cv2.cornerHarris(
                    gray, self.algo.corner_block_size, 3, self.algo.corner_k
                )
                corners = cv2.dilate(corners, None)

                # Threshold corners
                threshold = 0.01 * corners.max()
                corner_mask = np.zeros_like(gray)
                corner_mask[corners > threshold] = 255

                # Find contour from corner mask
                screen_contour = self.find_best_contour(corner_mask, image_area)
                if screen_contour is not None:
                    detection_stage = DetectionStage.CORNER_HARRIS

            if screen_contour is None:
                return CropResult(
                    False,
                    message="사진 테두리를 찾지 못했습니다.",
                    original_size=original_size,
                )

            # Scale contour back to original size
            rect = self.order_points(screen_contour.reshape(4, 2) * ratio)
            (tl, tr, br, bl) = rect

            # Calculate output dimensions
            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_width = max(int(width_a), int(width_b))

            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_height = max(int(height_a), int(height_b))

            if max_width <= 0 or max_height <= 0:
                return CropResult(
                    False,
                    message="검출된 영역 크기가 유효하지 않습니다.",
                    original_size=original_size,
                )

            if max_width < 50 or max_height < 50:
                return CropResult(
                    False,
                    message="검출된 영역이 너무 작습니다.",
                    original_size=original_size,
                )

            # Perspective transform
            dst = np.array(
                [
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1],
                ],
                dtype="float32",
            )

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(orig, M, (max_width, max_height))

            # Apply post-processing
            warped = self._apply_post_processing(warped)

            cropped_size = (warped.shape[1], warped.shape[0])

            # Cleanup large variables
            del gray
            if "edges" in locals():
                del edges
            if "thresh" in locals():
                del thresh
            if "image_resized" in locals() and image_resized is not image:
                del image_resized

            return CropResult(
                success=True,
                image=warped,
                message="성공",
                detection_stage=detection_stage,
                contour_points=rect,
                original_size=original_size,
                cropped_size=cropped_size,
            )

        except MemoryError:
            # Force garbage collection on memory error
            import gc

            gc.collect()
            return CropResult(False, message="메모리 부족 - 이미지가 너무 큽니다.")
        except Exception as e:
            logger.error(f"Image processing error: {traceback.format_exc()}")
            return CropResult(False, message=f"오류 발생: {str(e)}")

    def _apply_post_processing(self, image: np.ndarray) -> np.ndarray:
        """
        Apply post-processing effects to cropped image.

        Args:
            image: Cropped image

        Returns:
            Post-processed image
        """
        result = image.copy()

        # Grayscale conversion
        if self.proc.to_grayscale:
            result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

        # Denoise
        if self.proc.denoise:
            if len(result.shape) == 2:
                result = cv2.fastNlMeansDenoising(result, h=self.proc.denoise_strength)
            else:
                result = cv2.fastNlMeansDenoisingColored(
                    result,
                    h=self.proc.denoise_strength,
                    hForColorComponents=self.proc.denoise_strength,
                )

        # Auto contrast (CLAHE or histogram equalization)
        if self.proc.auto_contrast:
            if len(result.shape) == 2:
                # Grayscale - use cached CLAHE
                result = self._clahe_default.apply(result)
            else:
                # Color - apply CLAHE to L channel in LAB
                lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l = self._clahe_default.apply(l)
                lab = cv2.merge([l, a, b])
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Sharpening
        if self.proc.apply_sharpening:
            strength = self.proc.sharpening_strength
            if strength > 0:
                # Adjustable sharpening kernel
                kernel = np.array(
                    [
                        [-strength / 4, -strength / 4, -strength / 4],
                        [-strength / 4, 1 + 2 * strength, -strength / 4],
                        [-strength / 4, -strength / 4, -strength / 4],
                    ]
                )
                result = cv2.filter2D(result, -1, kernel)

        # ========================================
        # v8.0 Advanced Processing
        # ========================================

        # Auto deskew
        if self.advanced.auto_deskew:
            deskew_result = self._advanced_processor.auto_deskew(result)
            if deskew_result is not None and deskew_result.image is not None:
                result = deskew_result.image

        # Auto color correction
        if self.advanced.auto_color_correct:
            result = self._advanced_processor.auto_color_correct(
                result, method=self.advanced.color_correct_method
            )

        # Enhanced denoise
        if self.advanced.enhanced_denoise:
            result = self._advanced_processor.denoise_enhanced(
                result, strength=self.advanced.enhanced_denoise_strength
            )

        # Old photo restoration
        if self.advanced.restore_old_photo:
            result = self._advanced_processor.restore_old_photo(result)

        # Enhanced sharpening
        if self.advanced.enhanced_sharpen:
            result = self._advanced_processor.sharpen(result)

        # Auto crop borders
        if self.advanced.auto_crop_borders:
            result = self._advanced_processor.auto_crop_borders(result)

        return result

    @staticmethod
    def save_image(
        image: np.ndarray,
        output_path: str,
        output_format: str = "JPG",
        jpg_quality: int = 95,
        png_compression: int = 6,
        webp_quality: int = 90,
    ) -> Tuple[bool, str, float]:
        """
        Save image to file with Unicode path support.

        Args:
            image: Image array to save
            output_path: Output file path
            output_format: Format (JPG, PNG, WEBP)
            jpg_quality: JPEG quality (1-100)
            png_compression: PNG compression (0-9)
            webp_quality: WebP quality (1-100)

        Returns:
            Tuple of (success, message, file_size_kb)
        """
        try:
            fmt = output_format.upper()

            if fmt == "JPG" or fmt == "JPEG":
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpg_quality]
            elif fmt == "PNG":
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, png_compression]
            elif fmt == "WEBP":
                encode_params = [cv2.IMWRITE_WEBP_QUALITY, webp_quality]
            else:
                encode_params = []

            extension = os.path.splitext(output_path)[1]
            result, encoded_img = cv2.imencode(extension, image, encode_params)

            if result:
                # Handle Unicode paths
                with open(output_path, mode="wb") as f:
                    encoded_img.tofile(f)

                file_size = os.path.getsize(output_path) / 1024  # KB
                return True, "저장 완료", file_size
            else:
                return False, "인코딩 실패", 0.0

        except Exception as e:
            logger.error(f"Image save error: {e}")
            return False, f"저장 오류: {str(e)}", 0.0

    @staticmethod
    def get_image_info(image_path: str) -> Optional[Tuple[int, int, int]]:
        """
        Get image dimensions without fully loading.

        Args:
            image_path: Path to image

        Returns:
            Tuple of (width, height, channels) or None
        """
        # Try PIL first - only reads headers, much faster for large images
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                w, h = img.size
                # Determine channels from mode
                mode_channels = {
                    "L": 1,
                    "LA": 2,
                    "P": 1,
                    "RGB": 3,
                    "RGBA": 4,
                    "CMYK": 4,
                    "YCbCr": 3,
                    "LAB": 3,
                    "HSV": 3,
                }
                c = mode_channels.get(img.mode, 3)
                return w, h, c
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback to OpenCV (loads full image)
        try:
            img_array = np.fromfile(image_path, np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if image is not None:
                h, w = image.shape[:2]
                c = image.shape[2] if len(image.shape) > 2 else 1
                return w, h, c
        except Exception:
            pass
        return None

    def get_preview_with_contour(
        self, image_path: str, max_size: int = 800
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
        """
        Get preview images with detected contour overlay.

        Args:
            image_path: Path to input image
            max_size: Maximum dimension for preview

        Returns:
            Tuple of (original_preview, contour_overlay, message)
        """
        try:
            image = self.load_image(image_path)
            if image is None:
                return None, None, "이미지를 불러올 수 없습니다."

            # Resize for preview
            h, w = image.shape[:2]
            scale = min(max_size / w, max_size / h, 1.0)
            preview_size = (int(w * scale), int(h * scale))
            original_preview = cv2.resize(image, preview_size)

            # Process to get contour
            result = self.process_image(image_path)

            if result.success and result.contour_points is not None:
                # Draw contour on overlay
                overlay = original_preview.copy()
                scaled_contour = (result.contour_points * scale).astype(np.int32)
                cv2.polylines(overlay, [scaled_contour], True, (0, 255, 0), 2)

                # Draw corner points
                for point in scaled_contour:
                    cv2.circle(overlay, tuple(point), 5, (0, 0, 255), -1)

                return original_preview, overlay, result.message
            else:
                return original_preview, original_preview.copy(), result.message

        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return None, None, f"미리보기 오류: {str(e)}"
