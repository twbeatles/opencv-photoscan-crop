#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Result types for advanced image processing."""

from dataclasses import dataclass

import numpy as np


@dataclass
class DeskewResult:
    """Result of auto deskew operation."""
    image: np.ndarray
    angle: float
    confidence: float


@dataclass
class PerspectiveResult:
    """Result of perspective correction."""
    image: np.ndarray
    src_points: np.ndarray
    dst_points: np.ndarray
    success: bool
    message: str = ""

__all__ = ["DeskewResult", "PerspectiveResult"]
