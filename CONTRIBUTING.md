# Contributing / Agent Automation Guide

## Quick verify

From repository root:

```bash
pwsh -File scripts/verify.ps1
# or
bash scripts/verify.sh
```

Runs: `compileall` → `photo_cropper.selftest` → `pyright`.

Optional detection benchmark (skips if private labels/images are absent):

```bash
pwsh -File scripts/run_benchmark_if_present.ps1
# or
bash scripts/run_benchmark_if_present.sh
```

Detection pipeline notes: `opencv/docs/detection-pipeline.md`

## App directory

The application lives in `opencv/` (formerly `;opencv/`).

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PHOTOCROPPER_LIBRARY_DB` | Override SQLite library DB path (tests/agents) |
| `PHOTOCROPPER_OFFLINE=1` | Disable DNN face model download (CI/sandbox) |
| `QT_QPA_PLATFORM=offscreen` | Headless Qt tests |
| `PYTHONUTF8=1` | Stable Unicode logging on Windows |

## Tests

- Legacy integration suite: `python -m photo_cropper.selftest`
- Filter one case: `python -m photo_cropper.selftest cli_cancel`
- Pytest unit tests: `python -m pytest tests/test_path_validation.py`
- Pytest selftest registry (slow): `python -m pytest -m selftest`

Singleton reset helpers: `photo_cropper.core.test_reset.reset_all_singletons_for_tests()`

## CodeGraph (optional)

Local index lives in `.codegraph/` (gitignored). Rebuild with your CodeGraph MCP tooling before structural audits.

`opencv/convert_icon.py` is a local-only icon conversion helper (gitignored) with machine-specific paths; use `opencv/icon.ico` for builds instead.

## Dev dependencies

```bash
pip install -r opencv/requirements-dev.txt
```