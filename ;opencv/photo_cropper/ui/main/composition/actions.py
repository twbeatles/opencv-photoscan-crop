#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Action construction and signal wiring for MainWindow."""

from __future__ import annotations

from ..actions import (
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


def wire_window_actions(window, state, refs, services, signals) -> None:
    self = window
    self.feature_actions = FeatureActions(state, refs, services)
    self.preview_actions = PreviewActions(state, refs, services, signals)
    self.navigation_actions = NavigationActions(state, refs)
    self.dialog_actions = DialogActions(state, refs, services)
    self.batch_actions = BatchActions(state, refs, services, signals)
    self.settings_actions = SettingsActions(state, refs, services)
    self.input_actions = InputActions(state, refs, services)
    self.watch_actions = WatchActions(state, refs, services)
    self.tool_actions = ToolActions(state, refs, services)

    self.preview_actions.bind(
        update_batch_edit_controls=self.batch_actions.update_batch_edit_controls
    )
    self.navigation_actions.bind(
        request_preview=self.preview_actions.request_preview,
        update_batch_edit_controls=self.batch_actions.update_batch_edit_controls,
    )
    self.dialog_actions.bind(
        resolve_preview_path=self.preview_actions.resolve_preview_path,
        update_image_list=self.navigation_actions.update_image_list,
        on_crop_applied=self.feature_actions.on_crop_applied,
    )
    self.batch_actions.bind(
        request_preview=self.preview_actions.request_preview,
        update_navigation_status=self.navigation_actions.update_navigation_status,
        update_image_list=self.navigation_actions.update_image_list,
        open_output_folder=self.input_actions.open_output_folder,
    )
    self.settings_actions.bind(
        reconfigure_scheduler=self.watch_actions.reconfigure_scheduler
    )
    self.watch_actions.bind(start_processing=self.batch_actions.start_processing)
    self.tool_actions.bind(
        request_preview=self.preview_actions.request_preview,
        schedule_auto_save=self.settings_actions.schedule_auto_save,
        sync_current_settings=self.settings_actions.sync_current_settings,
    )
    self.input_actions.bind(
        reconfigure_scheduler=self.watch_actions.reconfigure_scheduler,
        update_image_list=self.navigation_actions.update_image_list,
        update_batch_edit_controls=self.batch_actions.update_batch_edit_controls,
        request_preview=self.preview_actions.request_preview,
        navigate_prev=self.navigation_actions.navigate_prev,
        navigate_next=self.navigation_actions.navigate_next,
        start_processing=self.batch_actions.start_processing,
        rotate_preview=self.tool_actions.rotate_preview,
        show_compare_dialog=self.dialog_actions.show_compare_dialog,
        show_fullscreen=self.feature_actions.show_fullscreen,
        undo=self.feature_actions.undo,
        redo=self.feature_actions.redo,
    )
    self.lifecycle_actions = LifecycleActions(
        state,
        refs,
        services,
        save_window_state=self.settings_actions.save_window_state,
        persist_paths=self.settings_actions.persist_paths,
        batch_cleanup=self.batch_actions.cleanup,
    )

    self.services.scheduler.set_process_callback(
        self.watch_actions.on_scheduled_batch_trigger
    )
    self.services.preview_timer.timeout.connect(self.preview_actions.do_preview)
    self.services.input_path_scan_timer.timeout.connect(
        self.input_actions.flush_input_path_change
    )
    self.batch_progress_received.connect(self.batch_actions.on_batch_progress)
    self.batch_log_received.connect(self.batch_actions.on_batch_log)
    self.batch_complete_received.connect(self.batch_actions.on_batch_complete)
    self.watch_mode_coordinator.processing_started.connect(
        self.watch_actions.on_processing_started
    )
    self.watch_mode_coordinator.processing_completed.connect(
        self.watch_actions.on_watched_file_complete
    )
    self.watch_mode_coordinator.processing_completed_detailed.connect(
        self.watch_actions.on_watched_file_complete_detailed
    )
    self.watch_mode_coordinator.queue_metrics_updated.connect(
        self.watch_actions.on_watch_queue_metrics
    )
    self._scheduler.task_started.connect(self.watch_actions.on_scheduler_task_started)
    self._scheduler.task_completed.connect(
        self.watch_actions.on_scheduler_task_completed
    )
    self.services.preview_worker_host = PreviewWorkerHost(
        services,
        self.preview_process_requested,
        self.preview_actions.on_preview_ready,
        self.preview_actions.on_preview_failed,
    )


__all__ = ["wire_window_actions"]
