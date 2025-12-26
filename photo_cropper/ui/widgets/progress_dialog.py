#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Dialog for Photo Cropper.

Provides batch processing progress display with cancel support.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QTextEdit, QGroupBox,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import time

from ...core.batch_processor import BatchProgress, FileResult, ProcessStatus


class StatsWidget(QFrame):
    """Widget to display processing statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(self)
        
        self.total_label = self._create_stat("총", "#888888")
        self.success_label = self._create_stat("성공", "#00c880")
        self.failed_label = self._create_stat("실패", "#e94560")
        self.skipped_label = self._create_stat("건너뜀", "#ffa500")
        self.rate_label = self._create_stat("성공률", "#0f3460")
        
        layout.addWidget(self.total_label)
        layout.addWidget(self.success_label)
        layout.addWidget(self.failed_label)
        layout.addWidget(self.skipped_label)
        layout.addWidget(self.rate_label)
    
    def _create_stat(self, name: str, color: str) -> QLabel:
        """Create a stat label."""
        label = QLabel(f"{name}: 0")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"font-weight: bold;")
        return label
    
    def update_stats(self, progress: BatchProgress):
        """Update all stat labels."""
        self.total_label.setText(f"총: {progress.processed}/{progress.total}")
        self.success_label.setText(f"성공: {progress.success}")
        self.success_label.setStyleSheet("color: #00c880; font-weight: bold;")
        self.failed_label.setText(f"실패: {progress.failed}")
        self.failed_label.setStyleSheet("color: #e94560; font-weight: bold;")
        self.skipped_label.setText(f"건너뜀: {progress.skipped}")
        self.skipped_label.setStyleSheet("color: #ffa500; font-weight: bold;")
        self.rate_label.setText(f"성공률: {progress.success_rate:.1f}%")


class ProgressDialog(QDialog):
    """
    Modal dialog showing batch processing progress.
    
    Signals:
        cancel_requested: Emitted when cancel is clicked
    """
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("처리 중...")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self._is_cancelled = False
        self._is_complete = False
        self._start_time = None  # ETA 계산을 위한 시작 시간
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        
        # Current file label
        self.current_file_label = QLabel("대기 중...")
        self.current_file_label.setWordWrap(True)
        layout.addWidget(self.current_file_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Progress percentage
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.percent_label.setFont(font)
        layout.addWidget(self.percent_label)
        
        # ETA label
        self.eta_label = QLabel("예상 남은 시간: 계산 중...")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eta_label.setObjectName("subtitleLabel")
        layout.addWidget(self.eta_label)
        
        # Stats widget
        self.stats_widget = StatsWidget()
        layout.addWidget(self.stats_widget)
        
        # Log area
        log_group = QGroupBox("처리 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("primaryButton")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        self.close_button = QPushButton("닫기")
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
        
        # Update current file
        if progress.current_file:
            self.current_file_label.setText(f"처리 중: {progress.current_file}")
        
        # Update stats
        self.stats_widget.update_stats(progress)
        
        # Check if complete
        if not progress.is_running and progress.processed > 0:
            self._on_complete(progress)
    
    def _update_eta(self, progress: BatchProgress):
        """
        Calculate and update estimated time remaining.
        
        Args:
            progress: Current batch progress
        """
        if self._start_time is None or progress.processed == 0:
            self.eta_label.setText("예상 남은 시간: 계산 중...")
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
        self.eta_label.setText(f"예상 남은 시간: {eta_str} ({speed:.1f} 파일/초)")
    
    def log_message(self, message: str, level: str = "info"):
        """
        Add message to log.
        
        Args:
            message: Log message
            level: Log level (info, success, error, warning, skip)
        """
        # Color mapping
        colors = {
            "info": "#888888",
            "success": "#00c880",
            "error": "#e94560",
            "warning": "#ffa500",
            "skip": "#666666",
        }
        color = colors.get(level, "#888888")
        
        # Add colored message
        html = f'<span style="color: {color}">{message}</span>'
        self.log_text.append(html)
        
        # Auto scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self._is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("취소 중...")
        self.cancel_requested.emit()
    
    def _on_complete(self, progress: BatchProgress):
        """Handle processing completion."""
        self._is_complete = True
        
        # Update UI
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
        
        if progress.is_cancelled:
            self.setWindowTitle("처리 중단됨")
            self.current_file_label.setText("작업이 취소되었습니다")
        else:
            self.setWindowTitle("처리 완료")
            self.current_file_label.setText("모든 작업이 완료되었습니다")
        
        self.progress_bar.setValue(100)
        self.percent_label.setText("완료")
    
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
        
        self.setWindowTitle("처리 중...")
        self.current_file_label.setText("대기 중...")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.eta_label.setText("예상 남은 시간: 계산 중...")
        self.log_text.clear()
        
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("취소")
        self.close_button.setEnabled(False)
        
        # Reset stats
        self.stats_widget.update_stats(BatchProgress())
