#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Status bar builder for the main window."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QStatusBar

from ....i18n.catalog import t
from ..models import WindowRefs


def build_statusbar(window, refs: WindowRefs) -> None:
    refs.statusbar = QStatusBar()
    window.setStatusBar(refs.statusbar)
    refs.statusbar.setSizeGripEnabled(True)

    refs.status_label = QLabel(f" {t('status.ready')}")
    refs.status_label.setStyleSheet("font-weight: bold; margin-left: 4px;")
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
    refs.image_info_badge.setStyleSheet(
        """
        background-color: rgba(128, 128, 128, 0.2);
        border-radius: 4px;
        padding: 2px 8px;
        margin: 0 4px;
    """
    )
    refs.statusbar.addPermanentWidget(refs.image_info_badge)

    refs.file_count_badge = QLabel(t("status.file_empty"))
    refs.file_count_badge.setStyleSheet(
        """
        background-color: rgba(9, 105, 218, 0.2);
        color: #58a6ff;
        border-radius: 4px;
        padding: 2px 8px;
        margin: 0 4px;
        font-weight: bold;
    """
    )
    refs.statusbar.addPermanentWidget(refs.file_count_badge)
