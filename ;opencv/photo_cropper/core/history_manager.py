#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History Manager for Photo Cropper v9.0.

Provides undo/redo functionality using the Command pattern.
"""

import copy
import logging
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Command type enumeration."""
    CROP = "crop"
    ROTATE = "rotate"
    RESIZE = "resize"
    WATERMARK = "watermark"
    COLOR_ADJUST = "color_adjust"
    FILTER = "filter"
    TRANSFORM = "transform"


@dataclass
class CommandState:
    """Stores state for undo/redo."""
    image_before: Optional[np.ndarray] = None
    image_after: Optional[np.ndarray] = None
    metadata: dict = field(default_factory=dict)


class Command(ABC):
    """Abstract base class for undoable commands."""
    
    def __init__(self, command_type: CommandType, description: str = ""):
        self.command_type = command_type
        self.description = description
        self._state: Optional[CommandState] = None
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the command. Returns True if successful."""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True if successful."""
        pass
    
    def redo(self) -> bool:
        """Redo the command. Default implementation re-executes."""
        return self.execute()


class ImageCommand(Command):
    """Command for image operations."""
    
    def __init__(
        self,
        command_type: CommandType,
        image_holder: 'ImageHolder',
        operation: Callable[[np.ndarray], np.ndarray],
        description: str = ""
    ):
        """
        Initialize image command.
        
        Args:
            command_type: Type of command
            image_holder: Object holding current image
            operation: Function that takes image and returns modified image
            description: Human-readable description
        """
        super().__init__(command_type, description)
        self._image_holder = image_holder
        self._operation = operation
    
    def execute(self) -> bool:
        """Execute the image operation."""
        try:
            current_image = self._image_holder.get_image()
            if current_image is None:
                return False
            
            # Store state for undo
            self._state = CommandState(
                image_before=current_image.copy()
            )
            
            # Apply operation
            new_image = self._operation(current_image)
            
            if new_image is not None:
                self._state.image_after = new_image.copy()
                self._image_holder.set_image(new_image)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False
    
    def undo(self) -> bool:
        """Undo the operation."""
        if self._state is None or self._state.image_before is None:
            return False
        
        try:
            self._image_holder.set_image(self._state.image_before.copy())
            return True
        except Exception as e:
            logger.error(f"Undo failed: {e}")
            return False
    
    def redo(self) -> bool:
        """Redo the operation."""
        if self._state is None or self._state.image_after is None:
            return False
        
        try:
            self._image_holder.set_image(self._state.image_after.copy())
            return True
        except Exception as e:
            logger.error(f"Redo failed: {e}")
            return False


class ImageHolder:
    """Interface for objects that hold an image."""
    
    def __init__(self, image: Optional[np.ndarray] = None):
        self._image = image
        self._on_change_callback: Optional[Callable[[np.ndarray], None]] = None
    
    def get_image(self) -> Optional[np.ndarray]:
        """Get current image."""
        return self._image
    
    def set_image(self, image: np.ndarray):
        """Set current image."""
        self._image = image
        if self._on_change_callback:
            self._on_change_callback(image)
    
    def set_change_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback for image changes."""
        self._on_change_callback = callback


class HistoryManager:
    """
    Manages command history for undo/redo functionality.
    
    Features:
        - Unlimited undo/redo (memory permitting)
        - Memory limit to prevent excessive usage
        - History persistence (optional)
    """
    
    def __init__(
        self,
        max_history: int = 50,
        max_memory_mb: int = 500
    ):
        """
        Initialize history manager.
        
        Args:
            max_history: Maximum number of commands to store
            max_memory_mb: Maximum memory usage in MB
        """
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []
        self._current_index: int = -1
        
        self._max_history = max_history
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        
        self._on_history_change: Optional[Callable[[], None]] = None
    
    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._current_index >= 0
    
    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    @property
    def history_count(self) -> int:
        """Get number of items in history."""
        return self._current_index + 1
    
    @property
    def redo_count(self) -> int:
        """Get number of items in redo stack."""
        return len(self._redo_stack)
    
    def execute(self, command: Command) -> bool:
        """
        Execute a command and add it to history.
        
        Args:
            command: Command to execute
            
        Returns:
            True if command executed successfully
        """
        if command.execute():
            # Clear redo stack
            self._redo_stack.clear()
            
            # Trim history to current position
            self._history = self._history[:self._current_index + 1]
            
            # Add command to history
            self._history.append(command)
            self._current_index += 1
            
            # Enforce limits
            self._enforce_limits()
            
            # Notify listeners
            self._notify_change()
            
            logger.debug(f"Executed: {command.description}")
            return True
        
        return False
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if undo was successful
        """
        if not self.can_undo:
            return False
        
        command = self._history[self._current_index]
        
        if command.undo():
            self._redo_stack.append(command)
            self._current_index -= 1
            
            self._notify_change()
            
            logger.debug(f"Undone: {command.description}")
            return True
        
        return False
    
    def redo(self) -> bool:
        """
        Redo the last undone command.
        
        Returns:
            True if redo was successful
        """
        if not self.can_redo:
            return False
        
        command = self._redo_stack.pop()
        
        if command.redo():
            self._current_index += 1
            
            self._notify_change()
            
            logger.debug(f"Redone: {command.description}")
            return True
        
        # Put back on redo stack if failed
        self._redo_stack.append(command)
        return False
    
    def clear(self):
        """Clear all history."""
        self._history.clear()
        self._redo_stack.clear()
        self._current_index = -1
        self._notify_change()
    
    def get_history_descriptions(self) -> List[str]:
        """Get list of command descriptions in history."""
        return [cmd.description for cmd in self._history[:self._current_index + 1]]
    
    def get_redo_descriptions(self) -> List[str]:
        """Get list of command descriptions in redo stack."""
        return [cmd.description for cmd in reversed(self._redo_stack)]
    
    def set_change_callback(self, callback: Callable[[], None]):
        """Set callback for history changes."""
        self._on_history_change = callback
    
    def _notify_change(self):
        """Notify listeners of history change."""
        if self._on_history_change:
            self._on_history_change()
    
    def _enforce_limits(self):
        """Enforce history size and memory limits."""
        # Enforce max history count
        while len(self._history) > self._max_history:
            self._history.pop(0)
            self._current_index -= 1
        
        # Enforce memory limit
        while self._estimate_memory() > self._max_memory_bytes and len(self._history) > 1:
            self._history.pop(0)
            self._current_index -= 1
    
    def _estimate_memory(self) -> int:
        """Estimate memory usage of history."""
        total = 0
        for cmd in self._history:
            if hasattr(cmd, '_state') and cmd._state is not None:
                if cmd._state.image_before is not None:
                    total += cmd._state.image_before.nbytes
                if cmd._state.image_after is not None:
                    total += cmd._state.image_after.nbytes
        return total


# Convenience functions for creating common commands

def create_crop_command(
    image_holder: ImageHolder,
    x: int, y: int, w: int, h: int
) -> ImageCommand:
    """Create a crop command."""
    def crop_operation(image: np.ndarray) -> np.ndarray:
        return image[y:y+h, x:x+w].copy()
    
    return ImageCommand(
        CommandType.CROP,
        image_holder,
        crop_operation,
        f"Crop to {w}x{h} at ({x}, {y})"
    )


def create_rotate_command(
    image_holder: ImageHolder,
    angle: int
) -> ImageCommand:
    """Create a rotation command."""
    import cv2
    
    def rotate_operation(image: np.ndarray) -> np.ndarray:
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270 or angle == -90:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image
    
    return ImageCommand(
        CommandType.ROTATE,
        image_holder,
        rotate_operation,
        f"Rotate {angle}°"
    )


def create_resize_command(
    image_holder: ImageHolder,
    width: int,
    height: int
) -> ImageCommand:
    """Create a resize command."""
    import cv2
    
    def resize_operation(image: np.ndarray) -> np.ndarray:
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LANCZOS4)
    
    return ImageCommand(
        CommandType.RESIZE,
        image_holder,
        resize_operation,
        f"Resize to {width}x{height}"
    )


def create_filter_command(
    image_holder: ImageHolder,
    filter_func: Callable[[np.ndarray], np.ndarray],
    filter_name: str
) -> ImageCommand:
    """Create a generic filter command."""
    return ImageCommand(
        CommandType.FILTER,
        image_holder,
        filter_func,
        f"Apply {filter_name}"
    )
