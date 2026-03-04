#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Image Processing Module for Photo Cropper.

Provides advanced CV algorithms:
- Free angle rotation
- Auto deskew
- Perspective correction
- Auto color correction
- Old photo restoration
- Enhanced denoising
- GPU acceleration (optional)
"""

import cv2
import numpy as np
import logging
from typing import Any, Optional, Tuple, List, cast
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GPUAccelerator:
    """GPU acceleration wrapper using CUDA (optional).
    
    Falls back to CPU if CUDA is not available.
    """
    
    _instance: Optional["GPUAccelerator"] = None
    _cuda_available: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._check_cuda()
        return cls._instance
    
    def _check_cuda(self):
        """Check if CUDA is available."""
        try:
            count = cv2.cuda.getCudaEnabledDeviceCount()
            self._cuda_available = count > 0
            if self._cuda_available:
                logger.info(f"CUDA available: {count} device(s) detected")
            else:
                logger.info("CUDA not available, using CPU")
        except Exception as e:
            logger.debug(f"CUDA check failed: {e}")
            self._cuda_available = False
    
    @property
    def is_available(self) -> bool:
        """Check if CUDA is available."""
        return bool(self._cuda_available)
    
    def upload(self, image: np.ndarray) -> Any:
        """Upload image to GPU memory."""
        if not self._cuda_available:
            raise RuntimeError("CUDA not available")
        gpu_mat_cls = getattr(cv2, "cuda_GpuMat", None)
        if gpu_mat_cls is None:
            raise RuntimeError("CUDA GpuMat API is not available")
        gpu_mat = gpu_mat_cls()
        gpu_mat.upload(image)
        return gpu_mat
    
    def download(self, gpu_mat: Any) -> np.ndarray:
        """Download image from GPU memory."""
        return gpu_mat.download()
    
    def denoise_gpu(self, image: np.ndarray, h: float = 10, 
                    template_window_size: int = 7,
                    search_window_size: int = 21) -> np.ndarray:
        """GPU-accelerated denoising."""
        if not self._cuda_available:
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )
        
        try:
            gpu_src = self.upload(image)
            # Note: cv2.cuda.fastNlMeansDenoising works on grayscale
            # For color, we process channels separately or fallback
            result = self.download(gpu_src)
            # Fallback to CPU for color denoising as CUDA version is limited
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )
        except Exception as e:
            logger.warning(f"GPU denoising failed, falling back to CPU: {e}")
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window_size, search_window_size
            )
    
    def resize_gpu(self, image: np.ndarray, 
                   size: Tuple[int, int]) -> np.ndarray:
        """GPU-accelerated resize."""
        if not self._cuda_available:
            return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
        
        try:
            gpu_src = self.upload(image)
            cuda_module = getattr(cv2, "cuda", None)
            resize_fn = getattr(cuda_module, "resize", None) if cuda_module else None
            if resize_fn is None:
                return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
            gpu_dst = resize_fn(gpu_src, size)
            return self.download(gpu_dst)
        except Exception as e:
            logger.warning(f"GPU resize failed, falling back to CPU: {e}")
            return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)


@dataclass
class DeskewResult:
    """Result of auto deskew operation."""
    image: np.ndarray
    angle: float
    confidence: float


@dataclass
class PerspectiveResult:
    """Result of perspective correction."""
    image: np.ndarray
    src_points: np.ndarray
    dst_points: np.ndarray
    success: bool
    message: str = ""


class AdvancedImageProcessor:
    """Advanced image processing algorithms."""
    
    def __init__(self, use_gpu: bool = False):
        """Initialize processor.
        
        Args:
            use_gpu: Whether to use GPU acceleration when available
        """
        self._use_gpu = use_gpu
        self._gpu: Optional[GPUAccelerator] = GPUAccelerator() if use_gpu else None
        
        # Performance: Cached CLAHE objects
        self._clahe_default = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self._clahe_strong = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Performance: Cached morphology kernels
        self._kernel_3x3 = np.ones((3, 3), np.uint8)
        self._kernel_line_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        self._kernel_line_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    
    @property
    def gpu_available(self) -> bool:
        """Check if GPU is available."""
        return self._gpu is not None and self._gpu.is_available
    
    # =========================================================================
    # Free Angle Rotation
    # =========================================================================
    
    @staticmethod
    def rotate_free(image: np.ndarray, angle: float, 
                    background_color: Tuple[int, int, int] = (255, 255, 255),
                    expand: bool = True) -> np.ndarray:
        """
        Rotate image by arbitrary angle.
        
        Args:
            image: Input image
            angle: Rotation angle in degrees (positive = counter-clockwise)
            background_color: Background fill color (BGR)
            expand: If True, expand canvas to fit rotated image
            
        Returns:
            Rotated image
        """
        if abs(angle) < 0.01:
            return image.copy()
        
        h, w = image.shape[:2]
        center = (w / 2, h / 2)
        
        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        if expand:
            # Calculate new bounding box size
            cos = np.abs(rotation_matrix[0, 0])
            sin = np.abs(rotation_matrix[0, 1])
            new_w = int(h * sin + w * cos)
            new_h = int(h * cos + w * sin)
            
            # Adjust rotation matrix for new center
            rotation_matrix[0, 2] += (new_w - w) / 2
            rotation_matrix[1, 2] += (new_h - h) / 2
            
            output_size = (new_w, new_h)
        else:
            output_size = (w, h)
        
        # Perform rotation
        rotated = cv2.warpAffine(
            image, rotation_matrix, output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=background_color
        )
        
        return rotated
    
    # =========================================================================
    # Auto Deskew
    # =========================================================================
    
    def auto_deskew(self, image: np.ndarray, 
                    max_angle: float = 45.0,
                    min_confidence: float = 0.3) -> DeskewResult:
        """
        Automatically detect and correct image skew.
        
        Optimization: Detects angle on downscaled image for performance.
        
        Args:
            image: Input image
            max_angle: Maximum allowed skew angle
            min_confidence: Minimum confidence threshold
            
        Returns:
            DeskewResult with corrected image and detected angle
        """
        h, w = image.shape[:2]
        
        # Optimization: Downscale for detection if image is large
        # This significantly speeds up Hough Transform
        max_dim = 1000
        scale = 1.0
        
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            detect_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            detect_img = image
            
        # Convert to grayscale
        if len(detect_img.shape) == 3:
            gray = cv2.cvtColor(detect_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = detect_img.copy()
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Dilate to connect broken edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Hough Line Transform
        lines = cv2.HoughLinesP(
            edges, 
            rho=1, 
            theta=np.pi / 180, 
            threshold=100,
            minLineLength=min(gray.shape) // 10,
            maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)
        
        # Calculate angles of detected lines
        angles = []
        weights = []  # Line length as weight
        
        for line in lines:
            line_points = np.asarray(line).reshape(-1)
            if line_points.size < 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in line_points[:4]]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            
            if x2 - x1 == 0:
                angle = 90.0
            else:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            
            # Normalize angle to -45 to 45 range
            while angle > 45:
                angle -= 90
            while angle < -45:
                angle += 90
            
            if abs(angle) <= max_angle:
                angles.append(angle)
                weights.append(length)
        
        if not angles:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)
        
        # Calculate weighted average angle
        weights = np.array(weights)
        angles = np.array(angles)
        total_weight = np.sum(weights)
        
        if total_weight == 0:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=0.0)
        
        avg_angle = np.sum(angles * weights) / total_weight
        
        # Calculate confidence based on angle consistency
        angle_std = np.sqrt(np.sum(weights * (angles - avg_angle) ** 2) / total_weight)
        confidence = max(0.0, 1.0 - angle_std / 15.0)
        
        # Skip if angle is too small or confidence is low
        if abs(avg_angle) < 0.5 or confidence < min_confidence:
            return DeskewResult(image=image.copy(), angle=0.0, confidence=confidence)
        
        # Rotate original full-resolution image
        # Use simple rotation for speed if GPU not available
        corrected = self.rotate_free(image, avg_angle, expand=True)
        
        logger.info(f"Auto deskew: {avg_angle:.2f}° (confidence: {confidence:.2f})")
        
        return DeskewResult(
            image=corrected,
            angle=avg_angle,
            confidence=confidence
        )
    
    # =========================================================================
    # Perspective Correction
    # =========================================================================
    
    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order points in consistent order: TL, TR, BR, BL.
        
        Args:
            pts: Array of 4 points
            
        Returns:
            Ordered points array
        """
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Sum and diff for corner detection
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        rect[0] = pts[np.argmin(s)]      # Top-left
        rect[2] = pts[np.argmax(s)]      # Bottom-right
        rect[1] = pts[np.argmin(diff)]   # Top-right
        rect[3] = pts[np.argmax(diff)]   # Bottom-left
        
        return rect

    @staticmethod
    def _validate_perspective_points(
        points: np.ndarray,
        image_shape: Tuple[int, int],
    ) -> Tuple[bool, str]:
        """Validate 4-point perspective geometry."""
        if points is None:
            return False, "원근 교정할 포인트가 없습니다"

        try:
            pts = np.array(points, dtype=np.float32).reshape((4, 2))
        except Exception:
            return False, "원근 교정 포인트 형식이 올바르지 않습니다"

        if not np.all(np.isfinite(pts)):
            return False, "원근 교정 포인트에 유효하지 않은 값이 포함되어 있습니다"

        h, w = image_shape[:2]
        if h <= 0 or w <= 0:
            return False, "이미지 크기가 올바르지 않습니다"

        # Duplicate/near-duplicate points.
        for i in range(4):
            for j in range(i + 1, 4):
                if float(np.linalg.norm(pts[i] - pts[j])) < 2.0:
                    return False, "원근 교정 포인트가 서로 너무 가깝거나 중복됩니다"

        # Convexity check.
        contour = pts.reshape((-1, 1, 2)).astype(np.float32)
        if not bool(cv2.isContourConvex(contour)):
            return False, "원근 교정 포인트가 비볼록 사각형입니다"

        # Degenerate polygon area check.
        area = float(cv2.contourArea(contour))
        min_area = max(64.0, (float(w) * float(h)) * 0.0002)
        if area < min_area:
            return False, "원근 교정 영역이 너무 작거나 퇴화되었습니다"

        # Minimum side length check.
        ordered = AdvancedImageProcessor.order_points(pts)
        side_lengths = []
        for i in range(4):
            p1 = ordered[i]
            p2 = ordered[(i + 1) % 4]
            side_lengths.append(float(np.linalg.norm(p1 - p2)))
        if min(side_lengths) < 5.0:
            return False, "원근 교정 영역의 변 길이가 너무 짧습니다"

        return True, ""
    
    def correct_perspective(self, image: np.ndarray,
                           src_points: Optional[np.ndarray] = None,
                           auto_detect: bool = True) -> PerspectiveResult:
        """
        Correct perspective distortion.
        
        Args:
            image: Input image
            src_points: Source corner points (4x2 array). If None, auto-detect.
            auto_detect: Whether to auto-detect corners if src_points is None
            
        Returns:
            PerspectiveResult with corrected image
        """
        h, w = image.shape[:2]
        
        if src_points is None and auto_detect:
            # Auto-detect document corners
            src_points = self._detect_document_corners(image)
            
            if src_points is None:
                return PerspectiveResult(
                    image=image.copy(),
                    src_points=np.array([]),
                    dst_points=np.array([]),
                    success=False,
                    message="문서 코너를 감지할 수 없습니다"
                )
        
        if src_points is None:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message="원근 교정할 포인트가 지정되지 않았습니다"
            )
        
        # Order points
        src_points = self.order_points(src_points.astype(np.float32))

        valid, invalid_reason = self._validate_perspective_points(
            src_points, image.shape[:2]
        )
        if not valid:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message=invalid_reason
            )
        
        # Calculate output dimensions
        width_a = np.linalg.norm(src_points[2] - src_points[3])
        width_b = np.linalg.norm(src_points[1] - src_points[0])
        max_width = int(max(width_a, width_b))
        
        height_a = np.linalg.norm(src_points[1] - src_points[2])
        height_b = np.linalg.norm(src_points[0] - src_points[3])
        max_height = int(max(height_a, height_b))
        if max_width <= 0 or max_height <= 0:
            return PerspectiveResult(
                image=image.copy(),
                src_points=np.array([]),
                dst_points=np.array([]),
                success=False,
                message="원근 교정 결과 크기가 올바르지 않습니다"
            )
        
        # Destination points
        dst_points = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)
        
        # Get perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply transform
        warped = cv2.warpPerspective(
            image, matrix, (max_width, max_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        
        return PerspectiveResult(
            image=warped,
            src_points=src_points,
            dst_points=dst_points,
            success=True,
            message="원근 교정 완료"
        )
    
    def _detect_document_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Auto-detect document corners for perspective correction.
        
        Args:
            image: Input image
            
        Returns:
            4x2 array of corner points or None if detection fails
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape[:2]
        
        # Blur and edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return None
        
        # Find largest contour with 4 corners
        image_area = h * w
        
        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(contour)
            
            # Skip if too small or too large
            if area < image_area * 0.1 or area > image_area * 0.98:
                continue
            
            # Approximate polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:
                return approx.reshape(4, 2)
        
        return None
    
    # =========================================================================
    # Auto Color Correction
    # =========================================================================
    
    @staticmethod
    def auto_color_correct(image: np.ndarray,
                          method: str = "gray_world") -> np.ndarray:
        """
        Automatic color correction.
        
        Args:
            image: Input image (BGR)
            method: Correction method ('gray_world', 'white_patch', 'histogram')
            
        Returns:
            Color-corrected image
        """
        if len(image.shape) != 3:
            return image.copy()
        
        if method == "gray_world":
            return AdvancedImageProcessor._gray_world_correction(image)
        elif method == "white_patch":
            return AdvancedImageProcessor._white_patch_correction(image)
        elif method == "histogram":
            return AdvancedImageProcessor._histogram_correction(image)
        else:
            return image.copy()
    
    @staticmethod
    def _gray_world_correction(image: np.ndarray) -> np.ndarray:
        """Gray World white balance algorithm."""
        result = image.copy().astype(np.float32)
        
        # Calculate mean of each channel
        avg_b = np.mean(result[:, :, 0])
        avg_g = np.mean(result[:, :, 1])
        avg_r = np.mean(result[:, :, 2])
        
        # Calculate overall average
        avg_gray = (avg_b + avg_g + avg_r) / 3
        
        # Scale factors
        if avg_b > 0:
            result[:, :, 0] *= avg_gray / avg_b
        if avg_g > 0:
            result[:, :, 1] *= avg_gray / avg_g
        if avg_r > 0:
            result[:, :, 2] *= avg_gray / avg_r
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def _white_patch_correction(image: np.ndarray) -> np.ndarray:
        """White Patch (Max-RGB) white balance algorithm."""
        result = image.copy().astype(np.float32)
        
        # Find maximum values in each channel
        max_b = np.percentile(result[:, :, 0], 99)
        max_g = np.percentile(result[:, :, 1], 99)
        max_r = np.percentile(result[:, :, 2], 99)
        
        # Scale to white
        if max_b > 0:
            result[:, :, 0] *= 255.0 / max_b
        if max_g > 0:
            result[:, :, 1] *= 255.0 / max_g
        if max_r > 0:
            result[:, :, 2] *= 255.0 / max_r
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def _histogram_correction(image: np.ndarray) -> np.ndarray:
        """Histogram-based color correction."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge and convert back
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # =========================================================================
    # Old Photo Restoration
    # =========================================================================
    
    def restore_old_photo(self, image: np.ndarray,
                         enhance_contrast: bool = True,
                         reduce_noise: bool = True,
                         restore_colors: bool = True,
                         remove_scratches: bool = True) -> np.ndarray:
        """
        Restore old/damaged photos.
        
        Apply multiple restoration techniques:
        - Contrast enhancement
        - Noise reduction
        - Color restoration
        - Scratch/damage removal
        
        Args:
            image: Input image
            enhance_contrast: Apply contrast enhancement
            reduce_noise: Apply noise reduction
            restore_colors: Apply color restoration
            remove_scratches: Attempt to remove scratches
            
        Returns:
            Restored image
        """
        result = image.copy()
        
        # Step 1: Noise reduction (before other processing)
        if reduce_noise:
            result = self.denoise_enhanced(result, strength=8)
        
        # Step 2: Contrast enhancement using CLAHE
        if enhance_contrast:
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Use cached CLAHE
            l = self._clahe_strong.apply(l)
            
            lab = cv2.merge([l, a, b])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Step 3: Color restoration
        if restore_colors:
            # Reduce color cast
            result = self.auto_color_correct(result, method="gray_world")
            
            # Boost saturation slightly
            hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # Step 4: Scratch removal using inpainting
        if remove_scratches:
            result = self._remove_scratches(result)
        
        return result
    
    def _remove_scratches(self, image: np.ndarray) -> np.ndarray:
        """
        Attempt to detect and remove scratches/damage.
        
        Uses morphological operations and inpainting.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect thin bright/dark lines (scratches)
        # Bright scratches
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        bright_lines = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)
        
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        bright_lines += cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel_line)
        
        # Threshold to create mask
        threshold_fn = cast(Any, cv2.threshold)
        _, mask = threshold_fn(
            np.asarray(bright_lines, dtype=np.uint8),
            30,
            255,
            cv2.THRESH_BINARY,
        )
        
        # Dilate mask slightly
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Check if mask has significant content
        if np.sum(mask) < image.shape[0] * image.shape[1] * 0.001:
            return image  # No significant scratches detected
        
        # Inpaint
        result = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        
        return result
    
    # =========================================================================
    # Enhanced Denoising
    # =========================================================================
    
    def denoise_enhanced(self, image: np.ndarray,
                        strength: int = 10,
                        preserve_details: bool = True) -> np.ndarray:
        """
        Enhanced denoising with detail preservation.
        
        Args:
            image: Input image
            strength: Denoising strength (1-20)
            preserve_details: Use bilateral filtering for edge preservation
            
        Returns:
            Denoised image
        """
        strength = max(1, min(20, strength))
        gpu = self._gpu
        
        if len(image.shape) != 3:
            # Grayscale
            if self._use_gpu and gpu is not None and gpu.is_available:
                return gpu.denoise_gpu(
                    cv2.cvtColor(image, cv2.COLOR_GRAY2BGR),
                    h=strength
                )[:, :, 0]
            return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)
        
        # Color image
        if self._use_gpu and gpu is not None and gpu.is_available:
            result = gpu.denoise_gpu(image, h=strength)
        else:
            result = cv2.fastNlMeansDenoisingColored(
                image, None, strength, strength, 7, 21
            )
        
        # Optional: Additional bilateral filtering for edge preservation
        if preserve_details:
            result = cv2.bilateralFilter(result, 5, 50, 50)
        
        return result
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    @staticmethod
    def auto_crop_borders(image: np.ndarray,
                         border_color: str = "auto",
                         threshold: int = 20) -> np.ndarray:
        """
        Automatically crop uniform borders.
        
        Args:
            image: Input image
            border_color: 'white', 'black', or 'auto'
            threshold: Color difference threshold
            
        Returns:
            Cropped image
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        
        if border_color == "auto":
            # Detect border color from corners
            corners = [
                gray[0, 0], gray[0, -1],
                gray[-1, 0], gray[-1, -1]
            ]
            avg_corner = np.mean(corners)
            is_white = avg_corner > 127
        else:
            is_white = border_color == "white"
        
        if is_white:
            mask = gray < (255 - threshold)
        else:
            mask = gray > threshold
        
        # Find bounding box of non-border content
        coords = np.column_stack(np.where(mask))
        
        if len(coords) == 0:
            return image.copy()
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        # Add small padding
        padding = 2
        y_min = max(0, y_min - padding)
        x_min = max(0, x_min - padding)
        y_max = min(h - 1, y_max + padding)
        x_max = min(w - 1, x_max + padding)
        
        return image[y_min:y_max+1, x_min:x_max+1]
    
    @staticmethod
    def sharpen(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Sharpen image.
        
        Args:
            image: Input image
            strength: Sharpening strength (0.5-3.0)
            
        Returns:
            Sharpened image
        """
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ]) * strength
        
        # Normalize kernel
        kernel[1, 1] = 9 * strength - 8 * strength + 8
        
        sharpened = cv2.filter2D(image, -1, kernel / kernel.sum() * strength)
        
        # Blend with original
        alpha = min(1.0, strength / 2)
        result = cv2.addWeighted(image, 1 - alpha, sharpened, alpha, 0)
        
        return result


# Convenience singleton instance
_processor: Optional[AdvancedImageProcessor] = None


def get_advanced_processor(use_gpu: bool = False) -> AdvancedImageProcessor:
    """Get or create advanced processor instance."""
    global _processor
    if _processor is None or _processor._use_gpu != use_gpu:
        _processor = AdvancedImageProcessor(use_gpu=use_gpu)
    return _processor
