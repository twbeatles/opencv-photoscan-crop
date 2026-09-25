#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filesystem path helpers for Photo Cropper.

Single responsibility: pure path normalization, containment checks, and
input-root-relative display paths. No I/O, no scanning, no mutations.
"""

import os
from typing import Optional


def normalize_path(path: str) -> str:
    """Normalize a filesystem path for case-insensitive comparisons."""
    text = str(path or "").strip()
    if not text:
        return ""
    return os.path.normcase(os.path.abspath(text))


def is_path_within(parent_path: str, child_path: str) -> bool:
    """Return True when ``child_path`` is the same path or nested under ``parent_path``."""
    parent = normalize_path(parent_path)
    child = normalize_path(child_path)
    if not parent or not child:
        return False
    try:
        return os.path.commonpath([parent, child]) == parent
    except Exception:
        return False


def is_output_inside_input(input_path: str, output_path: str) -> bool:
    """Return True when output path is the same as, or nested under, input path."""
    return is_path_within(input_path, output_path)


def relative_parent_dir(file_path: str, root_path: Optional[str]) -> str:
    """Return the input-root-relative parent directory for a file, or empty string."""
    root = str(root_path or "").strip()
    if not root:
        return ""

    normalized_root = normalize_path(root)
    normalized_file = normalize_path(file_path)
    if not is_path_within(normalized_root, normalized_file):
        return ""

    try:
        rel_path = os.path.relpath(normalized_file, normalized_root)
    except Exception:
        return ""

    rel_parent = os.path.dirname(rel_path)
    if rel_parent in ("", "."):
        return ""
    return rel_parent


def relative_display_path(file_path: str, root_path: Optional[str]) -> str:
    """Return root-relative display path when possible, otherwise basename."""
    root = str(root_path or "").strip()
    normalized_file = normalize_path(file_path)
    if root and is_path_within(root, normalized_file):
        try:
            rel_path = os.path.relpath(normalized_file, normalize_path(root))
            if rel_path not in ("", "."):
                return rel_path
        except Exception:
            pass
    return os.path.basename(normalized_file)


__all__ = [
    "normalize_path",
    "is_path_within",
    "is_output_inside_input",
    "relative_parent_dir",
    "relative_display_path",
]
