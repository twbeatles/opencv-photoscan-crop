#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Status bar builder for the main window."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QStatusBar

from ....i18n.catalog import t
from ...design_tokens import SPACE_XXS, status_badge_qss
from ..models import WindowRefs


def build_statusbar(window, refs: WindowRefs) -> None:
    refs.statusbar = QStatusBar()
    window.setStatusBar(refs.statusbar)
    refs.statusbar.setSizeGripEnabled(True)

    refs.status_label = QLabel(f" {t('status.ready')}")
    refs.status_label.setStyleSheet(
        f"font-weight: bold; margin-left: {SPACE_XXS}px;"
    )
    refs.statusbar.addWidget(refs.status_label, 1)

    refs.status_progress = QProgressBar()
    refs.status_progress.setMaximumWidth(200)
    refs.status_progress.setMaximumHeight(16)
    refs.status_progress.setVisible(False)
    refs.statusbar.addWidget(refs.status_progress)

    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    refs.statusbar.addPermanentWidget(line)

    refs.image_info_badge = QLabel(t("status.image_empty"))
    refs.image_info_badge.setStyleSheet(status_badge_qss())
    refs.statusbar.addPermanentWidget(refs.image_info_badge)

    refs.file_count_badge = QLabel(t("status.file_empty"))
    refs.file_count_badge.setStyleSheet(status_badge_qss())
    refs.statusbar.addPermanentWidget(refs.file_count_badge)
