#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resize Processor for Photo Cropper v9.0.

Provides image resizing and aspect ratio adjustment.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResizeMode(Enum):
    """Resize mode options."""
    NONE = "none"
    FIT = "fit"              # Fit within bounds, preserve aspect ratio
    FILL = "fill"            # Fill bounds, may crop
    STRETCH = "stretch"      # Stretch to exact size, ignore aspect ratio
    WIDTH = "width"          # Resize to width, preserve aspect ratio
    HEIGHT = "height"        # Resize to height, preserve aspect ratio
    PERCENTAGE = "percentage"  # Scale by percentage
    MAX_DIMENSION = "max_dimension"  # Limit largest dimension


class InterpolationMethod(Enum):
    """Interpolation methods for resizing."""
    NEAREST = cv2.INTER_NEAREST
    LINEAR = cv2.INTER_LINEAR
    AREA = cv2.INTER_AREA
    CUBIC = cv2.INTER_CUBIC
    LANCZOS = cv2.INTER_LANCZOS4


@dataclass
class ResizeSettings:
    """Settings for image resizing."""
    enabled: bool = False
    mode: ResizeMode = ResizeMode.NONE
    width: int = 0
    height: int = 0
    percentage: float = 100.0
    max_dimension: int = 0
    interpolation: InterpolationMethod = InterpolationMethod.LANCZOS
    upscale_allowed: bool = False  # Allow making image larger
    
    # Aspect ratio constraints
    maintain_aspect: bool = True
    target_aspect_ratio: Optional[float] = None  # e.g., 4/3, 16/9
    
    # Advanced options
    jpeg_compatible: bool = False  # Ensure dimensions are multiples of 8


@dataclass
class ResizeResult:
    """Result of resize operation."""
    success: bool
    image: Optional[np.ndarray]
    original_size: Tuple[int, int]
    new_size: Tuple[int, int]
    scale_factor: Tuple[float, float]
    message: str = ""


class ResizeProcessor:
    """
    Image resizing and scaling processor.
    
    Features:
        - Multiple resize modes (fit, fill, stretch, etc.)
        - Aspect ratio preservation
        - Quality interpolation options
        - Batch size presets
    """
    
    # Common size presets
    PRESETS = {
        "thumbnail": (150, 150),
        "small": (640, 480),
        "medium": (1024, 768),
        "large": (1920, 1080),
        "4k": (3840, 2160),
        "instagram_square": (1080, 1080),
        "instagram_portrait": (1080, 1350),
        "instagram_landscape": (1080, 566),
        "facebook_post": (1200, 630),
        "twitter_post": (1200, 675),
        "a4_300dpi": (2480, 3508),
        "a4_150dpi": (1240, 1754),
    }
    
    def __init__(self, settings: Optional[ResizeSettings] = None):
        """
        Initialize resize processor.
        
        Args:
            settings: Resize settings to use
        """
        self.settings = settings or ResizeSettings()
    
    def resize(
        self,
        image: np.ndarray,
        settings: Optional[ResizeSettings] = None
    ) -> ResizeResult:
        """
        Resize image according to settings.
        
        Args:
            image: Input image
            settings: Override settings (uses instance settings if None)
            
        Returns:
            ResizeResult with resized image
        """
        settings = settings or self.settings
        
        if not settings.enabled or settings.mode == ResizeMode.NONE:
            h, w = image.shape[:2]
            return ResizeResult(
                success=True,
                image=image,
                original_size=(w, h),
                new_size=(w, h),
                scale_factor=(1.0, 1.0),
                message="No resize applied"
            )
        
        try:
            original_h, original_w = image.shape[:2]
            
            # Calculate new dimensions
            new_w, new_h = self._calculate_dimensions(
                original_w, original_h, settings
            )
            
            # Check if upscaling is needed and allowed
            if not settings.upscale_allowed:
                if new_w > original_w or new_h > original_h:
                    new_w = min(new_w, original_w)
                    new_h = min(new_h, original_h)
            
            # Apply JPEG compatibility if needed
            if settings.jpeg_compatible:
                new_w = (new_w // 8) * 8
                new_h = (new_h // 8) * 8
                new_w = max(8, new_w)
                new_h = max(8, new_h)
            
            # Perform resize
            interpolation = settings.interpolation.value
            
            # Use INTER_AREA for downscaling for better quality
            if new_w < original_w and new_h < original_h:
                interpolation = cv2.INTER_AREA
            
            resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
            
            # Apply aspect ratio crop if mode is FILL
            if settings.mode == ResizeMode.FILL:
                resized = self._crop_to_aspect(resized, settings.width, settings.height)
            
            scale_x = new_w / original_w
            scale_y = new_h / original_h
            
            return ResizeResult(
                success=True,
                image=resized,
                original_size=(original_w, original_h),
                new_size=(new_w, new_h),
                scale_factor=(scale_x, scale_y),
                message=f"Resized from {original_w}x{original_h} to {new_w}x{new_h}"
            )
            
        except Exception as e:
            logger.error(f"Resize failed: {e}")
            h, w = image.shape[:2]
            return ResizeResult(
                success=False,
                image=image,
                original_size=(w, h),
                new_size=(w, h),
                scale_factor=(1.0, 1.0),
                message=str(e)
            )
    
    def _calculate_dimensions(
        self,
        original_w: int,
        original_h: int,
        settings: ResizeSettings
    ) -> Tuple[int, int]:
        """Calculate new dimensions based on resize mode."""
        mode = settings.mode
        
        if mode == ResizeMode.STRETCH:
            return settings.width, settings.height
        
        elif mode == ResizeMode.WIDTH:
            if settings.width <= 0:
                return original_w, original_h
            ratio = settings.width / original_w
            return settings.width, int(original_h * ratio)
        
        elif mode == ResizeMode.HEIGHT:
            if settings.height <= 0:
                return original_w, original_h
            ratio = settings.height / original_h
            return int(original_w * ratio), settings.height
        
        elif mode == ResizeMode.PERCENTAGE:
            scale = settings.percentage / 100.0
            return int(original_w * scale), int(original_h * scale)
        
        elif mode == ResizeMode.MAX_DIMENSION:
            if settings.max_dimension <= 0:
                return original_w, original_h
            
            max_dim = max(original_w, original_h)
            if max_dim <= settings.max_dimension:
                return original_w, original_h
            
            ratio = settings.max_dimension / max_dim
            return int(original_w * ratio), int(original_h * ratio)
        
        elif mode == ResizeMode.FIT:
            if settings.width <= 0 or settings.height <= 0:
                return original_w, original_h
            
            ratio_w = settings.width / original_w
            ratio_h = settings.height / original_h
            ratio = min(ratio_w, ratio_h)
            
            return int(original_w * ratio), int(original_h * ratio)
        
        elif mode == ResizeMode.FILL:
            if settings.width <= 0 or settings.height <= 0:
                return original_w, original_h
            
            ratio_w = settings.width / original_w
            ratio_h = settings.height / original_h
            ratio = max(ratio_w, ratio_h)
            
            return int(original_w * ratio), int(original_h * ratio)
        
        return original_w, original_h
    
    def _crop_to_aspect(
        self,
        image: np.ndarray,
        target_w: int,
        target_h: int
    ) -> np.ndarray:
        """Crop image to target dimensions (center crop)."""
        h, w = image.shape[:2]
        
        if w == target_w and h == target_h:
            return image
        
        # Calculate crop region
        start_x = (w - target_w) // 2
        start_y = (h - target_h) // 2
        
        return image[start_y:start_y+target_h, start_x:start_x+target_w]
    
    def resize_to_preset(
        self,
        image: np.ndarray,
        preset_name: str,
        fit: bool = True
    ) -> ResizeResult:
        """
        Resize image to a predefined preset size.
        
        Args:
            image: Input image
            preset_name: Name of preset (e.g., 'instagram_square')
            fit: If True, fit within bounds; if False, fill bounds
            
        Returns:
            ResizeResult
        """
        if preset_name not in self.PRESETS:
            h, w = image.shape[:2]
            return ResizeResult(
                success=False,
                image=image,
                original_size=(w, h),
                new_size=(w, h),
                scale_factor=(1.0, 1.0),
                message=f"Unknown preset: {preset_name}"
            )
        
        target_w, target_h = self.PRESETS[preset_name]
        
        settings = ResizeSettings(
            enabled=True,
            mode=ResizeMode.FIT if fit else ResizeMode.FILL,
            width=target_w,
            height=target_h
        )
        
        return self.resize(image, settings)
    
    def get_output_size(
        self,
        original_w: int,
        original_h: int,
        settings: Optional[ResizeSettings] = None
    ) -> Tuple[int, int]:
        """
        Calculate output size without performing resize.
        
        Args:
            original_w: Original width
            original_h: Original height
            settings: Resize settings
            
        Returns:
            (new_width, new_height)
        """
        settings = settings or self.settings
        
        if not settings.enabled or settings.mode == ResizeMode.NONE:
            return original_w, original_h
        
        return self._calculate_dimensions(original_w, original_h, settings)
    
    @staticmethod
    def calculate_aspect_ratio(width: int, height: int) -> Tuple[int, int]:
        """
        Calculate simplified aspect ratio.
        
        Args:
            width: Image width
            height: Image height
            
        Returns:
            Simplified ratio as (w_ratio, h_ratio)
        """
        from math import gcd
        divisor = gcd(width, height)
        return width // divisor, height // divisor
    
    @staticmethod
    def get_dimensions_for_aspect(
        target_aspect: float,
        max_width: int,
        max_height: int
    ) -> Tuple[int, int]:
        """
        Calculate dimensions that fit within bounds while maintaining aspect ratio.
        
        Args:
            target_aspect: Target width/height ratio
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            (width, height) that fits bounds with target aspect
        """
        # Try fitting to width
        w = max_width
        h = int(w / target_aspect)
        
        if h > max_height:
            # Fit to height instead
            h = max_height
            w = int(h * target_aspect)
        
        return w, h
    
    def batch_resize(
        self,
        images: list,
        settings: Optional[ResizeSettings] = None
    ) -> list:
        """
        Resize multiple images with same settings.
        
        Args:
            images: List of input images
            settings: Resize settings
            
        Returns:
            List of ResizeResult
        """
        return [self.resize(img, settings) for img in images]
