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
    # Optional OpenCV / BLAS runtime binaries not required for current build
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
        'PIL.ImageOps',
        'photo_cropper.core.settings_model',
        'photo_cropper.core.batch_profile_manager',
        'photo_cropper.core.folder_watcher',
        'photo_cropper.core.processed_index',
        'photo_cropper.core.scheduler',
        'photo_cropper.core.advanced',
        'photo_cropper.core.face',
        'photo_cropper.core.batch',
        'photo_cropper.core.batch.types',
        'photo_cropper.core.image',
        'photo_cropper.core.image.types',
        'photo_cropper.core.settings_model.app_settings',
        'photo_cropper.core.settings_model.manager',
        'photo_cropper.core.settings_model.migration',
        'photo_cropper.core.settings_model.validation',
        'photo_cropper.core.watch_mode',
        'photo_cropper.core.manual_extract',
        'photo_cropper.core.batch.session_service',
        'photo_cropper.core.image.save_io',
        'photo_cropper.ui.main',
        'photo_cropper.ui.main.models',
        'photo_cropper.ui.main.preview_worker',
        'photo_cropper.ui.main.services',
        'photo_cropper.ui.main.services.batch_flow',
        'photo_cropper.ui.main.services.dialog_flow',
        'photo_cropper.ui.main.services.message_factory',
        'photo_cropper.ui.main.services.watch_flow',
        'photo_cropper.ui.main.actions',
        'photo_cropper.ui.main.actions.batch',
        'photo_cropper.ui.main.actions.dialog',
        'photo_cropper.ui.main.actions.feature',
        'photo_cropper.ui.main.actions.input',
        'photo_cropper.ui.main.actions.lifecycle',
        'photo_cropper.ui.main.actions.navigation',
        'photo_cropper.ui.main.actions.preview',
        'photo_cropper.ui.main.actions.settings',
        'photo_cropper.ui.main.actions.tools',
        'photo_cropper.ui.main.actions.watch',
        'photo_cropper.ui.main.builders',
        'photo_cropper.ui.main.builders.central',
        'photo_cropper.ui.main.builders.fab',
        'photo_cropper.ui.main.builders.menu',
        'photo_cropper.ui.main.builders.statusbar',
        'photo_cropper.ui.main.builders.toolbar',
        'photo_cropper.ui.main.batch_actions',
        'photo_cropper.ui.main.dialog_actions',
        'photo_cropper.ui.main.feature_actions',
        'photo_cropper.ui.main.io_actions',
        'photo_cropper.ui.main.navigation_actions',
        'photo_cropper.ui.main.preview_actions',
        'photo_cropper.ui.main.settings_actions',
        'photo_cropper.ui.main.watch_actions',
        'photo_cropper.ui.widgets.settings',
        'photo_cropper.i18n.catalog',
        'photo_cropper.i18n.catalog.locales',
        'photo_cropper.i18n.catalog.locales.en',
        'photo_cropper.i18n.catalog.locales.ko',
        'photo_cropper.i18n.catalog.locales.ja',
        'photo_cropper.i18n.catalog.locales.zh',
        'photo_cropper.i18n.catalog.locales.es',
        'photo_cropper.utils.path_validation',
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
    icon='icon.ico',  # Set to 'photo_cropper/resources/icon.ico' if you have an icon file
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

2026-04-14 note:
    - Runtime i18n now loads Python locale catalog modules dynamically
      (`photo_cropper.i18n.catalog.locales.*`), so locale submodules are pinned
      explicitly in hidden imports for frozen builds.
    - `ui.main.services.*`, `core.settings_model.{manager,migration,validation}`,
      `core.{image,batch}.types`, and `utils.path_validation` were added to keep
      split-module discovery stable after the refactor.

2026-03-04 note:
    - Hidden imports were explicitly extended for recent split modules used by
      manual extract/watch mode/session I/O paths to keep one-file discovery
      stable across PyInstaller environments.
    - Type-check-only override signature updates (QEvent Optional annotations)
      do not change runtime packaging requirements.

2026-03-05 note:
    - Added hidden imports for `core.processed_index` and `core.scheduler` to
      keep frozen builds stable after skip-processed index persistence and
      runtime scheduler wiring.

2026-03-08 note:
    - EXIF-orientation normalization path (`ImageOps.exif_transpose`) was added
      in image loading.
    - Added explicit `PIL.ImageOps` hidden import to keep frozen runtime stable.

2026-03-09 note:
    - `ui/main/window.py` was reduced to a composition root and the UI layer was
      split into `ui/main/actions`, `ui/main/builders`, and `ui/main/models.py`.
    - Hidden imports now explicitly include both canonical package paths and the
      compatibility shim modules kept under `ui/main/*.py`.

2026-03-16 note:
    - Added explicit hidden import for `ui.main.preview_worker` to keep frozen
      discovery stable after the main-window split.
    - Repository-root type-check/editor config additions (`pyrightconfig.json`,
      `.editorconfig`) do not introduce any new frozen-build dependencies.
    - Recent false-positive filtering and multi-photo quad-dimension fixes are
      code-only changes and do not require extra packaging hooks.

2026-03-25 note:
    - Stabilization changes for manual-preview/save crop parity, recursive
      watch output guards, processed-index v2 status handling, and watch-mode
      overwrite/fileChanged handling are code-path-only updates.
    - No new third-party packages or PyInstaller hidden imports were required
      after verifying the current module graph against this patch set.
"""
