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
SETTINGS_PANEL_MIN_WIDTH = 280
NAV_RAIL_WIDTH = 168
SPLITTER_HANDLE_WIDTH = 8
PATH_LABEL_MIN_WIDTH = 72

# --- Semantic colors (theme-agnostic neutrals for minimal QSS only) ---
# Accent/status colors always come from qfluentwidgets theme tokens or
# ui/styles/themes.py palettes — never hardcode new hex colors in pages.
BADGE_NEUTRAL_BG = "rgba(128, 128, 128, 0.2)"
BADGE_RADIUS = 4

# Status tints (success/error) shared by badges and validation borders.
STATUS_SUCCESS = "#2e9d5b"
STATUS_ERROR = "#cf222e"
BADGE_SUCCESS_BG = "rgba(46, 157, 91, 0.18)"
HAIRLINE = "rgba(128, 128, 128, 0.25)"
HOVER_BG = "rgba(128, 128, 128, 0.10)"
SELECTED_BG = "rgba(128, 128, 128, 0.20)"

# --- Brand accent (single primary accent for the whole app) ---
BRAND_ACCENT = "#4C7DD9"


SPLITTER_HANDLE_QSS = """
QSplitter::handle { background: transparent; }
"""

NAV_LIST_QSS = f"""
QListWidget {{
    border: none;
    border-right: 1px solid {HAIRLINE};
    background: transparent;
    padding: {SPACE_XS}px;
    outline: none;
}}
QListWidget::item {{
    padding: {SPACE_XS}px {SPACE_SM}px;
    border-radius: {CARD_RADIUS}px;
    margin: 2px 0;
    color: palette(text);
}}
QListWidget::item:hover {{ background: {HOVER_BG}; }}
QListWidget::item:selected {{
    background: {SELECTED_BG};
    font-weight: 600;
}}
"""

CARD_QSS = f"""
QFrame#workbenchCard {{
    border: 1px solid {HAIRLINE};
    border-radius: {CARD_RADIUS}px;
}}
"""

COLLAPSIBLE_HEADER_QSS = f"""
QFrame#collapsibleHeader {{
    border: none;
    border-bottom: 1px solid {HAIRLINE};
}}
QFrame#collapsibleHeader:hover {{ background: {HOVER_BG}; }}
"""

INVALID_INPUT_QSS = (
    f"QLineEdit {{ border: 1px solid {STATUS_ERROR}; border-radius: {BADGE_RADIUS}px; }}"
)


def status_badge_qss(kind: str = "neutral") -> str:
    """Status-bar badge; ``kind`` is ``neutral`` or ``success``."""
    background = BADGE_SUCCESS_BG if kind == "success" else BADGE_NEUTRAL_BG
    color = f"color: {STATUS_SUCCESS}; " if kind == "success" else ""
    return (
        f"background-color: {background}; {color}"
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
    "SETTINGS_PANEL_MIN_WIDTH",
    "NAV_RAIL_WIDTH",
    "SPLITTER_HANDLE_WIDTH",
    "PATH_LABEL_MIN_WIDTH",
    "STATUS_SUCCESS",
    "STATUS_ERROR",
    "BADGE_SUCCESS_BG",
    "HAIRLINE",
    "HOVER_BG",
    "SELECTED_BG",
    "BADGE_NEUTRAL_BG",
    "BADGE_RADIUS",
    "BRAND_ACCENT",
    "SPLITTER_HANDLE_QSS",
    "NAV_LIST_QSS",
    "CARD_QSS",
    "COLLAPSIBLE_HEADER_QSS",
    "INVALID_INPUT_QSS",
    "status_badge_qss",
    "preferred_window_size",
]
