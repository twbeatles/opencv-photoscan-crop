#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch execution for the Photo Cropper CLI.

Single responsibility: validate I/O, run the batch processor with job
tracking, and map outcomes to process exit codes. Argument parsing lives
in :mod:`.parser`, settings merging in :mod:`.settings_builder`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Optional

try:
    from ..core.settings_model.validation import build_validation_summary, validate_settings
    from ..utils.file_helpers import is_output_inside_input
except ImportError:  # Support direct execution: python photo_cropper/cli.py
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from photo_cropper.core.settings_model.validation import (
        build_validation_summary,
        validate_settings,
    )
    from photo_cropper.utils.file_helpers import is_output_inside_input

from .parser import create_parser
from .settings_builder import build_settings_from_args
from .settings_sources import _resolve_profile_manager

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _validate_io_paths(input_dir: str, output_dir: str, *, recursive: bool = False) -> None:
    if not input_dir:
        raise ValueError("Input directory is required")
    if not output_dir:
        raise ValueError("Output directory is required")
    if not os.path.isdir(input_dir):
        raise ValueError(f"Input directory does not exist: {input_dir}")
    if recursive and is_output_inside_input(input_dir, output_dir):
        raise ValueError(
            "Recursive batch processing cannot use an output directory inside the input directory"
        )


def _list_presets() -> int:
    manager = _resolve_profile_manager()
    names = sorted(manager.list_profiles())
    if not names:
        print("No presets available")
        return 0
    print("Available presets:")
    for name in names:
        print(f"- {name}")
    return 0


def process_batch(args: argparse.Namespace) -> int:
    try:
        from ..core.batch import BatchProcessor
        from ..core.jobs import JobOrchestrator
        from ..core.library import get_library_repository
    except ImportError:
        from photo_cropper.core.batch import BatchProcessor
        from photo_cropper.core.jobs import JobOrchestrator
        from photo_cropper.core.library import get_library_repository

    try:
        settings = build_settings_from_args(args)
        issues = validate_settings(settings)
        if issues:
            raise ValueError(build_validation_summary(issues))
        _validate_io_paths(
            args.input,
            args.output,
            recursive=bool(settings.file_management.recursive_search),
        )
        os.makedirs(args.output, exist_ok=True)
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    processor = BatchProcessor(settings)
    job_orchestrator = None
    job_id: Optional[int] = None

    try:
        job_orchestrator = JobOrchestrator(get_library_repository())
        job_id = job_orchestrator.create_job(
            job_kind="cli_batch",
            input_path=args.input,
            output_path=args.output,
            recipe_name=str(args.preset or ""),
        )
    except Exception as exc:
        logger.warning("CLI job tracking unavailable: %s", exc)
        job_orchestrator = None
        job_id = None

    def on_log(message: str, level: str) -> None:
        level = str(level or "info").lower()
        if level in {"error", "warning"}:
            print(message, file=sys.stderr)
        else:
            print(message)

    def on_complete(progress, results) -> None:
        if job_orchestrator is None or job_id is None:
            return
        try:
            job_orchestrator.finalize_job(
                job_id=job_id,
                progress=progress,
                results=list(results or []),
                settings=settings,
                recipe_name=str(args.preset or ""),
                job_kind="cli_batch",
            )
        except Exception as exc:
            logger.warning("CLI job finalization failed: %s", exc)

    processor.set_callbacks(on_log=on_log, on_complete=on_complete)

    if not processor.start_async(args.input, args.output):
        if job_orchestrator is not None and job_id is not None:
            try:
                job_orchestrator.repository.finalize_job(
                    job_id,
                    status="failed",
                    total_items=0,
                    processed_items=0,
                    success_count=0,
                    partial_count=0,
                    failed_count=0,
                    skipped_count=0,
                    summary={"reason": "start_async_failed"},
                )
            except Exception:
                logger.debug("Failed to finalize rejected CLI job", exc_info=True)
        print("ERROR: Failed to start batch processing", file=sys.stderr)
        return 2

    cancelled = False
    try:
        while processor.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Cancellation requested...")
        processor.request_stop()
        processor.wait_for_completion(timeout=10.0)
        cancelled = True

    progress = processor.progress
    if progress.is_cancelled:
        cancelled = True
    print(
        "Summary: "
        f"processed={progress.processed}, "
        f"success={progress.success}, "
        f"partial_success={getattr(progress, 'partial_success', 0)}, "
        f"failed={progress.failed}, "
        f"skipped={progress.skipped}"
    )

    if bool(getattr(progress, "fatal_error", False)):
        fatal_message = str(getattr(progress, "fatal_message", "") or "")
        if fatal_message:
            print(f"ERROR: {fatal_message}", file=sys.stderr)
        return 1
    if cancelled:
        return 130
    if progress.failed > 0:
        return 1
    if args.strict_partial and int(getattr(progress, "partial_success", 0) or 0) > 0:
        return 1
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    if args.list_presets:
        return _list_presets()

    if not args.input or not args.output:
        parser.error("--input and --output are required unless --list-presets is used")

    return process_batch(args)


__all__ = [
    "_configure_logging",
    "_validate_io_paths",
    "_list_presets",
    "process_batch",
    "main",
]
