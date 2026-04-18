# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import os
import cv2
import numpy as np
import logging
import traceback
import json
import time
import math
from typing import Optional, Tuple, List, Dict, Any

from ..settings_model import (
    AlgorithmSettings,
    ProcessingSettings,
    AdvancedProcessingSettings,
    PerformanceSettings,
    DebugSettings,
)
from ..advanced import AdvancedImageProcessor, GPUAccelerator
from .types import CropResult, DetectionStage, PreviewProcessResult

logger = logging.getLogger(__name__)


class ImageDebugMixin:
    def _debug_enabled(self: Any, debug_dir: Optional[str]) -> bool:
        return bool(self.debug.enabled and debug_dir is not None)
    def _resolve_debug_root(self: Any, base_output_dir: Optional[str]) -> str:
        """
        Resolve debug root directory.

        If DebugSettings.output_dir is set, use it.
        Else if base_output_dir is a non-empty string, use {base_output_dir}/_debug.
        Else use %TEMP%/PhotoCropper/_debug.
        """
        if self.debug.output_dir:
            root = self.debug.output_dir
        elif base_output_dir:
            root = os.path.join(base_output_dir, "_debug")
        else:
            temp = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expanduser("~")
            root = os.path.join(temp, "PhotoCropper", "_debug")
        os.makedirs(root, exist_ok=True)
        return root
    def _prune_debug_root(self: Any, root: str):
        """Best-effort pruning of debug folders under root based on mtime."""
        try:
            max_keep = int(self.debug.max_files) if self.debug.max_files else 0
            if max_keep <= 0:
                return
            entries = []
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if not os.path.isdir(path):
                    continue
                try:
                    mtime = os.path.getmtime(path)
                except Exception:
                    mtime = 0
                entries.append((mtime, path))
            if len(entries) <= max_keep:
                return
            entries.sort(key=lambda x: x[0])  # oldest first
            for _, path in entries[: max(0, len(entries) - max_keep)]:
                try:
                    # Remove directory recursively (best-effort)
                    for root_dir, dirs, files in os.walk(path, topdown=False):
                        for f in files:
                            try:
                                os.remove(os.path.join(root_dir, f))
                            except Exception:
                                pass
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root_dir, d))
                            except Exception:
                                pass
                    os.rmdir(path)
                except Exception:
                    pass
        except Exception:
            pass
    @staticmethod
    def _save_debug_image(path: str, image: np.ndarray) -> bool:
        """Save image to path with Unicode support (PNG)."""
        try:
            ext = os.path.splitext(path)[1].lower() or ".png"
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                ext = ".png"
                path = path + ext
            ok, buf = cv2.imencode(ext, image)
            if not ok:
                return False
            buf.tofile(path)
            return True
        except Exception:
            return False
    def _draw_candidates_overlay(
        self: Any,
        base_bgr: np.ndarray,
        candidates: List[dict],
        final_quad: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        overlay = base_bgr.copy()
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
        ]
        for i, c in enumerate(candidates[:10]):
            quad = c.get("quad")
            if quad is None:
                continue
            pts = self.order_points(np.array(quad, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))
            color = colors[i % len(colors)]
            cv2.polylines(overlay, [pts], True, color, 2)
            cv2.putText(
                overlay,
                f"{i+1}:{c.get('score', 0.0):.2f}",
                tuple(pts[0][0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )
        if final_quad is not None:
            pts = self.order_points(np.array(final_quad, dtype=np.float32)).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(overlay, [pts], True, (0, 180, 255), 3)
        return overlay
