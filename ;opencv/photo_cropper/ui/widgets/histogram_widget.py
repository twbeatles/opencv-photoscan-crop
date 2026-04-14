#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Histogram Widget for Photo Cropper.

Displays RGB histogram of images.
"""

import numpy as np
import cv2
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath

from ...i18n.catalog import t


class HistogramWidget(QWidget):
    """
    Widget to display image histogram.
    
    Shows RGB channels as overlapping curves.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._histograms = None  # List of (color, histogram_data)
        self._background_color = QColor(30, 30, 50)
        
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
    
    def set_image(self, image: np.ndarray):
        """
        Calculate and display histogram for image.
        
        Args:
            image: OpenCV image (BGR or Grayscale)
        """
        if image is None:
            self._histograms = None
            self.update()
            return
        
        histograms = []
        
        if len(image.shape) == 2:
            # Grayscale
            hist = cv2.calcHist([image], [0], None, [256], [0, 256])
            hist = hist.flatten()
            histograms.append((QColor(200, 200, 200), hist))
        else:
            # Color (BGR)
            colors = [
                (QColor(100, 100, 255), 0),  # Blue
                (QColor(100, 255, 100), 1),  # Green
                (QColor(255, 100, 100), 2),  # Red
            ]
            
            for color, channel in colors:
                hist = cv2.calcHist([image], [channel], None, [256], [0, 256])
                hist = hist.flatten()
                histograms.append((color, hist))
        
        self._histograms = histograms
        self.update()
    
    def clear(self):
        """Clear histogram display."""
        self._histograms = None
        self.update()
    
    def paintEvent(self, event):
        """Paint the histogram."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self._background_color)
        
        if not self._histograms:
            # Draw placeholder text
            painter.setPen(QPen(QColor(100, 100, 100)))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                t("histogram.placeholder"),
            )
            return
        
        # Dimensions
        w = self.width()
        h = self.height()
        margin = 5
        
        # Find max value for normalization
        if not self._histograms:
            return
        max_val = max((np.max(hist) for _, hist in self._histograms), default=0)
        if max_val == 0:
            return
        
        # Draw each histogram
        for color, hist in self._histograms:
            pen = QPen(color)
            pen.setWidth(1)
            painter.setPen(pen)
            
            # Create path
            path = QPainterPath()
            
            for i, val in enumerate(hist):
                x = margin + (i / 255) * (w - 2 * margin)
                y = h - margin - (val / max_val) * (h - 2 * margin)
                
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            
            # Set semi-transparent color for fill
            fill_color = QColor(color)
            fill_color.setAlpha(50)
            
            # Draw path
            painter.drawPath(path)
