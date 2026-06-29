#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Compatibility wrapper for the Photo Cropper self-test suite.

Run:
  python -m photo_cropper.selftest
"""

from __future__ import annotations

from .selftests.runner import TESTS, main

__all__ = ["TESTS", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
