#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n package for Photo Cropper.
"""

from .catalog import (
    FALLBACK_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TranslationManager,
    detect_system_language,
    get_category_folder_defaults,
    get_translator,
    t,
    set_language,
    get_current_language
)

__all__ = [
    'FALLBACK_LANGUAGE',
    'SUPPORTED_LANGUAGES',
    'TranslationManager',
    'detect_system_language',
    'get_category_folder_defaults',
    'get_translator',
    't',
    'set_language',
    'get_current_language'
]
