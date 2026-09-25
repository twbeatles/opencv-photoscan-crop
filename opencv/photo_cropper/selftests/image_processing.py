#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Image processing self-tests (facade): compatibility facade re-exporting the split modules."""

from __future__ import annotations

from .extract_contour import (
    _test_manual_extract_session_runner_empty,
    _test_contour_utils_roundtrip,
    _test_manual_preview_shared_crop_mode,
    _test_find_best_contour_uses_score_edge_map,
    _test_accurate_mode_global_rerank_prefers_best_stage,
)
from .detect_accuracy import (
    _test_crop_accuracy_synthetic,
    _test_order_points_rotated_quad_stable,
    _test_scene_preset_album_enables_multi,
    _test_crop_accuracy_hard_scenarios,
    _test_detection_pipeline_composition,
    _test_nms_and_snap_helpers,
    _test_no_photo_false_positive_regression,
)
from .io_enhance import (
    _test_unicode_text_watermark,
    _test_grayscale_image_watermark_regression,
    _test_perspective_toggle_warp_vs_axis_crop,
    _test_save_image_fallback_and_metadata_best_effort,
    _test_resize_fill_no_upscale_boundary,
    _test_recursive_output_paths_preserve_relative_dirs,
    _test_unicode_image_io_helper_and_blank_path_guards,
    _test_history_record_applied_and_merge,
    _test_exif_orientation_normalization,
    _test_max_image_size_limit_applied,
)
from .preview_face_bench import (
    _test_preview_widget_contour_redraw_variants,
    _test_preview_single_pass,
    _test_face_dnn_fallback_when_download_fails,
    _test_face_rotation_uses_primary_face,
    _test_benchmark_harness_report_contract,
)

__all__ = [
    "_test_manual_extract_session_runner_empty",
    "_test_contour_utils_roundtrip",
    "_test_manual_preview_shared_crop_mode",
    "_test_find_best_contour_uses_score_edge_map",
    "_test_accurate_mode_global_rerank_prefers_best_stage",
    "_test_crop_accuracy_synthetic",
    "_test_order_points_rotated_quad_stable",
    "_test_scene_preset_album_enables_multi",
    "_test_crop_accuracy_hard_scenarios",
    "_test_detection_pipeline_composition",
    "_test_nms_and_snap_helpers",
    "_test_no_photo_false_positive_regression",
    "_test_unicode_text_watermark",
    "_test_grayscale_image_watermark_regression",
    "_test_perspective_toggle_warp_vs_axis_crop",
    "_test_save_image_fallback_and_metadata_best_effort",
    "_test_resize_fill_no_upscale_boundary",
    "_test_recursive_output_paths_preserve_relative_dirs",
    "_test_unicode_image_io_helper_and_blank_path_guards",
    "_test_history_record_applied_and_merge",
    "_test_exif_orientation_normalization",
    "_test_max_image_size_limit_applied",
    "_test_preview_widget_contour_redraw_variants",
    "_test_preview_single_pass",
    "_test_face_dnn_fallback_when_download_fails",
    "_test_face_rotation_uses_primary_face",
    "_test_benchmark_harness_report_contract",
]
