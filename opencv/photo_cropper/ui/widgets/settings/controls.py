from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSlider, QSpinBox

from ....core.scene_presets import SCENE_PRESET_META
from ....i18n.catalog import t

THEME_CHOICES = ("auto", "light", "dark")


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events."""

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel events."""

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events."""

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoScrollSlider(QSlider):
    """QSlider that ignores mouse wheel events."""

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


def scene_preset_ids() -> list[str]:
    """Preset ids for the picker; "keep current" leads so any pick applies."""
    ids = [sid for sid in SCENE_PRESET_META if sid != "custom"]
    return ["custom", *ids]


def populate_scene_presets(combo: QComboBox) -> None:
    """Fill (or relabel) a scene-preset combo with translated names."""
    ids = scene_preset_ids()
    was_blocked = combo.blockSignals(True)
    try:
        if combo.count() != len(ids):
            combo.clear()
            for sid in ids:
                combo.addItem("", sid)
        for index, sid in enumerate(ids):
            combo.setItemText(index, t(f"scene.{sid}", default=SCENE_PRESET_META[sid][0]))
    finally:
        combo.blockSignals(was_blocked)


def populate_theme_choices(combo: QComboBox) -> None:
    """Fill (or relabel) a theme combo; item data holds the stored value."""
    was_blocked = combo.blockSignals(True)
    try:
        if combo.count() != len(THEME_CHOICES):
            combo.clear()
            for name in THEME_CHOICES:
                combo.addItem("", name)
        for index, name in enumerate(THEME_CHOICES):
            combo.setItemText(index, t(f"settings.theme.{name}", default=name))
    finally:
        combo.blockSignals(was_blocked)


__all__ = [
    "THEME_CHOICES",
    "populate_scene_presets",
    "populate_theme_choices",
    "scene_preset_ids",
    "NoScrollSpinBox",
    "NoScrollDoubleSpinBox",
    "NoScrollComboBox",
    "NoScrollSlider",
]
