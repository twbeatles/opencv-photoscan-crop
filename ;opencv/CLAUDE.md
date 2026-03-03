# CLAUDE.md - Photo Cropper v9.0 Project Guide

## ?꾨줈?앺듃 媛쒖슂

?ㅼ틪???ъ쭊 ?먮뒗 諛곌꼍 ???ъ쭊???먮룞 媛먯??섏뿬 ?щ∼?섎뒗 Python ?좏뵆由ъ??댁뀡?낅땲??

- **吏꾩엯??*: `run.py` ??`photo_cropper/main.py`
- **Python**: 3.8+
- **?꾨젅?꾩썙??*: PyQt6 (GUI), OpenCV (?대?吏 泥섎━)

## ?듭떖 ?섏〈??

```
opencv-python>=4.8.0  # ?대?吏 泥섎━
numpy>=1.24.0         # 諛곗뿴 ?곗궛
Pillow>=10.0.0        # ?대?吏 I/O
PyQt6>=6.5.0          # GUI
winotify>=1.1.0       # Windows ?뚮┝ (?좏깮)
```

## ?꾨줈?앺듃 援ъ“

```
photo_cropper/
?쒋?? main.py              # 吏꾩엯??
?쒋?? cli.py               # CLI ?명꽣?섏씠??
?쒋?? core/                # ?듭떖 ?대?吏 泥섎━
??  ?쒋?? image/processor.py      # 硫붿씤 ?щ∼ ?뚭퀬由ъ쬁
??  ?쒋?? batch/processor.py      # 諛곗튂 泥섎━
??  ?쒋?? settings_model/app_settings.py             # ?ㅼ젙 dataclass
??  ?쒋?? multi_photo_detector.py # ?ㅼ쨷 ?ъ쭊 媛먯?
??  ?쒋?? watermark_processor.py  # ?뚰꽣留덊겕
??  ?쒋?? resize_processor.py     # 由ъ궗?댁쫰
??  ?쒋?? folder_watcher.py       # ?대뜑 媛먯떆
??  ?쒋?? scheduler.py            # ?ㅼ?以꾨윭
??  ?붴?? history_manager.py      # Undo/Redo
?쒋?? ui/                  # PyQt6 UI
??  ?쒋?? main/window.py          # 硫붿씤 ?덈룄??
??  ?쒋?? styles/                 # ?뚮쭏 ?ㅽ??쇱떆??
??  ?붴?? widgets/                # UI ?꾩젽
??      ?쒋?? settings/panel.py
??      ?쒋?? preview_widget.py
??      ?쒋?? toast_notification.py
??      ?붴?? ...
?쒋?? utils/               # ?좏떥由ы떚
??  ?쒋?? file_helpers.py
??  ?쒋?? naming_rules.py
??  ?붴?? processing_log.py
?붴?? i18n/                # ?ㅺ뎅??吏??
    ?붴?? catalog/manager.py
```

## ?듭떖 ?대옒??諛?API

### 1. ImageProcessor (core/image/processor.py)

?ъ쭊 媛먯? 諛??щ∼???듭떖 濡쒖쭅 ?대떦.

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

**媛먯? ?뚭퀬由ъ쬁 ?④퀎**:
1. Multi-Scale Canny Edge Detection
2. Adaptive Threshold
3. Gradient Analysis (Sobel)
4. Harris Corner Detection (?좏깮??

### 2. MainWindow (ui/main/window.py)

硫붿씤 ?좏뵆由ъ??댁뀡 ?덈룄??

- **?쒕옒洹????쒕∼**: ?대뜑/?대?吏 ?쒕∼ 吏??
- **?뚮쭏**: ?ㅽ겕/?쇱씠???뚮쭏 ?좉?
- **?ㅻ낫???⑥텞??*: Ctrl+O, Ctrl+P, Ctrl+R, F5, F11 ??

### 3. Settings (core/settings_model/app_settings.py)

紐⑤뱺 ?ㅼ젙??dataclass濡?愿由?

- `AlgorithmSettings`: Canny ?꾧퀎媛? CLAHE ??
- `ProcessingSettings`: ?먮룞 ?鍮? ?좊챸????
- `OutputSettings`: 異쒕젰 ?щ㎎, ?덉쭏
- `WatermarkSettings`: ?뚰꽣留덊겕 ?ㅼ젙
- `ResizeSettings`: 由ъ궗?댁쫰 ?ㅼ젙
- `AppSettings`: ?꾩껜 ?ㅼ젙 吏묓빀

### 4. BatchProcessor (core/batch/processor.py)

?ㅼ쨷 ?대?吏 諛곗튂 泥섎━. ?대??곸쑝濡?`threading.Thread` + `ThreadPoolExecutor` 湲곕컲?쇰줈 ?숈옉?섎ŉ,
`PerformanceSettings`濡?蹂묐젹 泥섎━ ?ㅻ젅???섎? ?쒖뼱?⑸땲??

- `process_single(input_path, output_dir)`瑜??쒓났?섏뿬 Watch Mode?먯꽌??諛곗튂? ?숈씪???뚯씠?꾨씪?몄쓣 ?ъ슜?⑸땲??
- ?⑥씪/硫?고룷??紐⑤몢 ?쇨뎬 蹂댁젙 ???ㅻ쭏??蹂댁젙 ??由ъ궗?댁쫰 ??遺꾨쪟 ?대뜑 ?쇱슦???뚰꽣留덊겕 ??湲곗?) ???뚰꽣留덊겕 ?쒖꽌瑜?怨듯넻 ?곸슜?⑸땲??
- ?쇨뎬 媛먯? `use_dnn=True` ??紐⑤뜽 ?먮룞 ?ㅼ슫濡쒕뱶/泥댄겕??寃利앹쓣 ?쒕룄?섎ŉ, ?ㅽ뙣 ??Haar 媛먯?濡?利됱떆 ?대갚?⑸땲??
- 痍⑥냼 ??pending future瑜?鍮좊Ⅴ寃??뺣━??以묐떒 ?묐떟?깆쓣 ?믪??듬땲??

## 二쇱슂 湲곕뒫 ?먮쫫

1. **?⑥씪 ?대?吏 泥섎━**:
   ```
   MainWindow._do_preview() ??ImageProcessor.process_image() ??CropResult
   ```

2. **諛곗튂 泥섎━**:
   ```
   MainWindow._start_processing() ??BatchProcessor.start_async() ??
   (ThreadPoolExecutor) ImageProcessor.process_image() ??肄쒕갚/濡쒓렇 ?낅뜲?댄듃
   ```

3. **Watch Mode 泥섎━**:
   ```
   MainWindow._start_watch_mode() ??AutoProcessor ??
   BatchProcessor.process_single() ??諛곗튂? ?숈씪 ?꾩쿂由????
   ```

4. **?ㅼ젙 ???濡쒕뱶**:
   ```
   SettingsManager.load() ??AppSettings
   SettingsManager.save(AppSettings)
   ??????꾩튂 (Windows): %APPDATA%/PhotoCropper/settings.json
   ??????꾩튂 (macOS/Linux): ~/.photo_cropper/photo_cropper_settings.json
   ```

## 肄붾뵫 媛?대뱶?쇱씤

### 1. ?대?吏 泥섎━

- OpenCV BGR ?щ㎎ ?ъ슜
- ?좊땲肄붾뱶 寃쎈줈: `cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)`
- CLAHE 諛?而ㅻ꼸 媛앹껜??罹먯떛?섏뿬 ?ъ궗??
- ?뚰꽣留덊겕 ?대?吏 濡쒕뱶???숈씪???좊땲肄붾뱶 ?덉쟾 ?⑦꽩 ?ъ슜 (`cv2.imread` 吏곸젒 ?ъ슜 吏??

### 2. GUI

- PyQt6 ?ㅽ??쇱떆?몃줈 ?뚮쭏 ?곸슜
- ?쒓렇???щ’ ?⑦꽩 ?ъ슜
- `BatchProcessor`??`threading.Thread`/`ThreadPoolExecutor`濡?臾닿굅??泥섎━ 遺꾨━

### 3. ?ㅼ젙 愿由?

- dataclass 湲곕컲 ?ㅼ젙
- JSON 吏곷젹??
- ?먮룞 ???(debounce ?곸슜)

## 鍮뚮뱶

```bash
pip install pyinstaller
pyinstaller photo_cropper.spec --clean
```

異쒕젰: `dist/PhotoCropper_v9.exe`

## 臾몄젣 ?닿껐

### ?쒓? 寃쎈줈 ?ㅻ쪟
- `cv2.imread` ???`np.fromfile` + `cv2.imdecode` ?ъ슜

### GPU 媛??
- `PerformanceSettings.use_gpu` ?쒖꽦??
- OpenCV CUDA 鍮뚮뱶 ?꾩슂

### 硫붾え由?遺議?
- `PerformanceSettings.max_image_size_mb` 議곗젙
- `downscale_large_images` ?쒖꽦??

### Watch Mode/Batch 寃곌낵 遺덉씪移?
- Watch Mode??`BatchProcessor.process_single()` 寃쎈줈瑜??ъ슜?댁빞 ??
- 吏곸젒 `ImageProcessor.process_image()`留??몄텧?섎㈃ ?꾩쿂由??쇨뎬/?ㅻ쭏??蹂댁젙, 由ъ궗?댁쫰, 遺꾨쪟 ?쇱슦?? ?뚰꽣留덊겕)媛 ?꾨씫?????덉쓬

### DNN ?쇨뎬 媛먯? 紐⑤뜽 ?ㅼ슫濡쒕뱶 ?ㅽ뙣
- ?ㅽ듃?뚰겕/紐⑤뜽 ?뚯씪 臾몄젣 ??寃쎄퀬 濡쒓렇 ??Haar 罹먯뒪耳?대뱶濡??먮룞 ?대갚??
- 泥섎━ ?ㅽ뙣媛 ?꾨땲???뺥솗?????紐⑤뱶濡?怨꾩냽 吏꾪뻾??

### 以묐떒 ?묐떟 吏??
- 硫?곗뒪?덈뱶 諛곗튂 痍⑥냼??in-flight ?묒뾽 ?꾨즺瑜??쇰? 湲곕떎由????덉쓬
- pending ?묒뾽? 利됱떆 痍⑥냼?섎?濡??湲곗뿴 湲몄씠媛 湲?寃쎌슦 媛쒖꽑 ?④낵媛 ??

## 2026-03-01 Agent Update

- CLI merge contract is explicit: defaults -> preset -> config -> cli override.
- Effective priority is CLI > config > preset.
- --preset and --config are composable and active.
- Legacy key compatibility is maintained (`advanced_processing` read-compatible), while persisted profile keys normalize to `advanced`.
- Watch mode now exposes detailed completion and queue telemetry:
  - processing_completed_detailed(filepath, success, status, message, wait_ms)
  - queue_metrics_updated(queue_size, avg_wait_ms)
- Recursive watch onboarding now includes immediate initial image scan for newly detected subdirectories.
- Watch timeout is configurable via watch_mode.max_wait_seconds (default 30.0).
- Backward compatibility is preserved:
  - Legacy processing_completed(filepath, success) signal is kept.
  - Callback result parser accepts ool, tuple, dict, and object-like returns.


## 2026-03-02 Split Refactor Notes

- Split long modules into package paths:
  - `core/settings_model`, `core/advanced`, `core/face`, `core/image`, `core/batch`
  - `ui/main`, `ui/widgets/settings`, `i18n/catalog`
- Updated internal imports and packaging metadata (`photo_cropper.spec`) for the new package layout.
- Runtime behavior target remains unchanged: CLI options, settings schema, output rules, watch/batch contracts.

## 2026-03-03 Manual Boundary Workflow Notes

- Added main-window folder batch edit controls (`폴더 일괄 불러오기`, `← 이전`, `다음 →`, `편집 저장 추출`).
- Added failed-boundary correction flow:
  - collect boundary-detection failures after batch completion
  - prompt and load only failed files for manual contour correction
- Preview interaction now supports:
  - contour handle drag editing
  - direct 4-point manual boundary input when auto contour is unavailable
- Manual extraction cancel/close path now requests stop without blocking the UI thread.

