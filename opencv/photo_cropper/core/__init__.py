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
    from .face import FaceDetectionResult, FaceDetector, get_face_detector
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

try:
    from .manual_extract import (
        ManualExtractOutcome,
        ManualExtractProcessor,
        ManualExtractSessionRunner,
        scale_contour_to_preview,
        normalize_contour_points,
        denormalize_contour_points,
        is_boundary_detection_failure,
        collect_boundary_failed_files,
    )
except Exception:  # pragma: no cover - optional runtime dependency (cv2)
    ManualExtractOutcome = None  # type: ignore[assignment]
    ManualExtractProcessor = None  # type: ignore[assignment]
    ManualExtractSessionRunner = None  # type: ignore[assignment]
    scale_contour_to_preview = None  # type: ignore[assignment]
    normalize_contour_points = None  # type: ignore[assignment]
    denormalize_contour_points = None  # type: ignore[assignment]
    is_boundary_detection_failure = None  # type: ignore[assignment]
    collect_boundary_failed_files = None  # type: ignore[assignment]

try:
    from .watch_mode import WatchModeCoordinator, WatchStartResult
except Exception:  # pragma: no cover - optional runtime dependency (PyQt6)
    WatchModeCoordinator = None  # type: ignore[assignment]
    WatchStartResult = None  # type: ignore[assignment]
