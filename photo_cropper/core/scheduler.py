#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler for Photo Cropper v8.5.

Provides scheduled batch processing functionality.
"""

import os
import logging
from datetime import datetime, time as dtime
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QTime

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Schedule type options."""
    ONCE = "once"          # Run once at specified time
    DAILY = "daily"        # Run every day at specified time
    INTERVAL = "interval"  # Run every N minutes
    HOURLY = "hourly"      # Run every hour


@dataclass
class ScheduleTask:
    """Represents a scheduled task."""
    task_id: str
    name: str
    schedule_type: ScheduleType
    time: Optional[QTime] = None  # For ONCE, DAILY
    interval_minutes: int = 60    # For INTERVAL
    input_path: str = ""
    output_path: str = ""
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class Scheduler(QObject):
    """
    Task scheduler for automated batch processing.
    
    Features:
        - One-time scheduled tasks
        - Daily recurring tasks
        - Interval-based tasks
        - Multiple concurrent schedules
    """
    
    # Signals
    task_started = pyqtSignal(str)      # task_id
    task_completed = pyqtSignal(str, bool)  # task_id, success
    task_added = pyqtSignal(str)        # task_id
    task_removed = pyqtSignal(str)      # task_id
    schedule_updated = pyqtSignal()
    
    def __init__(
        self,
        process_callback: Optional[Callable[[str, str], bool]] = None,
        parent: Optional[QObject] = None
    ):
        """
        Initialize scheduler.
        
        Args:
            process_callback: Function to process batch (input_dir, output_dir) -> success
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self._process_callback = process_callback
        self._tasks: dict[str, ScheduleTask] = {}
        self._task_timers: dict[str, QTimer] = {}
        
        # Master timer for checking schedules (runs every minute)
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_schedules)
        
        self._is_running = False
        self._task_counter = 0
    
    def start(self):
        """Start the scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        self._check_timer.start(60000)  # Check every minute
        
        # Initial check
        self._check_schedules()
        
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self._is_running = False
        self._check_timer.stop()
        
        # Stop all task timers
        for timer in self._task_timers.values():
            timer.stop()
        
        logger.info("Scheduler stopped")
    
    def add_task(self, task: ScheduleTask) -> str:
        """
        Add a scheduled task.
        
        Args:
            task: Task to add
            
        Returns:
            Task ID
        """
        if not task.task_id:
            self._task_counter += 1
            task.task_id = f"task_{self._task_counter}"
        
        self._tasks[task.task_id] = task
        self._calculate_next_run(task)
        
        self.task_added.emit(task.task_id)
        self.schedule_updated.emit()
        
        logger.info(f"Added task: {task.name} ({task.task_id})")
        
        return task.task_id
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            task_id: ID of task to remove
            
        Returns:
            True if removed
        """
        if task_id not in self._tasks:
            return False
        
        # Stop task timer if exists
        if task_id in self._task_timers:
            self._task_timers[task_id].stop()
            del self._task_timers[task_id]
        
        del self._tasks[task_id]
        
        self.task_removed.emit(task_id)
        self.schedule_updated.emit()
        
        logger.info(f"Removed task: {task_id}")
        
        return True
    
    def get_task(self, task_id: str) -> Optional[ScheduleTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduleTask]:
        """Get all scheduled tasks."""
        return list(self._tasks.values())
    
    def enable_task(self, task_id: str, enabled: bool = True):
        """Enable or disable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = enabled
            self.schedule_updated.emit()
    
    def run_task_now(self, task_id: str) -> bool:
        """
        Run a task immediately.
        
        Args:
            task_id: ID of task to run
            
        Returns:
            True if started successfully
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        return self._execute_task(task)
    
    def set_process_callback(self, callback: Callable[[str, str], bool]):
        """Set the processing callback function."""
        self._process_callback = callback
    
    def _check_schedules(self):
        """Check all schedules and run due tasks."""
        now = datetime.now()
        
        for task in self._tasks.values():
            if not task.enabled:
                continue
            
            if task.next_run and now >= task.next_run:
                self._execute_task(task)
                self._calculate_next_run(task)
    
    def _calculate_next_run(self, task: ScheduleTask):
        """Calculate next run time for a task."""
        now = datetime.now()
        
        if task.schedule_type == ScheduleType.ONCE:
            if task.time:
                next_run = datetime.combine(now.date(), dtime(
                    task.time.hour(), task.time.minute()
                ))
                if next_run <= now:
                    # Already passed today, schedule for tomorrow
                    from datetime import timedelta
                    next_run += timedelta(days=1)
                task.next_run = next_run
            
        elif task.schedule_type == ScheduleType.DAILY:
            if task.time:
                next_run = datetime.combine(now.date(), dtime(
                    task.time.hour(), task.time.minute()
                ))
                if next_run <= now:
                    from datetime import timedelta
                    next_run += timedelta(days=1)
                task.next_run = next_run
            
        elif task.schedule_type == ScheduleType.INTERVAL:
            from datetime import timedelta
            if task.last_run:
                task.next_run = task.last_run + timedelta(minutes=task.interval_minutes)
            else:
                task.next_run = now + timedelta(minutes=task.interval_minutes)
            
        elif task.schedule_type == ScheduleType.HOURLY:
            from datetime import timedelta
            next_hour = now.replace(minute=0, second=0, microsecond=0)
            next_hour += timedelta(hours=1)
            task.next_run = next_hour
    
    def _execute_task(self, task: ScheduleTask) -> bool:
        """Execute a scheduled task."""
        if not self._process_callback:
            logger.warning("No process callback set")
            return False
        
        if not task.input_path or not os.path.isdir(task.input_path):
            logger.error(f"Invalid input path for task {task.task_id}")
            return False
        
        output_path = task.output_path or task.input_path
        
        self.task_started.emit(task.task_id)
        logger.info(f"Starting scheduled task: {task.name}")
        
        try:
            success = self._process_callback(task.input_path, output_path)
            task.last_run = datetime.now()
            
            self.task_completed.emit(task.task_id, success)
            logger.info(f"Task completed: {task.name} (success={success})")
            
            # For one-time tasks, disable after execution
            if task.schedule_type == ScheduleType.ONCE:
                task.enabled = False
                self.schedule_updated.emit()
            
            return success
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.task_completed.emit(task.task_id, False)
            return False
    
    def create_daily_task(
        self,
        name: str,
        hour: int,
        minute: int,
        input_path: str,
        output_path: str = ""
    ) -> str:
        """
        Create a daily scheduled task.
        
        Args:
            name: Task name
            hour: Hour (0-23)
            minute: Minute (0-59)
            input_path: Input directory
            output_path: Output directory
            
        Returns:
            Task ID
        """
        task = ScheduleTask(
            task_id="",
            name=name,
            schedule_type=ScheduleType.DAILY,
            time=QTime(hour, minute),
            input_path=input_path,
            output_path=output_path
        )
        return self.add_task(task)
    
    def create_interval_task(
        self,
        name: str,
        interval_minutes: int,
        input_path: str,
        output_path: str = ""
    ) -> str:
        """
        Create an interval-based task.
        
        Args:
            name: Task name
            interval_minutes: Interval in minutes
            input_path: Input directory
            output_path: Output directory
            
        Returns:
            Task ID
        """
        task = ScheduleTask(
            task_id="",
            name=name,
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=interval_minutes,
            input_path=input_path,
            output_path=output_path
        )
        return self.add_task(task)
    
    def get_next_runs(self) -> List[tuple]:
        """
        Get list of upcoming task runs.
        
        Returns:
            List of (task_name, next_run_datetime) tuples, sorted by time
        """
        runs = []
        for task in self._tasks.values():
            if task.enabled and task.next_run:
                runs.append((task.name, task.next_run))
        
        runs.sort(key=lambda x: x[1])
        return runs
