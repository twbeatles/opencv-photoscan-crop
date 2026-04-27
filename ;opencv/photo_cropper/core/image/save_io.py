#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Image save I/O utilities.

Separates file encoding/metadata persistence from ImageProcessor to keep
processing and I/O responsibilities decoupled.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)
EXIF_ORIENTATION_TAG = 0x0112


def resolve_save_codec(output_path: str, output_format: str) -> Tuple[str, str]:
    """Resolve encoder extension and normalized format with fallback."""
    extension = (os.path.splitext(output_path)[1] or "").lower()
    ext_to_fmt = {
        ".jpg": "JPG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }
    fmt_to_ext = {
        "JPG": ".jpg",
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
    }

    requested_fmt = str(output_format or "JPG").upper()
    resolved_fmt = requested_fmt if requested_fmt in fmt_to_ext else ext_to_fmt.get(extension, "JPG")
    encode_ext = extension if extension in ext_to_fmt else fmt_to_ext[resolved_fmt]
    return encode_ext, resolved_fmt


def copy_metadata_best_effort(source_path: str, output_path: str) -> None:
    """Copy EXIF/ICC metadata via Pillow (best-effort, non-fatal)."""
    if not source_path:
        return

    try:
        from PIL import Image
    except Exception as e:
        logger.warning(f"Metadata preservation unavailable (Pillow): {e}")
        return

    temp_path = f"{output_path}.meta_tmp"
    try:
        with Image.open(source_path) as src:
            exif_obj = src.getexif()
            exif = exif_obj.tobytes() if exif_obj else None
            icc_profile = src.info.get("icc_profile")

        if exif_obj:
            # Pixel data is already orientation-normalized during load/save, so
            # the copied metadata must not request another viewer rotation.
            exif_obj[EXIF_ORIENTATION_TAG] = 1
            exif = exif_obj.tobytes()

        if exif is None and icc_profile is None:
            return

        with Image.open(output_path) as dst:
            save_kwargs = {}
            if exif is not None:
                save_kwargs["exif"] = exif
            if icc_profile is not None:
                save_kwargs["icc_profile"] = icc_profile

            fmt = str(dst.format or "").upper()
            if not fmt:
                ext = os.path.splitext(output_path)[1].lower()
                if ext in (".jpg", ".jpeg"):
                    fmt = "JPEG"
                elif ext == ".png":
                    fmt = "PNG"
                elif ext == ".webp":
                    fmt = "WEBP"
                else:
                    fmt = "JPEG"

            if fmt == "JPEG":
                save_kwargs.setdefault("quality", "keep")
                save_kwargs.setdefault("subsampling", "keep")

            dst.save(temp_path, format=fmt, **save_kwargs)

        os.replace(temp_path, output_path)
    except Exception as e:
        logger.warning(f"Metadata copy skipped for '{output_path}': {e}")
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def save_image_unicode(
    image: np.ndarray,
    output_path: str,
    output_format: str = "JPG",
    jpg_quality: int = 95,
    png_compression: int = 6,
    webp_quality: int = 90,
    source_path: Optional[str] = None,
    preserve_metadata: bool = False,
) -> Tuple[bool, str, float]:
    """Save an image with Unicode path support and optional metadata copy."""
    try:
        encode_ext, fmt = resolve_save_codec(output_path, output_format)

        if fmt == "JPG" or fmt == "JPEG":
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpg_quality]
        elif fmt == "PNG":
            encode_params = [cv2.IMWRITE_PNG_COMPRESSION, png_compression]
        elif fmt == "WEBP":
            encode_params = [cv2.IMWRITE_WEBP_QUALITY, webp_quality]
        else:
            encode_params = []

        result, encoded_img = cv2.imencode(encode_ext, image, encode_params)
        if not result:
            return False, "인코딩 실패", 0.0

        output_parent = os.path.dirname(output_path)
        if output_parent:
            os.makedirs(output_parent, exist_ok=True)

        with open(output_path, mode="wb") as f:
            encoded_img.tofile(f)

        if preserve_metadata and source_path:
            copy_metadata_best_effort(source_path, output_path)

        file_size = os.path.getsize(output_path) / 1024.0
        return True, "저장 완료", file_size
    except Exception as e:
        logger.error(f"Image save error: {e}")
        return False, f"저장 오류: {str(e)}", 0.0


class ImageSaveMixin:
    @staticmethod
    def _resolve_save_codec(
        output_path: str,
        output_format: str,
    ) -> Tuple[str, str]:
        """Resolve encoder extension and format with extension fallback."""
        return resolve_save_codec(output_path, output_format)
    @staticmethod
    def _copy_metadata_best_effort(source_path: str, output_path: str) -> None:
        """Best-effort EXIF/ICC metadata copy via Pillow."""
        copy_metadata_best_effort(source_path, output_path)
    @staticmethod
    def save_image(
        image: np.ndarray,
        output_path: str,
        output_format: str = "JPG",
        jpg_quality: int = 95,
        png_compression: int = 6,
        webp_quality: int = 90,
        source_path: Optional[str] = None,
        preserve_metadata: bool = False,
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
            source_path: Source image path for metadata copy
            preserve_metadata: Best-effort EXIF/ICC preservation

        Returns:
            Tuple of (success, message, file_size_kb)
        """
        return save_image_unicode(
            image=image,
            output_path=output_path,
            output_format=output_format,
            jpg_quality=jpg_quality,
            png_compression=png_compression,
            webp_quality=webp_quality,
            source_path=source_path,
            preserve_metadata=preserve_metadata,
        )
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

