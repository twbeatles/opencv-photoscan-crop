#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Menu builder for the main window."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence

from ...styles.themes import get_available_themes
from ..models import WindowRefs


def build_menu(
    window,
    refs: WindowRefs,
    *,
    settings_actions,
    input_actions,
    preview_actions,
    batch_actions,
    dialog_actions,
    watch_actions,
    tool_actions,
) -> None:
    menubar = window.menuBar()
    if menubar is None:
        return

    file_menu = menubar.addMenu("파일(&F)")
    if file_menu is None:
        return

    open_input_action = QAction("입력 폴더 선택(&O)", window)
    open_input_action.setShortcut(QKeySequence("Ctrl+O"))
    open_input_action.triggered.connect(input_actions.select_input_folder)
    file_menu.addAction(open_input_action)

    open_output_action = QAction("출력 폴더 선택", window)
    open_output_action.triggered.connect(input_actions.select_output_folder)
    file_menu.addAction(open_output_action)
    file_menu.addSeparator()

    open_image_action = QAction("이미지 열기(&I)", window)
    open_image_action.setShortcut(QKeySequence("Ctrl+I"))
    open_image_action.triggered.connect(input_actions.open_single_image)
    file_menu.addAction(open_image_action)
    file_menu.addSeparator()

    open_folder_action = QAction("출력 폴더 열기(&E)", window)
    open_folder_action.setShortcut(QKeySequence("Ctrl+E"))
    open_folder_action.triggered.connect(input_actions.open_output_folder)
    file_menu.addAction(open_folder_action)
    file_menu.addSeparator()

    exit_action = QAction("종료(&X)", window)
    exit_action.setShortcut(QKeySequence("Ctrl+Q"))
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    edit_menu = menubar.addMenu("편집(&E)")
    if edit_menu is None:
        return
    reset_settings_action = QAction("설정 초기화", window)
    reset_settings_action.triggered.connect(settings_actions.reset_settings)
    edit_menu.addAction(reset_settings_action)

    view_menu = menubar.addMenu("보기(&V)")
    if view_menu is None:
        return
    refs.theme_actions = {}
    for theme_name in get_available_themes():
        action = QAction(f"{theme_name.title()} 테마", window)
        action.setCheckable(True)
        action.triggered.connect(
            lambda _checked=False, theme=theme_name: settings_actions.set_theme(theme)
        )
        view_menu.addAction(action)
        refs.theme_actions[theme_name] = action

    tools_menu = menubar.addMenu("도구(&T)")
    if tools_menu is None:
        return

    preview_action = QAction("미리보기(&P)", window)
    preview_action.setShortcut(QKeySequence("Ctrl+P"))
    preview_action.triggered.connect(preview_actions.request_preview)
    tools_menu.addAction(preview_action)
    tools_menu.addSeparator()

    retry_failed_action = QAction("실패 파일 재처리", window)
    retry_failed_action.triggered.connect(batch_actions.retry_failed_files)
    tools_menu.addAction(retry_failed_action)

    refresh_action = QAction("새로고침", window)
    refresh_action.setShortcut(QKeySequence("F5"))
    refresh_action.triggered.connect(input_actions.refresh_file_list)
    tools_menu.addAction(refresh_action)

    rotate_action = QAction("회전(&R)", window)
    rotate_action.setShortcut(QKeySequence("Ctrl+R"))
    rotate_action.triggered.connect(tool_actions.rotate_preview)
    tools_menu.addAction(rotate_action)
    tools_menu.addSeparator()

    compare_action = QAction("Before/After 비교 (&C)", window)
    compare_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
    compare_action.triggered.connect(dialog_actions.show_compare_dialog)
    tools_menu.addAction(compare_action)

    crop_editor_action = QAction("수동 영역 편집...", window)
    crop_editor_action.triggered.connect(dialog_actions.show_crop_editor)
    tools_menu.addAction(crop_editor_action)
    tools_menu.addSeparator()

    duplicate_action = QAction("중복 파일 검색...", window)
    duplicate_action.triggered.connect(tool_actions.detect_duplicates)
    tools_menu.addAction(duplicate_action)
    tools_menu.addSeparator()

    ai_menu = tools_menu.addMenu("🤖 AI 기능")
    if ai_menu is None:
        return

    classification_action = QAction("이미지 자동 분류", window)
    classification_action.triggered.connect(tool_actions.toggle_classification_settings)
    ai_menu.addAction(classification_action)

    face_detect_action = QAction("얼굴 감지 설정", window)
    face_detect_action.triggered.connect(tool_actions.toggle_face_detection_settings)
    ai_menu.addAction(face_detect_action)

    smart_enhance_action = QAction("스마트 보정", window)
    smart_enhance_action.triggered.connect(tool_actions.show_smart_enhancement)
    ai_menu.addAction(smart_enhance_action)
    tools_menu.addSeparator()

    refs.watch_mode_action = QAction("👁️ 폴더 감시 모드", window)
    refs.watch_mode_action.setCheckable(True)
    refs.watch_mode_action.triggered.connect(watch_actions.toggle_watch_mode)
    tools_menu.addAction(refs.watch_mode_action)
    tools_menu.addSeparator()

    multi_compare_action = QAction("🖼️ 멀티 이미지 비교", window)
    multi_compare_action.setShortcut(QKeySequence("Ctrl+M"))
    multi_compare_action.triggered.connect(tool_actions.show_multi_compare)
    tools_menu.addAction(multi_compare_action)
    tools_menu.addSeparator()

    profile_menu = tools_menu.addMenu("📋 프로파일")
    if profile_menu is None:
        return
    profile_manager_action = QAction("프로파일 관리...", window)
    profile_manager_action.triggered.connect(tool_actions.show_profile_manager)
    profile_menu.addAction(profile_manager_action)
    profile_menu.addSeparator()
    refs.profile_menu = profile_menu

    help_menu = menubar.addMenu("도움말(&H)")
    if help_menu is None:
        return
    help_action = QAction("사용 방법", window)
    help_action.setShortcut(QKeySequence("F1"))
    help_action.triggered.connect(dialog_actions.show_help)
    help_menu.addAction(help_action)

    about_action = QAction("정보", window)
    about_action.triggered.connect(dialog_actions.show_about)
    help_menu.addAction(about_action)
