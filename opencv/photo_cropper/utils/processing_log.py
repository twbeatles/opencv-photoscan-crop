#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processing Log Module for Photo Cropper.

Provides comprehensive logging of image processing operations.
"""

import os
import json
import csv
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class ProcessingLogEntry:
    """Individual processing log entry.
    
    Attributes:
        timestamp: When the processing occurred
        input_file: Path to input file
        output_file: Path to output file
        status: Processing status
        detection_stage: Which detection algorithm succeeded
        processing_time_ms: Processing duration in milliseconds
        file_size_before_kb: Input file size in KB
        file_size_after_kb: Output file size in KB
        image_dimensions_before: Original image dimensions (WxH)
        image_dimensions_after: Output image dimensions (WxH)
        error_message: Error message if failed
        settings_used: Settings snapshot (optional)
    """
    timestamp: datetime
    input_file: str
    output_file: str = ""
    status: str = "pending"
    detection_stage: str = ""
    processing_time_ms: float = 0.0
    file_size_before_kb: float = 0.0
    file_size_after_kb: float = 0.0
    image_dimensions_before: str = ""
    image_dimensions_after: str = ""
    error_message: str = ""
    settings_used: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingLogEntry':
        """Create from dictionary."""
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ProcessingSession:
    """Processing session containing multiple log entries.
    
    Represents a single batch processing run.
    """
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_directory: str = ""
    output_directory: str = ""
    total_files: int = 0
    processed_files: int = 0
    success_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    entries: List[ProcessingLogEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'input_directory': self.input_directory,
            'output_directory': self.output_directory,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'success_count': self.success_count,
            'partial_count': self.partial_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'entries': [e.to_dict() for e in self.entries]
        }
        return data


class ProcessingLogger:
    """Manages processing logs with file persistence.
    
    Features:
        - Session-based logging
        - JSON and CSV export
        - Summary statistics
        - Log rotation
    """
    
    def __init__(self, log_directory: Optional[str] = None):
        """Initialize processing logger.
        
        Args:
            log_directory: Directory for log files. Uses current dir if None.
        """
        self.log_directory = log_directory or os.getcwd()
        self._current_session: Optional[ProcessingSession] = None
        self._all_sessions: List[ProcessingSession] = []
    
    def start_session(self, input_dir: str, output_dir: str,
                     total_files: int) -> str:
        """
        Start a new processing session.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            total_files: Total number of files to process
            
        Returns:
            Session ID
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self._current_session = ProcessingSession(
            session_id=session_id,
            start_time=datetime.now(),
            input_directory=input_dir,
            output_directory=output_dir,
            total_files=total_files
        )
        
        logger.info(f"Started logging session: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[ProcessingSession]:
        """
        End the current processing session.
        
        Returns:
            Completed session or None if no active session
        """
        if self._current_session is None:
            return None
        
        self._current_session.end_time = datetime.now()
        
        # Calculate summary
        for entry in self._current_session.entries:
            if entry.status == ProcessingStatus.SUCCESS.value:
                self._current_session.success_count += 1
            elif entry.status == ProcessingStatus.PARTIAL_SUCCESS.value:
                self._current_session.partial_count += 1
            elif entry.status == ProcessingStatus.FAILED.value:
                self._current_session.failed_count += 1
            elif entry.status == ProcessingStatus.SKIPPED.value:
                self._current_session.skipped_count += 1
        
        self._current_session.processed_files = len(self._current_session.entries)
        
        # Store session
        completed_session = self._current_session
        self._all_sessions.append(completed_session)
        self._current_session = None
        
        logger.info(f"Ended logging session: {completed_session.session_id}")
        return completed_session
    
    def log_entry(self, entry: ProcessingLogEntry):
        """
        Add a log entry to the current session.
        
        Args:
            entry: Log entry to add
        """
        if self._current_session is None:
            logger.warning("No active session, creating temporary session")
            self.start_session("", "", 0)
        session = self._current_session
        if session is None:
            return
        session.entries.append(entry)
    
    def log_success(self, input_file: str, output_file: str,
                   detection_stage: str, processing_time_ms: float,
                   file_size_before_kb: float, file_size_after_kb: float,
                   dimensions_before: str = "", dimensions_after: str = ""):
        """Convenience method to log successful processing."""
        entry = ProcessingLogEntry(
            timestamp=datetime.now(),
            input_file=input_file,
            output_file=output_file,
            status=ProcessingStatus.SUCCESS.value,
            detection_stage=detection_stage,
            processing_time_ms=processing_time_ms,
            file_size_before_kb=file_size_before_kb,
            file_size_after_kb=file_size_after_kb,
            image_dimensions_before=dimensions_before,
            image_dimensions_after=dimensions_after
        )
        self.log_entry(entry)
    
    def log_failure(self, input_file: str, error_message: str,
                   processing_time_ms: float = 0.0):
        """Convenience method to log failed processing."""
        entry = ProcessingLogEntry(
            timestamp=datetime.now(),
            input_file=input_file,
            status=ProcessingStatus.FAILED.value,
            error_message=error_message,
            processing_time_ms=processing_time_ms
        )
        self.log_entry(entry)

    def log_partial(
        self,
        input_file: str,
        output_file: str,
        detail_message: str,
        processing_time_ms: float = 0.0,
        file_size_before_kb: float = 0.0,
        file_size_after_kb: float = 0.0,
    ):
        """Convenience method to log partially successful processing."""
        entry = ProcessingLogEntry(
            timestamp=datetime.now(),
            input_file=input_file,
            output_file=output_file,
            status=ProcessingStatus.PARTIAL_SUCCESS.value,
            error_message=detail_message,
            processing_time_ms=processing_time_ms,
            file_size_before_kb=file_size_before_kb,
            file_size_after_kb=file_size_after_kb,
        )
        self.log_entry(entry)

    def log_skipped(self, input_file: str, reason: str):
        """Convenience method to log skipped file."""
        entry = ProcessingLogEntry(
            timestamp=datetime.now(),
            input_file=input_file,
            status=ProcessingStatus.SKIPPED.value,
            error_message=reason
        )
        self.log_entry(entry)
    
    @property
    def current_session(self) -> Optional[ProcessingSession]:
        """Get current active session."""
        return self._current_session
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for current session.
        
        Returns:
            Dictionary with summary statistics
        """
        if self._current_session is None:
            return {}
        
        session = self._current_session
        entries = session.entries
        
        success_entries = [e for e in entries if e.status == ProcessingStatus.SUCCESS.value]
        partial_entries = [
            e for e in entries if e.status == ProcessingStatus.PARTIAL_SUCCESS.value
        ]
        failed_entries = [e for e in entries if e.status == ProcessingStatus.FAILED.value]
        
        # Calculate statistics
        total_time_ms = sum(e.processing_time_ms for e in entries)
        avg_time_ms = total_time_ms / len(entries) if entries else 0
        
        total_input_kb = sum(e.file_size_before_kb for e in success_entries)
        total_output_kb = sum(e.file_size_after_kb for e in success_entries)
        
        # Detection stage breakdown
        stage_counts: Dict[str, int] = {}
        for entry in success_entries:
            stage = entry.detection_stage or "Unknown"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        return {
            'session_id': session.session_id,
            'total_files': session.total_files,
            'processed': len(entries),
            'success': len(success_entries),
            'partial_success': len(partial_entries),
            'failed': len(failed_entries),
            'skipped': len([e for e in entries if e.status == ProcessingStatus.SKIPPED.value]),
            'success_rate': (
                (len(success_entries) + len(partial_entries)) / len(entries) * 100
                if entries
                else 0
            ),
            'total_processing_time_ms': total_time_ms,
            'average_processing_time_ms': avg_time_ms,
            'total_input_size_kb': total_input_kb,
            'total_output_size_kb': total_output_kb,
            'size_reduction_percent': (1 - total_output_kb / total_input_kb) * 100 if total_input_kb > 0 else 0,
            'detection_stages': stage_counts,
            'failed_files': [e.input_file for e in failed_entries]
        }
    
    def save_to_json(self, path: Optional[str] = None,
                    include_all_sessions: bool = False) -> str:
        """
        Save log to JSON file.
        
        Args:
            path: Output file path. Auto-generated if None.
            include_all_sessions: Include all sessions or just current
            
        Returns:
            Path to saved file
        """
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.log_directory, f"processing_log_{timestamp}.json")
        
        # Prepare data
        data: Dict[str, Any]
        if include_all_sessions:
            data = {
                'sessions': [s.to_dict() for s in self._all_sessions]
            }
            if self._current_session:
                data['sessions'].append(self._current_session.to_dict())
        else:
            session = self._current_session or (self._all_sessions[-1] if self._all_sessions else None)
            if session:
                data = session.to_dict()
            else:
                data = {'error': 'No session data available'}
        
        # Add summary
        data['summary'] = self.get_summary()
        
        # Write file
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved JSON log to: {path}")
        return path
    
    def save_to_csv(self, path: Optional[str] = None) -> str:
        """
        Save log entries to CSV file.
        
        Args:
            path: Output file path. Auto-generated if None.
            
        Returns:
            Path to saved file
        """
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.log_directory, f"processing_log_{timestamp}.csv")
        
        # Collect entries
        entries = []
        if self._current_session:
            entries.extend(self._current_session.entries)
        for session in self._all_sessions:
            entries.extend(session.entries)
        
        if not entries:
            logger.warning("No entries to save")
            return ""
        
        # CSV columns
        fieldnames = [
            'timestamp', 'input_file', 'output_file', 'status',
            'detection_stage', 'processing_time_ms',
            'file_size_before_kb', 'file_size_after_kb',
            'image_dimensions_before', 'image_dimensions_after',
            'error_message'
        ]
        
        # Write CSV
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in entries:
                row = entry.to_dict()
                row = {k: v for k, v in row.items() if k in fieldnames}
                writer.writerow(row)
        
        logger.info(f"Saved CSV log to: {path}")
        return path
    
    def get_failed_files(self) -> List[str]:
        """Get list of failed file paths from current session."""
        if self._current_session is None:
            return []
        
        return [
            e.input_file for e in self._current_session.entries
            if e.status == ProcessingStatus.FAILED.value
        ]


# Singleton instance
_logger_instance: Optional[ProcessingLogger] = None


def get_processing_logger(log_directory: Optional[str] = None) -> ProcessingLogger:
    """Get or create processing logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ProcessingLogger(log_directory)
    return _logger_instance


def reset_processing_logger_for_tests() -> None:
    global _logger_instance
    _logger_instance = None
