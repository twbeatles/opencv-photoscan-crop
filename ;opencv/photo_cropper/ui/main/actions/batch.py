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

from ....core.batch import BatchProgress, ProcessStatus
from ....core.manual_extract import (
    ManualExtractSessionRunner,
    collect_boundary_failed_files,
)
from ....utils.file_helpers import get_image_files, open_file_explorer, validate_directory
from ...widgets.progress_dialog import ProgressDialog
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowSignals, WindowState

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

    @staticmethod
    def _partial_result_count(results: list) -> int:
        return sum(
            1
            for result in (results or [])
            if getattr(result, "status", None) == ProcessStatus.PARTIAL_SUCCESS
        )

    def _is_batch_running(self) -> bool:
        processor = self.batch_processor
        return bool(processor and processor.is_running)

    def _is_watch_running(self) -> bool:
        return bool(self.services.watch_mode_coordinator.is_active)

    def _show_batch_running_warning(self) -> None:
        QMessageBox.warning(
            self.services.host_window,
            "경고",
            "배치 처리가 이미 진행 중입니다. 현재 작업이 끝나거나 취소된 뒤 다시 시도하세요.",
        )

    def _show_watch_running_warning(self) -> None:
        QMessageBox.warning(
            self.services.host_window,
            "경고",
            "폴더 감시 모드가 활성화되어 있습니다. 먼저 중지한 뒤 다시 시도하세요.",
        )

    def _resolve_batch_io_paths(self) -> Optional[tuple[str, str]]:
        input_edit = self.refs.input_path_edit
        output_edit = self.refs.output_path_edit
        if input_edit is None or output_edit is None:
            return None

        input_path = input_edit.text().strip()
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self.services.host_window, "경고", f"입력 폴더 오류: {error}")
            return None

        output_path = output_edit.text().strip()
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            output_edit.setText(output_path)

        try:
            os.makedirs(output_path, exist_ok=True)
        except Exception as exc:
            QMessageBox.warning(
                self.services.host_window,
                "경고",
                f"출력 폴더 오류: {exc}",
            )
            return None

        return input_path, output_path

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
                f"편집 {current}/{total} | 수정 {edited} | 실패 {failed}"
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

    def start_processing(self) -> None:
        if self.state.manual_extract_running:
            QMessageBox.warning(
                self.services.host_window,
                "경고",
                "편집 저장 추출이 진행 중입니다. 먼저 해당 작업을 취소하거나 완료하세요.",
            )
            return

        if self._is_batch_running():
            self._show_batch_running_warning()
            return

        if self._is_watch_running():
            self._show_watch_running_warning()
            return

        paths = self._resolve_batch_io_paths()
        if paths is None:
            return
        input_path, output_path = paths

        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
        files = get_image_files(input_path, recursive=recursive)
        if not files:
            QMessageBox.information(
                self.services.host_window,
                "알림",
                "처리할 이미지 파일이 없습니다.",
            )
            return

        try:
            self.services.batch_session.create_processor(
                settings=self.state.settings,
                on_progress=self.signals.batch_progress_received.emit,
                on_log=self.signals.batch_log_received.emit,
                on_complete=self.signals.batch_complete_received.emit,
            )
        except RuntimeError as exc:
            QMessageBox.warning(self.services.host_window, "경고", str(exc))
            return
        self._create_progress_dialog(output_path)
        processor = self.batch_processor
        assert processor is not None
        processor.start_async(input_path, output_path, files)
        self.update_batch_edit_controls()

    def cancel_processing(self) -> None:
        if self.state.manual_extract_running:
            self.state.manual_extract_stop_event.set()
            if self.refs.status_label is not None:
                self.refs.status_label.setText("편집 저장 추출 중단 요청됨")
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
        recursive = bool(
            getattr(self.state.settings.file_management, "recursive_search", False)
        )
        batch_failed = self.services.batch_session.failed_files
        return collect_boundary_failed_files(
            results=results or [],
            input_root=input_root,
            image_list=self.state.image_list or [],
            batch_failed_entries=batch_failed,
            recursive_search=recursive,
            get_image_files_fn=get_image_files,
            logger=logger,
        )

    def on_batch_complete(self, progress: BatchProgress, results: list) -> None:
        partial_count = self._partial_result_count(results)
        full_success_count = max(int(progress.success) - partial_count, 0)
        summary_message = (
            f"처리 완료: 정상 성공 {full_success_count}개, 부분 성공 {partial_count}개, "
            f"실패 {progress.failed}개, 건너뜀 {progress.skipped}개"
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
                    f"작업 취소됨: 정상 성공 {full_success_count}개, 부분 성공 {partial_count}개, 실패 {progress.failed}개"
                )
                ToastManager.info("⏹️ 작업이 취소되었습니다")
            else:
                self.refs.status_label.setText(summary_message)
                if progress.failed == 0 and partial_count == 0:
                    ToastManager.success(f"✅ {full_success_count}개 파일 처리 완료!")
                else:
                    ToastManager.warning(
                        f"⚠️ 정상 성공 {full_success_count}개, 부분 성공 {partial_count}개, 실패 {progress.failed}개"
                    )

        self.state.failed_boundary_files = self.collect_boundary_failed_files(results)
        if self.state.failed_boundary_files and not progress.is_cancelled:
            failed_count = len(self.state.failed_boundary_files)
            reply = QMessageBox.question(
                self.services.host_window,
                "경계 실패 파일 감지",
                (
                    f"경계 자동 탐지 실패 파일 {failed_count}개가 있습니다.\n"
                    "해당 파일만 따로 불러와 수동으로 경계를 지정할 수 있습니다.\n\n"
                    "지금 실패 파일 수동 보정 모드로 이동하시겠습니까?"
                ),
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
                        "배치 처리 완료",
                        f"{full_success_count}개 파일 처리 완료!",
                        NotificationType.SUCCESS,
                    )
                else:
                    notifier.notify(
                        "배치 처리 완료",
                        (
                            f"정상 성공 {full_success_count}개, 부분 성공 {partial_count}개, "
                            f"실패 {progress.failed}개"
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

    def retry_failed_files(self) -> None:
        if self._is_batch_running():
            self._show_batch_running_warning()
            return

        if self._is_watch_running():
            self._show_watch_running_warning()
            return

        failed = self.services.batch_session.failed_files
        if not failed:
            QMessageBox.information(self.services.host_window, "알림", "재처리할 실패 파일이 없습니다.")
            return

        reply = QMessageBox.question(
            self.services.host_window,
            "재처리",
            f"{len(failed)}개의 실패한 파일을 재처리하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        paths = self._resolve_batch_io_paths()
        if paths is None:
            return
        input_path, output_path = paths

        try:
            self.services.batch_session.create_processor(
                settings=self.state.settings,
                on_progress=self.signals.batch_progress_received.emit,
                on_log=self.signals.batch_log_received.emit,
                on_complete=self.signals.batch_complete_received.emit,
            )
        except RuntimeError as exc:
            QMessageBox.warning(self.services.host_window, "경고", str(exc))
            return
        self._create_progress_dialog(output_path)
        processor = self.batch_processor
        assert processor is not None
        processor.start_async(input_path, output_path, failed)
        self.update_batch_edit_controls()

    def load_batch_images_for_edit(self) -> None:
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self.services.host_window, "경고", f"입력 폴더 오류: {error}")
            return

        if self.refs.output_path_edit is not None and not self.refs.output_path_edit.text():
            self.refs.output_path_edit.setText(os.path.join(input_path, "output_cropped"))

        if self._update_image_list is not None:
            self._update_image_list()
        if not self.state.image_list:
            QMessageBox.information(self.services.host_window, "알림", "불러올 이미지가 없습니다.")
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
            QMessageBox.warning(self.services.host_window, "경고", "처리 작업이 진행 중입니다. 완료/취소 후 실행하세요.")
            return

        if not self.state.failed_boundary_files:
            QMessageBox.information(self.services.host_window, "알림", "수동 보정할 경계 실패 파일이 없습니다.")
            return

        files = [path for path in self.state.failed_boundary_files if os.path.exists(path)]
        if not files:
            self.state.failed_boundary_files = []
            QMessageBox.information(
                self.services.host_window,
                "알림",
                "경계 실패 파일을 찾지 못했습니다. 폴더 경로를 다시 확인해주세요.",
            )
            self.update_batch_edit_controls()
            return

        self.state.image_list = files
        self.state.current_image_index = 0
        self.state.current_image_path = files[0]
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                f"경계 실패 파일 수동 보정 모드: {len(files)}개 (4점 클릭 또는 점 드래그)"
            )
        ToastManager.info(f"경계 실패 {len(files)}개 파일만 불러왔습니다")
        if self._request_preview is not None:
            self._request_preview()
        if self._update_navigation_status is not None:
            self._update_navigation_status()
        self.update_batch_edit_controls()

    def save_batch_edited_crops(self) -> None:
        if self.state.manual_extract_running:
            QMessageBox.information(self.services.host_window, "알림", "편집 저장 추출이 이미 진행 중입니다.")
            return
        if self.batch_processor and self.batch_processor.is_running:
            QMessageBox.warning(self.services.host_window, "경고", "기존 배치 작업이 진행 중입니다.")
            return

        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(self.services.host_window, "경고", f"입력 폴더 오류: {error}")
            return

        if not self.state.image_list and self._update_image_list is not None:
            self._update_image_list()
        if not self.state.image_list:
            QMessageBox.information(self.services.host_window, "알림", "추출할 이미지가 없습니다.")
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
            "편집 저장 추출",
            (
                f"총 {len(self.state.image_list)}장 추출을 시작합니다.\n"
                f"수정된 외곽선 {edited_count}장, 나머지는 자동 탐색 결과를 사용합니다.\n\n"
                "진행하시겠습니까?"
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
        self.update_batch_edit_controls()
        self._create_progress_dialog(output_path)

        self.state.manual_extract_thread = threading.Thread(
            target=self.run_manual_extract_worker,
            args=(output_path, files_snapshot, contours_snapshot, settings_snapshot),
            daemon=True,
        )
        self.state.manual_extract_thread.start()

    def run_manual_extract_worker(
        self,
        output_path: str,
        files: list,
        contours_norm: dict,
        settings_snapshot: dict,
    ) -> None:
        try:
            self._manual_runner.run(
                output_path=output_path,
                files=files,
                contours_norm=contours_norm,
                settings_snapshot=settings_snapshot,
                stop_event=self.state.manual_extract_stop_event,
                on_progress=self.signals.batch_progress_received.emit,
                on_log=self.signals.batch_log_received.emit,
                on_complete=self.signals.batch_complete_received.emit,
            )
        finally:
            self.state.manual_extract_running = False
            self.state.manual_extract_thread = None
            self.state.manual_extract_stop_event.clear()
