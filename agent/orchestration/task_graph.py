"""Task Graph Management for AetherOS Orchestration Layer.

Implements Phase 8 of Master Prompt 11: DAG-based task graphs with
topological ordering, parallel execution planning, and dependency management.

Provides:
- DAG representation of tasks with dependencies
- Topological ordering for execution planning
- Parallel execution planning with dependency resolution
- Cycle detection and prevention
- Graph operations (merge, split, prune)
- Graph visualization/export
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.types import (
    TaskSpec,
    TaskStatus,
    TaskNode,
    TaskGraph as BaseTaskGraph,
    TaskPriority,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enhanced Task Graph Types
# =============================================================================


class GraphExecutionMode(Enum):
    """How the graph should be executed."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DEPENDENT = "dependent"


@dataclass
class TaskEdge:
    """Edge in the task graph with metadata."""

    from_task_id: str
    to_task_id: str
    edge_type: str = "depends_on"  # depends_on, triggers, blocks
    condition: Optional[str] = None  # Optional condition for conditional edges
    weight: float = 1.0  # Weight for scheduling priority
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Computed execution plan from a task graph."""

    levels: List[List[str]]  # Tasks at each level can run in parallel
    total_levels: int
    estimated_sequential_time: float
    estimated_parallel_time: float
    parallelism_factor: float
    critical_path: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphMetrics:
    """Metrics about the task graph."""

    node_count: int
    edge_count: int
    max_depth: int
    avg_branching_factor: float
    critical_path_length: int
    parallelism_potential: float  # 0-1, how much can be parallelized
    cycles: List[List[str]] = field(default_factory=list)
    disconnected_components: List[List[str]] = field(default_factory=list)


class TaskGraphError(Exception):
    """Base exception for task graph operations."""
    pass


class CycleDetectedError(TaskGraphError):
    """Raised when a cycle is detected in the graph."""
    pass


class InvalidDependencyError(TaskGraphError):
    """Raised when an invalid dependency is added."""
    pass


# =============================================================================
# Task Graph Manager
# =============================================================================


class TaskGraphManager:
    """Manages task graphs with DAG operations."""

    def __init__(self):
        self._graphs: Dict[str, BaseTaskGraph] = {}
        self._lock = asyncio.Lock()

    # ── Graph Management ───────────────────────────────────────────────

    def create_graph(self, graph_id: Optional[str] = None) -> BaseTaskGraph:
        """Create a new empty task graph."""
        graph_id = graph_id or f"graph-{uuid.uuid4().hex[:12]}"
        graph = BaseTaskGraph()
        self._graphs[graph_id] = graph
        logger.info(f"Created task graph: {graph_id}")
        return graph

    def get_graph(self, graph_id: str) -> Optional[BaseTaskGraph]:
        """Get a graph by ID."""
        return self._graphs.get(graph_id)

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph."""
        if graph_id in self._graphs:
            del self._graphs[graph_id]
            logger.info(f"Deleted task graph: {graph_id}")
            return True
        return False

    def list_graphs(self) -> List[str]:
        """List all graph IDs."""
        return list(self._graphs.keys())

    # ── Node Operations ────────────────────────────────────────────────

    def add_task(self, graph_id: str, task: TaskSpec) -> bool:
        """Add a task to the graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        if task.task_id in graph.nodes:
            logger.warning(f"Task {task.task_id} already exists in graph")
            return False

        node = TaskNode(task_id=task.task_id, task=task)
        graph.add_node(node)
        return True

    def remove_task(self, graph_id: str, task_id: str) -> bool:
        """Remove a task and its edges from the graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        if task_id not in graph.nodes:
            return False

        # Remove edges involving this task
        graph.edges = [e for e in graph.edges if e[0] != task_id and e[1] != task_id]
        del graph.nodes[task_id]
        return True

    def get_task(self, graph_id: str, task_id: str) -> Optional[TaskSpec]:
        """Get a task from the graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None
        node = graph.nodes.get(task_id)
        return node.task if node else None

    # ── Edge Operations ────────────────────────────────────────────────

    def add_dependency(self, graph_id: str, from_task_id: str, to_task_id: str) -> bool:
        """Add a dependency edge: from_task must complete before to_task starts."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        if from_task_id not in graph.nodes or to_task_id not in graph.nodes:
            return False

        if from_task_id == to_task_id:
            raise InvalidDependencyError("Task cannot depend on itself")

        # Check for cycles before adding
        if self._would_create_cycle(graph, from_task_id, to_task_id):
            raise CycleDetectedError(f"Adding dependency {from_task_id} -> {to_task_id} would create a cycle")

        # Add edge
        if (from_task_id, to_task_id) not in graph.edges:
            graph.edges.append((from_task_id, to_task_id))
            logger.debug(f"Added dependency: {from_task_id} -> {to_task_id}")
            return True
        return False

    def remove_dependency(self, graph_id: str, from_task_id: str, to_task_id: str) -> bool:
        """Remove a dependency edge."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        edge = (from_task_id, to_task_id)
        if edge in graph.edges:
            graph.edges.remove(edge)
            return True
        return False

    def get_dependencies(self, graph_id: str, task_id: str) -> List[str]:
        """Get all tasks that must complete before this task."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return []
        return graph.get_dependencies(task_id)

    def get_dependents(self, graph_id: str, task_id: str) -> List[str]:
        """Get all tasks that depend on this task."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return []
        return graph.get_dependents(task_id)

    def _would_create_cycle(self, graph: BaseTaskGraph, from_id: str, to_id: str) -> bool:
        """Check if adding edge would create a cycle using DFS."""
        # If there's already a path from to_id to from_id, adding from->to creates cycle
        visited = set()
        stack = [to_id]
        while stack:
            current = stack.pop()
            if current == from_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for from_id, to_id in graph.edges:
                if from_id == current:
                    stack.append(to_id)
        return False

    # ── Graph Analysis ────────────────────────────────────────────────

    def compute_execution_plan(self, graph_id: str) -> Optional[ExecutionPlan]:
        """Compute an execution plan with parallel levels."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None

        try:
            topo_order = graph.topological_order()
        except ValueError as e:
            logger.error(f"Cannot compute execution plan: {e}")
            return None

        # Build level structure (Kahn's algorithm with level tracking)
        in_degree = {nid: 0 for nid in graph.nodes}
        for _, to_id in graph.edges:
            in_degree[to_id] += 1

        # Level assignment
        levels: List[List[str]] = []
        queue = [(nid, 0) for nid, deg in in_degree.items() if deg == 0]

        while queue:
            current_level = []
            next_queue = []

            for nid, level in queue:
                # Ensure we have enough levels
                while len(levels) <= level:
                    levels.append([])
                levels[level].append(nid)

                # Process edges
                for from_id, to_id in graph.edges:
                    if from_id == nid:
                        in_degree[to_id] -= 1
                        if in_degree[to_id] == 0:
                            next_queue.append((to_id, level + 1))

            queue = next_queue

        # Calculate metrics
        total_levels = len(levels)
        sequential_time = sum(
            self._estimate_level_time(graph, level)
            for level in levels
        )
        parallel_time = sum(
            max((self._estimate_task_time(graph.nodes[tid].task) for tid in level), default=0)
            for level in levels
        )

        # Find critical path
        critical_path = self._find_critical_path(graph)

        return ExecutionPlan(
            levels=levels,
            total_levels=total_levels,
            estimated_sequential_time=sequential_time,
            estimated_parallel_time=parallel_time,
            parallelism_factor=sequential_time / parallel_time if parallel_time > 0 else 1.0,
            critical_path=critical_path,
            metadata={
                "total_tasks": len(graph.nodes),
                "levels": len(levels),
            },
        )

    def _estimate_task_time(self, task: Optional[TaskSpec]) -> float:
        """Estimate execution time for a task."""
        if not task:
            return 60.0
        return task.budget.max_time_seconds if task.budget else 60.0

    def _estimate_level_time(self, graph: BaseTaskGraph, level: List[str]) -> float:
        """Estimate sequential time for a level (sum of task times)."""
        return sum(
            self._estimate_task_time(graph.nodes[tid].task)
            for tid in level
        )

    def _find_critical_path(self, graph: BaseTaskGraph) -> List[str]:
        """Find the critical path (longest path) in the DAG."""
        # Dynamic programming for longest path in DAG
        topo_order = graph.topological_order()
        dist = {nid: 0.0 for nid in graph.nodes}
        prev = {nid: None for nid in graph.nodes}

        for nid in topo_order:
            task = graph.nodes[nid].task
            task_time = self._estimate_task_time(task)
            for from_id, to_id in graph.edges:
                if from_id == nid:
                    new_dist = dist[nid] + self._estimate_task_time(graph.nodes[to_id].task)
                    if new_dist > dist[to_id]:
                        dist[to_id] = new_dist
                        prev[to_id] = nid

        # Find end of critical path
        end_node = max(dist, key=dist.get)
        path = []
        current = end_node
        while current:
            path.append(current)
            current = prev[current]
        path.reverse()
        return path

    def get_graph_metrics(self, graph_id: str) -> Optional[GraphMetrics]:
        """Compute metrics for a graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None

        # Detect cycles
        cycles = self._detect_cycles(graph)

        # Find disconnected components
        components = self._find_components(graph)

        # Calculate metrics
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)

        # Max depth
        max_depth = 0
        if graph.nodes:
            topo = graph.topological_order()
            depth = {nid: 0 for nid in graph.nodes}
            for nid in graph.topological_order():
                for from_id, to_id in graph.edges:
                    if from_id == nid:
                        depth[to_id] = max(depth[to_id], depth[nid] + 1)
            max_depth = max(depth.values())

        # Average branching factor
        out_degrees = defaultdict(int)
        for from_id, _ in graph.edges:
            out_degrees[from_id] += 1
        avg_branching = sum(out_degrees.values()) / max(1, len(out_degrees))

        # Critical path
        critical_path = self._find_critical_path(self._graphs[graph_id]) if graph_id in self._graphs else []
        parallelism = 1.0 - (len(critical_path) / max(1, len(graph.nodes)))

        return GraphMetrics(
            node_count=node_count,
            edge_count=edge_count,
            max_depth=max_depth,
            avg_branching_factor=avg_branching,
            critical_path_length=len(critical_path),
            parallelism_potential=parallelism,
            cycles=cycles,
            disconnected_components=components,
        )

    def _detect_cycles(self, graph: BaseTaskGraph) -> List[List[str]]:
        """Detect all cycles in the graph using Johnson's algorithm."""
        # Simplified: use DFS to find one cycle
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for from_id, to_id in graph.edges:
                if from_id == node:
                    if to_id not in visited:
                        if dfs(to_id):
                            return True
                    elif to_id in rec_stack:
                        # Found cycle
                        idx = path.index(to_id)
                        cycles.append(path[idx:])
                        return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph.nodes:
            if node not in visited:
                dfs(node)

        return cycles

    def _find_components(self, graph: BaseTaskGraph) -> List[List[str]]:
        """Find weakly connected components."""
        visited = set()
        components = []

        def dfs(node, component):
            visited.add(node)
            component.append(node)
            for from_id, to_id in graph.edges:
                if from_id == node and to_id not in visited:
                    dfs(to_id, component)
                if to_id == node and from_id not in visited:
                    dfs(from_id, component)

        for node in graph.nodes:
            if node not in visited:
                component = []
                dfs(node, component)
                if len(component) > 1:
                    components.append(component)
        return components

    # ── Graph Operations ────────────────────────────────────────────

    def merge_graphs(self, target_id: str, source_id: str, prefix: str = "") -> bool:
        """Merge source graph into target graph with optional prefix."""
        target = self._graphs.get(target_id)
        source = self._graphs.get(source_id)
        if not target or not source:
            return False

        # Add nodes with prefix
        for task_id, node in source.nodes.items():
            new_id = f"{prefix}{task_id}" if prefix else task_id
            if new_id in target.nodes:
                new_id = f"{new_id}-{uuid.uuid4().hex[:6]}"
            node.task.task_id = new_id
            target.nodes[new_id] = node

        # Add edges with prefix
        for from_id, to_id in source.edges:
            new_from = f"{prefix}{from_id}" if prefix else from_id
            new_to = f"{prefix}{to_id}" if prefix else to_id
            if (new_from, new_to) not in target.edges:
                target.edges.append((new_from, new_to))

        logger.info(f"Merged graph {source_id} into {target_id}")
        return True

    def split_graph(self, graph_id: str, task_ids: List[str], new_id: Optional[str] = None) -> Optional[str]:
        """Split a subgraph out into a new graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None

        new_id = new_id or f"graph-{uuid.uuid4().hex[:12]}"
        new_graph = BaseTaskGraph()

        # Copy specified nodes
        for task_id in task_ids:
            if task_id in graph.nodes:
                node = graph.nodes[task_id]
                new_graph.nodes[task_id] = node

        # Copy edges between selected nodes
        task_set = set(task_ids)
        for from_id, to_id in graph.edges:
            if from_id in task_set and to_id in task_set:
                new_graph.edges.append((from_id, to_id))

        self._graphs[new_id] = new_graph

        # Remove from original
        for task_id in task_ids:
            if task_id in graph.nodes:
                del graph.nodes[task_id]
        graph.edges = [e for e in graph.edges if e[0] not in task_set and e[1] not in task_set]

        logger.info(f"Split graph {graph_id} -> {new_id} with {len(task_ids)} tasks")
        return new_id

    def prune_completed(self, graph_id: str) -> int:
        """Remove completed tasks from graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return 0

        completed = [tid for tid, node in graph.nodes.items() if node.status == TaskStatus.COMPLETED]
        for tid in completed:
            self.remove_task(graph_id, tid)
        return len(completed)

    def get_ready_tasks(self, graph_id: str) -> List[str]:
        """Get tasks that have all dependencies satisfied and are ready to run."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return []

        ready = []
        for task_id, node in graph.nodes.items():
            if node.status not in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.READY):
                continue

            deps = graph.get_dependencies(task_id)
            if all(graph.nodes[dep].status == TaskStatus.COMPLETED for dep in deps):
                ready.append(task_id)

        return ready

    # ── Graph Export/Import ──────────────────────────────────────────

    def export_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Export graph to serializable format."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None

        return {
            "graph_id": graph_id,
            "nodes": {
                tid: {
                    "task": node.task.to_dict() if hasattr(node.task, 'to_dict') else str(node.task),
                    "status": node.status.value,
                    "assigned_agent": node.assigned_agent,
                    "result": str(node.result) if node.result else "",
                    "error": node.error,
                    "started_at": node.started_at,
                    "completed_at": node.completed_at,
                }
                for tid, node in graph.nodes.items()
            },
            "edges": [{"from": f, "to": t} for f, t in graph.edges],
        }

    def import_graph(self, data: Dict[str, Any], graph_id: Optional[str] = None) -> Optional[str]:
        """Import graph from serialized format."""
        graph_id = graph_id or f"graph-{uuid.uuid4().hex[:12]}"
        graph = BaseTaskGraph()

        # Restore nodes
        for tid, node_data in data.get("nodes", {}).items():
            # Reconstruct TaskSpec from dict (simplified)
            task = TaskSpec(
                task_id=tid,
                goal=node_data.get("task", {}).get("goal", "") if isinstance(node_data.get("task"), dict) else "",
                status=TaskStatus(node_data.get("status", "pending")),
            )
            node = TaskNode(task_id=tid, task=task)
            node.status = TaskStatus(node_data.get("status", "pending"))
            node.assigned_agent = node_data.get("assigned_agent", "")
            node.result = node_data.get("result", "")
            node.error = node_data.get("error", "")
            graph.nodes[tid] = node

        # Restore edges
        for edge in data.get("edges", []):
            graph.edges.append((edge["from"], edge["to"]))

        final_id = graph_id or f"graph-{uuid.uuid4().hex[:12]}"
        self._graphs[final_id] = graph
        return final_id


# =============================================================================
# Execution Scheduler
# =============================================================================


class ExecutionScheduler:
    """Schedules and executes tasks from a task graph."""

    def __init__(
        self,
        graph_manager: TaskGraphManager,
        lifecycle_manager: "TaskLifecycleManager",
        agent_registry: "AgentRegistry",
        max_parallel: int = 5,
    ):
        self._graph_manager = graph_manager
        self._lifecycle = lifecycle_manager
        self._registry = agent_registry
        self._max_parallel = max_parallel
        self._running = False
        self._current_graph: Optional[str] = None
        self._execution_task: Optional[asyncio.Task] = None

    async def execute_graph(
        self,
        graph_id: str,
        mode: GraphExecutionMode = GraphExecutionMode.PARALLEL,
    ) -> Dict[str, Any]:
        """Execute all tasks in a graph."""
        self._running = True
        self._current_graph = graph_id
        graph = self._graph_manager.get_graph(graph_id)
        if not graph:
            return {"success": False, "error": "Graph not found"}

        # Compute execution plan
        plan = self._graph_manager.compute_execution_plan(graph_id)
        if not plan:
            return {"success": False, "error": "Failed to compute execution plan"}

        results = {}
        start_time = time.time()

        try:
            if mode == GraphExecutionMode.SEQUENTIAL:
                await self._execute_sequential(graph, plan)
            elif mode == GraphExecutionMode.PARALLEL:
                await self._execute_parallel(graph, plan)
            elif mode == GraphExecutionMode.DEPENDENT:
                await self._execute_dependent(graph)
            else:
                await self._execute_parallel(graph, plan)

            return {
                "success": True,
                "graph_id": graph_id,
                "duration": time.time() - start_time,
                "completed_tasks": len([n for n in graph.nodes.values() if n.status == TaskStatus.COMPLETED]),
                "failed_tasks": len([n for n in graph.nodes.values() if n.status == TaskStatus.FAILED]),
            }
        finally:
            self._running = False
            self._current_graph = None

    async def _execute_sequential(self, graph: BaseTaskGraph, plan: ExecutionPlan):
        """Execute tasks sequentially following topological order."""
        for level in plan.levels:
            for task_id in level:
                await self._execute_task(task_id)

    async def _execute_parallel(self, graph: BaseTaskGraph, plan: ExecutionPlan):
        """Execute tasks in parallel by level."""
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def execute_with_semaphore(task_id: str):
            async with semaphore:
                await self._execute_task(task_id)

        for level in plan.levels:
            if not self._running:
                break
            tasks = [execute_with_semaphore(tid) for tid in level]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_dependent(self, graph: BaseTaskGraph):
        """Execute tasks as they become ready (dependency-driven)."""
        while self._running:
            ready = self._graph_manager.get_ready_tasks(self._current_graph)
            if not ready:
                # Check if all done
                pending = [n for n in graph.nodes.values() if n.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.READY)]
                if not pending:
                    break
                await asyncio.sleep(1)  # Wait for dependencies
                continue

            # Execute ready tasks in parallel
            semaphore = asyncio.Semaphore(self._max_parallel)
            tasks = [self._execute_task_with_semaphore(tid, semaphore) for tid in ready]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_task_with_semaphore(self, task_id: str, semaphore: asyncio.Semaphore):
        async with semaphore:
            await self._execute_task(task_id)

    async def _execute_task(self, task_id: str):
        """Execute a single task using the lifecycle manager."""
        from agent.orchestration.task_lifecycle import get_lifecycle_manager

        lifecycle = get_lifecycle_manager()
        task = self._graph_manager.get_task(self._current_graph, task_id)
        if not task:
            return

        # Find suitable agent
        from agent.orchestration.agent_registry import get_agent_registry
        registry = get_agent_registry()
        agent = await registry.route_task(task)
        if not agent:
            logger.error(f"No agent available for task {task_id}")
            await lifecycle.transition(task_id, TaskStatus.FAILED, "No suitable agent")
            return

        # Assign agent
        lifecycle.assign_agent(task_id, agent.identity.agent_id)

        try:
            await lifecycle.start_task(task_id)
            result = await agent.execute_task(task)
            await lifecycle.complete_task(task_id, result=result)
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            await lifecycle.fail_task(task_id, str(e))


# =============================================================================
# Graph Visualization
# =============================================================================


def export_mermaid(graph: BaseTaskGraph) -> str:
    """Export graph as Mermaid diagram."""
    lines = ["graph TD"]
    for task_id, node in graph.nodes.items():
        label = node.task.goal[:30] if node.task.goal else task_id
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.QUEUED: "📋",
            TaskStatus.PLANNING: "📝",
            TaskStatus.READY: "✅",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.WAITING: "⏳",
            TaskStatus.BLOCKED: "🚫",
            TaskStatus.VERIFYING: "🔍",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
            TaskStatus.PAUSED: "⏸️",
            TaskStatus.REQUIRES_APPROVAL: "⚠️",
        }.get(node.status, "❓")

        lines.append(f'    {task_id}["{status_emoji} {label}"]')

    for from_id, to_id in graph.edges:
        lines.append(f"    {from_id} --> {to_id}")

    return "\n".join(lines)


def export_graphviz(graph: BaseTaskGraph) -> str:
    """Export graph as Graphviz DOT format."""
    lines = ['digraph G {', '  rankdir=LR;', '  node [shape=box, style=filled];']

    for task_id, node in graph.nodes.items():
        label = node.task.goal[:30] if node.task.goal else task_id
        color = {
            TaskStatus.PENDING: "lightgray",
            TaskStatus.QUEUED: "lightblue",
            TaskStatus.PLANNING: "lightyellow",
            TaskStatus.READY: "lightgreen",
            TaskStatus.RUNNING: "yellow",
            TaskStatus.WAITING: "orange",
            TaskStatus.BLOCKED: "red",
            TaskStatus.VERIFYING: "lightblue",
            TaskStatus.COMPLETED: "green",
            TaskStatus.FAILED: "red",
            TaskStatus.CANCELLED: "gray",
            TaskStatus.PAUSED: "purple",
            TaskStatus.REQUIRES_APPROVAL: "pink",
        }.get(node.status, "white")

        lines.append(f'  "{task_id}" [label="{task_id}\\n{label}", fillcolor={color}];')

    for from_id, to_id in graph.edges:
        lines.append(f'  "{from_id}" -> "{to_id}";')

    lines.append("}")
    return "\n".join(lines)


# =============================================================================
# Global Graph Manager
# =============================================================================

_graph_manager: Optional[TaskGraphManager] = None


def get_graph_manager() -> TaskGraphManager:
    """Get the global task graph manager."""
    global _graph_manager
    if _graph_manager is None:
        _graph_manager = TaskGraphManager()
    return _graph_manager


__all__ = [
    "TaskGraphManager",
    "ExecutionScheduler",
    "ExecutionPlan",
    "GraphExecutionMode",
    "TaskGraphError",
    "CycleDetectedError",
    "InvalidDependencyError",
    "GraphMetrics",
    "ExecutionPlan",
    "TaskEdge",
    "TaskNode",
    "export_mermaid",
    "export_graphviz",
    "get_graph_manager",
]