# -*- mode: python ; coding: utf-8 -*-
"""
Photo Cropper v7.1 - PyInstaller Spec File

이 파일은 Photo Cropper를 Windows 실행 파일로 빌드하기 위한 PyInstaller 설정입니다.

빌드 방법:
    pyinstaller photo_cropper.spec

출력 위치:
    dist/PhotoCropper/PhotoCropper.exe
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 프로젝트 경로
block_cipher = None

# PyQt6 관련 숨겨진 imports
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
]

# 데이터 파일 수집
datas = []

# OpenCV 데이터 파일 (선택적)
try:
    import cv2
    cv2_path = cv2.__path__[0] if hasattr(cv2, '__path__') else None
    if cv2_path:
        # OpenCV는 대부분 코드이므로 별도 데이터 불필요
        pass
except:
    pass

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 모듈 제외 (빌드 크기 최적화)
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'pytest',
        'setuptools',
        'wheel',
        'pip',
        # Qt 불필요 모듈
        'PyQt6.QtNetwork',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtPositioning',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebSockets',
        'PyQt6.Qt3DCore',
        'PyQt6.Qt3DRender',
        'PyQt6.Qt3DInput',
        'PyQt6.Qt3DLogic',
        'PyQt6.Qt3DAnimation',
        'PyQt6.Qt3DExtras',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

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
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 아이콘 설정 (아이콘 파일이 있는 경우 활성화)
    # icon='assets/icon.ico',
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
