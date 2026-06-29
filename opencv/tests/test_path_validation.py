"""Unit tests for path segment validation."""

from __future__ import annotations

from photo_cropper.core.settings_model import AppSettings
from photo_cropper.utils.path_validation import (
    validate_settings_path_segments,
    validate_single_path_segment,
)


def test_validate_single_path_segment_rejects_dotdot() -> None:
    ok, reason = validate_single_path_segment("evil..name")
    assert ok is False
    assert reason == "dotdot"


def test_validate_single_path_segment_rejects_windows_reserved() -> None:
    ok, reason = validate_single_path_segment("CON")
    assert ok is False
    assert reason == "reserved"


def test_validate_settings_path_segments_flags_invalid_failed_folder() -> None:
    settings = AppSettings()
    settings.file_management.failed_folder_name = ".."
    issues = validate_settings_path_segments(settings)
    assert any(issue.key == "failed_folder_name" for issue in issues)