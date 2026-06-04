#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation helpers for safe single-segment folder and filename fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

from ..core.settings_model.app_settings import (
    AppSettings,
    CLASSIFICATION_CATEGORY_KEYS,
)

INVALID_SEGMENT_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{idx}" for idx in range(1, 10)),
    *(f"LPT{idx}" for idx in range(1, 10)),
}


@dataclass(frozen=True)
class SettingsPathIssue:
    """Structured validation issue for settings-backed path fragments."""

    field: str
    key: str
    message: str


def validate_single_path_segment(value: str, *, allow_empty: bool = False) -> tuple[bool, str]:
    """Validate that a value is a safe single path segment or filename fragment."""
    text = str(value or "")
    if not text:
        return (True, "") if allow_empty else (False, "empty")
    if text.endswith((" ", ".")):
        return False, "trailing"
    if "/" in text or "\\" in text:
        return False, "separator"
    if text in {".", ".."} or ".." in text:
        return False, "dotdot"
    if WINDOWS_DRIVE_RE.match(text) or text.startswith("\\\\"):
        return False, "path"
    if INVALID_SEGMENT_CHARS_RE.search(text):
        return False, "chars"
    reserved_probe = text.rstrip(" .").split(".", 1)[0].upper()
    if reserved_probe in WINDOWS_RESERVED_NAMES:
        return False, "reserved"
    return True, ""


def resolve_category_folder_name(
    key: str,
    raw_value: str,
    *,
    language: Optional[str] = None,
) -> str:
    """Resolve an empty custom folder name to the current locale default."""
    normalized = str(raw_value or "").strip()
    if normalized:
        return normalized
    from ..i18n.catalog import get_category_folder_defaults

    defaults = get_category_folder_defaults(language)
    return str(defaults.get(key, key)).strip() or key


def resolve_category_folder_map(
    category_folders: Mapping[str, str] | None,
    *,
    language: Optional[str] = None,
) -> dict[str, str]:
    """Resolve category folder map with locale defaults for empty sentinel values."""
    folder_map = dict(category_folders or {})
    return {
        key: resolve_category_folder_name(key, str(folder_map.get(key, "")), language=language)
        for key in CLASSIFICATION_CATEGORY_KEYS
    }


def validate_settings_path_segments(
    settings: AppSettings,
) -> list[SettingsPathIssue]:
    """Validate persisted settings fields that become path segments at runtime."""
    from ..i18n.catalog import t

    issues: list[SettingsPathIssue] = []

    prefix = str(getattr(settings.file_management, "naming_prefix", "") or "")
    valid, _ = validate_single_path_segment(prefix, allow_empty=True)
    if not valid:
        issues.append(
            SettingsPathIssue(
                field="file_management.naming_prefix",
                key="naming_prefix",
                message=t("validation.config_invalid_prefix"),
            )
        )

    suffix = str(getattr(settings.file_management, "naming_suffix", "") or "")
    valid, _ = validate_single_path_segment(suffix, allow_empty=True)
    if not valid:
        issues.append(
            SettingsPathIssue(
                field="file_management.naming_suffix",
                key="naming_suffix",
                message=t("validation.config_invalid_suffix"),
            )
        )

    failed_folder = str(getattr(settings.file_management, "failed_folder_name", "") or "")
    valid, _ = validate_single_path_segment(failed_folder, allow_empty=False)
    if not valid:
        issues.append(
            SettingsPathIssue(
                field="file_management.failed_folder_name",
                key="failed_folder_name",
                message=t("validation.config_invalid_failed_folder"),
            )
        )

    folder_map = getattr(settings.classification, "category_folders", {}) or {}
    for category in CLASSIFICATION_CATEGORY_KEYS:
        raw_value = str(folder_map.get(category, "") or "").strip()
        valid, _ = validate_single_path_segment(raw_value, allow_empty=True)
        if not valid:
            issues.append(
                SettingsPathIssue(
                    field=f"classification.category_folders.{category}",
                    key=category,
                    message=t("validation.config_invalid_category", category=category),
                )
            )

    return issues


def build_settings_validation_summary(issues: list[SettingsPathIssue]) -> str:
    """Format issues into a compact blocking dialog body."""
    if not issues:
        return ""
    unique_messages = []
    seen = set()
    for issue in issues:
        if issue.message in seen:
            continue
        unique_messages.append(issue.message)
        seen.add(issue.message)
    return "\n".join(f"• {message}" for message in unique_messages)
