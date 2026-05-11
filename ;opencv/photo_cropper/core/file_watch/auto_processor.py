#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Queue and execute processing for files detected by FolderWatcher."""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Set, Tuple

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .folder_watcher import FolderWatcher
from .types import WatchProcessResult

logger = logging.getLogger(__name__)

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


__all__ = ["AutoProcessor"]
