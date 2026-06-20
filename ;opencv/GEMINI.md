# GEMINI.md — Photo Cropper AI Assistant Guide

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
run.py (Entry)
    ↓
photo_cropper/main.py  (QApplication Setup)
    ↓
ui/main/window.py  (Composition Root / signal wiring)
    ↓
ui/main/composition/actions/builders/services/...
    ↓
core/  (처리 엔진)
    ├── ImageProcessor    — 크롭 알고리즘
    ├── BatchProcessor    — 배치 처리
    ├── SettingsManager   — 설정 관리
    ├── WatermarkProcessor
    ├── ResizeProcessor
    └── FolderWatcher     — 폴더 감시
```

## Key Files

### Core Logic

| 파일 | 역할 |
|------|------|
| `cli_support/runtime.py` | CLI parser / settings merge / validation / execution |
| `image/processor.py` | 핵심 크롭 알고리즘 (Canny, CLAHE, Sobel) |
| `image/types.py` | 크롭/미리보기 결과 타입 |
| `batch/processor.py` | 다중 이미지 배치 처리 |
| `batch/types.py` | 배치 진행/결과 타입 |
| `file_watch/` | `FolderWatcher`, `AutoProcessor`, watch result 타입 |
| `advanced/processor.py` | advanced image operation facade |
| `settings_model/app_settings.py` | 모든 설정 dataclass 정의 |
| `settings_model/manager.py` | 설정 저장/로드 |
| `settings_model/migration.py` | 레거시 설정 마이그레이션 |
| `settings_model/validation.py` | 실행 전 설정 검증 |
| `multi_photo_detector.py` | 한 스캔에서 여러 사진 분리 |
| `watermark_processor.py` | 텍스트/이미지 워터마크 |
| `resize_processor.py` | 이미지 리사이즈 |
| `processed_index.py` | `skip_processed` 로컬 처리 이력 인덱스 |
| `utils/image_io.py` | 유니코드 경로 안전 이미지 로딩 |
| `utils/path_validation.py` | 경로/파일명 segment validator |

### UI Components

| 파일 | 역할 |
|------|------|
| `main/window.py` | 메인 윈도우 composition root |
| `main/composition/` | 서비스 생성, 액션 바인딩, 레이아웃 조립 |
| `main/actions/` | preview/batch/input/watch/tools/settings/lifecycle |
| `main/builders/` | menu/toolbar/central/statusbar/fab 빌더 |
| `main/services/` | runtime flow / message helper |
| `widgets/settings/` | 설정 패널 facade + 탭/검증/i18n helper |
| `widgets/management/` | Library/Review/Duplicates/Jobs/Collections/Recipes 페이지 |
| `preview_widget.py` | 이미지 미리보기 위젯 |
| `toast_notification.py` | 토스트 알림 시스템 |

## Detection Algorithm Pipeline

```
입력 이미지
    ↓ CLAHE 대비 향상 (use_clahe=True)
    ↓ 그레이스케일 변환
    ↓ Stage 1: Multi-Scale Canny Edge  (scales: [0.5, 1.0, 1.5])
    ↓ Stage 2: Background Mask         (balanced/accurate)
    ↓ Stage 3: Adaptive Threshold      (ADAPTIVE_THRESH_GAUSSIAN_C)
    ↓ Stage 4: Gradient Analysis       (Sobel X+Y)
    ↓ Stage 5: Harris Corner           (optional)
    ↓ Stage 6: Hough Rectangle         (balanced/accurate fallback)
    ↓ Contour Scoring + Best Selection
    ↓ Perspective Transform (4-point)
    ↓ Post-processing (sharpen, denoise, ...)
    ↓ Output Image
```

- `fast`/`balanced`: 조기 종료
- `accurate`: Stage 1~6 후보 전체 수집 후 전역 재랭킹

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
class ClassificationSettings:
    enabled: bool = False
    model: str = "basic"   # basic | advanced (custom aliases to advanced)
    category_folders: dict[str, str]

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

## Stability-Critical Contracts

- Watch Mode는 `BatchProcessor.process_single()` 경로를 재사용
- 후처리 순서: 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 라우팅 → 워터마크
- 재귀 Batch/Watch/CLI: output이 input root 내부면 시작 차단
- 재귀 스캔 자동 제외: `output_root`, `_failed`, `backup`, `.photocropper`
- `skip_processed`: `.photocropper/processed_index.json` 우선, fallback은 파일명 탐색
  - signature: source_path + size + mtime_ns + pipeline_signature
  - `partial` 레코드 → 경고 후 재처리 (full skip 금지)
- `BatchProgress.fatal_error/fatal_message` → CLI exit code `1` + Job `failed`
- `file_management.failed_folder_name` → single path segment 검증 필수
- 명시 파일 목록 preflight: 누락 파일 하나라도 → 전체 차단
- Watch callback: `process_single(..., clear_stop_event=False)` 사용
- Watch 처리: settings snapshot에서 `move_failed_files=False` 강제
- Scheduler `once`: `STARTED`일 때만 소비, busy/no-files/config skip → 다음 tick 재시도
- 출력 경로: thread-safe reservation (일반/분류/멀티포토 공유)
- Library SQLite: WAL + `foreign_keys=ON` + `busy_timeout=5000`
- Batch job finalization: background thread + `management_task_finished` signal

## Common Development Tasks

### 새 처리 옵션 추가
1. `core/settings_model/app_settings.py`에 dataclass 필드 추가
2. `ui/widgets/settings/` 해당 탭에 UI 위젯 추가
3. `core/image/processor.py` 또는 후처리 파이프라인에 로직 추가

### 새 알고리즘 단계 추가
1. `DetectionStage` enum에 새 단계 추가
2. `ImageProcessor.process_image()`에 단계 로직 추가
3. `find_best_contour()` 호출로 결과 평가

### 새 출력 포맷 추가
1. `OutputFormat` enum에 포맷 추가
2. 저장 로직 수정
3. `OutputSettings`에 해당 포맷 옵션 추가

## Best Practices

```python
# 유니코드 경로 처리 — 올바른 방법
from photo_cropper.utils.image_io import load_image_unicode
img = load_image_unicode(path)

# 금지
img = cv2.imread(path)  # 한글 경로 오류
```

- **CLAHE/커널 캐싱**: `ImageProcessor._get_clahe_with_settings()` 사용
- **비동기 처리**: `BatchProcessor`는 `threading.Thread` + `ThreadPoolExecutor` 기반; 취소 시 완료 future drain + `CANCELLED` 반영
- **설정 자동 저장**: `_schedule_auto_save()` + debounce

## Build & Distribution

```bash
# 개발 실행
python run.py

# CLI
python -m photo_cropper.cli --help

# 안정 빌드
pyinstaller photo_cropper.spec --clean
# → dist/PhotoCropper_v9/PhotoCropper_v9.exe

# 실험용 단일 파일
pyinstaller photo_cropper_onefile.spec --clean
# → dist/PhotoCropper_v9_single.exe
```

## Troubleshooting

| 문제 | 해결 |
|------|------|
| 한글 경로 오류 | `utils.image_io.load_image_unicode()` 사용 |
| 메모리 부족 | `max_image_size_mb` 조정 |
| GPU 미사용 | OpenCV CUDA 빌드 필요 |
| 감지 실패 | `canny_min`/`max` 조정, CLAHE 활성화, `accurate` 모드 시도 |
| Watch/Batch 결과 차이 | Watch Mode가 `BatchProcessor.process_single()` 경로를 타는지 확인 |

## CLI Settings Merge Order

```
defaults → preset → config → cli override
우선순위: CLI > config > preset
```

- `--preset`: `BatchProfileManager`를 통한 실제 프로파일 로드
- `--config`: 전체 `AppSettings` 병합 (레거시 키 `advanced_processing` → `advanced` 지원)
- 병합 결과에 `validate_settings()` 적용 — invalid path segment → exit code `2`
