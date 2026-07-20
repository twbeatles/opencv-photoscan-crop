# 📸 Photo Cropper

🌐 English | [한국어](README.md)

A Python application that automatically detects and accurately crops scanned photos or photos placed on backgrounds.

> When running or building from the repository root, use paths under `opencv/` (the actual app directory).

---

## Features

### Auto Photo Detection & Cropping
- **8-stage intelligent detection**: Canny through LSD, plus NMS / GrabCut refine for varied backgrounds
- **Scene presets / simple mode**: One-click scanner/desk/album tuning; hide advanced settings tabs
- **Multi-photo detection**: Split multiple photos per scan + optional single-detect ROI refine (default ON)
- **Perspective correction**: Straightens skewed photos automatically (enabled by default)
- **Manual boundary editing**: Drag contour points or click 4 corners when auto-detection fails or confidence is low

### Batch Processing
- **Folder-level batch processing**: Process large sets of images at once (with ETA display)
- **Skip already-processed files**: Prevents duplicate work
- **Recursive processing**: Includes subfolders
- **Failed-file correction mode**: Reload only failed files for focused manual correction

### Post-processing Options
- **Watermark**: Text/image watermarks, 9 position anchors, tile mode
- **Resize**: Fit/Fill/percentage/max-dimension modes, presets for Instagram, Facebook, A4, and more
- **Image enhancement**: Grayscale, denoise, sharpen, face auto-enhancement
- **Auto classification**: AI-based routing into portrait/landscape/document/monochrome/other subfolders
- **Metadata preservation**: EXIF/ICC copy (best-effort)

### Management Features
- **Library**: SQLite-backed catalog of processed photos
- **Duplicate detection**: Find exact and near-duplicate photos
- **Collections / Recipes**: Save and reuse processing presets
- **Job history**: Track batch run results

### Automation
- **Watch Mode**: Monitor a folder and automatically process new files
- **Scheduler**: Trigger batch runs at a scheduled time
- **CLI support**: Script and pipeline integration

### UI/UX
- **Modern PyQt6 UI**: Dark/Light themes
- **Real-time preview**: Mouse wheel zoom, zoom slider (10%–500%)
- **Runtime language switching**: Korean, English, Japanese, Chinese, Spanish (no restart needed)
- **Drag and drop**: Drop folders or images directly onto the window
- **Undo/Redo**: Revert settings changes and manual edits with `Ctrl+Z`/`Ctrl+Y`

---

## Detection Algorithm

| Stage | Algorithm | Description |
|-------|-----------|-------------|
| Stage 1 | Multi-Scale Canny Edge | Multi-scale edge detection |
| Stage 2 | Background Mask | Background/foreground candidate extraction |
| Stage 3 | Adaptive Threshold | Adaptive binarization |
| Stage 4 | Gradient Analysis (Sobel) | Gradient-based candidate generation |
| Stage 5 | Harris Corner Detection | Corner detection (optional) |
| Stage 6 | Morphology Gradient | Morphology gradient + Otsu (textured beds) |
| Stage 7 | Hough Rectangle Fallback | Line-cluster based rectangle inference |
| Stage 8 | LSD Rectangle | Line Segment Detector rectangles (`accurate`) |

- **fast / balanced**: Early-exit for speed
- **accurate**: Full-pass candidates + global re-rank + content contrast + GrabCut refine
- **Scene presets**: Workbench / algorithm tab / CLI `--scene-preset`
- **Multi-photo ROI refine**: Re-run single detection per photo (default ON)

---

## Installation

**Requirements**
- Python 3.8 or higher
- Windows / macOS / Linux

```bash
cd opencv
pip install -r requirements.txt
```

---

## Usage

### GUI

```bash
# From repository root
python ".\\opencv\\run.py"

# Or from inside the app directory
cd opencv
python run.py
```

### CLI

```bash
cd opencv

# Basic usage
python -m photo_cropper.cli --input ./scans --output ./cropped

# Accuracy-first mode
python -m photo_cropper.cli -i ./scans -o ./cropped --detect-mode accurate

# Add watermark
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# Resize (percentage / resolution / preset)
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "50%"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize "1200x900"
python -m photo_cropper.cli -i ./scans -o ./cropped --resize instagram_square

# Separate multiple photos from one scan
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo

# Separate multiple photos into individual subfolders
python -m photo_cropper.cli -i ./scans -o ./cropped --multi-photo --multi-photo-separate-folders

# Preserve metadata
python -m photo_cropper.cli -i ./scans -o ./cropped --preserve-metadata

# Recursive processing (output must be outside input root)
python -m photo_cropper.cli -i ./scans -o ../cropped --recursive

# Skip already-processed files
python -m photo_cropper.cli -i ./scans -o ./cropped --skip-processed

# Parallel processing (number of threads)
python -m photo_cropper.cli -i ./scans -o ./cropped --jobs 6

# Show all options
python -m photo_cropper.cli --help
```

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| `Ctrl+O` | Select input folder |
| `Ctrl+I` | Open image |
| `Ctrl+P` | Preview |
| `Ctrl+R` | Rotate image (90° clockwise) |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `F11` | Fullscreen preview |
| `F5` | Refresh file list |
| `Ctrl+E` | Open output folder |
| `Ctrl+Q` | Exit |

---

## Settings

### Settings File Location

- **Windows**: `%APPDATA%/PhotoCropper/settings.json`
- **macOS / Linux**: `~/.photo_cropper/photo_cropper_settings.json`

### Algorithm Settings

| Setting | Description |
|---------|-------------|
| Detection mode | `fast` / `balanced` / `accurate` — speed vs. accuracy tradeoff |
| Canny threshold | Edge detection sensitivity (0–255) |
| CLAHE | Low-contrast image enhancement |
| Precision tuning | Min/max area ratio, background mask delta, adaptive block size, etc. |
| Perspective correction | ON (default): 4-point warp / OFF: axis-aligned bounding-box crop |
| Debug save | Save edge/mask/candidate overlays to `_debug` folder for failure analysis |

### Output Settings

| Setting | Description |
|---------|-------------|
| Output format | JPG / PNG / WEBP |
| Quality | JPG/WEBP: 1–100 / PNG compression: 0–9 |
| Metadata | EXIF/ICC copy (save continues on metadata failure) |
| Image enhancement | Grayscale, denoise, sharpen |
| Auto classification | Route into category subfolders when AI confidence threshold is met |

### Watermark Settings

- **Text watermark**: Text, font size, color, shadow
- **Image watermark**: PNG file, scale, opacity
- **Position**: 9 anchors from top-left to bottom-right
- **Tile mode**: Repeating pattern watermark

### Resize Settings

- **Modes**: Fit, Fill, Percentage (%), Max dimension
- **Presets**: Instagram, Facebook, A4, and more

### Automation Settings

- **Watch Mode**: Monitors a folder and processes new files automatically
  - In recursive Watch Mode, the output folder must be outside the input root
- **Scheduler**: Runs a batch at a scheduled time (`HH:MM`)
  - `once` type: runs once at the next occurrence of `HH:MM` (no date field)

---

## Project Structure

```text
opencv/
├── run.py
├── photo_cropper.spec
└── photo_cropper/
    ├── main.py
    ├── cli.py
    ├── selftest.py
    ├── core/
    │   ├── image/          # Crop algorithm
    │   ├── batch/          # Batch processor
    │   ├── library/        # Library catalog (SQLite)
    │   ├── jobs/           # Job history
    │   ├── recipes/        # Recipes / presets
    │   ├── settings_model/ # Settings dataclasses
    │   ├── advanced/       # Advanced image operations
    │   ├── watch_mode/     # Watch Mode
    │   ├── multi_photo_detector.py
    │   ├── watermark_processor.py
    │   ├── resize_processor.py
    │   └── scheduler.py
    ├── ui/
    │   ├── main/           # Main window
    │   └── widgets/        # UI components
    ├── i18n/catalog/       # Localization
    └── utils/
```

---

## Development & verification

- **Unified verify (recommended)**: from repository root run `powershell -NoProfile -File scripts/verify.ps1` or `bash scripts/verify.sh`
- **pytest unit tests**: `cd opencv && python -m pytest tests/test_path_validation.py -q`
- **selftest filter**: `cd opencv && python -m photo_cropper.selftest cli_cancel`
- See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow

---

## Build (PyInstaller)

```bash
pip install pyinstaller

# Stable build (recommended)
pyinstaller ".\\opencv\\photo_cropper.spec" --clean

# Experimental single-file build
pyinstaller ".\\opencv\\photo_cropper_onefile.spec" --clean
```

**Output paths**
- Stable build: `opencv/dist/PhotoCropper_v9/PhotoCropper_v9.exe`
- Single-file: `opencv/dist/PhotoCropper_v9_single.exe`

> The onedir build (`photo_cropper.spec`) is recommended for Windows environments with strict application-control policies.

---

## License

MIT License

## Contributing

Bug reports and feature suggestions are welcome — please open an Issue. See [CONTRIBUTING.md](CONTRIBUTING.md) for development and verification steps.
