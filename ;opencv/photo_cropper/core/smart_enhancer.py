#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Enhancer for Photo Cropper v9.0.

Provides intelligent image enhancement presets using OpenCV:
- Old photo restoration
- Sharpening enhancement
- B&W photo restoration
- Document optimization
- Portrait enhancement
"""

import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EnhancementPreset(Enum):
    """Enhancement preset enumeration."""
    OLD_PHOTO = "old_photo"
    SHARPEN = "sharpen"
    BW_RESTORE = "bw_restore"
    DOCUMENT = "document"
    PORTRAIT = "portrait"
    AUTO = "auto"
    NONE = "none"


@dataclass
class EnhancementSettings:
    """Settings for a specific enhancement."""
    # Denoising
    denoise_strength: int = 10
    denoise_color: int = 10
    
    # Contrast
    clahe_enabled: bool = True
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    
    # Sharpening
    sharpen_enabled: bool = False
    sharpen_amount: float = 1.0
    sharpen_radius: float = 1.0
    
    # Color correction
    auto_white_balance: bool = False
    saturation_boost: float = 1.0
    
    # Restoration
    scratch_removal: bool = False
    color_restoration: bool = False
    
    # Document specific
    binarize: bool = False
    binarize_threshold: int = 127


@dataclass
class EnhancementResult:
    """Result of enhancement operation."""
    image: np.ndarray
    preset_used: EnhancementPreset
    applied_effects: List[str] = field(default_factory=list)
    before_histogram: Optional[np.ndarray] = None
    after_histogram: Optional[np.ndarray] = None


class SmartEnhancer:
    """
    Intelligent image enhancement engine.
    
    Uses OpenCV for all processing:
    - CLAHE for contrast enhancement
    - fastNlMeansDenoisingColored for noise reduction
    - Unsharp masking for sharpening
    - Color space manipulation for restoration
    """
    
    # Preset configurations
    PRESETS: Dict[EnhancementPreset, EnhancementSettings] = {
        EnhancementPreset.OLD_PHOTO: EnhancementSettings(
            denoise_strength=12,
            denoise_color=12,
            clahe_enabled=True,
            clahe_clip_limit=3.0,
            sharpen_enabled=True,
            sharpen_amount=0.5,
            auto_white_balance=True,
            saturation_boost=1.2,
            color_restoration=True
        ),
        EnhancementPreset.SHARPEN: EnhancementSettings(
            denoise_strength=5,
            clahe_enabled=True,
            clahe_clip_limit=2.0,
            sharpen_enabled=True,
            sharpen_amount=1.5,
            sharpen_radius=1.0
        ),
        EnhancementPreset.BW_RESTORE: EnhancementSettings(
            denoise_strength=15,
            clahe_enabled=True,
            clahe_clip_limit=2.5,
            clahe_grid_size=8,
            sharpen_enabled=True,
            sharpen_amount=0.8,
            scratch_removal=True
        ),
        EnhancementPreset.DOCUMENT: EnhancementSettings(
            denoise_strength=8,
            clahe_enabled=True,
            clahe_clip_limit=1.5,
            sharpen_enabled=True,
            sharpen_amount=1.2,
            auto_white_balance=True,
            binarize=False  # Optional, configurable
        ),
        EnhancementPreset.PORTRAIT: EnhancementSettings(
            denoise_strength=8,
            denoise_color=10,
            clahe_enabled=True,
            clahe_clip_limit=1.5,
            sharpen_enabled=True,
            sharpen_amount=0.3,  # Subtle sharpening
            saturation_boost=1.1
        ),
        EnhancementPreset.NONE: EnhancementSettings()
    }
    
    # Category to preset mapping
    CATEGORY_PRESETS = {
        "portrait": EnhancementPreset.PORTRAIT,
        "landscape": EnhancementPreset.SHARPEN,
        "document": EnhancementPreset.DOCUMENT,
        "blackwhite": EnhancementPreset.BW_RESTORE,
        "other": EnhancementPreset.OLD_PHOTO
    }
    
    def __init__(self):
        """Initialize smart enhancer."""
        # Performance: Cache CLAHE objects by settings
        self._clahe_cache: Dict[Tuple[float, int], cv2.CLAHE] = {}
    
    def _get_clahe(self, clip_limit: float, grid_size: int) -> cv2.CLAHE:
        """Get or create cached CLAHE instance."""
        key = (clip_limit, grid_size)
        if key not in self._clahe_cache:
            self._clahe_cache[key] = cv2.createCLAHE(
                clipLimit=clip_limit,
                tileGridSize=(grid_size, grid_size)
            )
        return self._clahe_cache[key]
    
    def apply_preset(self, image: np.ndarray, 
                     preset: EnhancementPreset) -> EnhancementResult:
        """
        Apply enhancement preset to image.
        
        Args:
            image: Input BGR image
            preset: Enhancement preset to apply
            
        Returns:
            EnhancementResult with processed image
        """
        if image is None or image.size == 0:
            return EnhancementResult(
                image=image,
                preset_used=preset,
                applied_effects=[]
            )
        
        if preset == EnhancementPreset.NONE:
            return EnhancementResult(
                image=image.copy(),
                preset_used=preset,
                applied_effects=[]
            )
        
        settings = self.PRESETS.get(preset, self.PRESETS[EnhancementPreset.NONE])
        return self._apply_settings(image, settings, preset)
    
    def apply_custom(self, image: np.ndarray,
                     settings: EnhancementSettings) -> EnhancementResult:
        """
        Apply custom enhancement settings.
        
        Args:
            image: Input BGR image
            settings: Custom enhancement settings
            
        Returns:
            EnhancementResult with processed image
        """
        return self._apply_settings(image, settings, EnhancementPreset.AUTO)

    def apply_runtime_adjustments(
        self,
        image: np.ndarray,
        *,
        adjust_exposure: bool = True,
        adjust_color_balance: bool = True,
        strength: int = 50,
    ) -> np.ndarray:
        """
        Apply lightweight runtime adjustments controlled by UI options.

        This is intentionally conservative so existing successful outputs are not
        heavily altered.
        """
        if image is None or image.size == 0:
            return image

        level = max(0, min(100, int(strength))) / 100.0
        if level <= 0.0:
            return image

        result = image.copy()
        try:
            # Work in BGR 3-channel space for stable downstream behavior.
            if result.ndim == 2:
                result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
            elif result.ndim == 3 and result.shape[2] == 1:
                result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

            if adjust_exposure:
                # Nudge luminance toward a mid target using a bounded delta.
                lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                l = lab[:, :, 0].astype(np.float32)
                mean_l = float(np.mean(l))
                delta = np.clip((128.0 - mean_l) * (0.20 + 0.50 * level), -24.0, 24.0)
                lab[:, :, 0] = np.clip(l + delta, 0, 255).astype(np.uint8)
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            if adjust_color_balance:
                # Gray-world style channel balancing blended by strength.
                float_img = result.astype(np.float32)
                channel_means = np.mean(float_img, axis=(0, 1))
                mean_gray = float(np.mean(channel_means))
                gains = np.ones(3, dtype=np.float32)
                for i in range(3):
                    if channel_means[i] > 1e-6:
                        gains[i] = np.clip(mean_gray / channel_means[i], 0.85, 1.15)

                blend = 0.20 + 0.60 * level
                effective = 1.0 + (gains - 1.0) * blend
                float_img *= effective.reshape((1, 1, 3))
                result = np.clip(float_img, 0, 255).astype(np.uint8)
        except Exception as e:
            logger.warning(f"Runtime smart adjustments failed: {e}")
            return image

        return result
    
    def _apply_settings(self, image: np.ndarray,
                        settings: EnhancementSettings,
                        preset: EnhancementPreset) -> EnhancementResult:
        """
        Apply enhancement settings to image.
        
        Args:
            image: Input BGR image
            settings: Enhancement settings
            preset: Preset being applied
            
        Returns:
            EnhancementResult
        """
        result = image.copy()
        applied = []
        
        try:
            # 1. Denoising (first to reduce noise before enhancement)
            if settings.denoise_strength > 0:
                result = self._denoise(result, settings.denoise_strength, 
                                       settings.denoise_color)
                applied.append(f"노이즈 제거 (강도: {settings.denoise_strength})")
            
            # 2. Scratch removal for old photos
            if settings.scratch_removal:
                result = self._remove_scratches(result)
                applied.append("스크래치 제거")
            
            # 3. CLAHE contrast enhancement
            if settings.clahe_enabled:
                result = self._apply_clahe(result, settings.clahe_clip_limit,
                                          settings.clahe_grid_size)
                applied.append(f"대비 향상 (CLAHE)")
            
            # 4. Auto white balance
            if settings.auto_white_balance:
                result = self._auto_white_balance(result)
                applied.append("자동 화이트 밸런스")
            
            # 5. Color restoration for faded photos
            if settings.color_restoration:
                result = self._restore_colors(result)
                applied.append("색상 복원")
            
            # 6. Saturation boost
            if settings.saturation_boost != 1.0:
                result = self._adjust_saturation(result, settings.saturation_boost)
                applied.append(f"채도 조정 ({settings.saturation_boost:.1f}x)")
            
            # 7. Sharpening (last to preserve details)
            if settings.sharpen_enabled:
                result = self._sharpen(result, settings.sharpen_amount,
                                      settings.sharpen_radius)
                applied.append(f"선명도 향상 ({settings.sharpen_amount:.1f})")
            
            # 8. Document binarization (optional)
            if settings.binarize:
                result = self._binarize(result, settings.binarize_threshold)
                applied.append("이진화")
                
        except Exception as e:
            logger.error(f"Error during enhancement: {e}")
            applied.append(f"오류: {str(e)}")
        
        return EnhancementResult(
            image=result,
            preset_used=preset,
            applied_effects=applied
        )
    
    def _denoise(self, image: np.ndarray, strength: int, 
                 color_strength: int) -> np.ndarray:
        """
        Apply denoising using fastNlMeansDenoising.
        
        Args:
            image: Input image
            strength: Luminance denoising strength
            color_strength: Color denoising strength
            
        Returns:
            Denoised image
        """
        if len(image.shape) == 2 or image.shape[2] == 1:
            # Grayscale
            return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)
        else:
            # Color
            return cv2.fastNlMeansDenoisingColored(
                image, None, strength, color_strength, 7, 21
            )
    
    def _apply_clahe(self, image: np.ndarray, 
                     clip_limit: float, 
                     grid_size: int) -> np.ndarray:
        """
        Apply CLAHE contrast enhancement.
        
        Args:
            image: Input image
            clip_limit: CLAHE clip limit
            grid_size: CLAHE grid size
            
        Returns:
            Contrast-enhanced image
        """
        # Use cached CLAHE instance
        clahe = self._get_clahe(clip_limit, grid_size)
        
        if len(image.shape) == 2:
            return clahe.apply(image)
        
        # For color images, apply to L channel in LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    def _sharpen(self, image: np.ndarray, 
                 amount: float,
                 radius: float) -> np.ndarray:
        """
        Apply unsharp masking for sharpening.
        
        Args:
            image: Input image
            amount: Sharpening amount (0.0 to 3.0)
            radius: Blur radius for unsharp mask
            
        Returns:
            Sharpened image
        """
        # Create gaussian blur
        sigma = radius
        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        
        # Unsharp mask: sharpened = original + amount * (original - blurred)
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
        
        return np.clip(sharpened, 0, 255).astype(np.uint8)
    
    def _auto_white_balance(self, image: np.ndarray) -> np.ndarray:
        """
        Apply automatic white balance correction.
        
        Uses Gray World assumption.
        
        Args:
            image: Input BGR image
            
        Returns:
            White-balanced image
        """
        result = image.copy().astype(np.float32)
        
        # Calculate channel means
        avg_b = np.mean(result[:, :, 0])
        avg_g = np.mean(result[:, :, 1])
        avg_r = np.mean(result[:, :, 2])
        
        # Calculate gray value
        avg_gray = (avg_b + avg_g + avg_r) / 3
        
        # Scale channels
        if avg_b > 0:
            result[:, :, 0] *= (avg_gray / avg_b)
        if avg_g > 0:
            result[:, :, 1] *= (avg_gray / avg_g)
        if avg_r > 0:
            result[:, :, 2] *= (avg_gray / avg_r)
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _restore_colors(self, image: np.ndarray) -> np.ndarray:
        """
        Restore faded colors in old photos.
        
        Args:
            image: Input BGR image
            
        Returns:
            Color-restored image
        """
        # Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        
        # Enhance a and b channels (color)
        lab[:, :, 1] = np.clip((lab[:, :, 1] - 128) * 1.3 + 128, 0, 255)
        lab[:, :, 2] = np.clip((lab[:, :, 2] - 128) * 1.3 + 128, 0, 255)
        
        return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    
    def _adjust_saturation(self, image: np.ndarray, 
                          factor: float) -> np.ndarray:
        """
        Adjust image saturation.
        
        Args:
            image: Input BGR image
            factor: Saturation multiplier
            
        Returns:
            Saturation-adjusted image
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    def _remove_scratches(self, image: np.ndarray) -> np.ndarray:
        """
        Remove scratches and small defects.
        
        Uses morphological operations and inpainting.
        
        Args:
            image: Input image
            
        Returns:
            Scratch-free image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Detect scratches (thin bright/dark lines)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        
        # Detect bright scratches
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        _, bright_mask = cv2.threshold(tophat, 30, 255, cv2.THRESH_BINARY)
        
        # Detect dark scratches
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        _, dark_mask = cv2.threshold(blackhat, 30, 255, cv2.THRESH_BINARY)
        
        # Combine masks
        scratch_mask = cv2.bitwise_or(bright_mask, dark_mask)
        
        # Dilate mask slightly
        scratch_mask = cv2.dilate(scratch_mask, np.ones((3, 3), np.uint8))
        
        # Inpaint scratches
        result = cv2.inpaint(image, scratch_mask, 3, cv2.INPAINT_TELEA)
        
        return result
    
    def _binarize(self, image: np.ndarray, threshold: int) -> np.ndarray:
        """
        Binarize image for document processing.
        
        Args:
            image: Input image
            threshold: Binarization threshold
            
        Returns:
            Binarized image
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Adaptive thresholding for better results
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # Convert back to BGR if needed
        if len(image.shape) == 3:
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        return binary
    
    def recommend_preset(self, category: str) -> EnhancementPreset:
        """
        Recommend enhancement preset based on image category.
        
        Args:
            category: Image category string
            
        Returns:
            Recommended preset
        """
        return self.CATEGORY_PRESETS.get(category.lower(), EnhancementPreset.OLD_PHOTO)
    
    def auto_enhance(self, image: np.ndarray, 
                     category: Optional[str] = None) -> EnhancementResult:
        """
        Automatically enhance image based on its characteristics.
        
        Args:
            image: Input image
            category: Optional category hint
            
        Returns:
            EnhancementResult
        """
        if category:
            preset = self.recommend_preset(category)
        else:
            # Analyze image and choose preset
            preset = self._analyze_and_choose_preset(image)
        
        return self.apply_preset(image, preset)
    
    def _analyze_and_choose_preset(self, image: np.ndarray) -> EnhancementPreset:
        """
        Analyze image and choose best preset.
        
        Args:
            image: Input image
            
        Returns:
            Best matching preset
        """
        # Check if grayscale
        if len(image.shape) == 2:
            return EnhancementPreset.BW_RESTORE
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        
        # Low saturation = B&W or faded
        if np.mean(saturation) < 20:
            return EnhancementPreset.BW_RESTORE
        elif np.mean(saturation) < 50:
            return EnhancementPreset.OLD_PHOTO
        
        # Check contrast
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = np.std(gray)
        
        if contrast < 40:
            return EnhancementPreset.OLD_PHOTO
        
        # Default to sharpening
        return EnhancementPreset.SHARPEN
    
    def get_preset_names(self) -> Dict[EnhancementPreset, str]:
        """Get localized preset names."""
        return {
            EnhancementPreset.OLD_PHOTO: "오래된 사진 복원",
            EnhancementPreset.SHARPEN: "선명하게",
            EnhancementPreset.BW_RESTORE: "흑백 복원",
            EnhancementPreset.DOCUMENT: "문서 최적화",
            EnhancementPreset.PORTRAIT: "인물 보정",
            EnhancementPreset.AUTO: "자동",
            EnhancementPreset.NONE: "없음"
        }


# Singleton instance
_enhancer_instance: Optional[SmartEnhancer] = None


def get_smart_enhancer() -> SmartEnhancer:
    """Get global smart enhancer instance."""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = SmartEnhancer()
    return _enhancer_instance
