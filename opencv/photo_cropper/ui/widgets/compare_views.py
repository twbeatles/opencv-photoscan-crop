"""Before/after compare view implementations."""

from typing import Optional

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

from ...i18n.catalog import t
from .compare_conversions import numpy_to_qpixmap

class CompareGraphicsView(QGraphicsView):
    """Graphics view with synchronized zoom/pan for comparison."""
    
    zoom_changed = pyqtSignal(float)
    pan_changed = pyqtSignal(QPointF)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self._zoom_factor = 1.0
        self._image_item: Optional[QGraphicsPixmapItem] = None
    
    def set_image(self, image: Optional[np.ndarray]):
        """Set the image to display."""
        self._scene.clear()
        if image is not None:
            pixmap = numpy_to_qpixmap(image)
            self._image_item = self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
    
    def fit_in_view(self):
        """Fit image to view."""
        if self._scene.sceneRect().isValid():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_factor = self.transform().m11()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        self._zoom_factor *= factor
        self.zoom_changed.emit(self._zoom_factor)
        event.accept()


class SliderCompareWidget(QWidget):
    """Slider-based before/after comparison."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._before_image: Optional[np.ndarray] = None
        self._after_image: Optional[np.ndarray] = None
        self._slider_pos = 0.5  # 0.0 to 1.0
        self._dragging = False
        self._vertical_mode = False
        
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)
    
    def set_images(self, before: np.ndarray, after: np.ndarray):
        """Set before and after images."""
        self._before_image = before.copy() if before is not None else None
        self._after_image = after.copy() if after is not None else None
        self.update()
    
    def set_slider_position(self, pos: float):
        """Set slider position (0.0 to 1.0)."""
        self._slider_pos = max(0.0, min(1.0, pos))
        self.update()
    
    def set_vertical_mode(self, vertical: bool):
        """Toggle vertical split mode."""
        self._vertical_mode = vertical
        self.update()
    
    def paintEvent(self, event):
        """Paint the comparison view."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        rect = self.rect()
        
        if self._before_image is None and self._after_image is None:
            painter.fillRect(rect, QColor(40, 40, 40))
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("compare.placeholder"))
            return
        
        # Scale images to fit widget while maintaining aspect ratio
        if self._before_image is not None:
            h, w = self._before_image.shape[:2]
        elif self._after_image is not None:
            h, w = self._after_image.shape[:2]
        else:
            return
        
        # Calculate scaled size
        scale = min(rect.width() / w, rect.height() / h)
        scaled_w = int(w * scale)
        scaled_h = int(h * scale)
        
        # Center offset
        offset_x = (rect.width() - scaled_w) // 2
        offset_y = (rect.height() - scaled_h) // 2
        
        # Create pixmaps
        before_pix = None
        after_pix = None
        
        if self._before_image is not None:
            before_pix = numpy_to_qpixmap(self._before_image)
            before_pix = before_pix.scaled(scaled_w, scaled_h, 
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
        
        if self._after_image is not None:
            after_pix = numpy_to_qpixmap(self._after_image)
            after_pix = after_pix.scaled(scaled_w, scaled_h,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
        
        # Draw images with clip region
        if self._vertical_mode:
            split_y = int(offset_y + scaled_h * self._slider_pos)
            
            # Draw before (top)
            if before_pix:
                painter.setClipRect(0, 0, rect.width(), split_y)
                painter.drawPixmap(offset_x, offset_y, before_pix)
            
            # Draw after (bottom)
            if after_pix:
                painter.setClipRect(0, split_y, rect.width(), rect.height())
                painter.drawPixmap(offset_x, offset_y, after_pix)
            
            # Draw divider line
            painter.setClipping(False)
            pen = QPen(QColor(255, 255, 255), 3)
            painter.setPen(pen)
            painter.drawLine(0, split_y, rect.width(), split_y)
            
            # Draw handle
            handle_rect = QRectF(rect.width() / 2 - 30, split_y - 15, 60, 30)
            painter.setBrush(QColor(0, 120, 215))
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRoundedRect(handle_rect, 5, 5)
            painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "◆")
        else:
            split_x = int(offset_x + scaled_w * self._slider_pos)
            
            # Draw before (left)
            if before_pix:
                painter.setClipRect(0, 0, split_x, rect.height())
                painter.drawPixmap(offset_x, offset_y, before_pix)
            
            # Draw after (right)
            if after_pix:
                painter.setClipRect(split_x, 0, rect.width(), rect.height())
                painter.drawPixmap(offset_x, offset_y, after_pix)
            
            # Draw divider line
            painter.setClipping(False)
            pen = QPen(QColor(255, 255, 255), 3)
            painter.setPen(pen)
            painter.drawLine(split_x, 0, split_x, rect.height())
            
            # Draw handle
            handle_rect = QRectF(split_x - 15, rect.height() / 2 - 30, 30, 60)
            painter.setBrush(QColor(0, 120, 215))
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRoundedRect(handle_rect, 5, 5)
            painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "◆")
        
        # Labels
        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255))
        
        # Before label
        before_label = t("compare.before")
        painter.drawText(offset_x + 10, offset_y + 25, before_label)

        # After label
        after_label = t("compare.after")
        if self._vertical_mode:
            painter.drawText(offset_x + 10, offset_y + scaled_h - 10, after_label)
        else:
            painter.drawText(offset_x + scaled_w - 100, offset_y + 25, after_label)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_slider_from_mouse(event.pos())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        if self._dragging:
            self._update_slider_from_mouse(event.pos())
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        self._dragging = False
    
    def _update_slider_from_mouse(self, pos):
        """Update slider position from mouse position."""
        if self._before_image is None:
            return
        
        h, w = self._before_image.shape[:2]
        rect = self.rect()
        scale = min(rect.width() / w, rect.height() / h)
        scaled_w = int(w * scale)
        scaled_h = int(h * scale)
        offset_x = (rect.width() - scaled_w) // 2
        offset_y = (rect.height() - scaled_h) // 2
        
        if self._vertical_mode:
            self._slider_pos = (pos.y() - offset_y) / scaled_h
        else:
            self._slider_pos = (pos.x() - offset_x) / scaled_w
        
        self._slider_pos = max(0.0, min(1.0, self._slider_pos))
        self.update()


class OverlayCompareWidget(QWidget):
    """Fade overlay comparison widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._before_image: Optional[np.ndarray] = None
        self._after_image: Optional[np.ndarray] = None
        self._opacity = 0.5  # 0.0 = before only, 1.0 = after only
        
        self.setMinimumSize(200, 200)
    
    def set_images(self, before: np.ndarray, after: np.ndarray):
        """Set before and after images."""
        self._before_image = before.copy() if before is not None else None
        self._after_image = after.copy() if after is not None else None
        self.update()
    
    def set_opacity(self, opacity: float):
        """Set overlay opacity (0.0 to 1.0)."""
        self._opacity = max(0.0, min(1.0, opacity))
        self.update()
    
    def paintEvent(self, event):
        """Paint the overlay view."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        rect = self.rect()
        
        if self._before_image is None and self._after_image is None:
            painter.fillRect(rect, QColor(40, 40, 40))
            return
        
        # Get image dimensions
        if self._before_image is not None:
            h, w = self._before_image.shape[:2]
        else:
            if self._after_image is None:
                painter.fillRect(rect, QColor(40, 40, 40))
                return
            h, w = self._after_image.shape[:2]
        
        # Scale to fit
        scale = min(rect.width() / w, rect.height() / h)
        scaled_w = int(w * scale)
        scaled_h = int(h * scale)
        offset_x = (rect.width() - scaled_w) // 2
        offset_y = (rect.height() - scaled_h) // 2
        
        # Draw before image
        if self._before_image is not None:
            before_pix = numpy_to_qpixmap(self._before_image)
            before_pix = before_pix.scaled(scaled_w, scaled_h,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            painter.setOpacity(1.0 - self._opacity)
            painter.drawPixmap(offset_x, offset_y, before_pix)
        
        # Draw after image with opacity
        if self._after_image is not None:
            after_pix = numpy_to_qpixmap(self._after_image)
            after_pix = after_pix.scaled(scaled_w, scaled_h,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            painter.setOpacity(self._opacity)
            painter.drawPixmap(offset_x, offset_y, after_pix)
        
        # Reset opacity and draw label
        painter.setOpacity(1.0)
        painter.setPen(QColor(255, 255, 255))
        label = f"{t('compare.opacity')} {int(self._opacity * 100)}%"
        painter.drawText(10, 20, label)
