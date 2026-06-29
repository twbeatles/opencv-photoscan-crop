# 📸 Smart Photo Cropper v8.0

> 이 문서는 v8.0 기준의 보관(legacy) 문서입니다.
> 현재 안정화된 최신 동작(Watch/Batch 파이프라인 일치, 유니코드 워터마크 경로, 취소 응답성 개선 등)은 `README.md` 및 `README_EN.md`를 참고하세요.

**[English](#english) | [한국어](#korean)**

---

<div id="english"></div>

## Overview
**Smart Photo Cropper v8.0** is an intelligent batch image processing tool designed to automatically detect, crop, and enhance photos from scanned images or raw camera captures. Version 8.0 introduces a completely redesigned **Glassmorphism UI**, improved performance with GPU acceleration support, and advanced restoration features.

## ✨ Key Features
- **Auto Detection & Crop**: Intelligent multi-stage algorithm (Canny, Adaptive Threshold, Sobel) to find photos.
- **Batch Processing**: Process thousands of images with multi-threading.
- **Glassmorphism UI**: Modern, sleek interface with blur effects, smooth animations, and dark/light modes.
- **Advanced Processing**:
    - **Auto Deskew**: Automatically straightens tilted photos.
    - **Color Correction**: Restores faded colors using Gray World/White Patch algorithms.
    - **Old Photo Restoration**: Removes noise and enhances contrast for vintage photos.
    - **Perspective Correction**: Rectifies distortion in documents or photos.
- **Performance**:
    - **GPU Acceleration**: Optional CUDA support for faster processing.
    - **Smart Memory Management**: Optimized for large resolution images.

## 🚀 Installation
1. **Requirements**: Python 3.9+, PyQt6, OpenCV, NumPy
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure `opencv-python-headless` is used for lightweight server/cli usage, or `opencv-python` for GUI)*

## 🖥️ Usage
1. Run the application:
   ```bash
   python run.py
   ```
2. **Select Input Folder**: Drag & drop your folder containing images.
3. **Settings**:
   - Enable **Auto Deskew** or **Color Correction** in the Settings panel.
   - Adjust **Sensitivity** if detection is too strict or loose.
4. **Start**: Click "Start Processing".

---

<div id="korean"></div>

## 개요
**Smart Photo Cropper v8.0**은 스캔된 이미지나 촬영본에서 사진 영역을 자동으로 감지하여 자르고 보정해주는 지능형 일괄 처리 도구입니다. v8.0 업데이트로 **글래스모피즘(Glassmorphism)** 디자인이 적용된 새로운 UI와 GPU 가속, 고급 복원 기능이 추가되었습니다.

## ✨ 주요 기능
- **자동 감지 및 자르기**: 다단계 알고리즘(Canny, Adaptive Threshold, Sobel)을 통한 정밀 검출.
- **일괄 처리(Batch)**: 멀티스레딩을 지원하여 대량의 이미지를 고속으로 처리.
- **현대적인 UI & UX 개선 (New in v8.0)**:
    - **글래스모피즘 디자인**: 투명하고 부드러운 현대적 인터페이스.
    - **공간 최적화**: 컨트롤 바 최소화 및 "검출 영역 표시" 등 라벨 단축으로 사진 영역 극대화.
    - **자유로운 레이아웃**: `Splitter` 도입으로 프리뷰/히스토그램 비율 및 컨트롤 바 높이 조절 가능.
    - **스크롤 UI**: 작은 화면에서도 모든 설정에 접근 가능하도록 탭 스크롤 적용.
- **고급 이미지 처리**:
    - **자동 기울기 보정 (Auto Deskew)**: 비뚤어진 사진을 자동으로 수평에 맞게 회전.
    - **색상 자동 보정**: 바랜 사진의 색감을 생생하게 복원.
    - **옛날 사진 복원**: 노이즈 제거 및 디테일 강화.
    - **원근 왜곡 보정**: 문서나 사진의 기울어진 원근감 교정.
- **성능 최적화**:
    - **GPU 가속**: CUDA 지원 그래픽카드를 활용한 속도 향상.
    - **메모리 최적화**: 고해상도 이미지 처리 시 메모리 사용 최소화.

## 🚀 설치 방법
1. **필수 사항**: Python 3.9 이상
2. **라이브러리 설치**:
   ```bash
   pip install PyQt6 opencv-python numpy
   ```

## 🖥️ 사용법
1. 프로그램 실행:
   ```bash
   python -m photo_cropper.main
   ```
   또는 `run.py` 실행.
2. **폴더 선택**: 처리할 이미지가 있는 폴더를 메인 화면에 드래그 앤 드롭하세요.
3. **설정**:
   - 우측 설정 패널에서 **자동 기울기 보정**, **색상 보정** 등 필요한 옵션을 켭니다.
   - 툴바에서 프리셋(기본, 옛날 사진, 문서 등)을 선택할 수 있습니다.
4. **시작**: '변환 시작' 버튼을 눌러 작업을 시작합니다.

## 📦 빌드 (배포용)
경량화된 단일 실행 파일 생성:
```bash
pyinstaller photo_cropper.spec
```

## 📝 라이선스
MIT License
