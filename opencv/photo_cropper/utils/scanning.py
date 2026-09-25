#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Image discovery and folder inspection for Photo Cropper.

Single responsibility: finding image files and describing folders.
Depends on :mod:`.paths` for containment checks; performs no file
mutations and no hashing.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from .path_validation import validate_single_path_segment
from .paths import is_path_within, normalize_path

logger = logging.getLogger(__name__)


SUPPORTED_IMAGE_FORMATS = (
    '.png', '.jpg', '.jpeg', '.bmp', '.gif',
    '.tiff', '.tif', '.webp'
)


def build_recursive_excluded_roots(
    input_root: str,
    output_root: str = "",
    *,
    failed_folder_name: str = "_failed",
    include_backup: bool = True,
) -> List[str]:
    """Build canonical roots that should be excluded from recursive input scans."""
    normalized_input = normalize_path(input_root)
    if not normalized_input:
        return []

    roots: List[str] = []
    candidates = [output_root]
    if failed_folder_name:
        valid_failed_folder, _ = validate_single_path_segment(
            failed_folder_name,
            allow_empty=False,
        )
        if valid_failed_folder:
            candidates.append(os.path.join(normalized_input, failed_folder_name))
        else:
            logger.warning("Invalid failed folder name excluded from recursive roots")
    if include_backup:
        candidates.append(os.path.join(normalized_input, "backup"))

    for candidate in candidates:
        normalized_candidate = normalize_path(candidate)
        if not normalized_candidate:
            continue
        if normalized_candidate not in roots:
            roots.append(normalized_candidate)
    return roots


def _normalize_excluded_roots(
    excluded_roots: Optional[Sequence[str]],
) -> List[str]:
    normalized: List[str] = []
    for raw in excluded_roots or []:
        candidate = normalize_path(raw)
        if not candidate:
            continue
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _is_excluded_directory(path: str, excluded_roots: Sequence[str]) -> bool:
    if os.path.basename(path) == ".photocropper":
        return True
    normalized = normalize_path(path)
    return any(is_path_within(root, normalized) for root in excluded_roots)


def get_image_files(
    directory: str,
    recursive: bool = False,
    *,
    excluded_roots: Optional[Sequence[str]] = None,
    raise_errors: bool = False,
) -> List[str]:
    """
    Get all image files in a directory.

    Args:
        directory: Directory path
        recursive: Include subdirectories
        excluded_roots: Absolute roots to prune from recursive scans

    Returns:
        List of image file paths
    """
    files = []
    excluded = _normalize_excluded_roots(excluded_roots)

    try:
        if recursive:
            for root, dirnames, filenames in os.walk(directory):
                dirnames[:] = [
                    dirname
                    for dirname in dirnames
                    if not _is_excluded_directory(os.path.join(root, dirname), excluded)
                ]
                for filename in filenames:
                    if filename.lower().endswith(SUPPORTED_IMAGE_FORMATS):
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                if filename.lower().endswith(SUPPORTED_IMAGE_FORMATS):
                    files.append(os.path.join(directory, filename))

        return sorted(files)
    except Exception as e:
        logger.error(f"Error reading directory: {e}")
        if raise_errors:
            raise
        return []


def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        True if directory exists/was created
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        return False


def get_unique_filename(
    directory: str,
    base_name: str,
    extension: str,
    add_timestamp: bool = False
) -> str:
    """
    Generate a unique filename that doesn't exist.

    Args:
        directory: Target directory
        base_name: Base filename
        extension: File extension (with or without dot)
        add_timestamp: Add timestamp to filename

    Returns:
        Unique file path
    """
    if not extension.startswith('.'):
        extension = '.' + extension

    if add_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}{extension}"
    else:
        filename = f"{base_name}{extension}"

    path = os.path.join(directory, filename)

    # If exists, add counter
    counter = 1
    while os.path.exists(path):
        if add_timestamp:
            filename = f"{base_name}_{timestamp}_{counter}{extension}"
        else:
            filename = f"{base_name}_{counter}{extension}"
        path = os.path.join(directory, filename)
        counter += 1

    return path


def validate_directory(path: str) -> Tuple[bool, str]:
    """
    Validate that a directory exists and is accessible.

    Args:
        path: Directory path

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "경로가 비어있습니다"

    if not os.path.exists(path):
        return False, "경로가 존재하지 않습니다"

    if not os.path.isdir(path):
        return False, "폴더가 아닙니다"

    try:
        # Check read access
        os.listdir(path)
        return True, ""
    except PermissionError:
        return False, "폴더 접근 권한이 없습니다"
    except Exception as e:
        return False, f"폴더 접근 오류: {e}"


def get_image_files_with_info(
    directory: str,
    recursive: bool = False,
    *,
    excluded_roots: Optional[Sequence[str]] = None,
) -> List[dict]:
    """
    Get image files with additional metadata.

    Args:
        directory: Directory path
        recursive: Include subdirectories

    Returns:
        List of dicts with 'path', 'name', 'size_kb', 'modified' keys
    """
    files = []

    try:
        paths = get_image_files(directory, recursive, excluded_roots=excluded_roots)

        for path in paths:
            try:
                stat = os.stat(path)
                files.append({
                    'path': path,
                    'name': os.path.basename(path),
                    'size_kb': stat.st_size / 1024,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'relative_path': os.path.relpath(path, directory)
                })
            except Exception as e:
                logger.warning(f"Error getting info for {path}: {e}")

    except Exception as e:
        logger.error(f"Error reading directory: {e}")

    return files


def get_folder_stats(
    directory: str,
    recursive: bool = False,
    *,
    excluded_roots: Optional[Sequence[str]] = None,
) -> dict:
    """
    Get statistics about images in a folder.

    Args:
        directory: Directory path
        recursive: Include subdirectories

    Returns:
        Dictionary with folder statistics
    """
    files = get_image_files(directory, recursive, excluded_roots=excluded_roots)

    if not files:
        return {
            'total_files': 0,
            'total_size_mb': 0,
            'formats': {},
            'subfolders': 0
        }

    total_size = 0
    formats = {}
    subfolders = set()

    for filepath in files:
        try:
            # Size
            total_size += os.path.getsize(filepath)

            # Format
            ext = os.path.splitext(filepath)[1].lower()
            formats[ext] = formats.get(ext, 0) + 1

            # Subfolder
            if recursive:
                rel_dir = os.path.dirname(os.path.relpath(filepath, directory))
                if rel_dir:
                    subfolders.add(rel_dir)

        except Exception:
            pass

    return {
        'total_files': len(files),
        'total_size_mb': total_size / (1024 * 1024),
        'formats': formats,
        'subfolders': len(subfolders)
    }


__all__ = [
    "SUPPORTED_IMAGE_FORMATS",
    "build_recursive_excluded_roots",
    "get_image_files",
    "ensure_directory",
    "get_unique_filename",
    "validate_directory",
    "get_image_files_with_info",
    "get_folder_stats",
]
