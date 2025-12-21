#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Cropper - Main Application Entry Point

Launches the PyQt6 photo auto-cropping application.
"""

import sys
import os
import logging
import platform
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .ui.main_window import MainWindow


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def setup_high_dpi():
    """
    Configure high DPI support for all platforms.
    
    This must be called BEFORE creating QApplication.
    """
    # Enable high DPI scaling
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Use high DPI pixmaps
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    
    # Platform-specific settings
    if platform.system() == "Windows":
        # Windows-specific DPI awareness
        try:
            from ctypes import windll
            # Set DPI awareness (Per Monitor V2)
            windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def main():
    """Main application entry point."""
    # Setup HiDPI BEFORE creating QApplication
    setup_high_dpi()
    setup_logging()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Cropper")
    app.setApplicationVersion("7.1")
    app.setOrganizationName("PhotoCropper")
    
    # Set style hints for HiDPI
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Set default font for Korean text with fallbacks
    font = QFont()
    font.setFamilies(["Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", "sans-serif"])
    font.setPointSize(10)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

