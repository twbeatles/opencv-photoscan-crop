#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n package for Photo Cropper.
"""

from .translations import (
    TranslationManager,
    get_translator,
    t,
    set_language,
    get_current_language
)

__all__ = [
    'TranslationManager',
    'get_translator',
    't',
    'set_language',
    'get_current_language'
]
