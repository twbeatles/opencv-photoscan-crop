#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toast Notification Widget for Photo Cropper.

Provides non-intrusive toast notifications with auto-dismiss functionality.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont


class ToastWidget(QWidget):
    """
    Toast notification widget that appears at the top-right of the parent window.
    
    Features:
        - Auto-dismiss after configurable duration
        - Fade in/out animations
        - Different styles for success, warning, error, info
    """
    
    # Style presets
    STYLES = {
        "success": {
            "background": "#00c880",
            "color": "#ffffff",
            "icon": "✓"
        },
        "warning": {
            "background": "#ffa500",
            "color": "#ffffff",
            "icon": "⚠"
        },
        "error": {
            "background": "#e94560",
            "color": "#ffffff",
            "icon": "✕"
        },
        "info": {
            "background": "#0f3460",
            "color": "#ffffff",
            "icon": "ℹ"
        }
    }
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._duration = 3000  # Default 3 seconds
        self._animation_duration = 300  # 300ms fade
        
        self._setup_ui()
        self._setup_animation()
        
        # Hide initially
        self.hide()
        
        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)
    
    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # Icon label
        self.icon_label = QLabel()
        self.icon_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.icon_label)
        
        # Message label
        self.message_label = QLabel()
        self.message_label.setFont(QFont("Segoe UI", 10))
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(400)
        layout.addWidget(self.message_label)
        
        self.setFixedHeight(50)
    
    def _setup_animation(self):
        """Setup fade animation."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(self._animation_duration)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    def show_toast(
        self, 
        message: str, 
        style: str = "info",
        duration: int = 3000
    ):
        """
        Show a toast notification.
        
        Args:
            message: The message to display
            style: One of "success", "warning", "error", "info"
            duration: Time in milliseconds before auto-dismiss
        """
        self._duration = duration
        
        # Get style preset
        preset = self.STYLES.get(style, self.STYLES["info"])
        
        # Apply style
        self.setStyleSheet(f"""
            ToastWidget {{
                background-color: {preset['background']};
                border-radius: 8px;
            }}
            QLabel {{
                color: {preset['color']};
                background-color: transparent;
            }}
        """)
        
        # Set content
        self.icon_label.setText(preset['icon'])
        self.message_label.setText(message)
        
        # Adjust size
        self.adjustSize()
        
        # Position at top-right of parent
        self._position_toast()
        
        # Show with fade in
        self._fade_in()
        
        # Start dismiss timer
        self._dismiss_timer.start(self._duration)
    
    def _position_toast(self):
        """Position toast at top-right of parent window."""
        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.right() - self.width() - 20
            y = parent_rect.top() + 60  # Below toolbar
            self.move(x, y)
    
    def _fade_in(self):
        """Fade in animation."""
        self.opacity_effect.setOpacity(0)
        self.show()
        self.raise_()
        
        self.fade_animation.stop()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def _fade_out(self):
        """Fade out animation."""
        self.fade_animation.stop()
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_fade_out_finished)
        self.fade_animation.start()
    
    def _on_fade_out_finished(self):
        """Handle fade out completion."""
        self.hide()
        self.fade_animation.finished.disconnect(self._on_fade_out_finished)
    
    def mousePressEvent(self, event):
        """Allow clicking to dismiss."""
        self._dismiss_timer.stop()
        self._fade_out()
