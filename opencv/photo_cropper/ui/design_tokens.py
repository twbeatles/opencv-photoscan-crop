#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared design tokens for the Photo Cropper desktop UI.

Single source of truth for spacing, control sizing, typography, semantic
colors, and window sizing. Pages and builders must reuse these values
instead of hardcoding ad-hoc numbers or colors (see DESKTOP_UI_DESIGN_RULES).
"""

from __future__ import annotations

# --- Spacing scale (px). Use only these steps. ---
SPACE_XXS = 4
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

# --- Layout ---
PAGE_MARGIN = 24
SECTION_GAP = 24
GROUP_GAP = 16
ROW_GAP = 12
CONTROL_GAP = 8
CARD_RADIUS = 8

# --- Control heights ---
CONTROL_HEIGHT_SM = 30
CONTROL_HEIGHT_MD = 32
CONTROL_HEIGHT_LG = 36

# --- Typography (px) ---
FONT_SIZE_CAPTION = 11
FONT_SIZE_SECONDARY = 12
FONT_SIZE_BODY = 13
FONT_SIZE_SECTION = 16
FONT_SIZE_PAGE_TITLE = 22

FONT_FAMILY_FALLBACK = (
    "'Pretendard', 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
)

# --- Window sizing (ktrain-style: fit into available screen geometry) ---
DEFAULT_WINDOW_WIDTH = 1100
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 640
MIN_WINDOW_HEIGHT = 560
SCREEN_MARGIN = 40
SETTINGS_PANEL_MAX_WIDTH = 400
NAV_RAIL_WIDTH = 180

# --- Semantic colors (theme-agnostic neutrals for minimal QSS only) ---
# Accent/status colors always come from qfluentwidgets theme tokens or
# ui/styles/themes.py palettes — never hardcode new hex colors in pages.
BADGE_NEUTRAL_BG = "rgba(128, 128, 128, 0.2)"
BADGE_RADIUS = 4

# --- Brand accent (single primary accent for the whole app) ---
BRAND_ACCENT = "#4C7DD9"


SPLITTER_HANDLE_QSS = """
QSplitter::handle { background: transparent; }
QSplitter::handle:horizontal { width: 6px; margin: 0 2px; }
QSplitter::handle:vertical { height: 6px; margin: 2px 0; }
"""

NAV_LIST_QSS = """
QListWidget {
    border: none;
    border-right: 1px solid rgba(128, 128, 128, 0.25);
    padding: 10px 8px;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 0;
}
QListWidget::item:selected {
    font-weight: bold;
}
"""


def status_badge_qss() -> str:
    """Neutral status badge (no hardcoded accent colors)."""
    return (
        f"background-color: {BADGE_NEUTRAL_BG}; "
        f"border-radius: {BADGE_RADIUS}px; "
        f"padding: 2px {SPACE_XS}px; "
        f"margin: 0 {SPACE_XXS}px;"
    )


def preferred_window_size(avail_width: int, avail_height: int) -> tuple[int, int]:
    """Default window size clamped to the available screen geometry."""
    width = min(
        DEFAULT_WINDOW_WIDTH,
        max(MIN_WINDOW_WIDTH, avail_width - SCREEN_MARGIN),
    )
    height = min(
        DEFAULT_WINDOW_HEIGHT,
        max(MIN_WINDOW_HEIGHT, avail_height - SCREEN_MARGIN),
    )
    return width, height


__all__ = [
    "SPACE_XXS",
    "SPACE_XS",
    "SPACE_SM",
    "SPACE_MD",
    "SPACE_LG",
    "SPACE_XL",
    "PAGE_MARGIN",
    "SECTION_GAP",
    "GROUP_GAP",
    "ROW_GAP",
    "CONTROL_GAP",
    "CARD_RADIUS",
    "CONTROL_HEIGHT_SM",
    "CONTROL_HEIGHT_MD",
    "CONTROL_HEIGHT_LG",
    "FONT_SIZE_CAPTION",
    "FONT_SIZE_SECONDARY",
    "FONT_SIZE_BODY",
    "FONT_SIZE_SECTION",
    "FONT_SIZE_PAGE_TITLE",
    "FONT_FAMILY_FALLBACK",
    "DEFAULT_WINDOW_WIDTH",
    "DEFAULT_WINDOW_HEIGHT",
    "MIN_WINDOW_WIDTH",
    "MIN_WINDOW_HEIGHT",
    "SCREEN_MARGIN",
    "SETTINGS_PANEL_MAX_WIDTH",
    "NAV_RAIL_WIDTH",
    "BADGE_NEUTRAL_BG",
    "BADGE_RADIUS",
    "BRAND_ACCENT",
    "SPLITTER_HANDLE_QSS",
    "NAV_LIST_QSS",
    "status_badge_qss",
    "preferred_window_size",
]
