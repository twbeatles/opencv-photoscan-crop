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
from ....utils.file_helpers import get_image_files, validate_directory
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowState

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
                self.refs.status_label.setText(f"⏰ 스케줄러 시간 형식 오류: {schedule_time_text}")
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

    def on_scheduled_batch_trigger(self, _input_dir: str, _output_dir: str) -> bool:
        busy_reason = self.busy_reason_for_scheduled_batch()
        if busy_reason:
            message = f"⏰ 스케줄 실행 건너뜀: {busy_reason} 작업 진행 중"
            logger.info(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.info(message)
            return False

        input_path = self.refs.input_path_edit.text().strip() if self.refs.input_path_edit else ""
        output_path = self.refs.output_path_edit.text().strip() if self.refs.output_path_edit else ""
        valid, error = validate_directory(input_path)
        if not valid:
            message = f"⏰ 스케줄 실행 실패(입력 폴더): {error}"
            logger.warning(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.warning(message)
            return False

        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            if self.refs.output_path_edit is not None:
                self.refs.output_path_edit.setText(output_path)

        try:
            os.makedirs(output_path, exist_ok=True)
        except Exception as exc:
            message = f"⏰ 스케줄 실행 실패(출력 폴더): {exc}"
            logger.warning(message)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(message)
            ToastManager.warning(message)
            return False

        recursive = bool(getattr(self.state.settings.file_management, "recursive_search", False))
        files = get_image_files(input_path, recursive=recursive)
        if not files:
            message = "⏰ 스케줄 실행 건너뜀: 처리할 이미지가 없습니다"
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
            message = f"⏰ 스케줄 배치 시작: {len(files)}개 파일"
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
                f"👁️ 감시 중... 처리 시작: {os.path.basename(filepath)}"
            )

    def start_watch_mode(self) -> None:
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
                QMessageBox.warning(self.services.host_window, "경고", "유효한 입력 폴더를 선택하세요.")
            elif start_result.error_code == "invalid_output":
                ToastManager.error("출력 폴더 준비 실패")
                if start_result.message and self.refs.status_label is not None:
                    self.refs.status_label.setText(f"폴더 감시 시작 실패: {start_result.message}")
            else:
                ToastManager.error("폴더 감시 시작 실패")
            return

        watch_root = input_path.strip() or (
            self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        )
        if self.refs.watch_mode_action is not None:
            self.refs.watch_mode_action.setText("👁️ 폴더 감시 중지")
        ToastManager.success(f"👁️ 폴더 감시 모드 시작: {watch_root}")
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"👁️ 폴더 감시 중: {watch_root}")

    def stop_watch_mode(self) -> None:
        self.services.watch_mode_coordinator.stop()
        if self.refs.watch_mode_action is not None:
            self.refs.watch_mode_action.setText("👁️ 폴더 감시 모드")
        ToastManager.info("폴더 감시 모드 중지됨")
        if self.refs.status_label is not None:
            self.refs.status_label.setText("폴더 감시 중지됨")

    def on_watched_file_complete(self, filepath: str, success: bool) -> None:
        if self.refs.status_label is None:
            return
        filename = os.path.basename(filepath)
        self.refs.status_label.setText(
            f"👁️ 처리 완료: {filename}" if success else f"👁️ 처리 실패: {filename}"
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
                detail = message or "skip"
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        f"👁️ 스킵: {filename} ({detail}, 대기 {wait_text})"
                    )
                ToastManager.info(f"ℹ️ 자동 처리 스킵: {filename} ({detail})")
            elif status_key == "partial_success":
                detail = message or "partial success"
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(
                        f"👁️ 부분 완료: {filename} ({detail}, 대기 {wait_text})"
                    )
                ToastManager.warning(f"⚠️ 자동 처리 부분 완료: {filename} ({detail})")
            else:
                if self.refs.status_label is not None:
                    self.refs.status_label.setText(f"👁️ 처리 완료: {filename} (대기 {wait_text})")
                ToastManager.success(f"✅ 자동 처리 완료: {filename}")
            return

        reason = status_key or "failed"
        detail = message or reason
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                f"👁️ 처리 실패: {filename} ({reason}, 대기 {wait_text})"
            )
        ToastManager.warning(f"⚠️ 자동 처리 실패: {filename} - {detail}")

    def on_watch_queue_metrics(self, queue_size: int, avg_wait_ms: int) -> None:
        if not self.services.watch_mode_coordinator.is_active:
            return
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                f"👁️ 감시 중... 대기열: {int(queue_size)}개, 평균 대기: {int(avg_wait_ms)}ms"
            )
