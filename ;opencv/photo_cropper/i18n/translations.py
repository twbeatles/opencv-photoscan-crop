#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Module for Photo Cropper v9.0.

Provides multi-language support with dynamic language switching
and automatic system locale detection.
"""

import os
import json
import locale
import logging
from typing import Dict, Optional, Callable, List

logger = logging.getLogger(__name__)


def detect_system_language() -> str:
    """
    Detect language from system locale.
    
    Returns:
        Language code ('ko', 'en', 'ja', 'zh', 'es') or 'en' as default
    """
    def _extract_lang(locale_str: Optional[str]) -> str:
        if not locale_str:
            return ""
        # e.g. "ko_KR.UTF-8", "en_US", "zh_CN", "en_US:en"
        s = locale_str.split(":")[0].split(".")[0].replace("-", "_")
        return s.split("_")[0].lower()

    try:
        # Prefer getlocale() (getdefaultlocale() is deprecated).
        locale_lang = None
        try:
            locale_lang = locale.getlocale()[0]
        except Exception:
            locale_lang = None

        lang_code = _extract_lang(locale_lang)
        if not lang_code:
            # Fallback to environment variables
            for env_key in ("LC_ALL", "LANG", "LANGUAGE"):
                lang_code = _extract_lang(os.environ.get(env_key))
                if lang_code:
                    break

        supported = ["ko", "en", "ja", "zh", "es"]
        if lang_code in supported:
            logger.info(f"Detected system language: {lang_code}")
            return lang_code

        # Map similar Chinese locales
        if lang_code in ["zh-cn", "zh-hans", "zh-tw", "zh-hant"]:
            return "zh"
    except Exception as e:
        logger.debug(f"Could not detect system locale: {e}")
    
    return 'en'  # Default to English


# Default translations (Korean as base language)
DEFAULT_TRANSLATIONS = {
    "ko": {
        # App
        "app.name": "사진 자동 자르기",
        "app.version": "v9.0",
        
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
        "app.version": "v9.0",
        
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
        "app.version": "v9.0",
        
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
        
        # Toolbar
        "toolbar.open_folder": "フォルダを開く",
        "toolbar.open_image": "画像を開く",
        "toolbar.preview": "プレビュー",
        "toolbar.start": "開始",
        "toolbar.cancel": "キャンセル",
        "toolbar.rotate": "回転",
        "toolbar.theme": "テーマ切替",
        "toolbar.refresh": "更新",
        
        # Settings
        "settings.tab.basic": "基本",
        "settings.tab.algorithm": "アルゴリズム",
        "settings.tab.output": "出力",
        "settings.tab.filter": "フィルタ",
        "settings.tab.advanced": "高度",
        "settings.tab.watermark": "透かし",
        "settings.tab.resize": "リサイズ",
        "settings.tab.automation": "自動化",
        
        # Status
        "status.ready": "準備完了",
        "status.processing": "処理中...",
        "status.completed": "完了",
        "status.cancelled": "キャンセル",
        "status.error": "エラー",
        
        # Progress
        "progress.title": "処理中",
        "progress.processing_file": "ファイル処理中",
        "progress.success": "成功",
        "progress.failed": "失敗",
        "progress.skipped": "スキップ",
        "progress.remaining": "残り時間",
        "progress.cancel": "キャンセル",
        
        # Dialogs
        "dialog.confirm": "確認",
        "dialog.cancel": "キャンセル",
        "dialog.yes": "はい",
        "dialog.no": "いいえ",
        "dialog.ok": "OK",
        "dialog.save": "保存",
        "dialog.delete": "削除",
        
        # Messages
        "msg.no_files": "処理する画像がありません。",
        "msg.processing_complete": "処理が完了しました。",
        "msg.processing_cancelled": "処理がキャンセルされました。",
        "msg.select_folder": "フォルダを選択してください。",
        "msg.invalid_folder": "無効なフォルダです。",
    },
    
    "zh": {
        # App
        "app.name": "照片自动裁剪",
        "app.version": "v9.0",
        
        # Menu - File
        "menu.file": "文件",
        "menu.file.open_folder": "选择输入文件夹",
        "menu.file.open_image": "打开图片",
        "menu.file.open_output": "打开输出文件夹",
        "menu.file.exit": "退出",
        
        # Menu - Edit
        "menu.edit": "编辑",
        "menu.edit.undo": "撤销",
        "menu.edit.redo": "重做",
        "menu.edit.settings": "设置",
        "menu.edit.reset": "重置设置",
        
        # Menu - View
        "menu.view": "视图",
        "menu.view.theme": "主题",
        "menu.view.fullscreen": "全屏",
        "menu.view.grid_view": "网格视图",
        "menu.view.list_view": "列表视图",
        
        # Menu - Process
        "menu.process": "处理",
        "menu.process.preview": "预览",
        "menu.process.start": "开始处理",
        "menu.process.cancel": "取消",
        "menu.process.retry_failed": "重试失败",
        
        # Menu - Help
        "menu.help": "帮助",
        "menu.help.about": "关于",
        "menu.help.shortcuts": "快捷键",
        
        # Toolbar
        "toolbar.open_folder": "打开文件夹",
        "toolbar.open_image": "打开图片",
        "toolbar.preview": "预览",
        "toolbar.start": "开始",
        "toolbar.cancel": "取消",
        "toolbar.rotate": "旋转",
        "toolbar.theme": "切换主题",
        "toolbar.refresh": "刷新",
        
        # Settings
        "settings.tab.basic": "基本",
        "settings.tab.algorithm": "算法",
        "settings.tab.output": "输出",
        "settings.tab.filter": "过滤",
        "settings.tab.advanced": "高级",
        "settings.tab.watermark": "水印",
        "settings.tab.resize": "调整大小",
        "settings.tab.automation": "自动化",
        
        # Status
        "status.ready": "就绪",
        "status.processing": "处理中...",
        "status.completed": "完成",
        "status.cancelled": "已取消",
        "status.error": "错误",
        
        # Dialogs
        "dialog.confirm": "确认",
        "dialog.cancel": "取消",
        "dialog.yes": "是",
        "dialog.no": "否",
        "dialog.ok": "确定",
        "dialog.save": "保存",
        "dialog.delete": "删除",
        
        # Messages
        "msg.no_files": "没有可处理的图片。",
        "msg.processing_complete": "处理完成。",
        "msg.processing_cancelled": "处理已取消。",
        "msg.select_folder": "请选择文件夹。",
        "msg.invalid_folder": "无效的文件夹。",
    },
    
    "es": {
        # App
        "app.name": "Recortador de Fotos",
        "app.version": "v9.0",
        
        # Menu - File
        "menu.file": "Archivo",
        "menu.file.open_folder": "Seleccionar carpeta de entrada",
        "menu.file.open_image": "Abrir imagen",
        "menu.file.open_output": "Abrir carpeta de salida",
        "menu.file.exit": "Salir",
        
        # Menu - Edit
        "menu.edit": "Editar",
        "menu.edit.undo": "Deshacer",
        "menu.edit.redo": "Rehacer",
        "menu.edit.settings": "Configuración",
        "menu.edit.reset": "Restablecer configuración",
        
        # Menu - View
        "menu.view": "Ver",
        "menu.view.theme": "Tema",
        "menu.view.fullscreen": "Pantalla completa",
        "menu.view.grid_view": "Vista de cuadrícula",
        "menu.view.list_view": "Vista de lista",
        
        # Menu - Process
        "menu.process": "Procesar",
        "menu.process.preview": "Vista previa",
        "menu.process.start": "Iniciar procesamiento",
        "menu.process.cancel": "Cancelar",
        "menu.process.retry_failed": "Reintentar fallidos",
        
        # Menu - Help
        "menu.help": "Ayuda",
        "menu.help.about": "Acerca de",
        "menu.help.shortcuts": "Atajos",
        
        # Toolbar
        "toolbar.open_folder": "Abrir carpeta",
        "toolbar.open_image": "Abrir imagen",
        "toolbar.preview": "Vista previa",
        "toolbar.start": "Iniciar",
        "toolbar.cancel": "Cancelar",
        "toolbar.rotate": "Rotar",
        "toolbar.theme": "Cambiar tema",
        "toolbar.refresh": "Actualizar",
        
        # Settings
        "settings.tab.basic": "Básico",
        "settings.tab.algorithm": "Algoritmo",
        "settings.tab.output": "Salida",
        "settings.tab.filter": "Filtro",
        "settings.tab.advanced": "Avanzado",
        "settings.tab.watermark": "Marca de agua",
        "settings.tab.resize": "Redimensionar",
        "settings.tab.automation": "Automatización",
        
        # Status
        "status.ready": "Listo",
        "status.processing": "Procesando...",
        "status.completed": "Completado",
        "status.cancelled": "Cancelado",
        "status.error": "Error",
        
        # Dialogs
        "dialog.confirm": "Confirmar",
        "dialog.cancel": "Cancelar",
        "dialog.yes": "Sí",
        "dialog.no": "No",
        "dialog.ok": "Aceptar",
        "dialog.save": "Guardar",
        "dialog.delete": "Eliminar",
        
        # Messages
        "msg.no_files": "No hay imágenes para procesar.",
        "msg.processing_complete": "Procesamiento completado.",
        "msg.processing_cancelled": "Procesamiento cancelado.",
        "msg.select_folder": "Por favor, seleccione una carpeta.",
        "msg.invalid_folder": "Carpeta inválida.",
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
        """Initialize translation manager with auto-detected language."""
        if self._initialized:
            return
        
        self._translations: Dict[str, Dict[str, str]] = dict(DEFAULT_TRANSLATIONS)
        self._fallback_language = "en"
        self._on_language_change: List[Callable[[str], None]] = []
        
        # Auto-detect system language
        detected = detect_system_language()
        self._current_language = detected
        logger.info(f"Translation manager initialized with language: {detected}")
        
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
