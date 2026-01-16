#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watermark Processor for Photo Cropper v9.0.

Adds text and image watermarks to processed photos.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class WatermarkPosition(Enum):
    """Watermark position options."""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    CENTER = "center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class TextWatermarkSettings:
    """Settings for text watermark."""
    text: str = ""
    font_scale: float = 1.0
    color: Tuple[int, int, int] = (255, 255, 255)  # BGR
    opacity: float = 0.5
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    margin: int = 20
    shadow: bool = True
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_offset: int = 2


@dataclass
class ImageWatermarkSettings:
    """Settings for image watermark."""
    image_path: str = ""
    scale: float = 0.2  # Scale relative to main image
    opacity: float = 0.5
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    margin: int = 20


class WatermarkProcessor:
    """
    Applies watermarks to images.
    
    Supports:
        - Text watermarks with customizable font, color, opacity
        - Image watermarks (PNG with transparency)
        - 9 position options
        - Shadow effects for text
    """
    
    # OpenCV font mapping
    FONTS = {
        "simplex": cv2.FONT_HERSHEY_SIMPLEX,
        "plain": cv2.FONT_HERSHEY_PLAIN,
        "duplex": cv2.FONT_HERSHEY_DUPLEX,
        "complex": cv2.FONT_HERSHEY_COMPLEX,
        "triplex": cv2.FONT_HERSHEY_TRIPLEX,
        "script": cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
    }
    
    def __init__(self):
        """Initialize watermark processor."""
        self._cached_watermark_image: Optional[np.ndarray] = None
        self._cached_watermark_path: str = ""
    
    def apply_text_watermark(
        self,
        image: np.ndarray,
        settings: TextWatermarkSettings
    ) -> np.ndarray:
        """
        Apply text watermark to image.
        
        Args:
            image: Input image (BGR format)
            settings: Text watermark settings
            
        Returns:
            Image with watermark applied
        """
        if not settings.text:
            return image
        
        result = image.copy()
        height, width = result.shape[:2]
        
        # Get font and calculate text size
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(settings.font_scale * 2))
        
        (text_w, text_h), baseline = cv2.getTextSize(
            settings.text, font, settings.font_scale, thickness
        )
        
        # Calculate position
        x, y = self._calculate_position(
            width, height, text_w, text_h + baseline,
            settings.position, settings.margin
        )
        
        # Create overlay for opacity blending
        overlay = result.copy()
        
        # Draw shadow if enabled
        if settings.shadow:
            shadow_x = x + settings.shadow_offset
            shadow_y = y + settings.shadow_offset
            cv2.putText(
                overlay, settings.text, (shadow_x, shadow_y),
                font, settings.font_scale, settings.shadow_color, thickness
            )
        
        # Draw main text
        cv2.putText(
            overlay, settings.text, (x, y),
            font, settings.font_scale, settings.color, thickness
        )
        
        # Apply opacity
        cv2.addWeighted(overlay, settings.opacity, result, 1 - settings.opacity, 0, result)
        
        return result
    
    def apply_image_watermark(
        self,
        image: np.ndarray,
        settings: ImageWatermarkSettings
    ) -> np.ndarray:
        """
        Apply image watermark to image.
        
        Args:
            image: Input image (BGR format)
            settings: Image watermark settings
            
        Returns:
            Image with watermark applied
        """
        if not settings.image_path:
            return image
        
        # Load watermark image (with caching)
        watermark = self._load_watermark_image(settings.image_path)
        if watermark is None:
            logger.warning(f"Failed to load watermark image: {settings.image_path}")
            return image
        
        result = image.copy()
        height, width = result.shape[:2]
        
        # Scale watermark
        wm_h, wm_w = watermark.shape[:2]
        scale = min(
            settings.scale,
            (width * 0.5) / wm_w,  # Max 50% of image width
            (height * 0.5) / wm_h   # Max 50% of image height
        )
        
        new_w = int(wm_w * scale)
        new_h = int(wm_h * scale)
        watermark_resized = cv2.resize(watermark, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Calculate position
        x, y = self._calculate_position(
            width, height, new_w, new_h,
            settings.position, settings.margin
        )
        
        # Ensure watermark fits within image bounds
        x = max(0, min(x, width - new_w))
        y = max(0, min(y, height - new_h))
        
        # Apply watermark with transparency
        self._blend_watermark(result, watermark_resized, x, y, settings.opacity)
        
        return result
    
    def _load_watermark_image(self, path: str) -> Optional[np.ndarray]:
        """Load watermark image with caching."""
        if path == self._cached_watermark_path and self._cached_watermark_image is not None:
            return self._cached_watermark_image.copy()
        
        try:
            # Load with alpha channel
            watermark = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if watermark is None:
                return None
            
            # Add alpha channel if not present
            if len(watermark.shape) == 2:
                watermark = cv2.cvtColor(watermark, cv2.COLOR_GRAY2BGRA)
            elif watermark.shape[2] == 3:
                watermark = cv2.cvtColor(watermark, cv2.COLOR_BGR2BGRA)
            
            self._cached_watermark_image = watermark
            self._cached_watermark_path = path
            
            return watermark.copy()
            
        except Exception as e:
            logger.error(f"Failed to load watermark: {e}")
            return None
    
    def _calculate_position(
        self,
        img_w: int, img_h: int,
        wm_w: int, wm_h: int,
        position: WatermarkPosition,
        margin: int
    ) -> Tuple[int, int]:
        """Calculate watermark position."""
        positions = {
            WatermarkPosition.TOP_LEFT: (margin, margin + wm_h),
            WatermarkPosition.TOP_CENTER: ((img_w - wm_w) // 2, margin + wm_h),
            WatermarkPosition.TOP_RIGHT: (img_w - wm_w - margin, margin + wm_h),
            WatermarkPosition.MIDDLE_LEFT: (margin, (img_h + wm_h) // 2),
            WatermarkPosition.CENTER: ((img_w - wm_w) // 2, (img_h + wm_h) // 2),
            WatermarkPosition.MIDDLE_RIGHT: (img_w - wm_w - margin, (img_h + wm_h) // 2),
            WatermarkPosition.BOTTOM_LEFT: (margin, img_h - margin),
            WatermarkPosition.BOTTOM_CENTER: ((img_w - wm_w) // 2, img_h - margin),
            WatermarkPosition.BOTTOM_RIGHT: (img_w - wm_w - margin, img_h - margin),
        }
        return positions.get(position, positions[WatermarkPosition.BOTTOM_RIGHT])
    
    def _blend_watermark(
        self,
        image: np.ndarray,
        watermark: np.ndarray,
        x: int, y: int,
        opacity: float
    ):
        """Blend watermark onto image with alpha channel support."""
        wm_h, wm_w = watermark.shape[:2]
        
        # Get region of interest
        roi = image[y:y+wm_h, x:x+wm_w]
        
        if watermark.shape[2] == 4:
            # BGRA watermark - use alpha channel
            alpha = watermark[:, :, 3:4] / 255.0 * opacity
            bgr = watermark[:, :, :3]
            
            # Blend
            blended = (bgr * alpha + roi * (1 - alpha)).astype(np.uint8)
            image[y:y+wm_h, x:x+wm_w] = blended
        else:
            # BGR watermark - simple blend
            blended = cv2.addWeighted(watermark[:, :, :3], opacity, roi, 1 - opacity, 0)
            image[y:y+wm_h, x:x+wm_w] = blended
    
    def create_tiled_watermark(
        self,
        image: np.ndarray,
        text: str,
        spacing: int = 200,
        angle: float = -45,
        font_scale: float = 0.8,
        color: Tuple[int, int, int] = (128, 128, 128),
        opacity: float = 0.3
    ) -> np.ndarray:
        """
        Create tiled watermark pattern across entire image.
        
        Args:
            image: Input image
            text: Watermark text
            spacing: Spacing between watermarks
            angle: Rotation angle in degrees
            font_scale: Font scale
            color: Text color (BGR)
            opacity: Opacity (0-1)
            
        Returns:
            Image with tiled watermark
        """
        result = image.copy()
        height, width = result.shape[:2]
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = max(1, int(font_scale * 2))
        
        (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Create overlay
        overlay = result.copy()
        
        # Calculate rotated positions
        import math
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        
        # Extend beyond image bounds to cover after rotation
        for y in range(-height, height * 2, spacing):
            for x in range(-width, width * 2, spacing):
                # Rotate position
                rx = int(x * cos_a - y * sin_a)
                ry = int(x * sin_a + y * cos_a)
                
                if 0 <= rx < width and 0 <= ry < height:
                    cv2.putText(overlay, text, (rx, ry), font, font_scale, color, thickness)
        
        # Apply opacity
        cv2.addWeighted(overlay, opacity, result, 1 - opacity, 0, result)
        
        return result
    
    def preview_watermark(
        self,
        image: np.ndarray,
        text_settings: Optional[TextWatermarkSettings] = None,
        image_settings: Optional[ImageWatermarkSettings] = None
    ) -> np.ndarray:
        """
        Preview watermark without modifying original.
        
        Args:
            image: Input image
            text_settings: Text watermark settings
            image_settings: Image watermark settings
            
        Returns:
            Preview image with watermarks
        """
        result = image.copy()
        
        if image_settings:
            result = self.apply_image_watermark(result, image_settings)
        
        if text_settings:
            result = self.apply_text_watermark(result, text_settings)
        
        return result
