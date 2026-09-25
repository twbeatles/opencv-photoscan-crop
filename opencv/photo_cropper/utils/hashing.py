#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Content identity helpers for Photo Cropper.

Single responsibility: file hashing, duplicate grouping, and image
dimension probing. Read-only; never moves or copies files.
"""

import logging
import os
from typing import List, Optional, Tuple

import cv2

from .image_io import load_image_unicode

logger = logging.getLogger(__name__)


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


__all__ = [
    "compute_file_hash",
    "detect_duplicates",
    "get_image_dimensions",
]
