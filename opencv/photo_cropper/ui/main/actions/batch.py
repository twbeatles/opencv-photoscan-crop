#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch and manual-extract actions."""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

import numpy as np
from PyQt6.QtWidgets import QMessageBox

from ....core.batch import BatchProgress
from ....core.settings_model import AppSettings
from ....i18n.catalog import t
from ....core.manual_extract import (
    ManualExtractSessionRunner,
    collect_boundary_failed_files,
)
from ....utils.file_helpers import (
    build_recursive_excluded_roots,
    get_image_files,
    open_file_explorer,
    validate_directory,
)
from ...widgets.progress_dialog import ProgressDialog
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowSignals, WindowState
from ..services import BatchRuntimeFlow, UiMessageFactory

logger = logging.getLogger(__name__)


class BatchActions:
    """Encapsulate batch processing and manual extract flows."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
        signals: WindowSignals,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self.signals = signals
        self._manual_runner = ManualExtractSessionRunner()
        self.runtime_flow = BatchRuntimeFlow()
        self.messages = UiMessageFactory()
        self._request_preview: Optional[Callable[[], None]] = None
        self._update_navigation_status: Optional[Callable[[], None]] = None
        self._update_image_list: Optional[Callable[[], None]] = None
        self._open_output_folder: Optional[Callable[[], None]] = None

    def bind(
        self,
        *,
        request_preview: Callable[[], None],
        update_navigation_status: Callable[[], None],
        update_image_list: Callable[[], None],
        open_output_folder: Callable[[], None],
    ) -> None:
        self._request_preview = request_preview
        self._update_navigation_status = update_navigation_status
        self._update_image_list = update_image_list
        self._open_output_folder = open_output_folder

    @property
    def batch_processor(self):
        return self.services.batch_session.processor

    def cleanup(self) -> None:
        self.services.batch_session.cleanup()

    def update_settings(self) -> None:
        processor = self.services.batch_session.processor
        if processor is not None:
            processor.update_settings(self.state.settings)

    def _is_batch_running(self) -> bool:
        processor = self.batch_processor
        return bool(processor and processor.is_running)

    def _is_watch_running(self) -> bool:
        return bool(self.services.watch_mode_coordinator.is_active)

    def _show_batch_running_warning(self) -> None:
        QMessageBox.warning(
            self.services.host_window,
            self.messages.warning_title,
            t("batch.running_warning"),
        )

    def _show_watch_running_warning(self) -> None:
        QMessageBox.warning(
            self.services.host_window,
            self.messages.warning_title,
            t("batch.watch_running_warning"),
        )

    def _validate_runtime_settings(self) -> bool:
        result = self.runtime_flow.validate_settings(self.state.settings)
        if result.ok:
            return True
        QMessageBox.warning(
            self.services.host_window,
            result.title,
            result.message,
        )
        return False

    def _resolve_batch_io_paths(
        self,
        *,
        input_path_override: Optional[str] = None,
        output_path_override: Optional[str] = None,
        update_output_edit: bool = True,
    ) -> Optional[tuple[str, str]]:
        input_edit = self.refs.input_path_edit
        output_edit = self.refs.output_path_edit
        if (
            input_path_override is None
            and output_path_override is None
            and (input_edit is None or output_edit is None)
        ):
            return None

        if input_path_override is None:
            if input_edit is None:
                return None
            input_path = input_edit.text().strip()
        else:
            input_path = str(input_path_override).strip()

        if output_path_override is None:
            if output_edit is None:
                return None
            output_path = output_edit.text().strip()
        else:
            output_path = str(output_path_override).strip()
        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
        resolved = self.runtime_flow.resolve_io_paths(
            input_path=input_path,
            output_path=output_path,
            recursive=recursive,
            failed_folder_name=self.state.settings.file_management.failed_folder_name,
        )
        if not resolved.ok:
            QMessageBox.warning(
                self.services.host_window,
                resolved.title,
                resolved.message,
            )
            return None
        if update_output_edit and output_edit is not None and resolved.output_path != output_path:
            output_edit.setText(resolved.output_path)
        return resolved.input_path, resolved.output_path

    def update_batch_edit_controls(self) -> None:
        total = len(self.state.image_list) if self.state.image_list else 0
        current = (
            self.state.current_image_index + 1
            if total > 0 and self.state.current_image_index >= 0
            else 0
        )
        image_set = set(self.state.image_list or [])
        edited = sum(1 for path in self.state.batch_contours_edited if path in image_set)
        failed = len(self.state.failed_boundary_files)
        if self.refs.batch_edit_status_label is not None:
            self.refs.batch_edit_status_label.setText(
                t(
                    "central.batch_status",
                    current=current,
                    total=total,
                    edited=edited,
                    failed=failed,
                )
            )

        busy = bool(
            self.state.manual_extract_running
            or (self.batch_processor and self.batch_processor.is_running)
        )
        has_files = total > 0
        has_failed_targets = failed > 0
        if self.refs.batch_prev_btn is not None:
            self.refs.batch_prev_btn.setEnabled(has_files and total > 1 and not busy)
        if self.refs.batch_next_btn is not None:
            self.refs.batch_next_btn.setEnabled(has_files and total > 1 and not busy)
        if self.refs.batch_save_edits_btn is not None:
            self.refs.batch_save_edits_btn.setEnabled(has_files and not busy)
        if self.refs.batch_failed_btn is not None:
            self.refs.batch_failed_btn.setEnabled(has_failed_targets and not busy)
        if self.refs.batch_load_btn is not None:
            self.refs.batch_load_btn.setEnabled(not busy)

    def _create_progress_dialog(self, output_path: str) -> None:
        if self.refs.progress_dialog is not None:
            try:
                self.refs.progress_dialog.close()
            except Exception:
                pass
            self.refs.progress_dialog = None

        dialog = ProgressDialog(self.services.host_window)
        dialog.cancel_requested.connect(self.cancel_processing)
        if self._open_output_folder is not None:
            dialog.open_output_requested.connect(self._open_output_folder)
        dialog.set_output_path(output_path)
        dialog.finished.connect(
            lambda _result, dialog_obj=dialog: self.on_progress_dialog_finished(dialog_obj)
        )
        dialog.show()
        self.refs.progress_dialog = dialog

    def _start_job_tracking(self, job_kind: str, input_path: str, output_path: str) -> None:
        self.state.active_job_id = None
        self.state.active_job_kind = job_kind
        job_orchestrator = getattr(self.services, "job_orchestrator", None)
        if job_orchestrator is None:
            return
        try:
            self.state.active_job_id = job_orchestrator.create_job(
                job_kind=job_kind,
                input_path=input_path,
                output_path=output_path,
                recipe_name=self.state.active_recipe_name,
            )
        except Exception:
            logger.debug("Failed to create tracked job", exc_info=True)

    def start_processing_with_files(
        self,
        *,
        job_kind: str,
        input_path: str,
        output_path: str,
        files: list[str],
        tracked_job_id: Optional[int] = None,
    ) -> bool:
        if self.state.manual_extract_running:
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("batch.manual_extract_running"),
            )
            return False
        if self._is_batch_running():
            self._show_batch_running_warning()
            return False
        if self._is_watch_running():
            self._show_watch_running_warning()
            return False
        if not self._validate_runtime_settings():
            return False
        if not files:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.no_files"),
            )
            return False

        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
        resolved = self.runtime_flow.resolve_file_batch_paths(
            input_path=input_path,
            output_path=output_path,
            files=files,
            recursive=recursive,
            failed_folder_name=self.state.settings.file_management.failed_folder_name,
        )
        if not resolved.ok:
            QMessageBox.warning(
                self.services.host_window,
                resolved.title,
                resolved.message,
            )
            if tracked_job_id is not None:
                job_orchestrator = getattr(self.services, "job_orchestrator", None)
                if job_orchestrator is not None:
                    try:
                        job_orchestrator.repository.finalize_job(
                            int(tracked_job_id),
                            status="failed",
                            total_items=len(files),
                            processed_items=0,
                            success_count=0,
                            partial_count=0,
                            failed_count=len(files),
                            skipped_count=0,
                            summary={"error": resolved.message, "preflight_failed": True},
                        )
                    except Exception:
                        logger.debug("Failed to finalize preflight-failed job", exc_info=True)
            return False
        input_path = resolved.input_path
        output_path = resolved.output_path
        files = list(resolved.files or ())

        try:
            self.services.batch_session.create_processor(
                settings=self.state.settings,
                on_progress=self.signals.batch_progress_received.emit,
                on_log=self.signals.batch_log_received.emit,
                on_complete=self.signals.batch_complete_received.emit,
            )
        except RuntimeError as exc:
            QMessageBox.warning(self.services.host_window, self.messages.warning_title, str(exc))
            return False

        self.state.active_job_kind = job_kind
        self.state.active_job_id = int(tracked_job_id) if tracked_job_id is not None else None
        if tracked_job_id is None:
            self._start_job_tracking(job_kind, input_path, output_path)
        self._create_progress_dialog(output_path)
        processor = self.batch_processor
        assert processor is not None
        if not processor.start_async(input_path, output_path, files):
            self.state.active_job_id = None
            self.state.active_job_kind = ""
            return False
        self.update_batch_edit_controls()
        return True

    def start_processing(
        self,
        checked: bool = False,
        *,
        input_path_override: Optional[str] = None,
        output_path_override: Optional[str] = None,
        job_kind: str = "batch",
    ) -> bool:
        if self.state.manual_extract_running:
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("batch.manual_extract_running"),
            )
            return False

        if self._is_batch_running():
            self._show_batch_running_warning()
            return False

        if self._is_watch_running():
            self._show_watch_running_warning()
            return False
        if not self._validate_runtime_settings():
            return False

        paths = self._resolve_batch_io_paths(
            input_path_override=input_path_override,
            output_path_override=output_path_override,
            update_output_edit=input_path_override is None and output_path_override is None,
        )
        if paths is None:
            return False
        input_path, output_path = paths

        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
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
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.no_files"),
            )
            return False

        return self.start_processing_with_files(
            job_kind=job_kind,
            input_path=input_path,
            output_path=output_path,
            files=files,
        )

    def cancel_processing(self) -> None:
        if self.state.manual_extract_running:
            self.state.manual_extract_stop_event.set()
            if self.refs.status_label is not None:
                self.refs.status_label.setText(t("batch.manual_extract.stop_requested"))
            return
        self.services.batch_session.request_stop()

    def on_batch_progress(self, progress: BatchProgress) -> None:
        if self.refs.progress_dialog is not None and self.refs.progress_dialog.isVisible():
            self.refs.progress_dialog.update_progress(progress)

    def on_batch_log(self, message: str, level: str) -> None:
        if self.refs.progress_dialog is not None and self.refs.progress_dialog.isVisible():
            self.refs.progress_dialog.log_message(message, level)

    def on_progress_dialog_finished(self, dialog_obj) -> None:
        if self.refs.progress_dialog is dialog_obj:
            self.refs.progress_dialog = None
        try:
            dialog_obj.deleteLater()
        except Exception:
            pass

    def collect_boundary_failed_files(self, results: list) -> list[str]:
        input_root = self.refs.input_path_edit.text().strip() if self.refs.input_path_edit else ""
        output_path = self.refs.output_path_edit.text().strip() if self.refs.output_path_edit else ""
        if input_root and not output_path:
            output_path = os.path.join(input_root, "output_cropped")
        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
        excluded_roots = (
            build_recursive_excluded_roots(
                input_root,
                output_path,
                failed_folder_name=self.state.settings.file_management.failed_folder_name,
            )
            if recursive and input_root
            else None
        )
        batch_failed = self.services.batch_session.failed_files
        return collect_boundary_failed_files(
            results=results or [],
            input_root=input_root,
            image_list=self.state.image_list or [],
            batch_failed_entries=batch_failed,
            recursive_search=recursive,
            get_image_files_fn=(
                lambda root, recursive=False: get_image_files(
                    root,
                    recursive=recursive,
                    excluded_roots=excluded_roots if recursive else None,
                )
            ),
            logger=logger,
        )

    def on_batch_complete(self, progress: BatchProgress, results: list) -> None:
        job_orchestrator = getattr(self.services, "job_orchestrator", None)
        active_job_id = self.state.active_job_id
        active_job_kind = self.state.active_job_kind or "batch"
        active_recipe_name = self.state.active_recipe_name
        was_manual_extract = active_job_kind == "manual_extract"
        if active_job_id is not None and job_orchestrator is not None:
            progress_snapshot = BatchProgress(**progress.__dict__)
            results_snapshot = list(results or [])
            settings_snapshot = AppSettings.from_dict(self.state.settings.to_dict())
            finalize_signal = getattr(self.services.host_window, "management_task_finished", None)

            def finalize_worker() -> None:
                failed = False
                try:
                    job_orchestrator.finalize_job(
                        job_id=int(active_job_id),
                        progress=progress_snapshot,
                        results=results_snapshot,
                        settings=settings_snapshot,
                        recipe_name=active_recipe_name,
                        job_kind=active_job_kind,
                    )
                except Exception:
                    failed = True
                    logger.debug("Failed to finalize tracked job", exc_info=True)
                emit = getattr(finalize_signal, "emit", None)
                if callable(emit):
                    emit("batch_finalize:failed" if failed else "batch_finalize")

            threading.Thread(
                target=finalize_worker,
                name="photocropper-finalize-job",
                daemon=True,
            ).start()

        self.state.active_job_id = None
        self.state.active_job_kind = ""

        if was_manual_extract:
            self.state.manual_extract_running = False
            self.state.manual_extract_thread = None
            self.state.manual_extract_stop_event.clear()

        partial_count = int(getattr(progress, "partial_success", 0) or 0)
        full_success_count = int(progress.success)
        summary_message = self.messages.batch_summary(
            full_success_count=full_success_count,
            partial_count=partial_count,
            failed_count=progress.failed,
            skipped_count=progress.skipped,
        )
        summary_level = (
            "warning" if progress.failed > 0 else "partial" if partial_count > 0 else "success"
        )

        if self.refs.progress_dialog is not None and self.refs.progress_dialog.isVisible():
            self.refs.progress_dialog.update_progress(progress)
            self.refs.progress_dialog.log_message(
                summary_message,
                summary_level,
            )

        if self.refs.status_label is not None:
            if progress.is_cancelled:
                self.refs.status_label.setText(
                    self.messages.batch_cancelled_summary(
                        full_success_count=full_success_count,
                        partial_count=partial_count,
                        failed_count=progress.failed,
                    )
                )
                ToastManager.info(t("batch.cancelled.toast"))
            else:
                self.refs.status_label.setText(summary_message)
                if progress.failed == 0 and partial_count == 0:
                    ToastManager.success(
                        t("batch.complete.toast_success", count=full_success_count)
                    )
                else:
                    ToastManager.warning(
                        t(
                            "batch.complete.toast_warning",
                            success=full_success_count,
                            partial=partial_count,
                            failed=progress.failed,
                        )
                    )

        self.state.failed_boundary_files = self.collect_boundary_failed_files(results)
        if self.state.failed_boundary_files and not progress.is_cancelled:
            failed_count = len(self.state.failed_boundary_files)
            reply = QMessageBox.question(
                self.services.host_window,
                t("batch.failed_boundary.title"),
                t("batch.failed_boundary.body", count=failed_count),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.load_failed_boundary_images_for_edit()

        if self.state.settings.notification.enabled and not progress.is_cancelled:
            try:
                from ....utils.system_notification import (
                    NotificationType,
                    get_system_notification,
                )

                notifier = get_system_notification()
                if progress.failed == 0 and partial_count == 0:
                    notifier.notify(
                        t("batch.notification.title"),
                        t("batch.notification.body_success", count=full_success_count),
                        NotificationType.SUCCESS,
                    )
                else:
                    notifier.notify(
                        t("batch.notification.title"),
                        t(
                            "batch.notification.body_warning",
                            success=full_success_count,
                            partial=partial_count,
                            failed=progress.failed,
                        ),
                        NotificationType.WARNING,
                    )
            except Exception as exc:
                logger.warning("System notification error: %s", exc)

        if self.state.settings.ui.open_output_on_complete and not progress.is_cancelled:
            output_path = self.refs.output_path_edit.text() if self.refs.output_path_edit else ""
            if output_path and os.path.isdir(output_path):
                open_file_explorer(output_path)

        self.update_batch_edit_controls()
        refresh_views = getattr(self.services.host_window, "refresh_management_views", None)
        if callable(refresh_views):
            refresh_views()

    def retry_failed_files(self) -> None:
        if self._is_batch_running():
            self._show_batch_running_warning()
            return

        if self._is_watch_running():
            self._show_watch_running_warning()
            return
        if not self._validate_runtime_settings():
            return

        failed = self.services.batch_session.failed_files
        if not failed:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.retry.none"),
            )
            return

        reply = QMessageBox.question(
            self.services.host_window,
            t("batch.retry.title"),
            t("batch.retry.body", count=len(failed)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        paths = self._resolve_batch_io_paths()
        if paths is None:
            return
        input_path, output_path = paths

        self.start_processing_with_files(
            job_kind="batch_retry",
            input_path=input_path,
            output_path=output_path,
            files=list(failed),
        )

    def load_batch_images_for_edit(self) -> None:
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("validation.input_dir_error", error=error),
            )
            return

        if self.refs.output_path_edit is not None and not self.refs.output_path_edit.text():
            self.refs.output_path_edit.setText(os.path.join(input_path, "output_cropped"))

        if self._update_image_list is not None:
            self._update_image_list()
        if not self.state.image_list:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.load_edit.none"),
            )
            self.update_batch_edit_controls()
            return

        self.state.current_image_index = 0
        self.state.current_image_path = self.state.image_list[0]
        if self._request_preview is not None:
            self._request_preview()
        if self._update_navigation_status is not None:
            self._update_navigation_status()
        self.update_batch_edit_controls()

    def load_failed_boundary_images_for_edit(self) -> None:
        if self.state.manual_extract_running or (
            self.batch_processor and self.batch_processor.is_running
        ):
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("batch.failed_edit.busy"),
            )
            return

        # Review queue = boundary failures + low-confidence previews (if any).
        review_paths: list[str] = list(self.state.failed_boundary_files or [])
        for path in getattr(self.state, "low_confidence_files", None) or []:
            if path and path not in review_paths:
                review_paths.append(path)

        if not review_paths:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.failed_edit.none"),
            )
            return

        files = [path for path in review_paths if os.path.exists(path)]
        if not files:
            self.state.failed_boundary_files = []
            self.state.low_confidence_files = []
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.failed_edit.missing"),
            )
            self.update_batch_edit_controls()
            return

        self.state.image_list = files
        self.state.current_image_index = 0
        self.state.current_image_path = files[0]
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                t("batch.failed_edit.loaded_status", count=len(files))
            )
        ToastManager.info(t("batch.failed_edit.toast", count=len(files)))
        if self._request_preview is not None:
            self._request_preview()
        if self._update_navigation_status is not None:
            self._update_navigation_status()
        self.update_batch_edit_controls()

    def save_batch_edited_crops(self) -> None:
        if self.state.manual_extract_running:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.manual_extract.already_running"),
            )
            return
        if self.batch_processor and self.batch_processor.is_running:
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("batch.manual_extract.batch_running"),
            )
            return
        if not self._validate_runtime_settings():
            return

        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(
                self.services.host_window,
                self.messages.warning_title,
                t("validation.input_dir_error", error=error),
            )
            return

        if not self.state.image_list and self._update_image_list is not None:
            self._update_image_list()
        if not self.state.image_list:
            QMessageBox.information(
                self.services.host_window,
                self.messages.info_title,
                t("batch.manual_extract.no_images"),
            )
            return

        output_path = self.refs.output_path_edit.text().strip() if self.refs.output_path_edit else ""
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            if self.refs.output_path_edit is not None:
                self.refs.output_path_edit.setText(output_path)
        os.makedirs(output_path, exist_ok=True)

        edited_count = sum(
            1 for path in self.state.image_list if path in self.state.batch_contours_edited
        )
        reply = QMessageBox.question(
            self.services.host_window,
            t("batch.manual_extract.title"),
            t(
                "batch.manual_extract.confirm",
                total=len(self.state.image_list),
                edited=edited_count,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        contours_snapshot = {}
        for path, points in self.state.batch_contours_norm.items():
            if points is None:
                continue
            try:
                contours_snapshot[path] = (
                    np.array(points, dtype=np.float32).reshape((-1, 2)).copy()
                )
            except Exception:
                continue

        settings_snapshot = self.state.settings.to_dict()
        files_snapshot = list(self.state.image_list)

        self.state.manual_extract_stop_event.clear()
        self.state.manual_extract_running = True
        self._start_job_tracking("manual_extract", input_path, output_path)
        self.update_batch_edit_controls()
        self._create_progress_dialog(output_path)

        self.state.manual_extract_thread = threading.Thread(
            target=self.run_manual_extract_worker,
            args=(input_path, output_path, files_snapshot, contours_snapshot, settings_snapshot),
            daemon=True,
        )
        self.state.manual_extract_thread.start()

    def run_manual_extract_worker(
        self,
        input_path: str,
        output_path: str,
        files: list,
        contours_norm: dict,
        settings_snapshot: dict,
    ) -> None:
        try:
            self._manual_runner.run(
                input_root=input_path,
                output_path=output_path,
                files=files,
                contours_norm=contours_norm,
                settings_snapshot=settings_snapshot,
                stop_event=self.state.manual_extract_stop_event,
                on_progress=self.signals.batch_progress_received.emit,
                on_log=self.signals.batch_log_received.emit,
                on_complete=self.signals.batch_complete_received.emit,
            )
        except Exception as exc:
            message = f"수동 추출 오류: {exc}"
            logger.error(message)
            self.signals.batch_log_received.emit(message, "error")
            self.signals.batch_complete_received.emit(
                BatchProgress(
                    total=len(files),
                    processed=0,
                    is_running=False,
                    fatal_error=True,
                    fatal_message=message,
                ),
                [],
            )
