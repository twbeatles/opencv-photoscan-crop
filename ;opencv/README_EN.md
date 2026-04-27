# 📸 Photo Cropper v9.0

🌐 [한국어](README.md) | English

A Python application that automatically detects and accurately crops scanned photos or photos placed on backgrounds.

## ✨ What's New in v9.0

### 🎨 UI/UX Redesign
- **New Color Theme**: Indigo Purple accent (#818cf8)
- **Enhanced Color Palette**: Emerald/Rose/Amber for success/error/warning
- **Gradient Toast Notifications**: More refined notification UI
- **Improved Progress UI**: New color palette applied

### ⚡ Performance Optimization
- **CLAHE Object Caching**: Faster image processing
- **Kernel Caching**: Optimized morphological operations
- **Import Optimization**: Removed unnecessary inline imports

### 🛡️ Stability Updates (2026-02)
- **Watch/Batch Pipeline Parity**: Watch Mode now applies the same post-processing chain as batch mode (face adjustment, smart enhancement, resize, classification folders, watermark)
- **Fixed Post-Processing Order**: face adjustment → smart enhancement → resize → classification routing (pre-watermark) → watermark
- **AI Settings Enforcement**: Classification and face detection toggles are applied in actual processing/saving paths
- **Unicode-Safe Watermark Paths**: Image watermark loading uses `np.fromfile + cv2.imdecode`
- **Grayscale + Image Watermark Safety**: channel mismatch issues are handled for `to_grayscale + image watermark`
- **DNN Face Detection Fallback Hardening**: automatic model download/checksum with immediate Haar fallback on failure
- **Large File Guard Enforcement**: `performance.max_image_size_mb` is applied before processing
- **skip_processed Improvements**: duplicate checks now include classification subfolders
- **Faster Cancellation Response**: Multithreaded batch cancellation now reacts faster by cancelling pending tasks
- **GPU Setting Wiring**: `PerformanceSettings.use_gpu` is now propagated to advanced processor initialization

### 🛡️ Processing Consistency Update (2026-03)
- **Perspective default ON**: `advanced.perspective_correct=True` by default; OFF now uses axis-aligned bounding-box crop from detected 4 points
- **Manual extract parity with batch**: manual "Save Edited Extract" now reuses the same post-processing/routing/naming policy as batch
- **Save fallback hardening**: unsupported/missing output extension now falls back to encoder selected by `output_format`
- **Metadata preserve (best-effort)**: EXIF/ICC copy failures emit warnings only; image save remains successful
- **Multi-photo per-file subfolder**: `separate_output_folders=true` writes outputs under `<input_filename>_photos/`
- **merge_distance wired into dedup**: duplicate suppression sensitivity now follows `merge_distance`
- **Local processed index introduced**: `.photocropper/processed_index.json` improves `skip_processed` reproducibility
- **Custom classification folder names**: default Korean folders preserved, plus user-configurable per-category names in settings
- **Watch readiness fairness improvements**: not-ready files are re-queued fairly with explicit timeout/read-fail statuses
- **Scheduler runtime wiring**: scheduler settings in UI now trigger real automatic batch runs while app is running
- **Watch background worker**: Watch Mode callbacks now run sequentially on `AutoProcessor`'s background worker, and readiness timeout/retry ownership also lives in `AutoProcessor`
- **EXIF Orientation rewrite**: `preserve_metadata` keeps EXIF/ICC best-effort, but always rewrites Orientation to `1` to avoid double rotation
- **Multi-photo `partial_success` status**: incomplete multi-photo saves are surfaced as `partial_success` in batch summaries, Watch toasts, and processing log summaries
- **Shared multi-photo loader**: multi-photo input loading now reuses `ImageProcessor.load_image()` so EXIF orientation normalization matches single-photo and manual paths
- **Batch re-entry guard**: running batch sessions are no longer replaced, and `start_processing()` / `retry_failed_files()` refuse overlapping starts
- **Manual preview/save crop parity**: manual contour preview now shares the same crop rule as final save
- **Recursive Watch output guard**: recursive watch refuses to start when the output directory is inside the input root
- **Watch failed-file routing disabled**: Watch processing forces `move_failed_files=False` on a runtime snapshot to avoid `_failed` feedback loops
- **Watch overwrite reprocessing**: overwriting the same file path now re-queues through `fileChanged` only when the size/mtime signature actually changed
- **Processed index v2 partial policy**: index records now store `status=success|partial`, and `partial` warns then reprocesses instead of full skipping
- **Retry Failed path normalization**: empty output paths are normalized to `<input>/output_cropped` with the same validation used by normal batch start

### 🛡️ Implementation Alignment Update (2026-04)
- **Recursive Batch/CLI/Watch safety guard**: recursive runs now refuse to start when the output lives inside the input root
- **Recursive scan exclusion of generated folders**: `output_root`, `_failed`, `backup`, and `.photocropper` are pruned automatically
- **Relative-path-preserving output rules**: recursive output, `_failed`, and `*_photos` trees now preserve the input-relative directory context
- **Aligned `partial_success` accounting**: GUI and CLI summaries now use the same `success/partial_success/failed/skipped` counters
- **CLI `--strict-partial` added**: partial results remain success-like by default, but become exit code `1` in strict mode
- **Classification model normalization**: legacy `custom` is kept as a deprecated alias of `advanced`, and the UI now exposes only `basic/advanced`
- **Scheduler `once` wording clarified**: it means "run once at the next upcoming HH:MM" without a date field
- **Python locale catalogs**: translation sources are now centralized in `photo_cropper/i18n/catalog/locales/*.py`
- **Runtime UI retranslation**: the saved language is applied before initial UI construction, and long-lived widgets/menus/toolbars update immediately on language changes
- **Safe path-segment validation**: classification folders and naming prefix/suffix are validated as single safe path segments before emit/run
- **Locale-aware classification defaults**: blank classification folder values now resolve to the current UI language default, with legacy Korean defaults migrated automatically

### 🗂️ Management Shell & Refactor Update (2026-04-19)
- **Management shell**: the desktop UX now centers on `Library`, `Workbench`, `Review`, `Duplicates`, `Jobs`, `Collections`, `Recipes`, and `Settings`
- **Catalog + job history**: the management-app layer now lives under dedicated `core/library/`, `core/jobs/`, and `core/recipes/` packages
- **SOLID-oriented split refactor**: former hotspot files were converted into thin facades plus focused internal modules, especially in `core/batch/`, `core/image/`, `core/library/`, `ui/widgets/settings/`, and `ui/widgets/management/`
- **Packaging hardening**: PyInstaller specs now auto-collect split package submodules so frozen builds track the refactored layout more reliably
- **Validation baseline updated**: `pyright` is part of the standard consistency check together with `compileall` and `selftest`

### 🌐 Multi-Language Support
- Automatic system locale detection
- 5 languages: English, Korean, Japanese, Chinese, Spanish

### 🔥 v8.5 Core Features
- **Multi-Photo Detection**: Automatically separate multiple photos from single scan
- **Watermark Support**: Text/Image watermarks
- **Image Resize**: Multiple modes supported
- **Folder Monitoring**: Auto-processing Watch Mode
- **CLI Mode**: Command-line batch processing

---

## Key Features

### Core Features
- **3+ Stage Intelligent Detection Algorithm**: High detection success rate on various backgrounds
- **Batch Processing**: Process large quantities of images at once (with ETA display)
- **Main-screen Batch Editing**: Load folder images, navigate previous/next, edit contours, then save all in one pass
- **Watch Mode Pipeline Integration**: Watch and batch processing now produce consistent outputs
- **Skip Already Processed Files**: Prevent duplicate processing
- **Multiple Output Formats**: JPG, PNG, WEBP support

### UI/UX
- **Modern PyQt6-based UI**: Dark/Light themes, gradient effects
- **Runtime language switching**: Korean, English, Japanese, Chinese, and Spanish can be applied to major UI surfaces without restarting
- **Toast Notifications**: Slide-in animation notifications on completion
- **Real-time Preview**: Mouse wheel zoom, zoom slider (10%~500%)
- **Manual Boundary Editing**: Drag contour points in the Original tab, or click 4 points when auto-detection fails
- **Failed-files Correction Mode**: Load only boundary-detection failures for focused manual correction
- **Drag and Drop**: Drop folders or images directly

## 🛠️ Detection Algorithm

| Stage | Algorithm | Description |
|-------|-----------|-------------|
| Stage 1 | Multi-Scale Canny Edge | Multi-scale edge detection |
| Stage 2 | Background Mask | Background/foreground candidate extraction |
| Stage 3 | Adaptive Threshold | Adaptive binarization |
| Stage 4 | Gradient Analysis (Sobel) | Gradient analysis |
| Stage 5 | Harris Corner Detection | Corner detection (optional) |
| Stage 6 | Hough Rectangle Fallback | Line-cluster based rectangle inference |

- `fast` and `balanced` keep early-exit behavior for speed.
- `accurate` evaluates all stages and performs global re-ranking across stage candidates.

## 📦 Installation

### Requirements
- Python 3.8 or higher
- Windows / macOS / Linux

### Installation Steps

```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Running GUI Application

```bash
python run.py
```

### CLI Usage (v8.5+)

```bash
# Basic usage
python -m photo_cropper.cli --input ./scans --output ./cropped

# Accuracy-first + debug artifacts
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate --debug-detect

# Precision tuning overrides (CLI)
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate \
  --min-area-ratio 0.08 --max-area-ratio 0.97 \
  --bg-mask-delta 34 --adaptive-block-size 19 --adaptive-c 3.0

# With watermark
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# With resize
python -m photo_cropper.cli -i ./scans -o ./cropped --max-size 1920

# Multi-photo detailed options
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-merge-distance 80 --multi-photo-separate-folders

# Preserve metadata + disable perspective warp
python -m photo_cropper.cli -i ./scans -o ./cropped --preserve-metadata --no-perspective-correct

# Recursive input + strict partial failure policy
python -m photo_cropper.cli -i ./scans -o ../cropped --recursive --strict-partial

# Legacy custom is still accepted, but treated as advanced internally
python -m photo_cropper.cli -i ./scans -o ./cropped --classify --classify-model custom

# Show options
python -m photo_cropper.cli --help
```

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| `Ctrl+O` | Select input folder |
| `Ctrl+I` | Open image |
| `Ctrl+P` | Preview |
| `Ctrl+R` | Rotate image (90° clockwise) |
| `Ctrl+Z` | Undo (v8.5) |
| `Ctrl+Y` | Redo (v8.5) |
| `F11` | Fullscreen preview (v8.5) |
| `F5` | Refresh file list |
| `Ctrl+E` | Open output folder |
| `Ctrl+Q` | Exit |

## ⚙️ Settings

### Settings File Location
- Windows: `%APPDATA%/PhotoCropper/settings.json`
- macOS/Linux: `~/.photo_cropper/photo_cropper_settings.json`

> On Windows, if a legacy settings file exists (`~/.photo_cropper/photo_cropper_settings.json`), it will be automatically migrated to the new location.

### v8.5+ New Settings

#### Watermark Settings
- **Text Watermark**: Text, font size, color, shadow
- **Image Watermark**: PNG image, scale, opacity
- **Position**: 9 positions (top-left to bottom-right)
- **Tile Mode**: Repeated pattern watermark

#### Resize Settings
- **Modes**: Fit, Fill, Stretch, Percentage, Max Dimension
- **Size**: Width, Height, Percentage (%)
- **Presets**: Instagram, Facebook, A4, etc.

#### Automation Settings
- **Folder Watch**: Auto-process new files
- **Scheduler**: Scheduled batch processing

#### Language and Safe Naming
- **Live language updates**: changing the language in settings refreshes the main menu, toolbar, status bar, and other long-lived widgets immediately.
- **Safe classification folders**: classification folder names reject separators, `..`, drive/UNC patterns, Windows reserved names, trailing dots/spaces, and control characters.
- **Safe naming rules**: prefix/suffix use the same validator, and invalid form state blocks settings emit plus auto-preview.
- **Locale-default sentinel**: leaving a classification folder blank means "use the current UI language default folder name."

> Note: in recursive Watch Mode, the output directory must live outside the input root. If you want to keep the default `<input>/output_cropped`, disable recursive watch or choose an external output directory.
> Note: schedule type `once` means "run once at the next upcoming HH:MM" rather than a date-based one-shot schedule.
> Note: recursive Batch/Watch/CLI scans automatically exclude generated folders such as `output_root`, `_failed`, `backup`, and `.photocropper`.

### Algorithm Settings
- **Canny Threshold**: Edge detection sensitivity (0-255)
- **CLAHE**: Low contrast image enhancement
- **Multi-scale**: Detect photos of various sizes
- **Corner Detection**: Additional accuracy improvement
- **Detection Mode (fast/balanced/accurate)**: Presets to trade speed vs accuracy (enables stronger fallbacks in accurate mode)
- **Precision Tuning (UI + CLI)**:
  - `min_area_ratio`, `max_area_ratio`
  - `bg_mask_delta`
  - `adaptive_block_size`, `adaptive_c`
- **Detection Debug Save**: Save stage images/overlays/`meta.json` under `_debug` for failure analysis
- **Perspective default**: ON by default, OFF switches to axis-aligned bbox crop

### Output Settings
- **Output Format**: JPG, PNG, WEBP
- **Quality Control**: JPG/WEBP quality (1-100), PNG compression (0-9)
- **Metadata Preserve**: EXIF/ICC best-effort copy (save still succeeds on metadata failure)
- **Grayscale/Denoise/Sharpening**
- **Auto Classification Output (optional)**: Save into category subfolders when confidence threshold is met
> Note: recursive inputs preserve the input-relative directory structure across output results, `_failed`, and multi-photo `*_photos` folders.
> Note: classification model `custom` is no longer a separate profile and is treated as a compatibility alias of `advanced`.

> Note: `skip processed` now uses a local processed index first (`.photocropper/processed_index.json`).
> Index key: `source_path + size + mtime_ns + pipeline_signature`; multi-photo outputs are stored in `outputs[]`.
> `partial_success` is persisted as `status=partial`, but later runs do not fully skip it; they warn and reprocess.
> Filename-based probing is used as fallback only when the index is unavailable.
> Classification subfolders (default Korean names, user-configurable) and multi-photo subfolders (`*_photos`) are both included in fallback probing.
> Note: CLI summaries always print `processed/success/partial_success/failed/skipped`, and `--strict-partial` turns partial-only runs into exit code `1`.

## 🧪 Stability Checklist

- **Syntax validation**: `python -m compileall -q photo_cropper`
- **Type check**: `pyright --project pyrightconfig.json`
- **Full selftest**: `python -m photo_cropper.selftest`
- **CLI smoke test**: `python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-separate-folders --preserve-metadata --no-perspective-correct --skip-processed`
- **Watch mode parity**: verify new files in Watch Mode go through same resize/watermark/classification behavior as batch mode
- **Recursive batch safety**: verify recursive batch/CLI refuses to start when output is inside input
- **Recursive watch safety**: verify recursive watch refuses to start when output is inside input
- **Watch overwrite behavior**: overwrite a watched image in place and confirm it re-queues only when size/mtime actually changed
- **Manual preview/save parity**: with `advanced.perspective_correct=false`, confirm manual preview and saved crop shapes match
- **Scheduler check**: with `watch_mode.scheduler_enabled=true`, confirm auto-batch starts at scheduled time and overlapping triggers are skipped
- **CLI partial policy**: confirm partial-only runs exit `0` by default and exit `1` with `--strict-partial`
- **Unicode path test**: use a watermark image in a non-ASCII path and verify output succeeds
- **Cancel semantics**: in multithreaded batch, request stop and verify final stats consistency and CLI exit code `130`
- **Benchmark harness validation**:
  - `python -m photo_cropper.benchmark --images ./benchmark/images --labels ./benchmark/labels.json --report ./benchmark/report.json --detect-mode accurate`
  - Label format reference: `BENCHMARK_LABEL_FORMAT.md` (real-image datasets are intentionally not bundled in the repo)

## 📁 Project Structure

```
photo_cropper/
├── main.py
├── cli.py
├── core/
│   ├── app_paths.py
│   ├── batch/
│   ├── image/
│   ├── jobs/
│   ├── library/
│   ├── recipes/
│   ├── settings_model/
│   ├── manual_extract/
│   ├── watch_mode/
│   ├── multi_photo_detector.py
│   ├── processed_index.py
│   ├── resize_processor.py
│   ├── scheduler.py
│   └── watermark_processor.py
├── ui/
│   ├── main/
│   └── widgets/
│       ├── management/
│       └── settings/
├── i18n/
│   └── catalog/
└── utils/
    └── path_validation.py
```

## 🔧 Build (PyInstaller)

### Create Executable

```bash
# Install dependencies
pip install pyinstaller

# Stable Windows build
pyinstaller photo_cropper.spec --clean

# Experimental single-file build
pyinstaller photo_cropper_onefile.spec --clean
```

Built executables:
- Stable onedir: `dist/PhotoCropper_v9/PhotoCropper_v9.exe`
- Experimental onefile: `dist/PhotoCropper_v9_single.exe`

### Packaging Notes

- `photo_cropper.spec` is the recommended build target because it avoids the temp-extraction DLL blocking issue seen in stricter Windows application-control environments.
- `photo_cropper_onefile.spec` is kept for convenience/testing and still depends on runtime extraction.
- UPX is intentionally disabled for both specs because uncompressed Qt/PyQt builds were more reliable under Windows policy enforcement.

### Build Optimizations

| Item | Description |
|------|-------------|
| Stable target | `photo_cropper.spec` builds an onedir app folder |
| Experimental target | `photo_cropper_onefile.spec` builds a single-file `.exe` |
| Excluded Modules | matplotlib, scipy, pandas, tkinter, etc. |
| Split-module collection | package submodules are auto-collected for refactored `core/*` and `ui/*` packages |
| OpenCV/Qt Trimming | Excludes `cv2.gapi` plus unneeded Qt/OpenCV runtime binaries |
| Compression policy | UPX disabled for App Control / PyQt stability |

## 📋 Changelog

### v9.0 Implementation Alignment Update (2026-04-06)
- 🛡️ Unified the recursive output-inside-input guard across batch/watch/CLI, and centralized recursive scan exclusion for `output_root`, `_failed`, `backup`, and `.photocropper`
- 🛡️ Preserved input-relative directory structure for recursive output results, failed-file routing, and multi-photo folder layouts
- 🛡️ Split out `BatchProgress.partial_success`, aligned GUI/CLI summary semantics, and added CLI `--strict-partial`
- 🛡️ Normalized legacy classification model `custom` into the `advanced` alias while simplifying UI choices to `basic/advanced`
- 🛡️ Clarified Scheduler `once` as a no-date "next upcoming HH:MM" run

### v9.0 Integrated Improvements (2026-03-05)
- ✨ Added local processed index (`.photocropper/processed_index.json`) and wired it across batch/watch/manual flows
- ✨ Added configurable classification folder mapping (`ClassificationSettings.category_folders`) while preserving default Korean folder compatibility
- ✨ Connected scheduler UI settings to runtime automatic batch triggering (while app is running)
- 🛡️ Improved watch readiness/retry policy (stat/read timeout handling, fair queueing, retry-count diagnostics)
- 🛡️ Improved cancellation consistency with completed-future draining and explicit `CANCELLED` accounting for unstarted tasks
- 🛡️ Removed duplicate watch toasts by making detailed completion the user-facing notification path
- 🛡️ Standardized CLI exit codes: cancel `130`, failure `1`, success `0`
- 🛡️ Unified profile application through `to_dict + deep-merge + AppSettings.from_dict`

### v9.0 Precision Patch (2026-03-08)
- 🎯 Added global candidate re-ranking in `accurate` mode (collect Stage 1~6 then select by score/tie-breakers)
- 🎯 Separated edge-support scoring input from stage masks to a dedicated edge reference map
- 🎯 Improved area prior (plateau), aspect scoring (ordered-quad side lengths), and Hough fallback (angle-bin clusters)
- 🎯 Extended multi-photo contract with `DetectedPhoto.quad` and perspective-first crop (bbox fallback retained)
- 🎯 Wired `merge_distance` into dedup with combined `IoU + center distance + edge gap`
- 🎯 Added EXIF orientation normalization (Pillow-first, OpenCV fallback) and primary-face-based auto-rotation angle
- 🎯 Exposed 5 precision tuning parameters in UI and CLI
- 🎯 Added executable benchmark harness (`photo_cropper.benchmark`) with label template/docs

### v9.0 Manual Boundary Workflow Update (2026-03)
- ✨ Added main-screen flow for folder batch editing (`Load Batch`, `Prev/Next`, `Save Edited Extract`)
- ✨ Detects boundary-failed files after batch completion and prompts user to enter failed-files-only correction mode
- ✨ Improved original-tab contour editing, including direct 4-point boundary input
- 🛡️ Improved cancellation/close responsiveness during manual extraction

### v9.0 Stability Patch (2026-02)
- 🛡️ Unified Watch Mode to use `BatchProcessor.process_single()` pipeline
- 🛡️ Aligned face adjustment/smart enhancement/resize/classification-folder routing/watermark across batch and watch modes
- 🛡️ Classification routing now uses pre-watermark pixels to reduce classification distortion
- 🛡️ Switched watermark image loading to Unicode-safe `np.fromfile + cv2.imdecode`
- 🛡️ Removed channel-mismatch errors for grayscale + image watermark combinations
- 🛡️ Added automatic DNN face model download/checksum and immediate Haar fallback on network/model failures
- 🛡️ Enforced `max_image_size_mb` as a pre-processing file-size guard in batch/watch flows
- 🛡️ Extended `skip processed` duplicate probing to classification subfolder paths
- 🛡️ Improved multithreaded cancellation responsiveness by cancelling pending tasks first

### v9.0 (2026-01)
- 🎨 **UI/UX Redesign** - Indigo Purple theme (#818cf8)
- 🎨 **New Color Palette** - Emerald/Rose/Amber
- 🎨 **Gradient Toast** - More refined notification UI
- 🌐 **5 Language Support** - KO, EN, JA, ZH, ES with auto-detection
- ⚡ **CLAHE Caching** - Faster image processing
- ⚡ **Kernel Caching** - Optimized morphological operations

### v8.5 (2026-01)
- ✨ **Multi-Photo Detection** - Separate multiple photos from single scan
- ✨ **Watermark System** - Text/Image watermarks
- ✨ **Image Resize** - Multiple modes and presets
- ✨ **Folder Monitoring** - Auto-processing Watch Mode
- ✨ **Scheduler** - Scheduled batch processing
- ✨ **CLI Interface** - Command-line batch processing
- ✨ **Thumbnail Grid View** - Grid display for image list
- ✨ **Fullscreen Preview** - F11 fullscreen mode
- ✨ **FAB (Floating Action Button)** - Quick access menu
- ✨ **Undo/Redo History** - Undo/Redo support
- ✨ **Multi-language Support** - Korean, English, Japanese

## 📄 License

MIT License

## 👨‍💻 Contributing

Please report bugs or feature suggestions in Issues.

## 2026-03-01 Update (Implementation Alignment)

- CLI settings merge is now explicit: defaults -> preset -> config -> cli override.
- Effective precedence: CLI > config > preset.
- --preset now loads real profiles via BatchProfileManager.
- --config now merges full AppSettings, including legacy key mapping `advanced_processing` -> `advanced`.
- New CLI AI options are available for classification, face detection, and smart enhancement.
- Watch mode observability was expanded with detailed completion status and queue metrics.
- Recursive watch mode now scans newly added subdirectories immediately for pre-existing images.
- Watch timeout is configurable with watch_mode.max_wait_seconds (default 30.0).
- Profile key compatibility is maintained on read, while save/export normalizes to `advanced`.
- Self-tests were added for import smoke, CLI merge precedence, recursive watch ingestion, and watch max-wait roundtrip.
- Preview pipeline now has a fast-path mode (default on) that caps detection to 8MP for lower latency, while batch/save quality behavior is unchanged.
- Preview worker now reuses a persistent ImageProcessor and updates it only when settings revision changes, reducing repeated initialization overhead.
- Batch multithreading now uses bounded in-flight scheduling (max_workers * 3) instead of full upfront future submission for better throughput/memory balance.
- Watch mode queue internals were optimized from list pop(0)/insert(0) to deque popleft/appendleft for lower queue overhead at scale.
- Input-path file counting in UI is now debounced (250ms) to avoid repeated directory scans during typing.

> Note: full processing self-tests require OpenCV (cv2).


## 2026-03-02 Split Refactor Notes

- Split long modules into package paths:
  - `core/settings_model`, `core/advanced`, `core/face`, `core/image`, `core/batch`
  - `ui/main`, `ui/widgets/settings`, `i18n/catalog`
- Updated internal imports and packaging metadata (`photo_cropper.spec`) for the new package layout.
- Runtime behavior target remains unchanged: CLI options, settings schema, output rules, watch/batch contracts.

## 2026-03-04 Consistency Check Notes

- Verified `pyright --project pyrightconfig.json` with 0 errors / 0 warnings.
- Aligned `QWidget` override event signatures to PyQt6 stubs by matching both event types and stub parameter names (`a0`), and promoted required window timers to non-optional services to remove Pylance warnings.
- Strengthened PyInstaller hidden imports for split modules:
  `watch_mode`, `manual_extract`, `session_service`, `save_io`, `dialog_actions`.

## 2026-03-16 Consistency Check Notes

- Added a repository-root `../pyrightconfig.json` plus root `.editorconfig` so root-level and app-level workflows now share the same type-check and UTF-8 text rules.
- Verified both `pyright --project pyrightconfig.json` and root-level `pyright --project .\pyrightconfig.json` with 0 errors / 0 warnings.
- Verified `python -m photo_cropper.selftest` with `SELFTEST OK`.
- Reduced no-photo false-positive regressions in `accurate` mode with stage-specific candidate filters, and normalized quad point ordering for multi-photo perspective-crop dimension calculations.
- Added `ui.main.preview_worker` to `photo_cropper.spec` hidden imports; no new runtime third-party dependencies were introduced by this consistency pass.

## 2026-03-25 Stabilization Notes

- Manual contour preview now goes through `core.manual_extract.crop_manual_contour()`, so `perspective_correct=false` shows the same axis-aligned crop that save uses.
- `ui/widgets/preview_widget.py` now renders seed input (1-3 points) separately from a valid 4-point contour, removing the `UnboundLocalError` path and partial guide-line rendering bug.
- Recursive Watch Mode now rejects output paths inside the input root, and direct UI starts now enforce watch/batch/manual mutual exclusion.
- Watch processing uses a settings snapshot with `move_failed_files=False`, preventing `_failed` reprocessing loops, while `FolderWatcher.fileChanged` only re-queues overwrite events when the file signature actually changed.
- Processed-index schema is now v2 with `status=success|partial`; legacy records default to `success`, and `partial` records warn but still reprocess.
- `retry_failed_files()` now shares the same empty-output normalization and output-directory validation path as regular batch start.
- Verification: `python -m compileall -q photo_cropper`, `python -m photo_cropper.selftest`

## 2026-03-09 UI/MainWindow Consistency Notes

- `ui/main/window.py` is now a composition root, with runtime behavior moved into `ui/main/actions/`.
- Widget construction now lives in `ui/main/builders/`, and shared context types are defined in `ui/main/models.py`.
- `photo_cropper.spec` hidden imports now cover the canonical package paths (`ui.main.actions.*`, `ui.main.builders.*`, `ui.main.models`) plus the compatibility shim modules.

## 2026-04-19 Management + Refactor Notes

- Management-app architecture is now first-class: library ingest, review queue, duplicate handling, collections, recipes, and job orchestration live under dedicated `core/library`, `core/jobs`, and `core/recipes` packages.
- Former hotspot files now act as compatibility facades while the real implementation lives in focused modules:
  - `core/batch/processor.py`
  - `core/image/processor.py`
  - `core/library/repository.py`
  - `ui/widgets/management_pages.py`
- `core/batch/single.py`, `core/image/detect.py`, and `core/library/_repository_assets.py` were each further split into smaller internal modules to reduce responsibility overlap.
- Validation baseline confirmed on this structure:
  - `python -m compileall -q photo_cropper`
  - `python -m photo_cropper.selftest`
  - `pyright --project pyrightconfig.json`

## 2026-04-27 Management/Library Stabilization Notes

- Management rerun/reprocess, Watch, and Batch now share a file-list preflight path. Recursive output-inside-input guards, empty-output defaults, and missing-file validation are applied consistently.
- Library import, exact duplicate rebuild, near duplicate rebuild, and search-index rebuild now run through maintenance jobs instead of blocking the UI thread directly.
- SQLite connections enable `foreign_keys=ON` and `busy_timeout=5000`; initialization enables WAL best-effort. Write paths use a store-level `RLock` plus a write connection helper to reduce contention.
- `LibraryRepository.upsert_source()` now returns `ingest_state="invalid_source"` for empty paths, missing files, directories, and unsupported non-image files without creating assets.
- FTS refresh failures mark `app_state.search_index_dirty=1`, and `maintenance_search_index` can rebuild the full index.
- Asset timeline queries now use asset-specific SQL instead of scanning a 5000-item review window, and near-duplicate rebuild summaries include `scanned_assets`, `limited`, and `limit`.
- Thumbnail/AI/OCR/person provider failures are recorded in job summary fields: `metadata_warnings`, `ai_errors`, and `thumbnail_failed_count`.
- `core/library/_repository_protocol.py` documents repository mixin typing contracts, and file-level pyright suppressions in the touched library/batch/image areas were removed.
- Validation baseline:
  - `python -m compileall -q photo_cropper`
  - `pyright --project pyrightconfig.json`
  - `python -m photo_cropper.selftest`
