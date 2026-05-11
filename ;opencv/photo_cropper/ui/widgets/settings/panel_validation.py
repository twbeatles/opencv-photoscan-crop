#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SettingsPanel validation helpers."""

from __future__ import annotations

from ....core.settings_model import CLASSIFICATION_CATEGORY_KEYS
from ....i18n.catalog import t
from ....utils.path_validation import validate_single_path_segment

def validate_form_inputs(panel):
    self = panel
    naming_invalid = False
    classification_invalid = False

    for widget in (self.naming_prefix_edit, self.naming_suffix_edit):
        valid, _ = validate_single_path_segment(widget.text(), allow_empty=True)
        naming_invalid = naming_invalid or not valid
        self._set_line_edit_error(widget, not valid)

    for key in CLASSIFICATION_CATEGORY_KEYS:
        widget = self.classification_folder_inputs.get(key)
        if widget is None:
            continue
        valid, _ = validate_single_path_segment(widget.text(), allow_empty=True)
        classification_invalid = classification_invalid or not valid
        self._set_line_edit_error(widget, not valid)

    self.naming_validation_label.setVisible(naming_invalid)
    self.classification_validation_label.setVisible(classification_invalid)
    self._is_form_valid = not (naming_invalid or classification_invalid)
    return self._is_form_valid


def apply_validation_state(panel):
    self = panel
    self.naming_validation_label.setText(t("settings.validation.naming"))
    self.classification_validation_label.setText(t("settings.validation.classification"))
    self._validate_form_inputs()


__all__ = ["validate_form_inputs", "apply_validation_state"]
