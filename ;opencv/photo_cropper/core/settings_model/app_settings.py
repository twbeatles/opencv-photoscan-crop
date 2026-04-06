#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings management module for Photo Cropper.

Provides dataclasses and managers for application settings persistence.
"""

from __future__ import annotations

import json
import os
import logging
import platform
from dataclasses import dataclass, field, asdict, fields
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

def _filter_dataclass_kwargs(dataclass_type, value: Any) -> Dict[str, Any]:
    """
    Filter a dict to only the keys accepted by the given dataclass.

    This makes settings loading forward-compatible when newer versions add fields.
    """
    if not isinstance(value, dict):
        return {}
    allowed = {f.name for f in fields(dataclass_type)}
    return {k: v for k, v in value.items() if k in allowed}


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

    # Detection mode presets (trade accuracy vs speed)
    # - fast: minimize extra scoring/fallbacks
    # - balanced: enable robust quad scoring + background-mask fallback
    # - accurate: enable heavier fallbacks (e.g., Hough) and stricter scoring
    detection_mode: str = "balanced"

    # Canny edge detection
    canny_min: int = 50
    canny_max: int = 150

    # Background mask threshold offset from corner mean (higher = stricter fg selection)
    bg_mask_delta: float = 30.0

    # Adaptive threshold fallback tuning
    adaptive_block_size: int = 15  # Must be odd
    adaptive_c: float = 4.0
    
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
    
    def __post_init__(self):
        """Validate and clamp settings to valid ranges."""
        if self.detection_mode not in ("fast", "balanced", "accurate"):
            self.detection_mode = "balanced"

        # Canny thresholds: 1-255, min < max
        self.canny_min = max(1, min(254, self.canny_min))
        self.canny_max = max(2, min(255, self.canny_max))
        if self.canny_min >= self.canny_max:
            self.canny_max = self.canny_min + 1

        # Background/adaptive threshold tuning
        self.bg_mask_delta = max(5.0, min(80.0, float(self.bg_mask_delta)))
        self.adaptive_block_size = max(3, min(61, int(self.adaptive_block_size)))
        if self.adaptive_block_size % 2 == 0:
            self.adaptive_block_size += 1
            if self.adaptive_block_size > 61:
                self.adaptive_block_size = 61
        self.adaptive_c = max(-20.0, min(20.0, float(self.adaptive_c)))
        
        # CLAHE: clip_limit > 0, grid_size >= 2
        self.clahe_clip_limit = max(0.1, min(10.0, self.clahe_clip_limit))
        self.clahe_grid_size = max(2, min(16, self.clahe_grid_size))
        
        # Corner detection: block_size >= 2, k > 0
        self.corner_block_size = max(2, min(10, self.corner_block_size))
        self.corner_k = max(0.01, min(0.1, self.corner_k))
        
        # Contour scoring: must be valid option
        if self.contour_scoring not in ("basic", "enhanced", "strict"):
            self.contour_scoring = "enhanced"
        
        # Area ratios: 0 < min < max <= 1
        self.min_area_ratio = max(0.01, min(0.9, self.min_area_ratio))
        self.max_area_ratio = max(0.1, min(1.0, self.max_area_ratio))
        if self.min_area_ratio >= self.max_area_ratio:
            self.max_area_ratio = min(1.0, self.min_area_ratio + 0.1)


@dataclass
class ProcessingSettings:
    """Image processing settings."""
    auto_contrast: bool = True
    to_grayscale: bool = False
    apply_sharpening: bool = False
    sharpening_strength: float = 1.0
    denoise: bool = False
    denoise_strength: int = 10
    
    def __post_init__(self):
        """Validate and clamp settings to valid ranges."""
        # Sharpening strength: 0.1-5.0
        self.sharpening_strength = max(0.1, min(5.0, self.sharpening_strength))
        # Denoise strength: 1-30
        self.denoise_strength = max(1, min(30, self.denoise_strength))


@dataclass
class OutputSettings:
    """Output file settings."""
    output_format: str = "JPG"
    jpg_quality: int = 95
    png_compression: int = 6
    webp_quality: int = 90
    add_timestamp: bool = False
    preserve_metadata: bool = False
    
    def __post_init__(self):
        """Validate and clamp settings to valid ranges."""
        # Output format: must be valid
        if self.output_format.upper() not in ("JPG", "JPEG", "PNG", "WEBP"):
            self.output_format = "JPG"
        # Quality values: 1-100
        self.jpg_quality = max(1, min(100, self.jpg_quality))
        self.webp_quality = max(1, min(100, self.webp_quality))
        # PNG compression: 0-9
        self.png_compression = max(0, min(9, self.png_compression))


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
class DebugSettings:
    """Debug output settings (for detection/cropping diagnostics)."""

    enabled: bool = False
    save_detection_stages: bool = True
    save_candidate_overlays: bool = True
    output_dir: str = ""  # Optional. If empty, a default is chosen per caller.
    max_files: int = 200  # Max number of debug folders to keep (best-effort pruning).


@dataclass
class AdvancedProcessingSettings:
    """Advanced image processing settings for v8.0."""
    # Auto corrections
    auto_deskew: bool = False
    auto_color_correct: bool = False
    color_correct_method: str = "gray_world"  # gray_world, white_patch, histogram
    
    # Perspective
    perspective_correct: bool = True
    
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
    text_font_path: str = ""  # Optional .ttf/.otf path for Unicode text rendering (Pillow)
    text_font_scale: float = 1.0
    # Stored as RGB (OpenCV processing paths convert to BGR internally).
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
    max_wait_seconds: float = 30.0
    
    # Scheduler
    scheduler_enabled: bool = False
    schedule_type: str = "interval"  # once(next upcoming HH:MM), daily, interval, hourly
    schedule_time: str = "00:00"  # HH:MM format for daily/once(next upcoming time)
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

    def __post_init__(self):
        """Validate and clamp multi-photo settings."""
        self.min_photos = max(1, min(100, int(self.min_photos)))
        self.max_photos = max(self.min_photos, min(200, int(self.max_photos)))
        self.min_area_ratio = max(0.001, min(0.95, float(self.min_area_ratio)))
        self.max_area_ratio = max(self.min_area_ratio, min(1.0, float(self.max_area_ratio)))
        self.merge_distance = max(0, min(1000, int(self.merge_distance)))


# v9.0 Settings

@dataclass
class ClassificationSettings:
    """Image classification settings for v9.0."""
    enabled: bool = False
    model: str = "basic"  # basic, advanced (legacy custom aliases to advanced)
    auto_folder: bool = True  # Create category folders automatically
    categories_enabled: dict[str, bool] = field(default_factory=lambda: {
        "portrait": True,
        "landscape": True,
        "document": True,
        "blackwhite": True,
        "other": True
    })
    category_folders: dict[str, str] = field(default_factory=lambda: {
        "portrait": "인물",
        "landscape": "풍경",
        "document": "문서",
        "blackwhite": "흑백",
        "other": "기타",
    })
    min_confidence: float = 0.5

    def __post_init__(self):
        self.min_confidence = max(0.0, min(1.0, float(self.min_confidence)))
        model = str(self.model or "basic").lower()
        if model == "custom":
            model = "advanced"
        elif model not in ("basic", "advanced"):
            model = "basic"
        self.model = model

        default_enabled = {
            "portrait": True,
            "landscape": True,
            "document": True,
            "blackwhite": True,
            "other": True,
        }
        incoming_enabled = (
            self.categories_enabled if isinstance(self.categories_enabled, dict) else {}
        )
        self.categories_enabled = {
            key: bool(incoming_enabled.get(key, default_value))
            for key, default_value in default_enabled.items()
        }

        default_folders = {
            "portrait": "인물",
            "landscape": "풍경",
            "document": "문서",
            "blackwhite": "흑백",
            "other": "기타",
        }
        incoming_folders = (
            self.category_folders if isinstance(self.category_folders, dict) else {}
        )
        normalized_folders: dict[str, str] = {}
        for key, default_name in default_folders.items():
            raw_name = str(incoming_folders.get(key, "")).strip()
            normalized_folders[key] = raw_name or default_name
        self.category_folders = normalized_folders


@dataclass
class FaceDetectionSettings:
    """Face detection settings for v9.0."""
    enabled: bool = False
    use_dnn: bool = False  # Use DNN for more accurate detection
    auto_center_crop: bool = True  # Adjust crop to center on faces
    show_overlay: bool = True  # Show face rectangles in preview
    auto_rotate: bool = False  # Auto-rotate based on eye positions
    detect_eyes: bool = True
    min_face_size: int = 30

    def __post_init__(self):
        self.min_face_size = max(20, min(500, int(self.min_face_size)))


@dataclass
class SmartEnhancementSettings:
    """Smart enhancement settings for v9.0."""
    enabled: bool = False
    auto_preset: bool = True  # Automatically select preset based on classification
    default_preset: str = "none"  # Default preset if auto is off
    apply_to_batch: bool = True
    adjust_exposure: bool = True
    adjust_color_balance: bool = True
    strength: int = 50

    def __post_init__(self):
        self.strength = max(0, min(100, int(self.strength)))


@dataclass
class NotificationSettings:
    """System notification settings for v9.0."""
    enabled: bool = True
    play_sound: bool = True
    on_batch_complete: bool = True
    on_error: bool = True
    on_watch_mode: bool = True


@dataclass
class AppSettings:
    """Complete application settings."""
    # Core settings
    algorithm: AlgorithmSettings = field(default_factory=AlgorithmSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    filter: FilterSettings = field(default_factory=FilterSettings)
    ui: UISettings = field(default_factory=UISettings)
    debug: DebugSettings = field(default_factory=DebugSettings)
    
    # v8.0 settings
    advanced: AdvancedProcessingSettings = field(default_factory=AdvancedProcessingSettings)
    file_management: FileManagementSettings = field(default_factory=FileManagementSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    
    # v8.5 settings
    watermark: WatermarkSettings = field(default_factory=WatermarkSettings)
    resize: ResizeSettings = field(default_factory=ResizeSettings)
    watch_mode: WatchModeSettings = field(default_factory=WatchModeSettings)
    multi_photo: MultiPhotoSettings = field(default_factory=MultiPhotoSettings)
    
    # v9.0 settings
    classification: ClassificationSettings = field(default_factory=ClassificationSettings)
    face_detection: FaceDetectionSettings = field(default_factory=FaceDetectionSettings)
    smart_enhancement: SmartEnhancementSettings = field(default_factory=SmartEnhancementSettings)
    notification: NotificationSettings = field(default_factory=NotificationSettings)
    
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
            "debug": asdict(self.debug),
            "advanced": asdict(self.advanced),
            "file_management": asdict(self.file_management),
            "performance": asdict(self.performance),
            "watermark": asdict(self.watermark),
            "resize": asdict(self.resize),
            "watch_mode": asdict(self.watch_mode),
            "multi_photo": asdict(self.multi_photo),
            "classification": asdict(self.classification),
            "face_detection": asdict(self.face_detection),
            "smart_enhancement": asdict(self.smart_enhancement),
            "notification": asdict(self.notification),
            "last_input_path": self.last_input_path,
            "last_output_path": self.last_output_path,
            "create_backup": self.create_backup,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """Create settings from dictionary with defaults fallback."""
        try:
            algorithm = AlgorithmSettings(
                **_filter_dataclass_kwargs(AlgorithmSettings, data.get("algorithm", {}))
            )
        except TypeError:
            algorithm = AlgorithmSettings()
            
        try:
            processing = ProcessingSettings(
                **_filter_dataclass_kwargs(ProcessingSettings, data.get("processing", {}))
            )
        except TypeError:
            processing = ProcessingSettings()
            
        try:
            output = OutputSettings(
                **_filter_dataclass_kwargs(OutputSettings, data.get("output", {}))
            )
        except TypeError:
            output = OutputSettings()
            
        try:
            filter_settings = FilterSettings(
                **_filter_dataclass_kwargs(FilterSettings, data.get("filter", {}))
            )
        except TypeError:
            filter_settings = FilterSettings()
            
        try:
            ui = UISettings(
                **_filter_dataclass_kwargs(UISettings, data.get("ui", {}))
            )
        except TypeError:
            ui = UISettings()

        try:
            debug = DebugSettings(
                **_filter_dataclass_kwargs(DebugSettings, data.get("debug", {}))
            )
        except TypeError:
            debug = DebugSettings()
        
        # v8.0 settings
        try:
            advanced = AdvancedProcessingSettings(
                **_filter_dataclass_kwargs(
                    AdvancedProcessingSettings, data.get("advanced", {})
                )
            )
        except TypeError:
            advanced = AdvancedProcessingSettings()
        
        try:
            file_management = FileManagementSettings(
                **_filter_dataclass_kwargs(
                    FileManagementSettings, data.get("file_management", {})
                )
            )
        except TypeError:
            file_management = FileManagementSettings()
        
        try:
            performance = PerformanceSettings(
                **_filter_dataclass_kwargs(
                    PerformanceSettings, data.get("performance", {})
                )
            )
        except TypeError:
            performance = PerformanceSettings()
        
        # v8.5 settings
        try:
            watermark = WatermarkSettings(
                **_filter_dataclass_kwargs(WatermarkSettings, data.get("watermark", {}))
            )
        except TypeError:
            watermark = WatermarkSettings()
        
        try:
            resize = ResizeSettings(
                **_filter_dataclass_kwargs(ResizeSettings, data.get("resize", {}))
            )
        except TypeError:
            resize = ResizeSettings()
        
        try:
            watch_mode = WatchModeSettings(
                **_filter_dataclass_kwargs(WatchModeSettings, data.get("watch_mode", {}))
            )
        except TypeError:
            watch_mode = WatchModeSettings()
        
        try:
            multi_photo = MultiPhotoSettings(
                **_filter_dataclass_kwargs(
                    MultiPhotoSettings, data.get("multi_photo", {})
                )
            )
        except TypeError:
            multi_photo = MultiPhotoSettings()
        
        # v9.0 settings
        try:
            classification = ClassificationSettings(
                **_filter_dataclass_kwargs(
                    ClassificationSettings, data.get("classification", {})
                )
            )
        except TypeError:
            classification = ClassificationSettings()
        
        try:
            face_detection = FaceDetectionSettings(
                **_filter_dataclass_kwargs(
                    FaceDetectionSettings, data.get("face_detection", {})
                )
            )
        except TypeError:
            face_detection = FaceDetectionSettings()
        
        try:
            smart_enhancement = SmartEnhancementSettings(
                **_filter_dataclass_kwargs(
                    SmartEnhancementSettings, data.get("smart_enhancement", {})
                )
            )
        except TypeError:
            smart_enhancement = SmartEnhancementSettings()
        
        try:
            notification = NotificationSettings(
                **_filter_dataclass_kwargs(
                    NotificationSettings, data.get("notification", {})
                )
            )
        except TypeError:
            notification = NotificationSettings()
        
        return cls(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            debug=debug,
            advanced=advanced,
            file_management=file_management,
            performance=performance,
            watermark=watermark,
            resize=resize,
            watch_mode=watch_mode,
            multi_photo=multi_photo,
            classification=classification,
            face_detection=face_detection,
            smart_enhancement=smart_enhancement,
            notification=notification,
            last_input_path=data.get("last_input_path", ""),
            last_output_path=data.get("last_output_path", ""),
            create_backup=data.get("create_backup", False),
        )


class SettingsManager:
    """Manages loading and saving of application settings."""

    LEGACY_CONFIG_DIR = ".photo_cropper"
    LEGACY_CONFIG_FILE = "photo_cropper_settings.json"

    WINDOWS_CONFIG_DIR = "PhotoCropper"
    WINDOWS_CONFIG_FILE = "settings.json"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            config_file: Path to config file. Uses default if None.
        """
        if config_file is None:
            self.config_file = self._get_default_config_file()
        else:
            self.config_file = config_file

        self._legacy_config_files = self._get_legacy_config_files()
        
        self._settings: Optional[AppSettings] = None

    def _get_default_config_file(self) -> str:
        """Resolve the default settings file path for this OS."""
        system = platform.system()
        if system == "Windows":
            base = (
                os.environ.get("APPDATA")
                or os.environ.get("LOCALAPPDATA")
                or os.path.expanduser("~")
            )
            config_dir = os.path.join(base, self.WINDOWS_CONFIG_DIR)
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, self.WINDOWS_CONFIG_FILE)

        # Non-Windows: keep legacy location under home directory
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, self.LEGACY_CONFIG_DIR)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, self.LEGACY_CONFIG_FILE)

    def _get_legacy_config_files(self) -> list[str]:
        """Possible legacy config paths to migrate from."""
        paths: list[str] = []

        # Legacy path used by previous versions: ~/.photo_cropper/photo_cropper_settings.json
        home_dir = os.path.expanduser("~")
        legacy_dir = os.path.join(home_dir, self.LEGACY_CONFIG_DIR)
        paths.append(os.path.join(legacy_dir, self.LEGACY_CONFIG_FILE))

        # Some docs referenced %APPDATA%\\PhotoCropper\\settings.json; consider alternate legacy names.
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(os.path.join(appdata, self.WINDOWS_CONFIG_DIR, self.LEGACY_CONFIG_FILE))

        # De-duplicate and remove the current target file.
        normalized = []
        for p in paths:
            try:
                if os.path.abspath(p) == os.path.abspath(self.config_file):
                    continue
            except Exception:
                pass
            if p not in normalized:
                normalized.append(p)
        return normalized
    
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

            # Migration: load from legacy config if present, then save to new path.
            for legacy_path in self._legacy_config_files:
                if not legacy_path or not os.path.exists(legacy_path):
                    continue
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    settings = AppSettings.from_dict(data)
                    logger.info(f"Migrating settings from {legacy_path} -> {self.config_file}")
                    self.save(settings)
                    return settings
                except Exception as e:
                    logger.warning(f"Settings migration failed ({legacy_path}): {e}")
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
