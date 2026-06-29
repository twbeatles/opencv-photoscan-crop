#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility exports for the folder-watch runtime."""

from __future__ import annotations

from .file_watch import (
    AutoProcessor,
    FolderWatcher,
    SUPPORTED_EXTENSIONS,
    WatchProcessResult,
)

__all__ = [
    "AutoProcessor",
    "FolderWatcher",
    "SUPPORTED_EXTENSIONS",
    "WatchProcessResult",
]
