#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main window composition root for the Photo Cropper UI."""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow

from ..widgets.toast_notification import ToastManager
from .actions import (
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
from .builders import (
    build_central_widget,
    build_fab,
    build_menu,
    build_statusbar,
    build_toolbar,
)
from .models import WindowRefs, WindowServices, WindowSignals, WindowState
from ...core.batch import BatchProcessor, BatchSessionService, FileResult
from ...core.history_manager import HistoryManager
from ...core.image import ImageProcessor
from ...core.jobs import JobOrchestrator
from ...core.library import (
    DuplicateService,
    LibraryIngestService,
    QueryService,
    ReviewService,
    ThumbnailService,
    get_library_repository,
)
from ...core.recipes import get_recipe_manager
from ...i18n.catalog import get_translator, set_language, t
from ...core.scheduler import Scheduler
from ...core.settings_model import SettingsManager
from ...core.watch_mode import WatchModeCoordinator
from ..widgets.fullscreen_viewer import FullscreenViewerManager

logger = logging.getLogger(__name__)


def _management_job_label(job_kind: str) -> str:
    text = str(job_kind or "").strip()
    if not text:
        return "-"
    return t(f"management.job.kind.{text}", default=text)


class MainWindow(QMainWindow):
    """Thin composition root for the Photo Cropper desktop UI."""

    VERSION = "9.0"
    TITLE = f"📸 사진 자동 자르기 v{VERSION}"
    preview_process_requested = pyqtSignal(int, str, int, object)
    batch_progress_received = pyqtSignal(object)
    batch_log_received = pyqtSignal(str, str)
    batch_complete_received = pyqtSignal(object, object)
    management_task_finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        signals = WindowSignals(
            preview_process_requested=self.preview_process_requested,
            batch_progress_received=self.batch_progress_received,
            batch_log_received=self.batch_log_received,
            batch_complete_received=self.batch_complete_received,
        )
        settings_manager = SettingsManager()
        settings = settings_manager.load()
        set_language(getattr(settings.ui, "language", "ko"))
        library_repository = None
        thumbnail_service = None
        library_ingest_service = None
        query_service = None
        review_service = None
        duplicate_service = None
        recipe_manager = None
        job_orchestrator = None
        try:
            library_repository = get_library_repository()
            thumbnail_service = ThumbnailService()
            duplicate_service = DuplicateService(library_repository)
            job_orchestrator = JobOrchestrator(
                library_repository,
                thumbnail_service=thumbnail_service,
                duplicate_service=duplicate_service,
            )
            library_ingest_service = LibraryIngestService(
                library_repository,
                thumbnail_service=thumbnail_service,
                duplicate_service=duplicate_service,
            )
            query_service = QueryService(library_repository)
            review_service = ReviewService(
                library_repository,
                create_reprocess_job=job_orchestrator.prepare_review_reprocess,
            )
        except Exception as exc:
            logger.warning("Library services unavailable: %s", exc)

        try:
            recipe_manager = get_recipe_manager()
        except Exception as exc:
            logger.warning("Recipe manager unavailable: %s", exc)
            recipe_manager = None

        state = WindowState(
            settings=settings,
            preview_settings_snapshot=settings.to_dict(),
            active_recipe_name=recipe_manager.get_current_recipe_name()
            if recipe_manager is not None
            else "",
        )
        refs = WindowRefs()
        preview_timer = QTimer(self)
        preview_timer.setSingleShot(True)
        input_path_scan_timer = QTimer(self)
        input_path_scan_timer.setSingleShot(True)
        services = WindowServices(
            host_window=self,
            settings_manager=settings_manager,
            image_processor=ImageProcessor(
                settings.algorithm,
                settings.processing,
                settings.advanced,
                settings.performance,
                debug_settings=settings.debug,
            ),
            history_manager=HistoryManager(max_history=50),
            fullscreen_manager=FullscreenViewerManager(),
            watch_mode_coordinator=WatchModeCoordinator(
                settings=settings,
                on_log=signals.batch_log_received.emit,
                parent=self,
            ),
            scheduler=Scheduler(parent=self),
            batch_session=BatchSessionService(),
            preview_timer=preview_timer,
            input_path_scan_timer=input_path_scan_timer,
            library_repository=library_repository,
            thumbnail_service=thumbnail_service,
            library_ingest_service=library_ingest_service,
            query_service=query_service,
            review_service=review_service,
            duplicate_service=duplicate_service,
            recipe_manager=recipe_manager,
            job_orchestrator=job_orchestrator,
        )

        self.state = state
        self.refs = refs
        self.services = services
        self.signals = signals
        self.settings_manager = settings_manager
        self.image_processor = services.image_processor
        self.history_manager = services.history_manager
        self.fullscreen_manager = services.fullscreen_manager
        self.watch_mode_coordinator = services.watch_mode_coordinator
        self._scheduler = services.scheduler
        self._translator = get_translator()
        self.services.watch_mode_coordinator.set_result_callback(self._on_watch_result)
        self.management_task_finished.connect(self._on_management_task_finished)

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

        self._setup_window()
        build_menu(
            self,
            refs,
            settings_actions=self.settings_actions,
            input_actions=self.input_actions,
            preview_actions=self.preview_actions,
            batch_actions=self.batch_actions,
            dialog_actions=self.dialog_actions,
            watch_actions=self.watch_actions,
            tool_actions=self.tool_actions,
        )
        build_toolbar(
            self,
            refs,
            input_actions=self.input_actions,
            preview_actions=self.preview_actions,
            batch_actions=self.batch_actions,
            tool_actions=self.tool_actions,
        )
        build_central_widget(
            self,
            refs,
            state,
            services,
            input_actions=self.input_actions,
            preview_actions=self.preview_actions,
            batch_actions=self.batch_actions,
            navigation_actions=self.navigation_actions,
            settings_actions=self.settings_actions,
        )
        build_statusbar(self, refs)
        build_fab(
            self,
            refs,
            preview_actions=self.preview_actions,
            batch_actions=self.batch_actions,
            tool_actions=self.tool_actions,
            feature_actions=self.feature_actions,
        )

        ToastManager.set_parent(self)
        self.settings_actions.apply_loaded_settings(state.settings)
        self.batch_actions.update_batch_edit_controls()
        self.settings_actions.restore_window_state()
        self.refresh_management_views()
        self.setAcceptDrops(True)
        self._translator.add_language_change_listener(self._on_language_changed)
        self.retranslate_ui()

    @property
    def batch_processor(self) -> Optional[BatchProcessor]:
        return self.services.batch_session.processor

    def _setup_window(self) -> None:
        self.setWindowTitle(t("app.title", version=self.VERSION))
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        screen_obj = QApplication.primaryScreen()
        if screen_obj is not None:
            screen = screen_obj.geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )

    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]) -> None:
        self.input_actions.drag_enter_event(a0)

    def dropEvent(self, a0: Optional[QDropEvent]) -> None:
        self.input_actions.drop_event(a0)

    def keyPressEvent(self, a0: Optional[QKeyEvent]) -> None:
        if self.input_actions.handle_key_press(a0):
            return
        if a0 is not None:
            super().keyPressEvent(a0)

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        try:
            self._translator.remove_language_change_listener(self._on_language_changed)
        except Exception:
            pass
            self.lifecycle_actions.close_event(a0)

    def open_path_in_workbench(self, image_path: str) -> None:
        normalized = os.path.abspath(str(image_path or ""))
        if not normalized or not os.path.exists(normalized):
            return
        parent_dir = os.path.dirname(normalized)
        if self.refs.input_path_edit is not None:
            self.refs.input_path_edit.setText(parent_dir)
        if self.refs.output_path_edit is not None and not self.refs.output_path_edit.text().strip():
            self.refs.output_path_edit.setText(os.path.join(parent_dir, "output_cropped"))
        self.state.current_image_path = normalized
        if self.refs.shell_nav is not None:
            self.refs.shell_nav.setCurrentRow(1)
        self.preview_actions.request_preview()

    def apply_recipe_from_management(self, recipe_name: str) -> None:
        if not recipe_name:
            return
        self.state.active_recipe_name = recipe_name
        self.tool_actions.on_preset_selected(recipe_name)
        self.refresh_management_views()

    def refresh_management_views(self) -> None:
        for page in list(self.refs.management_pages.values()):
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

    def run_maintenance_job(self, job_kind: str) -> None:
        if self.services.job_orchestrator is None:
            return

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
        from typing import cast
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

    def _on_language_changed(self, _language: str) -> None:
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("app.title", version=self.VERSION))

        if self.refs.shell_nav is not None:
            for index, page_key in enumerate(
                (
                    "library",
                    "workbench",
                    "review",
                    "duplicates",
                    "jobs",
                    "collections",
                    "recipes",
                    "settings",
                )
            ):
                item = self.refs.shell_nav.item(index)
                if item is not None:
                    item.setText(t(f"shell.{page_key}", default=page_key.title()))

        menu_titles = {
            "file": t("menu.file"),
            "edit": t("menu.edit"),
            "view": t("menu.view"),
            "tools": t("menu.tools"),
            "tools.ai": t("menu.tools.ai"),
            "tools.profile": t("menu.tools.profile"),
            "help": t("menu.help"),
        }
        for key, text in menu_titles.items():
            menu = self.refs.menus.get(key)
            if menu is not None:
                menu.setTitle(text)

        action_texts = {
            "file.open_input": t("menu.file.open_input"),
            "file.open_output": t("menu.file.open_output"),
            "file.open_image": t("menu.file.open_image"),
            "file.open_output_folder": t("menu.file.open_output_folder"),
            "file.exit": t("menu.file.exit"),
            "edit.reset_settings": t("menu.edit.reset_settings"),
            "tools.preview": t("menu.tools.preview"),
            "tools.retry_failed": t("menu.tools.retry_failed"),
            "tools.refresh": t("menu.tools.refresh"),
            "tools.rotate": t("menu.tools.rotate"),
            "tools.compare": t("menu.tools.compare"),
            "tools.crop_editor": t("menu.tools.crop_editor"),
            "tools.duplicates": t("menu.tools.duplicates"),
            "tools.classification": t("menu.tools.classification"),
            "tools.face_detection": t("menu.tools.face_detection"),
            "tools.smart_enhancement": t("menu.tools.smart_enhancement"),
            "tools.multi_compare": t("menu.tools.multi_compare"),
            "tools.profile_manager": t("menu.tools.profile_manager"),
            "help.help": t("menu.help.help"),
            "help.about": t("menu.help.about"),
        }
        for key, text in action_texts.items():
            action = self.refs.actions.get(key)
            if action is not None:
                action.setText(text)

        for theme_name, action in self.refs.theme_actions.items():
            action.setText(t("menu.view.theme", theme=theme_name.title()))

        watch_action = self.refs.watch_mode_action
        if watch_action is not None:
            watch_action.setText(
                t("menu.tools.watch_stop")
                if watch_action.isChecked()
                else t("menu.tools.watch_mode")
            )

        toolbar_action = self.refs.actions.get("toolbar.open_folder")
        if toolbar_action is not None:
            toolbar_action.setText(t("toolbar.open_folder"))
            toolbar_action.setToolTip(t("toolbar.open_folder.tooltip"))
        toolbar_action = self.refs.actions.get("toolbar.output_folder")
        if toolbar_action is not None:
            toolbar_action.setText(t("toolbar.output_folder"))
            toolbar_action.setToolTip(t("toolbar.output_folder.tooltip"))
        toolbar_action = self.refs.actions.get("toolbar.preview")
        if toolbar_action is not None:
            toolbar_action.setText(t("toolbar.preview"))
            toolbar_action.setToolTip(t("toolbar.preview.tooltip"))
        toolbar_action = self.refs.actions.get("toolbar.rotate")
        if toolbar_action is not None:
            toolbar_action.setText(t("toolbar.rotate"))
            toolbar_action.setToolTip(t("toolbar.rotate.tooltip"))

        label = self.refs.labels.get("toolbar.preset")
        if label is not None:
            label.setText(t("toolbar.preset"))
        if self.refs.preset_combo is not None and hasattr(self.refs.preset_combo, "retranslate_ui"):
            self.refs.preset_combo.retranslate_ui()
        if self.refs.process_btn is not None:
            self.refs.process_btn.setText(t("toolbar.start"))
            self.refs.process_btn.setToolTip(t("toolbar.start.tooltip"))

        central_label = self.refs.labels.get("central.input_label")
        if central_label is not None:
            central_label.setText(t("central.input_folder"))
        central_label = self.refs.labels.get("central.output_label")
        if central_label is not None:
            central_label.setText(t("central.output_folder"))
        if self.refs.input_path_edit is not None:
            self.refs.input_path_edit.setPlaceholderText(t("central.input_placeholder"))
        if self.refs.output_path_edit is not None:
            self.refs.output_path_edit.setPlaceholderText(t("central.output_placeholder"))

        for key, text in (
            ("central.input_browse", t("central.browse")),
            ("central.output_browse", t("central.change")),
            ("central.output_open", t("central.open_output_folder")),
            ("central.batch_load", t("central.load_batch")),
            ("central.batch_failed", t("central.load_failed")),
            ("central.batch_prev", t("central.prev")),
            ("central.batch_next", t("central.next")),
            ("central.batch_save", t("central.save_edits")),
        ):
            button = self.refs.buttons.get(key)
            if button is not None:
                button.setText(text)

        central_hint = self.refs.labels.get("central.drag_hint")
        if central_hint is not None:
            central_hint.setText(t("central.drag_hint"))

        if self.refs.image_info_badge is not None and self.state.current_image_path is None:
            self.refs.image_info_badge.setText(t("status.image_empty"))
        if self.refs.file_count_badge is not None:
            count = len(self.state.image_list or [])
            self.refs.file_count_badge.setText(
                t("status.file_count", count=count) if count else t("status.file_empty")
            )
        if self.refs.status_label is not None and not self.refs.status_label.text().strip():
            self.refs.status_label.setText(f" {t('status.ready')}")
        if self.refs.settings_panel is not None:
            self.refs.settings_panel.retranslate_ui()
        self.batch_actions.update_batch_edit_controls()
        if self.refs.progress_dialog is not None:
            self.refs.progress_dialog.retranslate_ui()
        if self.refs.fab is not None and hasattr(self.refs.fab, "retranslate_ui"):
            self.refs.fab.retranslate_ui()
        if self.fullscreen_manager is not None and hasattr(self.fullscreen_manager, "retranslate_ui"):
            self.fullscreen_manager.retranslate_ui()
        if self.state.multi_compare_window is not None and hasattr(
            self.state.multi_compare_window, "retranslate_ui"
        ):
            self.state.multi_compare_window.retranslate_ui()
        for page in list(self.refs.management_pages.values()):
            if hasattr(page, "retranslate_ui"):
                page.retranslate_ui()
            else:
                refresh = getattr(page, "refresh", None)
                if callable(refresh):
                    refresh()
