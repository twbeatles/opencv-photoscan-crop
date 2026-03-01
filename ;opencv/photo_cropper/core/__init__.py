# Core module
"""
Core processing components for photo cropping.
"""

from .batch_profile_manager import (
    BatchProfile,
    BatchProfileManager,
    get_batch_profile_manager,
)

try:
    from .image_classifier import ImageClassifier, ImageCategory, get_classifier
except Exception:  # pragma: no cover - optional runtime dependency (cv2)
    ImageClassifier = None  # type: ignore[assignment]
    ImageCategory = None  # type: ignore[assignment]
    get_classifier = None  # type: ignore[assignment]

try:
    from .face_detector import FaceDetectionResult, FaceDetector, get_face_detector
except Exception:  # pragma: no cover - optional runtime dependency (cv2)
    FaceDetectionResult = None  # type: ignore[assignment]
    FaceDetector = None  # type: ignore[assignment]
    get_face_detector = None  # type: ignore[assignment]

try:
    from .smart_enhancer import EnhancementPreset, SmartEnhancer, get_smart_enhancer
except Exception:  # pragma: no cover - optional runtime dependency (cv2)
    EnhancementPreset = None  # type: ignore[assignment]
    SmartEnhancer = None  # type: ignore[assignment]
    get_smart_enhancer = None  # type: ignore[assignment]
