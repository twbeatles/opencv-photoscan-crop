#!/usr/bin/env bash
# Photo Cropper — 통합 검증 스크립트 (POSIX)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

resolve_app_dir() {
  for name in opencv ';opencv'; do
    if [[ -d "$REPO_ROOT/$name" ]]; then
      echo "$REPO_ROOT/$name"
      return 0
    fi
  done
  echo "App directory not found (expected opencv/ or ;opencv/)" >&2
  return 1
}

APP_DIR="$(resolve_app_dir)"
echo "==> App directory: $APP_DIR"

export PYTHONUTF8=1
export QT_QPA_PLATFORM=offscreen
export PHOTOCROPPER_OFFLINE=1

cd "$APP_DIR"

echo "==> compileall"
python -m compileall -q photo_cropper

echo "==> selftest"
python -m photo_cropper.selftest

echo "==> pytest (unit)"
python -m pytest tests/test_path_validation.py -q

echo "==> pyright"
PYRIGHT_CONFIG="$REPO_ROOT/pyrightconfig.json"
if [[ ! -f "$PYRIGHT_CONFIG" ]]; then
  PYRIGHT_CONFIG="$APP_DIR/pyrightconfig.json"
fi
pyright --project "$PYRIGHT_CONFIG"

echo "VERIFY OK"