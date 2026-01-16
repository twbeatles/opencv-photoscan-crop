#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Dialog for Photo Cropper.

Provides batch processing progress display with cancel support.
Enhanced UI/UX v7.2
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QTextEdit, QGroupBox,
    QFrame, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
import time

from ...core.batch_processor import BatchProgress, FileResult, ProcessStatus


class StatCard(QFrame):
    """Individual stat card with icon and value."""
    
    def __init__(self, icon: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self._value = 0
        
        self.setObjectName("statsFrame")
        self.setMinimumWidth(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Value
        self.value_label = QLabel("0")
        self.value_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color}; margin-top: 4px;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Label
        self.label_text = QLabel(label)
        self.label_text.setFont(QFont("Segoe UI", 10))
        self.label_text.setStyleSheet("color: #888888;")
        self.label_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_text)
    
    def set_value(self, value):
        """Set the value displayed."""
        self._value = value
        self.value_label.setText(str(value))
    
    def set_value_text(self, text: str):
        """Set custom value text."""
        self.value_label.setText(text)


class StatsWidget(QFrame):
    """Widget to display processing statistics with enhanced design."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Create stat cards with icons - using new theme colors
        self.total_card = StatCard("📊", "처리됨", "#8b949e", self)
        self.success_card = StatCard("✅", "성공", "#34d399", self)  # Emerald
        self.failed_card = StatCard("❌", "실패", "#f87171", self)   # Rose
        self.skipped_card = StatCard("⏭️", "건너뜀", "#fbbf24", self) # Amber
        self.rate_card = StatCard("📈", "성공률", "#818cf8", self)    # Indigo
        
        layout.addWidget(self.total_card)
        layout.addWidget(self.success_card)
        layout.addWidget(self.failed_card)
        layout.addWidget(self.skipped_card)
        layout.addWidget(self.rate_card)
    
    def update_stats(self, progress: BatchProgress):
        """Update all stat cards."""
        self.total_card.set_value_text(f"{progress.processed}/{progress.total}")
        self.success_card.set_value(progress.success)
        self.failed_card.set_value(progress.failed)
        self.skipped_card.set_value(progress.skipped)
        self.rate_card.set_value_text(f"{progress.success_rate:.1f}%")


class ProgressDialog(QDialog):
    """
    Modal dialog showing batch processing progress.
    
    Enhanced with better visuals and animations.
    
    Signals:
        cancel_requested: Emitted when cancel is clicked
    """
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("🔄 처리 중...")
        self.setMinimumSize(700, 550)
        self.setModal(True)
        
        self._is_cancelled = False
        self._is_complete = False
        self._start_time = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # 1. Header with Current File (Glass Card)
        header_frame = QFrame()
        header_frame.setObjectName("statsFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(10)
        
        title_label = QLabel("🚀 일괄 처리 진행 중")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        self.current_file_label = QLabel("준비 중...")
        self.current_file_label.setFont(QFont("Segoe UI", 11))
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_file_label.setStyleSheet("color: #8b949e;")
        header_layout.addWidget(self.current_file_label)
        
        layout.addWidget(header_frame)
        
        # 2. Progress Section
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        # Percentage & ETA Row
        info_row = QHBoxLayout()
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.percent_label.setStyleSheet("color: #818cf8;")  # Indigo
        info_row.addWidget(self.percent_label)
        
        info_row.addStretch()
        
        self.eta_label = QLabel("⏱️ 계산 중...")
        self.eta_label.setFont(QFont("Segoe UI", 10))
        self.eta_label.setStyleSheet("color: #8b949e;")
        info_row.addWidget(self.eta_label)
        progress_layout.addLayout(info_row)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(16)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_container)
        
        # 3. Stats Grid
        self.stats_widget = StatsWidget()
        layout.addWidget(self.stats_widget)
        
        # 4. Logs (Collapsible look)
        log_group = QGroupBox("📋 처리 로그")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 24, 12, 12)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("border: none; background-color: transparent;")
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group, 1) # Give it stretch
        
        # 5. Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        self.cancel_button = QPushButton("작업 취소")
        self.cancel_button.setObjectName("primaryButton") # Red/Warning style logic can be applied if needed
        self.cancel_button.setStyleSheet("""
            QPushButton { background-color: #cf222e; border: 1px solid rgba(27,31,36,0.15); }
            QPushButton:hover { background-color: #a40e26; }
        """)
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        self.close_button = QPushButton("닫기")
        self.close_button.setMinimumHeight(40)
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        self.close_button.hide() # Hide until complete
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def update_progress(self, progress: BatchProgress):
        """
        Update dialog with progress information.
        
        Args:
            progress: BatchProgress object
        """
        # Initialize start time on first update
        if self._start_time is None and progress.is_running:
            self._start_time = time.time()
        
        # Update progress bar
        if progress.total > 0:
            percent = int(progress.percent)
            self.progress_bar.setValue(percent)
            self.percent_label.setText(f"{percent}%")
            
            # Calculate ETA
            self._update_eta(progress)
        
        # Update current file with icon
        if progress.current_file:
            self.current_file_label.setText(f"🔄 처리 중: {progress.current_file}")
        
        # Update stats
        self.stats_widget.update_stats(progress)
        
        # Check if complete
        if not progress.is_running and progress.processed > 0:
            self._on_complete(progress)
    
    def _update_eta(self, progress: BatchProgress):
        """Calculate and update estimated time remaining."""
        if self._start_time is None or progress.processed == 0:
            self.eta_label.setText("⏱️ 예상 남은 시간: 계산 중...")
            return
        
        elapsed = time.time() - self._start_time
        if elapsed <= 0:
            return
        
        # Calculate average time per file
        avg_time_per_file = elapsed / progress.processed
        remaining_files = progress.total - progress.processed
        eta_seconds = avg_time_per_file * remaining_files
        
        # Format ETA
        if eta_seconds < 60:
            eta_str = f"{int(eta_seconds)}초"
        elif eta_seconds < 3600:
            minutes = int(eta_seconds // 60)
            seconds = int(eta_seconds % 60)
            eta_str = f"{minutes}분 {seconds}초"
        else:
            hours = int(eta_seconds // 3600)
            minutes = int((eta_seconds % 3600) // 60)
            eta_str = f"{hours}시간 {minutes}분"
        
        # Calculate processing speed
        speed = progress.processed / elapsed
        self.eta_label.setText(f"⏱️ 예상 남은 시간: {eta_str} ({speed:.1f} 파일/초)")
    
    def log_message(self, message: str, level: str = "info"):
        """
        Add message to log with enhanced styling.
        
        Args:
            message: Log message
            level: Log level (info, success, error, warning, skip)
        """
        # Color and icon mapping - using new theme colors
        styles = {
            "info": {"color": "#8b949e", "icon": "ℹ️"},
            "success": {"color": "#34d399", "icon": "✅"},  # Emerald
            "error": {"color": "#f87171", "icon": "❌"},    # Rose
            "warning": {"color": "#fbbf24", "icon": "⚠️"},  # Amber
            "skip": {"color": "#6b7280", "icon": "⏭️"},
        }
        style = styles.get(level, styles["info"])
        
        # Add colored message with icon
        html = f'<span style="color: {style["color"]}">{style["icon"]} {message}</span>'
        self.log_text.append(html)
        
        # Auto scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self._is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("⏳ 취소 중...")
        self.cancel_requested.emit()
    
    def _on_complete(self, progress: BatchProgress):
        """Handle processing completion."""
        self._is_complete = True
        
        # Update UI: Switch buttons
        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
        
        if progress.is_cancelled:
            self.setWindowTitle("⛔ 처리 중단됨")
            self.current_file_label.setText("⛔ 작업이 취소되었습니다")
            self.current_file_label.setStyleSheet("color: #f87171; font-weight: bold;")
        else:
            self.setWindowTitle("✅ 처리 완료")
            self.current_file_label.setText("🎉 모든 작업이 완료되었습니다!")
            self.current_file_label.setStyleSheet("color: #34d399; font-weight: bold;")
        
        self.progress_bar.setValue(100)
        self.percent_label.setText("완료! ✨")
        self.eta_label.setText("")
        
        # Calculate total time
        if self._start_time:
            total_time = time.time() - self._start_time
            if total_time < 60:
                time_str = f"{total_time:.1f}초"
            elif total_time < 3600:
                time_str = f"{int(total_time // 60)}분 {int(total_time % 60)}초"
            else:
                time_str = f"{int(total_time // 3600)}시간 {int((total_time % 3600) // 60)}분"
            self.eta_label.setText(f"⏱️ 총 소요 시간: {time_str}")
    
    def closeEvent(self, event):
        """Handle close event."""
        if not self._is_complete and not self._is_cancelled:
            # Prevent closing while processing
            event.ignore()
        else:
            event.accept()
    
    def reset(self):
        """Reset dialog for new processing session."""
        self._is_cancelled = False
        self._is_complete = False
        self._start_time = None
        
        self.setWindowTitle("🔄 처리 중...")
        self.current_file_label.setText("⏳ 대기 중...")
        self.current_file_label.setStyleSheet("color: #8b949e;")
        
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.eta_label.setText("⏱️ 예상 남은 시간: 계산 중...")
        self.log_text.clear()
        
        # Reset buttons
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("❌ 취소")
        self.close_button.setVisible(False)
        self.close_button.setEnabled(False)
        
        # Reset stats
        self.stats_widget.update_stats(BatchProgress())
