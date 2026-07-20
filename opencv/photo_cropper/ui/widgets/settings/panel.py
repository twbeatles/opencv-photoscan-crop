#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Settings Panel Widget for Photo Cropper v9.0.

Provides tabbed settings interface for all application settings.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFormLayout,
    QFrame,
    QLineEdit,
    QScrollArea,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ....core.settings_model import (
    AppSettings,
    AlgorithmSettings,
    CLASSIFICATION_CATEGORY_KEYS,
    DebugSettings,
    ProcessingSettings,
    OutputSettings,
    FilterSettings,
    UISettings,
    AdvancedProcessingSettings,
    FileManagementSettings,
    PerformanceSettings,
    WatermarkSettings,
    ResizeSettings,
    WatchModeSettings,
    MultiPhotoSettings,
    ClassificationSettings,
    FaceDetectionSettings,
    SmartEnhancementSettings,
    NotificationSettings,
)
from ....i18n.catalog import get_category_folder_defaults, get_translator, t
from ....utils.path_validation import (
    validate_single_path_segment,
)
from .controls import (
    NoScrollComboBox,
    NoScrollDoubleSpinBox,
    NoScrollSlider,
    NoScrollSpinBox,
)
from .i18n_bindings import apply_settings_i18n_bindings
from .panel_i18n import retranslate_panel
from .panel_layout import make_scrollable_tab, setup_ui
from .panel_settings import (
    build_settings,
    build_settings_v8,
    load_settings,
    load_settings_v8,
)
from .panel_validation import apply_validation_state, validate_form_inputs
from .tab_ai import create_ai_settings_tab, on_schedule_type_changed, schedule_hint_text
from .tab_algorithm import create_algorithm_tab
from .tab_basic import create_basic_tab
from .tab_management import create_management_tab
from .tab_processing import create_processing_tab


class SettingsPanel(QWidget):
    """
    Tabbed settings panel for all application settings.

    v9.0 Redesign: 11 tabs consolidated into 5 logical groups.

    Signals:
        settings_changed: Emitted when any setting changes
        preview_requested: Emitted when preview is requested
    """

    settings_changed = pyqtSignal(AppSettings)
    preview_requested = pyqtSignal()

    def __init__(self, settings: Optional[AppSettings] = None, parent=None):
        super().__init__(parent)
        self._settings = settings or AppSettings()
        self._block_signals = False
        self._is_form_valid = True
        self._translator = get_translator()
        self._setup_ui()
        self._load_settings(self._settings)
        self.retranslate_ui()
        self._translator.add_language_change_listener(self._on_runtime_language_changed)
        self.destroyed.connect(self._remove_language_listener)

    def _setup_ui(self):
        setup_ui(self)
        # Apply simple-mode visibility after all tabs exist.
        simple = bool(getattr(getattr(self._settings, "ui", None), "simple_mode", True))
        self.apply_simple_mode(simple)

    def apply_simple_mode(self, enabled: bool) -> None:
        """Hide advanced tabs when simple mode is on (keep Basic tab)."""
        if not hasattr(self, "tab_widget") or self.tab_widget is None:
            return
        # Tab order: 0=basic, 1=algorithm, 2=processing, 3=management, 4=ai
        for index in range(1, self.tab_widget.count()):
            self.tab_widget.setTabVisible(index, not bool(enabled))
        if enabled and self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)

    def _on_simple_mode_toggled(self, checked: bool = False) -> None:
        if self._block_signals:
            return
        self.apply_simple_mode(bool(checked))
        self._on_setting_changed()

    def _make_scrollable_tab(self, content_widget: QWidget) -> QWidget:
        return make_scrollable_tab(self, content_widget)

    def _create_basic_tab(self):
        """Create consolidated basic settings tab (post-processing + UI + output + filter)."""
        return create_basic_tab(self)


    def _create_algorithm_tab(self):
        """Create algorithm settings tab."""
        return create_algorithm_tab(self)


    # NOTE: _create_output_tab and _create_filter_tab removed.
    # Content moved into _create_basic_tab as CollapsibleSections.

    def _create_processing_tab(self):
        """Create consolidated processing tab (watermark + resize + advanced)."""
        return create_processing_tab(self)


    def _create_management_tab(self):
        """Create consolidated management tab (automation + file management + performance)."""
        return create_management_tab(self)


    def _remove_language_listener(self, *_args):
        try:
            self._translator.remove_language_change_listener(
                self._on_runtime_language_changed
            )
        except Exception:
            pass

    def _on_runtime_language_changed(self, _language: str):
        self.retranslate_ui()
        self._refresh_category_folder_defaults()
        self._apply_validation_state()

    def _set_line_edit_error(self, widget: QLineEdit, is_invalid: bool) -> None:
        if is_invalid:
            widget.setStyleSheet(
                "QLineEdit { border: 1px solid #cf222e; border-radius: 4px; }"
            )
        else:
            widget.setStyleSheet("")

    def _validate_form_inputs(self) -> bool:
        return validate_form_inputs(self)

    def _apply_validation_state(self) -> None:
        return apply_validation_state(self)

    def _on_setting_changed(self):
        """Handle any setting change."""
        if self._block_signals:
            return

        # Update sharpening value label
        sharpening_val = self.sharpening_slider.value() / 10.0
        self.sharpening_value.setText(f"{sharpening_val:.1f}")

        self._emit_settings()

    def _on_canny_changed(self):
        """Handle Canny slider changes."""
        if self._block_signals:
            return

        self.canny_min_label.setText(str(self.canny_min_slider.value()))
        self.canny_max_label.setText(str(self.canny_max_slider.value()))
        self._emit_settings()

    def _on_scene_preset_changed(self, index: int = 0):
        """Apply a scene preset to algorithm (and multi-photo) settings."""
        if self._block_signals:
            return
        if not hasattr(self, "scene_preset_combo"):
            return
        from ....core.scene_presets import apply_scene_preset

        scene_id = self.scene_preset_combo.currentData()
        if not scene_id or scene_id == "custom":
            self._emit_settings()
            return

        current = self._build_settings() if self._is_form_valid else self._settings
        updated = apply_scene_preset(current, str(scene_id))
        # Reload UI controls from updated settings (keeps other tabs intact).
        self._block_signals = True
        try:
            self._load_settings(updated)
            # Restore selected preset after load (load may not know about it).
            for i in range(self.scene_preset_combo.count()):
                if self.scene_preset_combo.itemData(i) == scene_id:
                    self.scene_preset_combo.setCurrentIndex(i)
                    break
        finally:
            self._block_signals = False
        self._settings = updated
        self.settings_changed.emit(updated)
        if hasattr(self, "auto_preview_check") and self.auto_preview_check.isChecked():
            self.preview_requested.emit()

    def _on_format_changed(self, format_name: str):
        """Handle output format change."""
        is_png = format_name.upper() == "PNG"
        self.quality_spin.setEnabled(not is_png)
        self.png_compression_spin.setEnabled(is_png)
        self._on_setting_changed()

    def _on_filter_changed(self):
        """Handle filter checkbox change."""
        self.min_size_spin.setEnabled(self.skip_small_check.isChecked())
        self._on_setting_changed()

    def _emit_settings(self):
        """Build and emit current settings."""
        if not self._validate_form_inputs():
            return
        settings = self._build_settings()
        self._settings = settings
        self.settings_changed.emit(settings)

        # Auto preview if enabled
        if self.auto_preview_check.isChecked():
            self.preview_requested.emit()

    def _build_settings(self) -> AppSettings:
        return build_settings(self)

    def _load_settings(self, settings: AppSettings):
        return load_settings(self, settings)


    def _browse_watermark_font(self):

        """Browse for a font file (.ttf/.otf) for Unicode watermark rendering."""

        try:

            path, _ = QFileDialog.getOpenFileName(

                self,

                t("settings.watermark_font.dialog_title"),

                "",

                "Font Files (*.ttf *.otf);;All Files (*)",

            )

            if path:

                self.watermark_font_path_edit.setText(path)

        except Exception:

            pass



    def _browse_debug_output_dir(self):

        """Browse for a directory to store detection debug artifacts."""

        try:

            path = QFileDialog.getExistingDirectory(

                self,

                t("settings.debug_output_dir.dialog_title"),

                "",

            )

            if path:

                self.debug_output_dir_edit.setText(path)

        except Exception:

            pass

    def _refresh_category_folder_defaults(self):
        defaults = get_category_folder_defaults()
        labels = {
            "portrait": t("settings.classification_folder.portrait"),
            "landscape": t("settings.classification_folder.landscape"),
            "document": t("settings.classification_folder.document"),
            "blackwhite": t("settings.classification_folder.blackwhite"),
            "other": t("settings.classification_folder.other"),
        }
        for key in CLASSIFICATION_CATEGORY_KEYS:
            widget = self.classification_folder_inputs.get(key)
            if widget is None:
                continue
            widget.setPlaceholderText(str(defaults.get(key, key)))
            label_widget = self.classification_folder_form.labelForField(widget)
            if label_widget is not None:
                label_widget.setText(labels.get(key, key))

    def retranslate_ui(self):
        return retranslate_panel(self)

    def _on_language_changed(self, index: int):

        """Handle language selection change."""

        lang_code = self.language_combo.itemData(index)

        if lang_code:

            from ....i18n.catalog import set_language

            set_language(lang_code)
            self.retranslate_ui()
            self._on_setting_changed()



    def _create_ai_settings_tab(self):
        """Create v9.0 AI settings tab."""
        return create_ai_settings_tab(self)


    @staticmethod
    def _schedule_hint_text(schedule_type: str) -> str:
        return schedule_hint_text(schedule_type)


    def _on_schedule_type_changed(self, schedule_type: str):
        """Handle schedule type change to show/hide relevant controls."""
        return on_schedule_type_changed(self, schedule_type)


    # ========================================
    # Updated _build_settings for v8.0
    # ========================================

    def _build_settings_v8(self) -> AppSettings:
        return build_settings_v8(self)

    def _load_settings_v8(self, settings: AppSettings):
        return load_settings_v8(self, settings)

    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings

    @settings.setter
    def settings(self, value: AppSettings):
        """Set and load settings."""
        self._settings = value
        self._load_settings(value)
        self._load_settings_v8(value)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._load_settings(AppSettings())
        self._load_settings_v8(AppSettings())
        self._emit_settings()
