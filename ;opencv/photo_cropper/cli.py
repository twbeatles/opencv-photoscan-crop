#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility wrapper for the Photo Cropper command-line interface."""

from __future__ import annotations

import sys as _sys

from .cli_support import runtime as _runtime

if __name__ == "__main__":
    raise SystemExit(_runtime.main())

_sys.modules[__name__] = _runtime
