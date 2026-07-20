#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composable photo-boundary detection engine.

``DetectionPipeline`` owns detection mixins. Mutable state (settings, kernels,
CLAHE caches) and monkeypatched hooks live on the host ``ImageProcessor``:

* Reads prefer host *instance* callables (test monkeypatches), then pipeline
  methods, then host attributes.
* Writes always go to the host so caches stay shared.
"""

from __future__ import annotations

from typing import Any

from ._detect_contours import ImageContourSelectionMixin
from ._detect_loading import ImageLoadAndClaheMixin
from ._detect_pipeline import ImageDetectionPipelineMixin
from ._detect_stages import ImageDetectionStageMixin


class DetectionPipeline(
    ImageLoadAndClaheMixin,
    ImageContourSelectionMixin,
    ImageDetectionStageMixin,
    ImageDetectionPipelineMixin,
):
    """Detection-only composition root used by ``ImageProcessor``."""

    MIN_CONTOUR_AREA = 100
    MIN_CROP_SIZE = 50
    PREVIEW_DETECTION_MAX_MP = 8.0

    # Facade wrappers that call back into this pipeline must not be re-entered.
    # Detection hooks (find_best_contour, etc.) remain overridable for selftests.
    _HOST_CALLABLE_SKIP = frozenset(
        {
            "detection",
            "load_image",
            "process_image",
            "process_preview",
            "update_settings",
            "save_image",
            "_process_loaded_image",
        }
    )

    def __init__(self, host: Any):
        object.__setattr__(self, "_host", host)

    def __getattribute__(self, name: str) -> Any:
        if name in ("_host", "__class__", "__dict__", "__weakref__", "_HOST_CALLABLE_SKIP"):
            return object.__getattribute__(self, name)

        host = object.__getattribute__(self, "_host")
        skip = object.__getattribute__(self, "_HOST_CALLABLE_SKIP")
        # Prefer host instance-level callables (monkeypatches from selftests),
        # except facade wrappers that would recurse into this pipeline.
        try:
            host_dict = object.__getattribute__(host, "__dict__")
            if (
                name in host_dict
                and callable(host_dict[name])
                and name not in skip
            ):
                return host_dict[name]
        except Exception:
            pass

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(host, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_host":
            object.__setattr__(self, name, value)
            return
        # Keep shared runtime state on the host processor.
        host = object.__getattribute__(self, "_host")
        setattr(host, name, value)


__all__ = ["DetectionPipeline"]
