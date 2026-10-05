#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shell construction for MainWindow."""

from __future__ import annotations

from ..builders import build_central_widget, build_menu, build_statusbar


def build_main_window_shell(window, state, refs, services) -> None:
    self = window
    self._setup_window()
    build_menu(
        self,
        refs,
        settings_actions=self.settings_actions,
        input_actions=self.input_actions,
        preview_actions=self.preview_actions,
        batch_actions=self.batch_actions,
        dialog_actions=self.dialog_actions,
        watch_actions=self.watch_actions,
        tool_actions=self.tool_actions,
        feature_actions=self.feature_actions,
    )
    self.services.history_manager.set_change_callback(self._update_history_actions)
    self._update_history_actions()
    build_central_widget(
        self,
        refs,
        state,
        services,
        input_actions=self.input_actions,
        preview_actions=self.preview_actions,
        batch_actions=self.batch_actions,
        navigation_actions=self.navigation_actions,
        settings_actions=self.settings_actions,
        tool_actions=self.tool_actions,
    )
    build_statusbar(self, refs)


__all__ = ["build_main_window_shell"]
