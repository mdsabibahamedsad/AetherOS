"""
Task Graph — represents every goal as a DAG (Directed Acyclic Graph).

Supports:
  - Dependencies between tasks
  - Parallel branches
  - Rollback metadata
  - Execution state tracking
  - Retry state
  - Progress reporting

Each node in the graph represents a unit of work. Edges represent
dependencies. The graph can be serialized for persistence.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class GraphStatus(enum.Enum):
    """Status of a task graph or individual node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class TaskDependency:
    """A dependency between two tasks.

    Attributes:
        source_id: The task that must complete first
        target_id: The task that depends on source
        required: If True, target cannot run unless source succeeded
    """
    source_id: str
    target_id: str
    required: bool = True


@dataclass
class TaskNode:
    """A single node/task in the graph.

    Attributes:
        id: Unique node ID
        name: Human-readable name
        description: Detailed description
        action: Action type (agent_run, tool_call, sub_graph, wait, notify)
        params: Action parameters
        status: Current status
        retry_count: Current retry attempt
        max_retries: Maximum retries allowed
        result: Execution result
        error: Error message (if failed)
        metadata: Additional metadata
        created_at: Creation timestamp
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    action: str = "agent_run"
    params: Dict[str, Any] = field(default_factory=dict)
    status: GraphStatus = GraphStatus.PENDING
    retry_count: int = 0
    max_retries: int = 0
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class TaskGraph:
    """Directed Acyclic Graph for representing tasks and their dependencies.

    Usage:
        g = TaskGraph(name="deploy-app")

        build = g.add_node("build", "Build the application")
        test = g.add_node("test", "Run tests", dependencies=["build"])
        deploy = g.add_node("deploy", "Deploy to production", dependencies=["test"])

        ready = g.get_ready_nodes()  # [build] — no deps
        g.update_status("build", GraphStatus.COMPLETED)
        ready = g.get_ready_nodes()  # [test] — dep satisfied
    """

    def __init__(self, name: str = "", graph_id: str = None,
                 event_bus: Optional[EventBus] = None):
        self.id = graph_id or uuid.uuid4().hex[:12]
        self.name = name or f"graph-{self.id[:8]}"
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._nodes: Dict[str, TaskNode] = {}
        # adjacency: target -> list of source dependencies
        self._dependencies: Dict[str, List[TaskDependency]] = {}
        # reverse: source -> list of dependents
        self._dependents: Dict[str, List[str]] = {}
        self.status: GraphStatus = GraphStatus.PENDING
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(self, name: str, description: str = "",
                 action: str = "agent_run",
                 params: Dict[str, Any] = None,
                 dependencies: List[str] = None,
                 max_retries: int = 0,
                 node_id: str = None) -> TaskNode:
        """Add a task node to the graph."""
        node = TaskNode(
            id=node_id or uuid.uuid4().hex[:12],
            name=name,
            description=description,
            action=action,
            params=params or {},
            max_retries=max_retries,
        )

        with self._lock:
            self._nodes[node.id] = node
            if dependencies:
                deps = []
                for dep_id in dependencies:
                    if dep_id in self._nodes:
                        deps.append(TaskDependency(source_id=dep_id, target_id=node.id))
                        self._dependents.setdefault(dep_id, []).append(node.id)
                if deps:
                    self._dependencies[node.id] = deps

        # Check if newly added node is ready (no unmet deps)
        self._update_ready_status(node.id)

        logger.debug("TaskGraph: added node '%s' (%s)", name, node.id)
        return node

    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """Get a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its dependencies."""
        with self._lock:
            node = self._nodes.pop(node_id, None)
            if node is None:
                return False
            # Remove as dependency of others
            self._dependencies.pop(node_id, None)
            for deps in self._dependencies.values():
                deps[:] = [d for d in deps if d.source_id != node_id]
            # Remove from dependents
            self._dependents.pop(node_id, None)
            for deps in self._dependents.values():
                if node_id in deps:
                    deps.remove(node_id)
        return True

    def get_nodes(self, status: GraphStatus = None) -> List[TaskNode]:
        """Get all nodes, optionally filtered by status."""
        with self._lock:
            nodes = list(self._nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        nodes.sort(key=lambda n: n.created_at)
        return nodes

    # ------------------------------------------------------------------
    # Dependency management
    # ------------------------------------------------------------------

    def get_dependencies(self, node_id: str) -> List[TaskNode]:
        """Get the dependency nodes for a given node."""
        with self._lock:
            dep_refs = self._dependencies.get(node_id, [])
            return [
                self._nodes[d.source_id]
                for d in dep_refs
                if d.source_id in self._nodes
            ]

    def get_dependents(self, node_id: str) -> List[TaskNode]:
        """Get the nodes that depend on a given node."""
        with self._lock:
            dep_ids = self._dependents.get(node_id, [])
            return [
                self._nodes[nid]
                for nid in dep_ids
                if nid in self._nodes
            ]

    def get_ready_nodes(self) -> List[TaskNode]:
        """Get nodes whose dependencies are all satisfied (ready to execute)."""
        ready = []
        with self._lock:
            for node_id, node in self._nodes.items():
                if node.status not in (GraphStatus.PENDING, GraphStatus.READY):
                    continue
                deps = self._dependencies.get(node_id, [])
                all_satisfied = all(
                    self._nodes.get(d.source_id)
                    and self._nodes[d.source_id].status == GraphStatus.COMPLETED
                    for d in deps
                )
                if all_satisfied:
                    ready.append(node)
        return ready

    def get_blocked_nodes(self) -> List[TaskNode]:
        """Get nodes that are blocked by failed dependencies."""
        blocked = []
        with self._lock:
            for node_id, node in self._nodes.items():
                if node.status == GraphStatus.BLOCKED:
                    blocked.append(node)
                elif node.status == GraphStatus.PENDING:
                    deps = self._dependencies.get(node_id, [])
                    for d in deps:
                        dep_node = self._nodes.get(d.source_id)
                        if dep_node and dep_node.status == GraphStatus.FAILED:
                            if d.required:
                                blocked.append(node)
                                break
        return blocked

    def _update_ready_status(self, node_id: str) -> None:
        """Update a node's status to READY if all deps are satisfied."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None or node.status != GraphStatus.PENDING:
                return
            deps = self._dependencies.get(node_id, [])
            if not deps:
                node.status = GraphStatus.READY

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    def update_status(self, node_id: str,
                      status: GraphStatus,
                      result: Any = None,
                      error: str = None) -> bool:
        """Update the status of a node.

        Automatically cascades: completed nodes may make dependents READY.
        Failed nodes may make dependents BLOCKED.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False

            node.status = status
            now = time.time()

            if status == GraphStatus.RUNNING:
                node.started_at = now
            elif status in (GraphStatus.COMPLETED, GraphStatus.FAILED,
                          GraphStatus.CANCELLED, GraphStatus.SKIPPED):
                node.completed_at = now
                if result is not None:
                    node.result = result
                if error is not None:
                    node.error = error

        # Cascade effects
        if status == GraphStatus.COMPLETED:
            for dep_id in self._dependents.get(node_id, []):
                self._update_ready_status(dep_id)
        elif status == GraphStatus.FAILED:
            for dep_id in self._dependents.get(node_id, []):
                with self._lock:
                    dep_node = self._nodes.get(dep_id)
                    if dep_node and dep_node.status in (GraphStatus.PENDING, GraphStatus.READY):
                        # Check if any required dependency is the failed one
                        dep_refs = self._dependencies.get(dep_id, [])
                        for d in dep_refs:
                            if d.source_id == node_id and d.required:
                                dep_node.status = GraphStatus.BLOCKED
                                break

        if self._event_bus:
            self._event_bus.emit_async(EventTopics.TASK_PROGRESS, {
                "graph_id": self.id,
                "node_id": node_id,
                "status": status.value,
                "progress": self.progress_summary(),
            })

        self._check_completion()
        return True

    def retry_node(self, node_id: str) -> bool:
        """Reset a failed node for retry."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            if node.retry_count >= node.max_retries:
                return False
            node.retry_count += 1
            node.status = GraphStatus.PENDING
            node.error = None
            node.result = None
            node.started_at = None
            node.completed_at = None

        self._update_ready_status(node_id)
        logger.info("TaskGraph: retrying node '%s' (attempt %d/%d)",
                     node.name, node.retry_count, node.max_retries)
        return True

    def cancel(self) -> None:
        """Cancel the entire graph."""
        with self._lock:
            for node in self._nodes.values():
                if node.status in (GraphStatus.PENDING, GraphStatus.READY,
                                 GraphStatus.RUNNING):
                    node.status = GraphStatus.CANCELLED
            self.status = GraphStatus.CANCELLED
            self.completed_at = time.time()
        logger.info("TaskGraph: cancelled '%s'", self.name)

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------

    def progress_summary(self) -> Dict[str, Any]:
        """Return a progress summary for the graph."""
        with self._lock:
            total = len(self._nodes)
            counts = {}
            for node in self._nodes.values():
                counts[node.status.value] = counts.get(node.status.value, 0) + 1

        completed = counts.get(GraphStatus.COMPLETED.value, 0)
        failed = counts.get(GraphStatus.FAILED.value, 0)
        return {
            "graph_id": self.id,
            "name": self.name,
            "status": self.status.value,
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": counts.get(GraphStatus.RUNNING.value, 0),
            "pending": counts.get(GraphStatus.PENDING.value, 0) + counts.get(GraphStatus.READY.value, 0),
            "progress_pct": (completed / total * 100) if total > 0 else 0,
        }

    def _check_completion(self) -> None:
        """Check if all nodes are done and update graph status."""
        with self._lock:
            if self.status in (GraphStatus.CANCELLED, GraphStatus.COMPLETED,
                             GraphStatus.FAILED):
                return
            has_pending = any(
                n.status not in (GraphStatus.COMPLETED, GraphStatus.FAILED,
                               GraphStatus.CANCELLED, GraphStatus.SKIPPED)
                for n in self._nodes.values()
            )
            has_failure = any(
                n.status == GraphStatus.FAILED for n in self._nodes.values()
            )
            if not has_pending:
                self.status = GraphStatus.FAILED if has_failure else GraphStatus.COMPLETED
                self.completed_at = time.time()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph to a dict."""
        with self._lock:
            return {
                "id": self.id,
                "name": self.name,
                "status": self.status.value,
                "created_at": self.created_at,
                "completed_at": self.completed_at,
                "nodes": [
                    {
                        "id": n.id,
                        "name": n.name,
                        "description": n.description,
                        "action": n.action,
                        "status": n.status.value,
                        "retry_count": n.retry_count,
                        "max_retries": n.max_retries,
                        "result": str(n.result)[:200] if n.result else None,
                        "error": n.error,
                    }
                    for n in self._nodes.values()
                ],
                "edges": [
                    {"from": d.source_id, "to": d.target_id, "required": d.required}
                    for target, deps in self._dependencies.items()
                    for d in deps
                ],
                "progress": self.progress_summary(),
            }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the graph to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
