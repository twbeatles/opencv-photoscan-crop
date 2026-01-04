#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Folder Watcher for Photo Cropper v8.5.

Monitors folders for new images and triggers automatic processing.
Uses QFileSystemWatcher for cross-platform compatibility.
"""

import os
import logging
from typing import Optional, Callable, Set, List
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QFileSystemWatcher

logger = logging.getLogger(__name__)

# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}


class FolderWatcher(QObject):
    """
    Watches a folder for new image files and emits signals when found.
    
    Features:
        - Real-time file monitoring
        - Debounced events to prevent duplicates
        - Filter by file extension
        - Recursive subdirectory watching (optional)
    """
    
    # Signals
    new_file_detected = pyqtSignal(str)  # Emitted when a new image file is detected
    file_removed = pyqtSignal(str)       # Emitted when a file is removed
    watch_started = pyqtSignal(str)      # Emitted when watching starts
    watch_stopped = pyqtSignal()         # Emitted when watching stops
    error_occurred = pyqtSignal(str)     # Emitted on error
    
    def __init__(
        self,
        watch_path: Optional[str] = None,
        recursive: bool = False,
        debounce_ms: int = 500,
        parent: Optional[QObject] = None
    ):
        """
        Initialize folder watcher.
        
        Args:
            watch_path: Path to watch (can be set later)
            recursive: Watch subdirectories
            debounce_ms: Debounce time in milliseconds
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self._watch_path: Optional[str] = watch_path
        self._recursive = recursive
        self._debounce_ms = debounce_ms
        
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)
        
        self._is_watching = False
        self._known_files: Set[str] = set()
        self._pending_files: Set[str] = set()
        
        # Debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._process_pending_files)
        
        # Callback for custom processing
        self._on_new_file_callback: Optional[Callable[[str], None]] = None
    
    @property
    def is_watching(self) -> bool:
        """Check if currently watching."""
        return self._is_watching
    
    @property
    def watch_path(self) -> Optional[str]:
        """Get current watch path."""
        return self._watch_path
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set callback function for new files."""
        self._on_new_file_callback = callback
    
    def start(self, path: Optional[str] = None) -> bool:
        """
        Start watching a folder.
        
        Args:
            path: Folder path to watch (uses current if None)
            
        Returns:
            True if started successfully
        """
        if path:
            self._watch_path = path
        
        if not self._watch_path:
            self.error_occurred.emit("No watch path specified")
            return False
        
        if not os.path.isdir(self._watch_path):
            self.error_occurred.emit(f"Path is not a directory: {self._watch_path}")
            return False
        
        try:
            # Stop existing watch
            self.stop()
            
            # Add directory to watcher
            if not self._watcher.addPath(self._watch_path):
                self.error_occurred.emit(f"Failed to watch: {self._watch_path}")
                return False
            
            # Watch subdirectories if recursive
            if self._recursive:
                for root, dirs, _ in os.walk(self._watch_path):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        self._watcher.addPath(dir_path)
            
            # Initial scan for existing files
            self._scan_existing_files()
            
            self._is_watching = True
            self.watch_started.emit(self._watch_path)
            logger.info(f"Started watching: {self._watch_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start watcher: {e}")
            self.error_occurred.emit(str(e))
            return False
    
    def stop(self):
        """Stop watching."""
        if not self._is_watching:
            return
        
        # Remove all paths from watcher
        paths = self._watcher.directories() + self._watcher.files()
        if paths:
            self._watcher.removePaths(paths)
        
        self._is_watching = False
        self._known_files.clear()
        self._pending_files.clear()
        self._debounce_timer.stop()
        
        self.watch_stopped.emit()
        logger.info("Stopped watching")
    
    def _scan_existing_files(self):
        """Scan for existing files in watch directory."""
        if not self._watch_path:
            return
        
        self._known_files.clear()
        
        if self._recursive:
            for root, _, files in os.walk(self._watch_path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self._is_image_file(filepath):
                        self._known_files.add(filepath)
        else:
            for filename in os.listdir(self._watch_path):
                filepath = os.path.join(self._watch_path, filename)
                if os.path.isfile(filepath) and self._is_image_file(filepath):
                    self._known_files.add(filepath)
        
        logger.debug(f"Found {len(self._known_files)} existing images")
    
    def _is_image_file(self, filepath: str) -> bool:
        """Check if file is a supported image."""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in SUPPORTED_EXTENSIONS
    
    def _on_directory_changed(self, path: str):
        """Handle directory change event."""
        logger.debug(f"Directory changed: {path}")
        self._check_for_new_files(path)
    
    def _on_file_changed(self, path: str):
        """Handle file change event."""
        logger.debug(f"File changed: {path}")
    
    def _check_for_new_files(self, directory: str):
        """Check directory for new image files."""
        try:
            current_files = set()
            
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath) and self._is_image_file(filepath):
                    current_files.add(filepath)
            
            # Find new files
            new_files = current_files - self._known_files
            
            # Find removed files
            removed_files = self._known_files.intersection(
                {f for f in self._known_files if os.path.dirname(f) == directory}
            ) - current_files
            
            # Update known files
            self._known_files.update(new_files)
            self._known_files -= removed_files
            
            # Add new files to pending (debounced)
            for filepath in new_files:
                self._pending_files.add(filepath)
            
            # Emit removed files immediately
            for filepath in removed_files:
                self.file_removed.emit(filepath)
            
            # Start/restart debounce timer
            if self._pending_files:
                self._debounce_timer.start(self._debounce_ms)
                
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
    
    def _process_pending_files(self):
        """Process pending new files after debounce."""
        for filepath in list(self._pending_files):
            # Verify file still exists and is complete
            if os.path.exists(filepath):
                try:
                    # Try to open file to verify it's complete
                    with open(filepath, 'rb') as f:
                        f.seek(0, 2)  # Seek to end
                    
                    self.new_file_detected.emit(filepath)
                    
                    if self._on_new_file_callback:
                        self._on_new_file_callback(filepath)
                        
                except (IOError, OSError):
                    # File might still be being written
                    logger.debug(f"File not ready yet: {filepath}")
                    # Re-queue with longer delay
                    QTimer.singleShot(1000, lambda f=filepath: self._retry_file(f))
        
        self._pending_files.clear()
    
    def _retry_file(self, filepath: str):
        """Retry processing a file that wasn't ready."""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    f.seek(0, 2)
                
                self.new_file_detected.emit(filepath)
                
                if self._on_new_file_callback:
                    self._on_new_file_callback(filepath)
                    
            except (IOError, OSError):
                logger.warning(f"File still not ready after retry: {filepath}")
    
    def get_watched_directories(self) -> List[str]:
        """Get list of watched directories."""
        return self._watcher.directories()
    
    def add_directory(self, path: str) -> bool:
        """Add additional directory to watch."""
        if not os.path.isdir(path):
            return False
        return self._watcher.addPath(path)
    
    def remove_directory(self, path: str) -> bool:
        """Remove directory from watch."""
        return self._watcher.removePath(path)


class AutoProcessor(QObject):
    """
    Automatic processor that combines folder watching with batch processing.
    """
    
    # Signals
    processing_started = pyqtSignal(str)
    processing_completed = pyqtSignal(str, bool)  # filepath, success
    queue_updated = pyqtSignal(int)  # queue size
    
    def __init__(
        self,
        watch_path: Optional[str] = None,
        output_path: Optional[str] = None,
        process_callback: Optional[Callable[[str, str], bool]] = None,
        parent: Optional[QObject] = None
    ):
        """
        Initialize auto processor.
        
        Args:
            watch_path: Input folder to watch
            output_path: Output folder for processed images
            process_callback: Function to process each file (input, output) -> success
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self._watch_path = watch_path
        self._output_path = output_path
        self._process_callback = process_callback
        
        self._watcher = FolderWatcher(watch_path, parent=self)
        self._watcher.new_file_detected.connect(self._on_new_file)
        
        self._queue: List[str] = []
        self._is_processing = False
        
        # Process timer for queue
        self._process_timer = QTimer(self)
        self._process_timer.setSingleShot(True)
        self._process_timer.timeout.connect(self._process_next)
    
    def start(self, watch_path: Optional[str] = None, output_path: Optional[str] = None):
        """Start auto processing."""
        if watch_path:
            self._watch_path = watch_path
        if output_path:
            self._output_path = output_path
        
        self._watcher.start(self._watch_path)
    
    def stop(self):
        """Stop auto processing."""
        self._watcher.stop()
        self._queue.clear()
        self._is_processing = False
    
    def set_process_callback(self, callback: Callable[[str, str], bool]):
        """Set the processing callback function."""
        self._process_callback = callback
    
    def _on_new_file(self, filepath: str):
        """Handle new file detected."""
        self._queue.append(filepath)
        self.queue_updated.emit(len(self._queue))
        
        if not self._is_processing:
            self._process_timer.start(100)  # Small delay to batch multiple files
    
    def _process_next(self):
        """Process next file in queue."""
        if not self._queue:
            self._is_processing = False
            return
        
        self._is_processing = True
        filepath = self._queue.pop(0)
        self.queue_updated.emit(len(self._queue))
        
        self.processing_started.emit(filepath)
        
        success = False
        if self._process_callback and self._output_path:
            try:
                success = self._process_callback(filepath, self._output_path)
            except Exception as e:
                logger.error(f"Processing failed for {filepath}: {e}")
        
        self.processing_completed.emit(filepath, success)
        
        # Process next file
        if self._queue:
            self._process_timer.start(100)
        else:
            self._is_processing = False
