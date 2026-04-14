# Refactor Status 2026-04-14

## Scope Check

The split refactor is not fully complete yet.

Completed:
- Python locale catalog based i18n loading in `photo_cropper/i18n/catalog/locales/*.py`
- Runtime UI retranslation wiring for main-window level long-lived widgets
- Shared path validation in `photo_cropper/utils/path_validation.py`
- Settings-model responsibility split into:
  - `core/settings_model/app_settings.py`
  - `core/settings_model/manager.py`
  - `core/settings_model/migration.py`
  - `core/settings_model/validation.py`
- Main-window runtime helper split into `ui/main/services/`
- Shared result/type extraction into:
  - `core/image/types.py`
  - `core/batch/types.py`

Still large and pending additional split:
- `;opencv/photo_cropper/ui/widgets/settings/panel.py`
- `;opencv/photo_cropper/core/image/processor.py`
- `;opencv/photo_cropper/core/batch/processor.py`
- `;opencv/photo_cropper/selftest.py`

## Packaging Notes

- `photo_cropper.spec` must pin `photo_cropper.i18n.catalog.locales.*` because locale modules are loaded dynamically.
- `ui.main.services.*`, `core.settings_model.{manager,migration,validation}`, `core.{image,batch}.types`, and `utils.path_validation` should remain explicit hidden imports until packaging is revalidated without them.

## Current Validation Baseline

Recommended checks after code changes:
- `python -m compileall -q photo_cropper`
- `python -m photo_cropper.selftest`
- `pyinstaller photo_cropper.spec --clean`
