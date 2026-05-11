#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Runtime translation updates for MainWindow."""

from __future__ import annotations

from ...i18n.catalog import t


class TranslationRuntimeMixin:
    """Update already-built widgets when the active language changes."""

    def _on_language_changed(self, _language: str) -> None:
        self.retranslate_ui()
    def _update_history_actions(self) -> None:
        undo_action = self.refs.actions.get("edit.undo")
        if undo_action is not None:
            undo_action.setEnabled(self.services.history_manager.can_undo)
        redo_action = self.refs.actions.get("edit.redo")
        if redo_action is not None:
            redo_action.setEnabled(self.services.history_manager.can_redo)
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
            "edit.undo": t("menu.edit.undo"),
            "edit.redo": t("menu.edit.redo"),
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
