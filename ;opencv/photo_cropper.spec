# -*- mode: python ; coding: utf-8 -*-
"""
Photo Cropper v9.0 - PyInstaller Spec File

Optimized for:
- Lightweight build (excluding unused packages)
- Single file executable
- UPX compression support
"""

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Include OpenCV data files required at runtime (e.g., haarcascades XML).
CV2_DATA_FILES = collect_data_files('cv2', includes=['data/*.xml'])

# ============================================
# Exclusions for lightweight build
# ============================================

# Heavy packages to exclude
EXCLUDES = [
    # Data science / ML (not needed)
    'matplotlib', 'scipy', 'pandas', 'sklearn', 'tensorflow', 'torch',
    'keras', 'statsmodels', 'seaborn', 'plotly', 'bokeh',
    
    # Testing frameworks
    'pytest', 'unittest', 'nose', 'mock', 'hypothesis',
    
    # Development tools
    'IPython', 'jupyter', 'notebook', 'ipykernel', 'debugpy',
    'sphinx', 'docutils', 'jedi', 'black', 'flake8', 'pylint',
    
    # Unused GUI frameworks
    'tkinter', '_tkinter', 'tcl', 'tk', 'wx', 'PySide6', 'PyGObject',
    
    # Unused database / network
    'sqlalchemy', 'aiohttp', 'asyncio', 'tornado', 'flask', 'django',
    'requests', 'urllib3', 'httpx', 'websockets',
    
    # Unused formats
    'xml.dom', 'xml.sax', 'email', 'html', 'http',
    'ftplib', 'imaplib', 'smtplib', 'telnetlib',
    
    # OpenCV unused submodules (reduces size significantly)
    'cv2.gapi',
    
    # PyQt6 unused modules
    'PyQt6.QtBluetooth', 'PyQt6.QtDBus', 'PyQt6.QtDesigner',
    'PyQt6.QtHelp', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtNetwork', 'PyQt6.QtNfc', 'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets', 'PyQt6.QtPositioning', 'PyQt6.QtPrintSupport',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuick3D', 'PyQt6.QtQuickWidgets',
    'PyQt6.QtRemoteObjects', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
    'PyQt6.QtSpatialAudio', 'PyQt6.QtSql', 'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
    'PyQt6.QtTest', 'PyQt6.QtWebChannel', 'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineQuick', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebSockets',
    'PyQt6.QtXml',
    
    # Misc
    'lib2to3', 'distutils', 'setuptools', 'pkg_resources', 'pip',
]

# Binary files to exclude
EXCLUDE_BINARIES = [
    # OpenCV DNN module (large, unused)
    'opencv_videoio_ffmpeg*.dll',
    'libopenblas*.dll',
    
    # Qt unused plugins
    'Qt6Multimedia.dll',
    'Qt6Network.dll',
    'Qt6Qml.dll',
    'Qt6Quick.dll',
    'Qt6Sql.dll',
    'Qt6WebEngine*.dll',
]

# ============================================
# Analysis
# ============================================

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include i18n translations if exists
        ('photo_cropper/i18n', 'photo_cropper/i18n'),
        *CV2_DATA_FILES,
    ],
    hiddenimports=[
        # Ensure these are included
        'cv2',
        'numpy',
        'PIL',
        'photo_cropper.core.settings_model',
        'photo_cropper.core.batch_profile_manager',
        'photo_cropper.core.folder_watcher',
        'photo_cropper.core.advanced',
        'photo_cropper.core.face',
        'photo_cropper.core.batch',
        'photo_cropper.core.image',
        'photo_cropper.core.settings_model.app_settings',
        'photo_cropper.ui.main',
        'photo_cropper.ui.widgets.settings',
        'photo_cropper.i18n.catalog',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================
# Remove excluded binaries
# ============================================

def should_exclude_binary(name):
    """Check if binary should be excluded."""
    import fnmatch
    name_lower = name.lower()
    for pattern in EXCLUDE_BINARIES:
        if fnmatch.fnmatch(name_lower, pattern.lower()):
            return True
    return False

# Filter binaries
a.binaries = [b for b in a.binaries if not should_exclude_binary(b[0])]

# ============================================
# PYZ (Python archive)
# ============================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# ============================================
# EXE Configuration
# ============================================

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhotoCropper_v9',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Set True on Linux for smaller size
    upx=True,     # Enable UPX compression
    upx_exclude=[
        # Don't compress these (causes issues)
        'vcruntime140.dll',
        'python*.dll',
        'Qt*.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # Windows specific - icon is optional
    icon=None,  # Set to 'photo_cropper/resources/icon.ico' if you have an icon file
    version=None,
)

# ============================================
# Build Notes
# ============================================

"""
Build Commands:
    
    # Standard build
    pyinstaller photo_cropper.spec --clean
    
    # With UPX (recommended for smaller size)
    # Install UPX: https://github.com/upx/upx/releases
    pyinstaller photo_cropper.spec --clean --upx-dir=/path/to/upx
    
    # Debug build (with console)
    # Change console=True above, then:
    pyinstaller photo_cropper.spec --clean

Expected Output Size:
    - Without UPX: ~80-100 MB
    - With UPX: ~50-70 MB

Tips for further size reduction:
    1. Install UPX compression
    2. Use Python 3.11+ (smaller stdlib)
    3. Use opencv-python-headless instead of opencv-python
    4. Consider using Nuitka instead of PyInstaller

2026-03-01 note:
    - No additional binary dependencies were introduced by the CLI/watch/profile
      alignment changes.
    - Hidden imports above explicitly pin core modules touched by the update to
      keep frozen-build module discovery stable.

2026-03-02 note:
    - Core/UI/i18n modules were split into package directories:
      core/settings_model, core/advanced, core/face, core/image, core/batch,
      ui/main, ui/widgets/settings, i18n/catalog.
    - Hidden imports were expanded to include package-level entry points used
      after the split refactor.

2026-03-03 note:
    - Main-window batch edit flow and manual boundary fallback UI were added.
    - No additional third-party dependencies were introduced.
    - Existing hidden imports remain sufficient for frozen builds.
"""
