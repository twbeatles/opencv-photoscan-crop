#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DNN model acquisition for face detection.

Single responsibility: locate, download (with checksum), and cache the
OpenCV Caffe face-detector model files. No detection logic here.
"""

import hashlib
import logging
import os
import platform
import tempfile
import urllib.request
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# DNN model metadata (OpenCV face detector, Caffe)
DNN_PROTOTXT_URL = (
    "https://raw.githubusercontent.com/opencv/opencv/master/"
    "samples/dnn/face_detector/deploy.prototxt"
)
DNN_MODEL_URL = (
    "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
    "dnn_samples_face_detector_20180205_fp16/"
    "res10_300x300_ssd_iter_140000_fp16.caffemodel"
)
DNN_PROTOTXT_SHA256 = (
    "dcd661dc48fc9de0a341db1f666a2164ea63a67265c7f779bc12d6b3f2fa67e9"
)
DNN_MODEL_SHA256 = (
    "510ffd2471bd81e3fcc88a5beb4eae4fb445ccf8333ebc54e7302b83f4158a76"
)
DNN_PROTOTXT_FILENAME = "deploy.prototxt"
DNN_MODEL_FILENAME = "res10_300x300_ssd_iter_140000_fp16.caffemodel"
DNN_CONFIDENCE_THRESHOLD = 0.55

_MODEL_CACHE: Optional[Tuple[str, str]] = None


def get_model_cache_dir() -> str:
    """Get OS-specific model cache directory."""
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Windows":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or home
    elif system == "Darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")

    model_dir = os.path.join(base, "PhotoCropper", "models")
    os.makedirs(model_dir, exist_ok=True)
    return model_dir


def _sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().lower()
    except Exception:
        return None


def is_valid_model_file(path: str, expected_sha256: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    actual = _sha256_file(path)
    return actual == expected_sha256.lower()


def download_file_atomic(
    url: str,
    dest_path: str,
    expected_sha256: str,
    timeout: int = 20,
) -> None:
    """Download and atomically replace target file after checksum validation."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=os.path.basename(dest_path) + ".",
        suffix=".tmp",
        dir=os.path.dirname(dest_path),
    )
    os.close(fd)
    try:
        hasher = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=timeout) as response, open(
            tmp_path, "wb"
        ) as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                hasher.update(chunk)

        digest = hasher.hexdigest().lower()
        if digest != expected_sha256.lower():
            raise ValueError(
                f"Checksum mismatch for {os.path.basename(dest_path)}: {digest}"
            )

        os.replace(tmp_path, dest_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def ensure_model_file(
    dest_path: str,
    url: str,
    expected_sha256: str,
) -> str:
    """Ensure model file exists and checksum is valid."""
    if is_valid_model_file(dest_path, expected_sha256):
        return dest_path

    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
        except Exception:
            pass

    download_file_atomic(url, dest_path, expected_sha256)
    return dest_path


def ensure_dnn_models() -> Tuple[str, str]:
    """Ensure DNN model files are available locally."""
    global _MODEL_CACHE

    offline = os.environ.get("PHOTOCROPPER_OFFLINE", "").strip().lower()
    if offline in {"1", "true", "yes", "on"}:
        raise RuntimeError("offline mode: DNN model download disabled")

    if _MODEL_CACHE:
        ptxt, pmodel = _MODEL_CACHE
        if is_valid_model_file(ptxt, DNN_PROTOTXT_SHA256) and is_valid_model_file(
            pmodel, DNN_MODEL_SHA256
        ):
            return _MODEL_CACHE

    model_dir = get_model_cache_dir()
    prototxt_path = os.path.join(model_dir, DNN_PROTOTXT_FILENAME)
    model_path = os.path.join(model_dir, DNN_MODEL_FILENAME)

    prototxt_path = ensure_model_file(
        prototxt_path,
        DNN_PROTOTXT_URL,
        DNN_PROTOTXT_SHA256,
    )
    model_path = ensure_model_file(
        model_path,
        DNN_MODEL_URL,
        DNN_MODEL_SHA256,
    )
    _MODEL_CACHE = (prototxt_path, model_path)
    return prototxt_path, model_path


__all__ = [
    'DNN_PROTOTXT_URL',
    'DNN_MODEL_URL',
    'DNN_PROTOTXT_SHA256',
    'DNN_MODEL_SHA256',
    'DNN_PROTOTXT_FILENAME',
    'DNN_MODEL_FILENAME',
    'DNN_CONFIDENCE_THRESHOLD',
    'get_model_cache_dir',
    'is_valid_model_file',
    'download_file_atomic',
    'ensure_model_file',
    'ensure_dnn_models',
]
