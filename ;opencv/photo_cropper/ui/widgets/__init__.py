# Widgets module
"""
Reusable PyQt6 widgets.
"""

from .toast_notification import ToastNotification, ToastManager

try:
    from .settings import SettingsPanel
except Exception:  # pragma: no cover - optional runtime dependency chain
    SettingsPanel = None  # type: ignore[assignment]

try:
    from .preview_widget import ImagePreviewWidget
except Exception:  # pragma: no cover - optional runtime dependency chain
    ImagePreviewWidget = None  # type: ignore[assignment]

try:
    from .progress_dialog import ProgressDialog
except Exception:  # pragma: no cover - optional runtime dependency chain
    ProgressDialog = None  # type: ignore[assignment]

try:
    from .histogram_widget import HistogramWidget
except Exception:  # pragma: no cover - optional runtime dependency chain
    HistogramWidget = None  # type: ignore[assignment]

__all__ = [
    'ToastNotification',
    'ToastManager',
    'SettingsPanel',
    'ImagePreviewWidget',
    'ProgressDialog',
    'HistogramWidget',
]
