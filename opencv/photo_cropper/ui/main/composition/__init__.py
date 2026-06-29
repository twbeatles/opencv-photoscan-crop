"""MainWindow composition helpers."""

from .actions import wire_window_actions
from .layout import build_main_window_shell

__all__ = ["build_main_window_shell", "wire_window_actions"]
