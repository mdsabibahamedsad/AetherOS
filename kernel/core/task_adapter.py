"""
Task-model consolidation adapter (Master 59 §6, migration path §47).

The canonical task model is `kernel.core.task_manager.TaskManager`
(states: pending/queued/planning/ready/running/waiting/blocked/verifying/
completed/failed/cancelled/paused/requires_approval).

Legacy DAGs (`kernel.task_graph.TaskGraph`, `aetheros_automation/tasks`,
`core/jarvis`, `agent/orchestration`) are NOT rewritten. This adapter
migrates a legacy graph into canonical tasks:

    LEGACY graph → import_graph() → CANONICAL tasks → execution

with status mapping, dependency preservation (depends_on), retry budgets,
and provenance recording the migration source.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from kernel.core.task_manager import Task, TaskManager, TaskStatus

_GRAPH_TO_TASK = {
    "pending": TaskStatus.PENDING,
    "ready": TaskStatus.READY,
    "running": TaskStatus.RUNNING,
    "completed": TaskStatus.COMPLETED,
    "failed": TaskStatus.FAILED,
    "cancelled": TaskStatus.CANCELLED,
    "blocked": TaskStatus.BLOCKED,
    "skipped": TaskStatus.CANCELLED,
}


def map_graph_status(status: Any) -> TaskStatus:
    """Map a legacy graph status onto the canonical lifecycle."""
    name = getattr(status, "value", str(status))
    return _GRAPH_TO_TASK.get(name, TaskStatus.PENDING)


def import_graph(
    graph: Any,
    task_manager: TaskManager,
    agent_id: str,
    intent_id: str,
    *,
    source: str = "legacy_task_graph",
) -> List[Task]:
    """Migrate every node of a legacy TaskGraph into canonical tasks.

    Dependencies are preserved via `depends_on` (resolved through
    `graph.get_dependencies(node_id)`). Node retry budgets, results, and
    errors carry over; provenance records the migration.
    """
    nodes = graph.get_nodes()
    node_to_task: Dict[str, Task] = {}
    # Pass 1: create tasks without edges.
    for node in nodes:
        task = task_manager.create_task(
            agent_id=agent_id,
            intent_id=intent_id,
            goal=node.name,
            description=node.description or "",
            required_capabilities=None,
        )
        task.metadata["migrated_from"] = source
        task.metadata["legacy_node_id"] = node.id
        task.metadata["legacy_action"] = getattr(node, "action", "")
        task.metadata["legacy_params"] = dict(getattr(node, "params", {}) or {})
        task.metadata["max_retries"] = getattr(node, "max_retries", 0)
        if getattr(node, "result", None) is not None:
            task.result = node.result
        if getattr(node, "error", None):
            task.error = node.error
        node_to_task[node.id] = task
    # Pass 2: wire dependencies, then statuses.
    for node in nodes:
        task = node_to_task[node.id]
        try:
            deps = graph.get_dependencies(node.id) or []
        except Exception:
            deps = []
        task.depends_on = [node_to_task[d.id].task_id for d in deps
                           if d.id in node_to_task]
        task_manager.update_task_status(task.task_id, map_graph_status(node.status))
    return [node_to_task[n.id] for n in nodes]


def export_status_map() -> Dict[str, str]:
    """Documented status correspondence (legacy → canonical)."""
    return {k: v.value for k, v in _GRAPH_TO_TASK.items()}
