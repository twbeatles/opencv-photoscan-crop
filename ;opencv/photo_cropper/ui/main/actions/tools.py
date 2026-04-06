#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tool and feature-toggle actions."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtWidgets import QInputDialog, QMessageBox

from ....core.batch_profile_manager import get_batch_profile_manager
from ....core.smart_enhancer import EnhancementPreset, get_smart_enhancer
from ....utils.file_helpers import build_recursive_excluded_roots, get_image_files
from ...widgets.preset_manager import get_preset_manager
from ...widgets.toast_notification import ToastManager
from ..models import WindowRefs, WindowServices, WindowState


class ToolActions:
    """Handle toolbar/menu features outside the core preview/batch flows."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._request_preview: Optional[Callable[[], None]] = None
        self._schedule_auto_save: Optional[Callable[[], None]] = None
        self._sync_current_settings: Optional[Callable[..., None]] = None

    def bind(
        self,
        *,
        request_preview: Callable[[], None],
        schedule_auto_save: Callable[[], None],
        sync_current_settings: Callable[..., None],
    ) -> None:
        self._request_preview = request_preview
        self._schedule_auto_save = schedule_auto_save
        self._sync_current_settings = sync_current_settings

    def rotate_preview(self) -> None:
        if not self.state.current_image_path or not os.path.exists(self.state.current_image_path):
            if self.refs.status_label is not None:
                self.refs.status_label.setText("회전할 이미지가 없습니다")
            return

        image = self.services.image_processor.load_image(self.state.current_image_path)
        if image is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("이미지를 불러올 수 없습니다")
            return

        rotated = self.services.image_processor.rotate_image(image, 90)
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_original_image(rotated)
            self.refs.preview_widget.set_processed_image(None)
        if self.refs.status_label is not None:
            self.refs.status_label.setText("이미지를 시계방향 90도 회전했습니다")

    def detect_duplicates(self) -> None:
        input_path = self.refs.input_path_edit.text() if self.refs.input_path_edit else ""
        if not input_path or not os.path.isdir(input_path):
            QMessageBox.warning(self.services.host_window, "경고", "유효한 입력 폴더를 선택하세요.")
            return

        if self.refs.status_label is not None:
            self.refs.status_label.setText("중복 파일 검색 중...")

        from ....utils.file_helpers import detect_duplicates

        recursive = bool(self.state.settings.file_management.recursive_search)
        output_edit = getattr(self.refs, "output_path_edit", None)
        output_path = output_edit.text().strip() if output_edit is not None else ""
        if not output_path:
            output_path = os.path.join(input_path, "output_cropped")
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
            QMessageBox.information(self.services.host_window, "결과", "검색할 이미지 파일이 없습니다.")
            return

        duplicates = detect_duplicates(files, method="size+hash")
        if not duplicates:
            QMessageBox.information(self.services.host_window, "결과", "중복 파일이 발견되지 않았습니다.")
            if self.refs.status_label is not None:
                self.refs.status_label.setText("중복 파일 없음")
            return

        dup_count = sum(len(v) - 1 for v in duplicates.values() if len(v) > 1)
        msg = f"총 {dup_count}개의 중복 파일이 발견되었습니다.\n\n"
        for _hash_key, paths in list(duplicates.items())[:5]:
            if len(paths) > 1:
                msg += f"• {os.path.basename(paths[0])} ({len(paths)}개 중복)\n"
        if len(duplicates) > 5:
            msg += f"\n... 외 {len(duplicates) - 5}개 그룹"

        QMessageBox.information(self.services.host_window, "중복 검색 결과", msg)
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"중복 파일 {dup_count}개 발견")

    def toggle_classification_settings(self) -> None:
        enabled = not self.state.settings.classification.enabled
        self.state.settings.classification.enabled = enabled
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=False)

        if enabled:
            ToastManager.success("🤖 AI 분류 활성화됨 - 배치 처리 시 이미지가 자동 분류됩니다")
            if self.refs.status_label is not None:
                self.refs.status_label.setText("AI 분류 활성화됨")
        else:
            ToastManager.info("AI 분류 비활성화됨")
            if self.refs.status_label is not None:
                self.refs.status_label.setText("AI 분류 비활성화됨")

        if self._schedule_auto_save is not None:
            self._schedule_auto_save()

    def toggle_face_detection_settings(self) -> None:
        enabled = not self.state.settings.face_detection.enabled
        self.state.settings.face_detection.enabled = enabled
        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=False)

        if enabled:
            ToastManager.success("👤 얼굴 감지 활성화됨 - 인물 사진 자동 크롭 조정")
            if self.refs.status_label is not None:
                self.refs.status_label.setText("얼굴 감지 활성화됨")
            if self.state.current_image_path:
                self.do_preview_with_faces()
        else:
            ToastManager.info("얼굴 감지 비활성화됨")
            if self.refs.status_label is not None:
                self.refs.status_label.setText("얼굴 감지 비활성화됨")

        if self._schedule_auto_save is not None:
            self._schedule_auto_save()

    def do_preview_with_faces(self) -> None:
        if not self.state.current_image_path:
            return

        import cv2
        import numpy as np

        from ....core.face import get_face_detector

        detector = get_face_detector(
            use_dnn=getattr(self.state.settings.face_detection, "use_dnn", False),
            min_face_size=getattr(self.state.settings.face_detection, "min_face_size", 30),
        )
        image = cv2.imdecode(
            np.fromfile(self.state.current_image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        if image is None:
            return

        result = detector.detect(image, detect_eyes=True, suggest_crop=True)
        if result.has_faces:
            overlay = detector.draw_detections(image, result)
            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_original_image(image, overlay)
            if self.refs.status_label is not None:
                self.refs.status_label.setText(f"👤 {len(result.faces)}개 얼굴 감지됨")
            ToastManager.info(f"👤 {len(result.faces)}개 얼굴 감지")
        elif self.refs.status_label is not None:
            self.refs.status_label.setText("얼굴을 감지하지 못했습니다")

    def show_smart_enhancement(self) -> None:
        if self.state.last_original is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText("먼저 이미지를 로드하세요")
            return

        enhancer = get_smart_enhancer()
        preset_names = enhancer.get_preset_names()
        presets = [name for preset, name in preset_names.items() if preset != EnhancementPreset.NONE]
        preset, ok = QInputDialog.getItem(
            self.services.host_window,
            "스마트 보정",
            "적용할 프리셋을 선택하세요:",
            presets,
            0,
            False,
        )
        if not (ok and preset):
            return

        selected_preset = None
        for preset_enum, name in preset_names.items():
            if name == preset:
                selected_preset = preset_enum
                break
        if selected_preset is None:
            return

        result = enhancer.apply_preset(self.state.last_original, selected_preset)
        self.state.last_processed = result.image
        if self.refs.preview_widget is not None:
            self.refs.preview_widget.set_processed_image(result.image)

        effects = ", ".join(result.applied_effects[:3])
        ToastManager.success(f"✨ {preset} 적용됨: {effects}")
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"스마트 보정 적용: {preset}")

    def show_multi_compare(self) -> None:
        from ...widgets.multi_compare_window import MultiCompareWindow

        if self.state.multi_compare_window is None:
            self.state.multi_compare_window = MultiCompareWindow(self.services.host_window)

        if self.state.last_original is not None:
            self.state.multi_compare_window.add_image(self.state.last_original, "원본", slot=0)
        if self.state.last_processed is not None:
            self.state.multi_compare_window.add_image(self.state.last_processed, "처리됨", slot=1)

        self.state.multi_compare_window.show()
        self.state.multi_compare_window.raise_()
        self.state.multi_compare_window.activateWindow()

    def show_profile_manager(self) -> None:
        manager = get_batch_profile_manager()
        profiles = manager.list_profiles()
        if not profiles:
            ToastManager.warning("저장된 프로파일이 없습니다")
            return

        profile, ok = QInputDialog.getItem(
            self.services.host_window,
            "프로파일 선택",
            "적용할 프로파일:",
            profiles,
            0,
            False,
        )
        if not (ok and profile):
            return
        if not manager.apply_profile(profile, self.state.settings):
            return

        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=True)
        ToastManager.success(f"📋 '{profile}' 프로파일 적용됨")
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"프로파일 적용: {profile}")
        if self.state.settings.ui.auto_preview and self._request_preview is not None:
            self._request_preview()

    def on_preset_selected(self, preset_name: str) -> None:
        if not preset_name:
            return

        manager = get_preset_manager()
        if not manager.apply_preset(preset_name, self.state.settings):
            return

        if self._sync_current_settings is not None:
            self._sync_current_settings(sync_panel=True, reconfigure_scheduler=True)
        if self.refs.status_label is not None:
            self.refs.status_label.setText(f"'{preset_name}' 프리셋 적용됨")
        ToastManager.success(f"🎨 {preset_name} 프리셋 적용")
        if self.state.settings.ui.auto_preview and self._request_preview is not None:
            self._request_preview()
