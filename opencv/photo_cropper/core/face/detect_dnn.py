#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DNN (SSD/Caffe) face detection backend.

Single responsibility: run the pre-loaded DNN net over an image and
return face rectangles with NMS. Model downloading and net loading live
in :mod:`.model_store`; orchestration lives in :mod:`.detector`.
"""

from typing import Any, List

import cv2
import numpy as np

from .types import FaceRect


def detect_faces_dnn(
    image: np.ndarray,
    dnn_net: Any,
    *,
    min_face_size: int = 30,
    confidence_threshold: float = 0.55,
) -> List[FaceRect]:
    """Detect faces using OpenCV DNN (SSD/Caffe)."""
    if dnn_net is None:
        return []

    src = image
    h, w = src.shape[:2]
    scale = 1.0
    max_dim = 1000
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        src = cv2.resize(src, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    sh, sw = src.shape[:2]
    blob = cv2.dnn.blobFromImage(
        src,
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
        swapRB=False,
        crop=False,
    )

    dnn_net.setInput(blob)
    detections = dnn_net.forward()
    if detections is None or detections.size == 0:
        return []

    faces: List[FaceRect] = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence < confidence_threshold:
            continue

        box = detections[0, 0, i, 3:7] * np.array([sw, sh, sw, sh], dtype=np.float32)
        x1, y1, x2, y2 = box.astype(np.int32)
        x1 = max(0, min(x1, sw - 1))
        y1 = max(0, min(y1, sh - 1))
        x2 = max(0, min(x2, sw))
        y2 = max(0, min(y2, sh))
        bw = max(0, x2 - x1)
        bh = max(0, y2 - y1)
        if bw < min_face_size or bh < min_face_size:
            continue

        if scale != 1.0:
            x1 = int(x1 / scale)
            y1 = int(y1 / scale)
            bw = int(bw / scale)
            bh = int(bh / scale)

        faces.append(
            FaceRect(
                x=x1,
                y=y1,
                width=bw,
                height=bh,
                confidence=confidence,
            )
        )

    if len(faces) <= 1:
        return faces

    boxes = [[f.x, f.y, f.width, f.height] for f in faces]
    confidences = [float(f.confidence) for f in faces]
    idxs = cv2.dnn.NMSBoxes(
        boxes,
        confidences,
        score_threshold=confidence_threshold,
        nms_threshold=0.3,
    )
    if idxs is None or len(idxs) == 0:
        return faces

    kept = []
    for idx in np.array(idxs).reshape(-1):
        if 0 <= int(idx) < len(faces):
            kept.append(faces[int(idx)])
    return kept


__all__ = ['detect_faces_dnn']
