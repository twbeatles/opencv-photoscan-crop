#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Compare Window for Photo Cropper v9.0.

Provides multi-image comparison in a separate window:
- 2-4 images side by side
- Synchronized zoom and pan
- Independent preset application
- Various layout options
"""

import numpy as np
import cv2
from typing import Optional, List, Tuple
from enum import Enum

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QToolBar,
    QSplitter, QFrame, QScrollArea, QSizePolicy, QFileDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QAction, QIcon

from ..widgets.toast_notification import ToastManager
from ...core.smart_enhancer import SmartEnhancer, EnhancementPreset, get_smart_enhancer


def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert numpy array to QPixmap."""
    if image is None:
        return QPixmap()
    
    if len(image.shape) == 2:
        h, w = image.shape
        bytes_per_line = w
        qimage = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
    else:
        h, w, ch = image.shape
        if ch == 4:
            bytes_per_line = 4 * w
            qimage = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        else:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w
            qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    
    return QPixmap.fromImage(qimage.copy())


class CompareLayout(Enum):
    """Comparison layout options."""
    HORIZONTAL_2 = "2x1"      # 2 images horizontal
    VERTICAL_2 = "1x2"        # 2 images vertical
    GRID_4 = "2x2"            # 4 images grid
    HORIZONTAL_4 = "4x1"      # 4 images horizontal


class SyncedGraphicsView(QGraphicsView):
    """Graphics view with synchronized zoom/pan."""
    
    zoom_changed = pyqtSignal(float)
    pan_changed = pyqtSignal(QPointF)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._original_image: Optional[np.ndarray] = None
        self._zoom_level = 1.0
        self._is_panning = False
        self._pan_start = QPointF()
        
        self._sync_enabled = True
        self._ignore_sync = False
        
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setStyleSheet("""
            QGraphicsView {
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                background-color: #1a1a2e;
            }
        """)
    
    def set_image(self, image: np.ndarray, title: str = ""):
        """Set image to display."""
        self._original_image = image
        
        if self._pixmap_item:
            self._scene.removeItem(self._pixmap_item)
        
        pixmap = numpy_to_qpixmap(image)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        
        self.fit_in_view()
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get current image."""
        return self._original_image
    
    def fit_in_view(self):
        """Fit image to view."""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_level = self.transform().m11()
    
    def set_sync_enabled(self, enabled: bool):
        """Enable/disable synchronization."""
        self._sync_enabled = enabled
    
    def set_zoom(self, zoom: float, from_sync: bool = False):
        """Set zoom level."""
        if from_sync and not self._sync_enabled:
            return
        
        if from_sync:
            self._ignore_sync = True
        
        scale_factor = zoom / self._zoom_level
        self.scale(scale_factor, scale_factor)
        self._zoom_level = zoom
        
        if not from_sync and self._sync_enabled:
            self.zoom_changed.emit(zoom)
        
        self._ignore_sync = False
    
    def set_center(self, center: QPointF, from_sync: bool = False):
        """Set view center."""
        if from_sync and not self._sync_enabled:
            return
        
        if from_sync:
            self._ignore_sync = True
        
        self.centerOn(center)
        
        if not from_sync and self._sync_enabled:
            self.pan_changed.emit(center)
        
        self._ignore_sync = False
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom."""
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        
        self._zoom_level = self.transform().m11()
        
        if self._sync_enabled:
            self.zoom_changed.emit(self._zoom_level)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle pan and emit sync signal."""
        super().mouseMoveEvent(event)
        
        if self._sync_enabled and event.buttons() == Qt.MouseButton.LeftButton:
            center = self.mapToScene(self.viewport().rect().center())
            self.pan_changed.emit(center)


class ImagePanel(QFrame):
    """Panel containing image view with controls."""
    
    image_changed = pyqtSignal()
    
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self._enhancer = get_smart_enhancer()
        self._original_image: Optional[np.ndarray] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Header with title and controls
        header = QHBoxLayout()
        
        self.title_label = QLabel(f"이미지 {self.index + 1}")
        self.title_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        # Preset selector
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("원본", EnhancementPreset.NONE)
        preset_names = self._enhancer.get_preset_names()
        for preset, name in preset_names.items():
            if preset != EnhancementPreset.NONE:
                self.preset_combo.addItem(name, preset)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preset_combo.setMaximumWidth(120)
        header.addWidget(self.preset_combo)
        
        # Load button
        self.load_btn = QPushButton("📂")
        self.load_btn.setMaximumWidth(30)
        self.load_btn.setToolTip("이미지 불러오기")
        self.load_btn.clicked.connect(self._on_load_clicked)
        header.addWidget(self.load_btn)
        
        layout.addLayout(header)
        
        # Image view
        self.view = SyncedGraphicsView()
        layout.addWidget(self.view, 1)
        
        self.setStyleSheet("""
            ImagePanel {
                background-color: #252535;
                border-radius: 8px;
            }
        """)
    
    def set_image(self, image: np.ndarray, title: str = ""):
        """Set image to display."""
        self._original_image = image.copy() if image is not None else None
        self.view.set_image(image, title)
        
        if title:
            self.title_label.setText(title)
        
        self.image_changed.emit()
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get current image."""
        return self.view.get_image()
    
    def _on_preset_changed(self, index: int):
        """Handle preset change."""
        if self._original_image is None:
            return
        
        preset = self.preset_combo.currentData()
        if preset == EnhancementPreset.NONE:
            self.view.set_image(self._original_image)
        else:
            result = self._enhancer.apply_preset(self._original_image, preset)
            self.view.set_image(result.image)
    
    def _on_load_clicked(self):
        """Handle load button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.webp *.bmp);;모든 파일 (*.*)"
        )
        
        if file_path:
            image = cv2.imdecode(
                np.fromfile(file_path, dtype=np.uint8),
                cv2.IMREAD_COLOR
            )
            if image is not None:
                title = file_path.split('/')[-1].split('\\')[-1]
                self.set_image(image, title)


class MultiCompareWindow(QMainWindow):
    """
    Multi-image comparison window.
    
    Features:
    - 2-4 image slots
    - Synchronized zoom/pan
    - Per-image preset application
    - Multiple layout options
    """
    
    MAX_IMAGES = 4
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._panels: List[ImagePanel] = []
        self._sync_enabled = True
        self._current_layout = CompareLayout.HORIZONTAL_2
        
        self._setup_window()
        self._setup_toolbar()
        self._setup_central_widget()
        self._connect_sync_signals()
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("멀티 이미지 비교")
        self.resize(1200, 700)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QToolBar {
                background-color: #252535;
                border: none;
                padding: 4px;
                spacing: 8px;
            }
            QToolButton {
                background-color: transparent;
                color: #e0e0e0;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3d3d5c;
            }
            QToolButton:checked {
                background-color: #4a4a6a;
            }
            QComboBox {
                background-color: #2d2d44;
                color: #e0e0e0;
                border: 1px solid #3d3d5c;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QCheckBox {
                color: #e0e0e0;
            }
        """)
    
    def _setup_toolbar(self):
        """Create toolbar."""
        toolbar = QToolBar("도구")
        toolbar.setObjectName("compareToolBar")
        self.addToolBar(toolbar)
        
        # Layout selector
        toolbar.addWidget(QLabel("레이아웃: "))
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("2개 가로", CompareLayout.HORIZONTAL_2)
        self.layout_combo.addItem("2개 세로", CompareLayout.VERTICAL_2)
        self.layout_combo.addItem("4개 그리드", CompareLayout.GRID_4)
        self.layout_combo.addItem("4개 가로", CompareLayout.HORIZONTAL_4)
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        toolbar.addWidget(self.layout_combo)
        
        toolbar.addSeparator()
        
        # Sync checkbox
        self.sync_checkbox = QCheckBox("동기화")
        self.sync_checkbox.setChecked(True)
        self.sync_checkbox.stateChanged.connect(self._on_sync_changed)
        toolbar.addWidget(self.sync_checkbox)
        
        toolbar.addSeparator()
        
        # Fit all button
        fit_action = QAction("전체 맞춤", self)
        fit_action.triggered.connect(self._fit_all)
        toolbar.addAction(fit_action)
        
        # Reset all button
        reset_action = QAction("모두 초기화", self)
        reset_action.triggered.connect(self._reset_all)
        toolbar.addAction(reset_action)
    
    def _setup_central_widget(self):
        """Create central widget with panels."""
        central = QWidget()
        self.setCentralWidget(central)
        
        self._main_layout = QGridLayout(central)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(8)
        
        # Create 4 panels
        for i in range(self.MAX_IMAGES):
            panel = ImagePanel(i)
            self._panels.append(panel)
        
        # Initial layout
        self._apply_layout(CompareLayout.HORIZONTAL_2)
    
    def _connect_sync_signals(self):
        """Connect synchronization signals."""
        for panel in self._panels:
            panel.view.zoom_changed.connect(self._on_zoom_changed)
            panel.view.pan_changed.connect(self._on_pan_changed)
    
    def _apply_layout(self, layout: CompareLayout):
        """Apply layout to panels."""
        # Clear current layout
        for i in reversed(range(self._main_layout.count())):
            self._main_layout.itemAt(i).widget().setParent(None)
        
        # Hide all panels first
        for panel in self._panels:
            panel.hide()
        
        if layout == CompareLayout.HORIZONTAL_2:
            self._main_layout.addWidget(self._panels[0], 0, 0)
            self._main_layout.addWidget(self._panels[1], 0, 1)
            self._panels[0].show()
            self._panels[1].show()
            
        elif layout == CompareLayout.VERTICAL_2:
            self._main_layout.addWidget(self._panels[0], 0, 0)
            self._main_layout.addWidget(self._panels[1], 1, 0)
            self._panels[0].show()
            self._panels[1].show()
            
        elif layout == CompareLayout.GRID_4:
            self._main_layout.addWidget(self._panels[0], 0, 0)
            self._main_layout.addWidget(self._panels[1], 0, 1)
            self._main_layout.addWidget(self._panels[2], 1, 0)
            self._main_layout.addWidget(self._panels[3], 1, 1)
            for panel in self._panels:
                panel.show()
                
        elif layout == CompareLayout.HORIZONTAL_4:
            for i, panel in enumerate(self._panels):
                self._main_layout.addWidget(panel, 0, i)
                panel.show()
        
        self._current_layout = layout
    
    def _on_layout_changed(self, index: int):
        """Handle layout change."""
        layout = self.layout_combo.currentData()
        self._apply_layout(layout)
    
    def _on_sync_changed(self, state: int):
        """Handle sync checkbox change."""
        self._sync_enabled = state == Qt.CheckState.Checked.value
        for panel in self._panels:
            panel.view.set_sync_enabled(self._sync_enabled)
    
    def _on_zoom_changed(self, zoom: float):
        """Handle zoom sync."""
        if not self._sync_enabled:
            return
        
        sender = self.sender()
        for panel in self._panels:
            if panel.view != sender and panel.isVisible():
                panel.view.set_zoom(zoom, from_sync=True)
    
    def _on_pan_changed(self, center: QPointF):
        """Handle pan sync."""
        if not self._sync_enabled:
            return
        
        sender = self.sender()
        for panel in self._panels:
            if panel.view != sender and panel.isVisible():
                panel.view.set_center(center, from_sync=True)
    
    def _fit_all(self):
        """Fit all visible images."""
        for panel in self._panels:
            if panel.isVisible():
                panel.view.fit_in_view()
    
    def _reset_all(self):
        """Reset all panels."""
        for panel in self._panels:
            panel.preset_combo.setCurrentIndex(0)
            if panel._original_image is not None:
                panel.view.set_image(panel._original_image)
                panel.view.fit_in_view()
    
    def add_image(self, image: np.ndarray, title: str = "", slot: int = -1):
        """
        Add image to comparison.
        
        Args:
            image: Image array
            title: Image title
            slot: Specific slot index (-1 for first empty)
        """
        if slot >= 0 and slot < len(self._panels):
            self._panels[slot].set_image(image, title)
        else:
            # Find first empty slot
            for panel in self._panels:
                if panel.get_image() is None:
                    panel.set_image(image, title)
                    break
    
    def set_images(self, images: List[Tuple[np.ndarray, str]]):
        """
        Set multiple images at once.
        
        Args:
            images: List of (image, title) tuples
        """
        for i, (image, title) in enumerate(images[:self.MAX_IMAGES]):
            self._panels[i].set_image(image, title)
    
    def clear_all(self):
        """Clear all images."""
        for panel in self._panels:
            panel.set_image(None)
            panel.title_label.setText(f"이미지 {panel.index + 1}")
