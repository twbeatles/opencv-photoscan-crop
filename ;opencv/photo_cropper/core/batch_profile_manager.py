#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Profile Manager for Photo Cropper v9.0.

Provides complete settings profile management:
- Profile creation, loading, saving
- Export/import for sharing
- Quick profile switching
- Category-specific settings
"""

import os
import json
import logging
import shutil
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

from .settings import AppSettings, get_settings_manager

logger = logging.getLogger(__name__)

_LEGACY_SETTINGS_KEY_ALIASES = {
    "advanced_processing": "advanced",
}


@dataclass
class BatchProfile:
    """
    Complete batch processing profile.
    
    Contains all application settings plus metadata
    and optional category-specific overrides.
    """
    name: str
    description: str = ""
    settings: Optional[Dict[str, Any]] = None
    category_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = ""
    modified_at: str = ""
    version: str = "9.0"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at
        if self.settings is None:
            self.settings = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "settings": self.settings,
            "category_rules": self.category_rules,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchProfile':
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            settings=data.get("settings", {}),
            category_rules=data.get("category_rules", {}),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
            version=data.get("version", "9.0")
        )


# Default profiles
DEFAULT_PROFILES: Dict[str, BatchProfile] = {
    "문서 스캔": BatchProfile(
        name="문서 스캔",
        description="스캔된 문서 처리에 최적화",
        settings={
            "algorithm": {
                "canny_min": 30,
                "canny_max": 100,
                "use_clahe": True,
                "clahe_clip_limit": 2.5
            },
            "processing": {
                "auto_contrast": True,
                "apply_sharpening": True,
                "sharpening_strength": 1.2
            },
            "output": {
                "output_format": "PNG",
                "png_compression": 6
            }
        }
    ),
    "오래된 앨범": BatchProfile(
        name="오래된 앨범",
        description="오래된 인화 사진 복원에 최적화",
        settings={
            "algorithm": {
                "canny_min": 40,
                "canny_max": 120,
                "use_clahe": True,
                "clahe_clip_limit": 3.0
            },
            "processing": {
                "denoise": True,
                "denoise_strength": 12
            },
            "advanced": {
                "auto_color_correct": True,
                "restore_old_photo": True
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 95
            }
        },
        category_rules={
            "portrait": {
                "processing": {"apply_sharpening": True, "sharpening_strength": 0.5}
            },
            "blackwhite": {
                "processing": {"to_grayscale": True}
            }
        }
    ),
    "고해상도 보존": BatchProfile(
        name="고해상도 보존",
        description="최대 품질 유지, 변환 최소화",
        settings={
            "algorithm": {
                "use_clahe": False,
                "multi_scale_edge": True
            },
            "processing": {
                "auto_contrast": False,
                "apply_sharpening": False,
                "denoise": False
            },
            "output": {
                "output_format": "PNG",
                "png_compression": 0,
                "preserve_metadata": True
            }
        }
    ),
    "빠른 처리": BatchProfile(
        name="빠른 처리",
        description="속도 최적화, 기본 설정",
        settings={
            "algorithm": {
                "use_clahe": False,
                "multi_scale_edge": False,
                "use_corner_detection": False
            },
            "processing": {
                "auto_contrast": False,
                "denoise": False
            },
            "performance": {
                "enable_multithreading": True,
                "thread_count": 8,
                "downscale_large_images": True
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 85
            }
        }
    ),
    "인물 사진": BatchProfile(
        name="인물 사진",
        description="인물 사진에 최적화, 얼굴 감지 활용",
        settings={
            "algorithm": {
                "use_clahe": True,
                "clahe_clip_limit": 1.5
            },
            "processing": {
                "denoise": True,
                "denoise_strength": 8,
                "apply_sharpening": True,
                "sharpening_strength": 0.3
            },
            "classification": {
                "enabled": True
            },
            "face_detection": {
                "enabled": True,
                "auto_center_crop": True
            },
            "output": {
                "output_format": "JPG",
                "jpg_quality": 95
            }
        }
    )
}


class BatchProfileManager:
    """
    Manager for batch processing profiles.
    
    Features:
    - Save/load profiles
    - Export/import for sharing
    - Quick profile switching
    - Category-specific rules
    """
    
    PROFILES_FILENAME = "batch_profiles.json"
    EXPORT_EXTENSION = ".photocropper"
    
    def __init__(self, profiles_dir: Optional[str] = None):
        """
        Initialize profile manager.
        
        Args:
            profiles_dir: Directory to store profiles
        """
        if profiles_dir:
            self._profiles_dir = profiles_dir
        else:
            # Use user's app data directory
            app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            self._profiles_dir = os.path.join(app_data, 'PhotoCropper', 'profiles')
        
        os.makedirs(self._profiles_dir, exist_ok=True)
        
        self._profiles: Dict[str, BatchProfile] = {}
        self._current_profile: Optional[str] = None
        
        self._load_profiles()
    
    def _get_profiles_path(self) -> str:
        """Get path to profiles file."""
        return os.path.join(self._profiles_dir, self.PROFILES_FILENAME)
    
    def _load_profiles(self):
        """Load profiles from file."""
        # Start with default profiles
        self._profiles = {name: profile for name, profile in DEFAULT_PROFILES.items()}
        
        # Load user profiles
        profiles_path = self._get_profiles_path()
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for name, profile_data in data.get('profiles', {}).items():
                    profile = BatchProfile.from_dict(profile_data)
                    self._normalize_profile(profile)
                    self._profiles[name] = profile
                
                self._current_profile = data.get('current_profile')
                logger.info(f"Loaded {len(data.get('profiles', {}))} user profiles")
                
            except Exception as e:
                logger.error(f"Error loading profiles: {e}")
    
    def _save_profiles(self):
        """Save profiles to file."""
        try:
            for profile in self._profiles.values():
                self._normalize_profile(profile)

            # Only save non-default profiles
            user_profiles = {
                name: profile.to_dict()
                for name, profile in self._profiles.items()
                if name not in DEFAULT_PROFILES
            }
            
            data = {
                'profiles': user_profiles,
                'current_profile': self._current_profile,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self._get_profiles_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved {len(user_profiles)} user profiles")
            
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")

    @classmethod
    def _normalize_settings_dict(cls, data: Any) -> Any:
        """Normalize legacy setting keys recursively."""
        if isinstance(data, dict):
            normalized: Dict[str, Any] = {}
            for key, value in data.items():
                mapped_key = _LEGACY_SETTINGS_KEY_ALIASES.get(key, key)
                normalized_value = cls._normalize_settings_dict(value)
                if (
                    mapped_key in normalized
                    and isinstance(normalized[mapped_key], dict)
                    and isinstance(normalized_value, dict)
                ):
                    normalized[mapped_key].update(normalized_value)
                else:
                    normalized[mapped_key] = normalized_value
            return normalized
        if isinstance(data, list):
            return [cls._normalize_settings_dict(item) for item in data]
        return data

    def _normalize_profile(self, profile: BatchProfile):
        """Normalize a profile in-place for backward compatibility."""
        profile.settings = self._normalize_settings_dict(profile.settings or {})
        normalized_rules: Dict[str, Dict[str, Any]] = {}
        for category, rule_data in (profile.category_rules or {}).items():
            normalized_rules[category] = self._normalize_settings_dict(rule_data or {})
        profile.category_rules = normalized_rules
    
    def list_profiles(self) -> List[str]:
        """Get list of profile names."""
        return list(self._profiles.keys())
    
    def get_profile(self, name: str) -> Optional[BatchProfile]:
        """Get profile by name."""
        return self._profiles.get(name)
    
    def get_current_profile(self) -> Optional[BatchProfile]:
        """Get currently active profile."""
        if self._current_profile:
            return self._profiles.get(self._current_profile)
        return None
    
    def set_current_profile(self, name: str) -> bool:
        """Set current profile."""
        if name in self._profiles:
            self._current_profile = name
            self._save_profiles()
            return True
        return False
    
    def is_default_profile(self, name: str) -> bool:
        """Check if profile is a default profile."""
        return name in DEFAULT_PROFILES
    
    def create_profile(self, name: str, 
                       settings: AppSettings,
                       description: str = "",
                       category_rules: Optional[Dict] = None) -> bool:
        """
        Create a new profile from current settings.
        
        Args:
            name: Profile name
            settings: Application settings
            description: Profile description
            category_rules: Optional category-specific rules
            
        Returns:
            True if created successfully
        """
        if not name:
            return False
        
        profile = BatchProfile(
            name=name,
            description=description,
            settings=self._normalize_settings_dict(settings.to_dict()),
            category_rules=category_rules or {}
        )
        self._normalize_profile(profile)
        
        self._profiles[name] = profile
        self._save_profiles()
        
        logger.info(f"Created profile: {name}")
        return True
    
    def update_profile(self, name: str, 
                       settings: Optional[AppSettings] = None,
                       description: Optional[str] = None,
                       category_rules: Optional[Dict] = None) -> bool:
        """
        Update an existing profile.
        
        Args:
            name: Profile name
            settings: New settings (optional)
            description: New description (optional)
            category_rules: New category rules (optional)
            
        Returns:
            True if updated successfully
        """
        if name not in self._profiles:
            return False
        
        if self.is_default_profile(name):
            logger.warning(f"Cannot modify default profile: {name}")
            return False
        
        profile = self._profiles[name]
        
        if settings is not None:
            profile.settings = self._normalize_settings_dict(settings.to_dict())
        if description is not None:
            profile.description = description
        if category_rules is not None:
            profile.category_rules = category_rules
        self._normalize_profile(profile)
        
        profile.modified_at = datetime.now().isoformat()
        
        self._save_profiles()
        return True
    
    def delete_profile(self, name: str) -> bool:
        """
        Delete a profile.
        
        Args:
            name: Profile name
            
        Returns:
            True if deleted successfully
        """
        if name not in self._profiles:
            return False
        
        if self.is_default_profile(name):
            logger.warning(f"Cannot delete default profile: {name}")
            return False
        
        del self._profiles[name]
        
        if self._current_profile == name:
            self._current_profile = None
        
        self._save_profiles()
        logger.info(f"Deleted profile: {name}")
        return True
    
    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """
        Rename a profile.
        
        Args:
            old_name: Current name
            new_name: New name
            
        Returns:
            True if renamed successfully
        """
        if old_name not in self._profiles or new_name in self._profiles:
            return False
        
        if self.is_default_profile(old_name):
            return False
        
        profile = self._profiles[old_name]
        profile.name = new_name
        profile.modified_at = datetime.now().isoformat()
        
        self._profiles[new_name] = profile
        del self._profiles[old_name]
        
        if self._current_profile == old_name:
            self._current_profile = new_name
        
        self._save_profiles()
        return True
    
    def apply_profile(self, name: str, settings: AppSettings) -> bool:
        """
        Apply profile to settings.
        
        Args:
            name: Profile name
            settings: Settings object to modify
            
        Returns:
            True if applied successfully
        """
        profile = self._profiles.get(name)
        if not profile:
            return False
        
        # Apply settings recursively
        self._apply_dict_to_settings(profile.settings, settings)
        
        self._current_profile = name
        logger.info(f"Applied profile: {name}")
        return True
    
    def apply_category_rules(self, name: str, 
                             category: str,
                             settings: AppSettings) -> bool:
        """
        Apply category-specific rules from profile.
        
        Args:
            name: Profile name
            category: Image category
            settings: Settings to modify
            
        Returns:
            True if rules were applied
        """
        profile = self._profiles.get(name)
        if not profile or not profile.category_rules:
            return False
        
        rules = profile.category_rules.get(category.lower())
        if not rules:
            return False
        
        self._apply_dict_to_settings(rules, settings)
        return True
    
    def _apply_dict_to_settings(self, data: Dict[str, Any], 
                                settings: AppSettings):
        """
        Recursively apply dictionary to settings object.
        
        Args:
            data: Settings dictionary
            settings: Settings object to modify
        """
        for key, value in data.items():
            resolved_key = _LEGACY_SETTINGS_KEY_ALIASES.get(key, key)
            if hasattr(settings, resolved_key):
                attr = getattr(settings, resolved_key)
                if isinstance(value, dict) and hasattr(attr, '__dataclass_fields__'):
                    # Nested dataclass
                    for sub_key, sub_value in value.items():
                        if hasattr(attr, sub_key):
                            setattr(attr, sub_key, sub_value)
                else:
                    setattr(settings, resolved_key, value)
    
    def export_profile(self, name: str, export_path: str) -> bool:
        """
        Export profile to file for sharing.
        
        Args:
            name: Profile name
            export_path: Path to export file
            
        Returns:
            True if exported successfully
        """
        profile = self._profiles.get(name)
        if not profile:
            return False
        
        try:
            # Ensure correct extension
            if not export_path.endswith(self.EXPORT_EXTENSION):
                export_path += self.EXPORT_EXTENSION

            self._normalize_profile(profile)
            
            data = {
                'type': 'photo_cropper_profile',
                'version': '9.0',
                'profile': profile.to_dict(),
                'exported_at': datetime.now().isoformat()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported profile '{name}' to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting profile: {e}")
            return False
    
    def import_profile(self, import_path: str, 
                       new_name: Optional[str] = None) -> Optional[BatchProfile]:
        """
        Import profile from file.
        
        Args:
            import_path: Path to import file
            new_name: Optional new name for the profile
            
        Returns:
            Imported BatchProfile or None on failure
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') != 'photo_cropper_profile':
                logger.error("Invalid profile file format")
                return None
            
            profile = BatchProfile.from_dict(data['profile'])
            self._normalize_profile(profile)
            
            if new_name:
                profile.name = new_name
            
            # Handle name conflicts
            original_name = profile.name
            counter = 1
            while profile.name in self._profiles:
                profile.name = f"{original_name} ({counter})"
                counter += 1
            
            self._profiles[profile.name] = profile
            self._save_profiles()
            
            logger.info(f"Imported profile: {profile.name}")
            return profile
            
        except Exception as e:
            logger.error(f"Error importing profile: {e}")
            return None
    
    def get_quick_profiles(self) -> List[str]:
        """
        Get list of profiles for quick switching.
        
        Returns:
            List of profile names suitable for toolbar
        """
        # Return first 5 profiles (defaults + recent)
        return list(self._profiles.keys())[:5]
    
    def duplicate_profile(self, name: str, new_name: str) -> bool:
        """
        Duplicate a profile.
        
        Args:
            name: Profile to duplicate
            new_name: Name for the copy
            
        Returns:
            True if duplicated successfully
        """
        profile = self._profiles.get(name)
        if not profile or new_name in self._profiles:
            return False
        
        new_profile = BatchProfile(
            name=new_name,
            description=f"{profile.description} (복사본)",
            settings=self._normalize_settings_dict(profile.settings.copy() if profile.settings else {}),
            category_rules=profile.category_rules.copy()
        )
        self._normalize_profile(new_profile)
        
        self._profiles[new_name] = new_profile
        self._save_profiles()
        return True


# Singleton instance
_manager_instance: Optional[BatchProfileManager] = None


def get_batch_profile_manager() -> BatchProfileManager:
    """Get global batch profile manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = BatchProfileManager()
    return _manager_instance
