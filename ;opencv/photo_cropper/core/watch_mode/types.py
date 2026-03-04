#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Types for watch mode orchestration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchStartResult:
    """Result of a watch mode start request."""

    success: bool
    output_path: str = ""
    error_code: str = ""
    message: str = ""

