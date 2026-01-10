#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thumbnail Grid Widget for Photo Cropper v8.5.

Provides grid view of images with thumbnails.
"""

import os
import logging
from typing import Optional, List, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QGridLayout, QSizePolicy, QMenu,
    QToolButton, QButtonGroup, QStackedWidget, QListWidget,
    QListWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QIcon

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ThumbnailItem(QFrame):
    """Individual thumbnail item widget."""
    
    clicked = pyqtSignal(str)  # filepath
    double_clicked = pyqtSignal(str)  # filepath
    context_menu_requested = pyqtSignal(str, object)  # filepath, QPoint
    
    def __init__(
        self,
        filepath: str,
        thumbnail_size: int = 150,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.filepath = filepath
        self.thumbnail_size = thumbnail_size
        self._is_selected = False
        self._pixmap: Optional[QPixmap] = None
        
        self._setup_ui()
        self._load_thumbnail()
    
    def _setup_ui(self):
        """Setup UI components."""
        self.setFixedSize(self.thumbnail_size + 20, self.thumbnail_size + 40)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Filename label
        self.name_label = QLabel(os.path.basename(self.filepath))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(30)
        self.name_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.name_label)
        
        self._update_style()
    
    def _load_thumbnail(self):
        """Load thumbnail image."""
        try:
            # Load image
            image = cv2.imread(self.filepath)
            if image is None:
                return
            
            # Resize to thumbnail
            h, w = image.shape[:2]
            scale = min(self.thumbnail_size / w, self.thumbnail_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            thumbnail = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Convert to QPixmap
            rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            self._pixmap = QPixmap.fromImage(qimg)
            self.image_label.setPixmap(self._pixmap)
            
        except Exception as e:
            logger.error(f"Failed to load thumbnail: {e}")
    
    def _update_style(self):
        """Update widget style based on selection state."""
        if self._is_selected:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: rgba(88, 166, 255, 0.3);
                    border: 2px solid #58a6ff;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                }
                ThumbnailItem:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
    
    def set_selected(self, selected: bool):
        """Set selection state."""
        self._is_selected = selected
        self._update_style()
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.filepath)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle context menu."""
        self.context_menu_requested.emit(self.filepath, event.globalPos())


class ThumbnailLoader(QThread):
    """Background thread for loading thumbnails."""
    
    thumbnail_loaded = pyqtSignal(str, QPixmap)
    
    def __init__(self, filepaths: List[str], size: int = 150):
        super().__init__()
        self.filepaths = filepaths
        self.size = size
        self._stop_requested = False
    
    def run(self):
        """Load thumbnails in background."""
        for filepath in self.filepaths:
            if self._stop_requested:
                break
            
            try:
                image = cv2.imread(filepath)
                if image is None:
                    continue
                
                h, w = image.shape[:2]
                scale = min(self.size / w, self.size / h)
                new_w, new_h = int(w * scale), int(h * scale)
                
                thumbnail = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
                
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb.data.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                
                self.thumbnail_loaded.emit(filepath, pixmap)
                
            except Exception as e:
                logger.debug(f"Thumbnail load failed: {e}")
    
    def stop(self):
        """Request stop."""
        self._stop_requested = True


class FlowLayout(QVBoxLayout):
    """Flow layout that wraps items to next row."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[QWidget] = []
        self._spacing = 10
    
    def add_item(self, widget: QWidget):
        """Add item to flow layout."""
        self._items.append(widget)
    
    def clear_items(self):
        """Clear all items."""
        for item in self._items:
            item.setParent(None)
            item.deleteLater()
        self._items.clear()


class ThumbnailGridWidget(QWidget):
    """
    Grid view for displaying image thumbnails.
    
    Features:
        - Responsive grid layout
        - Thumbnail caching
        - Selection support
        - Context menu
        - View mode switching (grid/list)
    """
    
    # Signals
    file_selected = pyqtSignal(str)
    file_double_clicked = pyqtSignal(str)
    selection_changed = pyqtSignal(list)
    
    def __init__(
        self,
        thumbnail_size: int = 150,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.thumbnail_size = thumbnail_size
        self._current_path: str = ""
        self._file_list: List[str] = []
        self._selected_files: List[str] = []
        self._thumbnail_items: dict = {}
        self._loader: Optional[ThumbnailLoader] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # View mode buttons
        self.grid_btn = QToolButton()
        self.grid_btn.setText("▦")
        self.grid_btn.setToolTip("그리드 보기")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        toolbar.addWidget(self.grid_btn)
        
        self.list_btn = QToolButton()
        self.list_btn.setText("☰")
        self.list_btn.setToolTip("리스트 보기")
        self.list_btn.setCheckable(True)
        self.list_btn.clicked.connect(lambda: self._set_view_mode("list"))
        toolbar.addWidget(self.list_btn)
        
        toolbar.addStretch()
        
        # Size slider (simplified)
        self.size_small_btn = QToolButton()
        self.size_small_btn.setText("S")
        self.size_small_btn.setToolTip("작은 썸네일")
        self.size_small_btn.clicked.connect(lambda: self.set_thumbnail_size(100))
        toolbar.addWidget(self.size_small_btn)
        
        self.size_medium_btn = QToolButton()
        self.size_medium_btn.setText("M")
        self.size_medium_btn.setToolTip("중간 썸네일")
        self.size_medium_btn.clicked.connect(lambda: self.set_thumbnail_size(150))
        toolbar.addWidget(self.size_medium_btn)
        
        self.size_large_btn = QToolButton()
        self.size_large_btn.setText("L")
        self.size_large_btn.setToolTip("큰 썸네일")
        self.size_large_btn.clicked.connect(lambda: self.set_thumbnail_size(200))
        toolbar.addWidget(self.size_large_btn)
        
        # Info label
        self.info_label = QLabel()
        toolbar.addWidget(self.info_label)
        
        layout.addLayout(toolbar)
        
        # Stacked widget for view modes
        self.view_stack = QStackedWidget()
        
        # Grid view
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_scroll.setWidget(self.grid_container)
        
        self.view_stack.addWidget(self.grid_scroll)
        
        # List view
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.itemClicked.connect(self._on_list_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_list_item_double_clicked)
        
        self.view_stack.addWidget(self.list_widget)
        
        layout.addWidget(self.view_stack)
    
    def _set_view_mode(self, mode: str):
        """Set view mode (grid/list)."""
        if mode == "grid":
            self.view_stack.setCurrentIndex(0)
            self.grid_btn.setChecked(True)
            self.list_btn.setChecked(False)
        else:
            self.view_stack.setCurrentIndex(1)
            self.grid_btn.setChecked(False)
            self.list_btn.setChecked(True)
    
    def set_files(self, filepaths: List[str]):
        """
        Set files to display.
        
        Args:
            filepaths: List of image file paths
        """
        # Stop any existing loader
        if self._loader and self._loader.isRunning():
            self._loader.stop()
            if not self._loader.wait(3000):  # 3 second timeout
                logger.warning("Thumbnail loader did not stop in time")
        
        self._file_list = filepaths
        self._selected_files.clear()
        
        self._clear_grid()
        self._populate_grid()
        self._populate_list()
        
        self.info_label.setText(f"{len(filepaths)} 파일")
    
    def _clear_grid(self):
        """Clear grid layout."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._thumbnail_items.clear()
    
    def _populate_grid(self):
        """Populate grid with thumbnails."""
        # Calculate columns based on widget width
        container_width = max(400, self.width() - 40)
        item_width = self.thumbnail_size + 30
        columns = max(1, container_width // item_width)
        
        for i, filepath in enumerate(self._file_list):
            row = i // columns
            col = i % columns
            
            item = ThumbnailItem(filepath, self.thumbnail_size, self.grid_container)
            item.clicked.connect(self._on_thumbnail_clicked)
            item.double_clicked.connect(self._on_thumbnail_double_clicked)
            item.context_menu_requested.connect(self._on_context_menu)
            
            self.grid_layout.addWidget(item, row, col)
            self._thumbnail_items[filepath] = item
    
    def _populate_list(self):
        """Populate list view."""
        self.list_widget.clear()
        
        for filepath in self._file_list:
            item = QListWidgetItem(os.path.basename(filepath))
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            item.setToolTip(filepath)
            self.list_widget.addItem(item)
    
    def _on_thumbnail_clicked(self, filepath: str):
        """Handle thumbnail click."""
        # Update selection
        self._selected_files = [filepath]
        
        # Update visual selection
        for path, item in self._thumbnail_items.items():
            item.set_selected(path == filepath)
        
        self.file_selected.emit(filepath)
        self.selection_changed.emit(self._selected_files)
    
    def _on_thumbnail_double_clicked(self, filepath: str):
        """Handle thumbnail double click."""
        self.file_double_clicked.emit(filepath)
    
    def _on_list_item_clicked(self, item: QListWidgetItem):
        """Handle list item click."""
        filepath = item.data(Qt.ItemDataRole.UserRole)
        self._selected_files = [filepath]
        self.file_selected.emit(filepath)
        self.selection_changed.emit(self._selected_files)
    
    def _on_list_item_double_clicked(self, item: QListWidgetItem):
        """Handle list item double click."""
        filepath = item.data(Qt.ItemDataRole.UserRole)
        self.file_double_clicked.emit(filepath)
    
    def _on_context_menu(self, filepath: str, pos):
        """Handle context menu request."""
        menu = QMenu(self)
        
        open_action = menu.addAction("열기")
        open_action.triggered.connect(lambda: self.file_double_clicked.emit(filepath))
        
        menu.addSeparator()
        
        explorer_action = menu.addAction("파일 위치 열기")
        explorer_action.triggered.connect(lambda: self._open_in_explorer(filepath))
        
        menu.exec(pos)
    
    def _open_in_explorer(self, filepath: str):
        """Open file location in explorer."""
        import subprocess
        folder = os.path.dirname(filepath)
        if os.name == 'nt':
            subprocess.run(['explorer', '/select,', filepath])
        else:
            subprocess.run(['xdg-open', folder])
    
    def set_thumbnail_size(self, size: int):
        """Change thumbnail size."""
        self.thumbnail_size = size
        if self._file_list:
            self.set_files(self._file_list)
    
    def get_selected_files(self) -> List[str]:
        """Get list of selected files."""
        return self._selected_files.copy()
    
    def select_all(self):
        """Select all files."""
        self._selected_files = self._file_list.copy()
        for item in self._thumbnail_items.values():
            item.set_selected(True)
        self.selection_changed.emit(self._selected_files)
    
    def clear_selection(self):
        """Clear selection."""
        self._selected_files.clear()
        for item in self._thumbnail_items.values():
            item.set_selected(False)
        self.selection_changed.emit(self._selected_files)
    
    def refresh(self):
        """Refresh thumbnails."""
        if self._file_list:
            self.set_files(self._file_list)
    
    def closeEvent(self, event):
        """Clean up resources on close."""
        if self._loader and self._loader.isRunning():
            self._loader.stop()
            self._loader.wait(2000)  # 2 second timeout
        super().closeEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize - reflow grid."""
        super().resizeEvent(event)
        # Could trigger grid recalculation here if needed
