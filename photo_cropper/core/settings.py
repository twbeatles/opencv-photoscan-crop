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
    open_output_on_complete: bool = False  # Auto-open output folder after batch


@dataclass
class AdvancedProcessingSettings:
    """Advanced image processing settings for v8.0."""
    # Auto corrections
    auto_deskew: bool = False
    auto_color_correct: bool = False
    color_correct_method: str = "gray_world"  # gray_world, white_patch, histogram
    
    # Perspective
    perspective_correct: bool = False
    
    # Enhanced processing
    enhanced_denoise: bool = False
    enhanced_denoise_strength: int = 10
    restore_old_photo: bool = False
    
    # Sharpening
    enhanced_sharpen: bool = False
    sharpen_strength: float = 1.0
    
    # Border removal
    auto_crop_borders: bool = False
    border_color: str = "auto"  # auto, white, black


@dataclass
class FileManagementSettings:
    """File management settings for v8.0."""
    # Recursive processing
    recursive_search: bool = False
    
    # Naming rules
    use_naming_rules: bool = False
    naming_prefix: str = ""
    naming_suffix: str = "_cropped"
    naming_use_counter: bool = False
    naming_counter_padding: int = 3
    naming_use_date: bool = False
    naming_date_format: str = "%Y%m%d"
    naming_preserve_original: bool = True
    
    # Failed file handling
    move_failed_files: bool = False
    failed_folder_name: str = "_failed"
    copy_failed_instead_of_move: bool = True
    
    # Logging
    enable_logging: bool = True
    log_format: str = "json"  # json, csv
    log_directory: str = ""  # Empty = output directory


@dataclass
class PerformanceSettings:
    """Performance and optimization settings for v8.0."""
    # GPU acceleration
    use_gpu: bool = False
    gpu_device_id: int = 0
    
    # Multithreading
    enable_multithreading: bool = True
    thread_count: int = 4  # 0 = auto (CPU count)
    
    # Memory management
    max_image_size_mb: int = 100  # Skip images larger than this
    downscale_large_images: bool = True
    downscale_threshold_mp: float = 50.0  # Megapixels


@dataclass
class WatermarkSettings:
    """Watermark settings for v8.5."""
    # Enable
    enabled: bool = False
    
    # Text watermark
    text: str = ""
    text_font_scale: float = 1.0
    text_color_r: int = 255
    text_color_g: int = 255
    text_color_b: int = 255
    text_shadow: bool = True
    
    # Image watermark
    image_path: str = ""
    image_scale: float = 0.2
    
    # Common settings
    position: str = "bottom_right"  # top_left, top_center, top_right, etc.
    opacity: float = 0.5
    margin: int = 20
    
    # Tiled watermark
    tiled: bool = False
    tile_spacing: int = 200
    tile_angle: float = -45


@dataclass
class ResizeSettings:
    """Resize settings for v8.5."""
    enabled: bool = False
    mode: str = "none"  # none, fit, fill, stretch, width, height, percentage, max_dimension
    width: int = 0
    height: int = 0
    percentage: float = 100.0
    max_dimension: int = 0
    maintain_aspect: bool = True
    upscale_allowed: bool = False
    jpeg_compatible: bool = False  # Ensure dimensions are multiples of 8


@dataclass
class WatchModeSettings:
    """Folder watch mode settings for v8.5."""
    enabled: bool = False
    watch_path: str = ""
    output_path: str = ""
    recursive: bool = False
    auto_process: bool = True
    debounce_ms: int = 500
    
    # Scheduler
    scheduler_enabled: bool = False
    schedule_type: str = "interval"  # once, daily, interval, hourly
    schedule_time: str = "00:00"  # HH:MM format for daily/once
    schedule_interval_minutes: int = 60


@dataclass 
class MultiPhotoSettings:
    """Multi-photo detection settings for v8.5."""
    enabled: bool = False
    min_photos: int = 1
    max_photos: int = 20
    min_area_ratio: float = 0.02
    max_area_ratio: float = 0.8
    merge_distance: int = 50
    separate_output_folders: bool = False


@dataclass
class AppSettings:
    """Complete application settings."""
    # Core settings
    algorithm: AlgorithmSettings = field(default_factory=AlgorithmSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    filter: FilterSettings = field(default_factory=FilterSettings)
    ui: UISettings = field(default_factory=UISettings)
    
    # v8.0 settings
    advanced: AdvancedProcessingSettings = field(default_factory=AdvancedProcessingSettings)
    file_management: FileManagementSettings = field(default_factory=FileManagementSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    
    # v8.5 settings
    watermark: WatermarkSettings = field(default_factory=WatermarkSettings)
    resize: ResizeSettings = field(default_factory=ResizeSettings)
    watch_mode: WatchModeSettings = field(default_factory=WatchModeSettings)
    multi_photo: MultiPhotoSettings = field(default_factory=MultiPhotoSettings)
    
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
            "advanced": asdict(self.advanced),
            "file_management": asdict(self.file_management),
            "performance": asdict(self.performance),
            "watermark": asdict(self.watermark),
            "resize": asdict(self.resize),
            "watch_mode": asdict(self.watch_mode),
            "multi_photo": asdict(self.multi_photo),
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
        
        # v8.0 settings
        try:
            advanced = AdvancedProcessingSettings(**data.get("advanced", {}))
        except TypeError:
            advanced = AdvancedProcessingSettings()
        
        try:
            file_management = FileManagementSettings(**data.get("file_management", {}))
        except TypeError:
            file_management = FileManagementSettings()
        
        try:
            performance = PerformanceSettings(**data.get("performance", {}))
        except TypeError:
            performance = PerformanceSettings()
        
        # v8.5 settings
        try:
            watermark = WatermarkSettings(**data.get("watermark", {}))
        except TypeError:
            watermark = WatermarkSettings()
        
        try:
            resize = ResizeSettings(**data.get("resize", {}))
        except TypeError:
            resize = ResizeSettings()
        
        try:
            watch_mode = WatchModeSettings(**data.get("watch_mode", {}))
        except TypeError:
            watch_mode = WatchModeSettings()
        
        try:
            multi_photo = MultiPhotoSettings(**data.get("multi_photo", {}))
        except TypeError:
            multi_photo = MultiPhotoSettings()
        
        return cls(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            advanced=advanced,
            file_management=file_management,
            performance=performance,
            watermark=watermark,
            resize=resize,
            watch_mode=watch_mode,
            multi_photo=multi_photo,
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
