#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark harness for photo-boundary detection precision.

Label format (JSON):
{
  "version": 1,
  "items": [
    {"file": "sample1.jpg", "has_photo": true, "quad": [[x,y],[x,y],[x,y],[x,y]]},
    {"file": "sample2.jpg", "has_photo": false}
  ]
}
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from .core.image import ImageProcessor
from .core.settings_model import AppSettings


def _coerce_quad(value: Any) -> Optional[np.ndarray]:
    if value is None:
        return None
    try:
        quad = np.array(value, dtype=np.float32).reshape((4, 2))
        return quad
    except Exception:
        return None


def _quad_iou(quad_a: np.ndarray, quad_b: np.ndarray, shape: tuple[int, int]) -> float:
    h, w = shape
    if h <= 0 or w <= 0:
        return 0.0
    mask_a = np.zeros((h, w), dtype=np.uint8)
    mask_b = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask_a, [quad_a.astype(np.int32)], 255)
    cv2.fillPoly(mask_b, [quad_b.astype(np.int32)], 255)
    inter = np.logical_and(mask_a > 0, mask_b > 0).sum()
    union = np.logical_or(mask_a > 0, mask_b > 0).sum()
    if union <= 0:
        return 0.0
    return float(inter) / float(union)


def load_labels(labels_path: str) -> List[Dict[str, Any]]:
    with open(labels_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("labels JSON must contain an 'items' list")

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"labels[{idx}] must be an object")
        file_name = str(item.get("file", "")).strip()
        if not file_name:
            raise ValueError(f"labels[{idx}].file is required")
        if "has_photo" not in item:
            raise ValueError(f"labels[{idx}].has_photo is required")
        has_photo_value = item.get("has_photo")
        if not isinstance(has_photo_value, bool):
            raise ValueError(f"labels[{idx}].has_photo must be boolean")
        has_photo = bool(has_photo_value)
        quad = _coerce_quad(item.get("quad"))
        if has_photo and quad is None:
            raise ValueError(f"labels[{idx}] requires quad when has_photo=true")
        normalized.append(
            {
                "file": file_name,
                "has_photo": has_photo,
                "quad": quad,
            }
        )
    return normalized


def run_benchmark(
    images_dir: str,
    labels_path: str,
    *,
    report_path: Optional[str] = None,
    settings: Optional[AppSettings] = None,
    processor_factory: Optional[Callable[[], ImageProcessor]] = None,
) -> Dict[str, Any]:
    labels = load_labels(labels_path)
    settings = settings or AppSettings()

    if processor_factory is not None:
        processor = processor_factory()
    else:
        processor = ImageProcessor(
            settings.algorithm,
            settings.processing,
            settings.advanced,
            settings.performance,
            settings.debug,
        )

    total = len(labels)
    photo_total = 0
    no_photo_total = 0
    success_on_photo = 0
    false_positives = 0
    ious: List[float] = []
    stage_distribution: Dict[str, int] = {}
    missing_files: List[str] = []
    per_item: List[Dict[str, Any]] = []

    for item in labels:
        file_name = item["file"]
        image_path = os.path.join(images_dir, file_name)
        if not os.path.exists(image_path):
            missing_files.append(file_name)
            per_item.append(
                {
                    "file": file_name,
                    "status": "missing",
                    "has_photo": bool(item["has_photo"]),
                }
            )
            continue

        result = processor.process_image(image_path)
        predicted_has_photo = bool(result.success and result.contour_points is not None)

        stage_name = (
            result.detection_stage.value if result.detection_stage is not None else "None"
        )
        stage_distribution[stage_name] = stage_distribution.get(stage_name, 0) + 1

        record: Dict[str, Any] = {
            "file": file_name,
            "has_photo": bool(item["has_photo"]),
            "predicted_has_photo": predicted_has_photo,
            "detection_stage": stage_name,
            "confidence": float(result.confidence or 0.0),
        }

        if item["has_photo"]:
            photo_total += 1
            if predicted_has_photo:
                success_on_photo += 1
                gt_quad = item["quad"]
                pred_quad = np.array(result.contour_points, dtype=np.float32).reshape((4, 2))
                image = processor.load_image(image_path)
                if image is not None:
                    h, w = image.shape[:2]
                    iou = _quad_iou(gt_quad, pred_quad, (h, w))
                else:
                    iou = 0.0
            else:
                iou = 0.0
            ious.append(float(iou))
            record["iou"] = float(iou)
        else:
            no_photo_total += 1
            if predicted_has_photo:
                false_positives += 1

        per_item.append(record)

    success_rate = (success_on_photo / photo_total) if photo_total else 0.0
    false_positive_rate = (false_positives / no_photo_total) if no_photo_total else 0.0
    mean_iou = float(sum(ious) / len(ious)) if ious else 0.0
    median_iou = float(statistics.median(ious)) if ious else 0.0
    p90_iou = float(np.percentile(np.array(ious, dtype=np.float32), 90)) if ious else 0.0

    report: Dict[str, Any] = {
        "summary": {
            "total": total,
            "photo_total": photo_total,
            "no_photo_total": no_photo_total,
            "missing_files": len(missing_files),
        },
        "metrics": {
            "success_rate": float(success_rate),
            "mean_iou": float(mean_iou),
            "median_iou": float(median_iou),
            "p90_iou": float(p90_iou),
            "false_positive_rate": float(false_positive_rate),
            "stage_distribution": stage_distribution,
        },
        "missing_files": missing_files,
        "items": per_item,
    }

    if report_path:
        os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PhotoCropper benchmark harness")
    parser.add_argument("--images", required=True, help="Directory with benchmark images")
    parser.add_argument("--labels", required=True, help="Labels JSON path")
    parser.add_argument("--report", required=False, help="Output report JSON path")
    parser.add_argument(
        "--detect-mode",
        choices=["fast", "balanced", "accurate"],
        default="accurate",
        help="Detection mode for benchmark runs",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    settings = AppSettings()
    settings.algorithm.detection_mode = args.detect_mode

    report = run_benchmark(
        args.images,
        args.labels,
        report_path=args.report,
        settings=settings,
    )
    metrics = report["metrics"]
    print(
        "Benchmark metrics: "
        f"success_rate={metrics['success_rate']:.4f}, "
        f"mean_iou={metrics['mean_iou']:.4f}, "
        f"median_iou={metrics['median_iou']:.4f}, "
        f"p90_iou={metrics['p90_iou']:.4f}, "
        f"false_positive_rate={metrics['false_positive_rate']:.4f}"
    )
    if args.report:
        print(f"Report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
