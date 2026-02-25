# CLAUDE.md - Photo Cropper v9.0 Project Guide

## 프로젝트 개요

스캔된 사진 또는 배경 위 사진을 자동 감지하여 크롭하는 Python 애플리케이션입니다.

- **진입점**: `run.py` → `photo_cropper/main.py`
- **Python**: 3.8+
- **프레임워크**: PyQt6 (GUI), OpenCV (이미지 처리)

## 핵심 의존성

```
opencv-python>=4.8.0  # 이미지 처리
numpy>=1.24.0         # 배열 연산
Pillow>=10.0.0        # 이미지 I/O
PyQt6>=6.5.0          # GUI
winotify>=1.1.0       # Windows 알림 (선택)
```

## 프로젝트 구조

```
photo_cropper/
├── main.py              # 진입점
├── cli.py               # CLI 인터페이스
├── core/                # 핵심 이미지 처리
│   ├── image_processor.py      # 메인 크롭 알고리즘
│   ├── batch_processor.py      # 배치 처리
│   ├── settings.py             # 설정 dataclass
│   ├── multi_photo_detector.py # 다중 사진 감지
│   ├── watermark_processor.py  # 워터마크
│   ├── resize_processor.py     # 리사이즈
│   ├── folder_watcher.py       # 폴더 감시
│   ├── scheduler.py            # 스케줄러
│   └── history_manager.py      # Undo/Redo
├── ui/                  # PyQt6 UI
│   ├── main_window.py          # 메인 윈도우
│   ├── styles/                 # 테마 스타일시트
│   └── widgets/                # UI 위젯
│       ├── settings_panel.py
│       ├── preview_widget.py
│       ├── toast_notification.py
│       └── ...
├── utils/               # 유틸리티
│   ├── file_helpers.py
│   ├── naming_rules.py
│   └── processing_log.py
└── i18n/                # 다국어 지원
    └── translations.py
```

## 핵심 클래스 및 API

### 1. ImageProcessor (core/image_processor.py)

사진 감지 및 크롭의 핵심 로직 담당.

```python
class ImageProcessor:
    def __init__(self, algorithm_settings, processing_settings, advanced_settings, performance_settings)
    def process_image(self, image_path: str) -> CropResult
    def load_image(self, image_path: str) -> np.ndarray
    def rotate_image(image: np.ndarray, angle: int) -> np.ndarray
    def apply_clahe(self, image: np.ndarray) -> np.ndarray
    def detect_edges_multiscale(self, gray: np.ndarray) -> np.ndarray
    def find_best_contour(self, edge_image, image_area, ...) -> tuple
```

**감지 알고리즘 단계**:
1. Multi-Scale Canny Edge Detection
2. Adaptive Threshold
3. Gradient Analysis (Sobel)
4. Harris Corner Detection (선택적)

### 2. MainWindow (ui/main_window.py)

메인 애플리케이션 윈도우.

- **드래그 앤 드롭**: 폴더/이미지 드롭 지원
- **테마**: 다크/라이트 테마 토글
- **키보드 단축키**: Ctrl+O, Ctrl+P, Ctrl+R, F5, F11 등

### 3. Settings (core/settings.py)

모든 설정을 dataclass로 관리:

- `AlgorithmSettings`: Canny 임계값, CLAHE 등
- `ProcessingSettings`: 자동 대비, 선명화 등
- `OutputSettings`: 출력 포맷, 품질
- `WatermarkSettings`: 워터마크 설정
- `ResizeSettings`: 리사이즈 설정
- `AppSettings`: 전체 설정 집합

### 4. BatchProcessor (core/batch_processor.py)

다중 이미지 배치 처리. 내부적으로 `threading.Thread` + `ThreadPoolExecutor` 기반으로 동작하며,
`PerformanceSettings`로 병렬 처리 스레드 수를 제어합니다.

- `process_single(input_path, output_dir)`를 제공하여 Watch Mode에서도 배치와 동일한 파이프라인을 사용합니다.
- 단일/멀티포토 모두 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 폴더 라우팅(워터마크 전 기준) → 워터마크 순서를 공통 적용합니다.
- 얼굴 감지 `use_dnn=True` 시 모델 자동 다운로드/체크섬 검증을 시도하며, 실패 시 Haar 감지로 즉시 폴백합니다.
- 취소 시 pending future를 빠르게 정리해 중단 응답성을 높였습니다.

## 주요 기능 흐름

1. **단일 이미지 처리**:
   ```
   MainWindow._do_preview() → ImageProcessor.process_image() → CropResult
   ```

2. **배치 처리**:
   ```
   MainWindow._start_processing() → BatchProcessor.start_async() →
   (ThreadPoolExecutor) ImageProcessor.process_image() → 콜백/로그 업데이트
   ```

3. **Watch Mode 처리**:
   ```
   MainWindow._start_watch_mode() → AutoProcessor →
   BatchProcessor.process_single() → 배치와 동일 후처리/저장
   ```

4. **설정 저장/로드**:
   ```
   SettingsManager.load() → AppSettings
   SettingsManager.save(AppSettings)
   → 저장 위치 (Windows): %APPDATA%/PhotoCropper/settings.json
   → 저장 위치 (macOS/Linux): ~/.photo_cropper/photo_cropper_settings.json
   ```

## 코딩 가이드라인

### 1. 이미지 처리

- OpenCV BGR 포맷 사용
- 유니코드 경로: `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)`
- CLAHE 및 커널 객체는 캐싱하여 재사용
- 워터마크 이미지 로드도 동일한 유니코드 안전 패턴 사용 (`cv2.imread` 직접 사용 지양)

### 2. GUI

- PyQt6 스타일시트로 테마 적용
- 시그널/슬롯 패턴 사용
- `BatchProcessor`의 `threading.Thread`/`ThreadPoolExecutor`로 무거운 처리 분리

### 3. 설정 관리

- dataclass 기반 설정
- JSON 직렬화
- 자동 저장 (debounce 적용)

## 빌드

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
```

출력: `dist/PhotoCropper_v9.exe`

## 문제 해결

### 한글 경로 오류
- `cv2.imread` 대신 `np.fromfile` + `cv2.imdecode` 사용

### GPU 가속
- `PerformanceSettings.use_gpu` 활성화
- OpenCV CUDA 빌드 필요

### 메모리 부족
- `PerformanceSettings.max_image_size_mb` 조정
- `downscale_large_images` 활성화

### Watch Mode/Batch 결과 불일치
- Watch Mode는 `BatchProcessor.process_single()` 경로를 사용해야 함
- 직접 `ImageProcessor.process_image()`만 호출하면 후처리(얼굴/스마트 보정, 리사이즈, 분류 라우팅, 워터마크)가 누락될 수 있음

### DNN 얼굴 감지 모델 다운로드 실패
- 네트워크/모델 파일 문제 시 경고 로그 후 Haar 캐스케이드로 자동 폴백됨
- 처리 실패가 아니라 정확도 저하 모드로 계속 진행됨

### 중단 응답 지연
- 멀티스레드 배치 취소는 in-flight 작업 완료를 일부 기다릴 수 있음
- pending 작업은 즉시 취소되므로 대기열 길이가 긴 경우 개선 효과가 큼
