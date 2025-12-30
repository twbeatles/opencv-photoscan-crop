#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme definitions for Photo Cropper PyQt6 UI.

Provides dark and light themes with modern styling and animations.
Updated: v7.2 - Enhanced UI/UX with improved visual effects
"""

from typing import Dict

# Common style values
FONT_FAMILY = "'Segoe UI', 'Malgun Gothic', sans-serif"
BORDER_RADIUS = "6px"
PADDING_SM = "4px"
PADDING_MD = "8px"
PADDING_LG = "12px"

# Color palette - Dark theme
DARK_COLORS = {
    "bg_primary": "#1a1a2e",
    "bg_secondary": "#16213e",
    "bg_tertiary": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#ff6b85",
    "success": "#00c880",
    "warning": "#ffa500",
    "error": "#e94560",
    "text_primary": "#ffffff",
    "text_secondary": "#e8e8e8",
    "text_muted": "#a0a0a0",
    "border": "#2a2a4a",
    "border_focus": "#0f3460",
}

# Color palette - Light theme
LIGHT_COLORS = {
    "bg_primary": "#f5f5f7",
    "bg_secondary": "#ffffff",
    "bg_tertiary": "#007aff",
    "accent": "#ff3b30",
    "accent_hover": "#e63028",
    "success": "#34c759",
    "warning": "#ff9500",
    "error": "#ff3b30",
    "text_primary": "#1d1d1f",
    "text_secondary": "#3a3a3c",
    "text_muted": "#6e6e73",
    "border": "#d1d1d6",
    "border_focus": "#007aff",
}


DARK_THEME = """
/* ============================================
   DARK THEME - Modern Dark Color Scheme v7.2
   Enhanced with animations and visual effects
   ============================================ */

/* Main Window */
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    background-color: #16213e;
    color: #e8e8e8;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 10pt;
}

/* Scroll Areas */
QScrollArea {
    border: none;
    background-color: #16213e;
}

/* Group Boxes / Frames - Enhanced with gradient title */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 6px 16px;
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 1 #1a5490);
    border-radius: 6px;
    color: #ffffff;
    font-size: 10pt;
    left: 10px;
}

/* Tab Widget - Enhanced */
QTabWidget::pane {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
    padding: 12px;
    top: -1px;
}

QTabBar::tab {
    background-color: #16213e;
    color: #a0a0a0;
    padding: 12px 24px;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #1a5490, stop: 1 #0f3460);
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #1a2744;
    color: #e0e0e0;
}

/* Buttons - Enhanced with hover transition effect */
QPushButton {
    background-color: #0f3460;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1a5490;
    border: 1px solid #2a7acc;
}

QPushButton:pressed {
    background-color: #0a2440;
}

QPushButton:disabled {
    background-color: #2a2a4a;
    color: #606060;
}

/* Primary Action Button - Enhanced with gradient */
QPushButton#primaryButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #e94560, stop: 1 #ff6b85);
    color: #ffffff;
    font-size: 11pt;
    padding: 12px 28px;
    border-radius: 8px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #ff6b85, stop: 1 #ff8a9d);
}

QPushButton#primaryButton:pressed {
    background-color: #c93050;
}

QPushButton#primaryButton:disabled {
    background: #3a3a5a;
    color: #707070;
}

/* Success Button */
QPushButton#successButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #00a86b, stop: 1 #00c880);
}

QPushButton#successButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #00c880, stop: 1 #00e89a);
}

/* Line Edit / Input - Enhanced with focus glow */
QLineEdit {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e8e8e8;
    selection-background-color: #0f3460;
}

QLineEdit:focus {
    border-color: #0f3460;
    background-color: #1e1e36;
}

QLineEdit:disabled {
    background-color: #0a0a1a;
    color: #505050;
}

/* Combo Box - Enhanced */
QComboBox {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e8e8e8;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #3a3a5a;
}

QComboBox:focus {
    border-color: #0f3460;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #a0a0a0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    selection-background-color: #0f3460;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #1a2744;
}

/* Spin Box - Enhanced */
QSpinBox, QDoubleSpinBox {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e8e8e8;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #0f3460;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    background-color: #0f3460;
    border: none;
    border-top-right-radius: 6px;
    width: 24px;
    subcontrol-position: top right;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #0f3460;
    border: none;
    border-bottom-right-radius: 6px;
    width: 24px;
    subcontrol-position: bottom right;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #1a5490;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 6px solid #ffffff;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #ffffff;
    width: 0;
    height: 0;
}

/* Checkbox - Enhanced with custom checkmark */
QCheckBox {
    spacing: 10px;
    color: #e8e8e8;
}

QCheckBox::indicator {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 2px solid #2a2a4a;
    background-color: #1a1a2e;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #0f3460, stop: 1 #1a5490);
    border-color: #0f3460;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTEuNjY3IDMuNUw1LjI1IDkuOTE2N0wyLjMzMzMgNyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
}

QCheckBox::indicator:hover {
    border-color: #0f3460;
    background-color: #1e1e36;
}

QCheckBox::indicator:disabled {
    background-color: #0a0a1a;
    border-color: #1a1a2e;
}

/* Slider - Enhanced with gradient track */
QSlider::groove:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2a2a4a, stop: 1 #3a3a5a);
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #ff6b85, stop: 1 #e94560);
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
    border: 2px solid #1a1a2e;
}

QSlider::handle:horizontal:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #ff8a9d, stop: 1 #ff6b85);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 1 #1a5490);
    border-radius: 4px;
}

/* Progress Bar - Animated gradient */
QProgressBar {
    background-color: #1a1a2e;
    border: none;
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: #ffffff;
    font-size: 9pt;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 0.5 #1a5490, stop: 1 #e94560);
    border-radius: 8px;
}

/* Scroll Bar - Enhanced */
QScrollBar:vertical {
    background-color: #16213e;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #3a3a5a, stop: 1 #2a2a4a);
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4a4a6a, stop: 1 #3a3a5a);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #16213e;
    height: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #3a3a5a, stop: 1 #2a2a4a);
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}

/* Text Edit / Log Area - Enhanced */
QTextEdit, QPlainTextEdit {
    background-color: #0a0a1a;
    border: 2px solid #2a2a4a;
    border-radius: 10px;
    padding: 12px;
    color: #c0c0c0;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 9pt;
    selection-background-color: #0f3460;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #0f3460;
}

/* Labels */
QLabel {
    color: #e8e8e8;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 18pt;
    font-weight: bold;
    color: #ffffff;
}

QLabel#subtitleLabel {
    font-size: 10pt;
    color: #a0a0a0;
}

QLabel#successLabel {
    color: #00c880;
    font-weight: bold;
}

QLabel#errorLabel {
    color: #e94560;
    font-weight: bold;
}

QLabel#warningLabel {
    color: #ffa500;
    font-weight: bold;
}

/* Splitter - Enhanced */
QSplitter::handle {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2a2a4a, stop: 0.5 #3a3a5a, stop: 1 #2a2a4a);
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #3a3a5a, stop: 0.5 #4a4a6a, stop: 1 #3a3a5a);
}

/* Tool Tip - Enhanced with shadow effect */
QToolTip {
    background-color: #1a1a2e;
    color: #e8e8e8;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 9pt;
}

/* Menu - Enhanced */
QMenuBar {
    background-color: #16213e;
    color: #e8e8e8;
    padding: 6px;
    border-bottom: 1px solid #2a2a4a;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #0f3460;
    border-radius: 4px;
}

QMenu {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 28px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 1 #1a5490);
}

QMenu::separator {
    height: 1px;
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 transparent, stop: 0.5 #2a2a4a, stop: 1 transparent);
    margin: 6px 12px;
}

QMenu::icon {
    padding-left: 10px;
}

/* Status Bar - Enhanced */
QStatusBar {
    background-color: #16213e;
    color: #a0a0a0;
    border-top: 1px solid #2a2a4a;
    padding: 4px;
}

QStatusBar::item {
    border: none;
}

/* Tool Bar - Enhanced */
QToolBar {
    background-color: #16213e;
    border: none;
    border-bottom: 1px solid #2a2a4a;
    padding: 6px;
    spacing: 6px;
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px;
    color: #e8e8e8;
}

QToolButton:hover {
    background-color: #0f3460;
}

QToolButton:pressed {
    background-color: #0a2440;
}

/* List Widget - Enhanced */
QListWidget {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 1 #1a5490);
}

QListWidget::item:hover:!selected {
    background-color: #1a2744;
}

/* Frame - Enhanced */
QFrame {
    background-color: transparent;
}

QFrame#statsFrame {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 8px;
}

/* Dialog - Enhanced */
QDialog {
    background-color: #16213e;
}

QDialog QLabel {
    color: #e8e8e8;
}

/* Message Box - Enhanced */
QMessageBox {
    background-color: #16213e;
}

QMessageBox QLabel {
    color: #e8e8e8;
    font-size: 10pt;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


LIGHT_THEME = """
/* ============================================
   LIGHT THEME - Clean Light Color Scheme v7.2
   Enhanced with animations and visual effects
   ============================================ */

/* Main Window */
QMainWindow {
    background-color: #f5f5f7;
}

QWidget {
    background-color: #ffffff;
    color: #1d1d1f;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 10pt;
}

/* Scroll Areas */
QScrollArea {
    border: none;
    background-color: #ffffff;
}

/* Group Boxes / Frames - Enhanced with gradient title */
QGroupBox {
    background-color: #f8f8fa;
    border: 1px solid #d1d1d6;
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 6px 16px;
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 1 #3a9dff);
    border-radius: 6px;
    color: #ffffff;
    font-size: 10pt;
    left: 10px;
}

/* Tab Widget - Enhanced */
QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 10px;
    padding: 12px;
    top: -1px;
}

QTabBar::tab {
    background-color: #f5f5f7;
    color: #6e6e73;
    padding: 12px 24px;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #3a9dff, stop: 1 #007aff);
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #e8e8ed;
    color: #1d1d1f;
}

/* Buttons - Enhanced */
QPushButton {
    background-color: #007aff;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #0066d6;
    border: 1px solid #0051a8;
}

QPushButton:pressed {
    background-color: #0051a8;
}

QPushButton:disabled {
    background-color: #d1d1d6;
    color: #8e8e93;
}

/* Primary Action Button - Enhanced with gradient */
QPushButton#primaryButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #ff3b30, stop: 1 #ff6b60);
    color: #ffffff;
    font-size: 11pt;
    padding: 12px 28px;
    border-radius: 8px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #ff6b60, stop: 1 #ff8a80);
}

QPushButton#primaryButton:disabled {
    background: #d1d1d6;
    color: #8e8e93;
}

/* Success Button - Enhanced with gradient */
QPushButton#successButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #34c759, stop: 1 #50d975);
}

QPushButton#successButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2eb350, stop: 1 #44c96a);
}

/* Line Edit / Input - Enhanced */
QLineEdit {
    background-color: #ffffff;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    padding: 10px 14px;
    color: #1d1d1f;
    selection-background-color: #007aff;
}

QLineEdit:focus {
    border-color: #007aff;
    background-color: #fafbff;
}

QLineEdit:disabled {
    background-color: #f5f5f7;
    color: #8e8e93;
}

/* Combo Box - Enhanced */
QComboBox {
    background-color: #ffffff;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    padding: 10px 14px;
    color: #1d1d1f;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #b1b1b6;
}

QComboBox:focus {
    border-color: #007aff;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #6e6e73;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    selection-background-color: #007aff;
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #f0f0f5;
}

/* Spin Box - Enhanced */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1d1d1f;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #007aff;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    background-color: #007aff;
    border: none;
    border-top-right-radius: 6px;
    width: 24px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #007aff;
    border: none;
    border-bottom-right-radius: 6px;
    width: 24px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #0066d6;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 6px solid #ffffff;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #ffffff;
    width: 0;
    height: 0;
}

/* Checkbox - Enhanced */
QCheckBox {
    spacing: 10px;
    color: #1d1d1f;
}

QCheckBox::indicator {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 2px solid #d1d1d6;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #007aff, stop: 1 #3a9dff);
    border-color: #007aff;
}

QCheckBox::indicator:hover {
    border-color: #007aff;
    background-color: #fafbff;
}

/* Slider - Enhanced */
QSlider::groove:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #d1d1d6, stop: 1 #e0e0e5);
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #3a9dff, stop: 1 #007aff);
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
    border: 2px solid #ffffff;
}

QSlider::handle:horizontal:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #5ab0ff, stop: 1 #3a9dff);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 1 #3a9dff);
    border-radius: 4px;
}

/* Progress Bar - Enhanced */
QProgressBar {
    background-color: #e8e8ed;
    border: none;
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: #1d1d1f;
    font-size: 9pt;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 0.5 #3a9dff, stop: 1 #34c759);
    border-radius: 8px;
}

/* Scroll Bar - Enhanced */
QScrollBar:vertical {
    background-color: #f5f5f7;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #c7c7cc, stop: 1 #b0b0b5);
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #aeaeb2, stop: 1 #9a9a9f);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f5f5f7;
    height: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #c7c7cc, stop: 1 #b0b0b5);
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}

/* Text Edit / Log Area - Enhanced */
QTextEdit, QPlainTextEdit {
    background-color: #f8f8fa;
    border: 2px solid #d1d1d6;
    border-radius: 10px;
    padding: 12px;
    color: #1d1d1f;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 9pt;
    selection-background-color: #007aff;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #007aff;
}

/* Labels */
QLabel {
    color: #1d1d1f;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 18pt;
    font-weight: bold;
    color: #1d1d1f;
}

QLabel#subtitleLabel {
    font-size: 10pt;
    color: #6e6e73;
}

QLabel#successLabel {
    color: #34c759;
    font-weight: bold;
}

QLabel#errorLabel {
    color: #ff3b30;
    font-weight: bold;
}

QLabel#warningLabel {
    color: #ff9500;
    font-weight: bold;
}

/* Splitter - Enhanced */
QSplitter::handle {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #d1d1d6, stop: 0.5 #c0c0c5, stop: 1 #d1d1d6);
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #b0b0b5, stop: 0.5 #a0a0a5, stop: 1 #b0b0b5);
}

/* Tool Tip - Enhanced */
QToolTip {
    background-color: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 9pt;
}

/* Menu - Enhanced */
QMenuBar {
    background-color: #f5f5f7;
    color: #1d1d1f;
    padding: 6px;
    border-bottom: 1px solid #d1d1d6;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #007aff;
    color: #ffffff;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 28px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 1 #3a9dff);
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 transparent, stop: 0.5 #d1d1d6, stop: 1 transparent);
    margin: 6px 12px;
}

/* Status Bar - Enhanced */
QStatusBar {
    background-color: #f5f5f7;
    color: #6e6e73;
    border-top: 1px solid #d1d1d6;
    padding: 4px;
}

QStatusBar::item {
    border: none;
}

/* Tool Bar - Enhanced */
QToolBar {
    background-color: #f5f5f7;
    border: none;
    border-bottom: 1px solid #d1d1d6;
    padding: 6px;
    spacing: 6px;
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px;
    color: #1d1d1f;
}

QToolButton:hover {
    background-color: #e8e8ed;
}

QToolButton:pressed {
    background-color: #d1d1d6;
}

/* List Widget - Enhanced */
QListWidget {
    background-color: #ffffff;
    border: 2px solid #d1d1d6;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 1 #3a9dff);
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: #f0f0f5;
}

/* Frame - Enhanced */
QFrame {
    background-color: transparent;
}

QFrame#statsFrame {
    background-color: #f8f8fa;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px;
}

/* Dialog - Enhanced */
QDialog {
    background-color: #ffffff;
}

QDialog QLabel {
    color: #1d1d1f;
}

/* Message Box - Enhanced */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1d1d1f;
    font-size: 10pt;
}

QMessageBox QPushButton {
    min-width: 80px;
}
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
