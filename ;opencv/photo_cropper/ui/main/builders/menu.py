#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Menu builder for the main window."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence

from ....i18n.catalog import t
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

    file_menu = menubar.addMenu(t("menu.file"))
    if file_menu is None:
        return
    refs.menus["file"] = file_menu

    open_input_action = QAction(t("menu.file.open_input"), window)
    open_input_action.setShortcut(QKeySequence("Ctrl+O"))
    open_input_action.triggered.connect(input_actions.select_input_folder)
    file_menu.addAction(open_input_action)
    refs.actions["file.open_input"] = open_input_action

    open_output_action = QAction(t("menu.file.open_output"), window)
    open_output_action.triggered.connect(input_actions.select_output_folder)
    file_menu.addAction(open_output_action)
    refs.actions["file.open_output"] = open_output_action
    file_menu.addSeparator()

    open_image_action = QAction(t("menu.file.open_image"), window)
    open_image_action.setShortcut(QKeySequence("Ctrl+I"))
    open_image_action.triggered.connect(input_actions.open_single_image)
    file_menu.addAction(open_image_action)
    refs.actions["file.open_image"] = open_image_action
    file_menu.addSeparator()

    open_folder_action = QAction(t("menu.file.open_output_folder"), window)
    open_folder_action.setShortcut(QKeySequence("Ctrl+E"))
    open_folder_action.triggered.connect(input_actions.open_output_folder)
    file_menu.addAction(open_folder_action)
    refs.actions["file.open_output_folder"] = open_folder_action
    file_menu.addSeparator()

    exit_action = QAction(t("menu.file.exit"), window)
    exit_action.setShortcut(QKeySequence("Ctrl+Q"))
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)
    refs.actions["file.exit"] = exit_action

    edit_menu = menubar.addMenu(t("menu.edit"))
    if edit_menu is None:
        return
    refs.menus["edit"] = edit_menu
    reset_settings_action = QAction(t("menu.edit.reset_settings"), window)
    reset_settings_action.triggered.connect(settings_actions.reset_settings)
    edit_menu.addAction(reset_settings_action)
    refs.actions["edit.reset_settings"] = reset_settings_action

    view_menu = menubar.addMenu(t("menu.view"))
    if view_menu is None:
        return
    refs.menus["view"] = view_menu
    refs.theme_actions = {}
    for theme_name in get_available_themes():
        action = QAction(t("menu.view.theme", theme=theme_name.title()), window)
        action.setCheckable(True)
        action.triggered.connect(
            lambda _checked=False, theme=theme_name: settings_actions.set_theme(theme)
        )
        view_menu.addAction(action)
        refs.theme_actions[theme_name] = action

    tools_menu = menubar.addMenu(t("menu.tools"))
    if tools_menu is None:
        return
    refs.menus["tools"] = tools_menu

    preview_action = QAction(t("menu.tools.preview"), window)
    preview_action.setShortcut(QKeySequence("Ctrl+P"))
    preview_action.triggered.connect(preview_actions.request_preview)
    tools_menu.addAction(preview_action)
    refs.actions["tools.preview"] = preview_action
    tools_menu.addSeparator()

    retry_failed_action = QAction(t("menu.tools.retry_failed"), window)
    retry_failed_action.triggered.connect(batch_actions.retry_failed_files)
    tools_menu.addAction(retry_failed_action)
    refs.actions["tools.retry_failed"] = retry_failed_action

    refresh_action = QAction(t("menu.tools.refresh"), window)
    refresh_action.setShortcut(QKeySequence("F5"))
    refresh_action.triggered.connect(input_actions.refresh_file_list)
    tools_menu.addAction(refresh_action)
    refs.actions["tools.refresh"] = refresh_action

    rotate_action = QAction(t("menu.tools.rotate"), window)
    rotate_action.setShortcut(QKeySequence("Ctrl+R"))
    rotate_action.triggered.connect(tool_actions.rotate_preview)
    tools_menu.addAction(rotate_action)
    refs.actions["tools.rotate"] = rotate_action
    tools_menu.addSeparator()

    compare_action = QAction(t("menu.tools.compare"), window)
    compare_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
    compare_action.triggered.connect(dialog_actions.show_compare_dialog)
    tools_menu.addAction(compare_action)
    refs.actions["tools.compare"] = compare_action

    crop_editor_action = QAction(t("menu.tools.crop_editor"), window)
    crop_editor_action.triggered.connect(dialog_actions.show_crop_editor)
    tools_menu.addAction(crop_editor_action)
    refs.actions["tools.crop_editor"] = crop_editor_action
    tools_menu.addSeparator()

    duplicate_action = QAction(t("menu.tools.duplicates"), window)
    duplicate_action.triggered.connect(tool_actions.detect_duplicates)
    tools_menu.addAction(duplicate_action)
    refs.actions["tools.duplicates"] = duplicate_action
    tools_menu.addSeparator()

    ai_menu = tools_menu.addMenu(t("menu.tools.ai"))
    if ai_menu is None:
        return
    refs.menus["tools.ai"] = ai_menu

    classification_action = QAction(t("menu.tools.classification"), window)
    classification_action.triggered.connect(tool_actions.toggle_classification_settings)
    ai_menu.addAction(classification_action)
    refs.actions["tools.classification"] = classification_action

    face_detect_action = QAction(t("menu.tools.face_detection"), window)
    face_detect_action.triggered.connect(tool_actions.toggle_face_detection_settings)
    ai_menu.addAction(face_detect_action)
    refs.actions["tools.face_detection"] = face_detect_action

    smart_enhance_action = QAction(t("menu.tools.smart_enhancement"), window)
    smart_enhance_action.triggered.connect(tool_actions.show_smart_enhancement)
    ai_menu.addAction(smart_enhance_action)
    refs.actions["tools.smart_enhancement"] = smart_enhance_action
    tools_menu.addSeparator()

    refs.watch_mode_action = QAction(t("menu.tools.watch_mode"), window)
    refs.watch_mode_action.setCheckable(True)
    refs.watch_mode_action.triggered.connect(watch_actions.toggle_watch_mode)
    tools_menu.addAction(refs.watch_mode_action)
    refs.actions["tools.watch_mode"] = refs.watch_mode_action
    tools_menu.addSeparator()

    multi_compare_action = QAction(t("menu.tools.multi_compare"), window)
    multi_compare_action.setShortcut(QKeySequence("Ctrl+M"))
    multi_compare_action.triggered.connect(tool_actions.show_multi_compare)
    tools_menu.addAction(multi_compare_action)
    refs.actions["tools.multi_compare"] = multi_compare_action
    tools_menu.addSeparator()

    profile_menu = tools_menu.addMenu(t("menu.tools.profile"))
    if profile_menu is None:
        return
    profile_manager_action = QAction(t("menu.tools.profile_manager"), window)
    profile_manager_action.triggered.connect(tool_actions.show_profile_manager)
    profile_menu.addAction(profile_manager_action)
    profile_menu.addSeparator()
    refs.profile_menu = profile_menu
    refs.menus["tools.profile"] = profile_menu
    refs.actions["tools.profile_manager"] = profile_manager_action

    help_menu = menubar.addMenu(t("menu.help"))
    if help_menu is None:
        return
    refs.menus["help"] = help_menu
    help_action = QAction(t("menu.help.help"), window)
    help_action.setShortcut(QKeySequence("F1"))
    help_action.triggered.connect(dialog_actions.show_help)
    help_menu.addAction(help_action)
    refs.actions["help.help"] = help_action

    about_action = QAction(t("menu.help.about"), window)
    about_action.triggered.connect(dialog_actions.show_about)
    help_menu.addAction(about_action)
    refs.actions["help.about"] = about_action
