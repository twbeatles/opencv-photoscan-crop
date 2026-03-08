# Photo Cropper Precision Implementation Review (2026-03-08)

## Implementation Status (Applied on 2026-03-08)
- Scope: All 10 recommendations in this review were implemented (P0 + P1 + P2).
- Mode policy:
  - Global stage candidate re-ranking is applied only in `accurate` mode.
  - `fast`/`balanced` keep early-exit behavior.
- Benchmark policy:
  - Repository includes benchmark harness, label format, template, and report generation.
  - Real-image datasets are intentionally excluded from the repository.
- Updated modules:
  - `;opencv/photo_cropper/core/image/processor.py`
  - `;opencv/photo_cropper/core/multi_photo_detector.py`
  - `;opencv/photo_cropper/core/face/detector.py`
  - `;opencv/photo_cropper/cli.py`
  - `;opencv/photo_cropper/ui/widgets/settings/panel.py`
  - `;opencv/photo_cropper/benchmark.py`
  - `;opencv/photo_cropper/selftest.py`
  - `;opencv/BENCHMARK_LABEL_FORMAT.md`
- Validation note:
  - Syntax compile checks passed for changed modules.
  - Full selftest in this environment still requires OpenCV (`cv2`) installation.

## Scope and References
- Reviewed docs:
  - `README.md` (root)
  - `;opencv/README.md`
  - `;opencv/README_EN.md`
  - `;opencv/CLAUDE.md`
- Reviewed code focus:
  - `;opencv/photo_cropper/core/image/processor.py`
  - `;opencv/photo_cropper/core/multi_photo_detector.py`
  - `;opencv/photo_cropper/core/face/detector.py`
  - `;opencv/photo_cropper/core/batch/processor.py`
  - `;opencv/photo_cropper/ui/widgets/settings/panel.py`
  - `;opencv/photo_cropper/cli.py`
  - `;opencv/photo_cropper/selftest.py`

## Key Findings (Precision / Recognition)

### 1) [High] `merge_distance` setting is effectively unused in multi-photo detection
- Evidence:
  - `;opencv/photo_cropper/core/multi_photo_detector.py:51`
  - `;opencv/photo_cropper/core/multi_photo_detector.py:71`
  - `;opencv/photo_cropper/core/multi_photo_detector.py:346`
- Why it matters:
  - UI/config gives users the impression they can tune nearby-photo merge behavior, but detection output does not reflect that knob.
- Recommendation:
  - Integrate `merge_distance` into `_merge_overlapping()` using center distance / edge gap rules in addition to IoU.

### 2) [High] Multi-photo mode crops by axis-aligned bounding boxes only (no perspective correction)
- Evidence:
  - `;opencv/photo_cropper/core/multi_photo_detector.py:387`
  - `;opencv/photo_cropper/core/multi_photo_detector.py:408`
  - `;opencv/photo_cropper/core/multi_photo_detector.py:414`
  - `;opencv/photo_cropper/core/batch/processor.py:1607`
- Why it matters:
  - Rotated/skewed photos remain geometrically distorted after split; this directly reduces crop precision.
- Recommendation:
  - For each detected contour, derive a quad (`approxPolyDP` / `minAreaRect`) and apply `warpPerspective`.
  - Keep bbox crop as fallback only.

### 3) [High] Stage pipeline early-exits after first accepted candidate
- Evidence:
  - `;opencv/photo_cropper/core/image/processor.py:994`
  - `;opencv/photo_cropper/core/image/processor.py:1011`
  - `;opencv/photo_cropper/core/image/processor.py:1048`
  - `;opencv/photo_cropper/core/image/processor.py:1083`
  - `;opencv/photo_cropper/core/image/processor.py:1107`
- Why it matters:
  - A marginal candidate from an earlier stage can block better candidates from later stages.
- Recommendation:
  - Collect top candidates from all stages, then global re-rank with a unified score and tie-breakers.
  - Keep mode-based speed shortcuts, but for `accurate` mode prefer full-stage evaluation.

### 4) [High] Edge-support score can be inflated on filled masks
- Evidence:
  - `;opencv/photo_cropper/core/image/processor.py:327`
  - `;opencv/photo_cropper/core/image/processor.py:545`
  - `;opencv/photo_cropper/core/image/processor.py:724`
  - `;opencv/photo_cropper/core/image/processor.py:995`
- Why it matters:
  - In background-mask/adaptive-threshold stages, scoring uses a binary foreground mask as if it were edge evidence; this can over-score wrong quads.
- Recommendation:
  - Compute edge-support against a dedicated edge map (e.g., Canny/gradient magnitude) independent of stage mask.

### 5) [Medium] Quad scoring has bias against extreme-yet-valid layouts
- Evidence:
  - `;opencv/photo_cropper/core/image/processor.py:410`
  - `;opencv/photo_cropper/core/image/processor.py:416`
  - `;opencv/photo_cropper/core/image/processor.py:419`
  - `;opencv/photo_cropper/core/image/processor.py:367`
- Why it matters:
  - Area score peaks at midpoint of min/max ratio and decays to zero at bounds; large full-frame photos can be penalized.
  - Aspect ratio uses axis-aligned bbox, which is unstable for perspective-distorted quads.
- Recommendation:
  - Replace triangular area prior with plateau/sigmoid prior.
  - Use side-length ratio from ordered quad points instead of bbox ratio.

### 6) [Medium] Hough rectangle fallback is angle-limited
- Evidence:
  - `;opencv/photo_cropper/core/image/processor.py:781`
  - `;opencv/photo_cropper/core/image/processor.py:802`
  - `;opencv/photo_cropper/core/image/processor.py:805`
- Why it matters:
  - Fallback strongly assumes near-horizontal/vertical lines; rotated photos can be missed.
- Recommendation:
  - Cluster by theta/rho and infer dominant orthogonal line pairs with broader angle tolerance.

### 7) [Medium] EXIF orientation normalization is missing
- Evidence:
  - `;opencv/photo_cropper/core/image/processor.py:192`
  - `;opencv/photo_cropper/core/image/processor.py:205`
- Why it matters:
  - Smartphone-origin images with orientation tags can be processed in wrong orientation, reducing detection and recognition quality.
- Recommendation:
  - Normalize orientation on load (`Pillow` + `ImageOps.exif_transpose`) before converting to OpenCV array.

### 8) [Medium] Face rotation angle uses `faces[0]` instead of primary face
- Evidence:
  - `;opencv/photo_cropper/core/face/detector.py:81`
  - `;opencv/photo_cropper/core/face/detector.py:357`
  - `;opencv/photo_cropper/core/face/detector.py:358`
- Why it matters:
  - In multi-face scenes, eye-angle may be computed from a non-primary face, causing wrong auto-rotation.
- Recommendation:
  - Use `primary_face` (largest/highest confidence) for rotation-angle estimation.

### 9) [Medium] Precision-critical algorithm knobs are not exposed in UI/CLI
- Evidence:
  - UI retains hidden values instead of exposing controls:
    - `;opencv/photo_cropper/ui/widgets/settings/panel.py:885`
    - `;opencv/photo_cropper/ui/widgets/settings/panel.py:889`
  - CLI only exposes detect mode + canny thresholds:
    - `;opencv/photo_cropper/cli.py:455`
    - `;opencv/photo_cropper/cli.py:461`
- Why it matters:
  - Hard to reproduce and tune precision behavior per data domain (scanner type, background texture, lighting).
- Recommendation:
  - Expose `min_area_ratio`, `max_area_ratio`, `bg_mask_delta`, `adaptive_block_size`, `adaptive_c` in UI and CLI.

### 10) [Process Gap] Current precision tests are mostly synthetic
- Evidence:
  - `;opencv/photo_cropper/selftest.py:370`
  - `;opencv/photo_cropper/selftest.py:484`
  - `;opencv/photo_cropper/selftest.py:551`
- Why it matters:
  - Synthetic success can hide real-world failures (glare, blur, shadows, scanner borders, textured paper).
- Recommendation:
  - Add a real-image benchmark set with labeled quads and report metrics per commit:
    - Detection success rate
    - Quad IoU (mean/median/P90)
    - False-positive rate on no-photo inputs
    - Stage usage distribution

## Suggested Implementation Priorities

### P0 (Immediate)
- Wire `merge_distance` into multi-photo dedup logic.
- Add EXIF orientation normalization in image loading.
- Use primary face for auto-rotate angle.

### P1 (Short-term)
- Change multi-photo split from bbox crop to quad perspective crop.
- Decouple edge-support scoring from filled masks.
- Add `accurate` mode full-stage candidate aggregation and global ranking.

### P2 (Mid-term)
- Expose advanced precision parameters in UI/CLI.
- Build real-world benchmark pack + automated regression gate.

## Validation Status in This Environment
- Attempted command:
  - `python -m photo_cropper.selftest`
- Result:
  - Failed due to missing dependency: `cv2` not installed in current environment.
  - Error observed: `SELFTEST FAILED: Crop editor import failed: No module named 'cv2'`
