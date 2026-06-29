#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Run the Photo Cropper self-test suite in the historical order."""

from __future__ import annotations

from .imports import (
    _test_crop_editor_import_smoke,
    _test_preview_worker_import_smoke,
    _test_ui_action_modules_import_smoke,
    _test_ui_canonical_package_import_smoke,
    _test_main_window_import_smoke,
    _test_manual_extract_service_import_smoke,
    _test_image_save_io_module_smoke,
    _test_watch_mode_coordinator_import_smoke,
)
from .watch_mode import (
    _test_watch_mode_coordinator_invalid_input,
    _test_watch_mode_coordinator_recursive_output_guard,
    _test_watch_mode_processing_disables_failed_file_move,
    _test_watch_process_single_preserves_stop_request,
    _test_recursive_watch_new_subdir_initial_scan,
    _test_folder_watcher_file_changed_requeues_only_on_signature_change,
    _test_watch_max_wait_roundtrip,
    _test_watch_callback_runs_on_background_worker,
    _test_watch_readiness_is_owned_by_auto_processor,
    _test_watch_actions_block_while_batch_or_manual_running,
    _test_batch_actions_block_when_watch_running,
    _test_scheduler_once_preserves_task_until_started,
    _test_scheduler_once_skip_keeps_next_run_due,
    _test_scheduled_batch_uses_task_paths,
    _test_folder_watcher_recursive_excluded_roots,
)
from .batch_cli import (
    _test_batch_session_service_smoke,
    _test_batch_session_service_reentry_guard,
    _test_boundary_failed_file_collection_helper,
    _test_boundary_failed_file_collection_prefers_relative_paths,
    _test_recursive_scan_excludes_internal_generated_dirs,
    _test_classify_failed_files_preserves_relative_dirs,
    _test_classify_failed_files_rejects_invalid_failed_folder,
    _test_cli_settings_merge_priority,
    _test_batch_thread_local_reuse,
    _test_batch_post_pipeline_order,
    _test_skip_processed_with_classification_subfolder,
    _test_cli_new_crop_options,
    _test_processed_index_roundtrip_and_source_change,
    _test_processed_index_backward_compat_and_partial_status,
    _test_retry_failed_files_normalizes_empty_output_path,
    _test_batch_actions_recursive_output_guard,
    _test_management_preflight_file_batch_guard,
    _test_profile_apply_rebuild_validation,
    _test_cli_cancel_exit_code_130,
    _test_cli_cancel_with_failed_still_returns_130,
    _test_cli_partial_exit_code_rules,
    _test_batch_fatal_error_and_cli_exit_code,
    _test_library_repository_singleton_reset,
    _test_ui_batch_completion_finalizes_in_background_and_clears_manual_state,
    _test_cli_recursive_output_guard,
    _test_cli_rejects_invalid_settings_segments,
    _test_processed_signature_includes_routing_and_backup,
    _test_output_reservation_is_thread_safe,
    _test_processing_logger_partial_summary,
)
from .settings_ui import (
    _test_classification_settings_custom_alias_normalizes_to_advanced,
    _test_settings_forward_compat,
    _test_settings_panel_performance_roundtrip,
    _test_settings_panel_classification_folder_roundtrip,
    _test_classification_folder_default_sentinel_migration,
    _test_settings_path_validation_blocks_invalid_segments,
    _test_settings_panel_legacy_custom_alias_and_schedule_once_hint,
    _test_i18n_catalog_placeholder_consistency,
    _test_settings_i18n_literal_binding_coverage,
    _test_settings_panel_ai_roundtrip,
    _test_settings_panel_algorithm_tuning_roundtrip,
)
from .image_processing import (
    _test_manual_extract_session_runner_empty,
    _test_contour_utils_roundtrip,
    _test_preview_widget_contour_redraw_variants,
    _test_manual_preview_shared_crop_mode,
    _test_unicode_text_watermark,
    _test_preview_single_pass,
    _test_perspective_toggle_warp_vs_axis_crop,
    _test_save_image_fallback_and_metadata_best_effort,
    _test_resize_fill_no_upscale_boundary,
    _test_recursive_output_paths_preserve_relative_dirs,
    _test_unicode_image_io_helper_and_blank_path_guards,
    _test_history_record_applied_and_merge,
    _test_crop_accuracy_synthetic,
    _test_no_photo_false_positive_regression,
    _test_grayscale_image_watermark_regression,
    _test_max_image_size_limit_applied,
    _test_face_dnn_fallback_when_download_fails,
    _test_face_rotation_uses_primary_face,
    _test_find_best_contour_uses_score_edge_map,
    _test_accurate_mode_global_rerank_prefers_best_stage,
    _test_exif_orientation_normalization,
    _test_benchmark_harness_report_contract,
)
from .multi_photo import (
    _test_multi_photo_merge_distance_and_separate_folders,
    _test_multi_photo_uses_shared_loader,
    _test_multi_photo_status_variants_and_partial_index_behavior,
    _test_multi_photo_close_gap_split,
    _test_multi_photo_merge_distance_effect,
    _test_multi_photo_perspective_crop_path,
)
from .library import (
    _test_sqlite_pragmas_and_ingest_cancel_progress,
    _test_library_catalog_import_and_duplicates,
    _test_library_search_and_collections,
    _test_duplicate_service_near_groups,
    _test_duplicate_preferences_preserved_on_rebuild,
    _test_source_relink_unique_and_ambiguous,
    _test_asset_query_filters_and_timeline,
    _test_library_sqlite_pragmas_and_invalid_sources,
    _test_search_index_dirty_and_rebuild,
    _test_timeline_review_query_not_limited_to_5000,
)
from .jobs_recipes import (
    _test_job_orchestrator_records_variants_and_review_queue,
    _test_recipe_determinism_and_preserved_global_state,
    _test_review_service_guard_and_reprocess_queue,
    _test_prepare_job_rerun_avoids_stale_queued_jobs_and_dedupes_sources,
    _test_job_finalization_prioritizes_fatal_error,
    _test_job_summary_metadata_warnings_and_near_summary,
)

TESTS = [
    _test_crop_editor_import_smoke,
    _test_preview_worker_import_smoke,
    _test_ui_action_modules_import_smoke,
    _test_ui_canonical_package_import_smoke,
    _test_main_window_import_smoke,
    _test_manual_extract_service_import_smoke,
    _test_batch_session_service_smoke,
    _test_batch_session_service_reentry_guard,
    _test_manual_extract_session_runner_empty,
    _test_image_save_io_module_smoke,
    _test_watch_mode_coordinator_import_smoke,
    _test_watch_mode_coordinator_invalid_input,
    _test_watch_mode_coordinator_recursive_output_guard,
    _test_watch_mode_processing_disables_failed_file_move,
    _test_watch_process_single_preserves_stop_request,
    _test_contour_utils_roundtrip,
    _test_preview_widget_contour_redraw_variants,
    _test_manual_preview_shared_crop_mode,
    _test_boundary_failed_file_collection_helper,
    _test_boundary_failed_file_collection_prefers_relative_paths,
    _test_recursive_scan_excludes_internal_generated_dirs,
    _test_classify_failed_files_preserves_relative_dirs,
    _test_classify_failed_files_rejects_invalid_failed_folder,
    _test_cli_settings_merge_priority,
    _test_classification_settings_custom_alias_normalizes_to_advanced,
    _test_settings_forward_compat,
    _test_unicode_text_watermark,
    _test_preview_single_pass,
    _test_batch_thread_local_reuse,
    _test_settings_panel_performance_roundtrip,
    _test_recursive_watch_new_subdir_initial_scan,
    _test_folder_watcher_file_changed_requeues_only_on_signature_change,
    _test_watch_max_wait_roundtrip,
    _test_watch_callback_runs_on_background_worker,
    _test_watch_readiness_is_owned_by_auto_processor,
    _test_batch_post_pipeline_order,
    _test_skip_processed_with_classification_subfolder,
    _test_perspective_toggle_warp_vs_axis_crop,
    _test_save_image_fallback_and_metadata_best_effort,
    _test_resize_fill_no_upscale_boundary,
    _test_multi_photo_merge_distance_and_separate_folders,
    _test_recursive_output_paths_preserve_relative_dirs,
    _test_multi_photo_uses_shared_loader,
    _test_multi_photo_status_variants_and_partial_index_behavior,
    _test_cli_new_crop_options,
    _test_processed_index_roundtrip_and_source_change,
    _test_processed_index_backward_compat_and_partial_status,
    _test_watch_actions_block_while_batch_or_manual_running,
    _test_batch_actions_block_when_watch_running,
    _test_retry_failed_files_normalizes_empty_output_path,
    _test_batch_actions_recursive_output_guard,
    _test_management_preflight_file_batch_guard,
    _test_profile_apply_rebuild_validation,
    _test_settings_panel_classification_folder_roundtrip,
    _test_classification_folder_default_sentinel_migration,
    _test_settings_path_validation_blocks_invalid_segments,
    _test_settings_panel_legacy_custom_alias_and_schedule_once_hint,
    _test_cli_cancel_exit_code_130,
    _test_cli_cancel_with_failed_still_returns_130,
    _test_cli_partial_exit_code_rules,
    _test_batch_fatal_error_and_cli_exit_code,
    _test_library_repository_singleton_reset,
    _test_ui_batch_completion_finalizes_in_background_and_clears_manual_state,
    _test_cli_recursive_output_guard,
    _test_unicode_image_io_helper_and_blank_path_guards,
    _test_cli_rejects_invalid_settings_segments,
    _test_processed_signature_includes_routing_and_backup,
    _test_output_reservation_is_thread_safe,
    _test_scheduler_once_preserves_task_until_started,
    _test_scheduler_once_skip_keeps_next_run_due,
    _test_scheduled_batch_uses_task_paths,
    _test_folder_watcher_recursive_excluded_roots,
    _test_sqlite_pragmas_and_ingest_cancel_progress,
    _test_i18n_catalog_placeholder_consistency,
    _test_settings_i18n_literal_binding_coverage,
    _test_history_record_applied_and_merge,
    _test_crop_accuracy_synthetic,
    _test_no_photo_false_positive_regression,
    _test_multi_photo_close_gap_split,
    _test_multi_photo_merge_distance_effect,
    _test_multi_photo_perspective_crop_path,
    _test_grayscale_image_watermark_regression,
    _test_max_image_size_limit_applied,
    _test_face_dnn_fallback_when_download_fails,
    _test_face_rotation_uses_primary_face,
    _test_find_best_contour_uses_score_edge_map,
    _test_accurate_mode_global_rerank_prefers_best_stage,
    _test_exif_orientation_normalization,
    _test_processing_logger_partial_summary,
    _test_settings_panel_ai_roundtrip,
    _test_settings_panel_algorithm_tuning_roundtrip,
    _test_benchmark_harness_report_contract,
    _test_library_catalog_import_and_duplicates,
    _test_job_orchestrator_records_variants_and_review_queue,
    _test_library_search_and_collections,
    _test_duplicate_service_near_groups,
    _test_duplicate_preferences_preserved_on_rebuild,
    _test_source_relink_unique_and_ambiguous,
    _test_recipe_determinism_and_preserved_global_state,
    _test_review_service_guard_and_reprocess_queue,
    _test_prepare_job_rerun_avoids_stale_queued_jobs_and_dedupes_sources,
    _test_job_finalization_prioritizes_fatal_error,
    _test_asset_query_filters_and_timeline,
    _test_library_sqlite_pragmas_and_invalid_sources,
    _test_search_index_dirty_and_rebuild,
    _test_timeline_review_query_not_limited_to_5000,
    _test_job_summary_metadata_warnings_and_near_summary,
]

def _select_tests(argv: list[str] | None = None) -> list:
    """Filter tests by function name (substring or exact match)."""
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        return list(TESTS)

    selected = []
    for test in TESTS:
        name = getattr(test, "__name__", "")
        if any(token in name for token in args):
            selected.append(test)
    return selected or list(TESTS)


def main(argv: list[str] | None = None) -> int:
    import traceback

    tests = _select_tests(argv)
    failures: list[str] = []

    for test in tests:
        name = getattr(test, "__name__", repr(test))
        print(f"RUN {name}")
        try:
            test()
        except Exception:
            print(f"FAIL {name}")
            traceback.print_exc()
            failures.append(name)

    if failures:
        print(f"SELFTEST FAILED ({len(failures)}): {', '.join(failures)}")
        return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
