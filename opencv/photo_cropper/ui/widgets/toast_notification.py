#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toast Notification Widget for Photo Cropper.

Provides non-intrusive, animated toast notifications for user feedback.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt6.QtGui import QFont


class ToastNotification(QWidget):
    """
    Animated toast notification widget.
    
    Features:
        - Slide-in/out animation
        - Auto-dismiss with configurable duration
        - Success/Warning/Error/Info types
        - Non-blocking
        - Gradient backgrounds
    """
    
    # Signal emitted when toast is closed
    closed = pyqtSignal()
    
    # Toast types with gradient colors and icons
    TOAST_TYPES = {
        "success": {"icon": "✅", "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #34d399)", "text": "#ffffff"},
        "error": {"icon": "❌", "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #f87171)", "text": "#ffffff"},
        "warning": {"icon": "⚠️", "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #fbbf24)", "text": "#1f2937"},
        "info": {"icon": "ℹ️", "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #818cf8)", "text": "#ffffff"},
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._duration = 3000  # Default 3 seconds
        self._animation_duration = 300  # Animation duration in ms
        self._is_showing = False
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self._setup_ui()
        self._setup_animations()
        
        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide_toast)
    
    def _setup_ui(self):
        """Setup UI components."""
        self.setFixedHeight(50)
        self.setMinimumWidth(200)
        self.setMaximumWidth(500)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)
        
        # Icon label
        self.icon_label = QLabel()
        self.icon_label.setFont(QFont("Segoe UI Emoji", 14))
        layout.addWidget(self.icon_label)
        
        # Message label
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.message_label, 1)
    
    def _setup_animations(self):
        """Setup slide animations."""
        # Opacity effect for fade
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Slide animation
        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(self._animation_duration)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity animation
        self._opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self._opacity_animation.setDuration(self._animation_duration)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def show_toast(
        self,
        message: str,
        toast_type: str = "info",
        duration: int | None = None,
    ):
        """
        Show toast notification.
        
        Args:
            message: Message to display
            toast_type: Type of toast (success, error, warning, info)
            duration: Auto-dismiss duration in ms (None for default)
        """
        if toast_type not in self.TOAST_TYPES:
            toast_type = "info"
        
        style = self.TOAST_TYPES[toast_type]
        
        # Apply styling
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {style['bg']};
                border-radius: 10px;
            }}
            QLabel {{
                color: {style['text']};
                background-color: transparent;
            }}
        """)
        
        # Set content
        self.icon_label.setText(style['icon'])
        self.message_label.setText(message)
        
        # Adjust width based on message length
        self.adjustSize()
        
        # Position at bottom center of parent
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            parent_rect = parent_widget.rect()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.bottom() - self.height() - 30
            
            # Start position (below screen)
            start_pos = QPoint(x, parent_rect.bottom())
            end_pos = QPoint(x, y)
            
            self.move(start_pos)
            
            # Configure slide animation
            self._slide_animation.setStartValue(start_pos)
            self._slide_animation.setEndValue(end_pos)
        
        # Configure opacity animation
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        
        # Show and animate
        self._is_showing = True
        self.show()
        self._slide_animation.start()
        self._opacity_animation.start()
        
        # Start dismiss timer
        dismiss_duration = duration or self._duration
        self._dismiss_timer.start(dismiss_duration)
    
    def hide_toast(self):
        """Hide toast with animation."""
        if not self._is_showing:
            return
        
        self._dismiss_timer.stop()
        
        # Reverse animations
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            parent_rect = parent_widget.rect()
            x = self.x()
            end_pos = QPoint(x, parent_rect.bottom())
            
            self._slide_animation.setStartValue(self.pos())
            self._slide_animation.setEndValue(end_pos)
        
        self._opacity_animation.setStartValue(1.0)
        self._opacity_animation.setEndValue(0.0)
        
        # Connect to hide when animation finishes
        self._opacity_animation.finished.connect(self._on_hide_finished)
        
        self._slide_animation.start()
        self._opacity_animation.start()
    
    def _on_hide_finished(self):
        """Handle hide animation finished."""
        self._opacity_animation.finished.disconnect(self._on_hide_finished)
        self._is_showing = False
        self.hide()
        self.closed.emit()
    
    def set_duration(self, duration: int):
        """Set default auto-dismiss duration in milliseconds."""
        self._duration = duration
    
    def mousePressEvent(self, event):
        """Dismiss on click."""
        self.hide_toast()


class ToastManager:
    """
    Manager for showing toast notifications.
    
    Provides a simple interface for showing toasts from anywhere in the app.
    """
    
    _instance = None
    _parent = None
    _current_toast = None
    
    @classmethod
    def set_parent(cls, parent: QWidget):
        """Set parent widget for positioning toasts."""
        cls._parent = parent
    
    @classmethod
    def show(cls, message: str, toast_type: str = "info", duration: int = 3000):
        """
        Show a toast notification.
        
        Args:
            message: Message to display
            toast_type: Type (success, error, warning, info)
            duration: Auto-dismiss duration in ms
        """
        if cls._parent is None:
            return
        
        # Hide current toast if showing
        if cls._current_toast and cls._current_toast._is_showing:
            cls._current_toast.hide()
        
        # Create new toast
        cls._current_toast = ToastNotification(cls._parent)
        cls._current_toast.show_toast(message, toast_type, duration)
    
    @classmethod
    def success(cls, message: str, duration: int = 3000):
        """Show success toast."""
        cls.show(message, "success", duration)
    
    @classmethod
    def error(cls, message: str, duration: int = 4000):
        """Show error toast."""
        cls.show(message, "error", duration)
    
    @classmethod
    def warning(cls, message: str, duration: int = 3500):
        """Show warning toast."""
        cls.show(message, "warning", duration)
    
    @classmethod
    def info(cls, message: str, duration: int = 3000):
        """Show info toast."""
        cls.show(message, "info", duration)
