# -*- mode: python ; coding: utf-8 -*-
"""
Photo Cropper v8.5 PyInstaller Spec File

최적화 및 경량화:
- UPX 압축 적용
- 불필요한 모듈 제외
- 단일 실행 파일 생성
"""

import os
import sys

block_cipher = None

# 현재 디렉토리
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['run.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=[
        # i18n 번역 파일 포함
        ('photo_cropper/i18n', 'photo_cropper/i18n'),
    ],
    hiddenimports=[
        # PyQt6 필수 모듈
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        # OpenCV
        'cv2',
        # NumPy
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # ============================================
    # 경량화: 불필요한 모듈 제외
    # ============================================
    excludes=[
        # 데이터 과학 라이브러리 (사용 안함)
        'matplotlib', 'matplotlib.pyplot',
        'scipy', 'scipy.io', 'scipy.stats', 'scipy.signal',
        'pandas', 'sklearn', 'tensorflow', 'torch',
        
        # GUI 충돌 방지 (다른 Qt 바인딩)
        'PyQt5', 'PySide2', 'PySide6', 'tkinter', 'wx',
        
        # 개발 도구
        'IPython', 'jupyter', 'notebook', 'nbconvert', 'nbformat',
        'pytest', 'unittest', 'doctest', 'pdb', 'pdbpp',
        'black', 'flake8', 'pylint', 'mypy',
        
        # 네트워크/서버 (불필요)
        'http.server', 'xmlrpc', 'ftplib', 'smtplib', 'poplib',
        'socketserver', 'wsgiref', 
        
        # 기타 불필요
        'PIL',  # Pillow - OpenCV로 대체
        'curses', 'readline',
        'distutils', 'setuptools', 'pkg_resources', 'pip',
        'lib2to3', 'ensurepip',
        
        # Windows 전용 제외
        'win32com', 'win32api', 'win32gui',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================
# OpenCV 최적화: 불필요한 바이너리 제거
# ============================================
opencv_excludes = [
    'libopencv_dnn',       # 딥러닝 (미사용)
    'libopencv_ml',        # 머신러닝 (미사용)
    'libopencv_video',     # 비디오 (미사용)  
    'libopencv_videoio',   # 비디오 I/O (미사용)
    'libopencv_objdetect', # 객체 감지 (미사용)
    'libopencv_photo',     # 사진 복원 (고급 사용시 활성화)
    'libopencv_stitching', # 파노라마 (미사용)
    'opencv_videoio_ffmpeg', # FFmpeg (미사용)
]

# 바이너리에서 제외
a.binaries = [b for b in a.binaries if not any(ex in b[0].lower() for ex in opencv_excludes)]

# ============================================
# NumPy 최적화: 테스트 파일 제거
# ============================================
a.datas = [d for d in a.datas if 'numpy/tests' not in d[0]]
a.datas = [d for d in a.datas if 'numpy/doc' not in d[0]]
a.datas = [d for d in a.datas if 'numpy/f2py' not in d[0]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ============================================
# 단일 실행 파일 생성 (onefile)
# ============================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartPhotoCropper_v85',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,           # 심볼 제거 (크기 감소)
    upx=True,             # UPX 압축 (설치 필요: https://upx.github.io/)
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
        'Qt*.dll',         # Qt DLL은 UPX 압축 시 문제 발생 가능
    ],
    runtime_tmpdir=None,
    console=False,         # GUI 앱: 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,             # 아이콘: 'resources/icon.ico' (있다면)
    version=None,          # 버전 정보: 'version_info.txt' (선택)
)

# ============================================
# 빌드 명령어:
#   pyinstaller photo_cropper.spec --clean
#
# UPX 설치 (선택, 권장):
#   https://github.com/upx/upx/releases 에서 다운로드
#   PATH에 upx.exe 추가
# ============================================
