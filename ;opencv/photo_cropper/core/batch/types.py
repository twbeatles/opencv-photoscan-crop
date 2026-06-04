from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProcessStatus(Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class FileResult:
    """Result for individual file processing."""

    filename: str
    status: ProcessStatus
    source_path: str = ""
    message: str = ""
    output_path: str = ""
    output_paths: list[str] = field(default_factory=list)
    file_size_kb: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class BatchProgress:
    """Batch processing progress information."""

    total: int = 0
    processed: int = 0
    success: int = 0
    partial_success: int = 0
    failed: int = 0
    skipped: int = 0
    current_file: str = ""
    is_running: bool = False
    is_cancelled: bool = False
    avg_time_per_file_ms: float = 0.0
    total_time_ms: float = 0.0
    fatal_error: bool = False
    fatal_message: str = ""

    @property
    def percent(self) -> float:
        """Get progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.processed / self.total) * 100

    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        if self.processed == 0:
            return 0.0
        return ((self.success + self.partial_success) / self.processed) * 100

    @property
    def eta_seconds(self) -> float:
        """Estimated time remaining in seconds."""
        if self.processed == 0 or self.avg_time_per_file_ms == 0:
            return 0.0
        remaining = self.total - self.processed
        return (remaining * self.avg_time_per_file_ms) / 1000


__all__ = ["ProcessStatus", "FileResult", "BatchProgress"]
