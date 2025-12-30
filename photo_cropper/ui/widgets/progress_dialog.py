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
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Icon and value row
        value_layout = QHBoxLayout()
        value_layout.setSpacing(6)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 14))
        value_layout.addWidget(icon_label)
        
        self.value_label = QLabel("0")
        self.value_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        value_layout.addWidget(self.value_label)
        value_layout.addStretch()
        
        layout.addLayout(value_layout)
        
        # Label
        self.label_text = QLabel(label)
        self.label_text.setFont(QFont("Segoe UI", 9))
        self.label_text.setStyleSheet("color: #888888;")
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
        
        # Create stat cards with icons
        self.total_card = StatCard("📊", "처리됨", "#888888", self)
        self.success_card = StatCard("✅", "성공", "#00c880", self)
        self.failed_card = StatCard("❌", "실패", "#e94560", self)
        self.skipped_card = StatCard("⏭️", "건너뜀", "#ffa500", self)
        self.rate_card = StatCard("📈", "성공률", "#0f3460", self)
        
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
        layout.setSpacing(12)
        
        # Header with current file
        header_frame = QFrame()
        header_frame.setObjectName("statsFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        self.current_file_label = QLabel("⏳ 대기 중...")
        self.current_file_label.setFont(QFont("Segoe UI", 11))
        self.current_file_label.setWordWrap(True)
        header_layout.addWidget(self.current_file_label)
        
        layout.addWidget(header_frame)
        
        # Progress bar with percentage
        progress_frame = QFrame()
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(20)
        progress_layout.addWidget(self.progress_bar)
        
        # Progress percentage and ETA row
        progress_info_layout = QHBoxLayout()
        
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        progress_info_layout.addWidget(self.percent_label)
        
        progress_info_layout.addStretch()
        
        self.eta_label = QLabel("⏱️ 예상 남은 시간: 계산 중...")
        self.eta_label.setFont(QFont("Segoe UI", 10))
        self.eta_label.setObjectName("subtitleLabel")
        progress_info_layout.addWidget(self.eta_label)
        
        progress_layout.addLayout(progress_info_layout)
        layout.addWidget(progress_frame)
        
        # Stats widget
        self.stats_widget = StatsWidget()
        layout.addWidget(self.stats_widget)
        
        # Log area with improved styling
        log_group = QGroupBox("📋 처리 로그")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 16, 8, 8)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(180)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Buttons with improved styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("❌ 취소")
        self.cancel_button.setObjectName("primaryButton")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        self.close_button = QPushButton("✅ 닫기")
        self.close_button.setObjectName("successButton")
        self.close_button.setMinimumWidth(100)
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
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
        # Color and icon mapping
        styles = {
            "info": {"color": "#888888", "icon": "ℹ️"},
            "success": {"color": "#00c880", "icon": "✅"},
            "error": {"color": "#e94560", "icon": "❌"},
            "warning": {"color": "#ffa500", "icon": "⚠️"},
            "skip": {"color": "#666666", "icon": "⏭️"},
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
        
        # Update UI
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
        
        if progress.is_cancelled:
            self.setWindowTitle("⛔ 처리 중단됨")
            self.current_file_label.setText("⛔ 작업이 취소되었습니다")
        else:
            self.setWindowTitle("✅ 처리 완료")
            self.current_file_label.setText("🎉 모든 작업이 완료되었습니다!")
        
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
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.eta_label.setText("⏱️ 예상 남은 시간: 계산 중...")
        self.log_text.clear()
        
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("❌ 취소")
        self.close_button.setEnabled(False)
        
        # Reset stats
        self.stats_widget.update_stats(BatchProgress())
