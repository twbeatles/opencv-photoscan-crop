# CLAUDE.md - Photo Cropper v9.0 Project Guide

## 프로젝트 개요

스캔된 사진 또는 배경 위에 놓인 사진을 자동으로 감지해 크롭하고 후처리하는 Python 애플리케이션입니다.

- **진입점**: `run.py`, `photo_cropper/main.py`
- **Python**: 3.8+
- **프레임워크**: PyQt6(GUI), OpenCV(이미지 처리)

## 의존성 요약

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

### 1) ImageProcessor (`core/image/processor.py`)

사진 경계 감지와 크롭을 담당합니다.

- `process_image(image_path) -> CropResult`
- `process_preview(image_path, ...)`
- `load_image`, `rotate_image`, `detect_edges_multiscale`, `find_best_contour`

### 2) BatchProcessor (`core/batch/processor.py`)

대량 이미지 처리 엔진입니다.

- `start_async(input_path, output_path, files)`
- `process_single(input_path, output_dir, input_root=None, *, clear_stop_event=True)` (Watch Mode/수동 추출에서 재사용)
- `apply_post_pipeline`, `build_output_path`, `find_existing_output`
- `lookup_processed_outputs_from_index`, `record_processed_outputs` (`skip_processed` 로컬 인덱스)
- `BatchProgress.partial_success`로 full success와 partial success를 분리 집계
- `BatchProgress.fatal_error/fatal_message`로 batch-level runtime failure를 CLI exit code `1` 및 Job `failed`와 동기화

### 2-1) Library / Jobs / Recipes

관리앱 계층은 아래 서비스 조합을 기준으로 봅니다.

- `LibraryRepository` (`core/library/repository.py`): SQLite 카탈로그 저장소 파사드
- `LibraryIngestService` / `QueryService` / `ReviewService` / `DuplicateService`
- `JobOrchestrator` (`core/jobs/orchestrator.py`): GUI/CLI/Watch/수동/maintenance 작업 기록과 실행 경로 통합
- `RecipeManager` (`core/recipes/manager.py`): preset/profile/recipe 호환 저장소

### 3) MainWindow (`ui/main/window.py`)

UI composition root입니다.

- `window.py`는 객체 생성, signal wiring, Qt 이벤트 위임만 담당합니다.
- 실제 동작은 `ui/main/actions/` 하위 클래스로 분리되었습니다.
- 위젯 생성은 `ui/main/builders/` 하위 함수로 분리되었습니다.
- 서비스 생성, 액션 바인딩, 메인 레이아웃 조립은 `ui/main/composition/`에 모였습니다.
- 관리탭 런타임 연결과 번역 갱신은 각각 `ui/main/management_runtime.py`, `ui/main/translation.py`가 담당합니다.
- 기존 `batch_actions.py` 등 평면 모듈은 호환용 shim으로 유지됩니다.

### 4) Settings (`core/settings_model/app_settings.py`)

설정을 dataclass로 관리합니다.

- `AlgorithmSettings`, `ProcessingSettings`, `OutputSettings`
- `AdvancedProcessingSettings`, `PerformanceSettings`
- `WatermarkSettings`, `ResizeSettings`, `WatchModeSettings`, `MultiPhotoSettings`
- `ClassificationSettings`, `FaceDetectionSettings`, `SmartEnhancementSettings`
- 루트: `AppSettings`
- persistence/마이그레이션/실행 전 검증은 각각 `manager.py`, `migration.py`, `validation.py`로 분리되었습니다.

## 주요 처리 흐름

1. **단일 미리보기**
   - `Input/Toolbar/Menu` -> `PreviewActions.request_preview()` -> `PreviewWorker.process_preview()` -> UI 반영

2. **배치 처리**
   - `Toolbar/FAB/Menu` -> `BatchActions.start_processing()` -> `BatchProcessor.start_async()`

3. **Watch Mode**
   - `WatchActions.start_watch_mode()` -> `WatchModeCoordinator.start()` -> `AutoProcessor` -> `BatchProcessor.process_single()`

4. **설정 저장/로드**
   - `SettingsManager.load()` / `SettingsManager.save()`
   - Windows: `%APPDATA%/PhotoCropper/settings.json`
   - macOS/Linux: `~/.photo_cropper/photo_cropper_settings.json`

5. **스케줄러 자동 배치**
   - `WatchActions.reconfigure_scheduler()`에서 `watch_mode.scheduler_*`를 런타임 스케줄에 반영
   - 앱 실행 중 예약 시각 도달 시 저장된 ScheduleTask input/output 경로로 전체 배치 트리거
   - 배치/수동/워치 실행 중에는 스케줄 트리거를 skip 처리
   - `schedule_type=once`는 날짜 없는 "다음 도래 HH:MM 1회 실행" 의미이며, busy/no files/invalid config skip은 예약을 소비하지 않음

## 코딩 가이드라인

### 이미지 I/O

- 유니코드 경로는 `utils.image_io.load_image_unicode()` 사용
- `cv2.imread` 직접 호출은 한글 경로에서 실패 가능
- worker thread에서는 `QPixmap`을 만들지 말고 `QImage`/bytes를 emit한 뒤 GUI thread에서 변환
- frozen build에서는 `photo_cropper.utils.image_io`, `photo_cropper.ui.widgets.settings.i18n_bindings`, `winotify`(Windows toast, importlib 로드) hidden import를 유지
- `cli.py`는 `cli_support.runtime` 호환 래퍼이므로 PyInstaller split package 수집 목록에 `photo_cropper.cli_support`를 유지

### 처리 파이프라인

- 후처리 순서: 얼굴 보정 -> 스마트 보정 -> 리사이즈 -> 분류 라우팅 -> 워터마크
- Watch/Batch/수동 추출 경로가 동일 규칙을 사용해야 함
- 재귀 Batch/Watch/CLI는 output path를 input root 내부에 둘 수 없음
- 재귀 입력은 `output_root`, `_failed`, `backup`, `.photocropper`를 입력 스캔에서 제외
- 재귀 출력/실패 보관/멀티포토 저장은 입력 기준 상대 경로를 보존
- `skip_processed`는 `.photocropper/processed_index.json` 인덱스 우선, 실패 시 파일명 기반 fallback
- `skip_processed` pipeline signature에는 언어별 분류 폴더 해석값과 `create_backup`이 포함됨
- processed index v2는 레코드별 `status=success|partial`를 저장하며, `partial`은 skip 대신 경고 후 재처리
- CLI는 summary에 `processed/success/partial_success/failed/skipped`를 항상 출력하고, `--strict-partial` 사용 시 partial도 종료코드 `1` 대상
- CLI는 `fatal_error=True`인 batch-level 오류를 cancel/partial보다 우선해 종료코드 `1`로 반환해야 함
- 분류 모델 `custom`은 legacy alias로만 유지되며 내부적으로 `advanced`로 정규화
- scheduler `once`는 날짜 없는 "다음 도래 HH:MM 1회 실행" 의미
- `ScheduleRunStatus.STARTED`일 때만 `once` 작업을 소비하고, busy/no-work/config 실패는 `next_run`을 다음 날로 밀지 않고 다음 tick에서 재시도
- 명시 파일 목록 기반 batch/rerun/reprocess는 누락 파일이 하나라도 있으면 전체 시작을 차단하고 `ResolvedIoPaths.files`만 실행에 넘겨야 함
- Management maintenance rerun은 queued batch job을 만들지 않고 maintenance 실행 spec만 반환해야 함
- Batch/management job finalization은 UI thread를 블로킹하지 않도록 background thread 또는 maintenance signal 경로를 사용해야 함
- 수동 contour preview도 `core.manual_extract.crop_manual_contour()`를 통해 실제 저장과 동일한 crop 규칙을 사용

### 성능/안정성

- 대용량 파일 제한: `performance.max_image_size_mb`
- DNN 얼굴 감지 실패 시 Haar 즉시 폴백
- 멀티스레드 취소 시 완료 future drain + 미실행 작업 `CANCELLED` 통계 반영
- 재귀 Watch Mode는 output path가 input root 내부면 시작을 차단
- Watch 처리 경로는 settings snapshot에서 `move_failed_files=False`를 강제해 `_failed` 루프를 막음
- Watch callback에서 `process_single(..., clear_stop_event=False)`를 사용해 stop 요청을 지우지 말아야 함
- `FolderWatcher.fileChanged`는 overwrite된 동일 경로도 size/mtime signature가 바뀐 경우에만 재큐잉
- UI 직접 실행 경로에서도 watch/batch/manual 상호 배제를 강제
- GUI 입력 검증과 batch/watch/manual preflight는 모두 `utils.path_validation` + `core.settings_model.validation`의 공용 API를 사용
- CLI도 병합된 config/preset/override 설정에 `validate_settings()`를 적용하고 invalid path segment는 exit code `2`로 차단
- `file_management.failed_folder_name`은 category folder/prefix/suffix와 같은 single segment validator를 적용하며, invalid 값은 `_failed` fallback으로 묵살하지 말고 명시 실패로 처리
- 분류 폴더 빈 문자열은 "현재 UI 언어 기본값 사용" sentinel 의미이며, 구 기본 한글값은 마이그레이션 시 sentinel로 정규화
- Batch 출력 경로는 일반/분류/멀티포토 모두 per-run thread-safe reservation을 거쳐 동시 저장 충돌을 방지
- Library SQLite 연결은 `foreign_keys=ON`, WAL, busy timeout을 설정하고, 폴더 import는 UI thread 밖에서 실행
- Undo/Redo는 세션 내 설정 변경, 수동 crop, 라이브러리/컬렉션/레시피 수동 변경을 대상으로 하며 Batch/Watch 산출물 rollback은 제외

## 빌드

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
```

출력 예:
- 안정 onedir: `dist/PhotoCropper_v9/PhotoCropper_v9.exe`
- 실험 onefile: `dist/PhotoCropper_v9_single.exe`

## 트러블슈팅

### 한글 경로 관련 오류

- `cv2.imread` 대신 `utils.image_io.load_image_unicode()` 사용

### Watch/Batch 결과 불일치

- Watch Mode가 반드시 `BatchProcessor.process_single()` 경로를 타는지 확인

### 중단 응답 지연

- 현재 구현은 취소 시 in-flight future 결과를 drain하고, 남은 미실행 항목은 `CANCELLED`로 집계함
- 여전히 실제 실행 중인 외부 I/O는 즉시 중단되지 않을 수 있으므로 thread count/입력 크기 점검

## 2026-03-01 Agent Update

- CLI 병합 규칙 명시: defaults -> preset -> config -> cli override
- 유효 우선순위: CLI > config > preset
- `--preset`, `--config` 동시 사용 가능
- 레거시 키(`advanced_processing`) 읽기 호환 유지, 저장 키는 `advanced`로 정규화
- Watch telemetry 신호:
  - `processing_completed_detailed(filepath, success, status, message, wait_ms)`
  - `queue_metrics_updated(queue_size, avg_wait_ms)`
- 재귀 감시 시 신규 하위 디렉터리의 초기 이미지 즉시 스캔
- `watch_mode.max_wait_seconds`로 timeout 제어(기본 30.0)
- callback result parser는 `bool`, `tuple`, `dict`, object-like 반환을 허용

## 2026-03-02 Split Refactor Notes

- 모듈 분리:
  - `core/settings_model`, `core/advanced`, `core/face`, `core/image`, `core/batch`
  - `ui/main`, `ui/widgets/settings`, `i18n/catalog`
- 패키징/내부 import를 새 구조에 맞게 정리
- 런타임 동작 목표: 기존 CLI/설정/출력 규칙/Watch-Batch 계약 유지

## 2026-03-03 Manual Boundary Workflow Notes

- 메인 윈도우에 폴더 일괄 편집 컨트롤 추가
- 경계 검출 실패 파일만 모아 수동 보정하는 흐름 추가
- Preview에서 핸들 드래그 및 4점 직접 입력 지원
- 수동 추출 취소 시 UI 스레드를 블로킹하지 않도록 개선

## 2026-03-04 Consistency Check Notes

- `pyright --project pyrightconfig.json`: 0 errors / 0 warnings
- QWidget 이벤트 오버라이드 시그니처를 PyQt6 스텁 기준 이벤트 타입 + 파라미터명(`a0`)까지 정렬하고, 필수 window timer service를 non-optional로 승격
- `photo_cropper.spec` hidden imports에 `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`를 명시

## 2026-03-16 Consistency Check Notes

- 저장소 루트 `pyrightconfig.json`과 `.editorconfig`를 추가해 루트/앱 폴더 워크플로의 타입 검사/UTF-8 규칙을 정렬
- `python -m photo_cropper.selftest`: `SELFTEST OK`
- `core/image/processor.py`에 stage-specific candidate filter를 추가해 accurate 모드 no-photo false positive 회귀를 완화
- `core/multi_photo_detector.py::_quad_dimensions()`는 quad point order를 정규화한 뒤 perspective crop 크기를 계산
- `photo_cropper.spec` hidden imports에 `ui.main.preview_worker`를 추가했고, 이번 변경으로 새로운 런타임 외부 의존성은 없음

## 2026-03-05 Integrated Improvement Notes

- `skip_processed` 로직을 출력 폴더 로컬 인덱스(`.photocropper/processed_index.json`) 기반으로 강화
- 분류 폴더명 매핑(`ClassificationSettings.category_folders`) 추가 및 설정 패널 노출
- Watch 재시도 정책 개선: stat/read 실패 만료 처리, 공정 큐 재시도, retry_count 로그
- 스케줄러 UI 설정과 런타임 자동 배치 트리거 연결
- Watch 완료 알림은 `processing_completed_detailed` 중심으로 사용자 토스트 중복 제거
- CLI 취소 종료코드 표준화: cancel `130`, failed `1`, success `0`
- 프로파일 적용 경로를 `to_dict + deep-merge + AppSettings.from_dict`로 일원화

## 2026-03-08 Precision Update Notes

- Implemented all 10 precision recommendations from the 2026-03-08 review plan.
- Detection core:
  - `accurate` mode now aggregates Stage 1~6 candidates and globally re-ranks.
  - `fast`/`balanced` retain early-exit behavior.
  - Edge-support scoring now uses a dedicated reference edge map.
  - Area/aspect/Hough scoring logic was upgraded for rotated/skewed cases.
- Multi-photo:
  - Added `DetectedPhoto.quad`.
  - Crop path is perspective-first (`warpPerspective`) with bbox fallback.
  - `merge_distance` now affects dedup (`IoU + center distance + edge gap`).
- EXIF / face:
  - EXIF orientation normalization added on image load (`ImageOps.exif_transpose` when available).
  - Face auto-rotation angle now uses `primary_face`.
- UI/CLI:
  - Added precision tuning controls/options:
    - `min_area_ratio`, `max_area_ratio`
    - `bg_mask_delta`
    - `adaptive_block_size`, `adaptive_c`
- Benchmark:
  - Added executable harness: `python -m photo_cropper.benchmark`
  - Added label format doc/template:
    - `BENCHMARK_LABEL_FORMAT.md`
    - `benchmark/labels.template.json`
  - Real-image benchmark datasets are intentionally excluded from the repository.

## 2026-03-14 Implementation Update

- Watch Mode processing now runs through a sequential background worker in `AutoProcessor`, and file readiness retry/timeout ownership also lives in `AutoProcessor` instead of `FolderWatcher`.
- Watch callbacks treat `partial_success` as success-like for the boolean completion signal, while `processing_completed_detailed` keeps the explicit `partial_success` status.
- Metadata preservation keeps EXIF/ICC on a best-effort basis and always rewrites EXIF Orientation to `1` after normalized save.
- Multi-photo input loading now reuses `ImageProcessor.load_image()` so EXIF orientation normalization matches single-photo and manual paths.
- Multi-photo runs can return `ProcessStatus.PARTIAL_SUCCESS`; batch/watch summaries and processing logs expose that status separately.
- `BatchSessionService.create_processor()` now rejects replacement of a running processor so UI batch actions cannot silently start overlapping sessions.

## 2026-03-25 Stabilization Update

- Manual contour preview now shares `core.manual_extract.crop_manual_contour()` with save, so `perspective_correct=False` yields the same axis-aligned crop in preview and output.
- `ui/widgets/preview_widget.py` redraw logic now cleanly separates seed points (1-3) from valid contours (4), eliminating the previous `UnboundLocalError` path.
- `WatchModeCoordinator.start()` now rejects recursive watch when output is inside input, and `WatchActions` / `BatchActions` block direct starts while watch/batch/manual work is already active.
- Watch-mode processing uses an `AppSettings` snapshot with `file_management.move_failed_files=False`, preventing `_failed` subtree feedback loops without mutating the global settings object.
- `FolderWatcher.fileChanged` now participates in reprocessing, but only queues when the file's size/mtime signature actually changed.

## 2026-04-19 Refactor Status

- 완료:
  - `ui/widgets/settings/panel.py`는 coordinator 역할만 남기고 `tab_basic.py`, `tab_algorithm.py`, `tab_processing.py`, `tab_management.py`, `tab_ai.py`, `controls.py`로 분리
  - `ui/widgets/management_pages.py`는 호환용 파사드로 축소되고 실제 구현은 `ui/widgets/management/` 패키지로 이동
  - `core/batch/processor.py`, `core/image/processor.py`, `core/library/repository.py`는 파사드로 축소되고 내부 구현은 세부 모듈로 이동
  - `core/batch/single.py`, `core/image/detect.py`, `core/library/_repository_assets.py`도 추가 분할
  - 관리앱 계층(`core/library`, `core/jobs`, `core/recipes`)과 관리 셸 UI가 기본 구조로 자리잡음
- 패키징 주의:
  - frozen build에서는 locale 패키지와 분할된 하위 모듈들을 안정적으로 포함해야 하므로 `photo_cropper.spec`/`photo_cropper_onefile.spec`는 `collect_submodules(...)` 기반 자동 수집을 사용
  - 기본 배포 타깃은 `photo_cropper.spec` onedir 빌드이며, `photo_cropper_onefile.spec`는 실험용으로 유지
- 검증 기준:
  - `python -m compileall -q photo_cropper`
  - `python -m photo_cropper.selftest`
  - `pyright --project pyrightconfig.json`

## 2026-04-30 안정화 완료 상태

- `utils.image_io.load_image_unicode()`가 core/UI 이미지 로딩 기준 API입니다.
- settings tab의 남은 legacy 표시 문자열은 `ui/widgets/settings/i18n_bindings.py`를 통해 locale key에 바인딩됩니다.
- CLI invalid config는 병합 후 `validate_settings()`에서 차단하며 exit code `2`를 반환해야 합니다.
- Scheduler callback 결과는 `ScheduleRunStatus`로 정규화되고 `once`는 실제 `STARTED`일 때만 소비됩니다.
- 2026-04-14/2026-04-19 standalone refactor snapshot 문서는 삭제 상태를 반영하고, README/GEMINI/CLAUDE가 최신 기준 문서입니다.

## 2026-05-11 전역 코드 분할 상태

- `selftest.py`는 실행 호환 래퍼이며 실제 suite registry는 `selftests/runner.py`와 책임별 selftests 모듈에 있습니다.
- `cli.py`, `core/folder_watcher.py`, `core/advanced/processor.py`는 public import 호환을 유지하는 facade이고 실제 구현은 `cli_support`, `core/file_watch`, `core/advanced/ops_*`로 분리되었습니다.
- `ui/widgets/settings/panel.py`와 `ui/widgets/management/library_page.py`는 public widget facade를 유지하고 설정 빌드/검증/i18n 및 library layout 세부 동작은 helper 패키지로 이동했습니다.
- `photo_cropper.spec`와 `photo_cropper_onefile.spec`는 `cli_support`, file-watch, advanced, settings, management, main composition split packages를 `collect_submodules(...)` 기반으로 수집합니다.

## 2026-06-29 Agent Automation Hardening

- App root directory is `opencv/` (renamed from `;opencv/`).
- Unified verify: repository root `scripts/verify.ps1` / `scripts/verify.sh`.
- Selftest runner prints `RUN <name>`, supports filter args, and reports failing test names.
- Pytest: `tests/test_path_validation.py` (unit) and `tests/test_selftest_registry.py` (`-m selftest`).
- Test isolation: `PHOTOCROPPER_LIBRARY_DB`, `PHOTOCROPPER_OFFLINE=1`, `core/test_reset.py` singleton resets.
- CLI cancel exit policy: `cancelled` returns `130` even when `failed>0` (documented in README).

## 2026-06-04 안정성 하드닝 상태

- `BatchProgress.fatal_error/fatal_message`는 output directory creation, file discovery, outer batch exception 같은 batch-level failure를 표현하는 공용 계약입니다. CLI는 summary 출력 후 exit code `1`, `JobOrchestrator.finalize_job()`는 `failed`를 최우선으로 반영합니다.
- `file_management.failed_folder_name`은 설정 검증과 `classify_failed_files()` 진입부에서 모두 `validate_single_path_segment(..., allow_empty=False)`로 검증합니다. invalid 값은 경로 fallback으로 보정하지 않습니다.
- `BatchRuntimeFlow.resolve_file_batch_paths()`는 mixed valid/missing file list를 전체 차단하고, caller는 원본 files가 아니라 `ResolvedIoPaths.files`만 `BatchProcessor.start_async()`에 전달해야 합니다.
- `JobOrchestrator.prepare_job_rerun()`은 source path를 순서 보존 dedupe하고, source 없는 maintenance job은 queued batch job 없이 maintenance spec만 반환합니다.
- Watch Mode는 `BatchProcessor.process_single(..., clear_stop_event=False)`를 호출해 stop 이후 queued callback이 stop event를 지우지 않도록 합니다.
- `BatchActions.on_batch_complete()`는 tracked job finalization을 background thread로 넘기고, `management_task_finished` signal 패턴으로 management refresh/toast를 처리합니다. 수동 추출 상태 해제도 UI completion path에서만 수행합니다.
- Scheduler `once`는 `STARTED`가 아닌 busy/no-files/config skip에서 `_calculate_next_run()`을 호출하지 않으며 다음 scheduler tick에서 재시도합니다.
- `.codegraph/`는 로컬 CodeGraph MCP 인덱스라 커밋하지 않고 `.gitignore`로 제외합니다.

## 2026-04-06 Implementation Alignment Update

- Recursive batch/watch/CLI now share the same output-inside-input guard and recursive scan exclusion rules (`output_root`, `_failed`, `backup`, `.photocropper`).
- Recursive outputs, failed-file routing, and multi-photo `*_photos` layouts now preserve the input-relative directory tree.
- `BatchProgress.partial_success` is now a first-class counter; GUI/CLI summaries use aligned semantics, and CLI gained `--strict-partial`.
- Legacy classification model `custom` is normalized to the `advanced` alias, while the settings UI only exposes `basic` and `advanced`.
- Scheduler `once` is documented/UI-labeled as "next upcoming HH:MM one-shot" rather than a date-based reservation.

## 2026-04-27 Management/Library Stabilization Update

- `BatchRuntimeFlow.resolve_file_batch_paths(...)` is the shared file-list preflight entry point for Management rerun/reprocess, Batch, and Watch-style flows. Use it before queueing tracked rerun jobs so output-inside-input, empty output defaults, and missing files fail consistently.
- Management maintenance work should run through `JobOrchestrator.run_maintenance_job(...)`. Current maintenance kinds include `maintenance_library_import`, `maintenance_exact_duplicates`, `maintenance_near_duplicates`, and `maintenance_search_index`.
- Library import and duplicate rebuild UI buttons emit management requests and rely on background worker completion signals, toast reporting, and current-page refresh. Avoid adding long-running direct calls in widget event handlers.
- `LibrarySqliteStore.connect()` applies `PRAGMA foreign_keys=ON` and `PRAGMA busy_timeout=5000` for every connection. Initialization attempts `PRAGMA journal_mode=WAL` best-effort, and write paths should use `store.write_connect()`.
- `LibraryRepository.upsert_source()` is non-throwing for invalid source inputs. Empty paths, missing files, directories, unsupported extensions, and unreadable image files return `ingest_state="invalid_source"` plus an `error` string without creating assets.
- FTS refresh failure must mark `app_state.search_index_dirty=1`; full recovery is exposed through `maintenance_search_index`.
- Job summaries now preserve observability fields for provider failures: `metadata_warnings`, `ai_errors`, `thumbnail_failed_count`, and near-duplicate scan scope fields such as `scanned_assets`, `limited`, and `limit`.
- Timeline queries for a single asset should use repository asset-specific SQL (`list_review_items_for_asset`) instead of broad review-window scans.
- Repository mixins use `core/library/_repository_protocol.py` for shared typing contracts. Keep pyright suppressions narrow and line-local when they are genuinely unavoidable.
- Packaging check: both `photo_cropper.spec` and `photo_cropper_onefile.spec` explicitly list `photo_cropper.core.library._repository_protocol` in addition to `collect_submodules(...)`; no new external packaging dependency was introduced.
- Validation baseline for this update:
  - `python -m compileall -q photo_cropper`
  - `pyright --project pyrightconfig.json`
  - `python -m photo_cropper.selftest`
