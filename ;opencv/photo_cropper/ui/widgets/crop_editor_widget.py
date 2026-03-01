#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crop Editor Widget for Photo Cropper.

Provides interactive crop region selection and editing:
- Manual rectangular selection
- Corner handle resizing
- Perspective point editing
- Free angle rotation
- Grid overlay
"""

import numpy as np
import cv2
from enum import Enum
from typing import Optional, List, Tuple, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QSlider, QPushButton, QLabel, QSpinBox,
    QFrame, QButtonGroup, QRadioButton, QGroupBox, QDoubleSpinBox,
    QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QLineF
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor,
    QWheelEvent, QMouseEvent, QKeyEvent, QCursor
)


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert numpy array to QPixmap."""
    if len(image.shape) == 2:
        height, width = image.shape
        bytes_per_line = width
        qimage = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
    else:
        height, width, channels = image.shape
        if channels == 4:
            bytes_per_line = 4 * width
            qimage = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * width
            qimage = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    
    return QPixmap.fromImage(qimage.copy())


class EditMode(Enum):
    """Editing mode enumeration."""
    NONE = "none"
    RECTANGLE = "rectangle"
    PERSPECTIVE = "perspective"
    ROTATE = "rotate"


class HandlePosition(Enum):
    """Corner handle position."""
    TOP_LEFT = 0
    TOP_RIGHT = 1
    BOTTOM_RIGHT = 2
    BOTTOM_LEFT = 3
    TOP = 4
    RIGHT = 5
    BOTTOM = 6
    LEFT = 7


class CropEditorView(QGraphicsView):
    """Graphics view for crop editing with handles."""
    
    # Signals
    region_changed = pyqtSignal(QRectF)  # Crop rectangle changed
    perspective_changed = pyqtSignal(list)  # 4-point perspective changed
    rotation_changed = pyqtSignal(float)  # Rotation angle changed
    
    HANDLE_SIZE = 12
    HANDLE_COLOR = QColor(0, 120, 215)
    HANDLE_HOVER_COLOR = QColor(0, 180, 255)
    RECT_COLOR = QColor(0, 120, 215, 180)
    GRID_COLOR = QColor(255, 255, 255, 100)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # Configure view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        
        # Image item
        self._image_item: Optional[QGraphicsPixmapItem] = None
        self._original_image: Optional[np.ndarray] = None
        self._image_size = (0, 0)
        
        # Edit mode
        self._mode = EditMode.RECTANGLE
        self._show_grid = True
        
        # Crop rectangle state
        self._crop_rect = QRectF()
        self._rect_item: Optional[QGraphicsRectItem] = None
        self._handles: List[QGraphicsEllipseItem] = []
        self._grid_lines: List[QGraphicsLineItem] = []
        
        # Perspective points (4 corners)
        self._perspective_points: List[QPointF] = []
        self._perspective_handles: List[QGraphicsEllipseItem] = []
        self._perspective_lines: List[QGraphicsLineItem] = []
        
        # Rotation state
        self._rotation_angle = 0.0
        self._rotation_center = QPointF()
        
        # Interaction state
        self._dragging = False
        self._drag_handle: Optional[HandlePosition] = None
        self._drag_start = QPointF()
        self._drawing_new_rect = False
        
    def set_image(self, image: np.ndarray):
        """Set the image to edit."""
        self._original_image = image.copy()
        self._image_size = (image.shape[1], image.shape[0])
        
        # Clear scene
        self._scene.clear()
        self._handles.clear()
        self._grid_lines.clear()
        self._perspective_handles.clear()
        self._perspective_lines.clear()
        
        # Add image
        pixmap = numpy_to_qpixmap(image)
        self._image_item = self._scene.addPixmap(pixmap)
        
        # Set scene rect
        self._scene.setSceneRect(0, 0, image.shape[1], image.shape[0])
        
        # Initialize crop rect to full image
        self._crop_rect = QRectF(0, 0, image.shape[1], image.shape[0])
        
        # Initialize perspective points to corners
        w, h = self._image_size
        self._perspective_points = [
            QPointF(0, 0),
            QPointF(w, 0),
            QPointF(w, h),
            QPointF(0, h)
        ]
        
        # Fit in view
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        # Update overlays
        self._update_overlays()
    
    def set_mode(self, mode: EditMode):
        """Set editing mode."""
        self._mode = mode
        self._update_overlays()
    
    def set_show_grid(self, show: bool):
        """Toggle grid visibility."""
        self._show_grid = show
        self._update_grid()
    
    def get_crop_rect(self) -> QRectF:
        """Get current crop rectangle."""
        return self._crop_rect
    
    def set_crop_rect(self, rect: QRectF):
        """Set crop rectangle."""
        self._crop_rect = rect
        self._update_overlays()
        self.region_changed.emit(self._crop_rect)
    
    def get_perspective_points(self) -> List[Tuple[float, float]]:
        """Get perspective corner points."""
        return [(p.x(), p.y()) for p in self._perspective_points]
    
    def set_perspective_points(self, points: List[Tuple[float, float]]):
        """Set perspective corner points."""
        self._perspective_points = [QPointF(x, y) for x, y in points]
        self._update_overlays()
        self.perspective_changed.emit(self.get_perspective_points())
    
    def get_rotation_angle(self) -> float:
        """Get rotation angle."""
        return self._rotation_angle
    
    def set_rotation_angle(self, angle: float):
        """Set rotation angle."""
        self._rotation_angle = angle
        self.rotation_changed.emit(angle)
    
    def reset_to_full(self):
        """Reset crop to full image."""
        if self._image_size[0] > 0:
            w, h = self._image_size
            self._crop_rect = QRectF(0, 0, w, h)
            self._perspective_points = [
                QPointF(0, 0),
                QPointF(w, 0),
                QPointF(w, h),
                QPointF(0, h)
            ]
            self._rotation_angle = 0.0
            self._update_overlays()
            self.region_changed.emit(self._crop_rect)
    
    def _update_overlays(self):
        """Update all overlay graphics."""
        # Remove old overlays (keep image)
        for item in self._handles + self._grid_lines + self._perspective_handles + self._perspective_lines:
            if item.scene():
                self._scene.removeItem(item)
        
        self._handles.clear()
        self._grid_lines.clear()
        self._perspective_handles.clear()
        self._perspective_lines.clear()
        
        if self._mode == EditMode.RECTANGLE:
            self._update_rectangle_overlay()
        elif self._mode == EditMode.PERSPECTIVE:
            self._update_perspective_overlay()
        
        if self._show_grid:
            self._update_grid()
    
    def _update_rectangle_overlay(self):
        """Update rectangle crop overlay."""
        if self._crop_rect.isEmpty():
            return
        
        # Draw crop rectangle
        pen = QPen(self.RECT_COLOR, 2)
        self._rect_item = self._scene.addRect(self._crop_rect, pen)
        
        # Draw handles at corners and edges
        handle_positions = [
            (self._crop_rect.topLeft(), HandlePosition.TOP_LEFT),
            (self._crop_rect.topRight(), HandlePosition.TOP_RIGHT),
            (self._crop_rect.bottomRight(), HandlePosition.BOTTOM_RIGHT),
            (self._crop_rect.bottomLeft(), HandlePosition.BOTTOM_LEFT),
            (QPointF(self._crop_rect.center().x(), self._crop_rect.top()), HandlePosition.TOP),
            (QPointF(self._crop_rect.right(), self._crop_rect.center().y()), HandlePosition.RIGHT),
            (QPointF(self._crop_rect.center().x(), self._crop_rect.bottom()), HandlePosition.BOTTOM),
            (QPointF(self._crop_rect.left(), self._crop_rect.center().y()), HandlePosition.LEFT),
        ]
        
        for pos, handle_type in handle_positions:
            handle = self._create_handle(pos)
            handle.setData(0, handle_type)
            self._handles.append(handle)
    
    def _update_perspective_overlay(self):
        """Update perspective editing overlay."""
        if len(self._perspective_points) != 4:
            return
        
        # Draw lines connecting points
        pen = QPen(self.RECT_COLOR, 2)
        for i in range(4):
            p1 = self._perspective_points[i]
            p2 = self._perspective_points[(i + 1) % 4]
            line = self._scene.addLine(QLineF(p1, p2), pen)
            self._perspective_lines.append(line)
        
        # Draw handles at corners
        for i, point in enumerate(self._perspective_points):
            handle = self._create_handle(point)
            handle.setData(0, i)
            self._perspective_handles.append(handle)
    
    def _update_grid(self):
        """Update rule of thirds grid."""
        if not self._show_grid:
            return
        
        pen = QPen(self.GRID_COLOR, 1, Qt.PenStyle.DashLine)
        
        if self._mode == EditMode.RECTANGLE and not self._crop_rect.isEmpty():
            rect = self._crop_rect
        elif self._image_size[0] > 0:
            rect = QRectF(0, 0, self._image_size[0], self._image_size[1])
        else:
            return
        
        # Vertical lines (thirds)
        for i in range(1, 3):
            x = rect.left() + rect.width() * i / 3
            line = self._scene.addLine(x, rect.top(), x, rect.bottom(), pen)
            self._grid_lines.append(line)
        
        # Horizontal lines (thirds)
        for i in range(1, 3):
            y = rect.top() + rect.height() * i / 3
            line = self._scene.addLine(rect.left(), y, rect.right(), y, pen)
            self._grid_lines.append(line)
    
    def _create_handle(self, pos: QPointF) -> QGraphicsEllipseItem:
        """Create a handle at the given position."""
        size = self.HANDLE_SIZE
        rect = QRectF(pos.x() - size/2, pos.y() - size/2, size, size)
        
        handle = self._scene.addEllipse(
            rect,
            QPen(Qt.GlobalColor.white, 2),
            QBrush(self.HANDLE_COLOR)
        )
        handle.setZValue(100)
        handle.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        
        return handle
    
    def _get_handle_at(self, pos: QPointF) -> Optional[Tuple[HandlePosition, int]]:
        """Check if position is over a handle."""
        threshold = self.HANDLE_SIZE * 1.5
        
        # Check rectangle handles
        for i, handle in enumerate(self._handles):
            center = handle.rect().center()
            if (pos - center).manhattanLength() < threshold:
                return (handle.data(0), i)
        
        # Check perspective handles
        for i, handle in enumerate(self._perspective_handles):
            center = handle.rect().center()
            if (pos - center).manhattanLength() < threshold:
                return (HandlePosition.TOP_LEFT, i)  # Use index as handle ID
        
        return None
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        
        scene_pos = self.mapToScene(event.pos())
        
        # Check if clicking on handle
        handle_info = self._get_handle_at(scene_pos)
        
        if handle_info:
            self._dragging = True
            self._drag_handle = handle_info
            self._drag_start = scene_pos
        elif self._mode == EditMode.RECTANGLE:
            # Start drawing new rectangle
            self._drawing_new_rect = True
            self._drag_start = scene_pos
            self._crop_rect = QRectF(scene_pos, scene_pos)
        
        event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        scene_pos = self.mapToScene(event.pos())
        
        if self._dragging and self._drag_handle:
            if self._mode == EditMode.RECTANGLE:
                self._update_rect_handle(scene_pos)
            elif self._mode == EditMode.PERSPECTIVE:
                self._update_perspective_handle(scene_pos)
        elif self._drawing_new_rect:
            self._crop_rect = QRectF(self._drag_start, scene_pos).normalized()
            self._update_overlays()
        else:
            # Update cursor based on hover
            handle_info = self._get_handle_at(scene_pos)
            if handle_info:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
        
        event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._dragging:
            self._dragging = False
            self._drag_handle = None
            self.region_changed.emit(self._crop_rect)
        
        if self._drawing_new_rect:
            self._drawing_new_rect = False
            self.region_changed.emit(self._crop_rect)
        
        event.accept()
    
    def _update_rect_handle(self, pos: QPointF):
        """Update rectangle based on handle drag."""
        if not self._drag_handle:
            return
        
        handle_type, _ = self._drag_handle
        rect = self._crop_rect
        
        # Constrain to image bounds
        pos.setX(max(0, min(pos.x(), self._image_size[0])))
        pos.setY(max(0, min(pos.y(), self._image_size[1])))
        
        # Update rectangle based on which handle is dragged
        if handle_type == HandlePosition.TOP_LEFT:
            rect.setTopLeft(pos)
        elif handle_type == HandlePosition.TOP_RIGHT:
            rect.setTopRight(pos)
        elif handle_type == HandlePosition.BOTTOM_RIGHT:
            rect.setBottomRight(pos)
        elif handle_type == HandlePosition.BOTTOM_LEFT:
            rect.setBottomLeft(pos)
        elif handle_type == HandlePosition.TOP:
            rect.setTop(pos.y())
        elif handle_type == HandlePosition.RIGHT:
            rect.setRight(pos.x())
        elif handle_type == HandlePosition.BOTTOM:
            rect.setBottom(pos.y())
        elif handle_type == HandlePosition.LEFT:
            rect.setLeft(pos.x())
        
        self._crop_rect = rect.normalized()
        self._update_overlays()
    
    def _update_perspective_handle(self, pos: QPointF):
        """Update perspective point based on handle drag."""
        if not self._drag_handle:
            return
        
        _, index = self._drag_handle
        
        # Constrain to image bounds
        pos.setX(max(0, min(pos.x(), self._image_size[0])))
        pos.setY(max(0, min(pos.y(), self._image_size[1])))
        
        self._perspective_points[index] = pos
        self._update_overlays()
        self.perspective_changed.emit(self.get_perspective_points())
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()


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
        
        # Apply rotation if any
        angle = self._rotation_spin.value()
        if abs(angle) > 0.1:
            image = processor.rotate_free(image, angle)
        
        # Apply crop or perspective
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
        
        self.crop_applied.emit(image)


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
