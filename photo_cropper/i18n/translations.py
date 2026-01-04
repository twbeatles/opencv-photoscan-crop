#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Module for Photo Cropper v8.5.

Provides multi-language support with dynamic language switching.
"""

import os
import json
import logging
from typing import Dict, Optional, Callable, List

logger = logging.getLogger(__name__)


# Default translations (Korean as base language)
DEFAULT_TRANSLATIONS = {
    "ko": {
        # App
        "app.name": "사진 자동 자르기",
        "app.version": "v8.5",
        
        # Menu - File
        "menu.file": "파일",
        "menu.file.open_folder": "입력 폴더 선택",
        "menu.file.open_image": "이미지 열기",
        "menu.file.open_output": "출력 폴더 열기",
        "menu.file.exit": "종료",
        
        # Menu - Edit
        "menu.edit": "편집",
        "menu.edit.undo": "실행 취소",
        "menu.edit.redo": "다시 실행",
        "menu.edit.settings": "설정",
        "menu.edit.reset": "설정 초기화",
        
        # Menu - View
        "menu.view": "보기",
        "menu.view.theme": "테마",
        "menu.view.fullscreen": "전체화면",
        "menu.view.grid_view": "그리드 보기",
        "menu.view.list_view": "리스트 보기",
        
        # Menu - Process
        "menu.process": "처리",
        "menu.process.preview": "미리보기",
        "menu.process.start": "변환 시작",
        "menu.process.cancel": "취소",
        "menu.process.retry_failed": "실패 파일 재시도",
        
        # Menu - Help
        "menu.help": "도움말",
        "menu.help.about": "정보",
        "menu.help.shortcuts": "단축키",
        
        # Toolbar
        "toolbar.open_folder": "폴더 열기",
        "toolbar.open_image": "이미지 열기",
        "toolbar.preview": "미리보기",
        "toolbar.start": "시작",
        "toolbar.cancel": "취소",
        "toolbar.rotate": "회전",
        "toolbar.theme": "테마 변경",
        "toolbar.refresh": "새로고침",
        
        # Settings Panel
        "settings.tab.basic": "기본",
        "settings.tab.algorithm": "알고리즘",
        "settings.tab.output": "출력",
        "settings.tab.filter": "필터",
        "settings.tab.advanced": "고급",
        "settings.tab.file_management": "파일 관리",
        "settings.tab.performance": "성능",
        "settings.tab.watermark": "워터마크",
        "settings.tab.resize": "리사이즈",
        "settings.tab.automation": "자동화",
        
        # Settings - Basic
        "settings.input_folder": "입력 폴더",
        "settings.output_folder": "출력 폴더",
        "settings.browse": "찾아보기",
        
        # Settings - Algorithm
        "settings.canny_threshold": "Canny 임계값",
        "settings.canny_min": "최소",
        "settings.canny_max": "최대",
        "settings.use_clahe": "CLAHE 대비 향상",
        "settings.multi_scale": "다중 스케일 감지",
        "settings.corner_detection": "코너 검출",
        
        # Settings - Output
        "settings.output_format": "출력 형식",
        "settings.quality": "품질",
        "settings.compression": "압축",
        "settings.grayscale": "그레이스케일",
        "settings.sharpen": "선명하게",
        "settings.denoise": "노이즈 제거",
        
        # Settings - Filter
        "settings.skip_small": "작은 이미지 건너뛰기",
        "settings.min_size": "최소 크기",
        "settings.skip_processed": "처리된 파일 건너뛰기",
        
        # Settings - Watermark
        "settings.watermark.enable": "워터마크 사용",
        "settings.watermark.text": "텍스트",
        "settings.watermark.position": "위치",
        "settings.watermark.opacity": "투명도",
        "settings.watermark.image": "이미지 워터마크",
        
        # Settings - Resize
        "settings.resize.enable": "리사이즈 사용",
        "settings.resize.mode": "모드",
        "settings.resize.width": "너비",
        "settings.resize.height": "높이",
        "settings.resize.percentage": "비율",
        "settings.resize.max_dimension": "최대 크기",
        
        # Settings - Automation
        "settings.auto.watch_mode": "폴더 감시 모드",
        "settings.auto.watch_folder": "감시 폴더",
        "settings.auto.scheduler": "스케줄러",
        "settings.auto.add_schedule": "스케줄 추가",
        
        # Status
        "status.ready": "준비",
        "status.processing": "처리 중...",
        "status.completed": "완료",
        "status.cancelled": "취소됨",
        "status.error": "오류",
        
        # Progress
        "progress.title": "처리 중",
        "progress.processing_file": "파일 처리 중",
        "progress.success": "성공",
        "progress.failed": "실패",
        "progress.skipped": "건너뜀",
        "progress.remaining": "남은 시간",
        "progress.cancel": "취소",
        
        # Dialogs
        "dialog.confirm": "확인",
        "dialog.cancel": "취소",
        "dialog.yes": "예",
        "dialog.no": "아니오",
        "dialog.ok": "확인",
        "dialog.save": "저장",
        "dialog.delete": "삭제",
        
        # Messages
        "msg.no_files": "처리할 이미지가 없습니다.",
        "msg.processing_complete": "처리가 완료되었습니다.",
        "msg.processing_cancelled": "처리가 취소되었습니다.",
        "msg.select_folder": "폴더를 선택하세요.",
        "msg.invalid_folder": "유효하지 않은 폴더입니다.",
        
        # Watermark positions
        "position.top_left": "왼쪽 상단",
        "position.top_center": "중앙 상단",
        "position.top_right": "오른쪽 상단",
        "position.middle_left": "왼쪽 중앙",
        "position.center": "중앙",
        "position.middle_right": "오른쪽 중앙",
        "position.bottom_left": "왼쪽 하단",
        "position.bottom_center": "중앙 하단",
        "position.bottom_right": "오른쪽 하단",
        
        # Resize modes
        "resize.mode.none": "없음",
        "resize.mode.fit": "맞춤",
        "resize.mode.fill": "채우기",
        "resize.mode.stretch": "늘리기",
        "resize.mode.width": "너비 기준",
        "resize.mode.height": "높이 기준",
        "resize.mode.percentage": "비율",
        "resize.mode.max_dimension": "최대 크기",
    },
    
    "en": {
        # App
        "app.name": "Photo Cropper",
        "app.version": "v8.5",
        
        # Menu - File
        "menu.file": "File",
        "menu.file.open_folder": "Open Input Folder",
        "menu.file.open_image": "Open Image",
        "menu.file.open_output": "Open Output Folder",
        "menu.file.exit": "Exit",
        
        # Menu - Edit
        "menu.edit": "Edit",
        "menu.edit.undo": "Undo",
        "menu.edit.redo": "Redo",
        "menu.edit.settings": "Settings",
        "menu.edit.reset": "Reset Settings",
        
        # Menu - View
        "menu.view": "View",
        "menu.view.theme": "Theme",
        "menu.view.fullscreen": "Fullscreen",
        "menu.view.grid_view": "Grid View",
        "menu.view.list_view": "List View",
        
        # Menu - Process
        "menu.process": "Process",
        "menu.process.preview": "Preview",
        "menu.process.start": "Start Processing",
        "menu.process.cancel": "Cancel",
        "menu.process.retry_failed": "Retry Failed",
        
        # Menu - Help
        "menu.help": "Help",
        "menu.help.about": "About",
        "menu.help.shortcuts": "Shortcuts",
        
        # Toolbar
        "toolbar.open_folder": "Open Folder",
        "toolbar.open_image": "Open Image",
        "toolbar.preview": "Preview",
        "toolbar.start": "Start",
        "toolbar.cancel": "Cancel",
        "toolbar.rotate": "Rotate",
        "toolbar.theme": "Toggle Theme",
        "toolbar.refresh": "Refresh",
        
        # Settings Panel
        "settings.tab.basic": "Basic",
        "settings.tab.algorithm": "Algorithm",
        "settings.tab.output": "Output",
        "settings.tab.filter": "Filter",
        "settings.tab.advanced": "Advanced",
        "settings.tab.file_management": "File Management",
        "settings.tab.performance": "Performance",
        "settings.tab.watermark": "Watermark",
        "settings.tab.resize": "Resize",
        "settings.tab.automation": "Automation",
        
        # Settings - Basic
        "settings.input_folder": "Input Folder",
        "settings.output_folder": "Output Folder",
        "settings.browse": "Browse",
        
        # Settings - Algorithm
        "settings.canny_threshold": "Canny Threshold",
        "settings.canny_min": "Min",
        "settings.canny_max": "Max",
        "settings.use_clahe": "CLAHE Enhancement",
        "settings.multi_scale": "Multi-scale Detection",
        "settings.corner_detection": "Corner Detection",
        
        # Settings - Output
        "settings.output_format": "Output Format",
        "settings.quality": "Quality",
        "settings.compression": "Compression",
        "settings.grayscale": "Grayscale",
        "settings.sharpen": "Sharpen",
        "settings.denoise": "Denoise",
        
        # Settings - Filter
        "settings.skip_small": "Skip Small Images",
        "settings.min_size": "Minimum Size",
        "settings.skip_processed": "Skip Processed",
        
        # Settings - Watermark
        "settings.watermark.enable": "Enable Watermark",
        "settings.watermark.text": "Text",
        "settings.watermark.position": "Position",
        "settings.watermark.opacity": "Opacity",
        "settings.watermark.image": "Image Watermark",
        
        # Settings - Resize
        "settings.resize.enable": "Enable Resize",
        "settings.resize.mode": "Mode",
        "settings.resize.width": "Width",
        "settings.resize.height": "Height",
        "settings.resize.percentage": "Percentage",
        "settings.resize.max_dimension": "Max Dimension",
        
        # Settings - Automation
        "settings.auto.watch_mode": "Watch Mode",
        "settings.auto.watch_folder": "Watch Folder",
        "settings.auto.scheduler": "Scheduler",
        "settings.auto.add_schedule": "Add Schedule",
        
        # Status
        "status.ready": "Ready",
        "status.processing": "Processing...",
        "status.completed": "Completed",
        "status.cancelled": "Cancelled",
        "status.error": "Error",
        
        # Progress
        "progress.title": "Processing",
        "progress.processing_file": "Processing file",
        "progress.success": "Success",
        "progress.failed": "Failed",
        "progress.skipped": "Skipped",
        "progress.remaining": "Remaining",
        "progress.cancel": "Cancel",
        
        # Dialogs
        "dialog.confirm": "Confirm",
        "dialog.cancel": "Cancel",
        "dialog.yes": "Yes",
        "dialog.no": "No",
        "dialog.ok": "OK",
        "dialog.save": "Save",
        "dialog.delete": "Delete",
        
        # Messages
        "msg.no_files": "No images to process.",
        "msg.processing_complete": "Processing completed.",
        "msg.processing_cancelled": "Processing cancelled.",
        "msg.select_folder": "Please select a folder.",
        "msg.invalid_folder": "Invalid folder.",
        
        # Watermark positions
        "position.top_left": "Top Left",
        "position.top_center": "Top Center",
        "position.top_right": "Top Right",
        "position.middle_left": "Middle Left",
        "position.center": "Center",
        "position.middle_right": "Middle Right",
        "position.bottom_left": "Bottom Left",
        "position.bottom_center": "Bottom Center",
        "position.bottom_right": "Bottom Right",
        
        # Resize modes
        "resize.mode.none": "None",
        "resize.mode.fit": "Fit",
        "resize.mode.fill": "Fill",
        "resize.mode.stretch": "Stretch",
        "resize.mode.width": "By Width",
        "resize.mode.height": "By Height",
        "resize.mode.percentage": "Percentage",
        "resize.mode.max_dimension": "Max Dimension",
    },
    
    "ja": {
        # App
        "app.name": "フォトクロッパー",
        "app.version": "v8.5",
        
        # Menu - File
        "menu.file": "ファイル",
        "menu.file.open_folder": "入力フォルダを選択",
        "menu.file.open_image": "画像を開く",
        "menu.file.open_output": "出力フォルダを開く",
        "menu.file.exit": "終了",
        
        # Menu - Edit
        "menu.edit": "編集",
        "menu.edit.undo": "元に戻す",
        "menu.edit.redo": "やり直し",
        "menu.edit.settings": "設定",
        "menu.edit.reset": "設定をリセット",
        
        # Menu - View
        "menu.view": "表示",
        "menu.view.theme": "テーマ",
        "menu.view.fullscreen": "全画面",
        "menu.view.grid_view": "グリッド表示",
        "menu.view.list_view": "リスト表示",
        
        # Menu - Process
        "menu.process": "処理",
        "menu.process.preview": "プレビュー",
        "menu.process.start": "処理開始",
        "menu.process.cancel": "キャンセル",
        "menu.process.retry_failed": "失敗を再試行",
        
        # Menu - Help
        "menu.help": "ヘルプ",
        "menu.help.about": "情報",
        "menu.help.shortcuts": "ショートカット",
        
        # Status
        "status.ready": "準備完了",
        "status.processing": "処理中...",
        "status.completed": "完了",
        "status.cancelled": "キャンセル",
        "status.error": "エラー",
        
        # Dialogs
        "dialog.confirm": "確認",
        "dialog.cancel": "キャンセル",
        "dialog.yes": "はい",
        "dialog.no": "いいえ",
        "dialog.ok": "OK",
        "dialog.save": "保存",
        "dialog.delete": "削除",
    }
}


class TranslationManager:
    """
    Multi-language translation manager.
    
    Features:
        - Dynamic language switching
        - Fallback to default language
        - External translation file loading
        - Translation key lookup with parameters
    """
    
    _instance: Optional['TranslationManager'] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize translation manager."""
        if self._initialized:
            return
        
        self._translations: Dict[str, Dict[str, str]] = dict(DEFAULT_TRANSLATIONS)
        self._current_language = "ko"
        self._fallback_language = "en"
        self._on_language_change: List[Callable[[str], None]] = []
        
        self._initialized = True
    
    @property
    def current_language(self) -> str:
        """Get current language code."""
        return self._current_language
    
    @property
    def available_languages(self) -> List[str]:
        """Get list of available language codes."""
        return list(self._translations.keys())
    
    def set_language(self, language: str):
        """
        Set current language.
        
        Args:
            language: Language code (e.g., 'ko', 'en', 'ja')
        """
        if language not in self._translations:
            logger.warning(f"Language not available: {language}")
            return
        
        self._current_language = language
        
        # Notify listeners
        for callback in self._on_language_change:
            try:
                callback(language)
            except Exception as e:
                logger.error(f"Language change callback error: {e}")
    
    def get(self, key: str, **kwargs) -> str:
        """
        Get translated string.
        
        Args:
            key: Translation key (e.g., 'menu.file.open')
            **kwargs: Format parameters
            
        Returns:
            Translated string or key if not found
        """
        # Try current language
        text = self._translations.get(self._current_language, {}).get(key)
        
        # Fallback to default
        if text is None:
            text = self._translations.get(self._fallback_language, {}).get(key)
        
        # Return key if not found
        if text is None:
            return key
        
        # Apply format parameters
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def t(self, key: str, **kwargs) -> str:
        """Alias for get()."""
        return self.get(key, **kwargs)
    
    def load_translations(self, filepath: str) -> bool:
        """
        Load translations from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for lang, translations in data.items():
                if lang in self._translations:
                    self._translations[lang].update(translations)
                else:
                    self._translations[lang] = translations
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load translations: {e}")
            return False
    
    def add_language_change_listener(self, callback: Callable[[str], None]):
        """Add listener for language changes."""
        self._on_language_change.append(callback)
    
    def remove_language_change_listener(self, callback: Callable[[str], None]):
        """Remove language change listener."""
        if callback in self._on_language_change:
            self._on_language_change.remove(callback)
    
    def get_language_name(self, code: str) -> str:
        """Get display name for language code."""
        names = {
            "ko": "한국어",
            "en": "English",
            "ja": "日本語",
            "zh": "中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
        }
        return names.get(code, code)


# Global instance
_manager: Optional[TranslationManager] = None


def get_translator() -> TranslationManager:
    """Get global translation manager instance."""
    global _manager
    if _manager is None:
        _manager = TranslationManager()
    return _manager


def t(key: str, **kwargs) -> str:
    """
    Get translated string (shortcut function).
    
    Args:
        key: Translation key
        **kwargs: Format parameters
        
    Returns:
        Translated string
    """
    return get_translator().get(key, **kwargs)


def set_language(language: str):
    """Set current language (shortcut function)."""
    get_translator().set_language(language)


def get_current_language() -> str:
    """Get current language code (shortcut function)."""
    return get_translator().current_language
