"""
Workspace Monitor — Workspace and project detection.

Detects active project context from the filesystem, open editor,
and current working directory. Provides structured events for
workspace changes.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """Information about a detected workspace/project.

    Attributes:
        path: Absolute path to workspace root
        name: Workspace/project name
        type: Type (git_repo, editor_workspace, directory)
        vcs: Version control system (git, hg, svn) or None
        languages: Detected programming languages
        frameworks: Detected frameworks
        open_files: Currently open files in workspace
        active_branch: Active git branch (if applicable)
        has_uncommitted: Whether there are uncommitted changes
        metadata: Additional metadata
    """
    path: str = ""
    name: str = ""
    type: str = "directory"
    vcs: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)
    active_branch: Optional[str] = None
    has_uncommitted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceChange:
    """Represents a detected workspace change.

    Attributes:
        previous: Previous workspace info (None if first)
        current: Current workspace info
        change_type: Type of change (switched, modified, opened, closed)
        detected_at: When the change was detected
    """
    previous: Optional[WorkspaceInfo] = None
    current: Optional[WorkspaceInfo] = None
    change_type: str = "unknown"
    detected_at: float = 0.0


class WorkspaceMonitor:
    """Monitors workspace and project context changes.

    Detects when the user switches projects, opens files in
    different workspaces, or starts/stops working on a project.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._current_workspace: Optional[WorkspaceInfo] = None
        self._subscribers: List[Callable[[WorkspaceChange], None]] = []
        self._history: List[WorkspaceChange] = []
        self._max_history: int = 50
        self._detectors: List[Callable[[], Optional[WorkspaceInfo]]] = []
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval: float = 5.0
        self._running = False

    def initialize(self) -> None:
        """Initialize the workspace monitor."""
        # Register built-in detectors
        self._detectors.append(self._detect_from_current_dir)
        self._detectors.append(self._detect_from_env)
        logger.info("WorkspaceMonitor: initialized")

    def register_detector(self, detector: Callable[[], Optional[WorkspaceInfo]]) -> None:
        """Register a custom workspace detector.

        Args:
            detector: Callable returning WorkspaceInfo or None
        """
        with self._lock:
            self._detectors.append(detector)

    def detect_workspace(self) -> Optional[WorkspaceInfo]:
        """Detect the current workspace using registered detectors.

        Later-registered detectors take priority over earlier ones,
        allowing custom detectors to override built-in detection.

        Returns:
            WorkspaceInfo or None
        """
        result: Optional[WorkspaceInfo] = None
        for detector in self._detectors:
            try:
                candidate = detector()
                if candidate is not None:
                    result = candidate  # Later detectors override earlier ones
            except Exception as exc:
                logger.debug("WorkspaceMonitor: detector failed: %s", exc)
        return result

    def get_current_workspace(self) -> Optional[WorkspaceInfo]:
        """Get the currently detected workspace.

        Returns:
            Current WorkspaceInfo or None
        """
        with self._lock:
            return self._current_workspace

    def subscribe(self, callback: Callable[[WorkspaceChange], None]) -> Callable:
        """Subscribe to workspace change events.

        Args:
            callback: Receives WorkspaceChange

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

    def start_polling(self, interval: float = 5.0) -> None:
        """Start periodic workspace detection.

        Args:
            interval: Poll interval in seconds
        """
        if self._running:
            return
        self._running = True
        self._poll_interval = interval

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="workspace-monitor",
        )
        self._poll_thread.start()
        logger.info("WorkspaceMonitor: polling started (interval=%.1fs)", interval)

    def stop_polling(self) -> None:
        """Stop periodic workspace detection."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2)
        logger.info("WorkspaceMonitor: polling stopped")

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            workspace = self.detect_workspace()
            if workspace:
                self._update(workspace)
            time.sleep(self._poll_interval)

    def _update(self, workspace: WorkspaceInfo) -> None:
        """Update workspace state and notify subscribers if changed.

        Args:
            workspace: Detected workspace info
        """
        with self._lock:
            prev = self._current_workspace
            if prev and prev.path == workspace.path and prev.name == workspace.name:
                return  # No meaningful change

            change = WorkspaceChange(
                previous=prev,
                current=workspace,
                change_type="switched" if prev else "detected",
                detected_at=time.time(),
            )

            self._current_workspace = workspace
            self._history.append(change)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            subscribers = list(self._subscribers)

        for cb in subscribers:
            try:
                cb(change)
            except Exception as exc:
                logger.debug("WorkspaceMonitor: subscriber failed: %s", exc)

    # ------------------------------------------------------------------
    # Built-in detectors
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_from_current_dir() -> Optional[WorkspaceInfo]:
        """Detect workspace from the current working directory.

        Walks up the directory tree to find a VCS root or project marker.

        Returns:
            WorkspaceInfo or None
        """
        cwd = Path.cwd().resolve()
        path = cwd
        for _ in range(5):  # Walk up at most 5 levels
            markers = [path / ".git", path / ".hg", path / ".svn"]
            for marker in markers:
                if marker.exists():
                    return WorkspaceInfo(
                        path=str(path),
                        name=path.name,
                        type="git_repo" if marker.name == ".git" else "vcs_repo",
                        vcs=marker.name.lstrip("."),
                    )
            parent = path.parent
            if parent == path:
                break
            path = parent

        return WorkspaceInfo(
            path=str(cwd),
            name=cwd.name,
            type="directory",
        )

    @staticmethod
    def _detect_from_env() -> Optional[WorkspaceInfo]:
        """Detect workspace from environment variables.

        Returns:
            WorkspaceInfo or None
        """
        project_dir = os.getenv("PROJECT_DIR") or os.getenv("WORKSPACE_DIR")
        if project_dir:
            path = Path(project_dir).resolve()
            if path.exists():
                return WorkspaceInfo(
                    path=str(path),
                    name=path.name,
                    type="env_workspace",
                )
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self._lock:
            return {
                "active": self._current_workspace.name if self._current_workspace else None,
                "type": self._current_workspace.type if self._current_workspace else None,
                "history_size": len(self._history),
                "polling": self._running,
                "detectors": len(self._detectors),
            }
