#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Main window composition root for the Photo Cropper UI."""

from __future__ import annotations

import logging
import os
from typing import Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow

from ..widgets.toast_notification import ToastManager
from .composition import build_main_window_shell, wire_window_actions
from .management_runtime import ManagementRuntimeMixin
from .models import WindowRefs, WindowServices, WindowSignals, WindowState
from .translation import TranslationRuntimeMixin
from ...core.batch import BatchProcessor, BatchSessionService
from ...core.history_manager import HistoryManager
from ...core.image import ImageProcessor
from ...core.jobs import JobOrchestrator
from ...core.library import (
    DuplicateService,
    LibraryIngestService,
    QueryService,
    ReviewService,
    ThumbnailService,
    get_library_repository,
)
from ...core.recipes import get_recipe_manager
from ...i18n.catalog import get_translator, set_language, t
from ...core.scheduler import Scheduler
from ...core.settings_model import SettingsManager
from ...core.watch_mode import WatchModeCoordinator
from ..widgets.fullscreen_viewer import FullscreenViewerManager

logger = logging.getLogger(__name__)




class MainWindow(ManagementRuntimeMixin, TranslationRuntimeMixin, QMainWindow):
    """Thin composition root for the Photo Cropper desktop UI."""

    VERSION = "9.0"
    TITLE = f"📸 사진 자동 자르기 v{VERSION}"
    preview_process_requested = pyqtSignal(int, str, int, object)
    batch_progress_received = pyqtSignal(object)
    batch_log_received = pyqtSignal(str, str)
    batch_complete_received = pyqtSignal(object, object)
    management_task_finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        signals = WindowSignals(
            preview_process_requested=self.preview_process_requested,
            batch_progress_received=self.batch_progress_received,
            batch_log_received=self.batch_log_received,
            batch_complete_received=self.batch_complete_received,
        )
        settings_manager = SettingsManager()
        settings = settings_manager.load()
        set_language(getattr(settings.ui, "language", "ko"))
        library_repository = None
        thumbnail_service = None
        library_ingest_service = None
        query_service = None
        review_service = None
        duplicate_service = None
        recipe_manager = None
        job_orchestrator = None
        try:
            library_repository = get_library_repository()
            thumbnail_service = ThumbnailService()
            duplicate_service = DuplicateService(library_repository)
            job_orchestrator = JobOrchestrator(
                library_repository,
                thumbnail_service=thumbnail_service,
                duplicate_service=duplicate_service,
            )
            library_ingest_service = LibraryIngestService(
                library_repository,
                thumbnail_service=thumbnail_service,
                duplicate_service=duplicate_service,
            )
            query_service = QueryService(library_repository)
            review_service = ReviewService(
                library_repository,
                create_reprocess_job=job_orchestrator.prepare_review_reprocess,
            )
        except Exception as exc:
            logger.warning("Library services unavailable: %s", exc)

        try:
            recipe_manager = get_recipe_manager()
        except Exception as exc:
            logger.warning("Recipe manager unavailable: %s", exc)
            recipe_manager = None

        state = WindowState(
            settings=settings,
            preview_settings_snapshot=settings.to_dict(),
            active_recipe_name=recipe_manager.get_current_recipe_name()
            if recipe_manager is not None
            else "",
        )
        refs = WindowRefs()
        preview_timer = QTimer(self)
        preview_timer.setSingleShot(True)
        input_path_scan_timer = QTimer(self)
        input_path_scan_timer.setSingleShot(True)
        services = WindowServices(
            host_window=self,
            settings_manager=settings_manager,
            image_processor=ImageProcessor(
                settings.algorithm,
                settings.processing,
                settings.advanced,
                settings.performance,
                debug_settings=settings.debug,
            ),
            history_manager=HistoryManager(max_history=50),
            fullscreen_manager=FullscreenViewerManager(),
            watch_mode_coordinator=WatchModeCoordinator(
                settings=settings,
                on_log=signals.batch_log_received.emit,
                parent=self,
            ),
            scheduler=Scheduler(parent=self),
            batch_session=BatchSessionService(),
            preview_timer=preview_timer,
            input_path_scan_timer=input_path_scan_timer,
            library_repository=library_repository,
            thumbnail_service=thumbnail_service,
            library_ingest_service=library_ingest_service,
            query_service=query_service,
            review_service=review_service,
            duplicate_service=duplicate_service,
            recipe_manager=recipe_manager,
            job_orchestrator=job_orchestrator,
        )

        self.state = state
        self.refs = refs
        self.services = services
        self.signals = signals
        self.settings_manager = settings_manager
        self.image_processor = services.image_processor
        self.history_manager = services.history_manager
        self.fullscreen_manager = services.fullscreen_manager
        self.watch_mode_coordinator = services.watch_mode_coordinator
        self._scheduler = services.scheduler
        self._translator = get_translator()
        self.services.watch_mode_coordinator.set_result_callback(self._on_watch_result)
        self.management_task_finished.connect(self._on_management_task_finished)

        wire_window_actions(self, state, refs, services, signals)

        build_main_window_shell(self, state, refs, services)

        ToastManager.set_parent(self)
        self.settings_actions.apply_loaded_settings(state.settings)
        self.batch_actions.update_batch_edit_controls()
        self.settings_actions.restore_window_state()
        self.refresh_management_views()
        self.setAcceptDrops(True)
        self._translator.add_language_change_listener(self._on_language_changed)
        self.retranslate_ui()

    @property
    def batch_processor(self) -> Optional[BatchProcessor]:
        return self.services.batch_session.processor

    def _setup_window(self) -> None:
        self.setWindowTitle(t("app.title", version=self.VERSION))
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        screen_obj = QApplication.primaryScreen()
        if screen_obj is not None:
            screen = screen_obj.geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )

    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]) -> None:
        self.input_actions.drag_enter_event(a0)

    def dropEvent(self, a0: Optional[QDropEvent]) -> None:
        self.input_actions.drop_event(a0)

    def keyPressEvent(self, a0: Optional[QKeyEvent]) -> None:
        if self.input_actions.handle_key_press(a0):
            return
        if a0 is not None:
            super().keyPressEvent(a0)

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        try:
            self._translator.remove_language_change_listener(self._on_language_changed)
        except Exception:
            pass
        self.lifecycle_actions.close_event(a0)

    def open_path_in_workbench(self, image_path: str) -> None:
        normalized = os.path.abspath(str(image_path or ""))
        if not normalized or not os.path.exists(normalized):
            return
        parent_dir = os.path.dirname(normalized)
        if self.refs.input_path_edit is not None:
            self.refs.input_path_edit.setText(parent_dir)
        if self.refs.output_path_edit is not None and not self.refs.output_path_edit.text().strip():
            self.refs.output_path_edit.setText(os.path.join(parent_dir, "output_cropped"))
        self.state.current_image_path = normalized
        if self.refs.shell_nav is not None:
            self.refs.shell_nav.setCurrentRow(1)
        self.preview_actions.request_preview()

    def apply_recipe_from_management(self, recipe_name: str) -> None:
        if not recipe_name:
            return
        self.state.active_recipe_name = recipe_name
        self.tool_actions.on_preset_selected(recipe_name)
        self.refresh_management_views()
