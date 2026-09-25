"""Interactive crop-editing graphics view."""

from typing import List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCursor, QMouseEvent, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)

from .crop_editor_conversions import numpy_to_qpixmap
from .crop_editor_modes import EditMode, HandlePosition

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
        self._drag_handle: Optional[Tuple[HandlePosition, int]] = None
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
            if handle is not None:
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
            if line is not None:
                self._perspective_lines.append(line)
        
        # Draw handles at corners
        for i, point in enumerate(self._perspective_points):
            handle = self._create_handle(point)
            if handle is not None:
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
            if line is not None:
                self._grid_lines.append(line)
        
        # Horizontal lines (thirds)
        for i in range(1, 3):
            y = rect.top() + rect.height() * i / 3
            line = self._scene.addLine(rect.left(), y, rect.right(), y, pen)
            if line is not None:
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
        if handle is None:
            handle = QGraphicsEllipseItem(rect)
            handle.setPen(QPen(Qt.GlobalColor.white, 2))
            handle.setBrush(QBrush(self.HANDLE_COLOR))
            self._scene.addItem(handle)
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
                handle_type = handle.data(0)
                if isinstance(handle_type, HandlePosition):
                    return (handle_type, i)
        
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
