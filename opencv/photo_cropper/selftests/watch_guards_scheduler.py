#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Watch guards and scheduler self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_watch_actions_block_while_batch_or_manual_running() -> None:
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("watch action guard test")
    if app is None:
        return

    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QLabel, QLineEdit, QMainWindow, QMessageBox

    from ..core.settings_model import AppSettings
    from ..ui.main.actions.watch import WatchActions

    class FakeProcessor:
        def __init__(self) -> None:
            self.is_running = False

    class FakeBatchSession:
        def __init__(self) -> None:
            self.processor = FakeProcessor()

    class FakeWatchCoordinator:
        def __init__(self) -> None:
            self.is_active = False
            self.start_calls = []

        def start(self, **kwargs):
            self.start_calls.append(kwargs)
            raise AssertionError("Watch coordinator start should have been blocked")

    host_window = QMainWindow()
    refs = SimpleNamespace(
        input_path_edit=QLineEdit(),
        output_path_edit=QLineEdit(),
        watch_mode_action=QAction(host_window),
        status_label=QLabel(),
    )
    refs.watch_mode_action.setCheckable(True)
    refs.watch_mode_action.setChecked(True)

    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=FakeWatchCoordinator(),
        scheduler=SimpleNamespace(),
    )
    state = SimpleNamespace(
        settings=AppSettings(),
        manual_extract_running=False,
    )
    actions = WatchActions(state=state, refs=refs, services=services)

    warnings = []
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        services.batch_session.processor.is_running = True
        actions.start_watch_mode()
        assert refs.watch_mode_action.isChecked() is False
        assert len(warnings) == 1
        assert services.watch_mode_coordinator.start_calls == []

        refs.watch_mode_action.setChecked(True)
        services.batch_session.processor.is_running = False
        state.manual_extract_running = True
        actions.start_watch_mode()
        assert refs.watch_mode_action.isChecked() is False
        assert len(warnings) == 2
        assert services.watch_mode_coordinator.start_calls == []
    finally:
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        refs.status_label.deleteLater()
        if owned_app:
            app.quit()


def _test_batch_actions_block_when_watch_running() -> None:
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("batch action watch guard test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLineEdit, QMainWindow, QMessageBox

    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.main.actions.batch import BatchActions

    class FakeProcessor:
        is_running = False

    class FakeBatchSession:
        def __init__(self) -> None:
            self.processor = FakeProcessor()
            self.failed_files = ["failed.jpg"]
            self.create_calls = 0

        def create_processor(self, **_kwargs):
            self.create_calls += 1
            raise AssertionError("Batch processor creation should have been blocked")

    host_window = QMainWindow()
    refs = SimpleNamespace(
        input_path_edit=QLineEdit(),
        output_path_edit=QLineEdit(),
        progress_dialog=None,
        status_label=None,
        batch_prev_btn=None,
        batch_next_btn=None,
        batch_save_edits_btn=None,
        batch_failed_btn=None,
        batch_load_btn=None,
        batch_edit_status_label=None,
    )
    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=SimpleNamespace(is_active=True),
    )
    state = SimpleNamespace(
        settings=AppSettings(),
        image_list=[],
        current_image_index=-1,
        batch_contours_edited=set(),
        failed_boundary_files=[],
        manual_extract_running=False,
    )
    signals = SimpleNamespace(
        batch_progress_received=_SignalRecorder(),
        batch_log_received=_SignalRecorder(),
        batch_complete_received=_SignalRecorder(),
    )
    actions = BatchActions(state=state, refs=refs, services=services, signals=signals)

    warnings = []
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        actions.start_processing()
        actions.retry_failed_files()
        assert len(warnings) == 2
        assert services.batch_session.create_calls == 0
    finally:
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        if owned_app:
            app.quit()


def _test_scheduler_once_preserves_task_until_started() -> None:
    from ..core.scheduler import Scheduler, ScheduleRunStatus, ScheduleTask, ScheduleType

    task = ScheduleTask(
        task_id="once",
        name="once",
        schedule_type=ScheduleType.ONCE,
        input_path="in",
        output_path="out",
    )
    scheduler = Scheduler(process_callback=lambda *_args: ScheduleRunStatus.SKIPPED_BUSY)
    assert scheduler._execute_task(task) is False
    assert task.enabled is True
    assert task.last_run is None

    scheduler.set_process_callback(lambda *_args: ScheduleRunStatus.STARTED)
    assert scheduler._execute_task(task) is True
    assert task.enabled is False
    assert task.last_run is not None


def _test_scheduler_once_skip_keeps_next_run_due() -> None:
    from datetime import datetime, timedelta

    from ..core.scheduler import Scheduler, ScheduleRunStatus, ScheduleTask, ScheduleType

    task = ScheduleTask(
        task_id="once",
        name="once",
        schedule_type=ScheduleType.ONCE,
        input_path="in",
        output_path="out",
        enabled=True,
    )
    due_time = datetime.now() - timedelta(seconds=5)
    task.next_run = due_time
    scheduler = Scheduler(process_callback=lambda *_args: ScheduleRunStatus.SKIPPED_BUSY)
    scheduler._tasks[task.task_id] = task
    scheduler._check_schedules()
    assert task.enabled is True
    assert task.last_run is None
    assert task.next_run == due_time


def _test_scheduled_batch_uses_task_paths() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("scheduled path test")
    if app is None:
        return

    from PyQt6.QtWidgets import QLabel, QLineEdit, QMainWindow

    from ..core.scheduler import ScheduleRunStatus
    from ..core.settings_model import AppSettings
    from ..ui.main.actions.watch import WatchActions

    class FakeProcessor:
        is_running = False

    class FakeBatchSession:
        def __init__(self) -> None:
            self.processor = FakeProcessor()

    with tempfile.TemporaryDirectory(prefix="photocropper_schedule_paths_") as td:
        scheduled_input = os.path.join(td, "scheduled_in")
        scheduled_output = os.path.join(td, "scheduled_out")
        ui_input = os.path.join(td, "ui_in")
        ui_output = os.path.join(td, "ui_out")
        os.makedirs(scheduled_input, exist_ok=True)
        os.makedirs(scheduled_output, exist_ok=True)
        os.makedirs(ui_input, exist_ok=True)
        with open(os.path.join(scheduled_input, "a.jpg"), "wb") as handle:
            handle.write(b"not decoded by scan")

        host_window = QMainWindow()
        refs = SimpleNamespace(
            input_path_edit=QLineEdit(ui_input),
            output_path_edit=QLineEdit(ui_output),
            status_label=QLabel(),
        )
        services = SimpleNamespace(
            host_window=host_window,
            batch_session=FakeBatchSession(),
            watch_mode_coordinator=SimpleNamespace(is_active=False),
        )
        state = SimpleNamespace(settings=AppSettings(), manual_extract_running=False)
        actions = WatchActions(state=state, refs=refs, services=services)
        captured: dict[str, str] = {}

        def start_processing(**kwargs) -> bool:
            captured.update(kwargs)
            services.batch_session.processor.is_running = True
            return True

        actions.bind(start_processing=start_processing)
        status = actions.on_scheduled_batch_trigger(scheduled_input, scheduled_output)
        assert status == ScheduleRunStatus.STARTED
        assert captured["input_path_override"] == scheduled_input
        assert captured["output_path_override"] == scheduled_output

        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        refs.status_label.deleteLater()
        if owned_app:
            app.quit()
