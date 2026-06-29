#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SettingsPanel runtime translation helpers."""

from __future__ import annotations

from ....i18n.catalog import t
from .i18n_bindings import apply_settings_i18n_bindings

def retranslate_panel(panel) -> None:
    self = panel
    apply_settings_i18n_bindings(self)

    self.tab_widget.setTabText(0, t("settings.tab.basic"))
    self.tab_widget.setTabText(1, t("settings.tab.algorithm"))
    self.tab_widget.setTabText(2, t("settings.tab.processing"))
    self.tab_widget.setTabText(3, t("settings.tab.management"))
    self.tab_widget.setTabText(4, t("settings.tab.ai"))

    self.post_section._title_label.setText(t("settings.section.post"))
    self.output_section._title_label.setText(t("settings.section.output"))
    self.filter_section._title_label.setText(t("settings.section.filter"))
    self.ui_section._title_label.setText(t("settings.section.ui"))
    self.file_management_section._title_label.setText(
        t("settings.section.file_management")
    )
    self.performance_section._title_label.setText(t("settings.section.performance"))
    self.language_section._title_label.setText(t("settings.section.language"))
    if hasattr(self, "tuning_group"):
        self.tuning_group.setTitle(t("settings.precision"))

    for form, widget, key in (
        (self.output_form, self.format_combo, "settings.output_format"),
        (self.output_form, self.quality_spin, "settings.jpg_quality"),
        (self.output_form, self.png_compression_spin, "settings.png_compression"),
        (self.ui_form, self.theme_combo, "settings.theme"),
        (self.file_management_form, self.use_naming_rules_check, "settings.naming_rules"),
        (self.file_management_form, self.naming_prefix_edit, "settings.naming_prefix"),
        (self.file_management_form, self.naming_suffix_edit, "settings.naming_suffix"),
        (self.log_form, self.enable_log_check, "settings.enable_log"),
        (self.log_form, self.log_format_combo, "settings.log_format"),
        (self.language_form, self.language_combo, "settings.language"),
    ):
        label_widget = form.labelForField(widget)
        if label_widget is not None:
            label_widget.setText(t(key))

    self.auto_contrast_check.setText(t("settings.auto_contrast"))
    self.grayscale_check.setText(t("settings.grayscale"))
    self.sharpening_check.setText(t("settings.sharpen"))
    self.denoise_check.setText(t("settings.denoise"))
    self.timestamp_check.setText(t("settings.add_timestamp"))
    self.preserve_metadata_check.setText(t("settings.preserve_metadata"))
    self.backup_original_check.setText(t("settings.backup_original"))
    self.skip_small_check.setText(t("settings.skip_small"))
    self.skip_processed_check.setText(t("settings.skip_processed"))
    self.auto_preview_check.setText(t("settings.auto_preview"))
    self.contour_overlay_check.setText(t("settings.contour_overlay"))
    self.recursive_check.setText(t("settings.recursive"))
    self.naming_counter_check.setText(t("settings.naming_counter"))
    self.naming_date_check.setText(t("settings.naming_date"))
    self.move_failed_check.setText(t("settings.move_failed"))
    self.copy_failed_check.setText(t("settings.copy_failed"))
    self.low_mem_check.setText(t("settings.low_mem"))

    self.classification_group.setTitle(t("settings.section.classification"))
    self.classification_enable_check.setText(t("settings.classification_enable"))
    self.classification_enable_check.setToolTip(
        t("settings.classification_enable.tooltip")
    )
    self.classification_model_label.setText(t("settings.classification_model"))
    self.classification_subfolders_check.setText(
        t("settings.classification_subfolders")
    )
    self.classification_help_label.setText(t("settings.classification_folder.help"))
    self.face_group.setTitle(t("settings.section.face"))
    self.face_detect_enable_check.setText(t("settings.face_enable"))
    self.face_detect_enable_check.setToolTip(t("settings.face_enable.tooltip"))
    if hasattr(self, "face_use_dnn_check"):
        self.face_use_dnn_check.setText(t("settings.face_use_dnn"))
    self.face_auto_orient_check.setText(t("settings.face_auto_orient"))
    self.face_enhance_check.setText(t("settings.face_enhance"))
    self.smart_group.setTitle(t("settings.section.smart"))
    self.smart_enhance_enable_check.setText(t("settings.smart_enable"))
    self.smart_enhance_enable_check.setToolTip(t("settings.smart_enable.tooltip"))
    if hasattr(self, "smart_exposure_check"):
        self.smart_exposure_check.setText(t("settings.smart_exposure"))
    if hasattr(self, "smart_color_balance_check"):
        self.smart_color_balance_check.setText(t("settings.smart_color_balance"))
    self.notification_group.setTitle(t("settings.section.notification"))
    self.notification_enable_check.setText(t("settings.notification_enable"))
    self.notification_enable_check.setToolTip(t("settings.notification_enable.tooltip"))
    self.notification_sound_check.setText(t("settings.notification_sound"))
    self.notification_error_only_check.setText(t("settings.notification_error_only"))
    self.language_info_label.setText(f"💡 {t('settings.language.info')}")

    self.naming_prefix_edit.setPlaceholderText(t("settings.naming_prefix.placeholder"))
    self.naming_suffix_edit.setPlaceholderText(t("settings.naming_suffix.placeholder"))
    if hasattr(self, "debug_browse_btn"):
        self.debug_browse_btn.setText(t("dialog.browse"))
    if hasattr(self, "font_browse_btn"):
        self.font_browse_btn.setText(t("dialog.browse"))
    if hasattr(self, "debug_output_dir_edit"):
        self.debug_output_dir_edit.setPlaceholderText(t("settings.debug_output_dir.placeholder"))
    if hasattr(self, "watermark_font_path_edit"):
        self.watermark_font_path_edit.setPlaceholderText(t("settings.watermark_font.placeholder"))

    current_code = self.language_combo.itemData(self.language_combo.currentIndex())
    self.language_combo.blockSignals(True)
    for index, code in enumerate(("ko", "en", "ja", "zh", "es")):
        self.language_combo.setItemText(index, self._translator.get_language_name(code))
    if current_code is not None:
        for index in range(self.language_combo.count()):
            if self.language_combo.itemData(index) == current_code:
                self.language_combo.setCurrentIndex(index)
                break
    self.language_combo.blockSignals(False)

    self._refresh_category_folder_defaults()
    self._apply_validation_state()


__all__ = ["retranslate_panel"]
