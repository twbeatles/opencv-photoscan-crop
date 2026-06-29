from __future__ import annotations

from ...utils.path_validation import (
    SettingsPathIssue,
    build_settings_validation_summary as _build_settings_validation_summary,
    validate_settings_path_segments as _validate_settings_path_segments,
)
from .app_settings import AppSettings


def validate_settings(settings: AppSettings) -> list[SettingsPathIssue]:
    """Validate persisted settings that are later used as path segments."""
    return _validate_settings_path_segments(settings)


def build_validation_summary(issues: list[SettingsPathIssue]) -> str:
    """Build a compact, user-facing validation summary."""
    return _build_settings_validation_summary(issues)


__all__ = [
    "SettingsPathIssue",
    "validate_settings",
    "build_validation_summary",
]
