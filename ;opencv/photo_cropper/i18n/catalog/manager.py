#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization manager for Photo Cropper.
"""

from __future__ import annotations

import importlib
import locale
import logging
import os
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("ko", "en", "ja", "zh", "es")
FALLBACK_LANGUAGE = "en"
DEFAULT_CATEGORY = ("portrait", "landscape", "document", "blackwhite", "other")


def detect_system_language() -> str:
    """Detect language from system locale."""

    def _extract_lang(locale_str: Optional[str]) -> str:
        if not locale_str:
            return ""
        normalized = locale_str.split(":")[0].split(".")[0].replace("-", "_")
        return normalized.split("_")[0].lower()

    try:
        locale_lang = None
        try:
            locale_lang = locale.getlocale()[0]
        except Exception:
            locale_lang = None

        lang_code = _extract_lang(locale_lang)
        if not lang_code:
            for env_key in ("LC_ALL", "LANG", "LANGUAGE"):
                lang_code = _extract_lang(os.environ.get(env_key))
                if lang_code:
                    break

        if lang_code in SUPPORTED_LANGUAGES:
            return lang_code
        if lang_code in {"zh-cn", "zh-hans", "zh-tw", "zh-hant"}:
            return "zh"
    except Exception as exc:
        logger.debug("Could not detect system locale: %s", exc)

    return FALLBACK_LANGUAGE


def _load_locale_module(language: str):
    module_name = f"{__package__}.locales.{language}"
    return importlib.import_module(module_name)


def _load_translations() -> Dict[str, Dict[str, str]]:
    translations: Dict[str, Dict[str, str]] = {}
    for language in SUPPORTED_LANGUAGES:
        try:
            module = _load_locale_module(language)
            raw = getattr(module, "TRANSLATIONS", {})
            translations[language] = dict(raw if isinstance(raw, dict) else {})
        except Exception as exc:
            logger.error("Failed to load locale module '%s': %s", language, exc)
            translations[language] = {}
    return translations


def _load_category_defaults() -> Dict[str, Dict[str, str]]:
    defaults: Dict[str, Dict[str, str]] = {}
    for language in SUPPORTED_LANGUAGES:
        try:
            module = _load_locale_module(language)
            raw = getattr(module, "CATEGORY_FOLDER_DEFAULTS", {})
            mapping = dict(raw if isinstance(raw, dict) else {})
            defaults[language] = {
                key: str(mapping.get(key, key)).strip() or key
                for key in DEFAULT_CATEGORY
            }
        except Exception as exc:
            logger.error("Failed to load category defaults '%s': %s", language, exc)
            defaults[language] = {key: key for key in DEFAULT_CATEGORY}
    return defaults


def _load_language_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for language in SUPPORTED_LANGUAGES:
        try:
            module = _load_locale_module(language)
            display_name = str(getattr(module, "LANGUAGE_NAME", language)).strip()
            names[language] = display_name or language
        except Exception:
            names[language] = language
    return names


class TranslationManager:
    """Singleton translation manager."""

    _instance: Optional["TranslationManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._translations = _load_translations()
        self._category_defaults = _load_category_defaults()
        self._language_names = _load_language_names()
        self._fallback_language = FALLBACK_LANGUAGE
        self._current_language = detect_system_language()
        if self._current_language not in self._translations:
            self._current_language = self._fallback_language
        self._on_language_change: list[Callable[[str], None]] = []
        self._initialized = True

    @property
    def current_language(self) -> str:
        return self._current_language

    @property
    def available_languages(self) -> list[str]:
        return list(self._translations.keys())

    def set_language(self, language: str) -> None:
        normalized = str(language or "").strip().lower()
        if normalized not in self._translations:
            logger.warning("Language not available: %s", language)
            return
        if normalized == self._current_language:
            return
        self._current_language = normalized
        for callback in list(self._on_language_change):
            try:
                callback(normalized)
            except Exception as exc:
                logger.error("Language change callback error: %s", exc)

    def get(
        self,
        key: str,
        *,
        language: Optional[str] = None,
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        lang = str(language or self._current_language or self._fallback_language).lower()
        text = self._translations.get(lang, {}).get(key)
        if text is None:
            text = self._translations.get(self._fallback_language, {}).get(key)
        if text is None:
            text = default if default is not None else key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception as exc:
                logger.warning(
                    "Translation formatting failed: language=%s key=%s error=%s",
                    lang,
                    key,
                    exc,
                )
        return text

    def t(self, key: str, **kwargs) -> str:
        return self.get(key, **kwargs)

    def add_language_change_listener(self, callback: Callable[[str], None]) -> None:
        if callback not in self._on_language_change:
            self._on_language_change.append(callback)

    def remove_language_change_listener(self, callback: Callable[[str], None]) -> None:
        if callback in self._on_language_change:
            self._on_language_change.remove(callback)

    def get_language_name(self, code: str) -> str:
        normalized = str(code or "").strip().lower()
        return self._language_names.get(normalized, normalized or code)

    def get_category_folder_defaults(
        self,
        language: Optional[str] = None,
    ) -> Dict[str, str]:
        lang = str(language or self._current_language or self._fallback_language).lower()
        defaults = self._category_defaults.get(lang)
        if defaults is None:
            defaults = self._category_defaults.get(self._fallback_language, {})
        return {
            key: str(defaults.get(key, key)).strip() or key
            for key in DEFAULT_CATEGORY
        }


_manager: Optional[TranslationManager] = None


def get_translator() -> TranslationManager:
    global _manager
    if _manager is None:
        _manager = TranslationManager()
    return _manager


def t(key: str, **kwargs) -> str:
    return get_translator().get(key, **kwargs)


def set_language(language: str) -> None:
    get_translator().set_language(language)


def get_current_language() -> str:
    return get_translator().current_language


def get_category_folder_defaults(language: Optional[str] = None) -> Dict[str, str]:
    return get_translator().get_category_folder_defaults(language)
