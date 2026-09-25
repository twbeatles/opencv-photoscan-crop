#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
# -*- coding: utf-8 -*-
"""Manual-extract/contour self-tests."""

from __future__ import annotations


def _test_manual_extract_session_runner_empty() -> None:
    import tempfile
    from threading import Event

    from ..core.manual_extract import ManualExtractSessionRunner

    calls = {"progress": 0, "log": 0, "completed": 0, "results": None}

    def on_progress(_progress):
        calls["progress"] += 1

    def on_log(_message: str, _level: str):
        calls["log"] += 1

    def on_complete(_progress, results):
        calls["completed"] += 1
        calls["results"] = results

    runner = ManualExtractSessionRunner()
    with tempfile.TemporaryDirectory(prefix="photocropper_manual_runner_") as td:
        runner.run(
            output_path=td,
            input_root=td,
            files=[],
            contours_norm={},
            settings_snapshot={},
            stop_event=Event(),
            on_progress=on_progress,
            on_log=on_log,
            on_complete=on_complete,
        )

    assert calls["progress"] >= 2
    assert calls["log"] == 0
    assert calls["completed"] == 1
    assert calls["results"] == []


def _test_contour_utils_roundtrip() -> None:
    import numpy as np

    from ..core.manual_extract import (
        normalize_contour_points,
        denormalize_contour_points,
        scale_contour_to_preview,
    )
    from ..core.image import CropResult

    pts = np.array([[10, 20], [90, 20], [90, 80], [10, 80]], dtype=np.float32)
    normalized = normalize_contour_points(pts, (100, 100, 3))
    assert normalized is not None
    restored = denormalize_contour_points(normalized, (100, 100, 3))
    assert restored is not None
    assert np.allclose(restored, pts, atol=1.0)

    preview = np.zeros((200, 300, 3), dtype=np.uint8)
    crop_result = CropResult(
        success=True,
        contour_points=pts,
        original_size=(100, 100),
    )
    scaled = scale_contour_to_preview(preview, crop_result)
    assert scaled is not None
    assert np.allclose(scaled[0], [30.0, 40.0], atol=1.0)


def _test_manual_preview_shared_crop_mode() -> None:
    from types import SimpleNamespace

    import numpy as np

    from ..core.manual_extract import crop_manual_contour
    from ..core.settings_model import AppSettings
    from ..ui.main.actions.preview import PreviewActions

    image = np.zeros((110, 140, 3), dtype=np.uint8)
    image[25:86, 35:96] = (15, 120, 240)
    contour = np.array(
        [[35, 25], [95, 25], [95, 85], [35, 85]],
        dtype=np.float32,
    )

    settings = AppSettings()
    settings.advanced.perspective_correct = False
    state = SimpleNamespace(
        settings=settings,
        last_original=image,
    )
    services = SimpleNamespace(
        image_processor=SimpleNamespace(_apply_post_processing=lambda img: img)
    )

    actions = PreviewActions(
        state=state,
        refs=SimpleNamespace(),
        services=services,
        signals=SimpleNamespace(),
    )

    preview_image = actions._build_manual_preview_image(contour)
    saved_image = crop_manual_contour(
        image,
        contour,
        perspective_correct=False,
        use_gpu=False,
    )

    assert preview_image is not None
    assert saved_image is not None
    assert preview_image.shape == saved_image.shape
    assert np.array_equal(preview_image, saved_image)


def _test_find_best_contour_uses_score_edge_map() -> None:
    import cv2
    import numpy as np

    from ..core.image import ImageProcessor
    from ..core.settings_model import AlgorithmSettings

    ip = ImageProcessor(AlgorithmSettings(use_clahe=False))
    mask = np.zeros((220, 220), dtype=np.uint8)
    cv2.rectangle(mask, (30, 30), (190, 190), 255, -1)
    score_map = np.zeros_like(mask)

    captured = {"edge": None}
    original_score = ip._score_quad

    def _spy_score(quad, image_area, edge_image=None, image_shape=None, **kwargs):
        captured["edge"] = edge_image
        return original_score(
            quad,
            image_area,
            edge_image=edge_image,
            image_shape=image_shape,
            **kwargs,
        )

    ip._score_quad = _spy_score
    _, score_default, _ = ip.find_best_contour(mask, mask.size)
    _, score_ref, _ = ip.find_best_contour(mask, mask.size, score_edge_map=score_map)
    assert captured["edge"] is score_map, "Expected dedicated score edge map to be used"
    assert score_ref < score_default, (
        "Expected lower score when edge support comes from empty reference edge map"
    )


def _test_accurate_mode_global_rerank_prefers_best_stage() -> None:
    import numpy as np

    from ..core.image import ImageProcessor, DetectionStage
    from ..core.settings_model import AlgorithmSettings, ProcessingSettings

    algo = AlgorithmSettings(detection_mode="accurate", use_clahe=False)
    proc = ProcessingSettings(auto_contrast=False)
    ip = ImageProcessor(algo, proc)

    img = np.full((300, 420, 3), 180, dtype=np.uint8)
    quad = np.array([[40, 40], [380, 50], [370, 250], [45, 260]], dtype=np.float32)

    stage_scores = [0.80, 0.83, 0.85, 0.86, 0.95]
    call_state = {"idx": 0}

    ip._accept_stage_candidate = lambda stage, score: True
    ip.detect_edges_multiscale = lambda gray: np.zeros_like(gray)

    def _find_best_contour(*_args, **_kwargs):
        i = call_state["idx"]
        call_state["idx"] += 1
        if i < len(stage_scores):
            score = stage_scores[i]
            return quad.copy(), score, [{"quad": quad.copy(), "score": score}]
        return None, 0.0, []

    ip.find_best_contour = _find_best_contour
    ip._detect_rectangle_by_hough = lambda _edges: quad.copy()
    ip._score_quad = lambda *_args, **_kwargs: 0.90
    ip._apply_post_processing = lambda image: image

    result = ip._process_loaded_image(img, "synthetic.png")
    assert result.success
    assert result.detection_stage == DetectionStage.CORNER_HARRIS
