#!/usr/bin/env bash
# Optional benchmark gate: exits 0 when labels/images are not present.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCV="$ROOT/opencv"
LABELS="$OPENCV/benchmark/labels.json"
IMAGES="$OPENCV/benchmark/images"

if [[ ! -f "$LABELS" ]]; then
  echo "SKIP benchmark: opencv/benchmark/labels.json not found"
  exit 0
fi
if [[ ! -d "$IMAGES" ]]; then
  echo "SKIP benchmark: opencv/benchmark/images not found"
  exit 0
fi

cd "$OPENCV"
python -m photo_cropper.benchmark \
  --images ./benchmark/images \
  --labels ./benchmark/labels.json \
  --report ./benchmark/report.json \
  --detect-mode accurate
