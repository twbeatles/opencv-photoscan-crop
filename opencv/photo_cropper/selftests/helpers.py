#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Shared helpers for lightweight self-tests."""

from __future__ import annotations

class _SignalRecorder:
    def __init__(self) -> None:
        self.calls = []

    def emit(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))

def _ensure_qt_app(context: str):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for {context}: {e}")
        return None, False

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True
    return app, owned_app
