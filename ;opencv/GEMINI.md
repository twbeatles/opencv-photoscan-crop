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
│         ui/main/window.py                 │
│   (Composition Root / signal wiring)     │
└─────────────────┬─────────────────────────┘
                  ▼
┌───────────────────────────────────────────┐
│         ui/main/actions/                  │
│  preview/batch/input/watch/tools/...      │
└─────────────────┬─────────────────────────┘
                  ▼
┌───────────────────────────────────────────┐
│         ui/main/builders/                 │
│  menu/toolbar/central/statusbar/fab       │
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
| `image/processor.py` | 핵심 크롭 알고리즘 (Canny, CLAHE, Sobel) |
| `batch/processor.py` | 다중 이미지 배치 처리 |
| `settings_model/app_settings.py` | 모든 설정 dataclass 정의 |
| `multi_photo_detector.py` | 한 스캔에서 여러 사진 분리 |
| `watermark_processor.py` | 텍스트/이미지 워터마크 |
| `resize_processor.py` | 이미지 리사이즈 |
| `processed_index.py` | `skip_processed` 로컬 처리 이력 인덱스 |

### Stability-Critical Flow

- Watch Mode는 `ui/main/actions/watch.py`를 통해 `BatchProcessor.process_single()` 경로를 재사용합니다.
- 저장 전 후처리 순서는 단일/멀티포토 모두 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 폴더 라우팅(워터마크 전) → 워터마크입니다.
- `performance.max_image_size_mb`는 실제 처리 전에 파일 크기 제한으로 적용됩니다.
- `skip_processed`는 `.photocropper/processed_index.json` 인덱스를 우선 사용하고, 실패 시 자동 분류 하위 폴더까지 포함해 fallback 탐지합니다.
- 얼굴 감지 `use_dnn=True`는 모델 자동 다운로드/체크섬 검증 후 로드하며, 실패 시 Haar로 즉시 폴백합니다.
- 멀티스레드 취소는 완료 future를 drain하고 남은 미실행 항목을 `CANCELLED`로 집계해 통계 정합성을 유지합니다.
- 스케줄러는 `watch_mode.scheduler_*` 설정과 런타임 연결되어 앱 실행 중 자동 배치를 트리거합니다.

### UI Components

| 파일 | 역할 |
|------|------|
| `main/window.py` | 메인 윈도우 composition root |
| `main/actions/` | preview/batch/input/watch/tools/settings/lifecycle 계층 |
| `main/builders/` | menu/toolbar/central/statusbar/fab 빌더 |
| `settings/panel.py` | 모든 설정 UI 패널 |
| `preview_widget.py` | 이미지 미리보기 위젯 |
| `toast_notification.py` | 토스트 알림 시스템 |

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
    │  Stage 2: Background Mask (balanced/accurate)
    ▼ ─────────────────────────────────
    │  Stage 3: Adaptive Threshold
    │  method: cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    ▼ ─────────────────────────────────
    │  Stage 4: Gradient Analysis (Sobel)
    │  combined X, Y gradients
    ▼ ─────────────────────────────────
    │  Stage 5: Harris Corner (optional)
    │  corner_block_size, corner_k
    ▼ ─────────────────────────────────
    │  Stage 6: Hough Rectangle (balanced/accurate fallback)
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
# core/settings_model/app_settings.py 주요 클래스

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

# v9.0+ 추가 예시
@dataclass
class ClassificationSettings:
    enabled: bool = False
    model: str = "basic"   # basic | advanced | custom(custom=advanced)
    category_folders: dict[str, str]  # portrait/landscape/document/blackwhite/other

@dataclass
class FaceDetectionSettings:
    use_dnn: bool = False
    min_face_size: int = 30

@dataclass
class SmartEnhancementSettings:
    adjust_exposure: bool = True
    adjust_color_balance: bool = True
    strength: int = 50
```

## Common Tasks

### 1. 새 처리 옵션 추가

1. `core/settings_model/app_settings.py`에 dataclass 필드 추가
2. `ui/widgets/settings/panel.py`에 UI 위젯 추가
3. `core/image/processor.py`에 처리 로직 추가

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
    - 취소 시 완료 future drain + 미실행 작업 `CANCELLED` 반영

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

## 2026-03-01 Update Notes

- CLI merge order is now fixed and documented:
  - Merge: defaults -> preset -> config -> cli override
  - Priority: CLI > config > preset
- New CLI AI controls are available for classification, face detection, and smart enhancement.
- Profile compatibility model:
  - Legacy key `advanced_processing` remains readable
  - Save/export path normalizes key to `advanced`
- Watch diagnostics and observability were expanded with detailed completion status and queue metrics.
- Recursive watch mode now scans newly watched subdirectories immediately for pre-existing images.

## 2026-03-03 Update Notes

- Main window now supports folder-level batch contour editing with previous/next navigation and one-shot save extraction.
- Added failed-boundary correction mode:
  - Collects files that failed auto boundary detection
  - Prompts user to switch to failed-files-only manual correction
- Original preview supports direct 4-point boundary input when auto contour is unavailable.
- Manual extraction cancellation path is wired to avoid UI freeze on close/cancel.
- Watch timeout is configurable through watch_mode.max_wait_seconds (default 30.0).
- Selftest coverage was extended for CLI merge precedence, recursive watch ingestion, and max-wait roundtrip.


## 2026-03-02 Split Refactor Notes

- Split long modules into package paths:
  - `core/settings_model`, `core/advanced`, `core/face`, `core/image`, `core/batch`
  - `ui/main`, `ui/widgets/settings`, `i18n/catalog`
- Updated internal imports and packaging metadata (`photo_cropper.spec`) for the new package layout.
- Runtime behavior target remains unchanged: CLI options, settings schema, output rules, watch/batch contracts.

## 2026-03-04 Consistency Check Notes

- Verified `pyright --project pyrightconfig.json` with 0 errors / 0 warnings.
- Updated `QWidget` override event signatures (`dragEnterEvent`, `dropEvent`, `keyPressEvent`) to match PyQt6 stub types via `Optional[...]`.
- Added explicit PyInstaller hidden imports for split modules:
  `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`.

## 2026-03-09 UI/MainWindow Consistency Notes

- `ui/main/window.py` is now a composition root that wires services, signals, and Qt event forwarding.
- Runtime behavior lives under `ui/main/actions/`, widget construction lives under `ui/main/builders/`, and shared context types live in `ui/main/models.py`.
- `photo_cropper.spec` hidden imports now explicitly cover the canonical UI package paths and the compatibility shim modules kept under `ui/main/*.py`.

## 2026-03-05 Integrated Improvement Notes

- Added processed index module: `core/processed_index.py` (`.photocropper/processed_index.json`)
- Wired skip-processed index checks/updates across batch/watch/manual flows
- Added classification folder mapping setting (`category_folders`) and settings-panel UI exposure
- Improved watch readiness fairness and timeout handling (`stat failed`/`read failed` paths)
- Connected runtime scheduler execution path in `MainWindow` with busy-conflict skip policy
- CLI cancel exit code aligned to `130`

## 2026-03-08 Precision Update Notes

- Implemented the full precision improvement plan (10 items, P0+P1+P2).
- Detection core:
  - `accurate` mode now collects Stage 1~6 candidates and performs global re-ranking.
  - `fast`/`balanced` keep early-exit flow.
  - Edge-support scoring uses a dedicated reference edge map, not stage binary masks.
  - Area/aspect/Hough scoring paths were upgraded for rotated/skewed inputs.
- Multi-photo:
  - Added `DetectedPhoto.quad` contract.
  - `crop_photos()` now uses perspective-first crop (`warpPerspective`) with bbox fallback.
  - Dedup now combines IoU + center distance + edge gap, with `merge_distance` applied.
- EXIF/Face:
  - EXIF orientation normalization on load (`ImageOps.exif_transpose` when Pillow is available).
  - Face rotation angle now uses `primary_face` instead of `faces[0]`.
- Tuning exposure:
  - Added UI + CLI controls for:
    - `min_area_ratio`, `max_area_ratio`
    - `bg_mask_delta`
    - `adaptive_block_size`, `adaptive_c`
- Benchmark:
  - Added `photo_cropper.benchmark` runnable harness + JSON report metrics.
  - Added `BENCHMARK_LABEL_FORMAT.md` and `benchmark/labels.template.json`.
  - Real-image datasets are intentionally excluded from the repository.
