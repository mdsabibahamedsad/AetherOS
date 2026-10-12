#!/usr/bin/env python3
"""
Task Model — Unified Task Representation with Full Lifecycle

This module contains the Task class and related functionality for managing
task state, progress, and persistence. The CommandGateway uses this for
the core task representation.
"""

from __future__ import annotations

# Re-export from models for convenience
from .models import (
    Task,
    TaskState,
    TaskStep,
    TaskProgress,
    TaskRequest,
    TaskSource,
    ExecutionResult,
    to_json_serializable,
)

# Additional task utilities
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import json


@dataclass
class TaskEvent:
    """Event in a task's lifecycle."""
    task_id: str
    event_type: str  # state_change, step_start, step_complete, error, progress
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Manages task lifecycle, events, and persistence."""
    
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._tasks: Dict[str, Task] = {}
        self._events: List[TaskEvent] = []
        self._lock = threading.RLock()
        self._event_listeners: List[Callable[[TaskEvent], None]] = []
        self._task_change_listeners: List[Callable[[Task, TaskState, TaskState], None]] = []
    
    def create_task(self, request) -> Task:
        """Create a new task from a request."""
        with self._lock:
            task = Task(
                id=request.id if hasattr(request, 'id') else None,
                goal=getattr(request, 'user_intent', str(request)),
                request=request if hasattr(request, '__dataclass_fields__') else None,
            )
            self._tasks[task.id] = task
            self._emit_event(TaskEvent(task.id, "created", {"goal": task.goal}))
            return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task_state(self, task_id: str, new_state: TaskState) -> bool:
        """Update task state and notify listeners."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            old_state = task.state
            task.state = new_state
            self._emit_event(TaskEvent(task_id, "state_change", {
                "old_state": old_state.value,
                "new_state": new_state.value,
            }))
            self._notify_state_change(task, old_state, new_state)
            return True
    
    def add_event_listener(self, listener: Callable[[TaskEvent], None]) -> None:
        with self._lock:
            self._event_listeners.append(listener)
    
    def add_state_change_listener(self, listener: Callable[[Task, TaskState, TaskState], None]) -> None:
        with self._lock:
            self._task_change_listeners.append(listener)
    
    def _emit_event(self, event: TaskEvent) -> None:
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Event listener error: {e}")
    
    def _notify_state_change(self, task: Task, old_state: TaskState, new_state: TaskState) -> None:
        for listener in self._task_change_listeners:
            try:
                listener(task, old_state, new_state)
            except Exception as e:
                logger.warning(f"State change listener error: {e}")
    
    def list_tasks(self, state: TaskState | None = None, limit: int = 100) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
            if state:
                tasks = [t for t in tasks if t.state == state]
            return tasks[-limit:]
    
    def cleanup_completed_tasks(self, max_age_hours: int = 168) -> int:
        """Remove old completed/failed tasks."""
        with self._lock:
            cutoff = time.time() - (max_age_hours * 3600)
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                    if task.completed_at and task.completed_at.timestamp() < cutoff:
                        to_remove.append(task_id)
            for task_id in to_remove:
                del self._tasks[task_id]
            return len(to_remove)


# Import logger at module level
import logging
logger = logging.getLogger(__name__)