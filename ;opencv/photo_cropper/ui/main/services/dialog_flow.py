from __future__ import annotations

from ....i18n.catalog import t


def build_editor_title(filename: str) -> str:
    return t("dialog.crop_editor.title", filename=filename)


def build_editor_position_label(current: int, total: int) -> str:
    if total <= 0 or current <= 0:
        return t("dialog.crop_editor.single")
    return t("dialog.crop_editor.position", current=current, total=total)
