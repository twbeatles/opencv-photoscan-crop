# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Photo Cropper v7.1

Build command:
    pyinstaller photo_cropper.spec

The executable will be created in the dist/PhotoCropper folder.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules
hiddenimports = [
    'cv2',
    'numpy',
    'PIL',
    'PyQt6.QtWidgets',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'photo_cropper',
    'photo_cropper.core',
    'photo_cropper.core.image_processor',
    'photo_cropper.core.batch_processor',
    'photo_cropper.core.settings',
    'photo_cropper.ui',
    'photo_cropper.ui.main_window',
    'photo_cropper.ui.widgets',
    'photo_cropper.ui.widgets.preview_widget',
    'photo_cropper.ui.widgets.settings_panel',
    'photo_cropper.ui.widgets.progress_dialog',
    'photo_cropper.ui.widgets.histogram_widget',
    'photo_cropper.ui.widgets.toast_widget',
    'photo_cropper.ui.styles',
    'photo_cropper.ui.styles.themes',
    'photo_cropper.utils',
    'photo_cropper.utils.file_helpers',
]

# Main analysis
a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'tkinter',
        'unittest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary binaries to reduce size
a.binaries = [x for x in a.binaries if not x[0].startswith('api-ms-')]
a.binaries = [x for x in a.binaries if not x[0].startswith('ucrtbase')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotoCropper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows-specific options
    icon=None,  # Add icon path here if available: icon='icon.ico',
    version=None,  # Add version file if available
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoCropper',
)

# For single-file executable (optional, larger startup time):
# Uncomment the following and comment out COLLECT above
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='PhotoCropper',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
# )
