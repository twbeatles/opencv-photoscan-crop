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
    font_path: str = ""  # Optional .ttf/.otf path for Pillow Unicode rendering
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
        self._cached_font_path: str = ""
        self._cached_font_size: int = 0
        self._cached_pil_font = None

    def apply_text_watermark(
        self, image: np.ndarray, settings: TextWatermarkSettings
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

        # Use Pillow when text includes non-ASCII (e.g., Korean) or a font path is provided.
        if settings.font_path or any(ord(ch) > 127 for ch in settings.text):
            pil_result = self._apply_text_watermark_pillow(image, settings)
            if pil_result is not None:
                return pil_result

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
            width, height, text_w, text_h + baseline, settings.position, settings.margin
        )

        # Create overlay for opacity blending
        overlay = result.copy()

        # Draw shadow if enabled
        if settings.shadow:
            shadow_x = x + settings.shadow_offset
            shadow_y = y + settings.shadow_offset
            cv2.putText(
                overlay,
                settings.text,
                (shadow_x, shadow_y),
                font,
                settings.font_scale,
                settings.shadow_color,
                thickness,
            )

        # Draw main text
        cv2.putText(
            overlay,
            settings.text,
            (x, y),
            font,
            settings.font_scale,
            settings.color,
            thickness,
        )

        # Apply opacity
        cv2.addWeighted(
            overlay, settings.opacity, result, 1 - settings.opacity, 0, result
        )

        return result

    def _apply_text_watermark_pillow(
        self, image: np.ndarray, settings: TextWatermarkSettings
    ) -> Optional[np.ndarray]:
        """Render Unicode text watermark using Pillow, then convert back to OpenCV BGR."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            logger.warning(f"Pillow not available for Unicode watermark: {e}")
            return None

        if image is None or image.size == 0:
            return None

        try:
            height, width = image.shape[:2]
            # Convert BGR -> RGBA
            base = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).convert(
                "RGBA"
            )
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            font_path = settings.font_path or self._find_default_windows_font()
            font_size = max(10, int(32 * float(settings.font_scale)))

            font = None
            if font_path:
                font = self._get_cached_font(ImageFont, font_path, font_size)
            if font is None:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), settings.text, font=font)
            text_w = max(1, int(bbox[2] - bbox[0]))
            text_h = max(1, int(bbox[3] - bbox[1]))

            # _calculate_position returns coordinates based on a baseline y (OpenCV-like).
            x_base, y_base = self._calculate_position(
                width, height, text_w, text_h, settings.position, settings.margin
            )
            x = int(x_base)
            y_top = int(y_base - text_h)

            # Clamp to image bounds
            x = max(0, min(x, width - 1))
            y_top = max(0, min(y_top, height - 1))

            # Colors: settings.color/shadow_color are BGR; Pillow expects RGBA.
            b, g, r = settings.color
            fill = (int(r), int(g), int(b), int(255 * float(settings.opacity)))
            sb, sg, sr = settings.shadow_color
            shadow_fill = (
                int(sr),
                int(sg),
                int(sb),
                int(255 * float(settings.opacity)),
            )

            if settings.shadow:
                sx = x + int(settings.shadow_offset)
                sy = y_top + int(settings.shadow_offset)
                draw.text((sx, sy), settings.text, font=font, fill=shadow_fill)

            draw.text((x, y_top), settings.text, font=font, fill=fill)

            combined = Image.alpha_composite(base, overlay).convert("RGB")
            out = cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)
            return out
        except Exception as e:
            logger.warning(f"Unicode watermark render failed, falling back to OpenCV: {e}")
            return None

    def _get_cached_font(self, ImageFont, font_path: str, font_size: int):
        """Cache loaded PIL fonts to avoid re-loading for every image."""
        try:
            if (
                self._cached_pil_font is not None
                and self._cached_font_path == font_path
                and self._cached_font_size == font_size
            ):
                return self._cached_pil_font
            font = ImageFont.truetype(font_path, font_size)
            self._cached_pil_font = font
            self._cached_font_path = font_path
            self._cached_font_size = font_size
            return font
        except Exception:
            return None

    @staticmethod
    def _find_default_windows_font() -> str:
        """Find a default font path on Windows for Korean/Unicode rendering."""
        candidates = [
            r"C:\Windows\Fonts\malgun.ttf",  # Malgun Gothic
            r"C:\Windows\Fonts\segoeui.ttf",  # Segoe UI
            r"C:\Windows\Fonts\arial.ttf",
        ]
        for p in candidates:
            try:
                if Path(p).exists():
                    return p
            except Exception:
                continue
        return ""

    def apply_image_watermark(
        self, image: np.ndarray, settings: ImageWatermarkSettings
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
            (height * 0.5) / wm_h,  # Max 50% of image height
        )

        new_w = int(wm_w * scale)
        new_h = int(wm_h * scale)
        watermark_resized = cv2.resize(
            watermark, (new_w, new_h), interpolation=cv2.INTER_AREA
        )

        # Calculate position
        x, y = self._calculate_position(
            width, height, new_w, new_h, settings.position, settings.margin
        )

        # Ensure watermark fits within image bounds
        x = max(0, min(x, width - new_w))
        y = max(0, min(y, height - new_h))

        # Apply watermark with transparency
        self._blend_watermark(result, watermark_resized, x, y, settings.opacity)

        return result

    def _load_watermark_image(self, path: str) -> Optional[np.ndarray]:
        """Load watermark image with caching."""
        if (
            path == self._cached_watermark_path
            and self._cached_watermark_image is not None
        ):
            return self._cached_watermark_image.copy()

        try:
            # Load with Unicode path support
            img_array = np.fromfile(path, dtype=np.uint8)
            watermark = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
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
        img_w: int,
        img_h: int,
        wm_w: int,
        wm_h: int,
        position: WatermarkPosition,
        margin: int,
    ) -> Tuple[int, int]:
        """Calculate watermark position."""
        positions = {
            WatermarkPosition.TOP_LEFT: (margin, margin + wm_h),
            WatermarkPosition.TOP_CENTER: ((img_w - wm_w) // 2, margin + wm_h),
            WatermarkPosition.TOP_RIGHT: (img_w - wm_w - margin, margin + wm_h),
            WatermarkPosition.MIDDLE_LEFT: (margin, (img_h + wm_h) // 2),
            WatermarkPosition.CENTER: ((img_w - wm_w) // 2, (img_h + wm_h) // 2),
            WatermarkPosition.MIDDLE_RIGHT: (
                img_w - wm_w - margin,
                (img_h + wm_h) // 2,
            ),
            WatermarkPosition.BOTTOM_LEFT: (margin, img_h - margin),
            WatermarkPosition.BOTTOM_CENTER: ((img_w - wm_w) // 2, img_h - margin),
            WatermarkPosition.BOTTOM_RIGHT: (img_w - wm_w - margin, img_h - margin),
        }
        return positions.get(position, positions[WatermarkPosition.BOTTOM_RIGHT])

    def _blend_watermark(
        self, image: np.ndarray, watermark: np.ndarray, x: int, y: int, opacity: float
    ):
        """Blend watermark onto image with alpha channel support."""
        wm_h, wm_w = watermark.shape[:2]

        # Get region of interest
        roi = image[y : y + wm_h, x : x + wm_w]

        if watermark.shape[2] == 4:
            # BGRA watermark - use alpha channel
            alpha = watermark[:, :, 3:4] / 255.0 * opacity
            bgr = watermark[:, :, :3]

            # Blend
            blended = (bgr * alpha + roi * (1 - alpha)).astype(np.uint8)
            image[y : y + wm_h, x : x + wm_w] = blended
        else:
            # BGR watermark - simple blend
            blended = cv2.addWeighted(watermark[:, :, :3], opacity, roi, 1 - opacity, 0)
            image[y : y + wm_h, x : x + wm_w] = blended

    def create_tiled_watermark(
        self,
        image: np.ndarray,
        text: str,
        spacing: int = 200,
        angle: float = -45,
        font_scale: float = 0.8,
        font_path: str = "",
        color: Tuple[int, int, int] = (128, 128, 128),
        opacity: float = 0.3,
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
        if text and any(ord(ch) > 127 for ch in text):
            pil_result = self._create_tiled_watermark_pillow(
                image,
                text=text,
                spacing=spacing,
                angle=angle,
                font_scale=font_scale,
                font_path=font_path,
                color=color,
                opacity=opacity,
            )
            if pil_result is not None:
                return pil_result

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
                    cv2.putText(
                        overlay, text, (rx, ry), font, font_scale, color, thickness
                    )

        # Apply opacity
        cv2.addWeighted(overlay, opacity, result, 1 - opacity, 0, result)

        return result

    def _create_tiled_watermark_pillow(
        self,
        image: np.ndarray,
        text: str,
        spacing: int,
        angle: float,
        font_scale: float,
        font_path: str,
        color: Tuple[int, int, int],
        opacity: float,
    ) -> Optional[np.ndarray]:
        """Create a tiled Unicode watermark using Pillow (supports non-ASCII)."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            logger.warning(f"Pillow not available for Unicode tiled watermark: {e}")
            return None

        if image is None or image.size == 0:
            return None

        try:
            import math

            height, width = image.shape[:2]
            base = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).convert(
                "RGBA"
            )

            diag = int(math.hypot(width, height))
            canvas = max(diag + int(spacing) * 2, 1)
            tile = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tile)

            font_size = max(10, int(32 * float(font_scale)))
            font_path = font_path or self._find_default_windows_font()
            font = None
            if font_path:
                font = self._get_cached_font(ImageFont, font_path, font_size)
            if font is None:
                font = ImageFont.load_default()

            b, g, r = color  # BGR -> RGBA
            fill = (int(r), int(g), int(b), int(255 * float(opacity)))

            step = max(10, int(spacing))
            for y in range(0, canvas, step):
                for x in range(0, canvas, step):
                    draw.text((x, y), text, font=font, fill=fill)

            rotated = tile.rotate(float(angle), resample=Image.BICUBIC, expand=False)

            left = max(0, (canvas - width) // 2)
            top = max(0, (canvas - height) // 2)
            overlay = rotated.crop((left, top, left + width, top + height))

            combined = Image.alpha_composite(base, overlay).convert("RGB")
            out = cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)
            return out
        except Exception as e:
            logger.warning(f"Unicode tiled watermark failed, falling back to OpenCV: {e}")
            return None

    def preview_watermark(
        self,
        image: np.ndarray,
        text_settings: Optional[TextWatermarkSettings] = None,
        image_settings: Optional[ImageWatermarkSettings] = None,
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
