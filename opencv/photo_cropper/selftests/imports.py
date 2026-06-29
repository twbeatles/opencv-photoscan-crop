#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Imports self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_crop_editor_import_smoke() -> None:
    try:
        from ..ui.widgets.crop_editor_widget import CropEditorWidget
    except Exception as e:
        raise AssertionError(f"Crop editor import failed: {e}")

    assert CropEditorWidget is not None

def _test_preview_worker_import_smoke() -> None:
    try:
        from ..ui.main.preview_worker import PreviewWorker
    except Exception as e:
        raise AssertionError(f"Preview worker import failed: {e}")

    assert PreviewWorker is not None

def _test_ui_action_modules_import_smoke() -> None:
    try:
        from ..ui.main.batch_actions import BatchActions
        from ..ui.main.preview_actions import PreviewActions
        from ..ui.main.feature_actions import FeatureActions
        from ..ui.main.navigation_actions import NavigationActions
        from ..ui.main.dialog_actions import DialogActions
        from ..ui.main.io_actions import InputActions
        from ..ui.main.settings_actions import SettingsActions
        from ..ui.main.watch_actions import WatchActions
    except Exception as e:
        raise AssertionError(f"UI action modules import failed: {e}")

    assert BatchActions is not None
    assert PreviewActions is not None
    assert FeatureActions is not None
    assert NavigationActions is not None
    assert DialogActions is not None
    assert InputActions is not None
    assert SettingsActions is not None
    assert WatchActions is not None

def _test_ui_canonical_package_import_smoke() -> None:
    try:
        from ..ui.main.actions import (
            BatchActions,
            DialogActions,
            FeatureActions,
            InputActions,
            LifecycleActions,
            NavigationActions,
            PreviewActions,
            PreviewWorkerHost,
            SettingsActions,
            ToolActions,
            WatchActions,
        )
        from ..ui.main.builders import (
            build_central_widget,
            build_fab,
            build_menu,
            build_statusbar,
            build_toolbar,
        )
        from ..ui.main.models import WindowRefs, WindowServices, WindowSignals, WindowState
    except Exception as e:
        raise AssertionError(f"UI canonical package import failed: {e}")

    assert BatchActions is not None
    assert DialogActions is not None
    assert FeatureActions is not None
    assert InputActions is not None
    assert LifecycleActions is not None
    assert NavigationActions is not None
    assert PreviewActions is not None
    assert PreviewWorkerHost is not None
    assert SettingsActions is not None
    assert ToolActions is not None
    assert WatchActions is not None
    assert build_central_widget is not None
    assert build_fab is not None
    assert build_menu is not None
    assert build_statusbar is not None
    assert build_toolbar is not None
    assert WindowRefs is not None
    assert WindowServices is not None
    assert WindowSignals is not None
    assert WindowState is not None

def _test_main_window_import_smoke() -> None:
    try:
        from ..ui.main import MainWindow
    except Exception as e:
        raise AssertionError(f"MainWindow import failed: {e}")

    assert MainWindow is not None

def _test_manual_extract_service_import_smoke() -> None:
    try:
        from ..core.manual_extract import ManualExtractProcessor, ManualExtractOutcome
    except Exception as e:
        raise AssertionError(f"Manual extract service import failed: {e}")

    assert ManualExtractProcessor is not None
    assert ManualExtractOutcome is not None

def _test_image_save_io_module_smoke() -> None:
    try:
        from ..core.image.save_io import resolve_save_codec, save_image_unicode
    except Exception as e:
        raise AssertionError(f"Image save IO module import failed: {e}")

    ext, fmt = resolve_save_codec("out", "PNG")
    assert ext == ".png"
    assert fmt == "PNG"
    assert save_image_unicode is not None

def _test_watch_mode_coordinator_import_smoke() -> None:
    try:
        from ..core.watch_mode import WatchModeCoordinator, WatchStartResult
    except Exception as e:
        raise AssertionError(f"Watch mode coordinator import failed: {e}")

    assert WatchModeCoordinator is not None
    assert WatchStartResult is not None

__all__ = [
    "_test_crop_editor_import_smoke",
    "_test_preview_worker_import_smoke",
    "_test_ui_action_modules_import_smoke",
    "_test_ui_canonical_package_import_smoke",
    "_test_main_window_import_smoke",
    "_test_manual_extract_service_import_smoke",
    "_test_image_save_io_module_smoke",
    "_test_watch_mode_coordinator_import_smoke",
]
