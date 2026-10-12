"""
Context Detector — Derives workspace context from active environment.

Understands the user's open project, repository, active files,
recent engineering tasks, and current workflow. Uses context
to improve suggestions without exposing unnecessary data.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextEvent(enum.Enum):
    """Events emitted by the context detector."""
    CONTEXT_CAPTURED = "context.captured"
    CONTEXT_CHANGED = "context.changed"
    PROJECT_DETECTED = "context.project_detected"
    FILE_CHANGED = "context.file_changed"
    TASK_DETECTED = "context.task_detected"


@dataclass
class WorkspaceContext:
    """Comprehensive workspace context snapshot.

    Attributes:
        timestamp: When the context was captured
        project_name: Detected project name
        project_root: Project root directory
        repository: VCS repository info
        active_branch: Current VCS branch
        open_files: Currently open files
        active_file: Most recently active file
        language: Primary language
        framework: Detected framework
        recent_tasks: Recent engineering tasks
        current_workflow: Current workflow if any
        environment: Environment identifiers (vscode, terminal, etc.)
        metadata: Additional context data
    """
    timestamp: float = 0.0
    project_name: str = ""
    project_root: str = ""
    repository: str = ""
    active_branch: str = ""
    open_files: List[str] = field(default_factory=list)
    active_file: str = ""
    language: str = ""
    framework: str = ""
    recent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    current_workflow: str = ""
    environment: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextDetector:
    """Derives workspace and project context from the environment.

    Combines signals from the desktop (active window, open files),
    filesystem (VCS state, project markers), and ongoing workflows
    to provide a comprehensive context snapshot.

    Usage:
        detector = ContextDetector()
        detector.register_source("window", window_info_fn)
        context = detector.capture()
        print(f"Project: {context.project_name}")
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._last_context: Optional[WorkspaceContext] = None
        self._subscribers: List[Callable[[ContextEvent, WorkspaceContext], None]] = []
        self._context_sources: List[Callable[[], Optional[Dict[str, Any]]]] = []
        self._history: List[WorkspaceContext] = []
        self._max_history: int = 100

    def initialize(self) -> None:
        """Initialize the context detector."""
        logger.info("ContextDetector: initialized")

    def register_source(self, source_fn: Callable[[], Optional[Dict[str, Any]]]) -> None:
        """Register a context data source.

        A source function returns a dict that contributes to the
        WorkspaceContext, or None if unavailable.

        Args:
            source_fn: Context source callback
        """
        with self._lock:
            self._context_sources.append(source_fn)

    def capture(self) -> WorkspaceContext:
        """Capture the current workspace context.

        Gathers data from all registered sources and returns a
        comprehensive WorkspaceContext.

        Returns:
            Current WorkspaceContext
        """
        context = WorkspaceContext(timestamp=time.time())

        with self._lock:
            sources = list(self._context_sources)

        for source in sources:
            try:
                data = source()
                if data:
                    self._merge_data(context, data)
            except Exception as exc:
                logger.debug("ContextDetector: source failed: %s", exc)

        # Detect changes from last context
        with self._lock:
            changed = (
                self._last_context is None
                or self._last_context.project_name != context.project_name
                or self._last_context.active_file != context.active_file
            )

            if changed:
                self._last_context = context
                self._history.append(context)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]

                subscribers = list(self._subscribers)

        if changed:
            for cb in subscribers:
                try:
                    cb(ContextEvent.CONTEXT_CHANGED, context)
                except Exception as exc:
                    logger.debug("ContextDetector: subscriber failed: %s", exc)

        return context

    def get_last_context(self) -> Optional[WorkspaceContext]:
        """Get the most recently captured context.

        Returns:
            Last captured WorkspaceContext or None
        """
        with self._lock:
            return self._last_context

    def subscribe(self, callback: Callable[[ContextEvent, WorkspaceContext], None]) -> Callable:
        """Subscribe to context change events.

        Args:
            callback: Receives (event, context)

        Returns:
            Unsubscribe function
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    @staticmethod
    def _merge_data(context: WorkspaceContext, data: Dict[str, Any]) -> None:
        """Merge data from a source into the context.

        Args:
            context: Context to merge into
            data: Source data dict
        """
        for key, value in data.items():
            if hasattr(context, key) and value:
                existing = getattr(context, key)
                if not existing:
                    setattr(context, key, value)
                elif isinstance(existing, list) and isinstance(value, list):
                    # Merge lists uniquely
                    for item in value:
                        if item not in existing:
                            existing.append(item)

    def get_history(self, limit: int = 10) -> List[WorkspaceContext]:
        """Get recent context history.

        Args:
            limit: Max entries

        Returns:
            List of recent WorkspaceContext objects
        """
        with self._lock:
            return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        with self._lock:
            return {
                "has_context": self._last_context is not None,
                "project": self._last_context.project_name if self._last_context else None,
                "sources": len(self._context_sources),
                "history_size": len(self._history),
            }
