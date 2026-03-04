#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preview/manual-contour UI action coordinator."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

import numpy as np

from ...core.image import PreviewProcessResult
from ...core.manual_extract import (
    denormalize_contour_points,
    normalize_contour_points,
    scale_contour_to_preview,
)
from ...utils.file_helpers import get_image_files

if TYPE_CHECKING:
    from .window import MainWindow


class PreviewActions:
    """Encapsulate preview request/apply flow for MainWindow."""

    def __init__(self, window: "MainWindow"):
        self.window = window

    def request_preview(self) -> None:
        self.window._preview_timer.start(200)

    def resolve_preview_path(self) -> Optional[str]:
        w = self.window
        if w._current_image_path and os.path.exists(w._current_image_path):
            return w._current_image_path

        input_path = w.input_path_edit.text()
        if input_path and os.path.isdir(input_path):
            files = get_image_files(input_path)
            if files:
                w._current_image_path = files[0]
                return w._current_image_path
        return None

    def update_image_info_badge(self, image_path: str) -> None:
        w = self.window
        try:
            info = w.image_processor.get_image_info(image_path)
            if info:
                width, height, _ = info
                file_size_kb = os.path.getsize(image_path) / 1024
                if file_size_kb >= 1024:
                    size_str = f"{file_size_kb / 1024:.1f} MB"
                else:
                    size_str = f"{file_size_kb:.0f} KB"
                w.image_info_badge.setText(f"📷 {width}×{height}px | {size_str}")
                return
        except Exception:
            pass
        w.image_info_badge.setText("이미지: -")

    def on_preview_contour_edited(self, contour_points) -> None:
        w = self.window
        if w._last_original is None:
            return
        try:
            points = np.array(contour_points, dtype=np.float32).reshape((-1, 2))
        except Exception:
            return
        if len(points) != 4:
            return

        w._last_detected_contour = points.copy()
        current_path = w._current_image_path
        if current_path:
            normalized = normalize_contour_points(
                points,
                w._last_original.shape if w._last_original is not None else None,
            )
            if normalized is not None:
                w._batch_contours_norm[current_path] = normalized
                w._batch_contours_edited.add(current_path)
                w._update_batch_edit_controls()

        try:
            from ...core.advanced import AdvancedImageProcessor

            processor = AdvancedImageProcessor()
            result = processor.correct_perspective(w._last_original, points)
            if result.success and result.image is not None:
                w.preview_widget.set_processed_image(result.image)
                w._last_processed = result.image.copy()
                w.status_label.setText("외곽선 수동 편집 반영됨")
            else:
                w.status_label.setText("외곽선 편집 반영 실패")
        except Exception as exc:
            w.status_label.setText(f"외곽선 편집 오류: {exc}")

    def do_preview(self) -> None:
        w = self.window
        image_path = self.resolve_preview_path()
        if not image_path:
            return

        w._preview_request_id += 1
        request_id = w._preview_request_id
        w._latest_preview_request_id = request_id
        w._preview_request_paths[request_id] = image_path
        if len(w._preview_request_paths) > 50:
            old_keys = sorted(w._preview_request_paths.keys())[:-50]
            for key in old_keys:
                w._preview_request_paths.pop(key, None)

        w.status_label.setText(f"미리보기 처리 중: {os.path.basename(image_path)}")
        self.update_image_info_badge(image_path)
        w.preview_process_requested.emit(
            request_id,
            image_path,
            w._preview_settings_revision,
            w._preview_settings_snapshot,
        )

    def on_preview_ready(
        self,
        request_id: int,
        preview_result: object,
    ) -> None:
        w = self.window
        preview_path = w._preview_request_paths.pop(request_id, None)
        if request_id != w._latest_preview_request_id:
            return
        if request_id == w._applied_preview_request_id:
            return

        if preview_result is None:
            w.status_label.setText("미리보기 실패: 결과 없음")
            return
        if not isinstance(preview_result, PreviewProcessResult):
            w.status_label.setText("미리보기 실패: 결과 형식 오류")
            return

        preview_contour = None
        if preview_result.original_preview is not None:
            auto_contour = scale_contour_to_preview(
                preview_result.original_preview,
                preview_result.crop_result,
            )
            saved_norm = w._batch_contours_norm.get(preview_path) if preview_path else None
            if saved_norm is not None:
                preview_contour = denormalize_contour_points(
                    saved_norm,
                    preview_result.original_preview.shape,
                )
            else:
                preview_contour = auto_contour
                if preview_path and auto_contour is not None:
                    norm = normalize_contour_points(
                        auto_contour,
                        preview_result.original_preview.shape,
                    )
                    if norm is not None:
                        w._batch_contours_norm[preview_path] = norm

            w.preview_widget.set_original_image(
                preview_result.original_preview,
                preview_result.overlay_preview,
                preview_contour,
            )
            w.histogram_widget.set_image(preview_result.original_preview)
            w._last_original = preview_result.original_preview
            if preview_path:
                w._current_image_path = preview_path

        crop_result = preview_result.crop_result
        w._last_detected_contour = (
            preview_contour.copy() if preview_contour is not None else None
        )
        if crop_result.success and crop_result.image is not None:
            w.preview_widget.set_processed_image(crop_result.image)
            w._last_processed = crop_result.image
            stage = crop_result.detection_stage.value if crop_result.detection_stage else "Unknown"
            w.status_label.setText(f"미리보기 성공 ({stage})")
        else:
            w.preview_widget.set_processed_image(None)
            w._last_processed = None
            w.status_label.setText(f"미리보기 실패: {crop_result.message}")

        w._applied_preview_request_id = request_id
        w._update_batch_edit_controls()

    def on_preview_failed(self, request_id: int, message: str) -> None:
        w = self.window
        w._preview_request_paths.pop(request_id, None)
        if request_id != w._latest_preview_request_id:
            return
        w.preview_widget.set_processed_image(None)
        w._last_processed = None
        w._last_detected_contour = None
        w.status_label.setText(f"미리보기 오류: {message}")
        w._update_batch_edit_controls()
