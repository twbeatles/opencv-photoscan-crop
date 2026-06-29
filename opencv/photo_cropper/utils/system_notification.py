#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Notification for Photo Cropper v9.0.

Provides Windows system notifications and sounds:
- Batch completion notifications
- Error notifications
- Watch mode file detection
- Sound alerts
"""

from __future__ import annotations

import os
import sys
import logging
import threading
from typing import Any, Callable, Optional
from enum import Enum
from dataclasses import dataclass

from ..i18n.catalog import t

logger = logging.getLogger(__name__)

# Optional Windows toast notifications (importlib keeps pyright clean on Linux CI).
_WINOTIFY_MODULE: Any = None
try:
    import importlib

    _WINOTIFY_MODULE = importlib.import_module("winotify")
    WINOTIFY_AVAILABLE = True
except ImportError:
    WINOTIFY_AVAILABLE = False
    logger.info("winotify not available, using fallback notifications")

# Try to import winsound for sound effects
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class NotificationType(Enum):
    """Notification type enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SoundType(Enum):
    """Sound effect type enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    NOTIFY = "notify"
    COMPLETE = "complete"


@dataclass
class NotificationSettings:
    """Notification settings."""
    enabled: bool = True
    play_sound: bool = True
    on_batch_complete: bool = True
    on_error: bool = True
    on_watch_mode: bool = True
    sound_volume: int = 100  # 0-100


class SystemNotification:
    """
    Windows system notification manager.
    
    Features:
    - Windows 10/11 toast notifications
    - Sound effects
    - Thread-safe async notifications
    - Fallback to console if winotify unavailable
    """
    
    APP_ID = "Photo Cropper"
    ICON_PATH = None  # Will be set if icon file exists
    
    # Windows system sound aliases
    SOUNDS = {
        SoundType.SUCCESS: "SystemAsterisk",
        SoundType.ERROR: "SystemHand",
        SoundType.NOTIFY: "SystemNotification", 
        SoundType.COMPLETE: "SystemExclamation"
    }
    
    def __init__(self, settings: Optional[NotificationSettings] = None):
        """
        Initialize notification manager.
        
        Args:
            settings: Notification settings
        """
        self.settings = settings or NotificationSettings()
        self._callbacks: dict[NotificationType, list[Callable]] = {
            t: [] for t in NotificationType
        }
        
        # Find icon if available
        self._find_icon()
    
    def _find_icon(self):
        """Find application icon file."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'icon.ico'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'icon.png'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.ICON_PATH = os.path.abspath(path)
                break
    
    def notify(self, title: str, message: str, 
               notification_type: NotificationType = NotificationType.INFO,
               play_sound: bool = True) -> bool:
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            play_sound: Whether to play sound
            
        Returns:
            True if notification was shown
        """
        if not self.settings.enabled:
            return False
        
        # Run in thread to avoid blocking
        thread = threading.Thread(
            target=self._show_notification,
            args=(title, message, notification_type, play_sound),
            daemon=True
        )
        thread.start()
        
        return True
    
    def _show_notification(self, title: str, message: str,
                          notification_type: NotificationType,
                          play_sound: bool):
        """Show notification (runs in thread)."""
        try:
            if WINOTIFY_AVAILABLE:
                self._show_winotify(title, message, notification_type)
            else:
                self._show_fallback(title, message, notification_type)
            
            if play_sound and self.settings.play_sound:
                self._play_sound(notification_type)
            
            # Call registered callbacks
            for callback in self._callbacks.get(notification_type, []):
                try:
                    callback(title, message)
                except Exception as e:
                    logger.error(f"Notification callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
    
    def _show_winotify(self, title: str, message: str,
                       notification_type: NotificationType):
        """Show notification using winotify."""
        if _WINOTIFY_MODULE is None:
            self._show_fallback(title, message, notification_type)
            return

        toast = _WINOTIFY_MODULE.Notification(
            app_id=self.APP_ID,
            title=title,
            msg=message,
            duration="short"
        )

        if self.ICON_PATH:
            toast.set_audio(_WINOTIFY_MODULE.audio.Default, loop=False)

        toast.show()
    
    def _show_fallback(self, title: str, message: str,
                       notification_type: NotificationType):
        """Show fallback notification (console)."""
        # Avoid emojis here: Windows console encoding may not support them.
        type_tag = {
            NotificationType.SUCCESS: "[OK]",
            NotificationType.ERROR: "[ERROR]",
            NotificationType.WARNING: "[WARN]",
            NotificationType.INFO: "[INFO]",
        }

        tag = type_tag.get(notification_type, "[INFO]")
        logger.info(f"{tag} {title}: {message}")
    
    def _play_sound(self, notification_type: NotificationType):
        """Play notification sound."""
        if not WINSOUND_AVAILABLE:
            return
        
        sound_map = {
            NotificationType.SUCCESS: SoundType.SUCCESS,
            NotificationType.ERROR: SoundType.ERROR,
            NotificationType.WARNING: SoundType.NOTIFY,
            NotificationType.INFO: SoundType.NOTIFY
        }
        
        sound_type = sound_map.get(notification_type, SoundType.NOTIFY)
        self.play_sound(sound_type)
    
    def play_sound(self, sound_type: SoundType):
        """
        Play a sound effect.
        
        Args:
            sound_type: Type of sound to play
        """
        if not WINSOUND_AVAILABLE or not self.settings.play_sound:
            return
        
        try:
            sound_alias = self.SOUNDS.get(sound_type, "SystemDefault")
            winsound.PlaySound(sound_alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception as e:
            logger.debug(f"Failed to play sound: {e}")
    
    def notify_batch_complete(self, processed: int, failed: int, 
                              time_seconds: float):
        """
        Notify batch processing completion.
        
        Args:
            processed: Number of images processed
            failed: Number of failures
            time_seconds: Total processing time
        """
        if not self.settings.on_batch_complete:
            return
        
        if failed == 0:
            title = t("notification.batch_complete.title")
            message = t(
                "notification.batch_complete.body",
                processed=processed,
                seconds=f"{time_seconds:.1f}",
            )
            notification_type = NotificationType.SUCCESS
        else:
            title = t("notification.batch_partial.title")
            message = t(
                "notification.batch_partial.body",
                processed=processed,
                failed=failed,
                seconds=f"{time_seconds:.1f}",
            )
            notification_type = NotificationType.WARNING
        
        self.notify(title, message, notification_type)
    
    def notify_error(self, message: str, details: str = ""):
        """
        Notify error occurrence.
        
        Args:
            message: Error message
            details: Additional details
        """
        if not self.settings.on_error:
            return
        
        full_message = message
        if details:
            full_message += f"\n{details}"
        
        self.notify(t("notification.error.title"), full_message, NotificationType.ERROR)
    
    def notify_watch_mode(self, new_files: int, processed: int = 0):
        """
        Notify watch mode file detection.
        
        Args:
            new_files: Number of new files detected
            processed: Number of files processed
        """
        if not self.settings.on_watch_mode:
            return
        
        if processed > 0:
            message = t(
                "notification.watch.processed",
                new_files=new_files,
                processed=processed,
            )
        else:
            message = t("notification.watch.detected", new_files=new_files)
        
        self.notify(t("notification.watch.title"), message, NotificationType.INFO)
    
    def notify_classification_complete(self, categories: dict):
        """
        Notify classification completion.
        
        Args:
            categories: Dictionary of category counts
        """
        if not self.settings.enabled:
            return
        
        summary = ", ".join(
            t("notification.classification.item", category=k, count=v)
            for k, v in categories.items()
            if v > 0
        )
        self.notify(t("notification.classification.title"), summary, NotificationType.SUCCESS)
    
    def register_callback(self, notification_type: NotificationType,
                          callback: Callable[[str, str], None]):
        """
        Register callback for notification type.
        
        Args:
            notification_type: Type to listen for
            callback: Function(title, message) to call
        """
        if notification_type not in self._callbacks:
            self._callbacks[notification_type] = []
        self._callbacks[notification_type].append(callback)
    
    def unregister_callback(self, notification_type: NotificationType,
                            callback: Callable):
        """
        Unregister callback.
        
        Args:
            notification_type: Type to unregister from
            callback: Function to remove
        """
        if notification_type in self._callbacks:
            try:
                self._callbacks[notification_type].remove(callback)
            except ValueError:
                pass
    
    def update_settings(self, settings: NotificationSettings):
        """Update notification settings."""
        self.settings = settings


# Singleton instance
_notification_instance: Optional[SystemNotification] = None


def get_system_notification() -> SystemNotification:
    """Get global system notification instance."""
    global _notification_instance
    if _notification_instance is None:
        _notification_instance = SystemNotification()
    return _notification_instance


def reset_system_notification_for_tests() -> None:
    global _notification_instance
    _notification_instance = None


def notify_success(title: str, message: str):
    """Quick success notification."""
    get_system_notification().notify(title, message, NotificationType.SUCCESS)


def notify_error(title: str, message: str):
    """Quick error notification."""
    get_system_notification().notify(title, message, NotificationType.ERROR)


def notify_info(title: str, message: str):
    """Quick info notification."""
    get_system_notification().notify(title, message, NotificationType.INFO)
