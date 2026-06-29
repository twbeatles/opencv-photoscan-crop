#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File helper utilities for Photo Cropper."""

import os
import logging
from typing import Iterable, List, Optional, Sequence, Tuple
from datetime import datetime

import cv2

from .image_io import load_image_unicode
from .path_validation import validate_single_path_segment

logger = logging.getLogger(__name__)


SUPPORTED_IMAGE_FORMATS = (
    '.png', '.jpg', '.jpeg', '.bmp', '.gif',
    '.tiff', '.tif', '.webp'
)


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


# =============================================================================
# New functions for v8.0
# =============================================================================

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


def compute_file_hash(filepath: str, algorithm: str = 'md5',
                     chunk_size: int = 8192) -> Optional[str]:
    """
    Compute hash of a file.
    
    Args:
        filepath: Path to file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
        chunk_size: Read chunk size
        
    Returns:
        Hexadecimal hash string or None if error
    """
    import hashlib
    
    try:
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {filepath}: {e}")
        return None


def detect_duplicates(file_list: List[str],
                     method: str = 'hash') -> dict:
    """
    Detect duplicate files.
    
    Args:
        file_list: List of file paths to check
        method: Detection method ('hash', 'size', 'size+hash')
        
    Returns:
        Dictionary mapping hash/key to list of duplicate file paths
    """
    from collections import defaultdict
    
    duplicates = defaultdict(list)
    
    if method == 'size':
        # Group by file size only (fast but less accurate)
        for filepath in file_list:
            try:
                size = os.path.getsize(filepath)
                duplicates[size].append(filepath)
            except Exception:
                pass
                
    elif method == 'size+hash':
        # First group by size, then hash only potential duplicates
        size_groups = defaultdict(list)
        for filepath in file_list:
            try:
                size = os.path.getsize(filepath)
                size_groups[size].append(filepath)
            except Exception:
                pass
        
        # Only compute hash for files with same size
        for size, paths in size_groups.items():
            if len(paths) > 1:
                for filepath in paths:
                    file_hash = compute_file_hash(filepath)
                    if file_hash:
                        duplicates[file_hash].append(filepath)
            else:
                # Single file with unique size, add with size as key
                duplicates[f"size_{size}"].append(paths[0])
                
    else:  # 'hash' - most accurate but slowest
        for filepath in file_list:
            file_hash = compute_file_hash(filepath)
            if file_hash:
                duplicates[file_hash].append(filepath)
    
    # Filter to only groups with duplicates
    return {k: v for k, v in duplicates.items() if len(v) > 1}


def get_image_dimensions(filepath: str) -> Optional[Tuple[int, int]]:
    """
    Get image dimensions without loading full image.
    
    Args:
        filepath: Path to image file
        
    Returns:
        Tuple of (width, height) or None
    """
    try:
        # Try PIL first (faster for reading headers)
        from PIL import Image
        with Image.open(filepath) as img:
            return img.size
    except ImportError:
        pass
    except Exception:
        pass
    
    try:
        img = load_image_unicode(filepath, cv2.IMREAD_UNCHANGED)
        if img is not None:
            h, w = img.shape[:2]
            return (w, h)
    except Exception:
        pass
    
    return None


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
