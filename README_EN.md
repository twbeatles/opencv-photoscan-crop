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
- **Skip Already Processed Files**: Prevent duplicate processing
- **Multiple Output Formats**: JPG, PNG, WEBP support

### UI/UX
- **Modern PyQt6-based UI**: Dark/Light themes, gradient effects
- **Toast Notifications**: Slide-in animation notifications on completion
- **Real-time Preview**: Mouse wheel zoom, zoom slider (10%~500%)
- **Drag and Drop**: Drop folders or images directly

## 🛠️ Detection Algorithm

| Stage | Algorithm | Description |
|-------|-----------|-------------|
| Stage 1 | Multi-Scale Canny Edge | Multi-scale edge detection |
| Stage 2 | Adaptive Threshold | Adaptive binarization |
| Stage 3 | Gradient Analysis (Sobel) | Gradient analysis |
| Stage 4 | Harris Corner Detection | Corner detection (optional) |

## 📦 Installation

### Requirements
- Python 3.8 or higher
- Windows / macOS / Linux

### Installation Steps

```bash
cd photo_cropper
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

# With watermark
python -m photo_cropper.cli -i ./scans -o ./cropped --watermark "© 2026"

# With resize
python -m photo_cropper.cli -i ./scans -o ./cropped --max-size 1920

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

### Algorithm Settings
- **Canny Threshold**: Edge detection sensitivity (0-255)
- **CLAHE**: Low contrast image enhancement
- **Multi-scale**: Detect photos of various sizes
- **Corner Detection**: Additional accuracy improvement

### Output Settings
- **Output Format**: JPG, PNG, WEBP
- **Quality Control**: JPG/WEBP quality (1-100), PNG compression (0-9)
- **Grayscale/Denoise/Sharpening**

## 📁 Project Structure

```
photo_cropper/
├── main.py                  # Entry point
├── cli.py                   # CLI interface (v8.5)
├── core/
│   ├── image_processor.py   # Core image processing
│   ├── batch_processor.py   # Batch processing
│   ├── settings.py          # Settings management
│   ├── multi_photo_detector.py  # Multi-photo detection (v8.5)
│   ├── watermark_processor.py   # Watermark (v8.5)
│   ├── resize_processor.py      # Resize (v8.5)
│   ├── folder_watcher.py        # Folder watch (v8.5)
│   ├── scheduler.py             # Scheduler (v8.5)
│   └── history_manager.py       # History management (v8.5)
├── ui/
│   ├── main_window.py
│   └── widgets/
│       ├── settings_panel.py
│       ├── preview_widget.py
│       ├── thumbnail_grid_widget.py  # Thumbnail grid (v8.5)
│       ├── fullscreen_viewer.py      # Fullscreen viewer (v8.5)
│       └── floating_action_button.py # FAB (v8.5)
├── i18n/                    # Internationalization (v8.5)
│   └── translations.py
└── utils/
    └── file_helpers.py
```

## 🔧 Build (PyInstaller)

### Create Executable

```bash
# Install dependencies
pip install pyinstaller

# Build (optimized)
pyinstaller photo_cropper.spec --clean
```

Built executable: `dist/SmartPhotoCropper_v85.exe`

### Additional Optimization (UPX)

Install [UPX](https://github.com/upx/upx/releases) to reduce executable size by ~30-50%:

1. Download and extract UPX
2. Add `upx.exe` to system PATH
3. Rebuild: `pyinstaller photo_cropper.spec --clean`

### Build Optimizations

| Item | Description |
|------|-------------|
| Single File | onefile mode creates single .exe |
| Excluded Modules | matplotlib, scipy, pandas, tkinter, etc. |
| OpenCV Optimization | Removed unused modules (dnn, ml, video, etc.) |
| NumPy Optimization | Removed test/doc files |
| UPX Compression | Compressed executable (~40% size reduction) |

## 📋 Changelog

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
