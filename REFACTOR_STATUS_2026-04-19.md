# Refactor Status 2026-04-19

## Current Scope

The split refactor is now materially complete for the biggest UI and core hotspots that were previously called out as backlog.

Completed since the earlier status note:
- `ui/widgets/settings/panel.py` was reduced to a coordinator and split into `tab_basic.py`, `tab_algorithm.py`, `tab_processing.py`, `tab_management.py`, `tab_ai.py`, and `controls.py`.
- `ui/widgets/management_pages.py` became a compatibility facade for the new `ui/widgets/management/` package.
- `core/batch/processor.py` became a facade over `context.py`, `io_paths.py`, `pipeline.py`, `runner.py`, and `single.py`.
- `core/batch/single.py` was further split into `_single_entry.py`, `_single_batch.py`, `_single_file.py`, and `_single_multi.py`.
- `core/image/processor.py` became a facade over `geometry.py`, `detect.py`, `debug_io.py`, `postprocess.py`, and `save_io.py`.
- `core/image/detect.py` was further split into `_detect_loading.py`, `_detect_contours.py`, `_detect_stages.py`, and `_detect_pipeline.py`.
- `core/library/repository.py` became a facade over repository mixin modules, and `_repository_assets.py` was split into `_repository_asset_core.py`, `_repository_asset_search.py`, and `_repository_asset_sources.py`.
- The management-app layer is now present in production code: `core/library/`, `core/jobs/`, `core/recipes/`, and `ui/widgets/management/`.

## Architecture Snapshot

Facade modules kept for API stability:
- `photo_cropper/core/batch/processor.py`
- `photo_cropper/core/image/processor.py`
- `photo_cropper/core/library/repository.py`
- `photo_cropper/ui/widgets/management_pages.py`

Primary split packages now expected by contributors:
- `photo_cropper/core/batch/`
- `photo_cropper/core/image/`
- `photo_cropper/core/library/`
- `photo_cropper/core/jobs/`
- `photo_cropper/core/recipes/`
- `photo_cropper/ui/widgets/settings/`
- `photo_cropper/ui/widgets/management/`

## Packaging Notes

- `photo_cropper.spec` remains the stable Windows build target and now uses `collect_submodules(...)` for the split package families so frozen builds do not depend on manually enumerating every newly extracted internal module.
- `photo_cropper_onefile.spec` remains experimental. It still relies on runtime extraction, but now derives `runtime_tmpdir` from the builder's `LOCALAPPDATA` or temp directory instead of a username-specific hardcoded path string.
- Dynamic locale loading still requires the locale package tree to be included in the frozen build. The spec keeps the locale package explicit and also collects locale submodules automatically.
- UPX remains disabled for both specs because Qt/PyQt + Windows application control policies were more reliable without compression.

## Validation Baseline

Recommended checks after structural or packaging changes:
- `cd ";opencv" && python -m compileall -q photo_cropper`
- `cd ";opencv" && python -m photo_cropper.selftest`
- `cd ";opencv" && pyright --project pyrightconfig.json`
- `cd ";opencv" && pyinstaller photo_cropper.spec --clean`

Optional packaging check:
- `cd ";opencv" && pyinstaller photo_cropper_onefile.spec --clean`

## Documentation Sync Notes

Documentation should now treat the following as current truth:
- The main UX is a management shell with `Library`, `Workbench`, `Review`, `Duplicates`, `Jobs`, `Collections`, `Recipes`, and `Settings`.
- The stable packaged output is the onedir build at `;opencv/dist/PhotoCropper_v9/PhotoCropper_v9.exe`.
- The onefile build is optional and experimental at `;opencv/dist/PhotoCropper_v9_single.exe`.
- `pyright` is part of the normal validation baseline alongside `compileall` and `selftest`.
