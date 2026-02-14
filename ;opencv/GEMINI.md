# GEMINI.md - Photo Cropper v9.0 AI Assistant Guide

## Quick Reference

| 항목 | 값 |
|------|-----|
| 언어 | Python 3.8+ |
| GUI | PyQt6 |
| 이미지 처리 | OpenCV 4.8+ |
| 진입점 | `run.py` |
| 설정 파일 | Windows: `%APPDATA%/PhotoCropper/settings.json`<br>macOS/Linux: `~/.photo_cropper/photo_cropper_settings.json` |

## Architecture Overview

```
┌───────────────────────────────────────────┐
│              run.py (Entry)                │
└─────────────────┬─────────────────────────┘
                  ▼
┌───────────────────────────────────────────┐
│         photo_cropper/main.py             │
│         (QApplication Setup)              │
└─────────────────┬─────────────────────────┘
                  ▼
┌───────────────────────────────────────────┐
│         ui/main_window.py                 │
│         (MainWindow - 메인 UI)             │
│  ┌─────────────┬───────────────────────┐  │
│  │ SettingsPanel│ PreviewWidget        │  │
│  │ ToastManager │ ThumbnailGrid        │  │
│  └─────────────┴───────────────────────┘  │
└─────────────────┬─────────────────────────┘
                  ▼
┌───────────────────────────────────────────┐
│              core/ (처리 엔진)              │
│  ┌───────────────────────────────────────┐│
│  │ ImageProcessor    - 크롭 알고리즘     ││
│  │ BatchProcessor    - 배치 처리        ││
│  │ SettingsManager   - 설정 관리        ││
│  │ WatermarkProcessor - 워터마크        ││
│  │ ResizeProcessor   - 리사이즈         ││
│  │ FolderWatcher     - 폴더 감시        ││
│  └───────────────────────────────────────┘│
└───────────────────────────────────────────┘
```

## Key Files

### Core Logic

| 파일 | 역할 |
|------|------|
| `image_processor.py` | 핵심 크롭 알고리즘 (Canny, CLAHE, Sobel) |
| `batch_processor.py` | 다중 이미지 배치 처리 |
| `settings.py` | 모든 설정 dataclass 정의 |
| `multi_photo_detector.py` | 한 스캔에서 여러 사진 분리 |
| `watermark_processor.py` | 텍스트/이미지 워터마크 |
| `resize_processor.py` | 이미지 리사이즈 |

### Stability-Critical Flow

- Watch Mode는 `ui/main_window.py`에서 `BatchProcessor.process_single()`을 호출해 배치와 동일 파이프라인을 재사용합니다.
- 저장 전 후처리 순서는 단일/멀티포토 모두 얼굴 보정 → 리사이즈 → 워터마크 → 분류 폴더 라우팅입니다.
- 멀티스레드 취소는 pending future를 우선 취소해 중단 응답성을 확보합니다.

### UI Components

| 파일 | 역할 |
|------|------|
| `main_window.py` | 메인 윈도우 (60KB+, 1500+ lines) |
| `settings_panel.py` | 모든 설정 UI 패널 |
| `preview_widget.py` | 이미지 미리보기 위젯 |
| `toast_notification.py` | 토스트 알림 시스템 |
| `thumbnail_grid_widget.py` | 썸네일 그리드 뷰 |

## Detection Algorithm Pipeline

```
입력 이미지
    │
    ▼ CLAHE 대비 향상 (use_clahe=True)
    │
    ▼ 그레이스케일 변환
    │
    ▼ ─────────────────────────────────
    │  Stage 1: Multi-Scale Canny Edge
    │  scales: [0.5, 1.0, 1.5]
    │  thresholds: canny_min, canny_max
    ▼ ─────────────────────────────────
    │  Stage 2: Adaptive Threshold
    │  method: cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    ▼ ─────────────────────────────────
    │  Stage 3: Gradient Analysis (Sobel)
    │  combined X, Y gradients
    ▼ ─────────────────────────────────
    │  Stage 4: Harris Corner (optional)
    │  corner_block_size, corner_k
    ▼ ─────────────────────────────────
    │
    ▼ Contour Scoring + Best Selection
    │
    ▼ Perspective Transform (4-point)
    │
    ▼ Post-processing (sharpen, denoise, etc.)
    │
    ▼ Output Image
```

## Settings Dataclasses

```python
# core/settings.py 주요 클래스

@dataclass
class AlgorithmSettings:
    canny_min: int = 50
    canny_max: int = 150
    use_clahe: bool = True
    multi_scale_edge: bool = True
    contour_scoring: str = "enhanced"
    min_area_ratio: float = 0.1
    max_area_ratio: float = 0.95

@dataclass
class ProcessingSettings:
    auto_contrast: bool = True
    to_grayscale: bool = False
    apply_sharpening: bool = False
    denoise: bool = False

@dataclass
class OutputSettings:
    output_format: str = "JPG"
    jpg_quality: int = 95

@dataclass
class AppSettings:
    algorithm: AlgorithmSettings
    processing: ProcessingSettings
    output: OutputSettings
    ui: UISettings
    # ... more settings
```

## Common Tasks

### 1. 새 처리 옵션 추가

1. `core/settings.py`에 dataclass 필드 추가
2. `ui/widgets/settings_panel.py`에 UI 위젯 추가
3. `core/image_processor.py`에 처리 로직 추가

### 2. 새 알고리즘 단계 추가

1. `DetectionStage` enum에 새 단계 추가
2. `ImageProcessor.process_image()`에 단계 로직 추가
3. `find_best_contour()` 호출로 결과 평가

### 3. 새 출력 포맷 추가

1. `OutputFormat` enum에 포맷 추가
2. `file_helpers.py`의 저장 로직 수정
3. `OutputSettings`에 해당 포맷 옵션 추가

## Keyboard Shortcuts

| 키 | 기능 |
|-----|------|
| `Ctrl+O` | 입력 폴더 선택 |
| `Ctrl+I` | 이미지 열기 |
| `Ctrl+P` | 미리보기 |
| `Ctrl+R` | 90도 회전 |
| `Ctrl+Z/Y` | Undo/Redo |
| `F11` | 전체화면 |
| `F5` | 새로고침 |
| `Ctrl+E` | 출력 폴더 열기 |

## Best Practices

1. **유니코드 경로 처리**
   ```python
   # 올바른 방법
   img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
   # 피해야 할 방법
   img = cv2.imread(path)  # 한글 경로 오류
   ```
   - 워터마크 이미지 로딩도 동일한 패턴을 사용해야 합니다.

2. **CLAHE/커널 캐싱**
   - `ImageProcessor._get_clahe_with_settings()` 사용
   - 반복 호출 시 성능 향상

3. **비동기 처리**
    - `BatchProcessor`는 `threading.Thread` + `ThreadPoolExecutor` 기반
    - 콜백으로 진행률 업데이트
    - 취소 시 pending 작업을 우선 취소하고 in-flight 작업은 완료를 기다릴 수 있음

4. **설정 자동 저장**
   - `_schedule_auto_save()` + debounce
   - 과도한 파일 I/O 방지

## Build & Distribution

```bash
# 개발 실행
python run.py

# CLI 실행
python -m photo_cropper.cli --help

# 빌드
pyinstaller photo_cropper.spec --clean
# → dist/PhotoCropper_v9.exe
```

## Troubleshooting

| 문제 | 해결 |
|------|------|
| 한글 경로 오류 | np.fromfile + cv2.imdecode 사용 |
| 메모리 부족 | max_image_size_mb 조정 |
| GPU 미사용 | OpenCV CUDA 빌드 필요 |
| 감지 실패 | canny_min/max 조정, CLAHE 활성화 |
| Watch/Batch 결과 차이 | Watch Mode가 `BatchProcessor.process_single()` 경로를 사용하는지 확인 |
