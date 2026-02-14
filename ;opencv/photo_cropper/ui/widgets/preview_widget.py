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
    QSlider, QPushButton, QCheckBox, QFrame, QSizePolicy,
    QSplitter,
    QGraphicsTextItem, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QWheelEvent, QMouseEvent, QFont, QColor, QBrush, QPen


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
        self.show_placeholder()
    
    def show_placeholder(self):
        """Show placeholder text in empty views."""
        for scene in [self.original_scene, self.processed_scene]:
            scene.clear()
            
            # Add icon and text
            text_item = QGraphicsTextItem("📷\n이미지를 열거나\n드래그하세요")
            font = QFont("Segoe UI", 14)
            font.setBold(True)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor("#8b949e"))
            
            # Center text
            rect = text_item.boundingRect()
            text_item.setPos(-rect.width() / 2, -rect.height() / 2)
            
            scene.addItem(text_item)
            
        # Reset items references
        self.original_pixmap_item = QGraphicsPixmapItem()
        self.processed_pixmap_item = QGraphicsPixmapItem()
        
        self.original_scene.addItem(self.original_pixmap_item)
        self.processed_scene.addItem(self.processed_pixmap_item)

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Graphics views container
        # Main Vertical Splitter (Image Area / Controls)
        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setHandleWidth(4)
        
        # Graphics views container (Resizable Splitter)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(4)
        
        # Original image view
        self.original_scene = QGraphicsScene()
        self.original_view = ZoomableGraphicsView()
        self.original_view.setScene(self.original_scene)
        self.original_pixmap_item = QGraphicsPixmapItem()
        self.original_scene.addItem(self.original_pixmap_item)
        
        original_container = QFrame()
        original_container.setFrameStyle(QFrame.Shape.StyledPanel)
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(8, 8, 8, 8)
        original_layout.setSpacing(6)
        original_label = QLabel("📷 원본")
        original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_label.setObjectName("subtitleLabel")
        original_label.setFont(QFont("Segoe UI", 10))
        original_layout.addWidget(original_label)
        original_layout.addWidget(self.original_view)
        # views_layout.addWidget(original_container)
        self._splitter.addWidget(original_container)
        
        # Processed image view
        self.processed_scene = QGraphicsScene()
        self.processed_view = ZoomableGraphicsView()
        self.processed_view.setScene(self.processed_scene)
        self.processed_pixmap_item = QGraphicsPixmapItem()
        self.processed_scene.addItem(self.processed_pixmap_item)
        
        processed_container = QFrame()
        processed_container.setFrameStyle(QFrame.Shape.StyledPanel)
        processed_layout = QVBoxLayout(processed_container)
        processed_layout.setContentsMargins(8, 8, 8, 8)
        processed_layout.setSpacing(6)
        processed_label = QLabel("✂️ 처리 결과")
        processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        processed_label.setObjectName("subtitleLabel")
        processed_label.setFont(QFont("Segoe UI", 10))
        processed_layout.addWidget(processed_label)
        processed_layout.addWidget(self.processed_view)
        # views_layout.addWidget(processed_container)
        self._splitter.addWidget(processed_container)
        
        # Set initial sizes (equal)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        
        self._main_splitter.addWidget(self._splitter)
        
        # Controls bar
        controls_frame = QFrame()
        controls_frame.setObjectName("statsFrame")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(6)
        
        self.contour_check = QCheckBox("🔲 영역")
        self.contour_check.setChecked(True)
        self.contour_check.stateChanged.connect(self._on_contour_toggle)
        controls_layout.addWidget(self.contour_check)
        
        controls_layout.addStretch()
        
        # Zoom controls
        zoom_icon = QLabel("🔍")
        controls_layout.addWidget(zoom_icon)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        controls_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(40)
        self.zoom_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        controls_layout.addWidget(self.zoom_label)
        
        # Separator
        sep = QLabel("|")
        sep.setStyleSheet("color: #888888;")
        controls_layout.addWidget(sep)
        
        fit_btn = QPushButton("맞춤")
        fit_btn.setMaximumWidth(50)
        fit_btn.clicked.connect(self._fit_all)
        controls_layout.addWidget(fit_btn)
        
        reset_btn = QPushButton("1:1")
        reset_btn.setMaximumWidth(40)
        reset_btn.clicked.connect(self._reset_zoom)
        controls_layout.addWidget(reset_btn)
        
        self._main_splitter.addWidget(controls_frame)
        
        # Set main splitter stretch (Max space for image)
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 0)
        self._main_splitter.setCollapsible(1, True)
        
        layout.addWidget(self._main_splitter)
        
        # Connect zoom signals
        self.original_view.zoom_changed.connect(self._on_zoom_changed)
        self.processed_view.zoom_changed.connect(self._on_zoom_changed)
        
        # Initialize placeholder
        self.show_placeholder()
    
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
        """Handle zoom level change from view."""
        percent = int(zoom * 100)
        self.zoom_label.setText(f"{percent}%")
        # Sync slider without triggering signal
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(min(500, max(10, percent)))
        self.zoom_slider.blockSignals(False)
    
    def _on_zoom_slider_changed(self, value: int):
        """Handle zoom slider change."""
        zoom = value / 100.0
        self.zoom_label.setText(f"{value}%")
        # Apply zoom to both views
        self.original_view.resetTransform()
        self.original_view.scale(zoom, zoom)
        self.original_view._zoom = zoom
        self.processed_view.resetTransform()
        self.processed_view.scale(zoom, zoom)
        self.processed_view._zoom = zoom
    
    def _fit_all(self):
        """Fit all views."""
        self.original_view.fit_in_view()
        self.processed_view.fit_in_view()
        # Update slider
        self.zoom_slider.setValue(100)
    
    def _reset_zoom(self):
        """Reset all zooms."""
        self.original_view.reset_zoom()
        self.processed_view.reset_zoom()
        # Update slider
        self.zoom_slider.setValue(100)
    
    def clear(self):
        """Clear all images and show placeholder."""
        self._original_image = None
        self._processed_image = None
        self._contour_overlay = None
        
        self.show_placeholder()
    
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
