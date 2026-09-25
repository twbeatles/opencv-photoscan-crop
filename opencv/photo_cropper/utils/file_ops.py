#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File mutation and OS-integration helpers for Photo Cropper.

Single responsibility: operations that change the filesystem or reach
out to the OS (move/copy to subfolders, failed-file routing, opening
the system file explorer) plus small file-size presentation helpers.
"""

import logging
import os
from typing import List, Optional, Tuple

from .path_validation import validate_single_path_segment
from .paths import normalize_path, relative_parent_dir

logger = logging.getLogger(__name__)


def get_file_size(path: str) -> Optional[float]:
    """
    Get file size in KB.

    Args:
        path: File path

    Returns:
        Size in KB or None if error
    """
    try:
        return os.path.getsize(path) / 1024
    except Exception:
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def open_file_explorer(path: str) -> bool:
    """
    Open file explorer at the specified path.

    Args:
        path: Directory or file path

    Returns:
        True if opened successfully
    """
    import platform
    import subprocess

    try:
        system = platform.system()

        if system == "Windows":
            if os.path.isfile(path):
                # Select file in explorer
                subprocess.run(['explorer', '/select,', path], check=False)
            else:
                try:
                    startfile = getattr(os, "startfile", None)
                    if startfile is None:
                        raise OSError("os.startfile is not available on this platform")
                    startfile(path)
                except OSError as e:
                    logger.warning(f"os.startfile failed, trying subprocess: {e}")
                    subprocess.run(['explorer', path], check=False)
        elif system == "Darwin":  # macOS
            subprocess.run(['open', path], check=False)
        else:  # Linux
            subprocess.run(['xdg-open', path], check=False)

        return True
    except Exception as e:
        logger.error(f"Error opening file explorer: {e}")
        return False


def move_to_subfolder(filepath: str,
                     subfolder_name: str,
                     copy_instead: bool = False) -> Optional[str]:
    """
    Move or copy file to a subfolder within its parent directory.

    Args:
        filepath: Source file path
        subfolder_name: Name of subfolder to move to
        copy_instead: If True, copy instead of move

    Returns:
        New file path or None if error
    """
    import shutil

    try:
        parent_dir = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        # Create subfolder
        subfolder_path = os.path.join(parent_dir, subfolder_name)
        os.makedirs(subfolder_path, exist_ok=True)

        # Destination path
        dest_path = os.path.join(subfolder_path, filename)

        # Handle existing file
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(subfolder_path, f"{base}_{counter}{ext}")
                counter += 1

        if copy_instead:
            shutil.copy2(filepath, dest_path)
        else:
            shutil.move(filepath, dest_path)

        return dest_path

    except Exception as e:
        logger.error(f"Error moving file {filepath}: {e}")
        return None


def classify_failed_files(
    failed_files: List[str],
    source_dir: str,
    failed_folder_name: str = "_failed",
    copy_mode: bool = True,
    *,
    input_root: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    Move/copy failed files to a separate folder.

    Args:
        failed_files: List of failed file paths
        source_dir: Source directory (for creating _failed subfolder)
        failed_folder_name: Name of failed files folder
        copy_mode: If True, copy files instead of moving

    Returns:
        Tuple of (success_count, error_messages)
    """
    import shutil

    success_count = 0
    errors = []

    valid_failed_folder, reason = validate_single_path_segment(
        failed_folder_name,
        allow_empty=False,
    )
    if not valid_failed_folder:
        return 0, [f"Invalid failed folder name: {reason}"]

    # Create failed folder
    failed_folder = os.path.join(source_dir, failed_folder_name)
    try:
        os.makedirs(failed_folder, exist_ok=True)
    except Exception as e:
        return 0, [f"Could not create failed folder: {e}"]

    normalized_input_root = normalize_path(input_root or source_dir)

    for filepath in failed_files:
        try:
            if not os.path.exists(filepath):
                errors.append(f"File not found: {filepath}")
                continue

            filename = os.path.basename(filepath)
            rel_parent = relative_parent_dir(filepath, normalized_input_root)
            dest_dir = os.path.join(failed_folder, rel_parent) if rel_parent else failed_folder
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            # Handle duplicate names
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                    counter += 1

            if copy_mode:
                shutil.copy2(filepath, dest_path)
            else:
                shutil.move(filepath, dest_path)

            success_count += 1

        except Exception as e:
            errors.append(f"Error processing {filepath}: {e}")

    return success_count, errors


__all__ = [
    "get_file_size",
    "format_file_size",
    "open_file_explorer",
    "move_to_subfolder",
    "classify_failed_files",
]
