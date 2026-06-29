from __future__ import annotations

import json
import logging
import os
import platform
from typing import Optional

from .app_settings import AppSettings

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages loading and saving of application settings."""

    LEGACY_CONFIG_DIR = ".photo_cropper"
    LEGACY_CONFIG_FILE = "photo_cropper_settings.json"

    WINDOWS_CONFIG_DIR = "PhotoCropper"
    WINDOWS_CONFIG_FILE = "settings.json"

    def __init__(self, config_file: Optional[str] = None):
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

        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, self.LEGACY_CONFIG_DIR)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, self.LEGACY_CONFIG_FILE)

    def _get_legacy_config_files(self) -> list[str]:
        """Possible legacy config paths to migrate from."""
        paths: list[str] = []

        home_dir = os.path.expanduser("~")
        legacy_dir = os.path.join(home_dir, self.LEGACY_CONFIG_DIR)
        paths.append(os.path.join(legacy_dir, self.LEGACY_CONFIG_FILE))

        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(
                os.path.join(
                    appdata, self.WINDOWS_CONFIG_DIR, self.LEGACY_CONFIG_FILE
                )
            )

        normalized: list[str] = []
        for path in paths:
            try:
                if os.path.abspath(path) == os.path.abspath(self.config_file):
                    continue
            except Exception:
                pass
            if path not in normalized:
                normalized.append(path)
        return normalized

    @property
    def settings(self) -> AppSettings:
        """Get current settings, loading if necessary."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings

    @settings.setter
    def settings(self, value: AppSettings) -> None:
        """Set current settings."""
        self._settings = value

    def load(self) -> AppSettings:
        """Load settings from disk, migrating legacy config files when necessary."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                logger.info("Settings loaded from %s", self.config_file)
                return AppSettings.from_dict(data)

            for legacy_path in self._legacy_config_files:
                if not legacy_path or not os.path.exists(legacy_path):
                    continue
                try:
                    with open(legacy_path, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                    settings = AppSettings.from_dict(data)
                    logger.info(
                        "Migrating settings from %s -> %s",
                        legacy_path,
                        self.config_file,
                    )
                    self.save(settings)
                    return settings
                except Exception as exc:
                    logger.warning(
                        "Settings migration failed (%s): %s",
                        legacy_path,
                        exc,
                    )
        except json.JSONDecodeError as exc:
            logger.error("Settings file JSON parse error: %s", exc)
        except Exception as exc:
            logger.error("Settings load error: %s", exc)

        logger.info("Using default settings")
        return AppSettings()

    def save(self, settings: Optional[AppSettings] = None) -> bool:
        """Persist settings to disk."""
        if settings is None:
            settings = self._settings

        if settings is None:
            logger.warning("No settings to save")
            return False

        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as handle:
                json.dump(settings.to_dict(), handle, indent=2, ensure_ascii=False)

            self._settings = settings
            logger.info("Settings saved to %s", self.config_file)
            return True
        except Exception as exc:
            logger.error("Settings save error: %s", exc)
            return False

    def reset_to_defaults(self) -> AppSettings:
        """Reset settings to defaults."""
        self._settings = AppSettings()
        logger.info("Settings reset to defaults")
        return self._settings

    def get_default(self) -> AppSettings:
        """Get default settings without mutating current state."""
        return AppSettings()


_default_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the default settings manager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = SettingsManager()
    return _default_manager


__all__ = ["SettingsManager", "get_settings_manager"]
