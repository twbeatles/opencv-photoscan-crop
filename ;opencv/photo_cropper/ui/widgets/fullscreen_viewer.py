#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fullscreen Viewer for Photo Cropper v9.0.

Provides fullscreen image preview with navigation.
"""

import os
import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QKeyEvent, QResizeEvent, QPainter, QColor

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FullscreenViewer(QWidget):
    """
    Fullscreen image viewer.
    
    Features:
        - F11 toggle fullscreen
        - Arrow keys for navigation
        - ESC to exit
        - Auto-hide controls
    """
    
    closed = pyqtSignal()
    image_changed = pyqtSignal(int)  # current index
    
    def __init__(
        self,
        images: Optional[List[str]] = None,
        current_index: int = 0,
        parent: Optional[QWidget] = None
    ):
        # Use frameless window for clean fullscreen
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        
        self._images = images or []
        self._current_index = current_index
        self._current_pixmap: Optional[QPixmap] = None
        
        self._controls_visible = True
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_controls)
        
        self._setup_ui()
        
        if self._images:
            self._load_current_image()
    
    def _setup_ui(self):
        """Setup UI components."""
        self.setStyleSheet("""
            FullscreenViewer {
                background-color: #000000;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.image_label, 1)
        
        # Controls overlay
        self.controls_frame = QFrame(self)
        self.controls_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
        
        controls_layout = QHBoxLayout(self.controls_frame)
        controls_layout.setContentsMargins(20, 10, 20, 10)
        controls_layout.setSpacing(15)
        
        # Previous button
        self.prev_btn = QPushButton("◀ 이전")
        self.prev_btn.clicked.connect(self._show_previous)
        controls_layout.addWidget(self.prev_btn)
        
        # Counter
        self.counter_label = QLabel()
        controls_layout.addWidget(self.counter_label)
        
        # Next button
        self.next_btn = QPushButton("다음 ▶")
        self.next_btn.clicked.connect(self._show_next)
        controls_layout.addWidget(self.next_btn)
        
        controls_layout.addStretch()
        
        # Filename
        self.filename_label = QLabel()
        controls_layout.addWidget(self.filename_label)
        
        controls_layout.addStretch()
        
        # Close button
        self.close_btn = QPushButton("✕ 닫기 (ESC)")
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)
        
        # Info label (top-right)
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                background-color: rgba(0, 0, 0, 0.5);
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.info_label.setText("F11: 전체화면 전환 | ←→: 이동 | ESC: 닫기")
        
        self.setMouseTracking(True)
    
    def show_fullscreen(self):
        """Show in fullscreen mode."""
        self.showFullScreen()
        self._position_controls()
        self._start_hide_timer()
    
    def _position_controls(self):
        """Position controls at bottom of screen."""
        # Bottom controls
        margin = 20
        controls_width = min(800, self.width() - margin * 2)
        controls_height = 60
        x = (self.width() - controls_width) // 2
        y = self.height() - controls_height - margin
        self.controls_frame.setGeometry(x, y, controls_width, controls_height)
        
        # Info label at top-right
        self.info_label.adjustSize()
        info_x = self.width() - self.info_label.width() - margin
        self.info_label.move(info_x, margin)
    
    def _load_current_image(self):
        """Load and display current image."""
        if not self._images or self._current_index < 0:
            return
        
        filepath = self._images[self._current_index]
        
        try:
            # Load image
            image = cv2.imread(filepath)
            if image is None:
                self.image_label.setText("이미지를 불러올 수 없습니다")
                return
            
            # Convert to QPixmap
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self._current_pixmap = QPixmap.fromImage(qimg)
            
            # Scale to fit
            self._display_scaled_image()
            
            # Update labels
            total = len(self._images)
            self.counter_label.setText(f"{self._current_index + 1} / {total}")
            self.filename_label.setText(os.path.basename(filepath))
            
            # Update navigation buttons
            self.prev_btn.setEnabled(self._current_index > 0)
            self.next_btn.setEnabled(self._current_index < total - 1)
            
            self.image_changed.emit(self._current_index)
            
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            self.image_label.setText(f"오류: {str(e)}")
    
    def _display_scaled_image(self):
        """Display image scaled to fit screen."""
        if self._current_pixmap is None:
            return
        
        # Available size (leave room for controls)
        available_w = self.width()
        available_h = self.height() - 100
        
        # Scale maintaining aspect ratio
        scaled = self._current_pixmap.scaled(
            available_w, available_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled)
    
    def _show_previous(self):
        """Show previous image."""
        if self._current_index > 0:
            self._current_index -= 1
            self._load_current_image()
    
    def _show_next(self):
        """Show next image."""
        if self._current_index < len(self._images) - 1:
            self._current_index += 1
            self._load_current_image()
    
    def set_images(self, images: List[str], start_index: int = 0):
        """
        Set image list to display.
        
        Args:
            images: List of image filepaths
            start_index: Starting image index
        """
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._load_current_image()
    
    def _show_controls(self):
        """Show controls."""
        self.controls_frame.show()
        self.info_label.show()
        self._controls_visible = True
    
    def _hide_controls(self):
        """Hide controls."""
        self.controls_frame.hide()
        self.info_label.hide()
        self._controls_visible = False
    
    def _start_hide_timer(self):
        """Start timer to auto-hide controls."""
        self._hide_timer.start(3000)  # Hide after 3 seconds
    
    def mouseMoveEvent(self, event):
        """Show controls on mouse move."""
        self._show_controls()
        self._start_hide_timer()
        super().mouseMoveEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation."""
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Left:
            self._show_previous()
        elif key == Qt.Key.Key_Right:
            self._show_next()
        elif key == Qt.Key.Key_Home:
            self._current_index = 0
            self._load_current_image()
        elif key == Qt.Key.Key_End:
            self._current_index = len(self._images) - 1
            self._load_current_image()
        elif key == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif key == Qt.Key.Key_Space:
            self._show_next()
        else:
            super().keyPressEvent(event)
        
        # Show controls on key press
        self._show_controls()
        self._start_hide_timer()
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize."""
        super().resizeEvent(event)
        self._position_controls()
        self._display_scaled_image()
    
    def closeEvent(self, event):
        """Handle close."""
        self.closed.emit()
        super().closeEvent(event)


class FullscreenViewerManager:
    """
    Manager class for fullscreen viewer.
    
    Provides easy integration with main window.
    """
    
    def __init__(self):
        self._viewer: Optional[FullscreenViewer] = None
    
    def show(
        self,
        images: List[str],
        current_index: int = 0,
        parent: Optional[QWidget] = None
    ):
        """
        Show fullscreen viewer.
        
        Args:
            images: List of image paths
            current_index: Starting index
            parent: Parent widget
        """
        if self._viewer:
            self._viewer.close()
        
        self._viewer = FullscreenViewer(images, current_index, parent)
        self._viewer.closed.connect(self._on_closed)
        self._viewer.show_fullscreen()
    
    def close(self):
        """Close viewer if open."""
        if self._viewer:
            self._viewer.close()
    
    def is_visible(self) -> bool:
        """Check if viewer is visible."""
        return self._viewer is not None and self._viewer.isVisible()
    
    def _on_closed(self):
        """Handle viewer closed."""
        self._viewer = None
