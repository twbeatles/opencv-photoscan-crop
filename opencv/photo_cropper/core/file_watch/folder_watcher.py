#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Directory watcher that detects image files with debounce."""

from __future__ import annotations

import logging
import os
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from PyQt6.QtCore import QObject, QFileSystemWatcher, QTimer, pyqtSignal

from ...utils.file_helpers import is_path_within, normalize_path
from .types import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

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


__all__ = ["FolderWatcher"]
