#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crop workbench page builder.

The page follows the order of the actual job: choose where the scans are
and where results go, check the detected area in the preview, then start.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ....i18n.catalog import t
from ...components import field_label, secondary_label, themed_splitter
from ...design_tokens import (
    CARD_QSS,
    CONTROL_GAP,
    CONTROL_HEIGHT_LG,
    CONTROL_HEIGHT_MD,
    GROUP_GAP,
    PAGE_MARGIN,
    ROW_GAP,
    SETTINGS_PANEL_MAX_WIDTH,
    SETTINGS_PANEL_MIN_WIDTH,
    SPACE_MD,
    SPACE_SM,
)
from ...fluent import new_button, new_primary_button
from ...widgets.histogram_widget import HistogramWidget
from ...widgets.preset_manager import PresetComboBox
from ...widgets.preview_widget import ImagePreviewWidget
from ...widgets.settings import SettingsPanel
from ...widgets.settings.controls import NoScrollComboBox, populate_scene_presets
from ...widgets.toggle_switch import ModernToggleSwitch
from ..models import WindowRefs, WindowState


def _action_button(refs: WindowRefs, key: str, text_key: str, slot, *, primary: bool = False):
    button = new_primary_button(t(text_key)) if primary else new_button(t(text_key))
    button.setMinimumHeight(CONTROL_HEIGHT_LG if primary else CONTROL_HEIGHT_MD)
    button.clicked.connect(slot)
    refs.buttons[key] = button
    return button


def _path_edit(placeholder_key: str, on_changed) -> QLineEdit:
    edit = QLineEdit()
    edit.setPlaceholderText(t(placeholder_key))
    edit.setMinimumHeight(CONTROL_HEIGHT_MD)
    edit.setClearButtonEnabled(True)
    edit.textChanged.connect(on_changed)
    return edit


def _build_setup_card(
    refs: WindowRefs,
    state: WindowState,
    *,
    input_actions,
    settings_actions,
    tool_actions,
) -> QFrame:
    """Step 1: where the scans are, where results go, what kind of scan."""
    card = QFrame()
    card.setObjectName("workbenchCard")
    card.setStyleSheet(CARD_QSS)

    grid = QGridLayout(card)
    grid.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
    grid.setHorizontalSpacing(CONTROL_GAP)
    grid.setVerticalSpacing(CONTROL_GAP)
    grid.setColumnStretch(1, 1)

    input_label = field_label(t("central.input_folder"))
    refs.labels["central.input_label"] = input_label
    grid.addWidget(input_label, 0, 0)
    refs.input_path_edit = _path_edit(
        "central.input_placeholder", input_actions.on_input_path_changed
    )
    grid.addWidget(refs.input_path_edit, 0, 1)
    grid.addWidget(
        _action_button(
            refs, "central.input_browse", "central.browse", input_actions.select_input_folder
        ),
        0,
        2,
        1,
        2,
    )

    output_label = field_label(t("central.output_folder"))
    refs.labels["central.output_label"] = output_label
    grid.addWidget(output_label, 1, 0)
    refs.output_path_edit = _path_edit(
        "central.output_placeholder", input_actions.on_output_path_changed
    )
    grid.addWidget(refs.output_path_edit, 1, 1)
    grid.addWidget(
        _action_button(
            refs, "central.output_browse", "central.change", input_actions.select_output_folder
        ),
        1,
        2,
    )
    grid.addWidget(
        _action_button(
            refs,
            "central.output_open",
            "central.open_output_folder",
            input_actions.open_output_folder,
        ),
        1,
        3,
    )

    scene_label = field_label(t("central.scene"))
    refs.labels["central.scene_preset_label"] = scene_label
    grid.addWidget(scene_label, 2, 0)

    options_row = QHBoxLayout()
    options_row.setContentsMargins(0, 0, 0, 0)
    options_row.setSpacing(GROUP_GAP)

    scene_combo = NoScrollComboBox()
    scene_combo.setMinimumHeight(CONTROL_HEIGHT_MD)
    scene_combo.setMinimumWidth(200)
    populate_scene_presets(scene_combo)
    scene_combo.setToolTip(t("central.scene.tooltip"))
    scene_combo.activated.connect(
        lambda _index: settings_actions.apply_scene_preset(
            str(scene_combo.currentData() or "custom")
        )
    )
    options_row.addWidget(scene_combo)
    refs.scene_preset_combo = scene_combo

    refs.multi_photo_quick_toggle = ModernToggleSwitch(t("central.multi_photo"))
    refs.multi_photo_quick_toggle.setToolTip(t("central.multi_photo.tooltip"))
    refs.multi_photo_quick_toggle.setChecked(bool(state.settings.multi_photo.enabled))
    refs.multi_photo_quick_toggle.toggled.connect(settings_actions.set_multi_photo_enabled)
    options_row.addWidget(refs.multi_photo_quick_toggle)
    options_row.addStretch(1)

    preset_label = secondary_label(t("toolbar.preset"))
    refs.labels["toolbar.preset"] = preset_label
    options_row.addWidget(preset_label)
    refs.preset_combo = PresetComboBox()
    refs.preset_combo.setMinimumHeight(CONTROL_HEIGHT_MD)
    refs.preset_combo.setMinimumWidth(160)
    refs.preset_combo.setToolTip(t("toolbar.preset.tooltip"))
    refs.preset_combo.preset_selected.connect(tool_actions.on_preset_selected)
    options_row.addWidget(refs.preset_combo)

    grid.addLayout(options_row, 2, 1, 1, 3)
    return card


def _build_action_bar(
    refs: WindowRefs,
    *,
    preview_actions,
    batch_actions,
    navigation_actions,
) -> QWidget:
    """Step 3: move between scans, then start the crop."""
    bar = QWidget()
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(CONTROL_GAP)

    refs.batch_prev_btn = _action_button(
        refs, "central.batch_prev", "central.prev", navigation_actions.navigate_prev
    )
    refs.batch_prev_btn.setToolTip(t("central.prev.tooltip"))
    layout.addWidget(refs.batch_prev_btn)
    refs.batch_next_btn = _action_button(
        refs, "central.batch_next", "central.next", navigation_actions.navigate_next
    )
    refs.batch_next_btn.setToolTip(t("central.next.tooltip"))
    layout.addWidget(refs.batch_next_btn)

    refs.batch_edit_status_label = secondary_label(t("central.position.empty"))
    refs.batch_edit_status_label.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(refs.batch_edit_status_label, 1)

    refs.redetect_btn = _action_button(
        refs, "central.redetect", "central.redetect", preview_actions.request_preview
    )
    refs.redetect_btn.setToolTip(t("central.redetect.tooltip"))
    layout.addWidget(refs.redetect_btn)

    refs.batch_failed_btn = _action_button(
        refs, "central.batch_failed", "central.load_failed", batch_actions.toggle_review_list
    )
    refs.batch_failed_btn.setVisible(False)
    layout.addWidget(refs.batch_failed_btn)

    refs.batch_save_edits_btn = _action_button(
        refs, "central.batch_save", "central.save_edits", batch_actions.save_batch_edited_crops
    )
    refs.batch_save_edits_btn.setToolTip(t("central.save_edits.tooltip"))
    refs.batch_save_edits_btn.setVisible(False)
    layout.addWidget(refs.batch_save_edits_btn)

    refs.process_btn = _action_button(
        refs, "toolbar.start", "toolbar.start", batch_actions.start_from_ui, primary=True
    )
    refs.process_btn.setMinimumWidth(140)
    refs.process_btn.setToolTip(t("toolbar.start.tooltip"))
    layout.addWidget(refs.process_btn)
    return bar


def build_workbench_page(
    refs: WindowRefs,
    state: WindowState,
    *,
    input_actions,
    preview_actions,
    batch_actions,
    navigation_actions,
    settings_actions,
    tool_actions,
) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(PAGE_MARGIN, SPACE_MD, PAGE_MARGIN, SPACE_MD)
    layout.setSpacing(ROW_GAP)

    layout.addWidget(
        _build_setup_card(
            refs,
            state,
            input_actions=input_actions,
            settings_actions=settings_actions,
            tool_actions=tool_actions,
        )
    )

    main_splitter = themed_splitter(Qt.Orientation.Horizontal)

    preview_column = themed_splitter(Qt.Orientation.Vertical)
    refs.preview_widget = ImagePreviewWidget()
    refs.preview_widget.contour_edited.connect(preview_actions.on_preview_contour_edited)
    preview_column.addWidget(refs.preview_widget)

    # Histogram is an expert aid; hidden until enabled from the View menu.
    refs.histogram_widget = HistogramWidget()
    refs.histogram_widget.setVisible(False)
    preview_column.addWidget(refs.histogram_widget)
    preview_column.setStretchFactor(0, 1)
    preview_column.setStretchFactor(1, 0)
    main_splitter.addWidget(preview_column)

    refs.settings_panel = SettingsPanel(state.settings)
    refs.settings_panel.settings_changed.connect(settings_actions.on_settings_changed)
    refs.settings_panel.preview_requested.connect(preview_actions.request_preview)
    refs.settings_panel.setMinimumWidth(SETTINGS_PANEL_MIN_WIDTH)
    refs.settings_panel.setMaximumWidth(SETTINGS_PANEL_MAX_WIDTH)
    main_splitter.addWidget(refs.settings_panel)
    main_splitter.setStretchFactor(0, 1)
    main_splitter.setStretchFactor(1, 0)
    main_splitter.setSizes([760, 320])
    layout.addWidget(main_splitter, 1)

    layout.addWidget(
        _build_action_bar(
            refs,
            preview_actions=preview_actions,
            batch_actions=batch_actions,
            navigation_actions=navigation_actions,
        )
    )
    return page


__all__ = ["build_workbench_page"]
