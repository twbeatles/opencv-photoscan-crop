#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch/manual-extract UI action coordinator."""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING, List

import numpy as np
from PyQt6.QtWidgets import QMessageBox

from ..widgets.progress_dialog import ProgressDialog
from ..widgets.toast_notification import ToastManager
from ...core.batch import BatchProgress, BatchSessionService
from ...core.manual_extract import (
    ManualExtractSessionRunner,
    collect_boundary_failed_files,
)
from ...utils.file_helpers import get_image_files, open_file_explorer, validate_directory

if TYPE_CHECKING:
    from .window import MainWindow


logger = logging.getLogger(__name__)


class BatchActions:
    """Encapsulate batch processing and manual extract flows for MainWindow."""

    def __init__(self, window: "MainWindow"):
        self.window = window
        self._batch_session = BatchSessionService()
        self._manual_runner = ManualExtractSessionRunner()

    def cleanup(self) -> None:
        self._batch_session.cleanup()
        self.window.batch_processor = None

    def update_settings(self, settings) -> None:
        processor = self._batch_session.processor
        if processor is not None:
            processor.update_settings(settings)

    def _create_progress_dialog(self, output_path: str) -> None:
        w = self.window
        if w.progress_dialog is not None:
            try:
                w.progress_dialog.close()
            except Exception:
                pass
            w.progress_dialog = None

        w.progress_dialog = ProgressDialog(w)
        w.progress_dialog.cancel_requested.connect(w._cancel_processing)
        w.progress_dialog.open_output_requested.connect(w._open_output_folder)
        w.progress_dialog.set_output_path(output_path)
        w.progress_dialog.finished.connect(w._on_progress_dialog_finished)
        w.progress_dialog.show()

    def start_processing(self) -> None:
        w = self.window
        if w._manual_extract_running:
            QMessageBox.warning(
                w,
                "경고",
                "편집 저장 추출이 진행 중입니다. 먼저 해당 작업을 취소하거나 완료하세요.",
            )
            return

        input_path = w.input_path_edit.text()
        output_path = w.output_path_edit.text()

        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(w, "경고", f"입력 폴더 오류: {error}")
            return

        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            w.output_path_edit.setText(output_path)

        recursive = bool(
            getattr(w._settings.file_management, "recursive_search", False)
        )
        files = get_image_files(input_path, recursive=recursive)
        if not files:
            QMessageBox.information(w, "알림", "처리할 이미지 파일이 없습니다.")
            return

        w.batch_processor = self._batch_session.create_processor(
            settings=w._settings,
            on_progress=w._emit_batch_progress,
            on_log=w._emit_batch_log,
            on_complete=w._emit_batch_complete,
        )
        self._create_progress_dialog(output_path)
        assert w.batch_processor is not None
        w.batch_processor.start_async(input_path, output_path, files)
        w._update_batch_edit_controls()

    def cancel_processing(self) -> None:
        w = self.window
        if w._manual_extract_running:
            w._manual_extract_stop_event.set()
            w.status_label.setText("편집 저장 추출 중단 요청됨")
            return
        self._batch_session.request_stop()

    def on_batch_progress(self, progress: BatchProgress) -> None:
        w = self.window
        if w.progress_dialog is not None and w.progress_dialog.isVisible():
            w.progress_dialog.update_progress(progress)

    def on_batch_log(self, message: str, level: str) -> None:
        w = self.window
        if w.progress_dialog is not None and w.progress_dialog.isVisible():
            w.progress_dialog.log_message(message, level)

    def on_progress_dialog_finished(self, dialog_obj) -> None:
        w = self.window
        if w.progress_dialog is dialog_obj:
            w.progress_dialog = None
        try:
            dialog_obj.deleteLater()
        except Exception:
            pass

    def collect_boundary_failed_files(self, results: list) -> List[str]:
        w = self.window
        input_root = w.input_path_edit.text().strip()
        recursive = bool(getattr(w._settings.file_management, "recursive_search", False))
        batch_failed = self._batch_session.failed_files
        return collect_boundary_failed_files(
            results=results or [],
            input_root=input_root,
            image_list=w._image_list or [],
            batch_failed_entries=batch_failed,
            recursive_search=recursive,
            get_image_files_fn=get_image_files,
            logger=logger,
        )

    def on_batch_complete(self, progress: BatchProgress, results: list) -> None:
        w = self.window

        if w.progress_dialog is not None and w.progress_dialog.isVisible():
            w.progress_dialog.update_progress(progress)
            w.progress_dialog.log_message(
                f"처리 완료: {progress.success}개 성공, {progress.failed}개 실패, {progress.skipped}개 건너뜀",
                "success" if progress.failed == 0 else "warning",
            )

        if progress.is_cancelled:
            w.status_label.setText(
                f"작업 취소됨: {progress.success}개 성공, {progress.failed}개 실패"
            )
            ToastManager.info("⏹️ 작업이 취소되었습니다")
        else:
            w.status_label.setText(
                f"완료: {progress.success}개 성공, {progress.failed}개 실패"
            )
            if progress.failed == 0:
                ToastManager.success(f"✅ {progress.success}개 파일 처리 완료!")
            else:
                ToastManager.warning(
                    f"⚠️ {progress.success}개 성공, {progress.failed}개 실패"
                )

        boundary_failed_files = self.collect_boundary_failed_files(results)
        w._failed_boundary_files = boundary_failed_files
        if boundary_failed_files and not progress.is_cancelled:
            failed_count = len(boundary_failed_files)
            reply = QMessageBox.question(
                w,
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
                w._load_failed_boundary_images_for_edit()

        if w._settings.notification.enabled and not progress.is_cancelled:
            try:
                from ...utils.system_notification import (
                    NotificationType,
                    get_system_notification,
                )

                notifier = get_system_notification()
                if progress.failed == 0:
                    notifier.notify(
                        "배치 처리 완료",
                        f"{progress.success}개 파일 처리 완료!",
                        NotificationType.SUCCESS,
                    )
                else:
                    notifier.notify(
                        "배치 처리 완료",
                        f"{progress.success}개 성공, {progress.failed}개 실패",
                        NotificationType.WARNING,
                    )
            except Exception as exc:
                logger.warning("System notification error: %s", exc)

        if w._settings.ui.open_output_on_complete and not progress.is_cancelled:
            output_path = w.output_path_edit.text()
            if output_path and os.path.isdir(output_path):
                open_file_explorer(output_path)

        w._update_batch_edit_controls()

    def retry_failed_files(self) -> None:
        w = self.window
        failed = self._batch_session.failed_files
        if not failed:
            QMessageBox.information(w, "알림", "재처리할 실패 파일이 없습니다.")
            return

        reply = QMessageBox.question(
            w,
            "재처리",
            f"{len(failed)}개의 실패한 파일을 재처리하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        input_path = w.input_path_edit.text()
        output_path = w.output_path_edit.text()
        w.batch_processor = self._batch_session.create_processor(
            settings=w._settings,
            on_progress=w._emit_batch_progress,
            on_log=w._emit_batch_log,
            on_complete=w._emit_batch_complete,
        )
        self._create_progress_dialog(output_path)
        assert w.batch_processor is not None
        w.batch_processor.start_async(input_path, output_path, failed)
        w._update_batch_edit_controls()

    def load_failed_boundary_images_for_edit(self) -> None:
        w = self.window
        if w._manual_extract_running or (
            w.batch_processor and w.batch_processor.is_running
        ):
            QMessageBox.warning(w, "경고", "처리 작업이 진행 중입니다. 완료/취소 후 실행하세요.")
            return

        if not w._failed_boundary_files:
            QMessageBox.information(w, "알림", "수동 보정할 경계 실패 파일이 없습니다.")
            return

        files = [path for path in w._failed_boundary_files if os.path.exists(path)]
        if not files:
            w._failed_boundary_files = []
            QMessageBox.information(
                w,
                "알림",
                "경계 실패 파일을 찾지 못했습니다. 폴더 경로를 다시 확인해주세요.",
            )
            w._update_batch_edit_controls()
            return

        w._image_list = files
        w._current_image_index = 0
        w._current_image_path = files[0]
        w.status_label.setText(
            f"경계 실패 파일 수동 보정 모드: {len(files)}개 (4점 클릭 또는 점 드래그)"
        )
        ToastManager.info(f"경계 실패 {len(files)}개 파일만 불러왔습니다")
        w._request_preview()
        w._update_navigation_status()
        w._update_batch_edit_controls()

    def save_batch_edited_crops(self) -> None:
        w = self.window
        if w._manual_extract_running:
            QMessageBox.information(w, "알림", "편집 저장 추출이 이미 진행 중입니다.")
            return
        if w.batch_processor and w.batch_processor.is_running:
            QMessageBox.warning(w, "경고", "기존 배치 작업이 진행 중입니다.")
            return

        input_path = w.input_path_edit.text()
        valid, error = validate_directory(input_path)
        if not valid:
            QMessageBox.warning(w, "경고", f"입력 폴더 오류: {error}")
            return

        if not w._image_list:
            w._update_image_list()
        if not w._image_list:
            QMessageBox.information(w, "알림", "추출할 이미지가 없습니다.")
            return

        output_path = w.output_path_edit.text().strip()
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
            w.output_path_edit.setText(output_path)
        os.makedirs(output_path, exist_ok=True)

        edited_count = sum(
            1 for path in w._image_list if path in w._batch_contours_edited
        )
        reply = QMessageBox.question(
            w,
            "편집 저장 추출",
            (
                f"총 {len(w._image_list)}장 추출을 시작합니다.\n"
                f"수정된 외곽선 {edited_count}장, 나머지는 자동 탐색 결과를 사용합니다.\n\n"
                "진행하시겠습니까?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        contours_snapshot = {}
        for path, points in w._batch_contours_norm.items():
            if points is None:
                continue
            try:
                contours_snapshot[path] = (
                    np.array(points, dtype=np.float32).reshape((-1, 2)).copy()
                )
            except Exception:
                continue

        settings_snapshot = w._settings.to_dict()
        files_snapshot = list(w._image_list)

        w._manual_extract_stop_event.clear()
        w._manual_extract_running = True
        w._update_batch_edit_controls()

        self._create_progress_dialog(output_path)

        w._manual_extract_thread = threading.Thread(
            target=w._run_manual_extract_worker,
            args=(
                input_path,
                output_path,
                files_snapshot,
                contours_snapshot,
                settings_snapshot,
            ),
            daemon=True,
        )
        w._manual_extract_thread.start()

    def run_manual_extract_worker(
        self,
        output_path: str,
        files: list,
        contours_norm: dict,
        settings_snapshot: dict,
    ) -> None:
        w = self.window
        try:
            self._manual_runner.run(
                output_path=output_path,
                files=files,
                contours_norm=contours_norm,
                settings_snapshot=settings_snapshot,
                stop_event=w._manual_extract_stop_event,
                on_progress=w.batch_progress_received.emit,
                on_log=w.batch_log_received.emit,
                on_complete=w.batch_complete_received.emit,
            )
        finally:
            w._manual_extract_running = False
            w._manual_extract_thread = None
            w._manual_extract_stop_event.clear()
