#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""CLI settings-merge self-tests."""

from __future__ import annotations


def _test_cli_settings_merge_priority() -> None:
    import json
    import os
    import tempfile

    from .. import cli as cli_mod
    from ..core.batch_profile_manager import BatchProfileManager
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_merge_") as td:
        profiles_dir = os.path.join(td, "profiles")
        manager = BatchProfileManager(profiles_dir=profiles_dir)

        preset_settings = AppSettings()
        preset_settings.algorithm.canny_min = 11
        preset_settings.algorithm.canny_max = 111
        preset_settings.output.jpg_quality = 88
        preset_settings.classification.model = "basic"
        created = manager.create_profile("selftest-merge", preset_settings)
        assert created

        config_path = os.path.join(td, "config.json")
        config_data = {
            "algorithm": {"canny_min": 22, "canny_max": 44},
            "advanced_processing": {"auto_deskew": True},
            "classification": {"model": "advanced", "min_confidence": 0.65},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        parser = cli_mod.create_parser()
        args = parser.parse_args(
            [
                "--preset",
                "selftest-merge",
                "--config",
                config_path,
                "--canny-min",
                "33",
                "--min-area-ratio",
                "0.12",
                "--max-area-ratio",
                "0.91",
                "--bg-mask-delta",
                "41",
                "--adaptive-block-size",
                "21",
                "--adaptive-c",
                "3.5",
                "--classify-model",
                "custom",
            ]
        )

        original_get_manager = cli_mod.get_batch_profile_manager
        cli_mod.get_batch_profile_manager = lambda: manager
        try:
            merged = cli_mod.build_settings_from_args(args)
        finally:
            cli_mod.get_batch_profile_manager = original_get_manager

        assert merged.algorithm.canny_min == 33  # CLI overrides config/preset
        assert merged.algorithm.canny_max == 44  # config overrides preset
        assert abs(float(merged.algorithm.min_area_ratio) - 0.12) < 1e-6
        assert abs(float(merged.algorithm.max_area_ratio) - 0.91) < 1e-6
        assert abs(float(merged.algorithm.bg_mask_delta) - 41.0) < 1e-6
        assert int(merged.algorithm.adaptive_block_size) == 21
        assert abs(float(merged.algorithm.adaptive_c) - 3.5) < 1e-6
        assert merged.output.jpg_quality == 88  # preset applied
        assert merged.classification.model == "advanced"  # CLI alias normalized
        assert abs(merged.classification.min_confidence - 0.65) < 1e-6
        assert merged.advanced.auto_deskew is True  # legacy alias mapped


def _test_cli_new_crop_options() -> None:
    from .. import cli as cli_mod

    parser = cli_mod.create_parser()
    args = parser.parse_args(
        [
            "--preserve-metadata",
            "--no-perspective-correct",
            "--multi-photo-merge-distance",
            "77",
            "--multi-photo-separate-folders",
        ]
    )
    settings = cli_mod.build_settings_from_args(args)
    assert settings.output.preserve_metadata is True
    assert settings.advanced.perspective_correct is False
    assert settings.multi_photo.enabled is True
    assert settings.multi_photo.merge_distance == 77
    assert settings.multi_photo.separate_output_folders is True

    args_on = parser.parse_args(["--perspective-correct"])
    settings_on = cli_mod.build_settings_from_args(args_on)
    assert settings_on.advanced.perspective_correct is True

    args_scene = parser.parse_args(
        ["--scene-preset", "album_multi", "--no-multi-photo-refine"]
    )
    settings_scene = cli_mod.build_settings_from_args(args_scene)
    assert settings_scene.multi_photo.enabled is True
    assert settings_scene.multi_photo.refine_with_single is False
    assert settings_scene.algorithm.detection_mode == "accurate"


def _test_processed_index_roundtrip_and_source_change() -> None:
    import os
    import tempfile
    import time

    from ..core.batch import BatchProcessor
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    settings.filter.skip_processed = True
    settings.file_management.use_naming_rules = True
    processor = BatchProcessor(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_index_") as td:
        in_dir = os.path.join(td, "in")
        out_dir = os.path.join(td, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        src = os.path.join(in_dir, "sample.jpg")
        out = os.path.join(out_dir, "sample_cropped.jpg")
        with open(src, "wb") as f:
            f.write(b"source-v1")
        with open(out, "wb") as f:
            f.write(b"result-v1")

        processor.record_processed_outputs(src, out_dir, [out])
        matched, usable, status = processor.lookup_processed_outputs_from_index(
            src, out_dir
        )
        assert usable is True
        assert status == "success"
        assert matched is not None and len(matched) == 1
        assert os.path.normcase(os.path.abspath(matched[0])) == os.path.normcase(
            os.path.abspath(out)
        )

        time.sleep(0.01)
        with open(src, "ab") as f:
            f.write(b"-changed")

        matched_changed, usable_changed, status_changed = (
            processor.lookup_processed_outputs_from_index(src, out_dir)
        )
        assert usable_changed is True
        assert status_changed == ""
        assert matched_changed is None


def _test_processed_index_backward_compat_and_partial_status() -> None:
    import json
    import os
    import tempfile

    from ..core.processed_index import (
        INDEX_DIRNAME,
        INDEX_FILENAME,
        RECORD_STATUS_PARTIAL,
        ProcessedIndexStore,
        build_pipeline_signature,
    )
    from ..core.settings_model import AppSettings

    settings = AppSettings()
    pipeline_signature = build_pipeline_signature(settings)

    with tempfile.TemporaryDirectory(prefix="photocropper_index_compat_") as td:
        output_dir = os.path.join(td, "out")
        os.makedirs(output_dir, exist_ok=True)
        index_root = os.path.join(output_dir, INDEX_DIRNAME)
        os.makedirs(index_root, exist_ok=True)

        src = os.path.join(td, "source.jpg")
        out = os.path.join(output_dir, "source_cropped.jpg")
        with open(src, "wb") as f:
            f.write(b"source")
        with open(out, "wb") as f:
            f.write(b"output")

        st = os.stat(src)
        legacy_payload = {
            "version": 1,
            "updated_at": "2026-03-25T00:00:00Z",
            "records": [
                {
                    "source_path": src,
                    "size": int(st.st_size),
                    "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                    "outputs": [out],
                    "pipeline_signature": pipeline_signature,
                }
            ],
        }
        with open(
            os.path.join(index_root, INDEX_FILENAME),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(legacy_payload, f, ensure_ascii=False)

        store = ProcessedIndexStore(output_dir)
        matched, usable, status = store.lookup_outputs(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            pipeline_signature=pipeline_signature,
        )
        assert usable is True
        assert status == "success"
        assert matched is not None and len(matched) == 1

        assert store.upsert_record(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            outputs=[out],
            pipeline_signature=pipeline_signature,
            status=RECORD_STATUS_PARTIAL,
        )
        partial_outputs, partial_usable, partial_status = store.lookup_outputs(
            source_path=src,
            size=int(st.st_size),
            mtime_ns=int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            pipeline_signature=pipeline_signature,
        )
        assert partial_usable is True
        assert partial_status == "partial"
        assert partial_outputs is not None and len(partial_outputs) == 1


def _test_profile_apply_rebuild_validation() -> None:
    import tempfile

    from ..core.batch_profile_manager import BatchProfile, BatchProfileManager
    from ..core.settings_model import AppSettings

    with tempfile.TemporaryDirectory(prefix="photocropper_profile_apply_") as td:
        manager = BatchProfileManager(profiles_dir=td)
        manager._profiles["selftest-invalid"] = BatchProfile(
            name="selftest-invalid",
            settings={
                "advanced_processing": {"auto_deskew": True},
                "face_detection": {"min_face_size": 1},
                "classification": {"min_confidence": 5.0},
            },
        )

        settings = AppSettings()
        ok = manager.apply_profile("selftest-invalid", settings)
        assert ok is True
        assert settings.advanced.auto_deskew is True
        assert settings.face_detection.min_face_size == 20
        assert abs(settings.classification.min_confidence - 1.0) < 1e-6


def _test_cli_rejects_invalid_settings_segments() -> None:
    import io
    import json
    import os
    import tempfile
    from contextlib import redirect_stderr

    from .. import cli as cli_mod

    with tempfile.TemporaryDirectory(prefix="photocropper_cli_invalid_") as td:
        in_dir = os.path.join(td, "input")
        out_dir = os.path.join(td, "output")
        os.makedirs(in_dir, exist_ok=True)
        config_path = os.path.join(td, "bad.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "file_management": {
                        "naming_prefix": "../bad",
                        "failed_folder_name": "CON",
                    },
                    "classification": {
                        "category_folders": {"portrait": "bad/folder"}
                    },
                },
                handle,
            )

        parser = cli_mod.create_parser()
        args = parser.parse_args(["-i", in_dir, "-o", out_dir, "--config", config_path])
        error_buffer = io.StringIO()
        with redirect_stderr(error_buffer):
            code = cli_mod.process_batch(args)
        assert code == 2
        assert "ERROR:" in error_buffer.getvalue()


def _test_processed_signature_includes_routing_and_backup() -> None:
    from ..core.processed_index import build_pipeline_signature
    from ..core.settings_model import AppSettings

    ko_settings = AppSettings()
    ko_settings.classification.enabled = True
    ko_settings.classification.auto_folder = True
    ko_settings.ui.language = "ko"

    en_settings = AppSettings.from_dict(ko_settings.to_dict())
    en_settings.ui.language = "en"

    backup_settings = AppSettings.from_dict(ko_settings.to_dict())
    backup_settings.create_backup = True

    assert build_pipeline_signature(ko_settings) != build_pipeline_signature(en_settings)
    assert build_pipeline_signature(ko_settings) != build_pipeline_signature(backup_settings)
