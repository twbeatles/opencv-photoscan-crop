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


class BatchProcessorIoPathsMixin:
    def _resolve_input_path(
        self: Any,
        input_dir: str,
        file_entry: str,
        *,
        input_root: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Resolve a file entry to an absolute input path and display name.

        Args:
            input_dir: Base input directory
            file_entry: Filename or full/relative path

        Returns:
            Tuple of (input_path, display_name)
        """
        display_root = input_root or input_dir
        if os.path.isabs(file_entry):
            return file_entry, relative_display_path(file_entry, display_root)

        candidate = os.path.join(input_dir, file_entry)
        if os.path.exists(candidate):
            return candidate, relative_display_path(candidate, display_root)

        if os.path.exists(file_entry):
            return file_entry, relative_display_path(file_entry, display_root)

        return candidate, relative_display_path(candidate, display_root)
    def _resolve_base_output_dir(
        self: Any,
        input_path: str,
        output_dir: str,
        *,
        input_root: Optional[str] = None,
    ) -> str:
        """Resolve output directory, preserving input-relative parent path when needed."""
        rel_parent = relative_parent_dir(input_path, input_root)
        resolved = os.path.join(output_dir, rel_parent) if rel_parent else output_dir
        os.makedirs(resolved, exist_ok=True)
        return resolved
    def _ensure_naming_engine(self: Any) -> Optional[NamingRuleEngine]:
        """Initialize naming engine if enabled in settings."""
        if not self.settings.file_management.use_naming_rules:
            self._naming_engine = None
            return None

        if self._naming_engine is None:
            rule = NamingRule(
                prefix=self.settings.file_management.naming_prefix,
                suffix=self.settings.file_management.naming_suffix,
                use_counter=self.settings.file_management.naming_use_counter,
                counter_padding=self.settings.file_management.naming_counter_padding,
                use_date=self.settings.file_management.naming_use_date,
                date_format=self.settings.file_management.naming_date_format,
                preserve_original_name=self.settings.file_management.naming_preserve_original,
            )
            self._naming_engine = NamingRuleEngine(rule)

        return self._naming_engine
    def _resolve_multi_photo_output_dir(
        self: Any,
        input_path: str,
        output_dir: str,
        *,
        input_root: Optional[str] = None,
    ) -> str:
        """Resolve per-input subfolder for multi-photo outputs when enabled."""
        base_output_dir = self._resolve_base_output_dir(
            input_path,
            output_dir,
            input_root=input_root,
        )
        if not (
            self.settings.multi_photo.enabled
            and self.settings.multi_photo.separate_output_folders
        ):
            return base_output_dir

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        folder_name = f"{base_name}_photos"
        resolved = os.path.join(base_output_dir, folder_name)

        os.makedirs(resolved, exist_ok=True)
        return resolved
    def _build_output_path(self: Any, input_path: str, output_dir: str, suffix: str) -> str:
        """Build output path using naming rules or default scheme."""
        os.makedirs(output_dir, exist_ok=True)

        output_format = self.settings.output.output_format
        if self.settings.file_management.use_naming_rules:
            engine = self._ensure_naming_engine()
            if engine:
                with self._naming_lock:
                    path = engine.generate_name(
                        input_path,
                        output_dir=output_dir,
                        output_format=output_format,
                    )
                if suffix and suffix != "_cropped":
                    base, ext = os.path.splitext(path)
                    return self._ensure_unique_output_path(base + suffix + ext)
                return self._ensure_unique_output_path(path)

        base_name = os.path.splitext(os.path.basename(input_path))[0] + suffix
        extension = "." + output_format.lower()
        path = get_unique_filename(
            output_dir,
            base_name,
            extension,
            add_timestamp=self.settings.output.add_timestamp,
        )
        return self._ensure_unique_output_path(path)

    def _pipeline_signature(self: Any) -> str:
        if self._pipeline_signature_cache is None:
            self._pipeline_signature_cache = build_pipeline_signature(self.settings)
        return self._pipeline_signature_cache
    def _get_processed_index_store(self: Any, output_dir: str) -> ProcessedIndexStore:
        key = os.path.normcase(os.path.abspath(str(output_dir or "")))
        store = self._processed_index_stores.get(key)
        if store is None:
            store = ProcessedIndexStore(key)
            self._processed_index_stores[key] = store
        return store
    def _warn_processed_index_issue(self: Any, output_dir: str, message: str) -> None:
        key = os.path.normcase(os.path.abspath(str(output_dir or "")))
        if key in self._processed_index_warned_roots:
            return
        self._processed_index_warned_roots.add(key)
        self._log(
            f"처리 이력 인덱스 사용 불가({os.path.join(key, '.photocropper', 'processed_index.json')}): {message}",
            "warning",
        )
    @staticmethod
    def _source_stat_signature(source_path: str) -> Optional[Tuple[int, int]]:
        try:
            st = os.stat(source_path)
        except Exception:
            return None
        size = int(st.st_size)
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        return size, mtime_ns
    def lookup_processed_outputs_from_index(
        self: Any, source_path: str, output_dir: str
    ) -> Tuple[Optional[List[str]], bool, str]:
        """Lookup previously produced outputs by source signature and pipeline signature."""
        signature = self._source_stat_signature(source_path)
        if signature is None:
            return None, False, ""

        size, mtime_ns = signature
        store = self._get_processed_index_store(output_dir)
        outputs, usable, status = store.lookup_outputs(
            source_path=source_path,
            size=size,
            mtime_ns=mtime_ns,
            pipeline_signature=self._pipeline_signature(),
        )
        if not usable and store.last_error:
            self._warn_processed_index_issue(output_dir, store.last_error)
        return outputs, usable, status
    def record_processed_outputs(
        self: Any,
        source_path: str,
        output_dir: str,
        outputs: List[str],
        *,
        status: str = RECORD_STATUS_SUCCESS,
    ) -> None:
        """Persist processed outputs for future skip-processed checks."""
        if not outputs:
            return

        signature = self._source_stat_signature(source_path)
        if signature is None:
            return

        size, mtime_ns = signature
        store = self._get_processed_index_store(output_dir)
        ok = store.upsert_record(
            source_path=source_path,
            size=size,
            mtime_ns=mtime_ns,
            outputs=outputs,
            pipeline_signature=self._pipeline_signature(),
            status=status,
        )
        if not ok and store.last_error:
            self._warn_processed_index_issue(output_dir, store.last_error)
    def _resolve_output_dir_for_classification(
        self: Any,
        image: np.ndarray,
        output_dir: str,
    ) -> str:
        """Resolve category subfolder output when classification is enabled."""
        cls_settings = self.settings.classification
        if not cls_settings.enabled or not cls_settings.auto_folder:
            return output_dir

        try:
            classifier = self._get_classifier()
            model = getattr(cls_settings, "model", "basic")
            classify_input, _ = self._to_bgr(image)
            classify_result = classifier.classify(classify_input, model=model)
            category_key = classify_result.category.value
            min_conf = max(0.0, min(1.0, cls_settings.min_confidence))

            if classify_result.confidence < min_conf:
                return output_dir

            enabled_map = cls_settings.categories_enabled or {}
            if not enabled_map.get(category_key, True):
                return output_dir

            category_dir_name = self._resolve_category_folder_name(
                classify_result.category
            )
            classified_output_dir = os.path.join(output_dir, category_dir_name)
            os.makedirs(classified_output_dir, exist_ok=True)
            self._log(
                f"  🤖 분류: {category_key} ({classify_result.confidence:.2f})",
                "info",
            )
            return classified_output_dir
        except Exception as e:
            self._log(f"  이미지 분류 오류: {e}", "warning")
            return output_dir
    def _resolve_category_folder_name(self: Any, category: ImageCategory) -> str:
        cls_settings = self.settings.classification
        key = getattr(category, "value", str(category or "")).lower()
        folder_map = resolve_category_folder_map(
            getattr(cls_settings, "category_folders", {}) or {},
            language=getattr(self.settings.ui, "language", None),
        )
        mapped_name = str(folder_map.get(key, "") or "").strip()
        if mapped_name:
            return mapped_name
        try:
            return self._get_classifier().get_output_folder(category)
        except Exception:
            fallback = {
                "portrait": "인물",
                "landscape": "풍경",
                "document": "문서",
                "blackwhite": "흑백",
                "other": "기타",
            }
            return fallback.get(key, "기타")
    def _iter_candidate_output_dirs(
        self: Any,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
        input_root: Optional[str] = None,
    ) -> List[str]:
        """
        Candidate output directories for duplicate probing.

        Includes classification category folders when auto-folder routing is enabled.
        """
        if input_path:
            base_output_dir = self._resolve_base_output_dir(
                input_path,
                output_dir,
                input_root=input_root,
            )
        else:
            base_output_dir = output_dir

        roots: List[str] = [base_output_dir]
        if multi_photo and input_path:
            roots.append(
                self._resolve_multi_photo_output_dir(
                    input_path,
                    output_dir,
                    input_root=input_root,
                )
            )

        dirs: List[str] = []
        for root in roots:
            dirs.append(root)
        cls_settings = self.settings.classification
        if not cls_settings.enabled or not cls_settings.auto_folder:
            return list(dict.fromkeys(dirs))

        try:
            enabled_map = cls_settings.categories_enabled or {}
            for category in ImageCategory:
                if enabled_map.get(category.value, True):
                    for root in roots:
                        dirs.append(
                            os.path.join(root, self._resolve_category_folder_name(category))
                        )
        except Exception:
            # Best-effort: keep base output_dir only.
            pass

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(dirs))
    def _find_existing_output(
        self: Any,
        base_name: str,
        ext: str,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
        input_root: Optional[str] = None,
    ) -> Optional[str]:
        """
        Find existing output path for skip-processed checks across candidate dirs.
        """
        for candidate_dir in self._iter_candidate_output_dirs(
            output_dir,
            multi_photo=multi_photo,
            input_path=input_path,
            input_root=input_root,
        ):
            expected = os.path.join(candidate_dir, f"{base_name}_cropped{ext}")
            if os.path.exists(expected):
                return expected

            if multi_photo:
                try:
                    prefix = f"{base_name}_photo"
                    if os.path.isdir(candidate_dir):
                        for entry in os.listdir(candidate_dir):
                            if not entry.startswith(prefix):
                                continue
                            candidate_path = os.path.join(candidate_dir, entry)
                            if not os.path.isfile(candidate_path):
                                continue
                            if ext and not entry.lower().endswith(ext.lower()):
                                continue
                            return candidate_path
                except Exception:
                    pass
        return None
    def find_existing_output(
        self: Any,
        base_name: str,
        ext: str,
        output_dir: str,
        *,
        multi_photo: bool = False,
        input_path: Optional[str] = None,
        input_root: Optional[str] = None,
    ) -> Optional[str]:
        """Public wrapper for skip-processed duplicate probing."""
        return self._find_existing_output(
            base_name,
            ext,
            output_dir,
            multi_photo=multi_photo,
            input_path=input_path,
            input_root=input_root,
        )
    def get_image_files(self: Any, input_dir: str) -> List[str]:
        """
        Get list of image files in directory.

        Args:
            input_dir: Input directory path

        Returns:
            List of image filenames
        """
        try:
            files = [
                f
                for f in os.listdir(input_dir)
                if f.lower().endswith(SUPPORTED_IMAGE_FORMATS)
            ]
            return sorted(files)
        except Exception as e:
            self._log(f"폴더 읽기 오류: {e}", "error")
            return []
