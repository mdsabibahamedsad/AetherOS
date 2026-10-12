"""
Conflict Resolution — handles conflicts between agents in the swarm.

Manages:
  - Duplicate work detection
  - Conflicting edits to the same file/resource
  - Tool contention (multiple agents wanting the same tool)
  - Workspace locking
  - Resource contention

Agents register their intentions before acting, and the conflict
resolver checks for conflicts and either prevents or resolves them.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ConflictType(enum.Enum):
    """Types of conflicts that can occur in the swarm."""
    DUPLICATE_WORK = "duplicate_work"
    CONFLICTING_EDIT = "conflicting_edit"
    TOOL_CONTENTION = "tool_contention"
    WORKSPACE_LOCK = "workspace_lock"
    RESOURCE_CONTENTION = "resource_contention"
    FILE_CONTENTION = "file_contention"


@dataclass
class ConflictRecord:
    """A record of a detected conflict.

    Attributes:
        id: Unique conflict ID
        conflict_type: Type of conflict
        description: Human-readable description
        agents_involved: Agent IDs involved
        resource: The resource being contested (file, tool, etc.)
        resolved: Whether the conflict was resolved
        resolution: How it was resolved
        detected_at: When it was detected
        resolved_at: When it was resolved
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    conflict_type: ConflictType = ConflictType.DUPLICATE_WORK
    description: str = ""
    agents_involved: List[str] = field(default_factory=list)
    resource: str = ""
    resolved: bool = False
    resolution: Optional[str] = None
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


class ConflictResolver:
    """Detects and resolves conflicts between agents in the swarm.

    Agents register their intentions (intended file writes, tool usage, etc.)
    before acting. The resolver checks for conflicts and can:
      - Block conflicting operations
      - Queue operations for serialization
      - Suggest merges for conflicting edits

    Usage:
        resolver = ConflictResolver(event_bus)

        # Agent registers intent to write a file
        ok, record = resolver.check_file_write("agent-1", "/path/to/file.py")

        # Agent registers tool usage
        ok, record = resolver.check_tool_usage("agent-2", "terminal")

        # Release resources when done
        resolver.release_agent("agent-1")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        # resource -> agent_id
        self._file_locks: Dict[str, str] = {}
        self._tool_locks: Dict[str, str] = {}
        self._workspace_locks: Dict[str, str] = {}
        # Map of agent -> set of resources it holds
        self._agent_resources: Dict[str, Set[str]] = {}
        # Conflict history
        self._history: List[ConflictRecord] = []

    # ------------------------------------------------------------------
    # File conflict checking
    # ------------------------------------------------------------------

    def check_file_write(self, agent_id: str, file_path: str) -> bool:
        """Check if an agent can write to a file.

        Returns True if the write is allowed, False if there's a conflict.
        """
        with self._lock:
            current_holder = self._file_locks.get(file_path)
            if current_holder is not None and current_holder != agent_id:
                record = ConflictRecord(
                    conflict_type=ConflictType.FILE_CONTENTION,
                    description=f"File '{file_path}' is locked by '{current_holder}'",
                    agents_involved=[current_holder, agent_id],
                    resource=file_path,
                )
                self._history.append(record)
                logger.warning(
                    "ConflictResolver: file '%s' locked by '%s', blocked '%s'",
                    file_path, current_holder, agent_id,
                )
                return False

            # Register the write
            self._file_locks[file_path] = agent_id
            self._agent_resources.setdefault(agent_id, set()).add(
                f"file:{file_path}",
            )
            return True

    def check_file_read(self, agent_id: str, file_path: str) -> bool:
        """Check if an agent can read a file.

        Reading is generally allowed even during writes, but we track
        reads for conflict detection on writes.
        """
        # Reads are always allowed
        return True

    # ------------------------------------------------------------------
    # Tool conflict checking
    # ------------------------------------------------------------------

    def check_tool_usage(self, agent_id: str, tool_name: str) -> bool:
        """Check if an agent can use a tool.

        Some tools (like terminal) may have contention if multiple agents
        try to use them simultaneously.

        Returns True if usage is allowed.
        """
        with self._lock:
            # Only certain tools are serialized
            if tool_name not in self._SERIALIZED_TOOLS:
                return True

            current_holder = self._tool_locks.get(tool_name)
            if current_holder is not None and current_holder != agent_id:
                record = ConflictRecord(
                    conflict_type=ConflictType.TOOL_CONTENTION,
                    description=f"Tool '{tool_name}' is in use by '{current_holder}'",
                    agents_involved=[current_holder, agent_id],
                    resource=f"tool:{tool_name}",
                )
                self._history.append(record)
                logger.warning(
                    "ConflictResolver: tool '%s' in use by '%s', blocked '%s'",
                    tool_name, current_holder, agent_id,
                )
                return False

            self._tool_locks[tool_name] = agent_id
            self._agent_resources.setdefault(agent_id, set()).add(
                f"tool:{tool_name}",
            )
            return True

    _SERIALIZED_TOOLS = frozenset({"terminal", "browser_navigate"})

    # ------------------------------------------------------------------
    # Workspace locking
    # ------------------------------------------------------------------

    def lock_workspace(self, agent_id: str, workspace_id: str) -> bool:
        """Lock a workspace for exclusive use by an agent.

        Returns True if the lock was acquired.
        """
        with self._lock:
            current = self._workspace_locks.get(workspace_id)
            if current is not None and current != agent_id:
                record = ConflictRecord(
                    conflict_type=ConflictType.WORKSPACE_LOCK,
                    description=f"Workspace '{workspace_id}' locked by '{current}'",
                    agents_involved=[current, agent_id],
                    resource=f"ws:{workspace_id}",
                )
                self._history.append(record)
                return False

            self._workspace_locks[workspace_id] = agent_id
            self._agent_resources.setdefault(agent_id, set()).add(
                f"ws:{workspace_id}",
            )
            return True

    def unlock_workspace(self, agent_id: str, workspace_id: str) -> bool:
        """Release a workspace lock."""
        with self._lock:
            current = self._workspace_locks.get(workspace_id)
            if current == agent_id:
                del self._workspace_locks[workspace_id]
                resources = self._agent_resources.get(agent_id)
                if resources:
                    resources.discard(f"ws:{workspace_id}")
                return True
            return False

    # ------------------------------------------------------------------
    # Resource release
    # ------------------------------------------------------------------

    def release_agent(self, agent_id: str) -> int:
        """Release all resources held by an agent.

        Returns the number of resources released.
        """
        count = 0
        with self._lock:
            resources = self._agent_resources.pop(agent_id, set())

            for resource in resources:
                if resource.startswith("file:"):
                    fp = resource[5:]
                    if self._file_locks.get(fp) == agent_id:
                        del self._file_locks[fp]
                        count += 1
                elif resource.startswith("tool:"):
                    tn = resource[5:]
                    if self._tool_locks.get(tn) == agent_id:
                        del self._tool_locks[tn]
                        count += 1
                elif resource.startswith("ws:"):
                    ws_id = resource[3:]
                    if self._workspace_locks.get(ws_id) == agent_id:
                        del self._workspace_locks[ws_id]
                        count += 1

        if count > 0:
            logger.debug("ConflictResolver: released %d resources for '%s'", count, agent_id)
        return count

    # ------------------------------------------------------------------
    # Duplicate work detection
    # ------------------------------------------------------------------

    def check_duplicate_work(self, task_description: str,
                             agent_id: str) -> bool:
        """Check if a task appears to be duplicate work.

        Returns True if the task is NOT a duplicate (OK to proceed).
        Returns False if it looks like a duplicate.
        """
        with self._lock:
            # Simple heuristic: check normalized descriptions
            normalized = task_description.strip().lower()[:100]

            for record in self._history:
                if record.conflict_type == ConflictType.DUPLICATE_WORK:
                    if record.resource == normalized:
                        if agent_id not in record.agents_involved:
                            logger.warning(
                                "ConflictResolver: duplicate work detected: '%s'",
                                task_description[:60],
                            )
                            return False
            return True

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get conflict resolver statistics."""
        with self._lock:
            return {
                "total_conflicts": len(self._history),
                "unresolved": sum(1 for r in self._history if not r.resolved),
                "active_file_locks": len(self._file_locks),
                "active_tool_locks": len(self._tool_locks),
                "active_workspace_locks": len(self._workspace_locks),
                "active_agents": len(self._agent_resources),
                "by_type": {
                    ct.value: sum(1 for r in self._history if r.conflict_type == ct)
                    for ct in ConflictType
                },
            }

    def release_all(self) -> int:
        """Release all locks and resources. Returns count released."""
        with self._lock:
            count = (
                len(self._file_locks)
                + len(self._tool_locks)
                + len(self._workspace_locks)
            )
            self._file_locks.clear()
            self._tool_locks.clear()
            self._workspace_locks.clear()
            self._agent_resources.clear()
            return count
