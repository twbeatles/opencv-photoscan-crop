#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog actions for the main window."""

from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ....core.manual_extract import scale_contour_to_preview
from ..models import WindowRefs, WindowServices, WindowState
from ...widgets.compare_widget import BeforeAfterCompareWidget
from ...widgets.crop_editor_widget import CropEditorWidget


class DialogActions:
    """Encapsulate compare/help/about/crop-editor dialogs."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._resolve_preview_path: Optional[Callable[[], Optional[str]]] = None
        self._update_image_list: Optional[Callable[[], None]] = None
        self._on_crop_applied: Optional[Callable[..., None]] = None

    def bind(
        self,
        *,
        resolve_preview_path: Callable[[], Optional[str]],
        update_image_list: Callable[[], None],
        on_crop_applied: Callable[..., None],
    ) -> None:
        self._resolve_preview_path = resolve_preview_path
        self._update_image_list = update_image_list
        self._on_crop_applied = on_crop_applied

    def show_compare_dialog(self) -> None:
        if self.state.last_original is None or self.state.last_processed is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    "비교할 이미지가 없습니다. 먼저 미리보기를 실행하세요."
                )
            return

        dialog = QDialog(self.services.host_window)
        dialog.setWindowTitle("Before/After 비교")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        compare_widget = BeforeAfterCompareWidget()
        compare_widget.set_images(self.state.last_original, self.state.last_processed)
        layout.addWidget(compare_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dialog.close)
        layout.addWidget(btn_box)
        dialog.exec()

    def _set_detected_contour(
        self, crop_editor: CropEditorWidget, contour_points
    ) -> None:
        if contour_points is None:
            crop_editor.set_rectangle_mode()
            return
        try:
            points = []
            for point in contour_points:
                if point is None or len(point) < 2:
                    continue
                points.append((float(point[0]), float(point[1])))
            if len(points) != 4:
                crop_editor.set_rectangle_mode()
                return
            crop_editor.set_perspective_points(points)
        except Exception:
            crop_editor.set_rectangle_mode()

    def show_crop_editor(self) -> None:
        source_path = self._resolve_preview_path() if self._resolve_preview_path else None
        if source_path is None and self.state.last_original is None:
            if self.refs.status_label is not None:
                self.refs.status_label.setText(
                    "편집할 이미지가 없습니다. 먼저 이미지를 불러오세요."
                )
            return

        if not self.state.image_list and self._update_image_list is not None:
            self._update_image_list()

        dialog = QDialog(self.services.host_window)
        dialog.setWindowTitle("수동 영역 편집")
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout(dialog)
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("← 이전 사진")
        next_btn = QPushButton("다음 사진 →")
        nav_hint = QLabel("외곽선 점을 드래그해 조정하세요 (←/→ 이동)")
        nav_hint.setObjectName("subtitleLabel")
        nav_pos_label = QLabel("")
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        nav_layout.addWidget(nav_hint)
        nav_layout.addStretch()
        nav_layout.addWidget(nav_pos_label)
        layout.addLayout(nav_layout)

        crop_editor = CropEditorWidget()
        crop_editor.crop_applied.connect(
            lambda img: self._on_crop_applied(img, None)
            if self._on_crop_applied is not None
            else None
        )
        crop_editor.crop_cancelled.connect(dialog.close)
        layout.addWidget(crop_editor)

        state = {"index": self.state.current_image_index}

        def update_editor_title(path: Optional[str]) -> None:
            filename = os.path.basename(path) if path else "현재 이미지"
            if self.state.image_list and state["index"] >= 0:
                nav_pos_label.setText(f"{state['index'] + 1}/{len(self.state.image_list)}")
            else:
                nav_pos_label.setText("단일")
            dialog.setWindowTitle(f"수동 영역 편집 - {filename}")

        def load_editor_image(path: Optional[str]) -> bool:
            if not path or not os.path.exists(path):
                return False
            try:
                preview_result = self.services.image_processor.process_preview(
                    path,
                    max_size=1200,
                    debug_tag="editor",
                )
            except Exception as exc:
                QMessageBox.warning(
                    dialog,
                    "경고",
                    f"이미지를 불러올 수 없습니다.\n{os.path.basename(path)}\n\n{exc}",
                )
                return False

            if preview_result is None or preview_result.original_preview is None:
                return False

            crop_editor.set_image(preview_result.original_preview)
            crop_result = preview_result.crop_result
            contour = scale_contour_to_preview(
                preview_result.original_preview,
                crop_result,
            )
            self.state.last_detected_contour = (
                contour.copy() if contour is not None else None
            )
            self._set_detected_contour(crop_editor, contour)

            if self.refs.preview_widget is not None:
                self.refs.preview_widget.set_original_image(
                    preview_result.original_preview,
                    preview_result.overlay_preview,
                    contour,
                )
            if crop_result and crop_result.success and crop_result.image is not None:
                if self.refs.preview_widget is not None:
                    self.refs.preview_widget.set_processed_image(crop_result.image)
                self.state.last_processed = crop_result.image.copy()
            else:
                if self.refs.preview_widget is not None:
                    self.refs.preview_widget.set_processed_image(None)
                self.state.last_processed = None

            self.state.last_original = preview_result.original_preview
            self.state.current_image_path = path

            if self.state.image_list:
                try:
                    state["index"] = self.state.image_list.index(path)
                    self.state.current_image_index = state["index"]
                except ValueError:
                    pass

            update_editor_title(path)
            return True

        def navigate_editor(delta: int) -> None:
            if not self.state.image_list and self._update_image_list is not None:
                self._update_image_list()
            if not self.state.image_list:
                return

            idx = state["index"]
            if idx < 0:
                if self.state.current_image_path in self.state.image_list:
                    idx = self.state.image_list.index(self.state.current_image_path)
                else:
                    idx = 0
            idx = (idx + delta) % len(self.state.image_list)
            state["index"] = idx
            load_editor_image(self.state.image_list[idx])

        prev_btn.clicked.connect(lambda: navigate_editor(-1))
        next_btn.clicked.connect(lambda: navigate_editor(1))
        prev_btn.setEnabled(len(self.state.image_list) > 1)
        next_btn.setEnabled(len(self.state.image_list) > 1)

        shortcut_prev = QShortcut(QKeySequence("Left"), dialog)
        shortcut_next = QShortcut(QKeySequence("Right"), dialog)
        shortcut_prev.activated.connect(lambda: navigate_editor(-1))
        shortcut_next.activated.connect(lambda: navigate_editor(1))

        loaded = False
        if source_path:
            loaded = load_editor_image(source_path)
        if not loaded and self.state.last_original is not None:
            crop_editor.set_image(self.state.last_original)
            self._set_detected_contour(crop_editor, self.state.last_detected_contour)
            update_editor_title(self.state.current_image_path)

        dialog.exec()

    def show_help(self) -> None:
        QMessageBox.information(
            self.services.host_window,
            "사용 방법",
            """🔧 사용 방법

1. 입력 폴더 선택: 처리할 이미지가 있는 폴더
2. 출력 폴더 선택: 결과를 저장할 폴더 (선택사항)
3. 설정 조정: 오른쪽 패널에서 설정 변경
4. 미리보기: Ctrl+P로 한 장 테스트
5. 변환 시작: 전체 이미지 처리

💡 팁
• 이미지를 드래그 앤 드롭으로 열 수 있습니다
• 마우스 휠로 미리보기 확대/축소
• Ctrl+클릭 드래그로 미리보기 이동

⚙️ 3단계+ 탐색 알고리즘
1단계: 다중 스케일 Canny Edge
2단계: Adaptive Threshold
3단계: Gradient Analysis (Sobel)
4단계: Harris Corner Detection (선택)""",
        )

    def show_about(self) -> None:
        version = getattr(self.services.host_window, "VERSION", "9.0")
        QMessageBox.about(
            self.services.host_window,
            "정보",
            f"""사진 자동 자르기 v{version}

3단계+ 지능형 CV 알고리즘으로
다양한 배경에서 사진을 자동으로 검출하고 자릅니다.

주요 기능:
• 다중 스케일 적응형 검출 알고리즘
• CLAHE 대비 향상
• 실시간 미리보기 (확대/축소 지원)
• 다크/라이트 테마
• 드래그 앤 드롭 지원
• 배치 처리 및 진행 상황 추적

기술: OpenCV, NumPy, PyQt6""",
        )
