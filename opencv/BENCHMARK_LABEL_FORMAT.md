# Benchmark Label Format

Use this format with `python -m photo_cropper.benchmark`.

## JSON schema (v1)
```json
{
  "version": 1,
  "items": [
    {
      "file": "relative/path/to/image.jpg",
      "has_photo": true,
      "quad": [[100, 120], [860, 110], [870, 620], [90, 630]]
    },
    {
      "file": "relative/path/to/no_photo.jpg",
      "has_photo": false
    }
  ]
}
```

## Rules
- `file`: required, path relative to `--images`.
- `has_photo`: required boolean.
- `quad`: required when `has_photo=true`.
- `quad` must be 4 points in image pixel coordinates.
- Real benchmark image datasets are intentionally not stored in this repository.
- Keep image paths external (local/private dataset directory) and pass via `--images`.

## Run
```bash
python -m photo_cropper.benchmark \
  --images ./benchmark/images \
  --labels ./benchmark/labels.json \
  --report ./benchmark/report.json \
  --detect-mode accurate
```

## Report metrics
- `success_rate`
- `mean_iou`
- `median_iou`
- `p90_iou`
- `false_positive_rate`
- `stage_distribution`
