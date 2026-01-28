#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Naming Rules Module for Photo Cropper.

Provides customizable file naming rules for output files.
"""

import os
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any


@dataclass
class NamingRule:
    """File naming rule configuration.
    
    Attributes:
        prefix: Prefix to add before filename
        suffix: Suffix to add after filename (before extension)
        use_counter: Whether to add sequential counter
        counter_start: Starting number for counter
        counter_padding: Zero-padding width (e.g., 3 -> 001, 002)
        use_date: Whether to add date to filename
        date_format: Date format string
        date_position: Where to place date ('prefix', 'suffix')
        preserve_original_name: Keep original filename as part of new name
        custom_pattern: Custom pattern using placeholders
        separator: Character between name parts
    
    Pattern placeholders:
        {name} - Original filename (without extension)
        {ext} - Original extension
        {counter} - Sequential counter
        {date} - Current date
        {datetime} - Current date and time
        {parent} - Parent folder name
    """
    prefix: str = ""
    suffix: str = "_cropped"
    use_counter: bool = False
    counter_start: int = 1
    counter_padding: int = 3
    use_date: bool = False
    date_format: str = "%Y%m%d"
    date_position: str = "suffix"  # 'prefix' or 'suffix'
    preserve_original_name: bool = True
    custom_pattern: str = ""  # Empty means use standard generation
    separator: str = "_"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NamingRule':
        """Create from dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class NamingRuleEngine:
    """Engine for generating filenames based on naming rules."""
    
    # Default presets
    PRESETS = {
        "default": NamingRule(suffix="_cropped"),
        "numbered": NamingRule(
            preserve_original_name=False,
            prefix="photo",
            use_counter=True,
            counter_padding=4,
            suffix=""
        ),
        "dated": NamingRule(
            suffix="",
            use_date=True,
            date_format="%Y%m%d_%H%M%S",
            date_position="suffix"
        ),
        "organized": NamingRule(
            custom_pattern="{date}_{parent}_{counter:04d}"
        ),
    }
    
    def __init__(self, rule: Optional[NamingRule] = None):
        """Initialize naming rule engine.
        
        Args:
            rule: Naming rule to use. Uses default if None.
        """
        self.rule = rule or NamingRule()
        self._counter = self.rule.counter_start
    
    def reset_counter(self, start: Optional[int] = None):
        """Reset the counter.
        
        Args:
            start: New starting value. Uses rule's counter_start if None.
        """
        self._counter = start if start is not None else self.rule.counter_start
    
    @property
    def current_counter(self) -> int:
        """Get current counter value."""
        return self._counter
    
    def generate_name(self, original_path: str,
                     output_dir: Optional[str] = None,
                     output_format: Optional[str] = None,
                     index: Optional[int] = None,
                     ensure_unique: bool = True) -> str:
        """
        Generate output filename based on rules.
        
        Args:
            original_path: Original file path
            output_dir: Output directory (uses original dir if None)
            output_format: Output format/extension (preserves original if None)
            index: Explicit counter index (uses internal counter if None)
            
        Returns:
            Generated output file path
        """
        # Parse original path
        original_dir = os.path.dirname(original_path)
        original_name = os.path.basename(original_path)
        name_without_ext, original_ext = os.path.splitext(original_name)
        parent_folder = os.path.basename(original_dir)
        
        # Determine output directory and extension
        out_dir = output_dir or original_dir
        out_ext = f".{output_format.lower().strip('.')}" if output_format else original_ext
        
        # Get counter value
        counter = index if index is not None else self._counter
        
        # Check for custom pattern
        if self.rule.custom_pattern:
            new_name = self._apply_pattern(
                self.rule.custom_pattern,
                name_without_ext,
                out_ext,
                counter,
                parent_folder
            )
        else:
            new_name = self._generate_standard_name(
                name_without_ext,
                counter,
                parent_folder
            )
        
        # Increment counter for next call
        if index is None:
            self._counter += 1
        
        # Build final path
        final_path = os.path.join(out_dir, new_name + out_ext)
        
        # Ensure uniqueness
        if ensure_unique:
            final_path = self._ensure_unique(final_path)
        
        return final_path
    
    def _generate_standard_name(self, original_name: str,
                                counter: int,
                                parent_folder: str) -> str:
        """Generate filename using standard rules."""
        parts = []
        
        # Prefix
        if self.rule.prefix:
            parts.append(self.rule.prefix)
        
        # Date (if at prefix position)
        if self.rule.use_date and self.rule.date_position == "prefix":
            parts.append(datetime.now().strftime(self.rule.date_format))
        
        # Original name
        if self.rule.preserve_original_name:
            parts.append(original_name)
        
        # Counter
        if self.rule.use_counter:
            counter_str = str(counter).zfill(self.rule.counter_padding)
            parts.append(counter_str)
        
        # Date (if at suffix position)
        if self.rule.use_date and self.rule.date_position == "suffix":
            parts.append(datetime.now().strftime(self.rule.date_format))
        
        # Suffix
        if self.rule.suffix:
            # Handle suffix that starts with separator
            suffix = self.rule.suffix
            if suffix.startswith(self.rule.separator):
                suffix = suffix[len(self.rule.separator):]
            parts.append(suffix)
        
        # Join parts
        result = self.rule.separator.join(filter(None, parts))
        
        return result if result else original_name
    
    def _apply_pattern(self, pattern: str, original_name: str,
                      ext: str, counter: int, parent_folder: str) -> str:
        """Apply custom pattern with placeholders."""
        now = datetime.now()
        
        # Basic replacements
        result = pattern
        result = result.replace("{name}", original_name)
        result = result.replace("{ext}", ext.lstrip('.'))
        result = result.replace("{parent}", parent_folder)
        result = result.replace("{date}", now.strftime("%Y%m%d"))
        result = result.replace("{datetime}", now.strftime("%Y%m%d_%H%M%S"))
        
        # Counter with optional format specifier
        # {counter} or {counter:04d}
        counter_pattern = re.compile(r'\{counter(?::(\d+)d)?\}')
        match = counter_pattern.search(result)
        if match:
            padding = int(match.group(1)) if match.group(1) else self.rule.counter_padding
            counter_str = str(counter).zfill(padding)
            result = counter_pattern.sub(counter_str, result)
        
        return result
    
    def _ensure_unique(self, path: str) -> str:
        """Ensure filename is unique by adding counter if needed."""
        if not os.path.exists(path):
            return path
        
        base, ext = os.path.splitext(path)
        counter = 1
        
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        
        return f"{base}_{counter}{ext}"
    
    def preview_names(self, files: List[str],
                     output_dir: Optional[str] = None,
                     output_format: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Preview generated filenames without renaming.
        
        Args:
            files: List of input file paths
            output_dir: Output directory
            output_format: Output format
            
        Returns:
            List of (original, new) filename tuples
        """
        # Save and reset counter
        saved_counter = self._counter
        self.reset_counter()
        
        previews = []
        for filepath in files:
            new_path = self.generate_name(
                filepath, 
                output_dir=output_dir,
                output_format=output_format
            )
            previews.append((filepath, new_path))
        
        # Restore counter
        self._counter = saved_counter
        
        return previews


def batch_rename_preview(files: List[str], 
                        rule: NamingRule,
                        output_dir: Optional[str] = None,
                        output_format: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Preview batch rename operation.
    
    Args:
        files: List of file paths to rename
        rule: Naming rule to apply
        output_dir: Output directory
        output_format: Output format
        
    Returns:
        List of (original, new) path tuples
    """
    engine = NamingRuleEngine(rule)
    return engine.preview_names(files, output_dir, output_format)


def batch_rename_execute(rename_map: List[Tuple[str, str]],
                        copy_mode: bool = False,
                        overwrite: bool = False) -> Tuple[int, List[str]]:
    """
    Execute batch rename/copy operation.
    
    Args:
        rename_map: List of (source, destination) tuples
        copy_mode: If True, copy files instead of moving
        overwrite: If True, overwrite existing files
        
    Returns:
        Tuple of (success_count, error_messages)
    """
    import shutil
    
    success_count = 0
    errors = []
    
    for src, dst in rename_map:
        try:
            # Skip if source doesn't exist
            if not os.path.exists(src):
                errors.append(f"Source not found: {src}")
                continue
            
            # Check destination
            if os.path.exists(dst) and not overwrite:
                errors.append(f"Destination exists: {dst}")
                continue
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            if copy_mode:
                shutil.copy2(src, dst)
            else:
                shutil.move(src, dst)
            
            success_count += 1
            
        except Exception as e:
            errors.append(f"Error processing {src}: {e}")
    
    return success_count, errors
