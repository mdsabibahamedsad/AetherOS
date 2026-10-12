from __future__ import annotations

import logging
from collections import deque
from typing import Any, Optional

from aetheros_automation.orchestrator.models import (
    Plan, OrchestrationTask, ExecutionGraph, GraphNode, GraphEdge,
    NodeType, TaskType, TaskStatus,
)

logger = logging.getLogger(__name__)


class ExecutionGraphEngine:
    def build_from_plan(self, plan: Plan) -> ExecutionGraph:
        graph = ExecutionGraph()
        if not plan.tasks:
            return graph
        task_map = {t.id: t for t in plan.tasks}
        for task in plan.tasks:
            node = GraphNode(
                id=task.id,
                task_id=task.id,
                node_type=self._task_to_node_type(task),
                label=task.name or task.description[:50],
                status=task.status,
                metadata={
                    "role": task.agent_role.value if hasattr(task.agent_role, 'value') else str(task.agent_role),
                    "type": task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type),
                    "risk": task.risk_level.value if hasattr(task.risk_level, 'value') else str(task.risk_level),
                    "estimated_duration": task.estimated_duration,
                },
            )
            graph.nodes.append(node)
        edges_added: set[tuple[str, str]] = set()
        for task in plan.tasks:
            for dep_id in task.dependencies:
                if dep_id in task_map and (dep_id, task.id) not in edges_added:
                    edge = GraphEdge(
                        source=dep_id,
                        target=task.id,
                        edge_type="dependency",
                    )
                    graph.edges.append(edge)
                    edges_added.add((dep_id, task.id))
        graph.entry_nodes = [
            t.id for t in plan.tasks if not t.dependencies
        ]
        graph.levels = self._compute_levels(graph)
        return graph

    def _task_to_node_type(self, task: OrchestrationTask) -> NodeType:
        mapping = {
            TaskType.PARALLEL: NodeType.PARALLEL,
            TaskType.CONDITIONAL: NodeType.CONDITION,
            TaskType.HUMAN_APPROVAL: NodeType.APPROVAL,
            TaskType.RETRY: NodeType.RETRY,
            TaskType.FALLBACK: NodeType.FALLBACK,
            TaskType.SUB_AGENT: NodeType.AGENT,
            TaskType.AGENT_TASK: NodeType.AGENT,
            TaskType.MERGE: NodeType.MERGE,
        }
        return mapping.get(task.task_type, NodeType.TASK)

    def _compute_levels(self, graph: ExecutionGraph) -> list[list[str]]:
        if not graph.nodes:
            return []
        adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
        for edge in graph.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}
        for edge in graph.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1
        queue: deque[str] = deque(
            nid for nid, deg in in_degree.items() if deg == 0
        )
        levels: list[list[str]] = []
        while queue:
            level: list[str] = []
            for _ in range(len(queue)):
                nid = queue.popleft()
                level.append(nid)
                for neighbor in adj.get(nid, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            if level:
                levels.append(level)
        return levels

    def get_execution_order(self, graph: ExecutionGraph) -> list[str]:
        order: list[str] = []
        for level in graph.levels:
            order.extend(level)
        return order

    def get_parallel_groups(self, graph: ExecutionGraph) -> list[list[str]]:
        return graph.levels

    def get_critical_path(self, graph: ExecutionGraph) -> list[str]:
        if not graph.nodes:
            return []
        node_map = {n.id: n for n in graph.nodes}
        adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
        for edge in graph.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        dist: dict[str, float] = {n.id: 0.0 for n in graph.nodes}
        pred: dict[str, Optional[str]] = {n.id: None for n in graph.nodes}
        duration_map: dict[str, float] = {}
        for node in graph.nodes:
            meta = node.metadata or {}
            duration_map[node.id] = meta.get("estimated_duration", 60.0)
        order = self.get_execution_order(graph)
        for nid in order:
            if nid in node_map:
                for neighbor in adj.get(nid, []):
                    candidate = dist[nid] + duration_map.get(nid, 0)
                    if candidate > dist.get(neighbor, 0):
                        dist[neighbor] = candidate
                        pred[neighbor] = nid
        if not dist:
            return []
        end_id = max(dist, key=lambda k: dist[k])
        path: list[str] = []
        cur: Optional[str] = end_id
        while cur is not None:
            path.append(cur)
            cur = pred.get(cur)
        path.reverse()
        return path

    def find_cycles(self, graph: ExecutionGraph) -> list[list[str]]:
        adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
        for edge in graph.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n.id: WHITE for n in graph.nodes}
        cycles: list[list[str]] = []
        path_stack: list[str] = []

        def dfs(nid: str) -> None:
            color[nid] = GRAY
            path_stack.append(nid)
            for neighbor in adj.get(nid, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    idx = path_stack.index(neighbor)
                    cycles.append(list(path_stack[idx:]))
                elif color[neighbor] == WHITE:
                    dfs(neighbor)
            path_stack.pop()
            color[nid] = BLACK

        for nid in list(adj.keys()):
            if color.get(nid) == WHITE:
                dfs(nid)
        return cycles

    def get_dependents(self, graph: ExecutionGraph, task_id: str) -> list[str]:
        dependents: list[str] = []
        for edge in graph.edges:
            if edge.source == task_id:
                dependents.append(edge.target)
                dependents.extend(self.get_dependents(graph, edge.target))
        return list(set(dependents))

    def visualize(self, graph: ExecutionGraph) -> str:
        lines: list[str] = ["```mermaid", "flowchart TD"]
        node_color_map = {
            TaskStatus.PENDING: "fill:#f0f0f0,stroke:#999",
            TaskStatus.RUNNING: "fill:#dff0d8,stroke:#4caf50",
            TaskStatus.COMPLETED: "fill:#c8e6c9,stroke:#2e7d32",
            TaskStatus.FAILED: "fill:#ffcdd2,stroke:#c62828",
            TaskStatus.CANCELLED: "fill:#e0e0e0,stroke:#616161",
            TaskStatus.PAUSED: "fill:#fff9c4,stroke:#f9a825",
            TaskStatus.BLOCKED: "fill:#ffe0b2,stroke:#e65100",
            TaskStatus.WAITING_APPROVAL: "fill:#bbdefb,stroke:#1565c0",
        }
        for node in graph.nodes:
            label = node.label.replace('"', "'")[:50]
            css = node_color_map.get(node.status, "fill:#f0f0f0,stroke:#999")
            node_id = node.id.replace("-", "_")
            lines.append(f'    {node_id}["{label}"]:::{node_id}_style')
            lines.append(f"    classDef {node_id}_style {css}")
        seen_edges: set[tuple[str, str]] = set()
        for edge in graph.edges:
            src = edge.source.replace("-", "_")
            tgt = edge.target.replace("-", "_")
            key = (src, tgt)
            if key not in seen_edges:
                seen_edges.add(key)
                if edge.condition:
                    lines.append(f"    {src} -->|{edge.condition}| {tgt}")
                else:
                    lines.append(f"    {src} --> {tgt}")
        lines.append("```")
        return "\n".join(lines)
