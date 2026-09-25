"""numpy <-> Qt image conversions for the crop editor."""

import cv2

import numpy as np
from PyQt6.QtGui import QImage, QPixmap

def numpy_to_qpixmap(image: np.ndarray) -> QPixmap:
    """Convert numpy array to QPixmap."""
    if len(image.shape) == 2:
        gray = np.ascontiguousarray(image)
        height, width = gray.shape
        bytes_per_line = width
        qimage = QImage(
            gray.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_Grayscale8,
        )
    else:
        height, width, channels = image.shape
        if channels == 4:
            rgba = np.ascontiguousarray(image)
            bytes_per_line = 4 * width
            qimage = QImage(
                rgba.tobytes(),
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGBA8888,
            )
        else:
            image_rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            bytes_per_line = 3 * width
            qimage = QImage(
                image_rgb.tobytes(),
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
    
    return QPixmap.fromImage(qimage.copy())
