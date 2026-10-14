# 📸 Photo Cropper (Photo Scan & Auto-Cropper)

🌐 **English** | [한국어](README.md)

A high-performance Python/PySide6 application designed to automatically detect, perspective-correct, and batch crop scanned photos, album pages, and documents on complex backgrounds using intelligent computer vision algorithms.

---

## 🌟 Key Features

- 🎯 **8-Stage Hybrid Detection Engine**: Combines Multi-Scale Canny, Background Mask, Adaptive Threshold, Sobel, Corner Detection, Morphological Gradient, Hough Rectangle, and LSD to reliably detect photos even on textured or uneven surfaces.
- 🖼️ **Multi-Photo Auto-Splitting**: Automatically detects multiple photos from a single scan (e.g., photo album pages), runs individual ROI re-detection (Refine), and saves them into separate image files.
- 📐 **Intelligent Perspective Deskew**: Automatically straightens skewed, tilted, or angled scans using 4-point perspective transformation.
- 🤖 **AI-Powered Auto-Classification & Portrait Tuning**: Classifies photos into `portrait`, `landscape`, `document`, `blackwhite`, and `other` folders; detects faces using DNN models for center-cropping and eye-level leveling; automatically restores faded color, contrast, and exposure (Smart Enhancement).
- 🛠️ **Professional GUI Workbench**: Real-time 10%–500% smooth zoom & pan, interactive 4-point & contour dragging for manual correction, Undo/Redo (`Ctrl+Z`/`Ctrl+Y`), and live RGB histogram.
- ⚡ **High-Speed Batch Processing & Automation**: Multi-threaded parallelism (`--jobs`), real-time folder monitoring (Watch Mode), automated scheduler, and duplicate skipping (`--skip-processed`).
- 📚 **Comprehensive Library & Asset Management**: SQLite catalog, visual thumbnail browsing, perceptual hashing (pHash) duplicate detection, failed photo review queue, and one-click re-run workflows.

---

## 🚀 Quick Start

### 1. Requirements & Installation

- **Python**: 3.11 or higher
- **OS**: Windows 10/11, macOS, Linux

```bash
# Clone the repository and navigate to the opencv folder
cd opencv

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch GUI

```bash
# Option A: From repository root
python ".\opencv\run.py"

# Option B: Inside opencv directory
cd opencv
python run.py
```

### 3. Quick 1-Line CLI Example

```bash
# Automatically crop all photos from scans folder and output to cropped directory
python -m photo_cropper.cli -i ./scans -o ./cropped
```

---

## 🖥️ GUI User Guide

The window has a **menu on the left** and the **working page** in the centre. The app opens on `Crop Photos`; work top to bottom: choose a folder → check the area → start cropping.

```text
┌───────────────┬──────────────────────────────────────────────────────────┐
│  Menu         │  Crop Photos                                             │
│               │  ┌────────────────────────────────────────────────────┐  │
│  Crop Photos  │  │ Photo folder | Save to | Scan type | Several photos │  │
│  Photo Library│  ├───────────────────────────────┬────────────────────┤  │
│  Needs a Check│  │  Original (detected area)     │ [Simple view] switch│  │
│  Duplicates   │  │  + cropped result preview     │ touch-up / saved    │  │
│  Job History  │  │  (wheel zoom, drag corners)   │ file options        │  │
│  Albums       │  ├───────────────────────────────┴────────────────────┤  │
│  Saved        │  │ Previous | Next | 1 / 12 · file   [Start Cropping]  │  │
│  Settings     │  └────────────────────────────────────────────────────┘  │
│  Maintenance  │                                                          │
└───────────────┴──────────────────────────────────────────────────────────┘
```

### 1. Standard Cropping Workflow

1. **Choose the photo folder**
   - Click `Choose Folder`, or **drag and drop** a folder/image onto the window. The detected area of the first scan appears **automatically**.
   - Leave `Save to` empty to save into an `output_cropped` folder inside the photo folder.
2. **Pick a scan type (only if needed)**
   - If the area is off, pick the closest `Scan type` (`Scanner, white background`, `Photo on a desk or table`, `Dark background`, `Album page`, `Document or paper`).
   - Turn on **`Several photos per scan`** when one scan holds more than one photo.
3. **Check and fix the area**
   - Use `Previous`/`Next` or the `←` `→` keys and check the green outline.
   - **Drag a corner dot** to fix it. Double-click the original to clear the area, then click the four corners yourself.
   - When detection fails or confidence is low, a `Needs a Check (N)` button appears to show just those scans.
4. **Start cropping**
   - Press `Start Cropping` (or `Space`) to crop and save every photo in the folder.
   - If you corrected any area by hand, the app first asks whether to **save with your corrections** or crop automatically.

### 2. Menu

| Page | What it does |
|------|--------------|
| **Crop Photos** | Choose a folder, check/fix the crop area, and crop everything in one go. |
| **Photo Library** | Browse processed photos as thumbnails; search by name, note, or tag. |
| **Needs a Check** | Only the scans where detection failed or confidence was low; re-process them. |
| **Duplicates** | Find identical or similar photos and tidy them up. |
| **Job History** | Success/failure statistics of past jobs; **retry failed photos only**. |
| **Albums** | Group photos by topic without moving files on disk. |
| **Saved Settings** | Save the settings you use often and apply them in one click. |
| **Maintenance** | See where library data lives; rebuild thumbnails and duplicate info. |

> The View menu switches the theme (follow system / light / dark) and shows the colour histogram.

### 3. Settings Panel

> By default **`Simple view`** is on and only everyday options are shown (touch-up, saved file, photos to skip, display). Turn it off to reveal the `Detection` / `Enhance` / `Automation` / `AI` tabs.

- **📷 Basic**: Post-processing defaults, UI themes (Dark/Light), runtime language switcher (KO/EN/JA/ZH/ES), output format (JPG/PNG/WEBP) & compression quality, skip existing files.
- **🔬 Algorithm**: Detection modes (`fast`, `balanced`, `accurate`), Canny edge thresholds, CLAHE enhancement, background mask delta, min/max area ratios, perspective warp toggle.
- **🔧 Processing**: Text/image/tiled watermarks, resize modes (Fit, Fill, %, SNS presets), unsharp masking (sharpen), denoise, grayscale conversion, auto deskew.
- **📂 Management**: Watch Mode real-time directory monitoring, scheduled batch runs, worker thread pool count (1–64), debug overlay image exports (`_debug`).
- **🤖 AI**: Category classification (Portrait/Landscape/Document/Monochrome), DNN face detector, face-centered cropping & eye-alignment auto-rotation, Smart Enhancement (auto exposure/color recovery).

### 4. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + O` | Select input directory |
| `Ctrl + I` | Open single image |
| `Ctrl + P` | Refresh preview |
| `Ctrl + R` | Rotate image 90° clockwise |
| `Ctrl + Z` / `Ctrl + Y` | Undo / Redo edits and setting changes |
| `F11` | Toggle fullscreen preview |
| `F5` | Refresh file list |
| `Ctrl + E` | Open output directory in file explorer |
| `Mouse Wheel` | Zoom in / out (10% to 500%) |
| `Right Click + Drag` | Pan across zoomed image |

---

## ⌨️ CLI Practical Guide

Integrate Photo Cropper into automated pipelines, batch scripts, or headless servers.

```bash
# Basic CLI structure (run inside opencv directory)
python -m photo_cropper.cli -i <input_dir> -o <output_dir> [options...]
```

### 1. Multi-Photo Splitting & Subfolder Organization

```bash
# Split multiple photos per scan + refine each ROI individually
python -m photo_cropper.cli -i ./album_scans -o ./out_photos --multi-photo --multi-photo-refine

# Save multi-photo crops into separate subfolders (<filename>_photos/)
python -m photo_cropper.cli -i ./album_scans -o ./out_photos --multi-photo --multi-photo-separate-folders
```

### 2. Scene Presets

```bash
# Flatbed scanner with white background
python -m photo_cropper.cli -i ./scans -o ./out --scene-preset scanner_white

# Wooden desk or textured table surface
python -m photo_cropper.cli -i ./desk_shots -o ./out --scene-preset desk_photo

# Dark cloth / black background
python -m photo_cropper.cli -i ./dark_bed -o ./out --scene-preset dark_background

# Photo album page with multiple photos
python -m photo_cropper.cli -i ./album -o ./out --scene-preset album_multi

# Document / paper sheets
python -m photo_cropper.cli -i ./docs -o ./out --scene-preset document
```

### 3. AI Category Classification & Folder Routing

```bash
# Enable AI classification and route into category folders (min confidence 70%)
python -m photo_cropper.cli -i ./scans -o ./out --classify --classify-auto-folder --classify-min-confidence 0.7
```

### 4. AI Face Detection, Centered Crop & Auto-Rotation

```bash
# DNN face detection + center crop around face + rotate based on eye level
python -m photo_cropper.cli -i ./portraits -o ./out --face-detect --face-dnn --face-auto-center-crop --face-auto-rotate
```

### 5. Smart Enhancement (Auto Exposure & Color Recovery)

```bash
# Automatically restore faded vintage scans (strength 80%)
python -m photo_cropper.cli -i ./old_scans -o ./out --smart-enhance --smart-strength 80
```

### 6. High-Speed Parallel Batch Processing

```bash
# 8 worker threads + recursive subfolder search + skip already processed images
python -m photo_cropper.cli -i ./all_scans -o ./out --jobs 8 --recursive --skip-processed
```

### 7. Formats, Resizing, Watermarking & Metadata Preservation

```bash
# WEBP output (quality 90) + Instagram square resize + watermark + keep EXIF
python -m photo_cropper.cli -i ./scans -o ./out \
  --format WEBP \
  --quality 90 \
  --resize instagram_square \
  --watermark "© 2026 Studio" \
  --preserve-metadata
```

> **Resize Specification Formats:**
> - Percentage: `--resize "50%"`
> - Fixed Resolution: `--resize "1200x900"`
> - Max Dimension: `--resize 1920` (or `--max-size 1920`)
> - Presets: `--resize instagram_square`, `--resize facebook_cover`, `--resize a4`

### 8. Using Saved Presets or JSON Config Files

```bash
# List available batch preset profiles
python -m photo_cropper.cli --list-presets

# Apply a saved profile
python -m photo_cropper.cli -i ./scans -o ./out --preset "High Quality Portrait"

# Use external JSON config with CLI overrides
python -m photo_cropper.cli -i ./scans -o ./out --config ./my_settings.json --jobs 4
```

---

## 🔬 Detection Engine & Tuning Guide

### 8-Stage Hybrid Pipeline

| Stage | Algorithm | Description & Role |
|:---:|:---|:---|
| **1** | Multi-Scale Canny Edge | Extracts edges across multiple scales to capture both coarse boundaries and fine lines. |
| **2** | Background Mask | Extracts background vs foreground candidates based on corner color sampling. |
| **3** | Adaptive Threshold | Local contrast binarization for unevenly lit scans. |
| **4** | Gradient Analysis (Sobel) | Analyzes intensity gradients to detect soft transitions. |
| **5** | Harris Corner Detection | Detects corner interest points to formulate rectangle hypotheses. |
| **6** | Morphology Gradient | Handles textured beds (fabric, wooden grains) via morphological gradients + Otsu. |
| **7** | Hough Rectangle Fallback | Clusters straight line segments to reconstruct partially clipped rectangles. |
| **8** | LSD Rectangle Detector | High-precision Line Segment Detector rectangle extraction (`accurate` mode). |

### Detection Mode (`--detect-mode`) Comparison

- `fast`: Early exit once a high-confidence candidate is found (ideal for plain scanner backgrounds).
- `balanced` (Default): Evaluates background mask + multi-scale edges + quad scoring for optimal speed/accuracy balance.
- `accurate`: Computes all candidates, performs global scoring (aspect ratio, orthogonality, area ratio, contrast), and applies GrabCut refinement.

---

## ⚙️ Configuration & Storage

### Configuration Paths

- **Windows**: `%APPDATA%\PhotoCropper\settings.json`
- **macOS / Linux**: `~/.photo_cropper/photo_cropper_settings.json`

### SQLite Database & Cache

- Library Catalog: `%APPDATA%\PhotoCropper\library.db` (stores metadata, processing history, pHash signatures, collections, and recipes)
- Thumbnail Cache: `%APPDATA%\PhotoCropper\thumbnails\`

---

## 🛠️ Development, Verification & Build

### 1. Verification Gate

Run full linting, typing, pytest suite, and selftests in one command:

```powershell
# Windows PowerShell
powershell -NoProfile -File scripts/verify.ps1
```

```bash
# macOS / Linux
bash scripts/verify.sh
```

### 2. Standalone Test Execution

```bash
cd opencv

# Pytest unit tests
python -m pytest tests/ -q

# Built-in self-test runner
python -m photo_cropper.selftest

# Benchmark runner
python -m photo_cropper.benchmark
```

### 3. PyInstaller Executable Build

```bash
cd opencv
pip install pyinstaller

# Directory build (recommended for stability)
pyinstaller photo_cropper.spec --clean

# Single-file build (experimental)
pyinstaller photo_cropper_onefile.spec --clean
```

- Output executable: `opencv/dist/PhotoCropper_v9/PhotoCropper_v9.exe`

---

## 📄 License & Contribution

- **License**: [MIT License](LICENSE)
- **Contributions**: Issues and PRs are welcome! Please check [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before submitting major changes.
