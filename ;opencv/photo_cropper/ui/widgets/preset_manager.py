#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Manager for Photo Cropper.

Provides settings preset save/load functionality.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QInputDialog,
    QGroupBox, QMenu, QDialog, QDialogButtonBox, QFormLayout,
    QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from ...core.settings import AppSettings, get_settings_manager

logger = logging.getLogger(__name__)


# Default presets
DEFAULT_PRESETS = {
    "스캔 문서": {
        "description": "스캔된 문서에 최적화된 설정",
        "algorithm": {
            "canny_min": 30,
            "canny_max": 100,
            "use_clahe": True,
            "clahe_clip_limit": 2.5,
            "multi_scale_edge": True,
            "contour_scoring": "strict"
        },
        "processing": {
            "auto_contrast": True,
            "to_grayscale": False,
            "apply_sharpening": True,
            "sharpening_strength": 1.2,
            "denoise": True,
            "denoise_strength": 8
        },
        "output": {
            "output_format": "PNG",
            "png_compression": 6
        }
    },
    "앨범 사진": {
        "description": "컬러 앨범 사진에 최적화된 설정",
        "algorithm": {
            "canny_min": 50,
            "canny_max": 150,
            "use_clahe": True,
            "clahe_clip_limit": 2.0,
            "multi_scale_edge": True,
            "contour_scoring": "enhanced"
        },
        "processing": {
            "auto_contrast": True,
            "to_grayscale": False,
            "apply_sharpening": False,
            "denoise": False
        },
        "output": {
            "output_format": "JPG",
            "jpg_quality": 95
        }
    },
    "오래된 사진 복원": {
        "description": "오래된 사진 복원에 최적화된 설정",
        "algorithm": {
            "canny_min": 40,
            "canny_max": 120,
            "use_clahe": True,
            "clahe_clip_limit": 3.0,
            "multi_scale_edge": True,
            "use_corner_detection": True
        },
        "processing": {
            "auto_contrast": True,
            "to_grayscale": False,
            "apply_sharpening": True,
            "sharpening_strength": 0.8,
            "denoise": True,
            "denoise_strength": 12
        },
        "output": {
            "output_format": "PNG",
            "png_compression": 4
        }
    },
    "빠른 처리": {
        "description": "속도 우선 처리 설정",
        "algorithm": {
            "canny_min": 50,
            "canny_max": 150,
            "use_clahe": False,
            "multi_scale_edge": False,
            "use_corner_detection": False,
            "contour_scoring": "basic"
        },
        "processing": {
            "auto_contrast": False,
            "apply_sharpening": False,
            "denoise": False
        },
        "output": {
            "output_format": "JPG",
            "jpg_quality": 85
        }
    }
}


class PresetManager:
    """Manages settings presets."""
    
    PRESETS_FILENAME = "photo_cropper_presets.json"
    
    def __init__(self, presets_dir: Optional[str] = None):
        """Initialize preset manager.
        
        Args:
            presets_dir: Directory to store presets file
        """
        if presets_dir:
            self._presets_dir = presets_dir
        else:
            self._presets_dir = os.path.expanduser("~/.photo_cropper")
        
        self._presets_file = os.path.join(self._presets_dir, self.PRESETS_FILENAME)
        self._presets: Dict[str, Dict[str, Any]] = {}
        
        self._load_presets()
    
    def _load_presets(self):
        """Load presets from file."""
        # Start with defaults
        self._presets = dict(DEFAULT_PRESETS)
        
        # Load user presets
        try:
            if os.path.exists(self._presets_file):
                with open(self._presets_file, 'r', encoding='utf-8') as f:
                    user_presets = json.load(f)
                    self._presets.update(user_presets)
                logger.info(f"Loaded {len(user_presets)} user presets")
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
    
    def _save_presets(self):
        """Save presets to file."""
        try:
            os.makedirs(self._presets_dir, exist_ok=True)
            
            # Only save user presets (not defaults)
            user_presets = {
                k: v for k, v in self._presets.items()
                if k not in DEFAULT_PRESETS
            }
            
            with open(self._presets_file, 'w', encoding='utf-8') as f:
                json.dump(user_presets, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(user_presets)} user presets")
            return True
        except Exception as e:
            logger.error(f"Error saving presets: {e}")
            return False
    
    def list_presets(self) -> List[str]:
        """Get list of preset names."""
        return list(self._presets.keys())
    
    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Get preset by name."""
        return self._presets.get(name)
    
    def get_preset_description(self, name: str) -> str:
        """Get preset description."""
        preset = self._presets.get(name)
        if preset:
            return preset.get("description", "")
        return ""
    
    def is_default_preset(self, name: str) -> bool:
        """Check if preset is a default preset."""
        return name in DEFAULT_PRESETS
    
    def save_preset(self, name: str, settings: AppSettings, 
                   description: str = "") -> bool:
        """Save current settings as a preset.
        
        Args:
            name: Preset name
            settings: Settings to save
            description: Optional description
            
        Returns:
            True if saved successfully
        """
        preset_data = {
            "description": description,
            "algorithm": settings.algorithm.__dict__.copy(),
            "processing": settings.processing.__dict__.copy(),
            "output": settings.output.__dict__.copy(),
            "filter": settings.filter.__dict__.copy()
        }
        
        self._presets[name] = preset_data
        return self._save_presets()
    
    def apply_preset(self, name: str, settings: AppSettings) -> bool:
        """Apply preset to settings.
        
        Args:
            name: Preset name
            settings: Settings object to modify
            
        Returns:
            True if applied successfully
        """
        preset = self._presets.get(name)
        if not preset:
            logger.warning(f"Preset not found: {name}")
            return False
        
        # Apply algorithm settings
        if "algorithm" in preset:
            for key, value in preset["algorithm"].items():
                if hasattr(settings.algorithm, key):
                    setattr(settings.algorithm, key, value)
        
        # Apply processing settings
        if "processing" in preset:
            for key, value in preset["processing"].items():
                if hasattr(settings.processing, key):
                    setattr(settings.processing, key, value)
        
        # Apply output settings
        if "output" in preset:
            for key, value in preset["output"].items():
                if hasattr(settings.output, key):
                    setattr(settings.output, key, value)
        
        # Apply filter settings
        if "filter" in preset:
            for key, value in preset["filter"].items():
                if hasattr(settings.filter, key):
                    setattr(settings.filter, key, value)
        
        logger.info(f"Applied preset: {name}")
        return True
    
    def delete_preset(self, name: str) -> bool:
        """Delete a preset.
        
        Args:
            name: Preset name
            
        Returns:
            True if deleted successfully
        """
        if name in DEFAULT_PRESETS:
            logger.warning("Cannot delete default preset")
            return False
        
        if name in self._presets:
            del self._presets[name]
            return self._save_presets()
        
        return False
    
    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Rename a preset.
        
        Args:
            old_name: Current preset name
            new_name: New preset name
            
        Returns:
            True if renamed successfully
        """
        if old_name in DEFAULT_PRESETS:
            logger.warning("Cannot rename default preset")
            return False
        
        if old_name not in self._presets:
            return False
        
        if new_name in self._presets:
            logger.warning("Preset name already exists")
            return False
        
        self._presets[new_name] = self._presets.pop(old_name)
        return self._save_presets()


class PresetManagerWidget(QWidget):
    """Widget for managing presets."""
    
    preset_selected = pyqtSignal(str)  # Emit preset name when selected
    preset_applied = pyqtSignal(str)   # Emit preset name when applied
    
    def __init__(self, settings: Optional[AppSettings] = None, parent=None):
        super().__init__(parent)
        
        self._settings = settings or AppSettings()
        self._manager = PresetManager()
        
        self._setup_ui()
        self._refresh_list()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Preset list
        list_group = QGroupBox("설정 프리셋")
        list_layout = QVBoxLayout(list_group)
        
        self._preset_list = QListWidget()
        self._preset_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._preset_list.itemDoubleClicked.connect(self._on_apply)
        list_layout.addWidget(self._preset_list)
        
        # Description label
        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: gray; font-style: italic;")
        list_layout.addWidget(self._desc_label)
        
        layout.addWidget(list_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._apply_btn = QPushButton("적용")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self._apply_btn)
        
        self._save_btn = QPushButton("현재 설정 저장")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        
        self._delete_btn = QPushButton("삭제")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_list(self):
        """Refresh preset list."""
        self._preset_list.clear()
        
        for name in self._manager.list_presets():
            item = QListWidgetItem(name)
            
            if self._manager.is_default_preset(name):
                item.setIcon(QIcon.fromTheme("folder"))
            else:
                item.setIcon(QIcon.fromTheme("document"))
            
            self._preset_list.addItem(item)
    
    def _on_selection_changed(self):
        """Handle preset selection change."""
        item = self._preset_list.currentItem()
        if item:
            name = item.text()
            desc = self._manager.get_preset_description(name)
            self._desc_label.setText(desc or "설명 없음")
            
            self._apply_btn.setEnabled(True)
            self._delete_btn.setEnabled(not self._manager.is_default_preset(name))
            
            self.preset_selected.emit(name)
        else:
            self._desc_label.setText("")
            self._apply_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
    
    def _on_apply(self):
        """Apply selected preset."""
        item = self._preset_list.currentItem()
        if item:
            name = item.text()
            if self._manager.apply_preset(name, self._settings):
                self.preset_applied.emit(name)
                QMessageBox.information(
                    self, "프리셋 적용",
                    f"'{name}' 프리셋이 적용되었습니다."
                )
    
    def _on_save(self):
        """Save current settings as preset."""
        name, ok = QInputDialog.getText(
            self, "프리셋 저장",
            "프리셋 이름:"
        )
        
        if ok and name:
            if name in self._manager.list_presets():
                reply = QMessageBox.question(
                    self, "프리셋 덮어쓰기",
                    f"'{name}' 프리셋이 이미 존재합니다. 덮어쓰시겠습니까?"
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            desc, _ = QInputDialog.getText(
                self, "프리셋 설명",
                "프리셋 설명 (선택사항):"
            )
            
            if self._manager.save_preset(name, self._settings, desc):
                self._refresh_list()
                QMessageBox.information(
                    self, "저장 완료",
                    f"'{name}' 프리셋이 저장되었습니다."
                )
    
    def _on_delete(self):
        """Delete selected preset."""
        item = self._preset_list.currentItem()
        if not item:
            return
        
        name = item.text()
        
        if self._manager.is_default_preset(name):
            QMessageBox.warning(
                self, "삭제 불가",
                "기본 프리셋은 삭제할 수 없습니다."
            )
            return
        
        reply = QMessageBox.question(
            self, "프리셋 삭제",
            f"'{name}' 프리셋을 삭제하시겠습니까?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._manager.delete_preset(name):
                self._refresh_list()
    
    def set_settings(self, settings: AppSettings):
        """Update settings reference."""
        self._settings = settings
    
    def get_manager(self) -> PresetManager:
        """Get preset manager instance."""
        return self._manager


class PresetComboBox(QComboBox):
    """Combo box for quick preset selection."""
    
    preset_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._manager = PresetManager()
        self._refresh()
        
        self.currentTextChanged.connect(self._on_changed)
    
    def _refresh(self):
        """Refresh preset list."""
        self.clear()
        self.addItem("-- 프리셋 선택 --")
        self.addItems(self._manager.list_presets())
    
    def _on_changed(self, text: str):
        """Handle selection change."""
        if text and not text.startswith("--"):
            self.preset_selected.emit(text)
    
    def apply_to_settings(self, settings: AppSettings) -> bool:
        """Apply selected preset to settings."""
        text = self.currentText()
        if text and not text.startswith("--"):
            return self._manager.apply_preset(text, settings)
        return False


# Singleton instance
_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    """Get or create preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager
