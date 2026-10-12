"""
Workspace Manager — manages projects, working directories, and execution sessions.

Provides:
  - Project/repository tracking
  - Working directory management
  - Artifact management
  - Temporary file lifecycle
  - Execution session isolation

Integrates with the existing TERMINAL_CWD mechanism and project
context file discovery (AGENTS.md, CLAUDE.md, .cursorrules).
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class Workspace:
    """A workspace (project) managed by the kernel.

    Attributes:
        id: Unique workspace ID
        name: Human-readable name
        root_path: Absolute path to the workspace root
        description: Optional description
        created_at: Creation timestamp
        tags: Optional tags for categorization
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    root_path: str = ""
    description: str = ""
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkspaceManager:
    """Manages workspaces and execution sessions.

    Usage:
        wm = WorkspaceManager(event_bus)

        # Register a workspace for a project
        ws = wm.create_workspace("my-project", "/home/user/project")

        # Create a temporary execution session
        session_path = wm.create_session("my-task")
        # ... run tools in session_path ...
        wm.cleanup_session("my-task")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._workspaces: Dict[str, Workspace] = {}
        self._sessions: Dict[str, str] = {}  # session_id -> temp dir path
        self._default_temp_dir: Optional[str] = None

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    def create_workspace(self, name: str, root_path: str,
                         description: str = "",
                         tags: List[str] = None) -> Workspace:
        """Create a new workspace from an existing directory."""
        abs_path = str(Path(root_path).expanduser().resolve())

        if not os.path.isdir(abs_path):
            raise ValueError(f"Workspace path does not exist or is not a directory: {abs_path}")

        ws = Workspace(
            name=name,
            root_path=abs_path,
            description=description,
            tags=tags or [],
        )
        with self._lock:
            self._workspaces[ws.id] = ws

        logger.info("Workspace: created '%s' at %s", name, abs_path)
        if self._event_bus:
            self._event_bus.emit_async("workspace.created", {
                "workspace_id": ws.id,
                "name": name,
                "path": abs_path,
            })
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        with self._lock:
            return self._workspaces.get(workspace_id)

    def find_workspace_by_path(self, path: str) -> Optional[Workspace]:
        """Find a workspace whose root_path matches or contains the given path."""
        resolved = str(Path(path).expanduser().resolve())
        with self._lock:
            for ws in self._workspaces.values():
                try:
                    Path(resolved).relative_to(ws.root_path)
                    return ws
                except ValueError:
                    continue
        return None

    def find_workspace_by_name(self, name: str) -> Optional[Workspace]:
        """Find a workspace by name (case-insensitive)."""
        name_lower = name.lower()
        with self._lock:
            for ws in self._workspaces.values():
                if ws.name.lower() == name_lower:
                    return ws
        return None

    def list_workspaces(self) -> List[Workspace]:
        """List all registered workspaces."""
        with self._lock:
            return sorted(
                self._workspaces.values(),
                key=lambda w: w.name,
            )

    def remove_workspace(self, workspace_id: str) -> bool:
        """Remove a workspace from tracking (does NOT delete files)."""
        with self._lock:
            ws = self._workspaces.pop(workspace_id, None)
        if ws:
            logger.info("Workspace: removed '%s'", ws.name)
            return True
        return False

    # ------------------------------------------------------------------
    # Context file discovery
    # ------------------------------------------------------------------

    def discover_context_files(self, workspace_id: str) -> List[str]:
        """Discover context files (AGENTS.md, CLAUDE.md, .cursorrules) in a workspace.

        Mirrors the existing context file discovery in the agent.
        """
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return []

        root = Path(ws.root_path)
        context_files = []

        # Search patterns matching the existing agent.coding_context behavior
        for pattern in ("AGENTS.md", "CLAUDE.md", ".cursorrules", ".cursor/rules/*.mdc"):
            for f in root.glob(pattern):
                if f.is_file():
                    context_files.append(str(f))

        # Also check parent directories up to git root or home
        # (mirrors existing resolution logic)
        current = root
        while current.parent != current:
            for name in ("AGENTS.md", "CLAUDE.md", ".cursorrules"):
                f = current / name
                if f.is_file() and str(f) not in context_files:
                    context_files.append(str(f))
            # Stop at git root or filesystem root
            if (current / ".git").is_dir():
                break
            current = current.parent

        return sorted(context_files)

    def get_agent_context(self, workspace_id: str, max_chars: int = 8000) -> str:
        """Read and concatenate context files from a workspace.

        Returns a formatted string suitable for injection into the agent prompt.
        """
        files = self.discover_context_files(workspace_id)
        if not files:
            return ""

        parts = []
        total = 0
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                if total + len(content) > max_chars:
                    content = content[: max_chars - total] + "\n[... truncated ...]"
                parts.append(f"--- {os.path.basename(fp)} ---\n{content}")
                total += len(content)
            except (OSError, IOError):
                pass

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, session_id: str = None,
                       prefix: str = "kernel-session-") -> str:
        """Create a temporary directory for an execution session.

        Returns the path to the temp directory.
        """
        sid = session_id or uuid.uuid4().hex[:12]
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        with self._lock:
            self._sessions[sid] = temp_dir

        logger.debug("Workspace: created session %s at %s", sid, temp_dir)
        return temp_dir

    def get_session_path(self, session_id: str) -> Optional[str]:
        """Get the temp directory path for a session."""
        with self._lock:
            return self._sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        """Remove a session's temporary directory."""
        with self._lock:
            temp_dir = self._sessions.pop(session_id, None)
        if temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug("Workspace: cleaned up session %s", session_id)
            return True
        return False

    def cleanup_all_sessions(self) -> int:
        """Clean up all temporary sessions."""
        with self._lock:
            session_ids = list(self._sessions.keys())
        count = 0
        for sid in session_ids:
            if self.cleanup_session(sid):
                count += 1
        return count

    # ------------------------------------------------------------------
    # Artifact management
    # ------------------------------------------------------------------

    def save_artifact(self, name: str, content: str,
                      workspace_id: str = None,
                      session_id: str = None,
                      subdir: str = "artifacts") -> Optional[str]:
        """Save an artifact to a workspace or session directory.

        Returns the path to the saved artifact, or None on failure.
        """
        base_path = None
        if workspace_id:
            ws = self.get_workspace(workspace_id)
            if ws:
                base_path = Path(ws.root_path) / subdir
        elif session_id:
            session_path = self.get_session_path(session_id)
            if session_path:
                base_path = Path(session_path) / subdir

        if base_path is None:
            return None

        base_path.mkdir(parents=True, exist_ok=True)
        file_path = base_path / name

        try:
            file_path.write_text(content, encoding="utf-8")
            logger.debug("Workspace: saved artifact %s", file_path)
            return str(file_path)
        except OSError as exc:
            logger.error("Workspace: failed to save artifact %s: %s", name, exc)
            return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def resolve_path(self, path: str,
                     workspace_id: str = None) -> str:
        """Resolve a potentially relative path against a workspace root.

        If the path is absolute, returns it as-is (after normalization).
        If relative and a workspace is specified, resolves against the workspace root.
        Otherwise, resolves against the current working directory.
        """
        p = Path(path).expanduser()
        if p.is_absolute():
            return str(p.resolve())

        if workspace_id:
            ws = self.get_workspace(workspace_id)
            if ws:
                return str((Path(ws.root_path) / p).resolve())

        return str(p.resolve())

    def stats(self) -> Dict[str, Any]:
        """Return workspace manager statistics."""
        with self._lock:
            return {
                "workspaces": len(self._workspaces),
                "active_sessions": len(self._sessions),
                "workspace_names": [w.name for w in self._workspaces.values()],
            }

    def shutdown(self) -> None:
        """Clean up all sessions on shutdown."""
        count = self.cleanup_all_sessions()
        if count > 0:
            logger.info("Workspace: cleaned up %d sessions on shutdown", count)
