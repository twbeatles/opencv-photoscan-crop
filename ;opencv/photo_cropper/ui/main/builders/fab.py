#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Floating action button builder for the main window."""

from __future__ import annotations

from ...widgets.floating_action_button import QuickActionFAB
from ..models import WindowRefs


def build_fab(
    window,
    refs: WindowRefs,
    *,
    preview_actions,
    batch_actions,
    tool_actions,
    feature_actions,
) -> None:
    refs.fab = QuickActionFAB(window)
    refs.fab.preview_requested.connect(preview_actions.request_preview)
    refs.fab.process_requested.connect(batch_actions.start_processing)
    refs.fab.rotate_requested.connect(tool_actions.rotate_preview)
    refs.fab.fullscreen_requested.connect(feature_actions.show_fullscreen)
    refs.fab.show()
