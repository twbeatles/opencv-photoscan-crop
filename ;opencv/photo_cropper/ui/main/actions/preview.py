#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preview and manual contour actions."""

from __future__ import annotations

import os
from typing import Callable, Optional

import numpy as np

from ....core.image import PreviewProcessResult
from ....core.manual_extract import (
    denormalize_contour_points,
    normalize_contour_points,
    scale_contour_to_preview,
)
from ....utils.file_helpers import get_image_files
from ..models import WindowRefs, WindowServices, WindowSignals, WindowState


class PreviewActions:
    """Encapsulate preview request/apply flow."""

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
        self._update_batch_edit_controls: Optional[Callable[[], None]] = None

    def bind(self, *, update_batch_edit_controls: Callable[[], None]) -> None:
        self._update_batch_edit_controls = update_batch_edit_controls

    def request_preview(self) -> None:
        if self.services.preview_timer is not None:
            self.services.preview_timer.start(200)

    def resolve_preview_path(self) -> Optional[str]:
        if self.state.current_image_path and os.path.exists(self.state.current_image_path):
            return self.state.current_image_path

        input_edit = self.refs.input_path_edit
        if input_edit is None:
            return None
        input_path = input_edit.text()
        if input_path and os.path.isdir(input_path):
            files = get_image_files(input_path)
            if files:
                self.state.current_image_path = files[0]
                return self.state.current_image_path
        return None

    def update_image_info_badge(self, image_path: str) -> None:
        if self.refs.image_info_badge is None:
            return
        try:
            info = self.services.image_processor.get_image_info(image_path)
            if info:
                width, height, _ = info
                file_size_kb = os.path.getsize(image_path) / 1024
                size_str = (
                    f"{file_size_kb / 1024:.1f} MB"
                    if file_size_kb >= 1024
                    else f"{file_size_kb:.0f} KB"
                )
                self.refs.image_info_badge.setText(f"📷 {width}×{height}px | {size_str}")
                return
        except Exception:
            pass
        self.refs.image_info_badge.setText("이미지: -")

    def scale_contour_to_preview(self, preview_image, crop_result):
        return scale_contour_to_preview(preview_image, crop_result)

    def normalize_contour_points(self, points, image_shape):
        return normalize_contour_points(points, image_shape)

    def denormalize_contour_points(self, normalized_points, image_shape):
        return denormalize_contour_points(normalized_points, image_shape)

    def on_preview_contour_edited(self, contour_points) -> None:
        if self.state.last_original is None:
            return
        try:
            points = np.array(contour_points, dtype=np.float32).reshape((-1, 2))
        except Exception:
            return
        if len(points) != 4:
            return

        self.state.last_detected_contour = points.copy()
        current_path = self.state.current_image_path
        if current_path:
            normalized = normalize_contour_points(
                points,
                self.state.last_original.shape
                if self.state.last_original is not None
                else None,
            )
            if normalized is not None:
                self.state.batch_contours_norm[current_path] = normalized
                self.state.batch_contours_edited.add(current_path)
                if self._update_batch_edit_controls is not None:
                    self._update_batch_edit_controls()

        try:
            from ....core.advanced import AdvancedImageProcessor

            processor = AdvancedImageProcessor()
            result = processor.correct_perspective(self.state.last_original, points)
            if result.success and result.image is not None:
                if self.refs.preview_widget is not None:
                    self.refs.preview_widget.set_processed_image(result.image)
                self.state.last_processed = result.image.copy()
                if self.refs.status_label is not None:
                    self.refs.status_label.setText("외곽선 수동 편집 반영됨")
            else:
                if self.refs.status_label is not None:
                    self.refs.status_label.setText("외곽선 편집 반영 실패")
        except Exception as exc:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(f"외곽선 편집 오류: {exc}")

    def do_preview(self) -> None:
        image_path = self.resolve_preview_path()
        if not image_path:
            return

        self.state.preview_request_id += 1
        request_id = self.state.preview_request_id
        self.state.latest_preview_request_id = request_id
        self.state.preview_request_paths[request_id] = image_path
        if len(self.state.preview_request_paths) > 50:
            old_keys = sorted(self.state.preview_request_paths.keys())[:-50]
            for key in old_keys:
                self.state.preview_request_paths.pop(key, None)

        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                f"미리보기 처리 중: {os.path.basename(image_path)}"
            )
        self.update_image_info_badge(image_path)
        self.signals.preview_process_requested.emit(
            request_id,
            image_path,
            self.state.preview_settings_revision,
            self.state.preview_settings_snapshot,
        )

    def on_preview_ready(self, request_id: int, preview_result: object) -> None:
        preview_path = self.state.preview_request_paths.pop(request_id, None)
        if request_id != self.state.latest_preview_request_id:
            return
        if request_id == self.state.applied_preview_request_id:
            return

        if preview_result is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("미리보기 실패: 결과 없음")
            return
        if not isinstance(preview_result, PreviewProcessResult):
            if self.refs.status_label is not None:
                self.refs.status_label.setText("미리보기 실패: 결과 형식 오류")
            return

        preview_contour = None
        if preview_result.original_preview is not None:
            auto_contour = scale_contour_to_preview(
                preview_result.original_preview,
                preview_result.crop_result,
            )
            saved_norm = (
                self.state.batch_contours_norm.get(preview_path)
                if preview_path
                else None
            )
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
                        self.state.batch_contours_norm[preview_path] = norm

            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_original_image(
                    preview_result.original_preview,
                    preview_result.overlay_preview,
                    preview_contour,
                )
            if self.refs.histogram_widget is not None:
                self.refs.histogram_widget.set_image(preview_result.original_preview)
            self.state.last_original = preview_result.original_preview
            if preview_path:
                self.state.current_image_path = preview_path

        crop_result = preview_result.crop_result
        self.state.last_detected_contour = (
            preview_contour.copy() if preview_contour is not None else None
        )
        if crop_result.success and crop_result.image is not None:
            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_processed_image(crop_result.image)
            self.state.last_processed = crop_result.image
            stage = (
                crop_result.detection_stage.value
                if crop_result.detection_stage
                else "Unknown"
            )
            if self.refs.status_label is not None:
                self.refs.status_label.setText(f"미리보기 성공 ({stage})")
        else:
            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_processed_image(None)
            self.state.last_processed = None
            if self.refs.status_label is not None:
                self.refs.status_label.setText(f"미리보기 실패: {crop_result.message}")

        self.state.applied_preview_request_id = request_id
        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()

    def on_preview_failed(self, request_id: int, message: str) -> None:
        self.state.preview_request_paths.pop(request_id, None)
        if request_id != self.state.latest_preview_request_id:
            return
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_processed_image(None)
        self.state.last_processed = None
        self.state.last_detected_contour = None
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"미리보기 오류: {message}")
        if self._update_batch_edit_controls is not None:
            self._update_batch_edit_controls()
