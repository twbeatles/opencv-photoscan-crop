# -*- mode: python ; coding: utf-8 -*-
"""
Photo Cropper v9.0 - PyInstaller Onefile Spec

Purpose:
- Keep the stable onedir build in `photo_cropper.spec`
- Provide an experimental single-file build
- Avoid the default user-temp extraction path that triggered Windows
  App Control blocking of Qt DLLs

Build (from opencv/ app directory):
    pyinstaller photo_cropper_onefile.spec --clean

Build (from repository root):
    pyinstaller opencv/photo_cropper_onefile.spec --clean

Output:
    opencv/dist/PhotoCropper_v9_single.exe

IMPORTANT:
- This spec still depends on runtime extraction, so it is less reliable than
  the onedir build under stricter Windows application-control environments.
- The extraction base path is derived from the builder's `LOCALAPPDATA`
  (fallback: temp directory) to avoid username-specific hardcoding.
"""

import os
import tempfile
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

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

RUNTIME_TMPDIR = str(
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "PhotoCropper"
    / "runtime"
)

EXCLUDES = [
    'matplotlib', 'scipy', 'pandas', 'sklearn', 'tensorflow', 'torch',
    'keras', 'statsmodels', 'seaborn', 'plotly', 'bokeh',
    'pytest', 'unittest', 'nose', 'mock', 'hypothesis',
    'IPython', 'jupyter', 'notebook', 'ipykernel', 'debugpy',
    'sphinx', 'docutils', 'jedi', 'black', 'flake8', 'pylint',
    'tkinter', '_tkinter', 'tcl', 'tk', 'wx', 'PySide6', 'PyGObject',
    'sqlalchemy', 'aiohttp', 'asyncio', 'tornado', 'flask', 'django',
    'requests', 'urllib3', 'httpx', 'websockets',
    'cv2.gapi',
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
    'lib2to3', 'distutils', 'setuptools', 'pkg_resources', 'pip',
]

EXCLUDE_BINARIES = [
    'opencv_videoio_ffmpeg*.dll',
    'libopenblas*.dll',
    'Qt6Multimedia.dll',
    'Qt6Network.dll',
    'Qt6Qml.dll',
    'Qt6Quick.dll',
    'Qt6Sql.dll',
    'Qt6WebEngine*.dll',
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('photo_cropper/i18n', 'photo_cropper/i18n'),
        *CV2_DATA_FILES,
    ],
    hiddenimports=sorted(set([
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
        'winotify',
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


def should_exclude_binary(name):
    import fnmatch
    name_lower = name.lower()
    for pattern in EXCLUDE_BINARIES:
        if fnmatch.fnmatch(name_lower, pattern.lower()):
            return True
    return False


a.binaries = [b for b in a.binaries if not should_exclude_binary(b[0])]

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhotoCropper_v9_single',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
        'Qt*.dll',
    ],
    runtime_tmpdir=RUNTIME_TMPDIR,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version=None,
)

"""
2026-04-19 note:
    - Hidden imports now use `collect_submodules(...)` for the split package
      families introduced by the management-shell and core refactors.
    - `runtime_tmpdir` is derived from `LOCALAPPDATA`/temp at build time to
      avoid username-specific hardcoded paths in the checked-in spec.

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
    - The new module is explicitly listed in hidden imports in addition to
      `collect_submodules(...)`. No onefile-specific data files or external
      runtime dependencies were added.

2026-06-04 note:
    - Stability hardening added batch fatal status fields, failed-folder-name
      validation, explicit file-list preflight, watch stop-race preservation,
      background job finalization, and Scheduler once retry behavior.
    - The changes stay within packages already covered by `collect_submodules`
      and the explicit hidden imports above. No onefile-specific runtime data,
      third-party dependency, or extraction-path policy change is required.

2026-06-29 note:
    - App root directory renamed from `;opencv/` to `opencv/`.
    - `winotify` is loaded via `importlib` at runtime; explicit hidden import
      preserves Windows toast support in onefile builds.
    - Dev-only automation (`test_reset`, pytest, verify scripts) does not affect
      onefile packaging or extraction policy.
"""
