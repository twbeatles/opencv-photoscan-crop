# Contributing / Agent Automation Guide

## Pre-push gate (required)

**Do not push until local verify is green.** GitHub Actions runs the same
`scripts/verify.*` path on Ubuntu + Windows; pyright failures there fail the
whole `verify` workflow.

From repository root:

```bash
pwsh -File scripts/verify.ps1
# or
bash scripts/verify.sh
```

Runs: `compileall` → `photo_cropper.selftest` → `pytest` (unit) → `pyright`.

Optional fast type-only check (same config CI uses):

```bash
pyright --project pyrightconfig.json
```

Install a local git pre-push hook once (optional but recommended):

```bash
# Windows (PowerShell)
pwsh -File scripts/install-hooks.ps1
# POSIX
bash scripts/install-hooks.sh
```

Optional detection benchmark (skips if private labels/images are absent):

```bash
pwsh -File scripts/run_benchmark_if_present.ps1
# or
bash scripts/run_benchmark_if_present.sh
```

Detection pipeline notes: `opencv/docs/detection-pipeline.md`

### Common CI failure patterns

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Argument of type "float" cannot be assigned to parameter ... of type "int"` | Building kwargs via mixed `dict(...)` then `**kwargs` | Pass explicit typed kwargs (or `int()`/`float()` casts) to constructors |
| `No overloads for "grabCut"` / `None` not assignable to `Rect` | OpenCV stubs require a rect even for `GC_INIT_WITH_MASK` | Pass a dummy `(x, y, w, h)` rect |
| `Code is too complex to analyze` | Large monolithic functions | Split into helpers (stages / finalize / crop) |

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