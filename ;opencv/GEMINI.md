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
│ ui/main/composition/actions/builders/...  │
│ services/actions/layout/runtime/i18n      │
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
| `cli_support/runtime.py` | CLI parser/settings merge/validation/execution runtime |
| `image/processor.py` | 핵심 크롭 알고리즘 (Canny, CLAHE, Sobel) |
| `image/types.py` | 크롭/미리보기 결과 타입 |
| `batch/processor.py` | 다중 이미지 배치 처리 |
| `batch/types.py` | 배치 진행/결과 타입 |
| `file_watch/` | `FolderWatcher`, `AutoProcessor`, watch result 타입 실제 구현 |
| `advanced/processor.py` | advanced image operation facade |
| `settings_model/app_settings.py` | 모든 설정 dataclass 정의 |
| `settings_model/manager.py` | 설정 저장/로드 진입점 |
| `settings_model/migration.py` | 레거시 설정/분류 폴더 기본값 마이그레이션 |
| `settings_model/validation.py` | 실행 전 설정 검증 요약 |
| `multi_photo_detector.py` | 한 스캔에서 여러 사진 분리 |
| `watermark_processor.py` | 텍스트/이미지 워터마크 |
| `resize_processor.py` | 이미지 리사이즈 |
| `processed_index.py` | `skip_processed` 로컬 처리 이력 인덱스 |
| `utils/image_io.py` | 유니코드 경로 안전 이미지 로딩 헬퍼 |
| `utils/path_validation.py` | 안전한 경로/파일명 segment validator |

### Stability-Critical Flow

- Watch Mode는 `ui/main/actions/watch.py`를 통해 `BatchProcessor.process_single()` 경로를 재사용합니다.
- 저장 전 후처리 순서는 단일/멀티포토 모두 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 폴더 라우팅(워터마크 전) → 워터마크입니다.
- 재귀 Batch/Watch/CLI는 output path를 input root 내부에 둘 수 없고, recursive scan에서는 `output_root`, `_failed`, `backup`, `.photocropper`를 자동 제외합니다.
- 재귀 출력/실패 보관/멀티포토 `*_photos`는 입력 기준 상대 경로를 유지합니다.
- `performance.max_image_size_mb`는 실제 처리 전에 파일 크기 제한으로 적용됩니다.
- `skip_processed`는 `.photocropper/processed_index.json` 인덱스를 우선 사용하고, 실패 시 자동 분류 하위 폴더까지 포함해 fallback 탐지합니다.
- `skip_processed` signature에는 언어별로 해석된 분류 폴더명과 `create_backup` 옵션이 포함됩니다.
- processed index v2는 레코드별 `status=success|partial`를 저장하며, `partial`은 경고 후 재처리하고 full skip하지 않습니다.
- `BatchProgress.partial_success`는 full success와 분리 집계되며, CLI는 항상 `processed/success/partial_success/failed/skipped`를 출력합니다.
- CLI `--strict-partial`은 partial-only run도 종료코드 `1`로 바꾸고, 분류 모델 `custom`은 `advanced` alias로만 유지됩니다.
- 얼굴 감지 `use_dnn=True`는 모델 자동 다운로드/체크섬 검증 후 로드하며, 실패 시 Haar로 즉시 폴백합니다.
- 멀티스레드 취소는 완료 future를 drain하고 남은 미실행 항목을 `CANCELLED`로 집계해 통계 정합성을 유지합니다.
- 스케줄러는 `watch_mode.scheduler_*` 설정과 런타임 연결되어 앱 실행 중 자동 배치를 트리거합니다.
- scheduler `once`는 날짜 없는 "다음 도래 HH:MM 1회 실행" 의미입니다.
- `once` 예약은 `ScheduleRunStatus.STARTED`일 때만 소비되며 busy/no-files/config-error skip에서는 보존됩니다.
- 재귀 Watch Mode는 output path가 input root 내부면 시작을 거부합니다.
- Watch 처리 경로는 settings snapshot에서 `move_failed_files=False`를 강제해 `_failed` 피드백 루프를 막습니다.
- `FolderWatcher.fileChanged`는 overwrite된 동일 경로도 size/mtime signature가 바뀌었을 때만 재큐잉합니다.
- 수동 contour preview는 `core.manual_extract.crop_manual_contour()`를 사용해 save와 같은 crop 규칙을 공유합니다.
- 일반/분류/멀티포토 출력 경로는 batch 단위 thread-safe reservation을 거쳐 같은 batch 안의 파일명 충돌을 방지합니다.
- 라이브러리 폴더 가져오기는 UI thread 밖에서 실행되고, SQLite 연결은 WAL, foreign key, busy timeout을 켭니다.
- Undo/Redo는 세션 내 설정 변경, 수동 crop, 라이브러리/컬렉션/레시피 수동 변경을 대상으로 하며 Batch/Watch 산출물 rollback은 제외합니다.

### UI Components

| 파일 | 역할 |
|------|------|
| `main/window.py` | 메인 윈도우 composition root |
| `main/composition/` | 서비스 생성, 액션 바인딩, 레이아웃 조립 |
| `main/actions/` | preview/batch/input/watch/tools/settings/lifecycle 계층 |
| `main/builders/` | menu/toolbar/central/statusbar/fab 빌더 |
| `main/services/` | runtime flow/message helper 계층 |
| `main/management_runtime.py` | 관리탭 signal/runtime 연결 |
| `main/translation.py` | 메인 윈도우 런타임 번역 갱신 |
| `widgets/settings/` | 설정 패널 facade + 탭/검증/i18n helper 구현 |
| `widgets/management/` | Library/Review/Duplicates/Jobs/Collections/Recipes/Settings 페이지와 library helper |
| `preview_widget.py` | 이미지 미리보기 위젯 |
| `toast_notification.py` | 토스트 알림 시스템 |

## 2026-04-19 Refactor Status

- 완료:
  - i18n manager가 Python locale catalog(`i18n/catalog/locales/*.py`)를 직접 로드
  - 장수명 UI용 runtime retranslate 경로와 `ui/main/services` 계층 추가
  - 분류 폴더명/prefix/suffix 공용 validator 도입
  - settings persistence/migration/validation 책임 분리
  - `ui/widgets/settings/panel.py`는 coordinator 역할만 남기고 탭 모듈로 분리
  - `core/image/processor.py`, `core/batch/processor.py`, `core/library/repository.py`는 파사드로 축소되고 실제 구현은 내부 모듈로 이동
  - `ui/widgets/management_pages.py`는 호환용 파사드로 축소되고 실제 구현은 `ui/widgets/management/` 패키지로 이동
- packaging note:
  - PyInstaller spec는 `photo_cropper.i18n.catalog.locales.*`와 분할된 패키지 하위 모듈을 안정적으로 포함해야 하므로 `collect_submodules(...)` 기반 자동 수집을 유지해야 함

## 2026-04-30 Stability Completion Status

- `utils.image_io.load_image_unicode()`가 core/UI 이미지 로딩 기준 API입니다.
- `ui/widgets/settings/i18n_bindings.py`는 기존 settings tab 리터럴을 locale key에 연결하고, selftest가 key coverage와 placeholder 일치를 검증합니다.
- CLI는 병합된 settings에 `validate_settings()`를 적용해 잘못된 naming/category path segment를 exit code `2`로 차단합니다.
- Scheduler callback 결과는 `ScheduleRunStatus`로 정규화되며, stored task input/output 경로를 실행 기준으로 사용합니다.
- PyInstaller spec는 `utils.image_io`, `ui.widgets.settings.i18n_bindings`, split package submodules를 frozen build에 포함해야 합니다.
- 2026-04-14/2026-04-19 standalone refactor snapshot docs are intentionally deleted; this guide plus README/CLAUDE are the current references.

## 2026-05-11 Global Code-Splitting Status

- `selftest.py` is a compatibility runner; the actual registry and test bodies live under `selftests/`.
- `cli.py`, `core/folder_watcher.py`, and `core/advanced/processor.py` remain public facades while implementation moved into `cli_support`, `core/file_watch`, and `core/advanced/ops_*`.
- `ui/main/window.py` now delegates service creation/action binding/layout assembly to `ui/main/composition/`; management runtime and translation refresh live in dedicated modules.
- `SettingsPanel` and `LibraryPage` keep their public import paths while helper responsibilities moved into settings panel helper modules and `widgets/management/library/`.
- PyInstaller specs collect `cli_support` plus the split core/UI packages with `collect_submodules(...)`; selftests are source validation modules, not frozen GUI runtime dependencies.

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
    model: str = "basic"   # basic | advanced (legacy custom aliases to advanced)
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
   from photo_cropper.utils.image_io import load_image_unicode

   img = load_image_unicode(path)
   # 피해야 할 방법
   img = cv2.imread(path)  # 한글 경로 오류
   ```
   - core/UI/워터마크 이미지 로딩은 같은 helper를 사용해야 합니다.

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
# → dist/PhotoCropper_v9/PhotoCropper_v9.exe

# 실험용 단일 파일 빌드
pyinstaller photo_cropper_onefile.spec --clean
# → dist/PhotoCropper_v9_single.exe
```

## Troubleshooting

| 문제 | 해결 |
|------|------|
| 한글 경로 오류 | `utils.image_io.load_image_unicode()` 사용 |
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
- Updated `QWidget` override event signatures to match PyQt6 stub event types and parameter names (`a0`), and promoted required window timers to non-optional services.
- Added explicit PyInstaller hidden imports for split modules:
  `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`.

## 2026-03-16 Consistency Check Notes

- Added repository-root `pyrightconfig.json` and `.editorconfig` so root/app workflows now share the same type-check and UTF-8 text rules.
- Verified `python -m photo_cropper.selftest` with `SELFTEST OK`.
- Added stage-specific candidate filters in `core/image/processor.py` to reduce no-photo false positives in `accurate` mode.
- Normalized quad point ordering in `core/multi_photo_detector.py::_quad_dimensions()` before perspective-crop dimension calculation.
- Added `ui.main.preview_worker` to `photo_cropper.spec` hidden imports; no extra runtime third-party dependencies were introduced.

## 2026-03-25 Stabilization Notes

- Manual contour preview and save now share `core.manual_extract.crop_manual_contour()`, so `perspective_correct=False` produces the same axis-aligned crop in both paths.
- `ui/widgets/preview_widget.py` redraw logic now has separate seed-point and 4-point contour branches, removing the previous `UnboundLocalError` and partial seed-guide rendering bug.
- `WatchModeCoordinator.start()` rejects recursive watch when output is inside input, and direct UI starts now enforce watch/batch/manual mutual exclusion.
- Watch-mode processing snapshots settings and forces `file_management.move_failed_files=False`; global settings remain unchanged.
- `FolderWatcher.fileChanged` is now part of the reprocessing path, but duplicate events are suppressed unless the file signature changed.
- `ProcessedIndexStore` moved to schema v2 with backward-compatible `status` handling for legacy records and partial-result records.
- `retry_failed_files()` now normalizes an empty output path to `<input>/output_cropped` before validation, matching normal batch start.

## 2026-04-06 Implementation Alignment Notes

- Recursive batch/watch/CLI now share a single output-inside-input safety rule plus recursive scan exclusion for `output_root`, `_failed`, `backup`, and `.photocropper`.
- Recursive output routing preserves input-relative paths for final outputs, failed-file storage, and multi-photo `*_photos` directories.
- `BatchProgress.partial_success` is now explicit, GUI/CLI summaries are aligned, and CLI gained `--strict-partial`.
- Classification model `custom` remains only as a deprecated compatibility alias of `advanced`; the settings UI now offers only `basic` and `advanced`.
- Scheduler `once` wording is clarified as "next upcoming HH:MM one-shot" with no date field.

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
