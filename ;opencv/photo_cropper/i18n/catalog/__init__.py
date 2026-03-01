from .detect import detect_system_language
from .manager import TranslationManager, get_translator, t, set_language, get_current_language

__all__ = [
    'detect_system_language',
    'TranslationManager',
    'get_translator',
    't',
    'set_language',
    'get_current_language',
]
