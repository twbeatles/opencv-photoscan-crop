#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File helper utilities for Photo Cropper.
"""

import os
import logging
from typing import List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


SUPPORTED_IMAGE_FORMATS = (
    '.png', '.jpg', '.jpeg', '.bmp', '.gif',
    '.tiff', '.tif', '.webp', '.heic', '.heif'
)


def get_image_files(directory: str, recursive: bool = False) -> List[str]:
    """
    Get all image files in a directory.
    
    Args:
        directory: Directory path
        recursive: Include subdirectories
        
    Returns:
        List of image file paths
    """
    files = []
    
    try:
        if recursive:
            for root, _, filenames in os.walk(directory):
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
                    os.startfile(path)
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
