"""Crop editor panel composing the view and controls."""

from typing import List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .crop_editor_modes import EditMode
from .crop_editor_view import CropEditorView

class CropEditorWidget(QWidget):
    """Complete crop editor widget with controls."""
    
    # Signals
    crop_applied = pyqtSignal(np.ndarray)  # Cropped image
    crop_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._original_image: Optional[np.ndarray] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Editor view
        self._editor = CropEditorView()
        self._editor.region_changed.connect(self._on_region_changed)
        self._editor.perspective_changed.connect(self._on_perspective_changed)
        layout.addWidget(self._editor, 1)
        
        # Controls frame
        controls = QFrame()
        controls.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        
        # Mode selection
        mode_group = QGroupBox("편집 모드")
        mode_layout = QHBoxLayout(mode_group)
        
        self._mode_buttons = QButtonGroup(self)
        
        self._rect_mode_btn = QRadioButton("사각형 자르기")
        self._rect_mode_btn.setChecked(True)
        self._mode_buttons.addButton(self._rect_mode_btn, 0)
        mode_layout.addWidget(self._rect_mode_btn)
        
        self._persp_mode_btn = QRadioButton("원근 교정")
        self._mode_buttons.addButton(self._persp_mode_btn, 1)
        mode_layout.addWidget(self._persp_mode_btn)
        
        self._mode_buttons.idClicked.connect(self._on_mode_changed)
        
        controls_layout.addWidget(mode_group)
        
        # Rotation controls
        rotation_group = QGroupBox("회전")
        rotation_layout = QHBoxLayout(rotation_group)
        
        self._rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self._rotation_slider.setRange(-450, 450)  # -45.0 to 45.0 degrees * 10
        self._rotation_slider.setValue(0)
        self._rotation_slider.valueChanged.connect(self._on_rotation_slider_changed)
        rotation_layout.addWidget(self._rotation_slider)
        
        self._rotation_spin = QDoubleSpinBox()
        self._rotation_spin.setRange(-180.0, 180.0)
        self._rotation_spin.setDecimals(1)
        self._rotation_spin.setSuffix("°")
        self._rotation_spin.setValue(0.0)
        self._rotation_spin.valueChanged.connect(self._on_rotation_spin_changed)
        rotation_layout.addWidget(self._rotation_spin)
        
        self._rotate_90_btn = QPushButton("90° ↻")
        self._rotate_90_btn.clicked.connect(lambda: self._rotate_by(90))
        rotation_layout.addWidget(self._rotate_90_btn)
        
        controls_layout.addWidget(rotation_group)
        
        # Crop info
        info_layout = QHBoxLayout()
        
        info_layout.addWidget(QLabel("X:"))
        self._x_spin = QSpinBox()
        self._x_spin.setRange(0, 99999)
        info_layout.addWidget(self._x_spin)
        
        info_layout.addWidget(QLabel("Y:"))
        self._y_spin = QSpinBox()
        self._y_spin.setRange(0, 99999)
        info_layout.addWidget(self._y_spin)
        
        info_layout.addWidget(QLabel("W:"))
        self._w_spin = QSpinBox()
        self._w_spin.setRange(1, 99999)
        info_layout.addWidget(self._w_spin)
        
        info_layout.addWidget(QLabel("H:"))
        self._h_spin = QSpinBox()
        self._h_spin.setRange(1, 99999)
        info_layout.addWidget(self._h_spin)
        
        info_layout.addStretch()
        controls_layout.addLayout(info_layout)
        
        # Options
        options_layout = QHBoxLayout()
        
        self._grid_check = QCheckBox("격자선 표시")
        self._grid_check.setChecked(True)
        self._grid_check.toggled.connect(self._editor.set_show_grid)
        options_layout.addWidget(self._grid_check)
        
        options_layout.addStretch()
        
        self._reset_btn = QPushButton("초기화")
        self._reset_btn.clicked.connect(self._editor.reset_to_full)
        options_layout.addWidget(self._reset_btn)
        
        controls_layout.addLayout(options_layout)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._cancel_btn = QPushButton("취소")
        self._cancel_btn.clicked.connect(self.crop_cancelled.emit)
        btn_layout.addWidget(self._cancel_btn)
        
        self._apply_btn = QPushButton("적용")
        self._apply_btn.setDefault(True)
        self._apply_btn.clicked.connect(self._apply_crop)
        btn_layout.addWidget(self._apply_btn)
        
        controls_layout.addLayout(btn_layout)
        
        layout.addWidget(controls)
    
    def set_image(self, image: np.ndarray):
        """Set image to edit."""
        self._original_image = image.copy()
        self._editor.set_image(image)
        
        # Update spin box maxes
        h, w = image.shape[:2]
        self._x_spin.setMaximum(w)
        self._y_spin.setMaximum(h)
        self._w_spin.setMaximum(w)
        self._h_spin.setMaximum(h)
        self._w_spin.setValue(w)
        self._h_spin.setValue(h)

    def set_rectangle_mode(self):
        """Activate rectangle edit mode."""
        self._rect_mode_btn.setChecked(True)
        self._on_mode_changed(0)

    def set_perspective_points(self, points: List[Tuple[float, float]]):
        """Activate perspective mode and set 4 corner points."""
        if points is None or len(points) != 4:
            return
        self._persp_mode_btn.setChecked(True)
        self._on_mode_changed(1)
        self._editor.set_perspective_points(points)
    
    def _on_mode_changed(self, id: int):
        """Handle mode button change."""
        if id == 0:
            self._editor.set_mode(EditMode.RECTANGLE)
        elif id == 1:
            self._editor.set_mode(EditMode.PERSPECTIVE)
    
    def _on_region_changed(self, rect: QRectF):
        """Handle crop region change."""
        self._x_spin.setValue(int(rect.x()))
        self._y_spin.setValue(int(rect.y()))
        self._w_spin.setValue(int(rect.width()))
        self._h_spin.setValue(int(rect.height()))
    
    def _on_perspective_changed(self, points: list):
        """Handle perspective points change."""
        pass  # Could add point coordinate display
    
    def _on_rotation_slider_changed(self, value: int):
        """Handle rotation slider change."""
        angle = value / 10.0
        self._rotation_spin.blockSignals(True)
        self._rotation_spin.setValue(angle)
        self._rotation_spin.blockSignals(False)
        self._editor.set_rotation_angle(angle)
    
    def _on_rotation_spin_changed(self, value: float):
        """Handle rotation spin change."""
        self._rotation_slider.blockSignals(True)
        self._rotation_slider.setValue(int(value * 10))
        self._rotation_slider.blockSignals(False)
        self._editor.set_rotation_angle(value)
    
    def _rotate_by(self, degrees: float):
        """Rotate by specified degrees."""
        current = self._rotation_spin.value()
        new_angle = (current + degrees) % 360
        if new_angle > 180:
            new_angle -= 360
        self._rotation_spin.setValue(new_angle)
    
    def _apply_crop(self):
        """Apply crop and emit result."""
        if self._original_image is None:
            return
        
        from ...core.advanced import AdvancedImageProcessor
        processor = AdvancedImageProcessor()
        
        image = self._original_image.copy()

        # IMPORTANT: preserve editor coordinate system.
        # Apply crop/perspective first, then rotate the extracted result.
        if self._rect_mode_btn.isChecked():
            rect = self._editor.get_crop_rect()
            x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
            
            # Clamp to image bounds
            img_h, img_w = image.shape[:2]
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = min(w, img_w - x)
            h = min(h, img_h - y)
            
            if w > 0 and h > 0:
                image = image[y:y+h, x:x+w]
        else:
            # Perspective mode
            points = self._editor.get_perspective_points()
            if len(points) == 4:
                pts = np.array(points, dtype=np.float32)
                result = processor.correct_perspective(image, pts)
                if result.success:
                    image = result.image

        # Apply rotation at the end so crop coordinates always match editor view.
        angle = self._rotation_spin.value()
        if abs(angle) > 0.1:
            image = processor.rotate_free(image, angle)
        
        self.crop_applied.emit(image)
