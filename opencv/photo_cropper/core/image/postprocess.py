from __future__ import annotations

import os
import cv2
import numpy as np
import logging
import traceback
import json
import time
import math
from typing import Optional, Tuple, List, Dict, Any

from ..settings_model import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
    DebugSettings,
)
from ..advanced import AdvancedImageProcessor, GPUAccelerator
from .types import CropResult, DetectionStage, PreviewProcessResult

logger = logging.getLogger(__name__)


class ImagePostprocessMixin:
    def process_image(
        self: Any,
        image_path: str,
        *,
        debug_dir: Optional[str] = None,
        debug_tag: str = "",
    ) -> CropResult:
        """
        Process image with multi-stage detection algorithm.

        Args:
            image_path: Path to input image
            debug_dir: Base output directory for debug artifacts. If empty string, a default is chosen.
            debug_tag: Optional tag recorded in debug meta.json.

        Returns:
            CropResult with processed image or error
        """
        image = self.load_image(image_path)
        if image is None:
            return CropResult(False, message="Failed to load image.")
        return self._process_loaded_image(
            image,
            image_path,
            debug_dir=debug_dir,
            debug_tag=debug_tag,
        )
    def process_preview(
        self: Any,
        image_path: str,
        max_size: int = 800,
        debug_tag: str = "preview",
        fast_preview: bool = True,
        preview_detection_max_mp: Optional[float] = None,
    ) -> PreviewProcessResult:
        """
        Build preview images and crop result in a single image-load pass.
        """
        image = self.load_image(image_path)
        if image is None:
            crop_result = CropResult(False, message="이미지를 불러올 수 없습니다.")
            return PreviewProcessResult(
                original_preview=None,
                overlay_preview=None,
                crop_result=crop_result,
                message=crop_result.message,
            )

        h, w = image.shape[:2]
        scale = min(max_size / w, max_size / h, 1.0)
        preview_size = (int(w * scale), int(h * scale))
        original_preview = cv2.resize(image, preview_size, interpolation=cv2.INTER_AREA)

        detection_image = image
        contour_scale_back = 1.0

        if fast_preview:
            max_mp = max(1.0, float(preview_detection_max_mp or self.PREVIEW_DETECTION_MAX_MP))
            current_mp = (h * w) / 1_000_000.0
            if current_mp > max_mp:
                detect_scale = math.sqrt(max_mp / current_mp)
                detect_w = max(1, int(w * detect_scale))
                detect_h = max(1, int(h * detect_scale))
                detection_image = cv2.resize(
                    image,
                    (detect_w, detect_h),
                    interpolation=cv2.INTER_AREA,
                )
                contour_scale_back = w / float(detect_w)

        debug_base = "" if self.debug.enabled else None
        crop_result = self._process_loaded_image(
            detection_image,
            image_path,
            debug_dir=debug_base,
            debug_tag=debug_tag,
        )

        if crop_result.contour_points is not None and contour_scale_back != 1.0:
            crop_result.contour_points = crop_result.contour_points * contour_scale_back

        # Keep preview metadata aligned to the source image dimensions.
        crop_result.original_size = (w, h)

        # Preview output is display-only; keep it bounded for UI responsiveness.
        if crop_result.image is not None:
            ch, cw = crop_result.image.shape[:2]
            display_scale = min(max_size / cw, max_size / ch, 1.0)
            if display_scale < 1.0:
                display_size = (
                    max(1, int(cw * display_scale)),
                    max(1, int(ch * display_scale)),
                )
                crop_result.image = cv2.resize(
                    crop_result.image,
                    display_size,
                    interpolation=cv2.INTER_AREA,
                )
                crop_result.cropped_size = (
                    crop_result.image.shape[1],
                    crop_result.image.shape[0],
                )

        if crop_result.success and crop_result.contour_points is not None:
            overlay = original_preview.copy()
            scaled_contour = (crop_result.contour_points * scale).astype(np.int32)
            cv2.polylines(overlay, [scaled_contour], True, (0, 255, 0), 2)
            for point in scaled_contour:
                cv2.circle(overlay, tuple(point), 5, (0, 0, 255), -1)
        else:
            overlay = original_preview.copy()

        return PreviewProcessResult(
            original_preview=original_preview,
            overlay_preview=overlay,
            crop_result=crop_result,
            message=crop_result.message,
        )
    def _apply_post_processing(self: Any, image: np.ndarray) -> np.ndarray:
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
            denoise_strength = float(self.proc.denoise_strength)
            if len(result.shape) == 2:
                # Use positional args for broad OpenCV Python binding compatibility.
                result = cv2.fastNlMeansDenoising(
                    result, None, denoise_strength, 7, 21
                )
            else:
                # OpenCV 4.13+ rejects some keyword names in this API.
                result = cv2.fastNlMeansDenoisingColored(
                    result,
                    None,
                    denoise_strength,
                    denoise_strength,
                    7,
                    21,
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
    def get_preview_with_contour(
        self: Any, image_path: str, max_size: int = 800
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
            preview_result = self.process_preview(
                image_path,
                max_size=max_size,
                debug_tag="preview_legacy",
            )
            return (
                preview_result.original_preview,
                preview_result.overlay_preview,
                preview_result.message,
            )
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return None, None, f"미리보기 오류: {str(e)}"
