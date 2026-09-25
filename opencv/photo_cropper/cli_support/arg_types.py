#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Range-checked argparse value types for the Photo Cropper CLI.

Single responsibility: convert raw CLI strings into validated
int/float values with consistent ``argparse.ArgumentTypeError`` messages.
"""

from __future__ import annotations

import argparse


def _int_in_range(min_value: int, max_value: int):
    def _parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Expected integer, got: {value}") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"Expected value in range [{min_value}, {max_value}], got: {parsed}"
            )
        return parsed

    return _parse


def _float_in_range(min_value: float, max_value: float):
    def _parse(value: str) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Expected float, got: {value}") from exc
        if parsed < min_value or parsed > max_value:
            raise argparse.ArgumentTypeError(
                f"Expected value in range [{min_value}, {max_value}], got: {parsed}"
            )
        return parsed

    return _parse


__all__ = ["_int_in_range", "_float_in_range"]
