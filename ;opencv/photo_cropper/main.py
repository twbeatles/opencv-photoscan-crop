#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Cropper - Main Application Entry Point

Launches the PyQt6 photo auto-cropping application.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

try:
    from .ui.main_window import MainWindow
except ImportError:
    # If run directly not as a module
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from photo_cropper.ui.main_window import MainWindow


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def setup_high_dpi():
    """Configure high DPI support."""
    # Enable high DPI scaling (Qt6 handles this automatically in most cases)
    pass


def main():
    """Main application entry point."""
    # Setup
    setup_logging()
    setup_high_dpi()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Cropper")
    app.setApplicationVersion("9.0")
    app.setOrganizationName("PhotoCropper")
    
    # Set default font for Korean text
    from PyQt6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    font.setFamilies(["Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo"])
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
