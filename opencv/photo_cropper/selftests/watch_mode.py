#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Watch Mode self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_watch_mode_coordinator_invalid_input() -> None:
    from ..core.settings_model import AppSettings
    from ..core.watch_mode import WatchModeCoordinator

    coordinator = WatchModeCoordinator(settings=AppSettings())
    result = coordinator.start(input_path="", output_path="")
    assert result.success is False
    assert result.error_code == "invalid_input"
    coordinator.stop()
    coordinator.deleteLater()

def _test_watch_mode_coordinator_recursive_output_guard() -> None:
    import os
    import tempfile

    from ..core.settings_model import AppSettings
    from ..core.watch_mode import WatchModeCoordinator

    settings = AppSettings()
    settings.watch_mode.recursive = True
    coordinator = WatchModeCoordinator(settings=settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_guard_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(input_dir, "output_cropped")
        os.makedirs(output_dir, exist_ok=True)

        result = coordinator.start(
            input_path=input_dir,
            output_path=output_dir,
            watch_settings=settings.watch_mode,
        )

        assert result.success is False
        assert result.error_code == "unsafe_output"
        assert os.path.abspath(result.output_path) == os.path.abspath(output_dir)

    coordinator.stop()
    coordinator.deleteLater()

def _test_watch_mode_processing_disables_failed_file_move() -> None:
    from types import SimpleNamespace

    from ..core.batch import ProcessStatus
    from ..core.settings_model import AppSettings
    from ..core.watch_mode import WatchModeCoordinator

    settings = AppSettings()
    settings.file_management.move_failed_files = True
    coordinator = WatchModeCoordinator(settings=settings)

    class FakeBatchProcessor:
        def __init__(self) -> None:
            self.updated_settings = []
            self.process_calls = []

        def update_settings(self, updated_settings) -> None:
            self.updated_settings.append(updated_settings)

        def process_single(
            self,
            input_path: str,
            output_path: str,
            input_root: str | None = None,
            **kwargs,
        ):
            snapshot = self.updated_settings[-1]
            self.process_calls.append(
                (
                    input_path,
                    output_path,
                    snapshot.file_management.move_failed_files,
                    input_root,
                    kwargs.get("clear_stop_event"),
                )
            )
            return SimpleNamespace(status=ProcessStatus.SUCCESS, message="ok")

    fake_batch = FakeBatchProcessor()
    coordinator._batch_processor = fake_batch
    coordinator._watch_input_root = "watch-root"

    result = coordinator._process_watched_file("input.jpg", "output")
    assert result["success"] is True
    assert result["status"] == "success"
    assert settings.file_management.move_failed_files is True
    assert len(fake_batch.updated_settings) == 1
    assert fake_batch.updated_settings[0] is not settings
    assert fake_batch.updated_settings[0].file_management.move_failed_files is False
    assert fake_batch.process_calls == [("input.jpg", "output", False, "watch-root", False)]

    coordinator.deleteLater()

def _test_watch_process_single_preserves_stop_request() -> None:
    import os
    import tempfile

    from ..core.batch import BatchProcessor, ProcessStatus
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_stop_") as td:
        src = os.path.join(td, "source.jpg")
        out = os.path.join(td, "out")
        with open(src, "wb") as handle:
            handle.write(b"placeholder")

        processor = BatchProcessor(AppSettings())
        processor.request_stop()
        result = processor.process_single(src, out, clear_stop_event=False)
        assert result.status == ProcessStatus.CANCELLED
        assert not os.path.exists(os.path.join(out, "source_cropped.jpg"))

def _test_recursive_watch_new_subdir_initial_scan() -> None:
    import os
    import shutil
    import tempfile
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for recursive watch test: {e}")
        return

    from ..core.folder_watcher import FolderWatcher

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_") as td:
        watch_root = os.path.join(td, "watch")
        incoming_root = os.path.join(td, "incoming")
        os.makedirs(watch_root, exist_ok=True)
        os.makedirs(incoming_root, exist_ok=True)

        bundle = os.path.join(incoming_root, "bundle")
        os.makedirs(bundle, exist_ok=True)
        src_file = os.path.join(bundle, "sample.jpg")
        with open(src_file, "wb") as f:
            f.write(b"fakejpg")

        detected = []
        watcher = FolderWatcher(recursive=True, debounce_ms=80)
        watcher.new_file_detected.connect(lambda path: detected.append(path))
        assert watcher.start(watch_root)

        moved_dir = os.path.join(watch_root, "bundle")
        shutil.move(bundle, moved_dir)

        deadline = time.time() + 3.0
        while time.time() < deadline and not detected:
            app.processEvents()
            time.sleep(0.02)

        watcher.stop()
        expected = os.path.join(moved_dir, "sample.jpg")
        assert any(os.path.abspath(p) == os.path.abspath(expected) for p in detected), (
            f"Expected initial scan detection for {expected}, got: {detected}"
        )

    if owned_app:
        app.quit()

def _test_folder_watcher_file_changed_requeues_only_on_signature_change() -> None:
    import os
    import tempfile

    app, owned_app = _ensure_qt_app("watch fileChanged signature test")
    if app is None:
        return

    from ..core.folder_watcher import FolderWatcher

    watcher = FolderWatcher(debounce_ms=10)
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_watch_changed_") as td:
            sample = os.path.join(td, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"seed")

            watcher._track_known_file(sample)
            initial_signature = watcher._file_signatures.get(sample)
            assert initial_signature is not None

            watcher._on_file_changed(sample)
            assert sample not in watcher._pending_files

            with open(sample, "ab") as f:
                f.write(b"-updated")

            watcher._on_file_changed(sample)
            assert sample in watcher._pending_files
            changed_signature = watcher._file_signatures.get(sample)
            assert changed_signature is not None
            assert changed_signature != initial_signature

            watcher._pending_files.clear()
            watcher._on_file_changed(sample)
            assert sample not in watcher._pending_files
    finally:
        watcher.deleteLater()
        if owned_app:
            app.quit()

def _test_watch_max_wait_roundtrip() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch max wait test: {e}")
        return

    from ..core.folder_watcher import AutoProcessor
    from ..core.settings_model import AppSettings
    from ..i18n.catalog import t
    from ..ui.widgets.settings import SettingsPanel

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    panel = SettingsPanel(AppSettings())
    panel.watch_max_wait_spin.setValue(47.5)
    built = panel._build_settings()
    assert abs(float(built.watch_mode.max_wait_seconds) - 47.5) < 1e-6

    panel.settings = built
    rebuilt = panel._build_settings()
    assert abs(float(rebuilt.watch_mode.max_wait_seconds) - 47.5) < 1e-6

    auto = AutoProcessor(max_wait_seconds=rebuilt.watch_mode.max_wait_seconds)
    assert abs(float(auto._max_wait_s) - 47.5) < 1e-6
    assert hasattr(auto._queue, "popleft"), "Watch queue must support O(1) front pop"

    panel.deleteLater()
    auto.stop()
    auto.deleteLater()
    if owned_app:
        app.quit()

def _test_watch_callback_runs_on_background_worker() -> None:
    import os
    import tempfile
    import threading
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch worker thread test: {e}")
        return

    from ..core.folder_watcher import AutoProcessor

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    auto = None
    try:
        main_thread_id = threading.get_ident()
        state = {"done": False, "callback_thread": None}

        with tempfile.TemporaryDirectory(prefix="photocropper_watch_worker_") as td:
            watch_root = os.path.join(td, "watch")
            output_root = os.path.join(td, "out")
            os.makedirs(watch_root, exist_ok=True)
            os.makedirs(output_root, exist_ok=True)

            sample = os.path.join(watch_root, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"watch-worker")

            def callback(input_path: str, output_path: str):
                assert os.path.exists(input_path)
                assert os.path.isdir(output_path)
                state["callback_thread"] = threading.get_ident()
                return {"success": True, "status": "success", "message": "ok"}

            auto = AutoProcessor(
                watch_path=watch_root,
                output_path=output_root,
                debounce_ms=10,
                process_callback=callback,
            )
            auto._stable_window_s = 0.0
            auto._retry_interval_ms = 10
            auto.processing_completed_detailed.connect(
                lambda *_args: state.__setitem__("done", True)
            )

            assert auto.start()
            auto._on_new_file(sample)

            deadline = time.time() + 3.0
            while time.time() < deadline and not state["done"]:
                app.processEvents()
                time.sleep(0.01)

            assert state["done"], "Expected watch callback to finish"
            assert state["callback_thread"] is not None
            assert state["callback_thread"] != main_thread_id
    finally:
        if auto is not None:
            auto.stop()
            auto.deleteLater()
        if owned_app:
            app.quit()

def _test_watch_readiness_is_owned_by_auto_processor() -> None:
    import os
    import tempfile
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"WARN: PyQt6 unavailable for watch readiness ownership test: {e}")
        return

    from ..core.folder_watcher import AutoProcessor

    app = QApplication.instance()
    owned_app = False
    if app is None:
        app = QApplication([])
        owned_app = True

    auto = None
    try:
        state = {"done": False, "callback_calls": 0, "readiness_checks": 0}

        with tempfile.TemporaryDirectory(prefix="photocropper_watch_ready_") as td:
            watch_root = os.path.join(td, "watch")
            output_root = os.path.join(td, "out")
            os.makedirs(watch_root, exist_ok=True)
            os.makedirs(output_root, exist_ok=True)

            sample = os.path.join(watch_root, "sample.jpg")
            with open(sample, "wb") as f:
                f.write(b"watch-ready")

            def callback(_input_path: str, _output_path: str):
                state["callback_calls"] += 1
                return {"success": True, "status": "success", "message": "ok"}

            auto = AutoProcessor(
                watch_path=watch_root,
                output_path=output_root,
                debounce_ms=10,
                process_callback=callback,
            )
            auto._stable_window_s = 0.0
            auto._retry_interval_ms = 10

            def fake_check(filepath: str):
                assert os.path.abspath(filepath) == os.path.abspath(sample)
                state["readiness_checks"] += 1
                if state["readiness_checks"] < 3:
                    return False, False, "not yet stable"
                return True, False, "ready"

            auto._check_file_ready = fake_check
            auto.processing_completed_detailed.connect(
                lambda *_args: state.__setitem__("done", True)
            )

            assert auto.start()
            auto._on_new_file(sample)

            deadline = time.time() + 3.0
            while time.time() < deadline and not state["done"]:
                app.processEvents()
                time.sleep(0.01)

            assert state["done"], "Expected watch processing to complete"
            assert state["callback_calls"] == 1
            assert state["readiness_checks"] >= 3
    finally:
        if auto is not None:
            auto.stop()
            auto.deleteLater()
        if owned_app:
            app.quit()

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

def _test_folder_watcher_recursive_excluded_roots() -> None:
    import os
    import tempfile

    app, owned_app = _ensure_qt_app("folder watcher exclusion test")
    if app is None:
        return

    from ..core.folder_watcher import FolderWatcher
    from ..utils.file_helpers import is_path_within, normalize_path

    with tempfile.TemporaryDirectory(prefix="photocropper_watch_exclude_") as td:
        root = os.path.join(td, "input")
        output = os.path.join(root, "output_cropped")
        keep = os.path.join(root, "keep")
        os.makedirs(output, exist_ok=True)
        os.makedirs(keep, exist_ok=True)
        with open(os.path.join(output, "out.jpg"), "wb") as handle:
            handle.write(b"x")
        with open(os.path.join(keep, "in.jpg"), "wb") as handle:
            handle.write(b"x")

        watcher = FolderWatcher(root, recursive=True, excluded_roots=[output])
        try:
            assert watcher.start(root)
            watched = {normalize_path(path) for path in watcher.get_watched_directories()}
            assert normalize_path(output) not in watched
            assert all(
                not is_path_within(output, path)
                for path in getattr(watcher, "_known_files", set())
            )
        finally:
            watcher.stop()
            watcher.deleteLater()
            if owned_app:
                app.quit()

__all__ = [
    "_test_watch_mode_coordinator_invalid_input",
    "_test_watch_mode_coordinator_recursive_output_guard",
    "_test_watch_mode_processing_disables_failed_file_move",
    "_test_watch_process_single_preserves_stop_request",
    "_test_recursive_watch_new_subdir_initial_scan",
    "_test_folder_watcher_file_changed_requeues_only_on_signature_change",
    "_test_watch_max_wait_roundtrip",
    "_test_watch_callback_runs_on_background_worker",
    "_test_watch_readiness_is_owned_by_auto_processor",
    "_test_watch_actions_block_while_batch_or_manual_running",
    "_test_batch_actions_block_when_watch_running",
    "_test_scheduler_once_preserves_task_until_started",
    "_test_scheduler_once_skip_keeps_next_run_due",
    "_test_scheduled_batch_uses_task_paths",
    "_test_folder_watcher_recursive_excluded_roots",
]
