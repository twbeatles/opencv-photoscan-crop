# CLAUDE.md — Photo Cropper Project Guide

## 프로젝트 개요

스캔된 사진 또는 배경 위에 놓인 사진을 자동으로 감지해 크롭하고 후처리하는 Python 애플리케이션입니다.

- **진입점**: `run.py`, `photo_cropper/main.py`
- **Python**: 3.8+
- **프레임워크**: PyQt6 (GUI), OpenCV (이미지 처리)

## 의존성

```txt
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
PyQt6>=6.5.0
winotify>=1.1.0  # Windows 알림(선택)
```

## 프로젝트 구조

```txt
photo_cropper/
├── main.py
├── cli.py
├── cli_support/
├── selftest.py
├── selftests/
├── core/
│   ├── advanced/
│   ├── app_paths.py
│   ├── image/
│   ├── batch/
│   ├── file_watch/
│   ├── jobs/
│   ├── library/
│   ├── recipes/
│   ├── settings_model/
│   ├── multi_photo_detector.py
│   ├── watermark_processor.py
│   ├── resize_processor.py
│   ├── folder_watcher.py   # compatibility re-export for core.file_watch
│   ├── scheduler.py
│   ├── processed_index.py
│   └── history_manager.py
├── ui/
│   ├── main/                # composition root + composition/actions/builders/services
│   ├── styles/
│   └── widgets/
│       ├── management/
│       └── settings/
├── i18n/
│   └── catalog/
│       └── locales/*.py
└── utils/
    ├── image_io.py
    └── path_validation.py
```

## 핵심 클래스/역할

### ImageProcessor (`core/image/processor.py`)

사진 경계 감지와 크롭을 담당합니다.

- `process_image(image_path) -> CropResult`
- `process_preview(image_path, ...)`
- `load_image`, `rotate_image`, `detect_edges_multiscale`, `find_best_contour`

### BatchProcessor (`core/batch/processor.py`)

대량 이미지 처리 엔진입니다.

- `start_async(input_path, output_path, files)`
- `process_single(input_path, output_dir, input_root=None, *, clear_stop_event=True)` — Watch Mode / 수동 추출에서 재사용
- `apply_post_pipeline`, `build_output_path`, `find_existing_output`
- `BatchProgress.partial_success` — full success와 partial을 분리 집계
- `BatchProgress.fatal_error/fatal_message` — batch-level runtime failure → CLI exit code `1` + Job `failed`

### Library / Jobs / Recipes

- `LibraryRepository` (`core/library/repository.py`): SQLite 카탈로그 저장소 파사드
- `LibraryIngestService` / `QueryService` / `ReviewService` / `DuplicateService`
- `JobOrchestrator` (`core/jobs/orchestrator.py`): 작업 기록과 실행 경로 통합
- `RecipeManager` (`core/recipes/manager.py`): preset/profile/recipe 저장소

### MainWindow (`ui/main/window.py`)

UI composition root입니다.

- `window.py`는 객체 생성, signal wiring, Qt 이벤트 위임만 담당
- 실제 동작: `ui/main/actions/`
- 위젯 생성: `ui/main/builders/`
- 서비스/레이아웃 조립: `ui/main/composition/`

### Settings (`core/settings_model/app_settings.py`)

설정을 dataclass로 관리합니다.

- `AlgorithmSettings`, `ProcessingSettings`, `OutputSettings`
- `AdvancedProcessingSettings`, `PerformanceSettings`
- `WatermarkSettings`, `ResizeSettings`, `WatchModeSettings`, `MultiPhotoSettings`
- `ClassificationSettings`, `FaceDetectionSettings`, `SmartEnhancementSettings`
- persistence / 마이그레이션 / 검증: `manager.py`, `migration.py`, `validation.py`

## 주요 처리 흐름

1. **단일 미리보기**: `PreviewActions.request_preview()` → `PreviewWorker.process_preview()` → UI 반영
2. **배치 처리**: `BatchActions.start_processing()` → `BatchProcessor.start_async()`
3. **Watch Mode**: `WatchModeCoordinator.start()` → `AutoProcessor` → `BatchProcessor.process_single()`
4. **스케줄러**: `watch_mode.scheduler_*` 설정 → 예약 시각에 배치 트리거

## 코딩 가이드라인

### 이미지 I/O

- 유니코드 경로는 `utils.image_io.load_image_unicode()` 사용 (`cv2.imread` 직접 호출 금지)
- worker thread에서는 `QPixmap` 생성 금지 — `QImage`/bytes를 emit한 뒤 GUI thread에서 변환
- frozen build: `photo_cropper.utils.image_io`와 `photo_cropper.ui.widgets.settings.i18n_bindings` hidden import 유지

### 처리 파이프라인

- 후처리 순서 고정: 얼굴 보정 → 스마트 보정 → 리사이즈 → 분류 라우팅 → 워터마크
- Watch / Batch / 수동 추출 경로가 동일 규칙을 사용
- 재귀 Batch/Watch/CLI: output path를 input root 내부에 둘 수 없음
- 재귀 스캔 제외 폴더: `output_root`, `_failed`, `backup`, `.photocropper`
- 재귀 출력/실패 보관/멀티포토 저장은 입력 기준 상대 경로 보존
- `skip_processed`: `.photocropper/processed_index.json` 인덱스 우선, 실패 시 파일명 기반 fallback
  - index signature = `source_path + size + mtime_ns + pipeline_signature` (언어별 분류 폴더명 + backup 옵션 포함)
  - `partial` 레코드: skip하지 않고 경고 후 재처리
- CLI summary: 항상 `processed/success/partial_success/failed/skipped` 출력
- `--strict-partial`: partial만 있어도 exit code `1`
- fatal error (`fatal_error=True`): cancel/partial보다 우선해 exit code `1`
- 분류 모델 `custom`: legacy alias, 내부적으로 `advanced`로 정규화
- Scheduler `once`: "다음 도래 HH:MM 1회 실행" — `STARTED`일 때만 소비
- 명시 파일 목록 preflight: 누락 파일이 하나라도 있으면 전체 차단
- Maintenance rerun: queued batch job 없이 maintenance spec만 반환
- `file_management.failed_folder_name`: single path segment 검증 필수

### 성능/안정성

- 대용량 파일 제한: `performance.max_image_size_mb`
- DNN 얼굴 감지 실패 시 Haar 즉시 폴백
- 멀티스레드 취소: 완료 future drain + 미실행 작업 `CANCELLED` 반영
- Watch callback: `process_single(..., clear_stop_event=False)` — stop 요청 유지
- `FolderWatcher.fileChanged`: size/mtime signature가 바뀐 경우에만 재큐잉
- Watch 처리: settings snapshot에서 `move_failed_files=False` 강제
- GUI/batch/manual preflight: `utils.path_validation` + `core.settings_model.validation` 공용 API 사용
- CLI: 병합된 config/preset/override에 `validate_settings()` 적용 — invalid path segment → exit code `2`
- 출력 경로: 일반/분류/멀티포토 모두 per-run thread-safe reservation
- Library SQLite: `foreign_keys=ON`, WAL, busy timeout 5000ms
- Undo/Redo: 세션 내 설정 변경 / 수동 crop / 라이브러리·컬렉션·레시피 수동 변경 대상 (Batch/Watch 산출물 제외)

## 검증 기준

```bash
cd ";opencv"
python -m compileall -q photo_cropper
python -m photo_cropper.selftest
pyright --project pyrightconfig.json
```

## 빌드

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
# → dist/PhotoCropper_v9/PhotoCropper_v9.exe
```

## 트러블슈팅

| 문제 | 해결 |
|------|------|
| 한글 경로 오류 | `utils.image_io.load_image_unicode()` 사용 |
| Watch/Batch 결과 불일치 | Watch Mode가 `BatchProcessor.process_single()` 경로를 타는지 확인 |
| 중단 응답 지연 | 취소 시 in-flight future drain + 미실행 항목 `CANCELLED` 집계 확인, thread count/입력 크기 점검 |
| 메모리 부족 | `max_image_size_mb` 조정 |
| 감지 실패 | `canny_min`/`canny_max` 조정, CLAHE 활성화, `accurate` 모드 시도 |
