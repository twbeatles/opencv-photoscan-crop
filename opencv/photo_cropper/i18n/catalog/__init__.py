from .detect import detect_system_language
from .manager import (
    FALLBACK_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TranslationManager,
    get_category_folder_defaults,
    get_current_language,
    get_translator,
    set_language,
    t,
)

__all__ = [
    "FALLBACK_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "detect_system_language",
    "TranslationManager",
    "get_category_folder_defaults",
    "get_translator",
    "t",
    "set_language",
    "get_current_language",
]
