#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""CLI execution/exit-code self-tests."""

from __future__ import annotations

from .helpers import _SignalRecorder, _ensure_qt_app

def _test_cli_cancel_exit_code_130() -> None:
    import os
    import tempfile
    from unittest.mock import patch

    from .. import cli as cli_mod
    from ..core import batch as batch_mod

    class FakeProgress:
        processed = 0
        success = 0
        partial_success = 0
        failed = 0
        skipped = 0
        is_cancelled = True

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, on_log=None, **_kwargs):
            self._on_log = on_log

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return True

        def request_stop(self):
            return None

        def wait_for_completion(self, timeout=None):
            return True

        @property
        def progress(self):
            return self._progress

    def _raise_keyboard_interrupt(_seconds):
        raise KeyboardInterrupt()

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_cancel_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir])
        with patch.object(batch_mod, "BatchProcessor", FakeProcessor), patch.object(
            cli_mod.time, "sleep", _raise_keyboard_interrupt
        ):
            code = cli_mod.process_batch(args)
        assert code == 130


def _test_cli_cancel_with_failed_still_returns_130() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stdout
    from unittest.mock import patch

    from .. import cli as cli_mod
    from ..core import batch as batch_mod

    class FakeProgress:
        processed = 3
        success = 1
        partial_success = 0
        failed = 2
        skipped = 0
        is_cancelled = True

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, **_kwargs):
            return None

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return True

        def request_stop(self):
            return None

        def wait_for_completion(self, timeout=None):
            return True

        @property
        def progress(self):
            return self._progress

    def _raise_keyboard_interrupt(_seconds):
        raise KeyboardInterrupt()

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_cancel_fail_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir])
        buffer = io.StringIO()
        with patch.object(batch_mod, "BatchProcessor", FakeProcessor), patch.object(
            cli_mod.time, "sleep", _raise_keyboard_interrupt
        ), redirect_stdout(buffer):
            code = cli_mod.process_batch(args)
        assert code == 130
        assert "failed=2" in buffer.getvalue()


def _test_cli_partial_exit_code_rules() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stdout
    from unittest.mock import patch

    from .. import cli as cli_mod
    from ..core import batch as batch_mod

    class FakeProgress:
        processed = 1
        success = 0
        partial_success = 1
        failed = 0
        skipped = 0
        is_cancelled = False

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, on_log=None, **_kwargs):
            self._on_log = on_log

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return False

        @property
        def progress(self):
            return self._progress

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_partial_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir])
        buffer = io.StringIO()
        with patch.object(batch_mod, "BatchProcessor", FakeProcessor), redirect_stdout(
            buffer
        ):
            code = cli_mod.process_batch(args)
        assert code == 0
        assert "partial_success=1" in buffer.getvalue()

        strict_args = parser.parse_args(
            ["-i", in_dir, "-o", out_dir, "--strict-partial"]
        )
        with patch.object(batch_mod, "BatchProcessor", FakeProcessor):
            assert cli_mod.process_batch(strict_args) == 1


def _test_batch_fatal_error_and_cli_exit_code() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stderr
    from unittest.mock import patch

    from .. import cli as cli_mod
    from ..core import batch as batch_mod
    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_batch_fatal_") as td:
        input_dir = os.path.join(td, "in")
        output_file = os.path.join(td, "out_file")
        os.makedirs(input_dir, exist_ok=True)
        with open(os.path.join(input_dir, "sample.jpg"), "wb") as handle:
            handle.write(b"placeholder")
        with open(output_file, "wb") as handle:
            handle.write(b"not a directory")

        processor = BatchProcessor(AppSettings())
        assert processor.start_async(input_dir, output_file, ["sample.jpg"]) is True
        assert processor.wait_for_completion(timeout=5.0) is True
        assert processor.progress.fatal_error is True
        assert "출력 폴더 생성 실패" in processor.progress.fatal_message

    class FakeProgress:
        processed = 0
        success = 0
        partial_success = 0
        failed = 0
        skipped = 0
        is_cancelled = True
        fatal_error = True
        fatal_message = "fatal"

    class FakeProcessor:
        def __init__(self, _settings):
            self._progress = FakeProgress()

        def set_callbacks(self, **_kwargs):
            return None

        def start_async(self, _input, _output):
            return True

        @property
        def is_running(self):
            return False

        @property
        def progress(self):
            return self._progress

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_fatal_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir])
        error_buffer = io.StringIO()
        with patch.object(batch_mod, "BatchProcessor", FakeProcessor), redirect_stderr(
            error_buffer
        ):
            code = cli_mod.process_batch(args)
        assert code == 1
        assert "ERROR: fatal" in error_buffer.getvalue()


def _test_library_repository_singleton_reset() -> None:
    import os
    import tempfile

    from ..core.library.repository import (
        get_library_repository,
        reset_library_repository_for_tests,
    )
    from ..core.library.sqlite_store import LibrarySqliteStore

    with tempfile.TemporaryDirectory(prefix="photocropper_repo_reset_") as td:
        db_a = os.path.join(td, "a.db")
        db_b = os.path.join(td, "b.db")
        os.environ["PHOTOCROPPER_LIBRARY_DB"] = db_a
        reset_library_repository_for_tests()
        repo_a = get_library_repository()
        assert repo_a.db_path == os.path.abspath(db_a)

        os.environ["PHOTOCROPPER_LIBRARY_DB"] = db_b
        reset_library_repository_for_tests()
        repo_b = get_library_repository()
        assert repo_b.db_path == os.path.abspath(db_b)
        assert repo_a is not repo_b
    os.environ.pop("PHOTOCROPPER_LIBRARY_DB", None)
    reset_library_repository_for_tests()


def _test_ui_batch_completion_finalizes_in_background_and_clears_manual_state() -> None:
    import time
    from types import SimpleNamespace

    from ..core.batch import BatchProgress
    from ..core.settings_model import AppSettings
    from ..ui.main.actions.batch import BatchActions

    class FakeSignal:
        def __init__(self) -> None:
            self.values = []

        def emit(self, value):
            self.values.append(value)

    class FakeJobOrchestrator:
        def __init__(self) -> None:
            self.calls = []

        def finalize_job(self, **kwargs):
            time.sleep(0.2)
            self.calls.append(kwargs)

    final_signal = FakeSignal()
    orchestrator = FakeJobOrchestrator()
    settings = AppSettings()
    settings.notification.enabled = False
    settings.ui.open_output_on_complete = False
    state = SimpleNamespace(
        settings=settings,
        active_job_id=42,
        active_job_kind="manual_extract",
        active_recipe_name="recipe",
        manual_extract_running=True,
        manual_extract_thread=object(),
        manual_extract_stop_event=SimpleNamespace(clear=lambda: None),
        failed_boundary_files=[],
    )
    refs = SimpleNamespace(progress_dialog=None, status_label=None)
    services = SimpleNamespace(
        host_window=SimpleNamespace(management_task_finished=final_signal),
        job_orchestrator=orchestrator,
    )
    actions = BatchActions(
        state=state,
        refs=refs,
        services=services,
        signals=SimpleNamespace(),
    )
    actions.collect_boundary_failed_files = lambda _results: []
    actions.update_batch_edit_controls = lambda: None

    started = time.monotonic()
    actions.on_batch_complete(BatchProgress(total=1, processed=1, success=1), [])
    elapsed = time.monotonic() - started
    assert elapsed < 0.15
    assert state.manual_extract_running is False
    assert state.manual_extract_thread is None
    assert state.active_job_id is None
    assert state.active_job_kind == ""

    deadline = time.time() + 2.0
    while not final_signal.values and time.time() < deadline:
        time.sleep(0.02)
    assert final_signal.values == ["batch_finalize"]
    assert len(orchestrator.calls) == 1


def _test_cli_recursive_output_guard() -> None:
    import io
    import os
    import tempfile
    from contextlib import redirect_stderr

    from .. import cli as cli_mod

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_guard_") as td:
        in_dir = os.path.join(td, "input")
        out_dir = os.path.join(in_dir, "output_cropped")
        os.makedirs(out_dir, exist_ok=True)

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir, "--recursive"])
        error_buffer = io.StringIO()
        with redirect_stderr(error_buffer):
            code = cli_mod.process_batch(args)
        assert code == 2
        assert "output directory inside the input directory" in error_buffer.getvalue()


def _test_batch_actions_recursive_output_guard() -> None:
    import os
    import tempfile
    from types import SimpleNamespace

    app, owned_app = _ensure_qt_app("batch action recursive output guard test")
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
    settings = AppSettings()
    settings.file_management.recursive_search = True
    services = SimpleNamespace(
        host_window=host_window,
        batch_session=FakeBatchSession(),
        watch_mode_coordinator=SimpleNamespace(is_active=False),
    )
    state = SimpleNamespace(
        settings=settings,
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
    original_question = QMessageBox.question
    original_warning = QMessageBox.warning
    QMessageBox.question = lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes
    QMessageBox.warning = lambda *_args, **_kwargs: warnings.append((_args, _kwargs))
    try:
        with tempfile.TemporaryDirectory(prefix="photocropper_batch_guard_") as td:
            input_dir = os.path.join(td, "input")
            output_dir = os.path.join(input_dir, "output_cropped")
            os.makedirs(output_dir, exist_ok=True)
            refs.input_path_edit.setText(input_dir)
            refs.output_path_edit.setText(output_dir)

            actions.start_processing()
            actions.retry_failed_files()

            assert len(warnings) == 2
            assert services.batch_session.create_calls == 0
            expected_message = t(
                "validation.recursive_output_guard",
                input=input_dir,
                output=output_dir,
            )
            assert all(args[2] == expected_message for args, _kwargs in warnings)
    finally:
        QMessageBox.question = original_question
        QMessageBox.warning = original_warning
        host_window.deleteLater()
        refs.input_path_edit.deleteLater()
        refs.output_path_edit.deleteLater()
        if owned_app:
            app.quit()


def _test_management_preflight_file_batch_guard() -> None:
    import os
    import tempfile

    from ..ui.main.services.batch_flow import BatchRuntimeFlow

    with tempfile.TemporaryDirectory(prefix="photocropper_preflight_") as td:
        input_dir = os.path.join(td, "input")
        output_dir = os.path.join(input_dir, "output_cropped")
        os.makedirs(input_dir, exist_ok=True)
        source = os.path.join(input_dir, "source.jpg")
        with open(source, "wb") as f:
            f.write(b"not a real image but present")

        flow = BatchRuntimeFlow()
        blocked = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=output_dir,
            files=[source],
            recursive=True,
            failed_folder_name="_failed",
        )
        assert blocked.ok is False
        allowed = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=os.path.join(td, "out"),
            files=[source],
            recursive=True,
            failed_folder_name="_failed",
        )
        assert allowed.ok is True
        assert allowed.files == (source,)
        missing = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=os.path.join(td, "out2"),
            files=[os.path.join(input_dir, "missing.jpg")],
            recursive=False,
            failed_folder_name="_failed",
        )
        assert missing.ok is False
        mixed = flow.resolve_file_batch_paths(
            input_path=input_dir,
            output_path=os.path.join(td, "out3"),
            files=[source, os.path.join(input_dir, "missing.jpg")],
            recursive=False,
            failed_folder_name="_failed",
        )
        assert mixed.ok is False
