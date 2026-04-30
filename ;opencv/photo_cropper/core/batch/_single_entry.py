# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import os
import shutil
import logging
import threading
import traceback
import time
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, CancelledError
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from queue import Queue

from ..image import ImageProcessor, CropResult
from ..settings_model import AppSettings
from ..face import FaceDetector
from ..image_classifier import ImageClassifier, ImageCategory, get_classifier
from ..smart_enhancer import SmartEnhancer, EnhancementPreset
from ..watermark_processor import (
    WatermarkProcessor,
    TextWatermarkSettings,
    ImageWatermarkSettings,
    WatermarkPosition,
)
from ..resize_processor import (
    ResizeProcessor,
    ResizeSettings as ResizeProcessorSettings,
    ResizeMode,
)
from ..multi_photo_detector import MultiPhotoDetector
from ...utils.file_helpers import (
    SUPPORTED_IMAGE_FORMATS,
    build_recursive_excluded_roots,
    get_image_files,
    classify_failed_files,
    get_unique_filename,
    relative_display_path,
    relative_parent_dir,
)
from ...utils.processing_log import ProcessingLogger, get_processing_logger
from ...utils.naming_rules import NamingRule, NamingRuleEngine
from ...utils.path_validation import resolve_category_folder_map
from ..processed_index import (
    ProcessedIndexStore,
    RECORD_STATUS_PARTIAL,
    RECORD_STATUS_SUCCESS,
    build_pipeline_signature,
)
from .types import BatchProgress, FileResult, ProcessStatus

logger = logging.getLogger(__name__)


class BatchProcessorSingleEntryMixin:
    def process_single(
        self: Any,
        input_path: str,
        output_dir: str,
        input_root: Optional[str] = None,
    ) -> FileResult:
        """Process one file synchronously using the same pipeline as batch mode."""
        normalized_input_path = os.path.abspath(str(input_path or ""))
        if not normalized_input_path or not os.path.exists(normalized_input_path):
            return FileResult(
                filename=os.path.basename(normalized_input_path) if normalized_input_path else "",
                status=ProcessStatus.FAILED,
                source_path=normalized_input_path,
                message="입력 파일이 존재하지 않습니다",
            )

        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return FileResult(
                filename=os.path.basename(normalized_input_path),
                status=ProcessStatus.FAILED,
                source_path=normalized_input_path,
                message=f"출력 폴더 생성 실패: {e}",
            )

        self._stop_event.clear()
        self._reset_output_reservations()
        backup_dir = None
        if self.settings.create_backup:
            backup_dir = os.path.join(output_dir, "backup")
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception:
                backup_dir = None

        result = self._process_single_file(
            os.path.dirname(normalized_input_path),
            output_dir,
            normalized_input_path,
            backup_dir,
            1,
            1,
            None,
            input_root=input_root or os.path.dirname(normalized_input_path),
        )

        if (
            result.status == ProcessStatus.FAILED
            and self.settings.file_management.move_failed_files
        ):
            try:
                classify_failed_files(
                    [normalized_input_path],
                    input_root or os.path.dirname(normalized_input_path),
                    failed_folder_name=self.settings.file_management.failed_folder_name,
                    copy_mode=self.settings.file_management.copy_failed_instead_of_move,
                    input_root=input_root or os.path.dirname(normalized_input_path),
                )
            except Exception as e:
                self._log(f"실패 파일 분류 중 오류: {e}", "warning")

        if not result.source_path:
            result.source_path = normalized_input_path
        return result
