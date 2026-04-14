#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings and theme actions."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QMessageBox

from ....i18n.catalog import t
from ...styles.themes import get_theme
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

    def bind(self, *, reconfigure_scheduler: Callable[[], None]) -> None:
        self._reconfigure_scheduler = reconfigure_scheduler

    def bump_preview_settings_snapshot(self) -> None:
        self.state.preview_settings_revision += 1
        self.state.preview_settings_snapshot = self.state.settings.to_dict()

    def set_theme(self, theme_name: str) -> None:
        self.services.host_window.setStyleSheet(get_theme(theme_name))
        for name, action in self.refs.theme_actions.items():
            action.setChecked(name == theme_name)
        if self.state.settings.ui.theme != theme_name:
            self.state.settings.ui.theme = theme_name

    def get_current_theme(self) -> str:
        for name, action in self.refs.theme_actions.items():
            if action.isChecked():
                return name
        return "dark"

    def toggle_theme(self) -> None:
        self.set_theme("light" if self.get_current_theme() == "dark" else "dark")

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
        self.state.settings = settings
        self.sync_current_settings(sync_panel=False, reconfigure_scheduler=True)
        self.schedule_auto_save()

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
        if self.refs.status_label is not None:
            self.refs.status_label.setText(
                "✓ " + t("dialog.save") if saved else "⚠ " + t("dialog.warning")
            )

    def reset_settings(self) -> None:
        reply = QMessageBox.question(
            self.services.host_window,
            t("menu.edit.reset_settings"),
            t("menu.edit.reset_settings"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            default_settings = self.services.settings_manager.get_default()
            if self.refs.settings_panel is not None:
                self.refs.settings_panel.settings = default_settings
            self.apply_loaded_settings(default_settings)
            if self.refs.statusbar is not None:
                self.refs.statusbar.showMessage(t("menu.edit.reset_settings"), 3000)

    def save_window_state(self) -> None:
        settings = QSettings("PhotoCropper", "MainWindow")
        settings.setValue("geometry", self.services.host_window.saveGeometry())
        settings.setValue("windowState", self.services.host_window.saveState())

    def restore_window_state(self) -> None:
        settings = QSettings("PhotoCropper", "MainWindow")
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        if geometry:
            self.services.host_window.restoreGeometry(geometry)
        if state:
            self.services.host_window.restoreState(state)
