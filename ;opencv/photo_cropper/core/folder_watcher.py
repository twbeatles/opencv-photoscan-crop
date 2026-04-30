#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Folder watcher and auto-processor for Photo Cropper.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Set, Tuple

from PyQt6.QtCore import QObject, QFileSystemWatcher, QTimer, pyqtSignal

from ..utils.file_helpers import is_path_within, normalize_path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".tiff",
    ".tif",
    ".webp",
}


@dataclass
class WatchProcessResult:
    """Detailed process callback result used by AutoProcessor."""

    success: bool
    status: str = "success"
    message: str = ""


class FolderWatcher(QObject):
    """Watch a directory tree and emit new image events with debounce."""

    new_file_detected = pyqtSignal(str)
    file_removed = pyqtSignal(str)
    watch_started = pyqtSignal(str)
    watch_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        watch_path: Optional[str] = None,
        recursive: bool = False,
        debounce_ms: int = 500,
        excluded_roots: Optional[Sequence[str]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._watch_path: Optional[str] = watch_path
        self._recursive = bool(recursive)
        self._debounce_ms = int(debounce_ms)
        self._excluded_roots = self._normalize_excluded_roots(excluded_roots)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)

        self._is_watching = False
        self._known_files: Set[str] = set()
        self._pending_files: Set[str] = set()
        self._file_signatures: Dict[str, Tuple[int, int]] = {}

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._process_pending_files)

        self._on_new_file_callback: Optional[Callable[[str], None]] = None

    @staticmethod
    def _normalize_excluded_roots(
        excluded_roots: Optional[Sequence[str]],
    ) -> List[str]:
        normalized: List[str] = []
        for raw in excluded_roots or []:
            candidate = normalize_path(str(raw or ""))
            if candidate and candidate not in normalized:
                normalized.append(candidate)
        return normalized

    def set_excluded_roots(self, excluded_roots: Optional[Sequence[str]]) -> None:
        self._excluded_roots = self._normalize_excluded_roots(excluded_roots)

    def _is_excluded_path(self, path: str) -> bool:
        if os.path.basename(str(path or "")) == ".photocropper":
            return True
        normalized = normalize_path(str(path or ""))
        if not normalized:
            return False
        return any(is_path_within(root, normalized) for root in self._excluded_roots)

    @property
    def is_watching(self) -> bool:
        return self._is_watching

    @property
    def watch_path(self) -> Optional[str]:
        return self._watch_path

    def set_callback(self, callback: Callable[[str], None]) -> None:
        self._on_new_file_callback = callback

    def start(self, path: Optional[str] = None) -> bool:
        if path:
            self._watch_path = path

        if not self._watch_path:
            self.error_occurred.emit("No watch path specified")
            return False

        if not os.path.isdir(self._watch_path):
            self.error_occurred.emit(f"Path is not a directory: {self._watch_path}")
            return False

        try:
            self.stop()

            if not self._watcher.addPath(self._watch_path):
                self.error_occurred.emit(f"Failed to watch: {self._watch_path}")
                return False

            if self._recursive:
                for root, dirs, _ in os.walk(self._watch_path):
                    dirs[:] = [
                        dirname
                        for dirname in dirs
                        if not self._is_excluded_path(os.path.join(root, dirname))
                    ]
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        self._watcher.addPath(dir_path)

            self._scan_existing_files()
            self._is_watching = True
            self.watch_started.emit(self._watch_path)
            logger.info("Started watching: %s", self._watch_path)
            return True
        except Exception as exc:
            logger.error("Failed to start watcher: %s", exc)
            self.error_occurred.emit(str(exc))
            return False

    def stop(self) -> None:
        if not self._is_watching:
            return

        paths = self._watcher.directories() + self._watcher.files()
        if paths:
            self._watcher.removePaths(paths)

        self._is_watching = False
        self._known_files.clear()
        self._pending_files.clear()
        self._file_signatures.clear()
        self._debounce_timer.stop()

        self.watch_stopped.emit()
        logger.info("Stopped watching")

    def _scan_existing_files(self) -> None:
        if not self._watch_path:
            return

        self._known_files.clear()
        self._file_signatures.clear()

        if self._recursive:
            for root, dirs, files in os.walk(self._watch_path):
                dirs[:] = [
                    dirname
                    for dirname in dirs
                    if not self._is_excluded_path(os.path.join(root, dirname))
                ]
                if self._is_excluded_path(root):
                    continue
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self._is_image_file(filepath) and not self._is_excluded_path(filepath):
                        self._track_known_file(filepath)
        else:
            for filename in os.listdir(self._watch_path):
                filepath = os.path.join(self._watch_path, filename)
                if os.path.isfile(filepath) and self._is_image_file(filepath):
                    self._track_known_file(filepath)

        logger.debug("Initial known files: %d", len(self._known_files))

    @staticmethod
    def _is_image_file(filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def _file_signature(filepath: str) -> Optional[Tuple[int, int]]:
        try:
            st = os.stat(filepath)
        except Exception:
            return None
        return (
            int(st.st_size),
            int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
        )

    def _ensure_file_path_watched(self, filepath: str) -> None:
        if not filepath or not os.path.isfile(filepath):
            return
        watched_files = set(self._watcher.files())
        if filepath not in watched_files:
            self._watcher.addPath(filepath)

    def _track_known_file(self, filepath: str) -> None:
        self._known_files.add(filepath)
        signature = self._file_signature(filepath)
        if signature is not None:
            self._file_signatures[filepath] = signature
        self._ensure_file_path_watched(filepath)

    def _untrack_known_file(self, filepath: str) -> None:
        self._known_files.discard(filepath)
        self._pending_files.discard(filepath)
        self._file_signatures.pop(filepath, None)
        watched_files = set(self._watcher.files())
        if filepath in watched_files:
            self._watcher.removePath(filepath)

    def _scan_directory_images(self, directory: str) -> Set[str]:
        images: Set[str] = set()
        if self._is_excluded_path(directory):
            return images
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if (
                    os.path.isfile(filepath)
                    and self._is_image_file(filepath)
                    and not self._is_excluded_path(filepath)
                ):
                    images.add(filepath)
        except Exception as exc:
            logger.debug("Directory scan failed (%s): %s", directory, exc)
        return images

    def _queue_new_files(self, filepaths: Set[str]) -> None:
        queued = False
        for filepath in filepaths:
            if self._is_excluded_path(filepath):
                continue
            if filepath in self._known_files:
                continue
            self._track_known_file(filepath)
            self._pending_files.add(filepath)
            queued = True

        if queued:
            self._debounce_timer.start(self._debounce_ms)

    def _on_directory_changed(self, path: str) -> None:
        logger.debug("Directory changed: %s", path)
        if self._is_excluded_path(path):
            return
        if self._recursive:
            self._refresh_recursive_directories(path)
        self._check_for_new_files(path)

    def _on_file_changed(self, path: str) -> None:
        logger.debug("File changed: %s", path)
        filepath = str(path or "")
        if not filepath:
            return
        if self._is_excluded_path(filepath):
            return

        if not os.path.exists(filepath):
            if filepath in self._known_files:
                self._untrack_known_file(filepath)
                self.file_removed.emit(filepath)
            return

        if not self._is_image_file(filepath):
            return

        self._ensure_file_path_watched(filepath)
        signature = self._file_signature(filepath)
        if signature is None:
            return

        previous = self._file_signatures.get(filepath)
        if previous == signature:
            return

        self._known_files.add(filepath)
        self._file_signatures[filepath] = signature
        self._pending_files.add(filepath)
        self._debounce_timer.start(self._debounce_ms)

    def _check_for_new_files(self, directory: str) -> None:
        try:
            current_files = self._scan_directory_images(directory)
            existing_in_dir = {
                f for f in self._known_files if os.path.dirname(f) == directory
            }

            new_files = current_files - self._known_files
            removed_files = existing_in_dir - current_files

            if new_files:
                self._queue_new_files(new_files)

            for filepath in removed_files:
                self._untrack_known_file(filepath)
                self.file_removed.emit(filepath)

        except Exception as exc:
            logger.error("Error checking for new files in %s: %s", directory, exc)

    def _refresh_recursive_directories(self, changed_dir: str) -> None:
        """
        Add newly created subdirectories to watcher and immediately scan any
        existing image files inside them.
        """
        try:
            if not self._watch_path or not os.path.isdir(changed_dir):
                return

            known_dirs = set(self._watcher.directories())
            discovered_files: Set[str] = set()

            for root, dirs, _ in os.walk(changed_dir):
                dirs[:] = [
                    dirname
                    for dirname in dirs
                    if not self._is_excluded_path(os.path.join(root, dirname))
                ]
                if self._is_excluded_path(root):
                    continue
                for dirname in dirs:
                    dir_path = os.path.join(root, dirname)
                    if dir_path in known_dirs:
                        continue

                    self._watcher.addPath(dir_path)
                    known_dirs.add(dir_path)

                    # Initial scan right after watcher registration.
                    discovered_files.update(self._scan_directory_images(dir_path))

            if discovered_files:
                self._queue_new_files(discovered_files)
        except Exception as exc:
            logger.debug("Failed to refresh recursive directories: %s", exc)

    def _process_pending_files(self) -> None:
        for filepath in list(self._pending_files):
            if not os.path.exists(filepath):
                continue

            self.new_file_detected.emit(filepath)
            if self._on_new_file_callback is not None:
                self._on_new_file_callback(filepath)

        self._pending_files.clear()

    def get_watched_directories(self) -> List[str]:
        return self._watcher.directories()

    def add_directory(self, path: str) -> bool:
        if not os.path.isdir(path) or self._is_excluded_path(path):
            return False
        return self._watcher.addPath(path)

    def remove_directory(self, path: str) -> bool:
        return self._watcher.removePath(path)


class AutoProcessor(QObject):
    """Auto-process files detected by FolderWatcher."""

    processing_started = pyqtSignal(str)
    processing_completed = pyqtSignal(str, bool)
    processing_completed_detailed = pyqtSignal(str, bool, str, str, int)
    queue_updated = pyqtSignal(int)
    queue_metrics_updated = pyqtSignal(int, int)
    worker_result_ready = pyqtSignal(str, bool, str, str, int)

    def __init__(
        self,
        watch_path: Optional[str] = None,
        output_path: Optional[str] = None,
        recursive: bool = False,
        debounce_ms: int = 500,
        max_wait_seconds: float = 30.0,
        excluded_roots: Optional[Sequence[str]] = None,
        process_callback: Optional[Callable[[str, str], Any]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._watch_path = watch_path
        self._output_path = output_path
        self._process_callback = process_callback

        self._watcher = FolderWatcher(
            watch_path,
            recursive=recursive,
            debounce_ms=debounce_ms,
            excluded_roots=excluded_roots,
            parent=self,
        )
        self._watcher.new_file_detected.connect(self._on_new_file)

        self._queue: Deque[str] = deque()
        self._queued_files: Set[str] = set()
        self._enqueue_times: Dict[str, float] = {}
        self._wait_samples_ms: List[int] = []

        self._is_processing = False
        self._halted = False

        # Readiness tracking for partially-copied files.
        self._file_states: Dict[str, Dict[str, Any]] = {}
        self._stable_window_s = max(0.5, debounce_ms / 1000.0)
        self._retry_interval_ms = max(200, int(debounce_ms * 0.8))
        self._max_wait_s = max(1.0, float(max_wait_seconds))

        self._process_timer = QTimer(self)
        self._process_timer.setSingleShot(True)
        self._process_timer.timeout.connect(self._process_next)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._active_future: Optional[Future] = None
        self.worker_result_ready.connect(self._handle_worker_result)

    def _ensure_executor(self) -> None:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="photocropper-watch",
            )

    def start(
        self,
        watch_path: Optional[str] = None,
        output_path: Optional[str] = None,
        recursive: Optional[bool] = None,
        debounce_ms: Optional[int] = None,
        max_wait_seconds: Optional[float] = None,
        excluded_roots: Optional[Sequence[str]] = None,
    ) -> bool:
        if watch_path:
            self._watch_path = watch_path
        if output_path:
            self._output_path = output_path
        if recursive is not None:
            self._watcher._recursive = bool(recursive)
        if debounce_ms is not None:
            self._watcher._debounce_ms = int(debounce_ms)
            self._stable_window_s = max(0.5, int(debounce_ms) / 1000.0)
            self._retry_interval_ms = max(200, int(int(debounce_ms) * 0.8))
        if max_wait_seconds is not None:
            self._max_wait_s = max(1.0, float(max_wait_seconds))
        if excluded_roots is not None:
            self._watcher.set_excluded_roots(excluded_roots)

        self._halted = False

        if not self._watch_path:
            logger.error("Watch path is not set")
            return False

        if not self._output_path:
            logger.error("Output path is not set")
            return False

        try:
            os.makedirs(self._output_path, exist_ok=True)
        except Exception as exc:
            logger.error("Failed to create output directory: %s", exc)
            return False

        self._queue.clear()
        self._queued_files.clear()
        self._enqueue_times.clear()
        self._wait_samples_ms.clear()
        self._is_processing = False
        self._active_future = None
        self._ensure_executor()
        self._emit_queue_metrics()

        return self._watcher.start(self._watch_path)

    def stop(self) -> None:
        self._halted = True
        self._watcher.stop()
        self._process_timer.stop()
        self._queue.clear()
        self._queued_files.clear()
        self._enqueue_times.clear()
        self._file_states.clear()
        self._wait_samples_ms.clear()
        self._is_processing = False
        if self._active_future is not None:
            self._active_future.cancel()
            self._active_future = None
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                self._executor.shutdown(wait=False)
            self._executor = None
        self._emit_queue_metrics()

    def set_process_callback(self, callback: Callable[[str, str], Any]) -> None:
        self._process_callback = callback

    def _avg_wait_ms(self) -> int:
        if not self._wait_samples_ms:
            return 0
        return int(sum(self._wait_samples_ms) / len(self._wait_samples_ms))

    def _emit_queue_metrics(self) -> None:
        queue_size = len(self._queue)
        avg_wait = self._avg_wait_ms()
        self.queue_updated.emit(queue_size)
        self.queue_metrics_updated.emit(queue_size, avg_wait)

    def _on_new_file(self, filepath: str) -> None:
        if self._halted or filepath in self._queued_files:
            return

        self._queue.append(filepath)
        self._queued_files.add(filepath)
        self._enqueue_times.setdefault(filepath, time.monotonic())
        self._file_states.pop(filepath, None)
        self._emit_queue_metrics()

        if not self._is_processing:
            self._process_timer.start(100)

    @staticmethod
    def _status_from_reason(reason: str) -> str:
        reason_key = (reason or "").lower()
        if reason_key == "timeout":
            return "not_ready_timeout"
        if reason_key == "missing":
            return "missing"
        if reason_key.startswith("read failed"):
            return "read_failed"
        if reason_key.startswith("stat failed"):
            return "read_failed"
        return "not_ready"

    @staticmethod
    def _parse_callback_result(result: Any) -> WatchProcessResult:
        if isinstance(result, WatchProcessResult):
            return result

        if isinstance(result, bool):
            return WatchProcessResult(
                success=result,
                status="success" if result else "failed",
                message="",
            )

        if isinstance(result, tuple):
            if len(result) == 2:
                success, status = result
                return WatchProcessResult(
                    success=bool(success),
                    status=str(status or ("success" if success else "failed")),
                    message="",
                )
            if len(result) >= 3:
                success, status, message = result[0], result[1], result[2]
                return WatchProcessResult(
                    success=bool(success),
                    status=str(status or ("success" if success else "failed")),
                    message=str(message or ""),
                )

        if isinstance(result, dict):
            success = bool(result.get("success", False))
            status = str(result.get("status") or ("success" if success else "failed"))
            message = str(result.get("message") or "")
            return WatchProcessResult(success=success, status=status, message=message)

        status_obj = getattr(result, "status", None)
        message = str(getattr(result, "message", "") or "")

        if status_obj is not None:
            status_name = str(getattr(status_obj, "name", "") or "")
            status_value = str(getattr(status_obj, "value", "") or "")
            raw_status = status_value or status_name
            normalized = raw_status.lower()
            if normalized:
                success = normalized in {"success", "skipped", "ok", "partial_success"}
                return WatchProcessResult(success=success, status=normalized, message=message)

        if hasattr(result, "success"):
            success = bool(getattr(result, "success"))
            status = str(getattr(result, "status", "") or ("success" if success else "failed"))
            return WatchProcessResult(success=success, status=status, message=message)

        raise TypeError(f"Unsupported callback return type: {type(result)}")

    def _process_next(self) -> None:
        if self._halted:
            self._queue.clear()
            self._queued_files.clear()
            self._emit_queue_metrics()
            self._is_processing = False
            return

        if not self._queue:
            self._is_processing = False
            self._emit_queue_metrics()
            return

        self._is_processing = True
        filepath = self._queue.popleft()
        self._queued_files.discard(filepath)

        now = time.monotonic()
        enqueued_at = self._enqueue_times.get(filepath, now)
        wait_ms = max(0, int((now - enqueued_at) * 1000))

        self._emit_queue_metrics()

        ready, expired, reason = self._check_file_ready(filepath)
        if not ready:
            state = self._file_states.get(filepath) or {}
            retry_count = int(state.get("retry_count", 0))
            if expired:
                status = self._status_from_reason(reason)
                message = f"File not ready: {reason} (retry={retry_count})"
                logger.error("%s (%s)", message, filepath)

                self.processing_completed.emit(filepath, False)
                self.processing_completed_detailed.emit(
                    filepath,
                    False,
                    status,
                    message,
                    wait_ms,
                )
                self._wait_samples_ms.append(wait_ms)
                if len(self._wait_samples_ms) > 200:
                    self._wait_samples_ms = self._wait_samples_ms[-200:]

                self._file_states.pop(filepath, None)
                self._enqueue_times.pop(filepath, None)

                if self._queue:
                    self._process_timer.start(100)
                else:
                    self._is_processing = False
                self._emit_queue_metrics()
                return

            # Requeue at tail for fairness (don't block younger files behind one slow file).
            logger.debug(
                "File not ready yet (retry=%d, reason=%s): %s",
                retry_count,
                reason,
                filepath,
            )
            self._queue.append(filepath)
            self._queued_files.add(filepath)
            self._emit_queue_metrics()
            self._process_timer.start(self._retry_interval_ms)
            return

        self.processing_started.emit(filepath)

        self._ensure_executor()
        if self._executor is None or self._process_callback is None or not self._output_path:
            self.worker_result_ready.emit(
                filepath,
                False,
                "process_exception",
                "Process callback/output path is not set",
                wait_ms,
            )
            return

        try:
            future = self._executor.submit(
                self._run_process_callback,
                filepath,
                self._output_path,
            )
            self._active_future = future
            future.add_done_callback(
                lambda done, path=filepath, waited=wait_ms: self._emit_worker_result(
                    path,
                    waited,
                    done,
                )
            )
        except Exception as exc:
            logger.error("Failed to submit watch processing for %s: %s", filepath, exc)
            self.worker_result_ready.emit(
                filepath,
                False,
                "process_exception",
                str(exc),
                wait_ms,
            )

    def _check_file_ready(self, filepath: str) -> Tuple[bool, bool, str]:
        now = time.monotonic()

        state = self._file_states.get(filepath)
        if state is None:
            state = {
                "first_seen": now,
                "last_size": None,
                "last_mtime_ns": None,
                "last_change": now,
                "retry_count": 0,
            }
            self._file_states[filepath] = state

        if not filepath or not os.path.exists(filepath):
            return False, True, "missing"

        state["retry_count"] = int(state.get("retry_count", 0)) + 1

        try:
            st = os.stat(filepath)
            size = int(st.st_size)
            mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        except Exception as exc:
            if now - float(state["first_seen"]) > self._max_wait_s:
                return False, True, f"stat failed: {exc}"
            return False, False, f"stat failed: {exc}"

        if state["last_size"] is None or state["last_mtime_ns"] is None:
            state["last_size"] = size
            state["last_mtime_ns"] = mtime_ns
            state["last_change"] = now
            return False, False, "initial"

        if size != state["last_size"] or mtime_ns != state["last_mtime_ns"]:
            state["last_size"] = size
            state["last_mtime_ns"] = mtime_ns
            state["last_change"] = now
            return False, False, "changing"

        if now - state["first_seen"] > self._max_wait_s:
            return False, True, "timeout"

        if now - state["last_change"] < self._stable_window_s:
            return False, False, "not yet stable"

        try:
            with open(filepath, "rb") as handle:
                handle.read(1)
        except Exception as exc:
            # Keep retrying until max_wait_s is exceeded.
            elapsed = now - state["first_seen"]
            if elapsed > self._max_wait_s:
                return False, True, f"read failed: {exc}"
            return False, False, f"read failed: {exc}"

        return True, False, "ready"

    def _run_process_callback(
        self,
        filepath: str,
        output_path: str,
    ) -> WatchProcessResult:
        callback = self._process_callback
        if callback is None:
            return WatchProcessResult(
                success=False,
                status="process_exception",
                message="Process callback is not set",
            )
        try:
            callback_result = callback(filepath, output_path)
            result = self._parse_callback_result(callback_result)
            if not result.status:
                result.status = "success" if result.success else "failed"
            return result
        except Exception as exc:
            logger.error("Processing failed for %s: %s", filepath, exc)
            return WatchProcessResult(
                success=False,
                status="process_exception",
                message=str(exc),
            )

    def _emit_worker_result(self, filepath: str, wait_ms: int, future: Future) -> None:
        if future.cancelled():
            result = WatchProcessResult(
                success=False,
                status="cancelled",
                message="Processing cancelled",
            )
        else:
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Watch worker future failed for %s: %s", filepath, exc)
                result = WatchProcessResult(
                    success=False,
                    status="process_exception",
                    message=str(exc),
                )

        self.worker_result_ready.emit(
            filepath,
            bool(result.success),
            str(result.status or ("success" if result.success else "failed")),
            str(result.message or ""),
            wait_ms,
        )

    def _handle_worker_result(
        self,
        filepath: str,
        success: bool,
        status: str,
        message: str,
        wait_ms: int,
    ) -> None:
        self._active_future = None

        if self._halted:
            self._file_states.pop(filepath, None)
            self._enqueue_times.pop(filepath, None)
            self._is_processing = False
            self._emit_queue_metrics()
            return

        self.processing_completed.emit(filepath, bool(success))
        self.processing_completed_detailed.emit(
            filepath,
            bool(success),
            str(status),
            str(message or ""),
            wait_ms,
        )
        self._wait_samples_ms.append(wait_ms)
        if len(self._wait_samples_ms) > 200:
            self._wait_samples_ms = self._wait_samples_ms[-200:]

        self._file_states.pop(filepath, None)
        self._enqueue_times.pop(filepath, None)

        if self._queue:
            self._process_timer.start(100)
        else:
            self._is_processing = False

        self._emit_queue_metrics()
