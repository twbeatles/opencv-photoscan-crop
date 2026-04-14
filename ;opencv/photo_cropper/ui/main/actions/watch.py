#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watch mode and scheduler actions."""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QMessageBox

from ....core.scheduler import ScheduleTask, ScheduleType
from ....core.settings_model.validation import (
    build_validation_summary,
    validate_settings,
)
from ....i18n.catalog import t
from ....utils.file_helpers import (
    build_recursive_excluded_roots,
    get_image_files,
)
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowState
from ..services import BatchRuntimeFlow, UiMessageFactory, WatchRuntimeFlow

logger = logging.getLogger(__name__)


class WatchActions:
    """Handle watch mode lifecycle and runtime scheduler integration."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self.batch_runtime = BatchRuntimeFlow()
        self.watch_runtime = WatchRuntimeFlow()
        self.messages = UiMessageFactory()
        self._start_processing: Optional[Callable[[], None]] = None
        self._scheduler_task_id: Optional[str] = None

    def bind(self, *, start_processing: Callable[[], None]) -> None:
        self._start_processing = start_processing

    @staticmethod
    def resolve_schedule_type(raw_value: str) -> ScheduleType:
        normalized = str(raw_value or "").strip().lower()
        mapping = {
            "once": ScheduleType.ONCE,
            "daily": ScheduleType.DAILY,
            "interval": ScheduleType.INTERVAL,
            "hourly": ScheduleType.HOURLY,
        }
        return mapping.get(normalized, ScheduleType.INTERVAL)

    def reconfigure_scheduler(self) -> None:
        self.services.scheduler.stop()
        for task in list(self.services.scheduler.get_all_tasks()):
            self.services.scheduler.remove_task(task.task_id)
        self._scheduler_task_id = None

        watch_settings = getattr(self.state.settings, "watch_mode", None)
        if not watch_settings or not bool(getattr(watch_settings, "scheduler_enabled", False)):
            return

        schedule_type = self.resolve_schedule_type(
            str(getattr(watch_settings, "schedule_type", "interval"))
        )
        schedule_time_text = str(getattr(watch_settings, "schedule_time", "00:00") or "00:00")
        schedule_time = QTime.fromString(schedule_time_text, "HH:mm")
        if schedule_type in (ScheduleType.DAILY, ScheduleType.ONCE) and not schedule_time.isValid():
            logger.warning("Scheduler time is invalid: %s", schedule_time_text)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    t("watch.scheduler.invalid_time", value=schedule_time_text)
                )
            return

        interval_minutes = int(getattr(watch_settings, "schedule_interval_minutes", 60) or 60)
        interval_minutes = max(5, min(1440, interval_minutes))
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        output_path = self.refs.output_path_edit.text() if self.refs.output_path_edit else ""

        task = ScheduleTask(
            task_id="",
            name="ui_auto_batch",
            schedule_type=schedule_type,
            time=schedule_time if schedule_time.isValid() else None,
            interval_minutes=interval_minutes,
            input_path=str(input_path or ""),
            output_path=str(output_path or ""),
            enabled=True,
        )
        self._scheduler_task_id = self.services.scheduler.add_task(task)
        self.services.scheduler.start()
        logger.info(
            "Scheduler configured: type=%s, time=%s, interval=%s",
            schedule_type.value,
            schedule_time_text,
            interval_minutes,
        )

    def busy_reason_for_scheduled_batch(self) -> str:
        processor = self.services.batch_session.processor
        if processor and processor.is_running:
            return "batch"
        if self.state.manual_extract_running:
            return "manual"
        if self.services.watch_mode_coordinator.is_active:
            return "watch"
        return ""

    def busy_reason_for_watch_start(self) -> str:
        processor = self.services.batch_session.processor
        if processor and processor.is_running:
            return "batch"
        if self.state.manual_extract_running:
            return "manual"
        if self.services.watch_mode_coordinator.is_active:
            return "watch"
        return ""

    def on_scheduled_batch_trigger(self, _input_dir: str, _output_dir: str) -> bool:
        busy_reason = self.busy_reason_for_scheduled_batch()
        if busy_reason:
            message = t(
                "watch.scheduler.skip_busy",
                reason=self.watch_runtime.busy_reason_label(busy_reason),
            )
            logger.info(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.info(message)
            return False
        issues = validate_settings(self.state.settings)
        if issues:
            message = build_validation_summary(issues)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.warning(message)
            return False

        input_path = self.refs.input_path_edit.text().strip() if self.refs.input_path_edit else ""
        output_path = self.refs.output_path_edit.text().strip() if self.refs.output_path_edit else ""
        resolved = self.batch_runtime.resolve_io_paths(
            input_path=input_path,
            output_path=output_path,
            recursive=bool(getattr(self.state.settings.file_management, "recursive_search", False)),
            failed_folder_name=self.state.settings.file_management.failed_folder_name,
        )
        if not resolved.ok:
            message = t("watch.scheduler.failed", error=resolved.message)
            logger.warning(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.warning(message)
            return False
        input_path = resolved.input_path
        output_path = resolved.output_path
        if self.refs.output_path_edit is not None and self.refs.output_path_edit.text().strip() != output_path:
            self.refs.output_path_edit.setText(output_path)

        recursive = bool(getattr(self.state.settings.file_management, "recursive_search", False))

        excluded_roots = (
            build_recursive_excluded_roots(
                input_path,
                output_path,
                failed_folder_name=self.state.settings.file_management.failed_folder_name,
            )
            if recursive
            else None
        )
        files = get_image_files(
            input_path,
            recursive=recursive,
            excluded_roots=excluded_roots,
        )
        if not files:
            message = t("watch.scheduler.skip_no_files")
            logger.info(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            return False

        if self._start_processing is None:
            return False
        self._start_processing()
        processor = self.services.batch_session.processor
        started = bool(processor and processor.is_running)
        if started:
            message = t("watch.scheduler.started", count=len(files))
            logger.info(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.info(message)
        return started

    def on_scheduler_task_started(self, task_id: str) -> None:
        if task_id != self._scheduler_task_id:
            return
        logger.info("Scheduled task fired: %s", task_id)

    def on_scheduler_task_completed(self, task_id: str, success: bool) -> None:
        if task_id != self._scheduler_task_id:
            return
        logger.info("Scheduled task completed: %s (started=%s)", task_id, success)

    def toggle_watch_mode(self, checked: bool) -> None:
        if checked:
            self.start_watch_mode()
        else:
            self.stop_watch_mode()

    def on_processing_started(self, filepath: str) -> None:
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t("watch.processing_started", filename=os.path.basename(filepath))
            )

    def start_watch_mode(self) -> None:
        busy_reason = self.busy_reason_for_watch_start()
        if busy_reason:
            if self.refs.watch_mode_action is not None:
                self.refs.watch_mode_action.setChecked(False)
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t(
                    "watch.start.busy",
                    reason=self.watch_runtime.busy_reason_label(busy_reason),
                ),
            )
            return
        issues = validate_settings(self.state.settings)
        if issues:
            if self.refs.watch_mode_action is not None:
                self.refs.watch_mode_action.setChecked(False)
            QMessageBox.warning(
                self.services.host_window,
                t("validation.config_invalid_title"),
                t(
                    "validation.config_invalid_body",
                    summary=build_validation_summary(issues),
                ),
            )
            return

        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        output_path = self.refs.output_path_edit.text() if self.refs.output_path_edit else ""
        watch_settings = getattr(self.state.settings, "watch_mode", None)

        start_result = self.services.watch_mode_coordinator.start(
            input_path=input_path,
            output_path=output_path,
            watch_settings=watch_settings,
        )

        if start_result.output_path and start_result.output_path != output_path:
            if self.refs.output_path_edit is not None:
                self.refs.output_path_edit.setText(start_result.output_path)

        if not start_result.success:
            if self.refs.watch_mode_action is not None:
                self.refs.watch_mode_action.setChecked(False)
            if start_result.error_code == "invalid_input":
                QMessageBox.warning(
                    self.services.host_window,
                    self.messages.warning_title,
                    t("validation.input_invalid"),
                )
            elif start_result.error_code == "invalid_output":
                ToastManager.error(t("watch.start.invalid_output"))
                if start_result.message and self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        t("watch.start.failed", error=start_result.message)
                    )
            elif start_result.error_code == "unsafe_output":
                QMessageBox.warning(
                    self.services.host_window,
                    self.messages.warning_title,
                    start_result.message
                    or t("watch.start.unsafe_output"),
                )
                if start_result.message and self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        t("watch.start.failed", error=start_result.message)
                    )
            else:
                ToastManager.error(t("watch.start.error"))
            return

        watch_root = input_path.strip() or (
            self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        )
        if self.refs.watch_mode_action is not None:
            self.refs.watch_mode_action.setText(t("menu.tools.watch_stop"))
        ToastManager.success(t("watch.start.toast", root=watch_root))
        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("watch.running", root=watch_root))

    def stop_watch_mode(self) -> None:
        self.services.watch_mode_coordinator.stop()
        if self.refs.watch_mode_action is not None:
            self.refs.watch_mode_action.setText(t("menu.tools.watch_mode"))
        ToastManager.info(t("watch.stop.toast"))
        if self.refs.status_label is not None:
            self.refs.status_label.setText(t("watch.stop.status"))

    def on_watched_file_complete(self, filepath: str, success: bool) -> None:
        if self.refs.status_label is None:
            return
        filename = os.path.basename(filepath)
        self.refs.status_label.setText(
            t("watch.file_complete.success", filename=filename)
            if success
            else t("watch.file_complete.failed", filename=filename)
        )

    def on_watched_file_complete_detailed(
        self,
        filepath: str,
        success: bool,
        status: str,
        message: str,
        wait_ms: int,
    ) -> None:
        filename = os.path.basename(filepath)
        status_key = (status or "").lower()
        wait_text = f"{int(wait_ms)}ms"

        if success:
            if status_key == "skipped":
                detail = message or t("watch.detail.skip")
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        t(
                            "watch.detailed.skipped",
                            filename=filename,
                            detail=detail,
                            wait=wait_text,
                        )
                    )
                ToastManager.info(
                    t("watch.toast.skipped", filename=filename, detail=detail)
                )
            elif status_key == "partial_success":
                detail = message or t("watch.detail.partial")
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        t(
                            "watch.detailed.partial",
                            filename=filename,
                            detail=detail,
                            wait=wait_text,
                        )
                    )
                ToastManager.warning(
                    t("watch.toast.partial", filename=filename, detail=detail)
                )
            else:
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        t("watch.detailed.success", filename=filename, wait=wait_text)
                    )
                ToastManager.success(t("watch.toast.success", filename=filename))
            return

        reason = status_key or t("watch.detail.failed")
        detail = message or reason
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t(
                    "watch.detailed.failed",
                    filename=filename,
                    reason=reason,
                    wait=wait_text,
                )
            )
        ToastManager.warning(
            t("watch.toast.failed", filename=filename, detail=detail)
        )

    def on_watch_queue_metrics(self, queue_size: int, avg_wait_ms: int) -> None:
        if not self.services.watch_mode_coordinator.is_active:
            return
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t(
                    "watch.queue_metrics",
                    queue=int(queue_size),
                    wait=int(avg_wait_ms),
                )
            )
