#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Processor for Photo Cropper v9.0.

Handles batch image processing with:
- Multithreading support (ThreadPoolExecutor)
- Progress tracking and cancellation
- Processing log integration
- Advanced image processing features
"""

import os
import shutil
import logging
import threading
import traceback
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from queue import Queue

from .image_processor import ImageProcessor, CropResult
from .settings import AppSettings
from .watermark_processor import WatermarkProcessor, TextWatermarkSettings, WatermarkPosition
from .resize_processor import ResizeProcessor, ResizeSettings as ResizeProcessorSettings, ResizeMode
from .multi_photo_detector import MultiPhotoDetector
from ..utils.file_helpers import SUPPORTED_IMAGE_FORMATS, get_image_files, classify_failed_files
from ..utils.processing_log import ProcessingLogger, get_processing_logger
from ..utils.naming_rules import NamingRule, NamingRuleEngine

logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class FileResult:
    """Result for individual file processing."""
    filename: str
    status: ProcessStatus
    message: str = ""
    output_path: str = ""
    file_size_kb: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class BatchProgress:
    """Batch processing progress information."""
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    current_file: str = ""
    is_running: bool = False
    is_cancelled: bool = False
    avg_time_per_file_ms: float = 0.0
    total_time_ms: float = 0.0
    
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
        return (self.success / self.processed) * 100
    
    @property
    def eta_seconds(self) -> float:
        """Estimated time remaining in seconds."""
        if self.processed == 0 or self.avg_time_per_file_ms == 0:
            return 0.0
        remaining = self.total - self.processed
        return (remaining * self.avg_time_per_file_ms) / 1000


class BatchProcessor:
    """
    Batch image processor with threading support.
    
    Features:
        - Background thread processing
        - Progress callbacks for UI updates
        - Cancellation support
        - Retry failed files
        - Backup creation
    """
    
    def __init__(self, settings: Optional[AppSettings] = None):
        """
        Initialize batch processor.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or AppSettings()
        self.processor = ImageProcessor(
            self.settings.algorithm,
            self.settings.processing,
            self.settings.advanced  # v9.0: Include advanced processing settings
        )
        
        self._progress = BatchProgress()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._processing_thread: Optional[threading.Thread] = None
        
        # Results tracking
        self._results: List[FileResult] = []
        self._failed_files: List[str] = []
        
        # Processing logger
        self._processing_logger: Optional[ProcessingLogger] = None
        
        # Naming rule engine
        self._naming_engine: Optional[NamingRuleEngine] = None
        
        # Thread pool for multithreading - dynamic based on CPU cores
        self._executor: Optional[ThreadPoolExecutor] = None
        self._thread_count = self._calculate_optimal_threads()
        
        # Time tracking for ETA
        self._processing_times: List[float] = []
        self._start_time: Optional[float] = None
        
        # Advanced processor (lazy init)
        self._advanced_processor = None
        
        # v9.0: Watermark and Resize processors (lazy init)
        self._watermark_processor: Optional[WatermarkProcessor] = None
        self._resize_processor: Optional[ResizeProcessor] = None
        self._multi_photo_detector: Optional[MultiPhotoDetector] = None
        
        # Callbacks
        self._on_progress: Optional[Callable[[BatchProgress], None]] = None
        self._on_file_complete: Optional[Callable[[FileResult], None]] = None
        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_complete: Optional[Callable[[BatchProgress, List[FileResult]], None]] = None
    
    def _calculate_optimal_threads(self) -> int:
        """Calculate optimal thread count based on CPU cores and settings."""
        # Get configured thread count from settings
        if hasattr(self.settings, 'performance') and self.settings.performance.thread_count > 0:
            return min(self.settings.performance.thread_count, os.cpu_count() or 4)
        
        # Auto-calculate: use CPU count but cap at 8 for I/O bound operations
        cpu_count = os.cpu_count() or 4
        return min(max(2, cpu_count - 1), 8)  # Leave one core free, max 8

    
    def set_callbacks(
        self,
        on_progress: Optional[Callable[[BatchProgress], None]] = None,
        on_file_complete: Optional[Callable[[FileResult], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[BatchProgress, List[FileResult]], None]] = None
    ):
        """Set callback functions for progress updates."""
        self._on_progress = on_progress
        self._on_file_complete = on_file_complete
        self._on_log = on_log
        self._on_complete = on_complete
    
    def update_settings(self, settings: AppSettings):
        """Update processor settings."""
        self.settings = settings
        self.processor.update_settings(
            settings.algorithm, 
            settings.processing,
            settings.advanced  # v9.0: Include advanced processing settings
        )
        
        # v9.0: Reset lazy-initialized processors so they use new settings
        self._multi_photo_detector = None
        self._watermark_processor = None
        self._resize_processor = None
    
    def _log(self, message: str, level: str = "info"):
        """Send log message through callback."""
        # Validate log level
        valid_levels = {"info", "error", "warning", "success", "skip"}
        level = level if level in valid_levels else "info"
        
        # v9.0: Thread-safe callback invocation
        with self._lock:
            callback = self._on_log
        self._safe_callback(callback, message, level)
        
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def _safe_callback(self, callback: Optional[Callable], *args, **kwargs):
        """
        Safely invoke a callback with exception handling.
        
        Args:
            callback: Callback function to call
            *args: Arguments to pass to callback
            **kwargs: Keyword arguments to pass to callback
        """
        if callback is None:
            return
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            logger.debug(traceback.format_exc())
            
    def cleanup(self):
        """Clean up resources and stop threads."""
        self.request_stop()
        if self._executor:
            self._executor.shutdown(wait=False)
        if self._processing_thread and self._processing_thread.is_alive():
            # Thread join is blocking, avoid if calling from UI thread
            pass
    
    def _update_progress(self):
        """Send progress update through callback."""
        with self._lock:
            progress_copy = BatchProgress(**self._progress.__dict__)
        self._safe_callback(self._on_progress, progress_copy)
    
    @property
    def is_running(self) -> bool:
        """Check if processing is in progress."""
        with self._lock:
            return self._progress.is_running
    
    @property
    def progress(self) -> BatchProgress:
        """Get current progress."""
        with self._lock:
            return BatchProgress(**self._progress.__dict__)
    
    @property
    def failed_files(self) -> List[str]:
        """Get list of failed files."""
        return self._failed_files.copy()
    
    @property
    def results(self) -> List[FileResult]:
        """Get all processing results."""
        return self._results.copy()
    
    def request_stop(self):
        """Request processing to stop."""
        self._stop_event.set()
        with self._lock:
            self._progress.is_cancelled = True
        self._log("작업 중단 요청됨", "warning")
    
    def _is_stop_requested(self) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()
    
    def get_image_files(self, input_dir: str) -> List[str]:
        """
        Get list of image files in directory.
        
        Args:
            input_dir: Input directory path
            
        Returns:
            List of image filenames
        """
        try:
            files = [
                f for f in os.listdir(input_dir)
                if f.lower().endswith(SUPPORTED_IMAGE_FORMATS)
            ]
            return sorted(files)
        except Exception as e:
            self._log(f"폴더 읽기 오류: {e}", "error")
            return []
    
    def start_async(
        self,
        input_dir: str,
        output_dir: str,
        file_list: Optional[List[str]] = None
    ) -> bool:
        """
        Start batch processing in background thread.
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            file_list: Specific files to process (None = all)
            
        Returns:
            True if started, False if already running
        """
        if self.is_running:
            self._log("이미 처리 중입니다", "warning")
            return False
        
        # Reset state
        self._stop_event.clear()
        self._results = []
        self._failed_files = []
        self._processing_times = []  # v9.0: Reset timing data
        self._start_time = time.time()  # v9.0: Track start time
        
        with self._lock:
            self._progress = BatchProgress(is_running=True)
        
        # Start thread
        self._processing_thread = threading.Thread(
            target=self._process_batch,
            args=(input_dir, output_dir, file_list),
            daemon=True
        )
        self._processing_thread.start()
        
        return True
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for processing to complete.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if completed, False if timeout
        """
        if self._processing_thread:
            self._processing_thread.join(timeout)
            return not self._processing_thread.is_alive()
        return True
    
    def _process_batch(
        self,
        input_dir: str,
        output_dir: str,
        file_list: Optional[List[str]] = None
    ):
        """Internal batch processing method (runs in thread)."""
        try:
            # Get file list
            if file_list is None:
                file_list = self.get_image_files(input_dir)
            
            if not file_list:
                self._log("처리할 이미지 파일이 없습니다", "warning")
                return
            
            # Create output directory
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self._log(f"출력 폴더 생성 실패: {e}", "error")
                return
            
            # Create backup directory if needed
            backup_dir = None
            if self.settings.create_backup:
                backup_dir = os.path.join(output_dir, "backup")
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    self._log(f"백업 폴더 생성: {backup_dir}", "info")
                except Exception as e:
                    self._log(f"백업 폴더 생성 실패: {e}", "warning")
                    backup_dir = None
            
            total = len(file_list)
            with self._lock:
                self._progress.total = total
                self._progress.processed = 0
            
            # v9.0: Start logging session if enabled
            if self.settings.file_management.enable_logging:
                try:
                    self._processing_logger = get_processing_logger(
                        self.settings.file_management.log_directory or output_dir
                    )
                    self._processing_logger.start_session(input_dir, output_dir, total)
                except Exception as e:
                    logger.warning(f"Failed to start processing logger: {e}")
            
            self._log(f"총 {total}개 파일 처리 시작", "info")
            self._update_progress()
            
            # Process each file
            for i, filename in enumerate(file_list):
                if self._is_stop_requested():
                    self._log("작업이 중단되었습니다", "warning")
                    break
                
                result = self._process_single_file(
                    input_dir, output_dir, filename, backup_dir, i + 1, total
                )
                # Thread-safe list operations
                with self._lock:
                    self._results.append(result)
                    
                    if result.status == ProcessStatus.FAILED:
                        self._failed_files.append(filename)
                    
                    # v9.0: Track processing times for accurate ETA
                    if result.processing_time_ms > 0:
                        self._processing_times.append(result.processing_time_ms)
                
                # Update progress
                with self._lock:
                    self._progress.processed = i + 1
                    self._progress.current_file = filename
                    
                    if result.status == ProcessStatus.SUCCESS:
                        self._progress.success += 1
                    elif result.status == ProcessStatus.FAILED:
                        self._progress.failed += 1
                    elif result.status == ProcessStatus.SKIPPED:
                        self._progress.skipped += 1
                    
                    # v9.0: Calculate average processing time for ETA
                    if self._processing_times:
                        self._progress.avg_time_per_file_ms = sum(self._processing_times) / len(self._processing_times)
                    if self._start_time:
                        self._progress.total_time_ms = (time.time() - self._start_time) * 1000
                
                # v9.0: Log processing result to file
                if self._processing_logger is not None:
                    try:
                        if result.status == ProcessStatus.SUCCESS:
                            self._processing_logger.log_success(
                                input_file=os.path.join(input_dir, filename),
                                output_file=result.output_path,
                                detection_stage=result.message.replace("탐지: ", "") if "탐지" in result.message else "Unknown",
                                processing_time_ms=result.processing_time_ms,
                                file_size_before_kb=0.0,  # Not tracked per file currently
                                file_size_after_kb=result.file_size_kb
                            )
                        elif result.status == ProcessStatus.FAILED:
                            self._processing_logger.log_failure(
                                input_file=os.path.join(input_dir, filename),
                                error_message=result.message,
                                processing_time_ms=result.processing_time_ms
                            )
                        elif result.status == ProcessStatus.SKIPPED:
                            self._processing_logger.log_skipped(
                                input_file=os.path.join(input_dir, filename),
                                reason=result.message
                            )
                    except Exception as log_err:
                        logger.debug(f"Failed to log processing result: {log_err}")
                
                self._update_progress()
                
                self._safe_callback(self._on_file_complete, result)
            
            # Completion
            self._log("=" * 50, "info")
            if self._is_stop_requested():
                self._log("작업이 중단되었습니다", "warning")
            else:
                self._log("모든 작업 완료!", "success")
            
            with self._lock:
                progress = self._progress
                self._log(
                    f"최종 통계 - 총: {progress.processed}, 성공: {progress.success}, "
                    f"실패: {progress.failed}, 건너뜀: {progress.skipped}",
                    "info"
                )
            
            if self._failed_files:
                self._log(f"실패한 파일: {len(self._failed_files)}개", "warning")
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self._log(f"배치 처리 오류: {e}", "error")
        finally:
            with self._lock:
                self._progress.is_running = False
            
            # v9.0: Save processing log if enabled
            if self._processing_logger is not None:
                try:
                    session = self._processing_logger.end_session()
                    if session:
                        log_format = self.settings.file_management.log_format.lower()
                        if log_format == "csv":
                            self._processing_logger.save_to_csv()
                        else:
                            self._processing_logger.save_to_json()
                        self._log("📋 처리 로그 저장 완료", "info")
                except Exception as e:
                    logger.warning(f"Failed to save processing log: {e}")
            
            self._safe_callback(self._on_complete, self.progress, self._results)
    
    def _process_single_file(
        self,
        input_dir: str,
        output_dir: str,
        filename: str,
        backup_dir: Optional[str],
        current: int,
        total: int
    ) -> FileResult:
        """Process a single file."""
        start_time = time.time()
        
        input_path = os.path.join(input_dir, filename)
        
        self._log(f"[{current}/{total}] 처리 중: {filename}", "info")
        
        # Size filtering
        if self.settings.filter.skip_small_images:
            info = self.processor.get_image_info(input_path)
            if info:
                w, h, _ = info
                min_size = self.settings.filter.min_image_size
                if w < min_size or h < min_size:
                    self._log(f"  건너뜀: 크기 {w}x{h} < {min_size}px", "skip")
                    return FileResult(
                        filename=filename,
                        status=ProcessStatus.SKIPPED,
                        message=f"크기 미달 ({w}x{h})"
                    )
        
        # Skip already processed files
        if self.settings.filter.skip_processed:
            base_name = os.path.splitext(filename)[0]
            ext = "." + self.settings.output.output_format.lower()
            expected_output = os.path.join(output_dir, f"{base_name}_cropped{ext}")
            if os.path.exists(expected_output):
                self._log(f"  건너뜀: 이미 처리됨 - {base_name}_cropped{ext}", "skip")
                return FileResult(
                    filename=filename,
                    status=ProcessStatus.SKIPPED,
                    message="이미 처리됨"
                )
        
        # Backup
        if backup_dir:
            try:
                backup_path = os.path.join(backup_dir, filename)
                shutil.copy2(input_path, backup_path)
            except Exception as e:
                self._log(f"  백업 실패: {e}", "warning")
        
        # v9.0: Multi-photo detection mode
        if self.settings.multi_photo.enabled:
            try:
                return self._process_multi_photo(
                    input_path, output_dir, filename, current, total, start_time
                )
            except Exception as e:
                self._log(f"  멀티포토 처리 오류: {e}, 단일 모드로 전환", "warning")
        
        # Process image (standard single-photo mode)
        result = self.processor.process_image(input_path)
        
        processing_time = (time.time() - start_time) * 1000
        
        if result.success and result.image is not None:
            processed_image = result.image
            
            # v9.0: Apply resize if enabled
            if self.settings.resize.enabled:
                try:
                    if self._resize_processor is None:
                        self._resize_processor = ResizeProcessor()
                    
                    # Build resize settings from app settings
                    resize_settings = ResizeProcessorSettings(
                        enabled=True,
                        mode=ResizeMode(self.settings.resize.mode) if self.settings.resize.mode != "none" else ResizeMode.NONE,
                        width=self.settings.resize.width,
                        height=self.settings.resize.height,
                        percentage=self.settings.resize.percentage,
                        max_dimension=self.settings.resize.max_dimension,
                        upscale_allowed=self.settings.resize.upscale_allowed,
                        maintain_aspect=self.settings.resize.maintain_aspect,
                        jpeg_compatible=self.settings.resize.jpeg_compatible
                    )
                    
                    resize_result = self._resize_processor.resize(processed_image, resize_settings)
                    if resize_result.success and resize_result.image is not None:
                        processed_image = resize_result.image
                        self._log(f"  ↔️ 리사이즈 적용: {resize_result.original_size} → {resize_result.new_size}", "info")
                except Exception as e:
                    self._log(f"  ⚠️ 리사이즈 오류: {e}", "warning")
            
            # v9.0: Apply watermark if enabled
            if self.settings.watermark.enabled:
                try:
                    if self._watermark_processor is None:
                        self._watermark_processor = WatermarkProcessor()
                    
                    # Check for tiled watermark first
                    if self.settings.watermark.tiled and self.settings.watermark.text:
                        processed_image = self._watermark_processor.create_tiled_watermark(
                            processed_image,
                            self.settings.watermark.text,
                            spacing=self.settings.watermark.tile_spacing,
                            angle=self.settings.watermark.tile_angle,
                            font_scale=self.settings.watermark.text_font_scale,
                            color=(
                                self.settings.watermark.text_color_r,
                                self.settings.watermark.text_color_g,
                                self.settings.watermark.text_color_b
                            ),
                            opacity=self.settings.watermark.opacity
                        )
                        self._log("  💧 타일 워터마크 적용", "info")
                    else:
                        # Apply text watermark
                        if self.settings.watermark.text:
                            text_settings = TextWatermarkSettings(
                                text=self.settings.watermark.text,
                                font_scale=self.settings.watermark.text_font_scale,
                                color=(
                                    self.settings.watermark.text_color_r,
                                    self.settings.watermark.text_color_g,
                                    self.settings.watermark.text_color_b
                                ),
                                opacity=self.settings.watermark.opacity,
                                position=WatermarkPosition(self.settings.watermark.position),
                                margin=self.settings.watermark.margin,
                                shadow=self.settings.watermark.text_shadow
                            )
                            processed_image = self._watermark_processor.apply_text_watermark(
                                processed_image, text_settings
                            )
                            self._log(f"  💧 텍스트 워터마크 적용: '{self.settings.watermark.text}'", "info")
                except Exception as e:
                    self._log(f"  ⚠️ 워터마크 오류: {e}", "warning")
            
            # Generate output filename
            ext = "." + self.settings.output.output_format.lower()
            base_name = os.path.splitext(filename)[0]
            
            if self.settings.output.add_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{base_name}_cropped_{timestamp}{ext}"
            else:
                output_filename = f"{base_name}_cropped{ext}"
            
            output_path = os.path.join(output_dir, output_filename)
            
            # Save (use processed_image which may have watermark/resize applied)
            success, msg, file_size = self.processor.save_image(
                processed_image,
                output_path,
                self.settings.output.output_format,
                self.settings.output.jpg_quality,
                self.settings.output.png_compression,
                self.settings.output.webp_quality
            )
            
            if success:
                self._log(f"  ✓ 성공: {output_filename} ({file_size:.1f} KB)", "success")
                return FileResult(
                    filename=filename,
                    status=ProcessStatus.SUCCESS,
                    message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                    output_path=output_path,
                    file_size_kb=file_size,
                    processing_time_ms=processing_time
                )
            else:
                self._log(f"  ✗ 저장 실패: {msg}", "error")
                return FileResult(
                    filename=filename,
                    status=ProcessStatus.FAILED,
                    message=f"저장 실패: {msg}",
                    processing_time_ms=processing_time
                )
        else:
            self._log(f"  ✗ 실패: {result.message}", "error")
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message=result.message,
                processing_time_ms=processing_time
            )
    
    def _process_multi_photo(
        self,
        input_path: str,
        output_dir: str,
        filename: str,
        current: int,
        total: int,
        start_time: float
    ) -> FileResult:
        """
        Process a single file with multi-photo detection.
        Detects multiple photos in a single scan and saves each separately.
        """
        import cv2
        import numpy as np
        
        # Initialize detector if needed
        if self._multi_photo_detector is None:
            self._multi_photo_detector = MultiPhotoDetector(
                min_area_ratio=self.settings.multi_photo.min_area_ratio,
                max_area_ratio=self.settings.multi_photo.max_area_ratio,
                min_photos=self.settings.multi_photo.min_photos,
                max_photos=self.settings.multi_photo.max_photos,
                merge_distance=self.settings.multi_photo.merge_distance
            )
        
        # Load image with Unicode support
        img_array = np.fromfile(input_path, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if image is None:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message="이미지 로드 실패",
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Detect multiple photos
        detection_result = self._multi_photo_detector.detect(image)
        
        if not detection_result.success or detection_result.total_found == 0:
            self._log(f"  멀티포토: 사진 감지 안됨, 단일 모드로 처리", "info")
            # Fall through to standard processing
            result = self.processor.process_image(input_path)
            processing_time = (time.time() - start_time) * 1000
            
            if result.success and result.image is not None:
                return self._save_single_result(result, output_dir, filename, processing_time)
            else:
                return FileResult(
                    filename=filename,
                    status=ProcessStatus.FAILED,
                    message=result.message,
                    processing_time_ms=processing_time
                )
        
        # Crop and save each detected photo
        self._log(f"  📷 멀티포토: {detection_result.total_found}개 사진 감지", "info")
        
        cropped_photos = self._multi_photo_detector.crop_photos(
            image, detection_result.photos, padding=10
        )
        
        saved_count = 0
        ext = "." + self.settings.output.output_format.lower()
        base_name = os.path.splitext(filename)[0]
        
        for idx, (cropped_img, photo_info) in enumerate(cropped_photos, 1):
            output_filename = f"{base_name}_photo{idx:02d}{ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            # Apply watermark/resize if enabled
            processed_img = cropped_img
            if self.settings.resize.enabled and self._resize_processor:
                resize_result = self._resize_processor.resize(processed_img)
                if resize_result.success:
                    processed_img = resize_result.image
            
            if self.settings.watermark.enabled and self._watermark_processor and self.settings.watermark.text:
                text_settings = TextWatermarkSettings(
                    text=self.settings.watermark.text,
                    font_scale=self.settings.watermark.text_font_scale,
                    opacity=self.settings.watermark.opacity,
                    position=WatermarkPosition(self.settings.watermark.position)
                )
                processed_img = self._watermark_processor.apply_text_watermark(processed_img, text_settings)
            
            # Save
            success, msg, file_size = self.processor.save_image(
                processed_img,
                output_path,
                self.settings.output.output_format,
                self.settings.output.jpg_quality,
                self.settings.output.png_compression,
                self.settings.output.webp_quality
            )
            
            if success:
                saved_count += 1
                self._log(f"    ✓ 사진 {idx}: {output_filename}", "success")
        
        processing_time = (time.time() - start_time) * 1000
        
        if saved_count > 0:
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"멀티포토: {saved_count}/{detection_result.total_found}개 저장",
                processing_time_ms=processing_time
            )
        else:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message="멀티포토 저장 실패",
                processing_time_ms=processing_time
            )
    
    def _save_single_result(
        self,
        result: CropResult,
        output_dir: str,
        filename: str,
        processing_time: float
    ) -> FileResult:
        """Save a single processed result."""
        ext = "." + self.settings.output.output_format.lower()
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_cropped{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        success, msg, file_size = self.processor.save_image(
            result.image,
            output_path,
            self.settings.output.output_format,
            self.settings.output.jpg_quality,
            self.settings.output.png_compression,
            self.settings.output.webp_quality
        )
        
        if success:
            return FileResult(
                filename=filename,
                status=ProcessStatus.SUCCESS,
                message=f"탐지: {result.detection_stage.value if result.detection_stage else 'Unknown'}",
                output_path=output_path,
                file_size_kb=file_size,
                processing_time_ms=processing_time
            )
        else:
            return FileResult(
                filename=filename,
                status=ProcessStatus.FAILED,
                message=f"저장 실패: {msg}",
                processing_time_ms=processing_time
            )
