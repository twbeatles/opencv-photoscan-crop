"""numpy <-> Qt image conversions for the preview."""

from typing import Optional

import numpy as np
from PyQt6.QtGui import QImage, QPixmap

def numpy_to_qimage(image: Optional[np.ndarray]) -> QImage:
    """
    Convert numpy array to QImage.
    
    Args:
        image: OpenCV image (BGR or Grayscale)
        
    Returns:
        QImage
    """
    if image is None:
        return QImage()
    
    if len(image.shape) == 2:
        # Grayscale - make a copy for memory safety
        h, w = image.shape
        image_copy = np.ascontiguousarray(image)
        bytes_per_line = w
        qimage = QImage(
            image_copy.tobytes(),
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_Grayscale8,
        )
        # Copy to ensure QImage owns its data
        return qimage.copy()
    else:
        # Color
        h, w, c = image.shape
        color = np.ascontiguousarray(image)
        if c == 4:
            bytes_per_line = 4 * w
            qimage = QImage(
                color.tobytes(),
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGBA8888,
            )
        else:
            bytes_per_line = 3 * w
            qimage = QImage(
                color.tobytes(),
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_BGR888,
            )
        # Copy to ensure QImage owns its data
        return qimage.copy()


def numpy_to_qpixmap(image: Optional[np.ndarray]) -> QPixmap:
    """Convert numpy array to QPixmap."""
    qimage = numpy_to_qimage(image)
    return QPixmap.fromImage(qimage)
