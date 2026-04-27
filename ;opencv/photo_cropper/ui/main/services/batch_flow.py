from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from ....core.settings_model import AppSettings
from ....core.settings_model.validation import (
    build_validation_summary,
    validate_settings,
)
from ....i18n.catalog import t
from ....utils.file_helpers import is_output_inside_input, validate_directory


@dataclass(frozen=True)
class BatchPreflightResult:
    ok: bool
    title: str = ""
    message: str = ""


@dataclass(frozen=True)
class ResolvedIoPaths:
    ok: bool
    input_path: str = ""
    output_path: str = ""
    title: str = ""
    message: str = ""


class BatchRuntimeFlow:
    """Reusable runtime checks for batch/manual entrypoints."""

    def validate_settings(self, settings: AppSettings) -> BatchPreflightResult:
        issues = validate_settings(settings)
        if not issues:
            return BatchPreflightResult(ok=True)
        return BatchPreflightResult(
            ok=False,
            title=t("validation.config_invalid_title"),
            message=t(
                "validation.config_invalid_body",
                summary=build_validation_summary(issues),
            ),
        )

    def resolve_io_paths(
        self,
        *,
        input_path: str,
        output_path: str,
        recursive: bool,
        failed_folder_name: str,
    ) -> ResolvedIoPaths:
        valid, error = validate_directory(input_path)
        if not valid:
            return ResolvedIoPaths(
                ok=False,
                title=t("dialog.warning"),
                message=t("validation.input_dir_error", error=error),
            )

        normalized_output = str(output_path or "").strip()
        if not normalized_output:
            normalized_output = os.path.join(input_path, "output_cropped")

        try:
            os.makedirs(normalized_output, exist_ok=True)
        except Exception as exc:
            return ResolvedIoPaths(
                ok=False,
                title=t("dialog.warning"),
                message=t("validation.output_dir_error", error=exc),
            )

        if recursive and is_output_inside_input(input_path, normalized_output):
            return ResolvedIoPaths(
                ok=False,
                title=t("dialog.warning"),
                message=t(
                    "validation.recursive_output_guard",
                    input=input_path,
                    output=normalized_output,
                ),
            )

        return ResolvedIoPaths(
            ok=True,
            input_path=input_path,
            output_path=normalized_output,
        )

    def resolve_file_batch_paths(
        self,
        *,
        input_path: str,
        output_path: str,
        files: Sequence[str],
        recursive: bool,
        failed_folder_name: str,
    ) -> ResolvedIoPaths:
        normalized_files = [os.path.abspath(str(item or "")) for item in files]
        valid_files = [
            path
            for path in normalized_files
            if path and os.path.isfile(path)
        ]
        if not valid_files:
            return ResolvedIoPaths(
                ok=False,
                title=t("dialog.warning"),
                message=t("batch.no_files"),
            )

        normalized_input = str(input_path or "").strip()
        if not normalized_input:
            normalized_input = os.path.dirname(valid_files[0]) or os.getcwd()
        if os.path.isfile(normalized_input):
            normalized_input = os.path.dirname(normalized_input) or os.getcwd()

        return self.resolve_io_paths(
            input_path=normalized_input,
            output_path=output_path,
            recursive=recursive,
            failed_folder_name=failed_folder_name,
        )
