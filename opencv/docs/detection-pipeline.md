# Detection Pipeline Notes

This document summarizes the photo-boundary detection path after the 2026 accuracy/UX refactor.

## Architecture

- `ImageProcessor` — facade (post-process, save, settings, geometry)
- `DetectionPipeline` — composed detection engine (`core/image/detection_pipeline.py`)
  - Mixin methods: load/CLAHE, stages, contours, full pipeline
  - Host shares settings/kernels; monkeypatches on `ImageProcessor` still apply
  - UI **simple mode** hides advanced settings tabs; workbench scene presets remain

## Single-photo flow

```text
load_image (EXIF normalize)
  → optional detection downscale
  → CLAHE
  → stage candidates (Canny / BG / Adaptive / Sobel / Harris / Morph / Hough / LSD)
  → per-stage soft gates + filters
  → cross-stage NMS (IoU)
  → accurate: global re-rank | fast/balanced: early exit
  → final confidence floor
  → corner snap to edge map
  → GrabCut ROI refine (accurate only, optional accept)
  → perspective or axis crop
  → post-process
  → CropResult (+ failure_reason, stage_scores)
```

## Multi-photo flow

```text
MultiPhotoDetector (Adaptive + multi-scale Canny + LAB/Otsu)
  → split connected components
  → merge overlapping (IoU / distance)
  → crop_photos (perspective-first)
  → optional ROI refine via ImageProcessor._process_loaded_image
  → batch post pipeline (face / enhance / resize / classify / watermark)
```

Algorithm Canny / Adaptive knobs are shared into `MultiPhotoDetector` via batch context.

## Scene presets

`core/scene_presets.py` maps:

| id | intent |
|----|--------|
| `scanner_white` | bright scanner bed |
| `desk_photo` | mixed desk surface |
| `dark_background` | dark cloth / low-key |
| `album_multi` | multi-photo page (enables multi + refine) |
| `document` | paper / document |

CLI: `--scene-preset <id>`  
GUI: workbench quick combo + algorithm tab

## Scoring signals

- area / aspect / corner angle
- edge support (denser sampling in accurate)
- border penalty (scanner frame)
- **content contrast** (interior vs shell) for noise FP rejection

## Benchmark

```bash
python -m photo_cropper.benchmark \
  --images ./benchmark/images \
  --labels ./benchmark/labels.json \
  --report ./benchmark/report.json \
  --detect-mode accurate \
  --baseline ./benchmark/baseline.json
```

Per-item report fields include `failure_reason` and `stage_scores`.
