"""Reset process-wide singletons for isolated tests and agent sandboxes."""

from __future__ import annotations


def reset_library_repository_for_tests() -> None:
    from photo_cropper.core.library.repository import (
        reset_library_repository_for_tests as _reset,
    )

    _reset()


def reset_classifier_for_tests() -> None:
    from photo_cropper.core.image_classifier import reset_classifier_for_tests as _reset

    _reset()


def reset_face_detector_for_tests() -> None:
    from photo_cropper.core.face.detector import reset_face_detector_for_tests as _reset

    _reset()


def reset_smart_enhancer_for_tests() -> None:
    from photo_cropper.core.smart_enhancer import reset_smart_enhancer_for_tests as _reset

    _reset()


def reset_processing_logger_for_tests() -> None:
    from photo_cropper.utils.processing_log import reset_processing_logger_for_tests as _reset

    _reset()


def reset_system_notification_for_tests() -> None:
    from photo_cropper.utils.system_notification import (
        reset_system_notification_for_tests as _reset,
    )

    _reset()


def reset_translation_manager_for_tests() -> None:
    from photo_cropper.i18n.catalog.manager import (
        reset_translation_manager_for_tests as _reset,
    )

    _reset()


def reset_all_singletons_for_tests() -> None:
    """Best-effort reset of all known global singletons."""
    reset_library_repository_for_tests()
    reset_classifier_for_tests()
    reset_face_detector_for_tests()
    reset_smart_enhancer_for_tests()
    reset_processing_logger_for_tests()
    reset_system_notification_for_tests()
    reset_translation_manager_for_tests()


__all__ = [
    "reset_all_singletons_for_tests",
    "reset_classifier_for_tests",
    "reset_face_detector_for_tests",
    "reset_library_repository_for_tests",
    "reset_processing_logger_for_tests",
    "reset_smart_enhancer_for_tests",
    "reset_system_notification_for_tests",
    "reset_translation_manager_for_tests",
]