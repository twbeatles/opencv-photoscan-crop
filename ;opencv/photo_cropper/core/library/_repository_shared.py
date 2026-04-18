# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_json_loads(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        loaded = json.loads(str(value or ""))
    except Exception:
        return default
    return loaded if isinstance(loaded, type(default)) else default


def compute_perceptual_hash(file_path: str) -> str:
    try:
        import cv2
        import numpy as np

        data = np.fromfile(file_path, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return ""
        image = cv2.resize(image, (32, 32))
        image = image.astype("float32")
        dct = cv2.dct(image)
        low = dct[:8, :8]
        median = float(low[1:, :].mean()) if low.size > 1 else 0.0
        bits = low > median
        return "".join("1" if bool(flag) else "0" for flag in bits.flatten())
    except Exception:
        return ""
