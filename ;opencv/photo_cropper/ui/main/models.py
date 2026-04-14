#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared models for the main-window composition layer."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLineEdit,
    QLabel,
    QPushButton,
    QMenu,
    QProgressBar,
    QStatusBar,
    QToolBar,
    QMainWindow,
)

from ..widgets.floating_action_button import QuickActionFAB
from ..widgets.fullscreen_viewer import FullscreenViewerManager
from ..widgets.histogram_widget import HistogramWidget
from ..widgets.preview_widget import ImagePreviewWidget
from ..widgets.progress_dialog import ProgressDialog
from ..widgets.preset_manager import PresetComboBox
from ..widgets.settings import SettingsPanel
from ...core.batch import BatchSessionService
from ...core.history_manager import HistoryManager
from ...core.image import ImageProcessor
from ...core.scheduler import Scheduler
from ...core.settings_model import AppSettings, SettingsManager
from ...core.watch_mode import WatchModeCoordinator


@dataclass
class WindowState:
    """Pure runtime state for the main window."""

    settings: AppSettings
    current_image_path: Optional[str] = None
    image_list: list[str] = field(default_factory=list)
    current_image_index: int = -1
    preview_request_id: int = 0
    latest_preview_request_id: int = 0
    applied_preview_request_id: int = -1
    preview_request_paths: dict[int, str] = field(default_factory=dict)
    preview_settings_revision: int = 0
    preview_settings_snapshot: dict[str, Any] = field(default_factory=dict)
    pending_input_path: str = ""
    last_original: Optional[Any] = None
    last_processed: Optional[Any] = None
    last_detected_contour: Optional[Any] = None
    active_input_root: str = ""
    batch_contours_norm: dict[str, Any] = field(default_factory=dict)
    batch_contours_edited: set[str] = field(default_factory=set)
    failed_boundary_files: list[str] = field(default_factory=list)
    manual_extract_thread: Optional[threading.Thread] = None
    manual_extract_stop_event: threading.Event = field(
        default_factory=threading.Event
    )
    manual_extract_running: bool = False
    multi_compare_window: Optional[Any] = None


@dataclass
class WindowRefs:
    """Concrete Qt object references created by UI builders."""

    toolbar: Optional[QToolBar] = None
    statusbar: Optional[QStatusBar] = None
    status_label: Optional[QLabel] = None
    status_progress: Optional[QProgressBar] = None
    image_info_badge: Optional[QLabel] = None
    file_count_badge: Optional[QLabel] = None
    input_path_edit: Optional[QLineEdit] = None
    output_path_edit: Optional[QLineEdit] = None
    preview_widget: Optional[ImagePreviewWidget] = None
    histogram_widget: Optional[HistogramWidget] = None
    settings_panel: Optional[SettingsPanel] = None
    process_btn: Optional[QPushButton] = None
    preset_combo: Optional[PresetComboBox] = None
    batch_load_btn: Optional[QPushButton] = None
    batch_failed_btn: Optional[QPushButton] = None
    batch_prev_btn: Optional[QPushButton] = None
    batch_next_btn: Optional[QPushButton] = None
    batch_save_edits_btn: Optional[QPushButton] = None
    batch_edit_status_label: Optional[QLabel] = None
    fab: Optional[QuickActionFAB] = None
    progress_dialog: Optional[ProgressDialog] = None
    watch_mode_action: Optional[QAction] = None
    theme_actions: dict[str, QAction] = field(default_factory=dict)
    profile_menu: Optional[QMenu] = None
    menus: dict[str, QMenu] = field(default_factory=dict)
    actions: dict[str, QAction] = field(default_factory=dict)
    labels: dict[str, QLabel] = field(default_factory=dict)
    buttons: dict[str, QPushButton] = field(default_factory=dict)


@dataclass
class WindowServices:
    """Runtime services used by the window actions."""

    host_window: QMainWindow
    settings_manager: SettingsManager
    image_processor: ImageProcessor
    history_manager: HistoryManager
    fullscreen_manager: FullscreenViewerManager
    watch_mode_coordinator: WatchModeCoordinator
    scheduler: Scheduler
    batch_session: BatchSessionService
    preview_timer: QTimer
    input_path_scan_timer: QTimer
    preview_worker_host: Optional[Any] = None
    auto_save_timer: Optional[QTimer] = None


@dataclass
class WindowSignals:
    """Qt signals exposed as injectable collaborators."""

    preview_process_requested: Any
    batch_progress_received: Any
    batch_log_received: Any
    batch_complete_received: Any
