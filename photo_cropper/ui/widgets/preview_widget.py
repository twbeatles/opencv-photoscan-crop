#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preview Widget for Photo Cropper.

Provides image preview with zoom, pan, and contour overlay capabilities.
"""

import numpy as np
import cv2
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QSlider, QPushButton, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QMouseEvent


def numpy_to_qimage(image: np.ndarray) -> QImage:
    """
    Convert numpy array to QImage.
    
    Args:
        image: OpenCV image (BGR or Grayscale)
        
    Returns:
        QImage
    """
    if image is None:
        return QImage()
    
    if len(image.shape) == 2:
        # Grayscale - make a copy for memory safety
        h, w = image.shape
        image_copy = np.ascontiguousarray(image)
        bytes_per_line = w
        qimage = QImage(image_copy.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
        # Copy to ensure QImage owns its data
        return qimage.copy()
    else:
        # Color (BGR -> RGB) - make contiguous copy
        h, w, c = image.shape
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        bytes_per_line = 3 * w
        qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        # Copy to ensure QImage owns its data
        return qimage.copy()


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert numpy array to QPixmap."""
    qimage = numpy_to_qimage(image)
    return QPixmap.fromImage(qimage)


class ZoomableGraphicsView(QGraphicsView):
    """
    QGraphicsView with zoom and pan capabilities.
    
    Features:
        - Mouse wheel zoom
        - Click and drag to pan
        - Smooth zooming
    """
    
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._is_panning = False
        self._pan_start = QPointF()
        
        # Setup
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zoom."""
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            # Zoom in
            if self._zoom < self._max_zoom:
                self._zoom *= zoom_factor
                self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            if self._zoom > self._min_zoom:
                self._zoom /= zoom_factor
                self.scale(1 / zoom_factor, 1 / zoom_factor)
        
        self.zoom_changed.emit(self._zoom)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning."""
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and 
            event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning."""
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(int(h_bar.value() - delta.x()))
            v_bar.setValue(int(v_bar.value() - delta.y()))
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
    
    def fit_in_view(self):
        """Fit content to view."""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)
    
    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)
    
    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom


class ImagePreviewWidget(QWidget):
    """
    Complete image preview widget with controls.
    
    Features:
        - Zoomable image display
        - Contour overlay toggle
        - Zoom controls
        - Side-by-side comparison mode
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._original_image: np.ndarray = None
        self._processed_image: np.ndarray = None
        self._contour_overlay: np.ndarray = None
        self._show_contour = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Graphics views container
        views_layout = QHBoxLayout()
        
        # Original image view
        self.original_scene = QGraphicsScene()
        self.original_view = ZoomableGraphicsView()
        self.original_view.setScene(self.original_scene)
        self.original_pixmap_item = QGraphicsPixmapItem()
        self.original_scene.addItem(self.original_pixmap_item)
        
        original_container = QFrame()
        original_container.setFrameStyle(QFrame.Shape.StyledPanel)
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)
        original_label = QLabel("원본")
        original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_label.setObjectName("subtitleLabel")
        original_layout.addWidget(original_label)
        original_layout.addWidget(self.original_view)
        views_layout.addWidget(original_container)
        
        # Processed image view
        self.processed_scene = QGraphicsScene()
        self.processed_view = ZoomableGraphicsView()
        self.processed_view.setScene(self.processed_scene)
        self.processed_pixmap_item = QGraphicsPixmapItem()
        self.processed_scene.addItem(self.processed_pixmap_item)
        
        processed_container = QFrame()
        processed_container.setFrameStyle(QFrame.Shape.StyledPanel)
        processed_layout = QVBoxLayout(processed_container)
        processed_layout.setContentsMargins(0, 0, 0, 0)
        processed_label = QLabel("처리 결과")
        processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        processed_label.setObjectName("subtitleLabel")
        processed_layout.addWidget(processed_label)
        processed_layout.addWidget(self.processed_view)
        views_layout.addWidget(processed_container)
        
        layout.addLayout(views_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.contour_check = QCheckBox("검출 영역 표시")
        self.contour_check.setChecked(True)
        self.contour_check.stateChanged.connect(self._on_contour_toggle)
        controls_layout.addWidget(self.contour_check)
        
        controls_layout.addStretch()
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        controls_layout.addWidget(self.zoom_label)
        
        fit_btn = QPushButton("맞춤")
        fit_btn.setMaximumWidth(60)
        fit_btn.clicked.connect(self._fit_all)
        controls_layout.addWidget(fit_btn)
        
        reset_btn = QPushButton("1:1")
        reset_btn.setMaximumWidth(50)
        reset_btn.clicked.connect(self._reset_zoom)
        controls_layout.addWidget(reset_btn)
        
        layout.addLayout(controls_layout)
        
        # Connect zoom signals
        self.original_view.zoom_changed.connect(self._on_zoom_changed)
        self.processed_view.zoom_changed.connect(self._on_zoom_changed)
    
    def set_original_image(self, image: np.ndarray, contour_overlay: np.ndarray = None):
        """
        Set original image with optional contour overlay.
        
        Args:
            image: Original image
            contour_overlay: Image with contour drawn on it
        """
        self._original_image = image
        self._contour_overlay = contour_overlay
        self._update_original_display()
    
    def set_processed_image(self, image: np.ndarray):
        """
        Set processed image.
        
        Args:
            image: Processed/cropped image
        """
        self._processed_image = image
        
        if image is not None:
            pixmap = numpy_to_qpixmap(image)
            self.processed_pixmap_item.setPixmap(pixmap)
            self.processed_scene.setSceneRect(pixmap.rect().toRectF())
        else:
            self.processed_pixmap_item.setPixmap(QPixmap())
    
    def _update_original_display(self):
        """Update original image display based on contour toggle."""
        if self._show_contour and self._contour_overlay is not None:
            image = self._contour_overlay
        else:
            image = self._original_image
        
        if image is not None:
            pixmap = numpy_to_qpixmap(image)
            self.original_pixmap_item.setPixmap(pixmap)
            self.original_scene.setSceneRect(pixmap.rect().toRectF())
        else:
            self.original_pixmap_item.setPixmap(QPixmap())
    
    def _on_contour_toggle(self, state):
        """Handle contour overlay toggle."""
        self._show_contour = bool(state)
        self._update_original_display()
    
    def _on_zoom_changed(self, zoom: float):
        """Handle zoom level change."""
        self.zoom_label.setText(f"{int(zoom * 100)}%")
    
    def _fit_all(self):
        """Fit all views."""
        self.original_view.fit_in_view()
        self.processed_view.fit_in_view()
    
    def _reset_zoom(self):
        """Reset all zooms."""
        self.original_view.reset_zoom()
        self.processed_view.reset_zoom()
    
    def clear(self):
        """Clear all images."""
        self._original_image = None
        self._processed_image = None
        self._contour_overlay = None
        self.original_pixmap_item.setPixmap(QPixmap())
        self.processed_pixmap_item.setPixmap(QPixmap())
    
    @property
    def show_contour(self) -> bool:
        """Get contour visibility state."""
        return self._show_contour
    
    @show_contour.setter
    def show_contour(self, value: bool):
        """Set contour visibility."""
        self._show_contour = value
        self.contour_check.setChecked(value)
        self._update_original_display()
