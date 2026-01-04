#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme definitions for Photo Cropper PyQt6 UI v8.0.

Provides dark and light themes with:
- Glassmorphism effects
- Enhanced gradients and shadows
- Micro-animations and hover transitions
- Modern card-based UI patterns
"""

from typing import Dict

# Common style values
FONT_FAMILY = "'Segoe UI', 'Malgun Gothic', -apple-system, BlinkMacSystemFont, sans-serif"
BORDER_RADIUS = "8px"
BORDER_RADIUS_LG = "12px"
PADDING_SM = "4px"
PADDING_MD = "8px"
PADDING_LG = "12px"
PADDING_XL = "16px"
BOX_SHADOW = "0 4px 20px rgba(0, 0, 0, 0.15)"
BOX_SHADOW_HOVER = "0 8px 30px rgba(0, 0, 0, 0.25)"

# Color palette - Dark theme (enhanced for glassmorphism)
DARK_COLORS = {
    "bg_primary": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "bg_glass": "rgba(22, 27, 34, 0.85)",
    "accent": "#58a6ff",
    "accent_hover": "#79b8ff",
    "accent_glow": "rgba(88, 166, 255, 0.3)",
    "success": "#3fb950",
    "success_glow": "rgba(63, 185, 80, 0.3)",
    "warning": "#d29922",
    "error": "#f85149",
    "error_glow": "rgba(248, 81, 73, 0.3)",
    "text_primary": "#f0f6fc",
    "text_secondary": "#c9d1d9",
    "text_muted": "#8b949e",
    "border": "#30363d",
    "border_subtle": "rgba(48, 54, 61, 0.5)",
    "border_focus": "#58a6ff",
    "gradient_start": "#238636",
    "gradient_end": "#2ea043",
}

# Color palette - Light theme (enhanced for glassmorphism)
LIGHT_COLORS = {
    "bg_primary": "#f6f8fa",
    "bg_secondary": "#ffffff",
    "bg_tertiary": "#ebeef1",
    "bg_glass": "rgba(255, 255, 255, 0.9)",
    "accent": "#0969da",
    "accent_hover": "#0550ae",
    "accent_glow": "rgba(9, 105, 218, 0.2)",
    "success": "#1a7f37",
    "success_glow": "rgba(26, 127, 55, 0.2)",
    "warning": "#9a6700",
    "error": "#cf222e",
    "error_glow": "rgba(207, 34, 46, 0.2)",
    "text_primary": "#1f2328",
    "text_secondary": "#57606a",
    "text_muted": "#8c959f",
    "border": "#d0d7de",
    "border_subtle": "rgba(208, 215, 222, 0.5)",
    "border_focus": "#0969da",
    "gradient_start": "#2ea043",
    "gradient_end": "#3fb950",
}


DARK_THEME = """
/* ============================================
   DARK THEME - Glassmorphism & Modern UI v8.0
   ============================================ */

/* Main Window & Global Backgrounds */
QMainWindow, QDialog, QMessageBox {
    background-color: #0d1117;
}

QWidget {
    background-color: transparent;
    color: #f0f6fc;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 10pt;
}

/* Glassmorphism Cards & Containers */
QFrame#statsFrame, QGroupBox, QTabWidget::pane {
    background-color: rgba(22, 27, 34, 0.7);
    border: 1px solid rgba(48, 54, 61, 0.5);
    border-radius: 12px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

/* Group Box - Enhanced Header */
QGroupBox {
    margin-top: 24px;
    padding: 20px 12px 12px 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 6px 12px;
    background-color: #21262d;
    border: 1px solid rgba(48, 54, 61, 0.5);
    border-radius: 6px;
    color: #58a6ff;
    left: 12px;
}

/* Tab Widget - Modern Pills Style */
QTabWidget::pane {
    padding: 16px;
    border-radius: 12px;
}

QTabBar::tab {
    background-color: transparent;
    color: #8b949e;
    padding: 8px 16px;
    margin-right: 4px;
    border: 1px solid transparent;
    border-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: rgba(88, 166, 255, 0.15);
    color: #58a6ff;
    border: 1px solid rgba(88, 166, 255, 0.3);
}

QTabBar::tab:hover:!selected {
    background-color: rgba(139, 148, 158, 0.1);
    color: #c9d1d9;
}

/* Buttons - Modern & Soft Glow */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid rgba(48, 54, 61, 0.8);
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #161b22;
    border-color: #8b949e;
}

QPushButton:disabled {
    background-color: rgba(33, 38, 45, 0.5);
    color: rgba(139, 148, 158, 0.5);
    border-color: rgba(48, 54, 61, 0.3);
}

/* Primary Action Button (Gradient & Shadow) */
QPushButton#primaryButton {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid rgba(240, 246, 252, 0.1);
}

QPushButton#primaryButton:hover {
    background-color: #2ea043;
    border-color: rgba(240, 246, 252, 0.2);
}

QPushButton#primaryButton:pressed {
    background-color: #1a7f37;
}

/* Success Button */
QPushButton#successButton {
    background-color: rgba(56, 139, 253, 0.15);
    color: #58a6ff;
    border: 1px solid rgba(56, 139, 253, 0.4);
}

QPushButton#successButton:hover {
    background-color: rgba(56, 139, 253, 0.25);
}

/* Inputs - Minimalist */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f0f6fc;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
    background-color: #161b22;
}

/* Combo Box */
QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: url(none);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #8b949e;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    outline: none;
}

/* Sliders - Enhanced Track */
QSlider::groove:horizontal {
    background: #30363d;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #58a6ff;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 2px solid #0d1117;
}

QSlider::handle:horizontal:hover {
    background: #79b8ff;
    transform: scale(1.1);
}

QSlider::sub-page:horizontal {
    background: #1f6feb;
    border-radius: 3px;
}

/* Progress Bar - Animated Gradient Style */
QProgressBar {
    background-color: #161b22;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #238636, stop:1 #2ea043);
    border-radius: 6px;
}

/* Scrollbars - Minimal & Dark */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 40px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #8b949e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: rgba(177, 186, 196, 0.12);
    border-radius: 4px;
}

QMenu {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 12px; /* Top Right Bottom Left */
    border-radius: 4px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

/* Text Editors */
QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    color: #c9d1d9;
    font-family: 'Consolas', 'Monospace';
}

/* Tooltips */
QToolTip {
    background-color: #21262d;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background: #0d1117;
}
QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #1f6feb;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDEyIDEyIj48cGF0aCBmaWxsPSIjZmZmIiBkPSJNOS43LjMgbC01IDUgLTIuNS0yLjUgLTEuNCAxLjQgNCA0IDYuNC02LjR6Ii8+PC9zdmc+);
}

/* Labels */
QLabel#subtitleLabel { color: #8b949e; }
QLabel#titleLabel { color: #f0f6fc; font-weight: bold; font-size: 14pt; }
"""


LIGHT_THEME = """
/* ============================================
   LIGHT THEME - Clean, Modern & Airy v8.0
   ============================================ */

/* Main Window & Global Backgrounds */
QMainWindow, QDialog, QMessageBox {
    background-color: #f6f8fa;
}

QWidget {
    background-color: transparent;
    color: #1f2328;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 10pt;
}

/* Cards & Containers - White with subtle borders */
QFrame#statsFrame, QGroupBox, QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 12px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

/* Group Box */
QGroupBox {
    margin-top: 24px;
    padding: 20px 12px 12px 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 6px 12px;
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    color: #0969da;
    left: 12px;
}

/* Tab Widget - Modern Pills */
QTabWidget::pane {
    padding: 16px;
    border-radius: 12px;
}

QTabBar::tab {
    background-color: transparent;
    color: #57606a;
    padding: 8px 16px;
    margin-right: 4px;
    border: 1px solid transparent;
    border-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: rgba(9, 105, 218, 0.1);
    color: #0969da;
    border: 1px solid rgba(9, 105, 218, 0.2);
}

QTabBar::tab:hover:!selected {
    background-color: rgba(208, 215, 222, 0.3);
    color: #24292f;
}

/* Buttons */
QPushButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid rgba(27, 31, 36, 0.15);
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f3f4f6;
    border-color: rgba(27, 31, 36, 0.15);
    /* box-shadow effect is difficult in pure qss without graphics effects */
}

QPushButton:pressed {
    background-color: #ebecf0;
}

QPushButton:disabled {
    background-color: #f6f8fa;
    color: #8c959f;
    border-color: rgba(27, 31, 36, 0.1);
}

/* Primary Action Button */
QPushButton#primaryButton {
    background-color: #1f883d;
    color: #ffffff;
    border: 1px solid rgba(27, 31, 36, 0.15);
}

QPushButton#primaryButton:hover {
    background-color: #1a7f37;
}

QPushButton#primaryButton:pressed {
    background-color: #16692f;
}

/* Success Button */
QPushButton#successButton {
    background-color: rgba(9, 105, 218, 0.1);
    color: #0969da;
    border: 1px solid rgba(9, 105, 218, 0.2);
}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1f2328;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0969da;
    box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.3);
}

/* Combo Box */
QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: url(none);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #57606a;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    selection-background-color: #0969da;
    selection-color: #ffffff;
    outline: none;
}

/* Sliders */
QSlider::groove:horizontal {
    background: #d0d7de;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    border: 1px solid #d0d7de;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

QSlider::handle:horizontal:hover {
    border-color: #0969da;
    transform: scale(1.1);
}

QSlider::sub-page:horizontal {
    background: #0969da;
    border-radius: 3px;
}

/* Progress Bar */
QProgressBar {
    background-color: #eaeef2;
    border: none;
    border-radius: 6px;
    height: 12px;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ea043, stop:1 #3fb950);
    border-radius: 6px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
}

QScrollBar::handle:vertical {
    background: #d0d7de;
    min-height: 40px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #8c959f;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: rgba(208, 215, 222, 0.5);
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #0969da;
    color: #ffffff;
}

/* Text Editors */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 12px;
    font-family: 'Consolas', 'Monospace';
}

/* Tooltips */
QToolTip {
    background-color: #24292f;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #d0d7de;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #0969da;
    border-color: #0969da;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDEyIDEyIj48cGF0aCBmaWxsPSIjZmZmIiBkPSJNOS43LjMgbC01IDUgLTIuNS0yLjUgLTEuNCAxLjQgNCA0IDYuNC02LjR6Ii8+PC9zdmc+);
}

/* Labels */
QLabel#subtitleLabel { color: #57606a; }
QLabel#titleLabel { color: #1f2328; font-weight: bold; font-size: 14pt; }
"""


THEMES: Dict[str, str] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def get_theme(name: str) -> str:
    """
    Get theme stylesheet by name.
    
    Args:
        name: Theme name ('dark' or 'light')
        
    Returns:
        Theme stylesheet string
    """
    return THEMES.get(name.lower(), DARK_THEME)


def get_available_themes() -> list:
    """Get list of available theme names."""
    return list(THEMES.keys())


def get_color(theme: str, color_key: str) -> str:
    """
    Get a specific color from the theme palette.
    
    Args:
        theme: Theme name ('dark' or 'light')
        color_key: Color key from the palette
        
    Returns:
        Color hex string
    """
    colors = DARK_COLORS if theme == "dark" else LIGHT_COLORS
    return colors.get(color_key, "#000000")
