"""Before/after compare panel composing the views."""

from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...i18n.catalog import t
from .compare_modes import CompareMode
from .compare_views import CompareGraphicsView, OverlayCompareWidget, SliderCompareWidget

class BeforeAfterCompareWidget(QWidget):
    """Complete before/after comparison widget with mode selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._before_image: Optional[np.ndarray] = None
        self._after_image: Optional[np.ndarray] = None
        self._current_mode = CompareMode.SLIDER
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Mode selection toolbar
        toolbar = QHBoxLayout()
        
        self._mode_label = QLabel(t("compare.mode"))
        toolbar.addWidget(self._mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)
        
        toolbar.addStretch()
        
        # Opacity slider (for overlay mode)
        self._opacity_label = QLabel(t("compare.opacity"))
        self._opacity_label.setVisible(False)
        toolbar.addWidget(self._opacity_label)
        
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(50)
        self._opacity_slider.setFixedWidth(150)
        self._opacity_slider.setVisible(False)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        toolbar.addWidget(self._opacity_slider)
        
        # Toggle button (for toggle mode)
        self._toggle_btn = QPushButton(t("compare.toggle"))
        self._toggle_btn.setVisible(False)
        self._toggle_btn.clicked.connect(self._toggle_image)
        toolbar.addWidget(self._toggle_btn)
        
        layout.addLayout(toolbar)
        
        # Stacked widget for different comparison views
        self._stack = QStackedWidget()
        
        # Slider compare widget
        self._slider_widget = SliderCompareWidget()
        self._stack.addWidget(self._slider_widget)
        
        # Side by side widget
        self._side_widget = QWidget()
        side_layout = QHBoxLayout(self._side_widget)
        side_layout.setContentsMargins(0, 0, 0, 0)
        self._left_view = CompareGraphicsView()
        self._right_view = CompareGraphicsView()
        side_layout.addWidget(self._left_view)
        side_layout.addWidget(self._right_view)
        self._stack.addWidget(self._side_widget)
        
        # Overlay widget
        self._overlay_widget = OverlayCompareWidget()
        self._stack.addWidget(self._overlay_widget)
        
        # Toggle widget (just shows one image)
        self._toggle_widget = CompareGraphicsView()
        self._toggle_showing_after = True
        self._stack.addWidget(self._toggle_widget)

        layout.addWidget(self._stack, 1)
        self.retranslate_ui()
    
    def set_images(self, before: np.ndarray, after: np.ndarray):
        """Set before and after images."""
        self._before_image = before.copy() if before is not None else None
        self._after_image = after.copy() if after is not None else None
        
        # Update all widgets
        self._slider_widget.set_images(before, after)
        self._overlay_widget.set_images(before, after)
        
        self._left_view.set_image(before)
        self._right_view.set_image(after)
        self._left_view.fit_in_view()
        self._right_view.fit_in_view()
        
        self._toggle_widget.set_image(after if self._toggle_showing_after else before)
        self._toggle_widget.fit_in_view()
    
    def _on_mode_changed(self, index: int):
        """Handle mode selection change."""
        # Hide mode-specific controls
        self._opacity_label.setVisible(False)
        self._opacity_slider.setVisible(False)
        self._toggle_btn.setVisible(False)
        
        if index == 0:  # Slider horizontal
            self._slider_widget.set_vertical_mode(False)
            self._stack.setCurrentIndex(0)
        elif index == 1:  # Slider vertical
            self._slider_widget.set_vertical_mode(True)
            self._stack.setCurrentIndex(0)
        elif index == 2:  # Side by side
            self._stack.setCurrentIndex(1)
        elif index == 3:  # Overlay
            self._opacity_label.setVisible(True)
            self._opacity_slider.setVisible(True)
            self._stack.setCurrentIndex(2)
        elif index == 4:  # Toggle
            self._toggle_btn.setVisible(True)
            self._stack.setCurrentIndex(3)
    
    def _on_opacity_changed(self, value: int):
        """Handle opacity slider change."""
        self._overlay_widget.set_opacity(value / 100.0)
    
    def _toggle_image(self):
        """Toggle between before and after in toggle mode."""
        self._toggle_showing_after = not self._toggle_showing_after
        
        if self._toggle_showing_after:
            self._toggle_widget.set_image(self._after_image)
            self._toggle_btn.setText(t("compare.toggle.after"))
        else:
            self._toggle_widget.set_image(self._before_image)
            self._toggle_btn.setText(t("compare.toggle.before"))

        self._toggle_widget.fit_in_view()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Space:
            if self._mode_combo.currentIndex() == 4:  # Toggle mode
                self._toggle_image()
        else:
            super().keyPressEvent(event)

    def retranslate_ui(self):
        self._mode_label.setText(t("compare.mode"))
        items = (
            t("compare.mode.slider_h"),
            t("compare.mode.slider_v"),
            t("compare.mode.side"),
            t("compare.mode.overlay"),
            t("compare.mode.toggle"),
        )
        current_index = self._mode_combo.currentIndex()
        self._mode_combo.blockSignals(True)
        self._mode_combo.clear()
        self._mode_combo.addItems(list(items))
        self._mode_combo.setCurrentIndex(max(0, current_index))
        self._mode_combo.blockSignals(False)
        self._opacity_label.setText(t("compare.opacity"))
        if self._toggle_showing_after:
            self._toggle_btn.setText(t("compare.toggle.after"))
        else:
            self._toggle_btn.setText(t("compare.toggle.before"))
