#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lifecycle utilities for the main window."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QThread
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from ..models import WindowRefs, WindowServices, WindowState
from ..preview_worker import PreviewWorker


class PreviewWorkerHost:
    """Manage the preview worker and its dedicated thread."""

    def __init__(
        self,
        services: WindowServices,
        preview_process_requested,
        on_preview_ready,
        on_preview_failed,
    ):
        self._thread = QThread(services.host_window)
        self._worker = PreviewWorker()
        self._worker.moveToThread(self._thread)
        preview_process_requested.connect(self._worker.process_preview)
        self._worker.preview_ready.connect(on_preview_ready)
        self._worker.preview_failed.connect(on_preview_failed)
        self._thread.start()

    def teardown(self) -> None:
        if self._thread is None:
            return
        self._thread.quit()
        self._thread.wait(2000)
        self._worker = None
        self._thread = None


class LifecycleActions:
    """Handle teardown and window-close behavior."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
        *,
        save_window_state: Callable[[], None],
        persist_paths: Callable[[], bool],
        batch_cleanup: Callable[[], None],
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._save_window_state = save_window_state
        self._persist_paths = persist_paths
        self._batch_cleanup = batch_cleanup

    def close_event(self, event: Optional[QCloseEvent]) -> None:
        if event is None:
            return

        processor = self.services.batch_session.processor
        batch_running = bool(processor and processor.is_running)
        manual_running = bool(self.state.manual_extract_running)

        if batch_running or manual_running:
            reply = QMessageBox.question(
                self.services.host_window,
                "종료 확인",
                "작업이 진행 중입니다. 정말 종료하시겠습니까?\n종료 시 진행 중인 작업은 중단됩니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            if manual_running:
                self.state.manual_extract_stop_event.set()
            if batch_running:
                self.services.batch_session.request_stop()

        if self.refs.progress_dialog is not None:
            try:
                self.refs.progress_dialog.close()
            except Exception:
                pass
            self.refs.progress_dialog = None

        self._persist_paths()
        self._save_window_state()
        self._batch_cleanup()
        self.services.history_manager.clear()
        if self.services.watch_mode_coordinator.is_active:
            self.services.watch_mode_coordinator.stop()
        self.services.scheduler.stop()
        if self.services.preview_worker_host is not None:
            self.services.preview_worker_host.teardown()
            self.services.preview_worker_host = None

        event.accept()
