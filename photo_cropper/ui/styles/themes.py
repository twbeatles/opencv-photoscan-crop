#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme definitions for Photo Cropper PyQt6 UI.

Provides dark and light themes with modern styling.
"""

from typing import Dict

# Common style values
FONT_FAMILY = "'Segoe UI', 'Malgun Gothic', sans-serif"
BORDER_RADIUS = "6px"
PADDING_SM = "4px"
PADDING_MD = "8px"
PADDING_LG = "12px"


DARK_THEME = """
/* ============================================
   DARK THEME - Modern Dark Color Scheme
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

/* Group Boxes / Frames */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: #0f3460;
    border-radius: 4px;
    color: #e8e8e8;
}

/* Tab Widget */
QTabWidget::pane {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 8px;
}

QTabBar::tab {
    background-color: #16213e;
    color: #a0a0a0;
    padding: 10px 20px;
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #0f3460;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #1a2744;
    color: #e0e0e0;
}

/* Buttons */
QPushButton {
    background-color: #0f3460;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1a5490;
}

QPushButton:pressed {
    background-color: #0a2440;
}

QPushButton:disabled {
    background-color: #2a2a4a;
    color: #606060;
}

/* Primary Action Button */
QPushButton#primaryButton {
    background-color: #e94560;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #ff6b85;
}

QPushButton#primaryButton:pressed {
    background-color: #c93050;
}

/* Success Button */
QPushButton#successButton {
    background-color: #00a86b;
}

QPushButton#successButton:hover {
    background-color: #00c880;
}

/* Line Edit / Input */
QLineEdit {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e8e8e8;
    selection-background-color: #0f3460;
}

QLineEdit:focus {
    border-color: #0f3460;
}

QLineEdit:disabled {
    background-color: #0a0a1a;
    color: #505050;
}

/* Combo Box */
QComboBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e8e8e8;
    min-width: 100px;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #a0a0a0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    selection-background-color: #0f3460;
    outline: none;
}

/* Spin Box */
QSpinBox, QDoubleSpinBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e8e8e8;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #0f3460;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #1a5490;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #e8e8e8;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #2a2a4a;
    background-color: #1a1a2e;
}

QCheckBox::indicator:checked {
    background-color: #0f3460;
    border-color: #0f3460;
}

QCheckBox::indicator:hover {
    border-color: #0f3460;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #2a2a4a;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #e94560;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #ff6b85;
}

QSlider::sub-page:horizontal {
    background-color: #0f3460;
    border-radius: 3px;
}

/* Progress Bar */
QProgressBar {
    background-color: #1a1a2e;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: #ffffff;
    font-size: 9pt;
}

QProgressBar::chunk {
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f3460, stop: 1 #e94560
    );
    border-radius: 6px;
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #2a2a4a;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3a3a5a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #16213e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2a4a;
    border-radius: 6px;
    min-width: 30px;
}

/* Text Edit / Log Area */
QTextEdit, QPlainTextEdit {
    background-color: #0a0a1a;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px;
    color: #c0c0c0;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 9pt;
}

/* Labels */
QLabel {
    color: #e8e8e8;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 16pt;
    font-weight: bold;
    color: #ffffff;
}

QLabel#subtitleLabel {
    font-size: 10pt;
    color: #a0a0a0;
}

QLabel#successLabel {
    color: #00c880;
}

QLabel#errorLabel {
    color: #e94560;
}

QLabel#warningLabel {
    color: #ffc107;
}

/* Splitter */
QSplitter::handle {
    background-color: #2a2a4a;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* Tool Tip */
QToolTip {
    background-color: #1a1a2e;
    color: #e8e8e8;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 6px;
}

/* Menu */
QMenuBar {
    background-color: #16213e;
    color: #e8e8e8;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #0f3460;
    border-radius: 4px;
}

QMenu {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0f3460;
}

QMenu::separator {
    height: 1px;
    background-color: #2a2a4a;
    margin: 4px 8px;
}

/* Status Bar */
QStatusBar {
    background-color: #16213e;
    color: #a0a0a0;
    border-top: 1px solid #2a2a4a;
}

QStatusBar::item {
    border: none;
}

/* Tool Bar */
QToolBar {
    background-color: #16213e;
    border: none;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 8px;
    color: #e8e8e8;
}

QToolButton:hover {
    background-color: #0f3460;
}

QToolButton:pressed {
    background-color: #0a2440;
}

/* List Widget */
QListWidget {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #0f3460;
}

QListWidget::item:hover:!selected {
    background-color: #1a2744;
}
"""


LIGHT_THEME = """
/* ============================================
   LIGHT THEME - Clean Light Color Scheme
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

/* Group Boxes / Frames */
QGroupBox {
    background-color: #f8f8fa;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: #007aff;
    border-radius: 4px;
    color: #ffffff;
}

/* Tab Widget */
QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px;
}

QTabBar::tab {
    background-color: #f5f5f7;
    color: #6e6e73;
    padding: 10px 20px;
    border: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #007aff;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #e8e8ed;
    color: #1d1d1f;
}

/* Buttons */
QPushButton {
    background-color: #007aff;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #0066d6;
}

QPushButton:pressed {
    background-color: #0051a8;
}

QPushButton:disabled {
    background-color: #d1d1d6;
    color: #8e8e93;
}

/* Primary Action Button */
QPushButton#primaryButton {
    background-color: #ff3b30;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #e63028;
}

/* Success Button */
QPushButton#successButton {
    background-color: #34c759;
}

QPushButton#successButton:hover {
    background-color: #2eb350;
}

/* Line Edit / Input */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1d1d1f;
    selection-background-color: #007aff;
}

QLineEdit:focus {
    border-color: #007aff;
}

QLineEdit:disabled {
    background-color: #f5f5f7;
    color: #8e8e93;
}

/* Combo Box */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 8px 12px;
    color: #1d1d1f;
    min-width: 100px;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6e6e73;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    selection-background-color: #007aff;
    selection-color: #ffffff;
    outline: none;
}

/* Spin Box */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1d1d1f;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #1d1d1f;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #d1d1d6;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #007aff;
    border-color: #007aff;
}

QCheckBox::indicator:hover {
    border-color: #007aff;
}

/* Slider */
QSlider::groove:horizontal {
    background-color: #d1d1d6;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #007aff;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #0066d6;
}

QSlider::sub-page:horizontal {
    background-color: #007aff;
    border-radius: 3px;
}

/* Progress Bar */
QProgressBar {
    background-color: #e8e8ed;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: #1d1d1f;
    font-size: 9pt;
}

QProgressBar::chunk {
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #007aff, stop: 1 #34c759
    );
    border-radius: 6px;
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: #f5f5f7;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #c7c7cc;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #aeaeb2;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f5f5f7;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #c7c7cc;
    border-radius: 6px;
    min-width: 30px;
}

/* Text Edit / Log Area */
QTextEdit, QPlainTextEdit {
    background-color: #f8f8fa;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    padding: 8px;
    color: #1d1d1f;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 9pt;
}

/* Labels */
QLabel {
    color: #1d1d1f;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 16pt;
    font-weight: bold;
    color: #1d1d1f;
}

QLabel#subtitleLabel {
    font-size: 10pt;
    color: #6e6e73;
}

QLabel#successLabel {
    color: #34c759;
}

QLabel#errorLabel {
    color: #ff3b30;
}

QLabel#warningLabel {
    color: #ff9500;
}

/* Menu */
QMenuBar {
    background-color: #f5f5f7;
    color: #1d1d1f;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #007aff;
    color: #ffffff;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #007aff;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #d1d1d6;
    margin: 4px 8px;
}

/* Status Bar */
QStatusBar {
    background-color: #f5f5f7;
    color: #6e6e73;
    border-top: 1px solid #d1d1d6;
}

/* Tool Bar */
QToolBar {
    background-color: #f5f5f7;
    border: none;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 8px;
    color: #1d1d1f;
}

QToolButton:hover {
    background-color: #e8e8ed;
}

QToolButton:pressed {
    background-color: #d1d1d6;
}

/* List Widget */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #007aff;
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: #f0f0f5;
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
