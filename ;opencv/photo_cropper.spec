# -*- mode: python ; coding: utf-8 -*-
"""
Photo Cropper v9.0 - PyInstaller Spec File

Optimized for:
- Lightweight build (excluding unused packages)
- Windows policy-friendly onedir executable
- No UPX compression for Qt/PyQt stability under App Control
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Include OpenCV data files required at runtime (e.g., haarcascades XML).
CV2_DATA_FILES = collect_data_files('cv2', includes=['data/*.xml'])

SPLIT_PACKAGES = [
    'photo_cropper.cli_support',
    'photo_cropper.core.settings_model',
    'photo_cropper.core.advanced',
    'photo_cropper.core.face',
    'photo_cropper.core.batch',
    'photo_cropper.core.image',
    'photo_cropper.core.file_watch',
    'photo_cropper.core.watch_mode',
    'photo_cropper.core.manual_extract',
    'photo_cropper.core.library',
    'photo_cropper.core.jobs',
    'photo_cropper.core.recipes',
    'photo_cropper.ui.main.actions',
    'photo_cropper.ui.main.builders',
    'photo_cropper.ui.main.composition',
    'photo_cropper.ui.main.services',
    'photo_cropper.ui.widgets.settings',
    'photo_cropper.ui.widgets.management',
    'photo_cropper.i18n.catalog.locales',
]

COLLECTED_HIDDENIMPORTS = []
for package_name in SPLIT_PACKAGES:
    COLLECTED_HIDDENIMPORTS.extend(collect_submodules(package_name))

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
    hiddenimports=sorted(set([
        # Ensure these are included
        'cv2',
        'numpy',
        'PIL',
        'PIL.ImageOps',
        'photo_cropper.cli',
        'photo_cropper.cli_support',
        'photo_cropper.cli_support.runtime',
        'photo_cropper.core.settings_model',
        'photo_cropper.core.batch_profile_manager',
        'photo_cropper.core.app_paths',
        'photo_cropper.core.folder_watcher',
        'photo_cropper.core.file_watch',
        'photo_cropper.core.file_watch.auto_processor',
        'photo_cropper.core.file_watch.folder_watcher',
        'photo_cropper.core.file_watch.types',
        'photo_cropper.core.jobs',
        'photo_cropper.core.jobs.orchestrator',
        'photo_cropper.core.library',
        'photo_cropper.core.library.duplicate_service',
        'photo_cropper.core.library.ingest_service',
        'photo_cropper.core.library.providers',
        'photo_cropper.core.library.query_service',
        'photo_cropper.core.library.repository',
        'photo_cropper.core.library._repository_protocol',
        'photo_cropper.core.library.review_service',
        'photo_cropper.core.library.sqlite_store',
        'photo_cropper.core.library.thumbnail_service',
        'photo_cropper.core.processed_index',
        'photo_cropper.core.recipes',
        'photo_cropper.core.recipes.manager',
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
        'photo_cropper.ui.main.composition',
        'photo_cropper.ui.main.composition.actions',
        'photo_cropper.ui.main.composition.layout',
        'photo_cropper.ui.main.management_runtime',
        'photo_cropper.ui.main.translation',
        'photo_cropper.ui.main.batch_actions',
        'photo_cropper.ui.main.dialog_actions',
        'photo_cropper.ui.main.feature_actions',
        'photo_cropper.ui.main.io_actions',
        'photo_cropper.ui.main.navigation_actions',
        'photo_cropper.ui.main.preview_actions',
        'photo_cropper.ui.main.settings_actions',
        'photo_cropper.ui.main.watch_actions',
        'photo_cropper.ui.widgets.management_pages',
        'photo_cropper.ui.widgets.settings',
        'photo_cropper.ui.widgets.settings.i18n_bindings',
        'photo_cropper.ui.widgets.settings.panel_i18n',
        'photo_cropper.ui.widgets.settings.panel_layout',
        'photo_cropper.ui.widgets.settings.panel_settings',
        'photo_cropper.ui.widgets.settings.panel_validation',
        'photo_cropper.ui.widgets.management.library',
        'photo_cropper.ui.widgets.management.library.layout',
        'photo_cropper.i18n.catalog',
        'photo_cropper.i18n.catalog.locales',
        'photo_cropper.i18n.catalog.locales.en',
        'photo_cropper.i18n.catalog.locales.ko',
        'photo_cropper.i18n.catalog.locales.ja',
        'photo_cropper.i18n.catalog.locales.zh',
        'photo_cropper.i18n.catalog.locales.es',
        'photo_cropper.utils.image_io',
        'photo_cropper.utils.path_validation',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        *COLLECTED_HIDDENIMPORTS,
    ])),
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
# EXE / COLLECT Configuration
# ============================================

# NOTE:
# Windows AppLocker / WDAC environments commonly block DLLs unpacked by
# PyInstaller one-file executables from the per-run temp extraction directory.
# Building as onedir keeps Qt/PyQt binaries beside the EXE in a stable location
# and avoids the "DLL load failed ... application control policy blocked this
# file" startup error seen in the field.

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotoCropper_v9',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Set True on Linux for smaller size
    upx=False,    # Disabled for App Control / PyQt stability
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
        'Qt*.dll',
    ],
    name='PhotoCropper_v9',
)

# ============================================
# Build Notes
# ============================================

"""
Build Commands:
    
    # Standard build
    pyinstaller photo_cropper.spec --clean
    
    # Debug build (with console)
    # Change console=True above, then:
    pyinstaller photo_cropper.spec --clean

Expected Output Size:
    - onedir without UPX: larger than one-file, but more reliable under
      Windows application control policies.

Tips for further size reduction:
    1. Use Python 3.11+ (smaller stdlib)
    2. Use opencv-python-headless instead of opencv-python
    3. Consider using Nuitka instead of PyInstaller

If a single-file EXE is absolutely required:
    - Code-sign the executable and extracted binaries, or
    - Allowlist the PyInstaller temp extraction path in App Control policy, or
    - Use a different packager/runtime strategy that does not unpack to a
      blocked user-writable temp location.

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

2026-04-19 note:
    - The management-app split added `core/library`, `core/jobs`,
      `core/recipes`, `ui/widgets/management`, and deeper internal module
      extraction under `core/batch` / `core/image`.
    - Hidden imports now use `collect_submodules(...)` for split package
      families so future internal module extraction does not require editing
      this file every time.

2026-04-30 note:
    - Added explicit hidden imports for `utils.image_io` and
      `ui.widgets.settings.i18n_bindings` after Unicode-safe image loading and
      runtime settings-tab i18n binding were introduced.
    - These changes add no new third-party runtime dependency; Pillow/OpenCV
      were already part of the packaging contract.

2026-05-11 note:
    - Added `cli_support` to the collected split-package set after `cli.py`
      became a compatibility wrapper around the runtime implementation.
    - Existing collect-submodules coverage now also tracks the file-watch,
      advanced-operation, settings-panel helper, management-library, and
      main-window composition splits from the SOLID refactor.

2026-04-27 note:
    - Management/library stabilization added a private repository Protocol
      module plus code-only maintenance flows for search-index rebuild,
      background library import, and duplicate rebuild jobs.
    - `collect_submodules("photo_cropper.core.library")` already covers the
      new private module; it is also listed explicitly above as a packaging
      guard for frozen builds. No new third-party packages are required.

2026-06-04 note:
    - Stability hardening added batch fatal status fields, failed-folder-name
      validation, explicit file-list preflight, watch stop-race preservation,
      background job finalization, and Scheduler once retry behavior.
    - These are code-path changes inside already collected packages:
      `cli_support`, `core.batch`, `core.jobs`, `core.watch_mode`,
      `ui.main.actions`, `ui.main.services`, and `utils.path_validation`.
      No new data files, third-party dependencies, or hidden imports are
      required for frozen builds.
"""
