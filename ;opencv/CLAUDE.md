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
├── core/
│   ├── image/processor.py
│   ├── batch/processor.py
│   ├── settings_model/app_settings.py
│   ├── multi_photo_detector.py
│   ├── watermark_processor.py
│   ├── resize_processor.py
│   ├── folder_watcher.py
│   ├── scheduler.py
│   └── history_manager.py
├── ui/
│   ├── main/window.py
│   ├── main/*.py            # actions/coordinator 분리
│   ├── styles/
│   └── widgets/
├── i18n/
│   └── catalog/
└── utils/
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
- `process_single(input_path, output_dir)` (Watch Mode에서 재사용)
- `apply_post_pipeline`, `build_output_path`, `find_existing_output`

### 3) MainWindow (`ui/main/window.py`)

UI 진입 오케스트레이터입니다.

- 파일/폴더 입력, 미리보기, 배치 처리 시작/중단
- 최근 리팩토링으로 액션 클래스로 분리:
  - `batch_actions.py`
  - `preview_actions.py`
  - `feature_actions.py`
  - `navigation_actions.py`
  - `dialog_actions.py`
  - `watch_mode`는 `core/watch_mode/coordinator.py`로 분리

### 4) Settings (`core/settings_model/app_settings.py`)

설정을 dataclass로 관리합니다.

- `AlgorithmSettings`, `ProcessingSettings`, `OutputSettings`
- `AdvancedProcessingSettings`, `PerformanceSettings`
- `WatermarkSettings`, `ResizeSettings`, `WatchModeSettings`, `MultiPhotoSettings`
- `ClassificationSettings`, `FaceDetectionSettings`, `SmartEnhancementSettings`
- 루트: `AppSettings`

## 주요 처리 흐름

1. **단일 미리보기**
   - `MainWindow._request_preview()` -> `PreviewWorker.process_preview()` -> UI 반영

2. **배치 처리**
   - `MainWindow._start_processing()` -> `BatchActions.start_processing()` -> `BatchProcessor.start_async()`

3. **Watch Mode**
   - `MainWindow._start_watch_mode()` -> `WatchModeCoordinator.start()` -> `AutoProcessor` -> `BatchProcessor.process_single()`

4. **설정 저장/로드**
   - `SettingsManager.load()` / `SettingsManager.save()`
   - Windows: `%APPDATA%/PhotoCropper/settings.json`
   - macOS/Linux: `~/.photo_cropper/photo_cropper_settings.json`

## 코딩 가이드라인

### 이미지 I/O

- 유니코드 경로는 `np.fromfile + cv2.imdecode` 패턴 사용
- `cv2.imread` 직접 호출은 한글 경로에서 실패 가능

### 처리 파이프라인

- 후처리 순서: 얼굴 보정 -> 스마트 보정 -> 리사이즈 -> 분류 라우팅 -> 워터마크
- Watch/Batch/수동 추출 경로가 동일 규칙을 사용해야 함

### 성능/안정성

- 대용량 파일 제한: `performance.max_image_size_mb`
- DNN 얼굴 감지 실패 시 Haar 즉시 폴백
- 멀티스레드 취소 시 pending 작업 우선 취소

## 빌드

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
```

출력 예: `dist/PhotoCropper_v9.exe`

## 트러블슈팅

### 한글 경로 관련 오류

- `cv2.imread` 대신 `np.fromfile + cv2.imdecode` 사용

### Watch/Batch 결과 불일치

- Watch Mode가 반드시 `BatchProcessor.process_single()` 경로를 타는지 확인

### 중단 응답 지연

- 멀티스레드 작업 중 일부 in-flight task는 완료 대기될 수 있음
- pending task 취소 설정 및 thread count 재점검

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
- QWidget 이벤트 오버라이드 타입 시그니처를 PyQt6 스텁 기준 `Optional[...]`로 정렬
- `photo_cropper.spec` hidden imports에 `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`를 명시
