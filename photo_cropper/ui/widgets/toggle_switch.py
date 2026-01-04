#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern Toggle Switch Widget.
"""

from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QPoint, QEasingCurve, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QPen

class ModernToggleSwitch(QCheckBox):
    """
    iOS-style modern toggle switch.
    Inherits from QCheckBox for easy integration (stateChanged signal).
    """
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # Style parameters
        self._track_radius = 12
        self._thumb_radius = 10
        self._margin = 2
        self._base_height = 24
        
        # Colors (from themes.py or default)
        self._track_off_color = QColor("#30363d")
        self._track_on_color = QColor("#238636") # Success green
        self._thumb_color = QColor("#ffffff")
        self._text_color = QColor("#f0f6fc")
        
        # Animation
        self._thumb_pos = 0.0 # 0.0 to 1.0
        self._animation = QPropertyAnimation(self, b"thumb_pos", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Setup
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._start_animation)
        
        # Initialize position
        self._thumb_pos = 1.0 if self.isChecked() else 0.0
        
    @pyqtProperty(float)
    def thumb_pos(self):
        return self._thumb_pos
        
    @thumb_pos.setter
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()
        
    def _start_animation(self, checked):
        self._animation.setStartValue(self._thumb_pos)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()
        
    def hitButton(self, pos: QPoint):
        """Override to make the whole area clickable."""
        return self.rect().contains(pos)
        
    def paintEvent(self, event):
        """Custom paint event."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dimensions
        track_width = 44
        track_height = self._base_height
        
        # Draw text
        rect = self.rect()
        text_rect = rect.adjusted(track_width + 10, 0, 0, 0)
        painter.setPen(self._text_color)
        painter.setFont(self.font())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        
        # Draw track
        track_rect = QRectF(0, (rect.height() - track_height) / 2, track_width, track_height)
        
        # Interpolate color
        if self.isChecked():
            color = self._track_on_color
        else:
            color = self._track_off_color
            
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, track_height / 2, track_height / 2)
        
        # Draw thumb
        thumb_size = self._thumb_radius * 2
        thumb_range = track_width - thumb_size - (self._margin * 2)
        thumb_x = self._margin + (thumb_range * self._thumb_pos)
        thumb_y = track_rect.y() + self._margin
        
        thumb_rect = QRectF(thumb_x, thumb_y, thumb_size, thumb_size)
        painter.setBrush(QBrush(self._thumb_color))
        painter.drawEllipse(thumb_rect)
