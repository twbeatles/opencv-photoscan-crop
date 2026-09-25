#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Watch mode self-tests (facade): compatibility facade re-exporting the split modules."""

from __future__ import annotations

from .watch_coordinator import (
    _test_watch_mode_coordinator_invalid_input,
    _test_watch_mode_coordinator_recursive_output_guard,
    _test_watch_process_single_preserves_stop_request,
    _test_watch_mode_processing_disables_failed_file_move,
    _test_recursive_watch_new_subdir_initial_scan,
    _test_folder_watcher_file_changed_requeues_only_on_signature_change,
    _test_watch_max_wait_roundtrip,
    _test_watch_callback_runs_on_background_worker,
    _test_watch_readiness_is_owned_by_auto_processor,
    _test_folder_watcher_recursive_excluded_roots,
)
from .watch_guards_scheduler import (
    _test_watch_actions_block_while_batch_or_manual_running,
    _test_batch_actions_block_when_watch_running,
    _test_scheduler_once_preserves_task_until_started,
    _test_scheduler_once_skip_keeps_next_run_due,
    _test_scheduled_batch_uses_task_paths,
)

__all__ = [
    "_test_watch_mode_coordinator_invalid_input",
    "_test_watch_mode_coordinator_recursive_output_guard",
    "_test_watch_process_single_preserves_stop_request",
    "_test_watch_mode_processing_disables_failed_file_move",
    "_test_recursive_watch_new_subdir_initial_scan",
    "_test_folder_watcher_file_changed_requeues_only_on_signature_change",
    "_test_watch_max_wait_roundtrip",
    "_test_watch_callback_runs_on_background_worker",
    "_test_watch_readiness_is_owned_by_auto_processor",
    "_test_folder_watcher_recursive_excluded_roots",
    "_test_watch_actions_block_while_batch_or_manual_running",
    "_test_batch_actions_block_when_watch_running",
    "_test_scheduler_once_preserves_task_until_started",
    "_test_scheduler_once_skip_keeps_next_run_due",
    "_test_scheduled_batch_uses_task_paths",
]
