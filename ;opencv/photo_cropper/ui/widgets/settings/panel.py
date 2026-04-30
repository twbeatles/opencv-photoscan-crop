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
        """Setup the UI components with 5 consolidated tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 5 consolidated tabs (was 11)
        self._create_basic_tab()          # 📷 기본 (후처리 + UI + 출력 + 필터)
        self._create_algorithm_tab()      # 🔬 알고리즘
        self._create_processing_tab()     # 🔧 처리 (워터마크 + 리사이즈 + 고급)
        self._create_management_tab()     # 📂 관리 (자동화 + 파일관리 + 성능)
        self._create_ai_settings_tab()    # 🤖 AI

    def _make_scrollable_tab(self, content_widget: QWidget) -> QWidget:
        """Wrap widget in a scroll area for tab content."""
        scroll = QScrollArea()
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Style the scroll area to be transparent
        scroll.setStyleSheet("background: transparent;")

        return scroll

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

    def _apply_validation_state(self) -> None:
        self.naming_validation_label.setText(t("settings.validation.naming"))
        self.classification_validation_label.setText(t("settings.validation.classification"))
        self._validate_form_inputs()

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
        """Build AppSettings from current UI state."""
        algorithm = AlgorithmSettings(
            detection_mode=getattr(self, "detect_mode_combo", None)
            and self.detect_mode_combo.currentText()
            or "balanced",
            canny_min=self.canny_min_slider.value(),
            canny_max=self.canny_max_slider.value(),
            use_clahe=self.use_clahe_check.isChecked(),
            clahe_clip_limit=self.clahe_clip_spin.value(),
            clahe_grid_size=self.clahe_grid_spin.value(),
            multi_scale_edge=self.multi_scale_check.isChecked(),
            use_corner_detection=self.corner_detection_check.isChecked(),
            contour_scoring=self.scoring_combo.currentText(),
            min_area_ratio=self.min_area_ratio_spin.value(),
            max_area_ratio=self.max_area_ratio_spin.value(),
            bg_mask_delta=self.bg_mask_delta_spin.value(),
            adaptive_block_size=self.adaptive_block_size_spin.value(),
            adaptive_c=self.adaptive_c_spin.value(),
        )

        processing = ProcessingSettings(
            auto_contrast=self.auto_contrast_check.isChecked(),
            to_grayscale=self.grayscale_check.isChecked(),
            apply_sharpening=self.sharpening_check.isChecked(),
            sharpening_strength=self.sharpening_slider.value() / 10.0,
            denoise=self.denoise_check.isChecked(),
        )

        output = OutputSettings(
            output_format=self.format_combo.currentText(),
            jpg_quality=self.quality_spin.value(),
            png_compression=self.png_compression_spin.value(),
            webp_quality=self.quality_spin.value(),  # Use same quality value as JPG
            add_timestamp=self.timestamp_check.isChecked(),
            preserve_metadata=self.preserve_metadata_check.isChecked(),
        )

        filter_settings = FilterSettings(
            skip_small_images=self.skip_small_check.isChecked(),
            min_image_size=self.min_size_spin.value(),
            skip_processed=self.skip_processed_check.isChecked(),
        )

        # Safe language reference - widget may not exist yet during init
        language = "ko"
        if hasattr(self, "language_combo") and self.language_combo is not None:
            language = (
                self.language_combo.itemData(self.language_combo.currentIndex()) or "ko"
            )

        ui = UISettings(
            theme=self.theme_combo.currentText(),
            language=language,
            auto_preview=self.auto_preview_check.isChecked(),
            show_contour_overlay=self.contour_overlay_check.isChecked(),
        )

        debug = DebugSettings(
            enabled=getattr(self, "debug_detect_check", None)
            and self.debug_detect_check.isChecked()
            or False,
            output_dir=getattr(self, "debug_output_dir_edit", None)
            and self.debug_output_dir_edit.text().strip()
            or "",
        )

        # v8.5 settings
        watermark = WatermarkSettings(
            enabled=self.watermark_enable_check.isChecked(),
            text=self.watermark_text_edit.text(),
            text_font_path=getattr(self, "watermark_font_path_edit", None)
            and self.watermark_font_path_edit.text().strip()
            or "",
            text_font_scale=self.watermark_font_spin.value(),
            opacity=self.watermark_opacity_spin.value() / 100.0,
            position=self.watermark_position_combo.currentText(),
            text_shadow=self.watermark_shadow_check.isChecked(),
            tiled=self.watermark_tiled_check.isChecked(),
            tile_spacing=self.watermark_spacing_spin.value(),
        )

        resize = ResizeSettings(
            enabled=self.resize_enable_check.isChecked(),
            mode=self.resize_mode_combo.currentText(),
            width=self.resize_width_spin.value(),
            height=self.resize_height_spin.value(),
            percentage=float(self.resize_percent_spin.value()),
            max_dimension=self.resize_max_dim_spin.value(),
            maintain_aspect=self.resize_aspect_check.isChecked(),
            upscale_allowed=self.resize_upscale_check.isChecked(),
        )

        # Build watch_mode with scheduler fields
        scheduler_check = getattr(self, "scheduler_enable_check", None)
        schedule_type_combo = getattr(self, "schedule_type_combo", None)
        schedule_time_edit = getattr(self, "schedule_time_edit", None)
        schedule_interval_spin = getattr(self, "schedule_interval_spin", None)
        watch_mode = WatchModeSettings(
            enabled=self.watch_mode_check.isChecked(),
            recursive=self.watch_recursive_check.isChecked(),
            debounce_ms=self.watch_delay_spin.value(),
            max_wait_seconds=float(
                self.watch_max_wait_spin.value()
                if hasattr(self, "watch_max_wait_spin")
                else 30.0
            ),
            scheduler_enabled=bool(
                scheduler_check.isChecked() if scheduler_check is not None else False
            ),
            schedule_type=(
                schedule_type_combo.currentText()
                if schedule_type_combo is not None
                else "interval"
            ),
            schedule_time=(
                schedule_time_edit.text()
                if schedule_time_edit is not None
                else "00:00"
            ),
            schedule_interval_minutes=(
                int(schedule_interval_spin.value())
                if schedule_interval_spin is not None
                else 60
            ),
        )

        prev_multi_photo = getattr(self._settings, "multi_photo", MultiPhotoSettings())
        multi_photo = MultiPhotoSettings(
            enabled=self.multi_photo_enable_check.isChecked()
            if hasattr(self, "multi_photo_enable_check")
            else bool(getattr(prev_multi_photo, "enabled", False)),
            min_photos=int(getattr(prev_multi_photo, "min_photos", 1)),
            max_photos=int(getattr(prev_multi_photo, "max_photos", 20)),
            min_area_ratio=float(getattr(prev_multi_photo, "min_area_ratio", 0.02)),
            max_area_ratio=float(getattr(prev_multi_photo, "max_area_ratio", 0.8)),
            merge_distance=self.multi_photo_merge_distance_spin.value()
            if hasattr(self, "multi_photo_merge_distance_spin")
            else int(getattr(prev_multi_photo, "merge_distance", 50)),
            separate_output_folders=self.multi_photo_separate_folders_check.isChecked()
            if hasattr(self, "multi_photo_separate_folders_check")
            else bool(getattr(prev_multi_photo, "separate_output_folders", False)),
        )

        # v8.0 Advanced settings - safely build if widgets exist
        advanced = AdvancedProcessingSettings()
        if hasattr(self, "auto_deskew_check"):
            advanced = AdvancedProcessingSettings(
                auto_deskew=self.auto_deskew_check.isChecked(),
                auto_color_correct=self.auto_color_check.isChecked(),
                color_correct_method=self.color_method_combo.currentText(),
                perspective_correct=self.perspective_check.isChecked(),
                enhanced_denoise=self.enhanced_denoise_check.isChecked(),
                enhanced_denoise_strength=self.enhanced_denoise_spin.value(),
                restore_old_photo=self.restore_old_check.isChecked(),
                enhanced_sharpen=self.enhanced_sharpen_check.isChecked(),
                auto_crop_borders=self.auto_crop_border_check.isChecked(),
            )

        # v8.0 File management settings
        file_management = FileManagementSettings()
        if hasattr(self, "recursive_check"):
            file_management = FileManagementSettings(
                recursive_search=self.recursive_check.isChecked(),
                use_naming_rules=self.use_naming_rules_check.isChecked(),
                naming_prefix=self.naming_prefix_edit.text(),
                naming_suffix=self.naming_suffix_edit.text(),
                naming_use_counter=self.naming_counter_check.isChecked(),
                naming_use_date=self.naming_date_check.isChecked(),
                move_failed_files=self.move_failed_check.isChecked(),
                copy_failed_instead_of_move=self.copy_failed_check.isChecked(),
                enable_logging=self.enable_log_check.isChecked(),
                log_format=self.log_format_combo.currentText(),
            )

        # v9.x Performance settings (management tab controls)
        prev_perf = getattr(self._settings, "performance", PerformanceSettings())
        thread_count = max(1, int(self.max_threads_spin.value()))
        low_mem_mode = self.low_mem_check.isChecked()
        performance = PerformanceSettings(
            use_gpu=getattr(prev_perf, "use_gpu", False),
            gpu_device_id=getattr(prev_perf, "gpu_device_id", 0),
            enable_multithreading=thread_count > 1,
            thread_count=thread_count,
            max_image_size_mb=50 if low_mem_mode else 100,
            downscale_large_images=True,
            downscale_threshold_mp=24.0 if low_mem_mode else 50.0,
        )

        # v9.0 Classification settings
        prev_cls = getattr(self._settings, "classification", ClassificationSettings())
        classification = ClassificationSettings()
        if hasattr(self, "classification_enable_check"):
            category_folders = dict(getattr(prev_cls, "category_folders", {}) or {})
            folder_inputs = getattr(self, "classification_folder_inputs", {}) or {}
            if isinstance(folder_inputs, dict):
                for key in CLASSIFICATION_CATEGORY_KEYS:
                    widget = folder_inputs.get(key)
                    if widget is None:
                        continue
                    value = str(widget.text() if hasattr(widget, "text") else "").strip()
                    category_folders[key] = value
            classification = ClassificationSettings(
                enabled=self.classification_enable_check.isChecked(),
                model=self.classification_model_combo.currentText()
                if hasattr(self, "classification_model_combo")
                else "basic",
                auto_folder=self.classification_subfolders_check.isChecked(),
                categories_enabled=dict(
                    getattr(prev_cls, "categories_enabled", {}) or {}
                ),
                category_folders=category_folders,
                min_confidence=float(getattr(prev_cls, "min_confidence", 0.5)),
            )

        # v9.0 Face detection settings
        prev_face = getattr(self._settings, "face_detection", FaceDetectionSettings())
        face_detection = FaceDetectionSettings()
        if hasattr(self, "face_detect_enable_check"):
            face_detection = FaceDetectionSettings(
                enabled=self.face_detect_enable_check.isChecked(),
                use_dnn=self.face_use_dnn_check.isChecked()
                if hasattr(self, "face_use_dnn_check")
                else False,
                auto_rotate=self.face_auto_orient_check.isChecked(),
                auto_center_crop=self.face_enhance_check.isChecked(),
                show_overlay=bool(getattr(prev_face, "show_overlay", True)),
                detect_eyes=bool(getattr(prev_face, "detect_eyes", True)),
                min_face_size=self.face_min_size_spin.value()
                if hasattr(self, "face_min_size_spin")
                else 30,
            )

        # v9.0 Smart enhancement settings
        prev_smart = getattr(
            self._settings, "smart_enhancement", SmartEnhancementSettings()
        )
        smart_enhancement = SmartEnhancementSettings()
        if hasattr(self, "smart_enhance_enable_check"):
            smart_enhancement = SmartEnhancementSettings(
                enabled=self.smart_enhance_enable_check.isChecked(),
                auto_preset=bool(getattr(prev_smart, "auto_preset", True)),
                default_preset=str(getattr(prev_smart, "default_preset", "none")),
                apply_to_batch=bool(getattr(prev_smart, "apply_to_batch", True)),
                adjust_exposure=self.smart_exposure_check.isChecked()
                if hasattr(self, "smart_exposure_check")
                else True,
                adjust_color_balance=self.smart_color_balance_check.isChecked()
                if hasattr(self, "smart_color_balance_check")
                else True,
                strength=self.smart_strength_spin.value()
                if hasattr(self, "smart_strength_spin")
                else 50,
            )

        # v9.0 Notification settings
        notification = NotificationSettings()
        if hasattr(self, "notification_enable_check"):
            notification = NotificationSettings(
                enabled=self.notification_enable_check.isChecked(),
                play_sound=self.notification_sound_check.isChecked(),
                on_error=self.notification_error_only_check.isChecked(),
            )

        return AppSettings(
            algorithm=algorithm,
            processing=processing,
            output=output,
            filter=filter_settings,
            ui=ui,
            debug=debug,
            advanced=advanced,
            file_management=file_management,
            performance=performance,
            watermark=watermark,
            resize=resize,
            watch_mode=watch_mode,
            multi_photo=multi_photo,
            classification=classification,
            face_detection=face_detection,
            smart_enhancement=smart_enhancement,
            notification=notification,
            create_backup=self.backup_original_check.isChecked(),
        )

    def _load_settings(self, settings: AppSettings):
        """Load settings into UI."""
        self._block_signals = True

        # Algorithm
        self.canny_min_slider.setValue(settings.algorithm.canny_min)
        self.canny_max_slider.setValue(settings.algorithm.canny_max)
        self.canny_min_label.setText(str(settings.algorithm.canny_min))
        self.canny_max_label.setText(str(settings.algorithm.canny_max))
        self.use_clahe_check.setChecked(settings.algorithm.use_clahe)
        self.clahe_clip_spin.setValue(settings.algorithm.clahe_clip_limit)
        self.clahe_grid_spin.setValue(settings.algorithm.clahe_grid_size)
        self.multi_scale_check.setChecked(settings.algorithm.multi_scale_edge)
        self.corner_detection_check.setChecked(settings.algorithm.use_corner_detection)
        index = self.scoring_combo.findText(settings.algorithm.contour_scoring)
        if index >= 0:
            self.scoring_combo.setCurrentIndex(index)
        if hasattr(self, "min_area_ratio_spin"):
            self.min_area_ratio_spin.setValue(float(settings.algorithm.min_area_ratio))
        if hasattr(self, "max_area_ratio_spin"):
            self.max_area_ratio_spin.setValue(float(settings.algorithm.max_area_ratio))
        if hasattr(self, "bg_mask_delta_spin"):
            self.bg_mask_delta_spin.setValue(
                float(getattr(settings.algorithm, "bg_mask_delta", 30.0))
            )
        if hasattr(self, "adaptive_block_size_spin"):
            self.adaptive_block_size_spin.setValue(
                int(getattr(settings.algorithm, "adaptive_block_size", 15))
            )
        if hasattr(self, "adaptive_c_spin"):
            self.adaptive_c_spin.setValue(
                float(getattr(settings.algorithm, "adaptive_c", 4.0))
            )

        if hasattr(self, "detect_mode_combo"):
            idx = self.detect_mode_combo.findText(getattr(settings.algorithm, "detection_mode", "balanced"))
            if idx >= 0:
                self.detect_mode_combo.setCurrentIndex(idx)

        if hasattr(self, "debug_detect_check") and hasattr(settings, "debug"):
            self.debug_detect_check.setChecked(bool(settings.debug.enabled))
        if hasattr(self, "debug_output_dir_edit") and hasattr(settings, "debug"):
            self.debug_output_dir_edit.setText(getattr(settings.debug, "output_dir", "") or "")

        # Processing
        self.auto_contrast_check.setChecked(settings.processing.auto_contrast)
        self.grayscale_check.setChecked(settings.processing.to_grayscale)
        self.sharpening_check.setChecked(settings.processing.apply_sharpening)
        self.sharpening_slider.setValue(
            int(settings.processing.sharpening_strength * 10)
        )
        self.sharpening_value.setText(f"{settings.processing.sharpening_strength:.1f}")
        self.denoise_check.setChecked(settings.processing.denoise)

        # Output
        index = self.format_combo.findText(settings.output.output_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.quality_spin.setValue(settings.output.jpg_quality)
        self.png_compression_spin.setValue(settings.output.png_compression)
        self.timestamp_check.setChecked(settings.output.add_timestamp)
        self.preserve_metadata_check.setChecked(
            bool(getattr(settings.output, "preserve_metadata", False))
        )

        # Filter
        self.skip_small_check.setChecked(settings.filter.skip_small_images)
        self.min_size_spin.setValue(settings.filter.min_image_size)
        self.min_size_spin.setEnabled(settings.filter.skip_small_images)
        self.skip_processed_check.setChecked(settings.filter.skip_processed)

        # UI
        index = self.theme_combo.findText(settings.ui.theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.auto_preview_check.setChecked(settings.ui.auto_preview)
        self.contour_overlay_check.setChecked(settings.ui.show_contour_overlay)

        # Language
        if hasattr(settings.ui, "language"):
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == settings.ui.language:
                    self.language_combo.setCurrentIndex(i)
                    break

        # Misc
        self.backup_original_check.setChecked(settings.create_backup)

        # Format-dependent enables
        is_png = settings.output.output_format.upper() == "PNG"
        self.quality_spin.setEnabled(not is_png)
        self.png_compression_spin.setEnabled(is_png)

        # v8.5 Watermark settings
        if hasattr(settings, "watermark"):
            wm = settings.watermark
            self.watermark_enable_check.setChecked(wm.enabled)
            self.watermark_text_edit.setText(wm.text)
            if hasattr(self, "watermark_font_path_edit"):
                self.watermark_font_path_edit.setText(getattr(wm, "text_font_path", ""))
            self.watermark_font_spin.setValue(wm.text_font_scale)
            self.watermark_opacity_spin.setValue(int(wm.opacity * 100))
            idx = self.watermark_position_combo.findText(wm.position)
            if idx >= 0:
                self.watermark_position_combo.setCurrentIndex(idx)
            self.watermark_shadow_check.setChecked(wm.text_shadow)
            self.watermark_tiled_check.setChecked(wm.tiled)
            self.watermark_spacing_spin.setValue(wm.tile_spacing)

        # v8.5 Resize settings
        if hasattr(settings, "resize"):
            rs = settings.resize
            self.resize_enable_check.setChecked(rs.enabled)
            idx = self.resize_mode_combo.findText(rs.mode)
            if idx >= 0:
                self.resize_mode_combo.setCurrentIndex(idx)
            self.resize_width_spin.setValue(rs.width)
            self.resize_height_spin.setValue(rs.height)
            self.resize_percent_spin.setValue(int(rs.percentage))
            self.resize_max_dim_spin.setValue(rs.max_dimension)
            self.resize_aspect_check.setChecked(rs.maintain_aspect)
            self.resize_upscale_check.setChecked(rs.upscale_allowed)

        # v8.5 Watch mode settings
        if hasattr(settings, "watch_mode"):
            wm = settings.watch_mode
            self.watch_mode_check.setChecked(wm.enabled)
            self.watch_recursive_check.setChecked(wm.recursive)
            self.watch_delay_spin.setValue(wm.debounce_ms)
            if hasattr(self, "watch_max_wait_spin"):
                self.watch_max_wait_spin.setValue(
                    float(getattr(wm, "max_wait_seconds", 30.0))
                )
            if hasattr(self, "scheduler_enable_check"):
                self.scheduler_enable_check.setChecked(
                    bool(getattr(wm, "scheduler_enabled", False))
                )
            if hasattr(self, "schedule_type_combo"):
                idx = self.schedule_type_combo.findText(
                    str(getattr(wm, "schedule_type", "interval") or "interval")
                )
                if idx >= 0:
                    self.schedule_type_combo.setCurrentIndex(idx)
            if hasattr(self, "schedule_time_edit"):
                self.schedule_time_edit.setText(
                    str(getattr(wm, "schedule_time", "00:00") or "00:00")
                )
            if hasattr(self, "schedule_interval_spin"):
                self.schedule_interval_spin.setValue(
                    int(getattr(wm, "schedule_interval_minutes", 60) or 60)
                )
            if hasattr(self, "schedule_type_combo"):
                self._on_schedule_type_changed(self.schedule_type_combo.currentText())

        if hasattr(settings, "multi_photo"):
            mp = settings.multi_photo
            if hasattr(self, "multi_photo_enable_check"):
                self.multi_photo_enable_check.setChecked(bool(mp.enabled))
            if hasattr(self, "multi_photo_merge_distance_spin"):
                self.multi_photo_merge_distance_spin.setValue(
                    int(getattr(mp, "merge_distance", 50))
                )
            if hasattr(self, "multi_photo_separate_folders_check"):
                self.multi_photo_separate_folders_check.setChecked(
                    bool(getattr(mp, "separate_output_folders", False))
                )

        # v9.0 AI settings
        if hasattr(settings, "classification"):
            cs = settings.classification
            self.classification_enable_check.setChecked(cs.enabled)
            self.classification_subfolders_check.setChecked(cs.auto_folder)
            if hasattr(self, "classification_model_combo"):
                idx = self.classification_model_combo.findText(
                    getattr(cs, "model", "basic")
                )
                if idx >= 0:
                    self.classification_model_combo.setCurrentIndex(idx)
            folder_inputs = getattr(self, "classification_folder_inputs", {}) or {}
            folder_map = dict(getattr(cs, "category_folders", {}) or {})
            for key in CLASSIFICATION_CATEGORY_KEYS:
                widget = folder_inputs.get(key) if isinstance(folder_inputs, dict) else None
                if widget is None:
                    continue
                widget.setText(str(folder_map.get(key, "") or ""))

        if hasattr(settings, "face_detection"):
            fd = settings.face_detection
            self.face_detect_enable_check.setChecked(fd.enabled)
            if hasattr(self, "face_use_dnn_check"):
                self.face_use_dnn_check.setChecked(getattr(fd, "use_dnn", False))
            self.face_auto_orient_check.setChecked(fd.auto_rotate)
            self.face_enhance_check.setChecked(fd.auto_center_crop)
            if hasattr(self, "face_min_size_spin"):
                self.face_min_size_spin.setValue(
                    int(getattr(fd, "min_face_size", 30))
                )

        if hasattr(settings, "smart_enhancement"):
            se = settings.smart_enhancement
            self.smart_enhance_enable_check.setChecked(se.enabled)
            if hasattr(self, "smart_exposure_check"):
                self.smart_exposure_check.setChecked(
                    bool(getattr(se, "adjust_exposure", True))
                )
            if hasattr(self, "smart_color_balance_check"):
                self.smart_color_balance_check.setChecked(
                    bool(getattr(se, "adjust_color_balance", True))
                )
            if hasattr(self, "smart_strength_spin"):
                self.smart_strength_spin.setValue(int(getattr(se, "strength", 50)))

        if hasattr(settings, "notification"):
            ns = settings.notification
            self.notification_enable_check.setChecked(ns.enabled)
            self.notification_sound_check.setChecked(ns.play_sound)
            self.notification_error_only_check.setChecked(ns.on_error)

        # Performance (management tab)
        if hasattr(settings, "performance"):
            perf = settings.performance
            self.max_threads_spin.setValue(max(1, int(perf.thread_count)))
            low_mem_mode = (
                int(getattr(perf, "max_image_size_mb", 100)) <= 50
                or float(getattr(perf, "downscale_threshold_mp", 50.0)) <= 24.0
            )
            self.low_mem_check.setChecked(low_mem_mode)

        self._block_signals = False
        self._refresh_category_folder_defaults()
        self._apply_validation_state()


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
        """Build v8.0 settings from UI."""
        # Build base settings first
        settings = self._build_settings()

        # Add v8.0 advanced settings
        settings.advanced = AdvancedProcessingSettings(
            auto_deskew=self.auto_deskew_check.isChecked(),
            auto_color_correct=self.auto_color_check.isChecked(),
            color_correct_method=self.color_method_combo.currentText(),
            perspective_correct=self.perspective_check.isChecked(),
            enhanced_denoise=self.enhanced_denoise_check.isChecked(),
            enhanced_denoise_strength=self.enhanced_denoise_spin.value(),
            restore_old_photo=self.restore_old_check.isChecked(),
            enhanced_sharpen=self.enhanced_sharpen_check.isChecked(),
            auto_crop_borders=self.auto_crop_border_check.isChecked(),
        )

        # Add file management settings
        settings.file_management = FileManagementSettings(
            recursive_search=self.recursive_check.isChecked(),
            use_naming_rules=self.use_naming_rules_check.isChecked(),
            naming_prefix=self.naming_prefix_edit.text(),
            naming_suffix=self.naming_suffix_edit.text(),
            naming_use_counter=self.naming_counter_check.isChecked(),
            naming_use_date=self.naming_date_check.isChecked(),
            move_failed_files=self.move_failed_check.isChecked(),
            copy_failed_instead_of_move=self.copy_failed_check.isChecked(),
            enable_logging=self.enable_log_check.isChecked(),
            log_format=self.log_format_combo.currentText(),
        )

        # Add performance settings
        low_mem_mode = self.low_mem_check.isChecked()
        settings.performance = PerformanceSettings(
            use_gpu=getattr(settings.performance, "use_gpu", False),
            gpu_device_id=getattr(settings.performance, "gpu_device_id", 0),
            enable_multithreading=self.max_threads_spin.value() > 1,
            thread_count=self.max_threads_spin.value(),
            max_image_size_mb=50 if low_mem_mode else 100,
            downscale_large_images=True,
            downscale_threshold_mp=24.0 if low_mem_mode else 50.0,
        )

        return settings

    def _load_settings_v8(self, settings: AppSettings):
        """Load v8.0 settings into UI."""
        # Advanced settings
        if hasattr(settings, "advanced"):
            adv = settings.advanced
            self.auto_deskew_check.setChecked(adv.auto_deskew)
            self.auto_color_check.setChecked(adv.auto_color_correct)
            idx = self.color_method_combo.findText(adv.color_correct_method)
            if idx >= 0:
                self.color_method_combo.setCurrentIndex(idx)
            self.perspective_check.setChecked(adv.perspective_correct)
            self.enhanced_denoise_check.setChecked(adv.enhanced_denoise)
            self.enhanced_denoise_spin.setValue(adv.enhanced_denoise_strength)
            self.restore_old_check.setChecked(adv.restore_old_photo)
            self.enhanced_sharpen_check.setChecked(adv.enhanced_sharpen)
            self.auto_crop_border_check.setChecked(adv.auto_crop_borders)

        # File management settings
        if hasattr(settings, "file_management"):
            fm = settings.file_management
            self.recursive_check.setChecked(fm.recursive_search)
            self.use_naming_rules_check.setChecked(fm.use_naming_rules)
            self.naming_prefix_edit.setText(fm.naming_prefix)
            self.naming_suffix_edit.setText(fm.naming_suffix)
            self.naming_counter_check.setChecked(fm.naming_use_counter)
            self.naming_date_check.setChecked(fm.naming_use_date)
            self.move_failed_check.setChecked(fm.move_failed_files)
            self.copy_failed_check.setChecked(fm.copy_failed_instead_of_move)
            self.enable_log_check.setChecked(fm.enable_logging)
            idx = self.log_format_combo.findText(fm.log_format)
            if idx >= 0:
                self.log_format_combo.setCurrentIndex(idx)

        # Performance settings
        if hasattr(settings, "performance"):
            perf = settings.performance
            if hasattr(self, "max_threads_spin"):
                self.max_threads_spin.setValue(max(1, int(perf.thread_count)))
            if hasattr(self, "low_mem_check"):
                self.low_mem_check.setChecked(
                    int(getattr(perf, "max_image_size_mb", 100)) <= 50
                    or float(getattr(perf, "downscale_threshold_mp", 50.0)) <= 24.0
                )

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
