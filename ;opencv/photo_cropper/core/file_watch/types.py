#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared types for folder watching."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WatchProcessResult:
    """Detailed process callback result used by AutoProcessor."""

    success: bool
    status: str = "success"
    message: str = ""


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".tiff",
    ".tif",
    ".webp",
}

__all__ = ["SUPPORTED_EXTENSIONS", "WatchProcessResult"]
