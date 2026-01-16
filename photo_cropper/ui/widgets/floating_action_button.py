#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Floating Action Button for Photo Cropper v9.0.

Material Design-inspired FAB with expandable menu.
Fixed positioning and click handling.
"""

import logging
from typing import Optional, List, Callable

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, QTimer
)
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class FABMenuItem(QPushButton):
    """Individual menu item button for the FAB."""
    
    def __init__(
        self,
        icon: str,
        tooltip: str,
        color: str = "#58a6ff",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.setFixedSize(44, 44)
        self.setText(icon)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {self._adjust_color(color, 30)};
            }}
            QPushButton:pressed {{
                background-color: {self._adjust_color(color, -30)};
            }}
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
    
    @staticmethod
    def _adjust_color(hex_color: str, amount: int) -> str:
        """Lighten or darken a hex color."""
        hex_color = hex_color.lstrip('#')
        r = max(0, min(255, int(hex_color[0:2], 16) + amount))
        g = max(0, min(255, int(hex_color[2:4], 16) + amount))
        b = max(0, min(255, int(hex_color[4:6], 16) + amount))
        return f"#{r:02x}{g:02x}{b:02x}"


class FABMenuRow(QWidget):
    """A row containing label + button for the FAB menu."""
    
    clicked = pyqtSignal()
    
    def __init__(
        self,
        icon: str,
        label_text: str,
        color: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Label (on left)
        self.label = QLabel(label_text)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 0.9);
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.label)
        
        # Button (on right)
        self.button = FABMenuItem(icon, label_text, color, self)
        self.button.clicked.connect(self.clicked.emit)
        layout.addWidget(self.button)


class QuickActionFAB(QWidget):
    """
    Floating Action Button with expandable menu.
    
    Fixed version with proper positioning and click handling.
    """
    
    # Signals
    preview_requested = pyqtSignal()
    process_requested = pyqtSignal()
    rotate_requested = pyqtSignal()
    fullscreen_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._is_expanded = False
        self._menu_items: List[FABMenuRow] = []
        
        # Make transparent but clickable
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._create_menu_items()
        
        # Install event filter on parent for repositioning
        if parent:
            parent.installEventFilter(self)
    
    def _setup_ui(self):
        """Setup FAB UI."""
        # Main vertical layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        # Menu container (hidden initially)
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(6)
        self.menu_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.menu_container.hide()
        self.main_layout.addWidget(self.menu_container)
        
        # Main FAB button
        self.main_button = QPushButton("+")
        self.main_button.setFixedSize(56, 56)
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #58a6ff, stop:1 #1f6feb);
                color: white;
                border: none;
                border-radius: 28px;
                font-size: 26px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #79b8ff, stop:1 #388bfd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #1f6feb, stop:1 #0550ae);
            }
        """)
        self.main_button.clicked.connect(self._toggle_expand)
        
        # Add shadow to main button
        shadow = QGraphicsDropShadowEffect(self.main_button)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.main_button.setGraphicsEffect(shadow)
        
        self.main_layout.addWidget(self.main_button, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _create_menu_items(self):
        """Create the menu items."""
        items = [
            ("👁", "미리보기", "#238636", self.preview_requested),
            ("▶", "변환 시작", "#1f6feb", self.process_requested),
            ("↻", "회전", "#8957e5", self.rotate_requested),
            ("⛶", "전체화면", "#f0883e", self.fullscreen_requested),
        ]
        
        for icon, label, color, signal in items:
            row = FABMenuRow(icon, label, color, self.menu_container)
            row.clicked.connect(signal.emit)
            row.clicked.connect(self._collapse)
            self.menu_layout.addWidget(row)
            self._menu_items.append(row)
        
        # Update size based on items
        self._update_size()
    
    def _update_size(self):
        """Update widget size based on content."""
        # Calculate height: main button + menu items + margins
        base_height = 56 + 16  # Main button + margins
        menu_height = len(self._menu_items) * 56 if self._is_expanded else 0
        
        width = 220  # Fixed width for labels + buttons
        height = base_height + menu_height + 50  # Extra padding
        
        self.setFixedSize(width, height + 200)  # Extra space for expanded menu
    
    def _toggle_expand(self):
        """Toggle expanded state."""
        if self._is_expanded:
            self._collapse()
        else:
            self._expand()
    
    def _expand(self):
        """Expand the menu."""
        self._is_expanded = True
        self.main_button.setText("×")
        self.menu_container.show()
        self._update_position()
    
    def _collapse(self):
        """Collapse the menu."""
        self._is_expanded = False
        self.main_button.setText("+")
        self.menu_container.hide()
    
    def _update_position(self):
        """Update FAB position in parent."""
        if not self.parent():
            return
        
        parent = self.parent()
        margin = 20
        
        # Position in bottom-right
        x = parent.width() - self.width() - margin
        y = parent.height() - self.height() + 150  # Offset because of extra height
        
        self.move(max(0, x), max(0, y))
    
    def eventFilter(self, obj, event):
        """Handle parent resize events."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Resize:
            # Delay position update
            QTimer.singleShot(10, self._update_position)
        return super().eventFilter(obj, event)
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        QTimer.singleShot(100, self._update_position)
    
    def resizeEvent(self, event):
        """Handle resize."""
        super().resizeEvent(event)
        self._update_position()


# Keep old class name for compatibility
FloatingActionButton = QuickActionFAB
