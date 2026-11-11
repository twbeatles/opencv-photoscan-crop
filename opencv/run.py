#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Cropper - Run Script

Simple entry script to launch the application.
Usage: python run.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from photo_cropper.main import main

if __name__ == "__main__":
    main()
