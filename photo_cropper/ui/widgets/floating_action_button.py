#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Floating Action Button for Photo Cropper v8.5.

Material Design-inspired FAB with expandable menu.
"""

import logging
from typing import Optional, List, Callable, Tuple

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QIcon

logger = logging.getLogger(__name__)


class FABAction:
    """Represents a FAB menu action."""
    
    def __init__(
        self,
        name: str,
        icon: str,  # emoji or text
        tooltip: str,
        callback: Callable,
        color: str = "#58a6ff"
    ):
        self.name = name
        self.icon = icon
        self.tooltip = tooltip
        self.callback = callback
        self.color = color


class MiniActionButton(QPushButton):
    """Small action button for FAB menu."""
    
    def __init__(
        self,
        action: FABAction,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.action = action
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup button UI."""
        self.setFixedSize(48, 48)
        self.setText(self.action.icon)
        self.setToolTip(self.action.tooltip)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.action.color};
                color: white;
                border: none;
                border-radius: 24px;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(self.action.color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(self.action.color)};
            }}
        """)
        
        self.clicked.connect(self.action.callback)
    
    @staticmethod
    def _lighten_color(hex_color: str) -> str:
        """Lighten a hex color."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def _darken_color(hex_color: str) -> str:
        """Darken a hex color."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
        return f"#{r:02x}{g:02x}{b:02x}"


class ActionLabel(QWidget):
    """Label shown next to mini action button."""
    
    def __init__(
        self,
        text: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        self.label = QLabel(text)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.label)


class FloatingActionButton(QWidget):
    """
    Floating Action Button with expandable menu.
    
    Features:
        - Main FAB button
        - Expandable action menu
        - Smooth animations
        - Auto-position in parent widget
    """
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        position: str = "bottom-right"  # bottom-right, bottom-left, top-right, top-left
    ):
        super().__init__(parent)
        
        self._position = position
        self._is_expanded = False
        self._actions: List[FABAction] = []
        self._action_widgets: List[Tuple[MiniActionButton, ActionLabel]] = []
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup FAB UI."""
        # Main layout (vertical for stacking action buttons above main FAB)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        # Container for action buttons (hidden initially)
        self.actions_container = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.actions_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.actions_container.hide()
        self.main_layout.addWidget(self.actions_container)
        
        # Main FAB button
        self.main_button = QPushButton()
        self.main_button.setFixedSize(56, 56)
        self.main_button.setText("+")
        self.main_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #58a6ff, stop:1 #1f6feb);
                color: white;
                border: none;
                border-radius: 28px;
                font-size: 28px;
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
        
        # Add shadow effect via stylesheet
        self.main_layout.addWidget(self.main_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setFixedSize(200, 400)  # Will be adjusted based on actions
    
    def add_action(self, action: FABAction):
        """Add an action to the FAB menu."""
        self._actions.append(action)
        self._rebuild_actions()
    
    def add_actions(self, actions: List[FABAction]):
        """Add multiple actions to the FAB menu."""
        self._actions.extend(actions)
        self._rebuild_actions()
    
    def clear_actions(self):
        """Clear all actions."""
        self._actions.clear()
        self._rebuild_actions()
    
    def _rebuild_actions(self):
        """Rebuild action button widgets."""
        # Clear existing
        for btn, label in self._action_widgets:
            btn.deleteLater()
            label.deleteLater()
        self._action_widgets.clear()
        
        # Clear layout
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create new buttons
        for action in self._actions:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            
            label = ActionLabel(action.tooltip, row)
            row_layout.addWidget(label)
            
            btn = MiniActionButton(action, row)
            btn.clicked.connect(self._collapse)  # Collapse on action click
            row_layout.addWidget(btn)
            
            self.actions_layout.addWidget(row)
            self._action_widgets.append((btn, label))
        
        # Adjust widget size
        height = 80 + len(self._actions) * 60
        self.setFixedHeight(height)
    
    def _toggle_expand(self):
        """Toggle expanded state."""
        if self._is_expanded:
            self._collapse()
        else:
            self._expand()
    
    def _expand(self):
        """Expand the FAB menu."""
        self._is_expanded = True
        self.main_button.setText("×")
        
        # Rotate animation for main button would go here
        # For simplicity, just show the container
        self.actions_container.show()
        
        # Animate opacity
        for btn, label in self._action_widgets:
            effect = QGraphicsOpacityEffect(btn)
            btn.setGraphicsEffect(effect)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0)
            anim.setEndValue(1)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
    
    def _collapse(self):
        """Collapse the FAB menu."""
        self._is_expanded = False
        self.main_button.setText("+")
        self.actions_container.hide()
    
    def position_in_parent(self):
        """Position FAB in parent widget."""
        if self.parent() is None:
            return
        
        parent = self.parent()
        margin = 20
        
        if "right" in self._position:
            x = parent.width() - self.width() - margin
        else:
            x = margin
        
        if "bottom" in self._position:
            y = parent.height() - self.height() - margin
        else:
            y = margin
        
        self.move(x, y)
    
    def set_visible_animated(self, visible: bool):
        """Show/hide with animation."""
        if visible:
            self.show()
            # Could add slide-in animation here
        else:
            self._collapse()
            self.hide()


class QuickActionFAB(FloatingActionButton):
    """
    Pre-configured FAB with common quick actions for Photo Cropper.
    """
    
    # Signals
    preview_requested = pyqtSignal()
    process_requested = pyqtSignal()
    rotate_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    fullscreen_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, "bottom-right")
        
        self._setup_actions()
    
    def _setup_actions(self):
        """Setup default quick actions."""
        actions = [
            FABAction(
                name="preview",
                icon="👁",
                tooltip="미리보기 (Ctrl+P)",
                callback=lambda: self.preview_requested.emit(),
                color="#238636"
            ),
            FABAction(
                name="process",
                icon="▶",
                tooltip="변환 시작",
                callback=lambda: self.process_requested.emit(),
                color="#1f6feb"
            ),
            FABAction(
                name="rotate",
                icon="↻",
                tooltip="회전 (Ctrl+R)",
                callback=lambda: self.rotate_requested.emit(),
                color="#8957e5"
            ),
            FABAction(
                name="fullscreen",
                icon="⛶",
                tooltip="전체화면 (F11)",
                callback=lambda: self.fullscreen_requested.emit(),
                color="#f0883e"
            ),
            FABAction(
                name="settings",
                icon="⚙",
                tooltip="설정",
                callback=lambda: self.settings_requested.emit(),
                color="#8b949e"
            ),
        ]
        
        self.add_actions(actions)
