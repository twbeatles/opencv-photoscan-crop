#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Management-page runtime behavior for MainWindow."""

from __future__ import annotations

import logging
import os
import threading
from typing import cast

from PyQt6.QtCore import QTimer

from ...core.batch import FileResult
from ...i18n.catalog import t
from ..widgets.toast_notification import ToastManager

logger = logging.getLogger(__name__)


def _management_job_label(job_kind: str) -> str:
    text = str(job_kind or "").strip()
    if not text:
        return "-"
    return t(f"management.job.kind.{text}", default=text)


class ManagementRuntimeMixin:
    """Operations used by management pages and watch-result recording."""

    def refresh_management_views(self) -> None:
        current_key = ""
        if self.refs.shell_nav is not None:
            keys = list(self.refs.management_pages.keys())
            row = self.refs.shell_nav.currentRow()
            if 0 <= row < len(keys):
                current_key = keys[row]
        pages = (
            [self.refs.management_pages[current_key]]
            if current_key in self.refs.management_pages
            else list(self.refs.management_pages.values())
        )
        for page in pages:
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:
                    logger.debug("Management page refresh failed", exc_info=True)

    def run_review_reprocess(self, review_id: int) -> None:
        if self.services.review_service is None or self.services.query_service is None:
            return
        job_id = self.services.review_service.enqueue_reprocess(review_id)
        if not job_id:
            ToastManager.warning(t("management.window.review_reprocess.create_failed"))
            return
        job = self.services.query_service.get_job(job_id)
        if job is None:
            ToastManager.warning(t("management.window.review_reprocess.job_missing"))
            return
        source_path = str(job.get("input_path", "") or "")
        if not source_path:
            ToastManager.warning(t("management.window.review_reprocess.source_missing"))
            return
        input_root = os.path.dirname(source_path) or source_path
        output_path = str(job.get("output_path", "") or "")
        if not output_path:
            output_path = os.path.join(input_root, "output_cropped")
        started = self.batch_actions.start_processing_with_files(
            job_kind=str(job.get("job_kind", "") or "review_reprocess"),
            input_path=input_root,
            output_path=output_path,
            files=[source_path],
            tracked_job_id=job_id,
        )
        if not started:
            ToastManager.warning(t("management.window.review_reprocess.start_failed"))
            return
        self.refresh_management_views()
    def run_job_rerun(self, job_id: int, *, failed_only: bool = False) -> None:
        if self.services.job_orchestrator is None:
            return
        spec = self.services.job_orchestrator.prepare_job_rerun(job_id, failed_only=failed_only)
        if spec is None:
            ToastManager.warning(t("management.window.rerun.job_missing"))
            return
        origin_job_kind = str(spec.get("origin_job_kind", "") or "")
        source_paths = list(spec.get("source_paths", []) or [])
        input_path = str(spec.get("input_path", "") or "")
        if origin_job_kind.startswith("maintenance_") and not source_paths:
            self.run_maintenance_job(origin_job_kind)
            return
        if not source_paths and input_path and os.path.isfile(input_path):
            source_paths = [input_path]
        if not source_paths:
            ToastManager.warning(t("management.window.rerun.source_missing"))
            return
        output_path = str(spec.get("output_path", "") or "")
        if not output_path:
            output_path = os.path.join(
                os.path.dirname(source_paths[0]) or os.getcwd(),
                "output_cropped",
            )
        started = self.batch_actions.start_processing_with_files(
            job_kind=str(spec.get("job_kind", "") or "batch_rerun"),
            input_path=input_path or os.path.dirname(source_paths[0]),
            output_path=output_path,
            files=source_paths,
            tracked_job_id=int(spec.get("job_id", 0) or 0),
        )
        if not started:
            ToastManager.warning(t("management.window.rerun.start_failed"))
            return
        self.refresh_management_views()

    def show_review_page_for_job(self, job_id: int) -> None:
        review_page = self.refs.management_pages.get("review")
        focus = getattr(review_page, "focus_job", None)
        if callable(focus):
            focus(int(job_id))
        if self.refs.shell_nav is not None:
            self.refs.shell_nav.setCurrentRow(2)

    def _set_management_page_busy(self, page_key: str, busy: bool) -> None:
        page = self.refs.management_pages.get(page_key)
        set_busy = getattr(page, "set_busy", None)
        if callable(set_busy):
            try:
                set_busy(bool(busy))
            except Exception:
                logger.debug("Failed to update management page busy state", exc_info=True)

    def run_library_import_job(self, folder: str, recursive: bool) -> None:
        if self.services.job_orchestrator is None:
            return
        self._set_management_page_busy("library", True)

        def worker() -> None:
            orchestrator = self.services.job_orchestrator
            if orchestrator is None:
                self.management_task_finished.emit("maintenance_library_import:failed")
                return
            try:
                orchestrator.run_maintenance_job(
                    "maintenance_library_import",
                    input_path=folder,
                    recursive=recursive,
                )
                self.management_task_finished.emit("maintenance_library_import")
            except Exception:
                logger.debug("Library import job failed", exc_info=True)
                self.management_task_finished.emit("maintenance_library_import:failed")

        threading.Thread(target=worker, daemon=True).start()
        ToastManager.info(
            t("management.window.maintenance.started", task=_management_job_label("maintenance_library_import"))
        )

    def run_maintenance_job(self, job_kind: str) -> None:
        if self.services.job_orchestrator is None:
            return
        if job_kind in ("maintenance_exact_duplicates", "maintenance_near_duplicates"):
            self._set_management_page_busy("duplicates", True)

        def worker() -> None:
            orchestrator = self.services.job_orchestrator
            if orchestrator is None:
                self.management_task_finished.emit(f"{job_kind}:failed")
                return
            try:
                orchestrator.run_maintenance_job(job_kind)
                self.management_task_finished.emit(job_kind)
            except Exception:
                logger.debug("Maintenance job failed", exc_info=True)
                self.management_task_finished.emit(f"{job_kind}:failed")

        threading.Thread(target=worker, daemon=True).start()
        ToastManager.info(
            t("management.window.maintenance.started", task=_management_job_label(job_kind))
        )

    def _on_watch_result(self, source_path: str, output_path: str, result: object) -> None:
        if self.services.job_orchestrator is None:
            return
        try:
            self.services.job_orchestrator.record_watch_file(
                source_path=source_path,
                output_path=output_path,
                result=cast(FileResult, result),
                settings=self.state.settings,
                recipe_name=self.state.active_recipe_name,
            )
        except Exception:
            logger.debug("Failed to record watch result", exc_info=True)
        QTimer.singleShot(0, self.refresh_management_views)

    def _on_management_task_finished(self, job_kind: str) -> None:
        if str(job_kind or "").startswith("maintenance_library_import"):
            self._set_management_page_busy("library", False)
        if str(job_kind or "").startswith(("maintenance_exact_duplicates", "maintenance_near_duplicates")):
            self._set_management_page_busy("duplicates", False)
        self.refresh_management_views()
        failed = str(job_kind or "").endswith(":failed")
        normalized = str(job_kind or "")
        if failed:
            normalized = normalized[:-7]
        message_key = (
            "management.window.maintenance.failed"
            if failed
            else "management.window.maintenance.complete"
        )
        toast = ToastManager.warning if failed else ToastManager.success
        toast(t(message_key, task=_management_job_label(normalized)))
