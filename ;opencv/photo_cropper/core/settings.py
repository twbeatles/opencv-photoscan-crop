#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings management module for Photo Cropper.

Provides dataclasses and managers for application settings persistence.
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ContourScoringMethod(Enum):
    """Contour scoring method enumeration."""
    BASIC = "basic"
    ENHANCED = "enhanced"
    STRICT = "strict"


class OutputFormat(Enum):
    """Output image format enumeration."""
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"


@dataclass
class AlgorithmSettings:
    """Algorithm-related settings."""
    # Canny edge detection
    canny_min: int = 50
    canny_max: int = 150
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    use_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    
    # Multi-scale edge detection
    multi_scale_edge: bool = True
    
    # Corner detection
    use_corner_detection: bool = False
    corner_block_size: int = 2
    corner_k: float = 0.04
    
    # Contour scoring
    contour_scoring: str = "enhanced"
    
    # Area ratios
    min_area_ratio: float = 0.1
    max_area_ratio: float = 0.95


@dataclass
class ProcessingSettings:
    """Image processing settings."""
    auto_contrast: bool = True
    to_grayscale: bool = False
    apply_sharpening: bool = False
    sharpening_strength: float = 1.0
    denoise: bool = False
    denoise_strength: int = 10


@dataclass
class OutputSettings:
    """Output file settings."""
    output_format: str = "JPG"
    jpg_quality: int = 95
    png_compression: int = 6
    webp_quality: int = 90
    add_timestamp: bool = False
    preserve_metadata: bool = False


@dataclass
class FilterSettings:
    """Image filtering settings."""
    skip_small_images: bool = True
    min_image_size: int = 100
    max_image_size: int = 0  # 0 = no limit
    skip_processed: bool = False


@dataclass
class UISettings:
    """UI-related settings."""
    theme: str = "dark"
    language: str = "ko"
    preview_quality: int = 80
    show_histogram: bool = False
    show_contour_overlay: bool = True
    auto_preview: bool = True
    confirm_before_process: bool = True


@dataclass
class AppSettings:
    """Complete application settings."""
    # Sub-settings
    algorithm: AlgorithmSettings = field(default_factory=AlgorithmSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    filter: FilterSettings = field(default_factory=FilterSettings)
    ui: UISettings = field(default_factory=UISettings)
    
    # Path settings
    last_input_path: str = ""
    last_output_path: str = ""
    create_backup: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "algorithm": asdict(self.algorithm),
            "processing": asdict(self.processing),
            "output": asdict(self.output),
            "filter": asdict(self.filter),
            "ui": asdict(self.ui),
            "last_input_path": self.last_input_path,
            "last_output_path": self.last_output_path,
            "create_backup": self.create_backup,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """Create settings from dictionary with defaults fallback."""
        try:
            algorithm = AlgorithmSettings(**data.get("algorithm", {}))
        except TypeError:
            algorithm = AlgorithmSettings()
            
        try:
            processing = ProcessingSettings(**data.get("processing", {}))
        except TypeError:
            processing = ProcessingSettings()
            
        try:
            output = OutputSettings(**data.get("output", {}))
        except TypeError:
            output = OutputSettings()
            
        try:
            filter_settings = FilterSettings(**data.get("filter", {}))
        except TypeError:
            filter_settings = FilterSettings()
            
        try:
            ui = UISettings(**data.get("ui", {}))
        except TypeError:
            ui = UISettings()
        
        return cls(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            last_input_path=data.get("last_input_path", ""),
            last_output_path=data.get("last_output_path", ""),
            create_backup=data.get("create_backup", False),
        )


class SettingsManager:
    """Manages loading and saving of application settings."""
    
    DEFAULT_CONFIG_FILE = "photo_cropper_settings.json"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            config_file: Path to config file. Uses default if None.
        """
        if config_file is None:
            # Use user's home directory for config
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".photo_cropper")
            os.makedirs(config_dir, exist_ok=True)
            self.config_file = os.path.join(config_dir, self.DEFAULT_CONFIG_FILE)
        else:
            self.config_file = config_file
        
        self._settings: Optional[AppSettings] = None
    
    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading if necessary."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings
    
    @settings.setter
    def settings(self, value: AppSettings):
        """Set current settings."""
        self._settings = value
    
    def load(self) -> AppSettings:
        """
        Load settings from file.
        
        Returns:
            AppSettings instance (defaults if file doesn't exist or is invalid).
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Settings loaded from {self.config_file}")
                    return AppSettings.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Settings file JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Settings load error: {e}")
        
        logger.info("Using default settings")
        return AppSettings()
    
    def save(self, settings: Optional[AppSettings] = None) -> bool:
        """
        Save settings to file.
        
        Args:
            settings: Settings to save. Uses current settings if None.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        if settings is None:
            settings = self._settings
        
        if settings is None:
            logger.warning("No settings to save")
            return False
        
        try:
            # Ensure directory exists
            config_dir = os.path.dirname(self.config_file)
            if config_dir:  # Only makedirs if path is not empty
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._settings = settings
            logger.info(f"Settings saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Settings save error: {e}")
            return False
    
    def reset_to_defaults(self) -> AppSettings:
        """
        Reset settings to defaults.
        
        Returns:
            Default AppSettings instance.
        """
        self._settings = AppSettings()
        logger.info("Settings reset to defaults")
        return self._settings
    
    def get_default(self) -> AppSettings:
        """Get default settings without modifying current."""
        return AppSettings()


# Convenience function for quick access
_default_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the default settings manager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = SettingsManager()
    return _default_manager
