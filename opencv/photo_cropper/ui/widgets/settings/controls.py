from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSlider, QSpinBox


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


__all__ = [
    "NoScrollSpinBox",
    "NoScrollDoubleSpinBox",
    "NoScrollComboBox",
    "NoScrollSlider",
]
