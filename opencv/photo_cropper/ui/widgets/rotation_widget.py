"""Standalone rotation control widget."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDoubleSpinBox, QSlider, QWidget

class RotationWidget(QWidget):
    """Simple rotation control widget."""
    
    rotation_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("각도:"))
        
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(-450, 450)
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)
        
        self._spin = QDoubleSpinBox()
        self._spin.setRange(-180.0, 180.0)
        self._spin.setDecimals(1)
        self._spin.setSuffix("°")
        self._spin.setValue(0.0)
        self._spin.valueChanged.connect(self._on_spin_changed)
        layout.addWidget(self._spin)
    
    def get_angle(self) -> float:
        return self._spin.value()
    
    def set_angle(self, angle: float):
        self._spin.setValue(angle)
    
    def _on_slider_changed(self, value: int):
        angle = value / 10.0
        self._spin.blockSignals(True)
        self._spin.setValue(angle)
        self._spin.blockSignals(False)
        self.rotation_changed.emit(angle)
    
    def _on_spin_changed(self, value: float):
        self._slider.blockSignals(True)
        self._slider.setValue(int(value * 10))
        self._slider.blockSignals(False)
        self.rotation_changed.emit(value)
