#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings and theme actions."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QMessageBox

from ....core.history_manager import CallableCommand, CommandType
from ....core.scene_presets import apply_scene_preset
from ....core.settings_model import AppSettings
from ....i18n.catalog import t
from ...fluent import confirm_qt, nav_icon
from ...styles.themes import get_theme  # legacy QSS fallback
from ...theme_fluent import FLUENT_AVAILABLE, apply_fluent_theme, normalize_theme_name
from ..models import WindowRefs, WindowServices, WindowState


class SettingsActions:
    """Handle settings application, persistence, and theme state."""

    def __init__(
        self,
        state: WindowState,
        refs: WindowRefs,
        services: WindowServices,
    ):
        self.state = state
        self.refs = refs
        self.services = services
        self._reconfigure_scheduler: Optional[Callable[[], None]] = None
        self._request_preview: Optional[Callable[[], None]] = None
        self._applying_history = False

    def bind(
        self,
        *,
        reconfigure_scheduler: Callable[[], None],
        request_preview: Optional[Callable[[], None]] = None,
    ) -> None:
        self._reconfigure_scheduler = reconfigure_scheduler
        self._request_preview = request_preview

    def bump_preview_settings_snapshot(self) -> None:
        self.state.preview_settings_revision += 1
        self.state.preview_settings_snapshot = self.state.settings.to_dict()

    def set_theme(self, theme_name: str) -> None:
        normalized = normalize_theme_name(theme_name)
        if FLUENT_AVAILABLE:
            # qfluentwidgets owns rendering; drop the legacy window QSS.
            apply_fluent_theme(normalized)
            self.services.host_window.setStyleSheet("")
        else:
            self.services.host_window.setStyleSheet(get_theme(normalized))
        theme_name = normalized
        self._refresh_nav_icons()
        for name, action in self.refs.theme_actions.items():
            action.setChecked(name == theme_name)
        if self.state.settings.ui.theme != theme_name:
            self.state.settings.ui.theme = theme_name

    def _refresh_nav_icons(self) -> None:
        """Give the nav rail fresh icons so they repaint for the new theme."""
        nav = getattr(self.refs, "shell_nav", None)
        if nav is None:
            return
        for index, page_key in enumerate(getattr(self.refs, "management_pages", {})):
            item = nav.item(index)
            icon = nav_icon(page_key)
            if item is not None and icon is not None:
                item.setIcon(icon)

    def choose_theme(self, theme_name: str) -> None:
        """Theme picked by the user (menu): apply, mirror in the panel, save."""
        self.set_theme(theme_name)
        if self.refs.settings_panel is not None:
            self.refs.settings_panel.settings = self.state.settings
        self.schedule_auto_save()

    def get_current_theme(self) -> str:
        for name, action in self.refs.theme_actions.items():
            if action.isChecked():
                return name
        return "auto"

    def toggle_theme(self) -> None:
        self.set_theme("light" if self.get_current_theme() == "dark" else "dark")

    def sync_workbench_controls(self) -> None:
        """Mirror settings that also have a quick control on the workbench."""
        toggle = getattr(self.refs, "multi_photo_quick_toggle", None)
        if toggle is not None:
            enabled = bool(self.state.settings.multi_photo.enabled)
            if toggle.isChecked() != enabled:
                was_blocked = toggle.blockSignals(True)
                toggle.setChecked(enabled)
                toggle.blockSignals(was_blocked)
        preview = getattr(self.refs, "preview_widget", None)
        if preview is not None:
            show = bool(self.state.settings.ui.show_contour_overlay)
            if preview.show_contour != show:
                preview.show_contour = show

    def _apply_quick_change(self, mutate: Callable[[AppSettings], None]) -> None:
        """Apply a workbench quick-control change like a settings-panel edit."""
        updated = AppSettings.from_dict(self.state.settings.to_dict())
        mutate(updated)
        self.on_settings_changed(updated)
        if self.refs.settings_panel is not None:
            self.refs.settings_panel.settings = self.state.settings
        if self._request_preview is not None and self.state.settings.ui.auto_preview:
            self._request_preview()

    def apply_scene_preset(self, scene_id: str) -> None:
        if not scene_id or scene_id == "custom":
            return

        def mutate(settings: AppSettings) -> None:
            apply_scene_preset(settings, scene_id)

        self._apply_quick_change(mutate)

    def set_multi_photo_enabled(self, enabled: bool) -> None:
        if bool(self.state.settings.multi_photo.enabled) == bool(enabled):
            return

        def mutate(settings: AppSettings) -> None:
            settings.multi_photo.enabled = bool(enabled)

        self._apply_quick_change(mutate)

    def sync_current_settings(
        self,
        *,
        sync_panel: bool = False,
        reconfigure_scheduler: bool = True,
    ) -> None:
        self.services.image_processor.update_settings(
            self.state.settings.algorithm,
            self.state.settings.processing,
            self.state.settings.advanced,
            self.state.settings.performance,
            self.state.settings.debug,
        )
        self.bump_preview_settings_snapshot()
        processor = self.services.batch_session.processor
        if processor is not None:
            processor.update_settings(self.state.settings)
        self.services.watch_mode_coordinator.update_settings(self.state.settings)

        if self.state.settings.ui.theme != self.get_current_theme():
            self.set_theme(self.state.settings.ui.theme)

        if sync_panel and self.refs.settings_panel is not None:
            self.refs.settings_panel.settings = self.state.settings
        self.sync_workbench_controls()

        if reconfigure_scheduler and self._reconfigure_scheduler is not None:
            self._reconfigure_scheduler()

    def apply_loaded_settings(self, settings) -> None:
        self.state.settings = settings
        self.sync_current_settings(sync_panel=False, reconfigure_scheduler=False)

        if self.refs.input_path_edit is not None and settings.last_input_path:
            self.refs.input_path_edit.setText(settings.last_input_path)
        if self.refs.output_path_edit is not None and settings.last_output_path:
            self.refs.output_path_edit.setText(settings.last_output_path)

        if self._reconfigure_scheduler is not None:
            self._reconfigure_scheduler()

    def on_settings_changed(self, settings) -> None:
        previous = AppSettings.from_dict(self.state.settings.to_dict())
        next_settings = AppSettings.from_dict(settings.to_dict())
        if (
            not self._applying_history
            and previous.to_dict() != next_settings.to_dict()
        ):
            self.services.history_manager.record_applied(
                CallableCommand(
                    do=lambda: self._apply_settings_from_history(next_settings),
                    undo=lambda: self._apply_settings_from_history(previous),
                    redo=lambda: self._apply_settings_from_history(next_settings),
                    description=t("history.settings_changed"),
                    command_type=CommandType.SETTINGS,
                    merge_key="settings",
                ),
                merge_key="settings",
            )
        self.state.settings = settings
        self.sync_current_settings(sync_panel=False, reconfigure_scheduler=True)
        self.schedule_auto_save()

    def _apply_settings_from_history(self, settings: AppSettings) -> bool:
        self._applying_history = True
        try:
            snapshot = AppSettings.from_dict(settings.to_dict())
            self.state.settings = snapshot
            self.sync_current_settings(sync_panel=True, reconfigure_scheduler=True)
            self.schedule_auto_save()
            return True
        finally:
            self._applying_history = False

    def schedule_auto_save(self) -> None:
        if self.services.auto_save_timer is None:
            timer = QTimer(self.services.host_window)
            timer.setSingleShot(True)
            timer.timeout.connect(self.do_auto_save)
            self.services.auto_save_timer = timer
        self.services.auto_save_timer.start(2000)

    def persist_paths(self) -> bool:
        if self.refs.input_path_edit is not None:
            self.state.settings.last_input_path = self.refs.input_path_edit.text()
        if self.refs.output_path_edit is not None:
            self.state.settings.last_output_path = self.refs.output_path_edit.text()
        return self.services.settings_manager.save(self.state.settings)

    def do_auto_save(self) -> None:
        saved = self.persist_paths()
        if not saved and self.refs.statusbar is not None:
            # Saving is silent when it works; only a failure needs attention.
            self.refs.statusbar.showMessage(t("settings.autosave.failed"), 5000)

    def reset_settings(self) -> None:
        reply = confirm_qt(
            self.services.host_window,
            t("menu.edit.reset_settings"),
            t("settings.reset.confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply:
            default_settings = self.services.settings_manager.get_default()
            if self.refs.settings_panel is not None:
                self.refs.settings_panel.settings = default_settings
            self.apply_loaded_settings(default_settings)
            if self.refs.statusbar is not None:
                self.refs.statusbar.showMessage(t("settings.reset.done"), 3000)

    def save_window_state(self) -> None:
        settings = QSettings("PhotoCropper", "MainWindow")
        settings.setValue("geometry", self.services.host_window.saveGeometry())
        settings.setValue("windowState", self.services.host_window.saveState())
        histogram_action = self.refs.actions.get("view.histogram")
        if histogram_action is not None:
            settings.setValue("showHistogram", histogram_action.isChecked())

    def restore_window_state(self) -> None:
        settings = QSettings("PhotoCropper", "MainWindow")
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        if geometry:
            self.services.host_window.restoreGeometry(geometry)
        if state:
            self.services.host_window.restoreState(state)
        histogram_action = self.refs.actions.get("view.histogram")
        if histogram_action is not None:
            histogram_action.setChecked(
                str(settings.value("showHistogram", "false")).lower() == "true"
            )
