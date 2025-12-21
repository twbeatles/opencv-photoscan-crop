# 📸 사진 자동 자르기 (Photo Cropper) v7.1

스캔된 사진이나 배경 위에 놓인 사진을 자동으로 감지하여 정확하게 자르는 Python 애플리케이션입니다.

## ✨ 주요 기능

- **3단계+ 지능형 탐색 알고리즘**: 다양한 배경에서 높은 검출 성공률
- **PyQt6 기반 현대적 UI**: 다크/라이트 테마 지원
- **HiDPI 디스플레이 지원**: 고해상도 모니터에서도 선명한 UI
- **실시간 미리보기**: 마우스 휠로 확대/축소, 드래그로 이동
- **배치 처리**: 대량의 이미지를 한 번에 처리 (예상 시간 표시)
- **드래그 앤 드롭**: 폴더나 이미지를 직접 끌어다 놓기
- **다양한 출력 포맷**: JPG, PNG, WEBP 지원
- **Toast 알림**: 작업 완료시 비침투적 알림

## 🛠️ 감지 알고리즘

| 단계 | 알고리즘 | 설명 |
|------|----------|------|
| 1단계 | Multi-Scale Canny Edge | 다중 스케일 에지 검출 |
| 2단계 | Adaptive Threshold | 적응형 이진화 |
| 3단계 | Gradient Analysis (Sobel) | 그래디언트 분석 |
| 4단계 | Harris Corner Detection | 코너 검출 (선택적) |

## 📦 설치

### 요구 사항

- Python 3.8 이상
- Windows / macOS / Linux

### 설치 방법

```bash
# 저장소 클론 또는 다운로드 후
cd photo_cropper

# 의존성 설치
pip install -r requirements.txt
```

### 의존성

```
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
PyQt6>=6.5.0
```

## 🚀 사용법

### 애플리케이션 실행

```bash
python run.py
```

### 기본 워크플로우

1. **입력 폴더 선택**: 처리할 이미지가 있는 폴더 선택
2. **출력 폴더 선택**: 결과를 저장할 폴더 지정 (선택사항)
3. **설정 조정**: 오른쪽 패널에서 알고리즘/출력 설정 변경
4. **미리보기**: `Ctrl+P`로 한 장 테스트
5. **변환 시작**: 전체 이미지 일괄 처리

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 입력 폴더 선택 |
| `Ctrl+I` | 이미지 열기 |
| `Ctrl+P` | 미리보기 |
| `Ctrl+E` | 출력 폴더 열기 |
| `F1` | 도움말 |
| `Ctrl+Q` | 종료 |

## ⚙️ 설정 옵션

### 알고리즘 설정

- **Canny 임계값**: 에지 감지 민감도 조절
- **CLAHE**: 저대비 이미지 향상
- **다중 스케일**: 다양한 크기의 사진 감지
- **코너 검출**: 추가적인 정확도 향상

### 출력 설정

- **출력 포맷**: JPG, PNG, WEBP
- **품질 조절**: 포맷별 압축률/품질 설정
- **그레이스케일 변환**: 흑백 출력
- **노이즈 제거**: 스캔 노이즈 감소
- **선명도 향상**: 출력 이미지 선명화

## 📁 프로젝트 구조

```
photo_cropper/
├── __init__.py          # 패키지 초기화
├── main.py              # 애플리케이션 진입점
├── core/
│   ├── image_processor.py   # 핵심 이미지 처리 엔진
│   ├── batch_processor.py   # 배치 처리 관리
│   └── settings.py          # 설정 데이터클래스
├── ui/
│   ├── main_window.py       # 메인 윈도우
│   ├── widgets/             # UI 위젯들
│   │   ├── preview_widget.py    # 미리보기
│   │   ├── settings_panel.py    # 설정 패널
│   │   ├── progress_dialog.py   # 진행률 다이얼로그
│   │   ├── histogram_widget.py  # 히스토그램
│   │   └── toast_widget.py      # Toast 알림
│   └── styles/              # 테마 스타일시트
└── utils/
    └── file_helpers.py      # 파일 유틸리티
```

## 🎨 테마

- **다크 테마**: 눈의 피로를 줄이는 어두운 색상
- **라이트 테마**: 밝은 환경에 적합한 밝은 색상

툴바의 🌙 버튼 또는 보기 메뉴에서 테마 전환 가능

## 🖥️ HiDPI 지원

- Windows, macOS, Linux의 고해상도 디스플레이 자동 지원
- Per-Monitor DPI awareness (Windows)
- Qt6 네이티브 HiDPI 스케일링

## 📦 빌드

### PyInstaller로 실행 파일 생성

```bash
pyinstaller photo_cropper.spec
```

빌드된 파일은 `dist/PhotoCropper/` 폴더에 생성됩니다.

## 📝 지원 포맷

### 입력 포맷

PNG, JPG, JPEG, BMP, GIF, TIFF, TIF, WEBP, HEIC, HEIF

### 출력 포맷

JPG, PNG, WEBP

## 📄 라이선스

MIT License

## 🔄 변경 이력

### v7.1 (2024-12)
- HiDPI 디스플레이 지원 추가
- Toast 알림 시스템 추가
- 진행률 다이얼로그에 예상 남은 시간 표시
- 히스토그램 위젯 테마 연동
- 코드 품질 개선 및 버그 수정
