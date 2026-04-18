from __future__ import annotations

import os
import platform


APP_NAME = "PhotoCropper"
LEGACY_HOME_DIR = ".photo_cropper"


def get_app_config_dir() -> str:
    system = platform.system()
    if system == "Windows":
        base = (
            os.environ.get("APPDATA")
            or os.environ.get("LOCALAPPDATA")
            or os.path.expanduser("~")
        )
        path = os.path.join(base, APP_NAME)
    else:
        path = os.path.join(os.path.expanduser("~"), LEGACY_HOME_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def get_app_cache_dir() -> str:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or get_app_config_dir()
        path = os.path.join(base, APP_NAME)
    else:
        path = get_app_config_dir()
    os.makedirs(path, exist_ok=True)
    return path


def get_library_root() -> str:
    path = os.path.join(get_app_cache_dir(), "library")
    os.makedirs(path, exist_ok=True)
    return path


def get_library_db_path() -> str:
    return os.path.join(get_library_root(), "library.db")


def get_thumbnails_dir() -> str:
    path = os.path.join(get_library_root(), "thumbnails")
    os.makedirs(path, exist_ok=True)
    return path


def get_preview_cache_dir() -> str:
    path = os.path.join(get_library_root(), "preview_cache")
    os.makedirs(path, exist_ok=True)
    return path


def get_logs_dir() -> str:
    path = os.path.join(get_library_root(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


def ensure_library_dirs() -> dict[str, str]:
    return {
        "root": get_library_root(),
        "db_path": get_library_db_path(),
        "thumbnails": get_thumbnails_dir(),
        "preview_cache": get_preview_cache_dir(),
        "logs": get_logs_dir(),
    }


def get_legacy_presets_file() -> str:
    return os.path.join(os.path.expanduser("~/.photo_cropper"), "photo_cropper_presets.json")


def get_legacy_profiles_dir() -> str:
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_NAME, "profiles")
    else:
        path = os.path.join(get_app_config_dir(), "profiles")
    os.makedirs(path, exist_ok=True)
    return path


def get_recipes_fallback_file() -> str:
    return os.path.join(get_app_config_dir(), "recipes.json")
