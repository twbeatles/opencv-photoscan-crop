from __future__ import annotations

from ....i18n.catalog import t


class WatchRuntimeFlow:
    """Translated helper messages for watch/scheduler flows."""

    @staticmethod
    def busy_reason_label(reason: str) -> str:
        normalized = str(reason or "").strip().lower()
        return t(f"watch.busy.{normalized}") if normalized else ""
