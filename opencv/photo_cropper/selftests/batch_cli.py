#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Batch CLI self-tests (facade): compatibility facade re-exporting the split modules."""

from __future__ import annotations

from .batch_session import (
    _test_batch_session_service_smoke,
    _test_batch_session_service_reentry_guard,
    _test_batch_thread_local_reuse,
    _test_batch_post_pipeline_order,
    _test_output_reservation_is_thread_safe,
    _test_processing_logger_partial_summary,
)
from .batch_failed_files import (
    _test_boundary_failed_file_collection_helper,
    _test_boundary_failed_file_collection_prefers_relative_paths,
    _test_recursive_scan_excludes_internal_generated_dirs,
    _test_classify_failed_files_preserves_relative_dirs,
    _test_classify_failed_files_rejects_invalid_failed_folder,
    _test_retry_failed_files_normalizes_empty_output_path,
    _test_skip_processed_with_classification_subfolder,
)
from .cli_settings import (
    _test_cli_settings_merge_priority,
    _test_cli_new_crop_options,
    _test_processed_index_roundtrip_and_source_change,
    _test_processed_index_backward_compat_and_partial_status,
    _test_profile_apply_rebuild_validation,
    _test_cli_rejects_invalid_settings_segments,
    _test_processed_signature_includes_routing_and_backup,
)
from .cli_execution import (
    _test_cli_cancel_exit_code_130,
    _test_cli_cancel_with_failed_still_returns_130,
    _test_cli_partial_exit_code_rules,
    _test_batch_fatal_error_and_cli_exit_code,
    _test_library_repository_singleton_reset,
    _test_ui_batch_completion_finalizes_in_background_and_clears_manual_state,
    _test_cli_recursive_output_guard,
    _test_batch_actions_recursive_output_guard,
    _test_management_preflight_file_batch_guard,
)

__all__ = [
    "_test_batch_session_service_smoke",
    "_test_batch_session_service_reentry_guard",
    "_test_batch_thread_local_reuse",
    "_test_batch_post_pipeline_order",
    "_test_output_reservation_is_thread_safe",
    "_test_processing_logger_partial_summary",
    "_test_boundary_failed_file_collection_helper",
    "_test_boundary_failed_file_collection_prefers_relative_paths",
    "_test_recursive_scan_excludes_internal_generated_dirs",
    "_test_classify_failed_files_preserves_relative_dirs",
    "_test_classify_failed_files_rejects_invalid_failed_folder",
    "_test_retry_failed_files_normalizes_empty_output_path",
    "_test_skip_processed_with_classification_subfolder",
    "_test_cli_settings_merge_priority",
    "_test_cli_new_crop_options",
    "_test_processed_index_roundtrip_and_source_change",
    "_test_processed_index_backward_compat_and_partial_status",
    "_test_profile_apply_rebuild_validation",
    "_test_cli_rejects_invalid_settings_segments",
    "_test_processed_signature_includes_routing_and_backup",
    "_test_cli_cancel_exit_code_130",
    "_test_cli_cancel_with_failed_still_returns_130",
    "_test_cli_partial_exit_code_rules",
    "_test_batch_fatal_error_and_cli_exit_code",
    "_test_library_repository_singleton_reset",
    "_test_ui_batch_completion_finalizes_in_background_and_clears_manual_state",
    "_test_cli_recursive_output_guard",
    "_test_batch_actions_recursive_output_guard",
    "_test_management_preflight_file_batch_guard",
]
