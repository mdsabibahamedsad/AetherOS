from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any

from aetheros_automation.models.models import Task, Workflow

logger = logging.getLogger(__name__)


class TaskGraph:
    """Dependency graph analysis for workflows.

    Builds an adjacency structure from a ``Workflow`` and exposes
    topological ordering, cycle detection, critical-path analysis,
    parallelisation candidates, and several output formats.
    """

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    @staticmethod
    def build_graph(workflow: Workflow) -> dict[str, Any]:
        """Create a dependency graph dict from *workflow*.

        Returns ``{"nodes": [...], "edges": [...], "adjacency": {...}}``.
        """
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        adjacency: dict[str, list[str]] = {}
        task_map: dict[str, Task] = {t.id: t for t in workflow.tasks}

        for task in workflow.tasks:
            nodes.append({
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "agent": task.agent.value if task.agent else "unknown",
            })
            adjacency[task.id] = list(task.dependencies)

            for dep_id in task.dependencies:
                edges.append({"from": dep_id, "to": task.id})
                if dep_id not in task_map:
                    logger.warning(
                        "Dependency %s for task %s not found in workflow",
                        dep_id, task.id,
                    )

        graph = {
            "nodes": nodes,
            "edges": edges,
            "adjacency": adjacency,
        }
        workflow.graph = graph
        return graph

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    async def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Record that *task_id* depends on *depends_on*.

        This is a no-op placeholder for external orchestration; real
        dependency wiring is done through ``Task.dependencies``.
        """
        logger.info("add_dependency(%s -> %s) recorded", depends_on, task_id)

    async def remove_dependency(self, task_id: str, depends_on: str) -> None:
        """Remove a previously recorded dependency edge."""
        logger.info("remove_dependency(%s -> %s) recorded", depends_on, task_id)

    # ------------------------------------------------------------------
    # analysis
    # ------------------------------------------------------------------

    @staticmethod
    def get_execution_order(workflow: Workflow) -> list[str]:
        """Return task IDs in topological order (dependencies first).

        Uses Kahn's algorithm.  Tasks whose dependencies are missing or
        already completed are yielded first.
        """
        graph = TaskGraph.build_graph(workflow)
        adj = dict(graph["adjacency"])

        in_degree: dict[str, int] = {tid: 0 for tid in adj}
        for tid, deps in adj.items():
            for dep in deps:
                in_degree[tid] = in_degree.get(tid, 0) + 1

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for tid, deps in adj.items():
                if node in deps:
                    in_degree[tid] -= 1
                    if in_degree[tid] == 0:
                        queue.append(tid)

        # tasks not reachable (disconnected nodes) are appended
        all_ids = {t.id for t in workflow.tasks}
        for tid in all_ids:
            if tid not in order:
                order.append(tid)

        return order

    @staticmethod
    def find_cycles(workflow: Workflow) -> list[list[str]]:
        """Return a list of cycles (each as a list of task IDs).

        Uses DFS with back-edge detection.
        """
        graph = TaskGraph.build_graph(workflow)
        adj = graph["adjacency"]

        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbour_tid, deps in adj.items():
                if node in deps:
                    if neighbour_tid not in visited:
                        dfs(neighbour_tid)
                    elif neighbour_tid in rec_stack:
                        # back-edge found — extract the cycle
                        idx = path.index(neighbour_tid)
                        cycles.append(list(path[idx:]))

            path.pop()
            rec_stack.discard(node)

        for tid in list(adj):
            if tid not in visited:
                dfs(tid)

        return cycles

    @staticmethod
    def get_critical_path(workflow: Workflow) -> list[str]:
        """Return the longest path through the dependency graph.

        Assumes each task has ``estimated_duration`` populated.  The path
        with the greatest total estimated duration is returned.
        """
        task_map: dict[str, Task] = {t.id: t for t in workflow.tasks}
        order = TaskGraph.get_execution_order(workflow)

        dist: dict[str, float] = {t.id: 0.0 for t in workflow.tasks}
        predecessor: dict[str, str | None] = {t.id: None for t in workflow.tasks}

        for tid in order:
            task = task_map[tid]
            for dep_id in task.dependencies:
                candidate = dist[dep_id] + task_map[dep_id].estimated_duration
                if candidate > dist[tid]:
                    dist[tid] = candidate
                    predecessor[tid] = dep_id

        # find the task with the greatest distance
        end = max(dist, key=lambda k: dist[k])  # type: ignore[arg-type]

        path: list[str] = []
        cur: str | None = end
        while cur is not None:
            path.append(cur)
            cur = predecessor[cur]
        path.reverse()
        return path

    @staticmethod
    def get_parallelizable_tasks(workflow: Workflow) -> list[list[str]]:
        """Group tasks that can run in parallel.

        Each group contains tasks whose dependencies are satisfied at the
        same depth level (topological tier).
        """
        graph = TaskGraph.build_graph(workflow)
        adj = graph["adjacency"]

        in_degree: dict[str, int] = {tid: 0 for tid in adj}
        for tid, deps in adj.items():
            for dep in deps:
                in_degree[tid] = in_degree.get(tid, 0) + 1

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        temp_deg = dict(in_degree)
        levels: list[list[str]] = []

        while queue:
            current_level: list[str] = []
            for _ in range(len(queue)):
                node = queue.popleft()
                current_level.append(node)

                for tid, deps in adj.items():
                    if node in deps:
                        temp_deg[tid] -= 1
                        if temp_deg[tid] == 0:
                            queue.append(tid)

            if current_level:
                levels.append(current_level)

        return levels

    # ------------------------------------------------------------------
    # output
    # ------------------------------------------------------------------

    @staticmethod
    def visualize(workflow: Workflow) -> str:
        """Render the workflow as a Mermaid flowchart string.

        Paste the output into any Mermaid renderer (e.g. GitHub markdown).
        """
        lines: list[str] = ["```mermaid", "flowchart TD"]
        task_map: dict[str, Task] = {t.id: t for t in workflow.tasks}

        # node declarations
        for task in workflow.tasks:
            label = task.name.replace('"', "'")[:50]
            cls = _status_css(task.status.value)
            lines.append(f'    {task.id}["{label}"]:::{cls}')

        # edges
        seen_edges: set[tuple[str, str]] = set()
        for task in workflow.tasks:
            for dep in task.dependencies:
                key = (dep, task.id)
                if key not in seen_edges:
                    seen_edges.add(key)
                    lines.append(f"    {dep} --> {task.id}")

        # style definitions
        lines.append("")
        lines.append("    classDef pending fill:#f0f0f0,stroke:#999;")
        lines.append("    classDef running fill:#dff0d8,stroke:#4caf50;")
        lines.append("    classDef completed fill:#c8e6c9,stroke:#2e7d32;")
        lines.append("    classDef failed fill:#ffcdd2,stroke:#c62828;")
        lines.append("    classDef cancelled fill:#e0e0e0,stroke:#616161;")
        lines.append("    classDef paused fill:#fff9c4,stroke:#f9a825;")
        lines.append("    classDef blocked fill:#ffe0b2,stroke:#e65100;")
        lines.append("```")

        return "\n".join(lines)

    @staticmethod
    def export_graph(workflow: Workflow) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the graph."""
        graph = TaskGraph.build_graph(workflow)

        cycles = TaskGraph.find_cycles(workflow)
        order = TaskGraph.get_execution_order(workflow)
        critical = TaskGraph.get_critical_path(workflow)
        parallel = TaskGraph.get_parallelizable_tasks(workflow)

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "topological_order": order,
            "critical_path": critical,
            "parallel_groups": parallel,
            "cycles": cycles,
            "has_cycles": len(cycles) > 0,
        }


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _status_css(status: str) -> str:
    mapping = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "paused": "paused",
        "blocked": "blocked",
        "rolled_back": "completed",
    }
    return mapping.get(status, "pending")
