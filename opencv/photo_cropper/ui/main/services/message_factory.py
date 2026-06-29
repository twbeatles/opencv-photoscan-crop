from __future__ import annotations

import os
from typing import Mapping

from ....i18n.catalog import t


class UiMessageFactory:
    """Centralized, translated UI message composition for main-window actions."""

    @property
    def warning_title(self) -> str:
        return t("dialog.warning")

    @property
    def info_title(self) -> str:
        return t("dialog.info")

    @property
    def result_title(self) -> str:
        return t("dialog.result")

    def batch_summary(
        self,
        *,
        full_success_count: int,
        partial_count: int,
        failed_count: int,
        skipped_count: int,
    ) -> str:
        return t(
            "batch.summary",
            success=full_success_count,
            partial=partial_count,
            failed=failed_count,
            skipped=skipped_count,
        )

    def batch_cancelled_summary(
        self,
        *,
        full_success_count: int,
        partial_count: int,
        failed_count: int,
    ) -> str:
        return t(
            "batch.cancelled.summary",
            success=full_success_count,
            partial=partial_count,
            failed=failed_count,
        )

    def duplicate_summary(self, duplicates: Mapping[str, list[str]]) -> tuple[int, str]:
        dup_count = sum(len(paths) - 1 for paths in duplicates.values() if len(paths) > 1)
        lines = [t("tools.duplicates.summary", count=dup_count), ""]
        for paths in list(duplicates.values())[:5]:
            if len(paths) > 1:
                lines.append(
                    t(
                        "tools.duplicates.summary_line",
                        filename=os.path.basename(paths[0]),
                        count=len(paths),
                    )
                )
        if len(duplicates) > 5:
            lines.append("")
            lines.append(t("tools.duplicates.summary_more", count=len(duplicates) - 5))
        return dup_count, "\n".join(lines).strip()

    def editor_load_error(self, path: str, error: object) -> str:
        return t(
            "msg.cannot_load_image",
            filename=os.path.basename(path),
            error=error,
        )

    def feature_toggle_message(
        self,
        *,
        prefix: str,
        enabled: bool,
        subject: str = "",
    ) -> str:
        key = f"{prefix}.enabled" if enabled else f"{prefix}.disabled"
        return t(key, subject=subject)

    def watch_busy_reason(self, reason: str) -> str:
        normalized = str(reason or "").strip().lower()
        return t(f"watch.busy.{normalized}") if normalized else ""
