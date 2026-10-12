from __future__ import annotations

import time
import uuid
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    DEPENDENT = "dependent"


@dataclass
class TaskNode:
    id: str
    label: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5
    estimated_duration: float = 10.0
    progress: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    metadata: dict = field(default_factory=dict)
    subtasks: list[TaskNode] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskGraph:
    id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    nodes: list[TaskNode] = field(default_factory=list)
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: int = 5
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


class TaskPlanner:
    def __init__(self):
        self._graphs: dict[str, TaskGraph] = {}
        self._lock = threading.Lock()

    def create_graph(self, goal: str, priority: int = 5) -> TaskGraph:
        graph = TaskGraph(
            id=f"graph-{uuid.uuid4().hex[:12]}",
            goal=goal,
            priority=priority,
        )
        with self._lock:
            self._graphs[graph.id] = graph
        return graph

    def add_node(self, graph_id: str, label: str, description: str = "",
                 dependencies: Optional[list[str]] = None,
                 priority: int = 5, estimated_duration: float = 10.0,
                 execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL) -> Optional[TaskNode]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return None
            node = TaskNode(
                id=f"node-{uuid.uuid4().hex[:8]}",
                label=label,
                description=description,
                priority=priority,
                estimated_duration=estimated_duration,
                dependencies=dependencies or [],
                execution_mode=execution_mode,
            )
            graph.nodes.append(node)
            return node

    def start_graph(self, graph_id: str) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return False
            graph.status = TaskStatus.RUNNING
            graph.started_at = time.time()
            for node in graph.nodes:
                if not node.dependencies:
                    node.status = TaskStatus.READY
            return True

    def get_ready_nodes(self, graph_id: str) -> list[TaskNode]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return []
            ready = []
            for node in graph.nodes:
                if node.status != TaskStatus.PENDING:
                    continue
                deps_satisfied = all(
                    any(n.id == dep and n.status == TaskStatus.COMPLETED for n in graph.nodes)
                    for dep in node.dependencies
                )
                if deps_satisfied:
                    node.status = TaskStatus.READY
                    ready.append(node)
            return ready

    def update_node_status(self, graph_id: str, node_id: str,
                           status: TaskStatus, result: Optional[Any] = None) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return False
            for node in graph.nodes:
                if node.id == node_id:
                    node.status = status
                    node.result = result
                    if status == TaskStatus.RUNNING and node.started_at is None:
                        node.started_at = time.time()
                    elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        node.completed_at = time.time()
                    return True
            return False

    def update_node_progress(self, graph_id: str, node_id: str, progress: float) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return False
            for node in graph.nodes:
                if node.id == node_id:
                    node.progress = min(progress, 100.0)
                    return True
            return False

    def get_graph_status(self, graph_id: str) -> dict:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return {"total": 0, "completed": 0, "failed": 0, "running": 0, "pending": 0}
            total = len(graph.nodes)
            completed = sum(1 for n in graph.nodes if n.status == TaskStatus.COMPLETED)
            failed = sum(1 for n in graph.nodes if n.status == TaskStatus.FAILED)
            running = sum(1 for n in graph.nodes if n.status == TaskStatus.RUNNING)
            pending = sum(1 for n in graph.nodes if n.status in (TaskStatus.PENDING, TaskStatus.READY))
            return {"total": total, "completed": completed, "failed": failed,
                    "running": running, "pending": pending}

    def get_graph(self, graph_id: str) -> Optional[TaskGraph]:
        with self._lock:
            import copy
            graph = self._graphs.get(graph_id)
            return copy.deepcopy(graph) if graph else None

    def get_all_graphs(self) -> list[TaskGraph]:
        with self._lock:
            import copy
            return [copy.deepcopy(g) for g in self._graphs.values()]

    def cancel_graph(self, graph_id: str) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return False
            graph.status = TaskStatus.CANCELLED
            for node in graph.nodes:
                if node.status in (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING):
                    node.status = TaskStatus.CANCELLED
            return True

    def create_code_plan(self, goal: str, graph_id: Optional[str] = None) -> str:
        gid = graph_id or self.create_graph(goal).id
        g = self.get_graph(gid)
        if not g:
            return gid
        n1 = self.add_node(gid, "Analyze Requirements", "Understand code requirements and scope",
                           priority=9, estimated_duration=8.0)
        n2 = self.add_node(gid, "Design Solution", "Design the architecture and approach",
                           dependencies=[n1.id] if n1 else None,
                           priority=8, estimated_duration=10.0)
        n3a = self.add_node(gid, "Implement Core", "Implement the core logic",
                            dependencies=[n2.id] if n2 else None,
                            priority=7, estimated_duration=30.0)
        n3b = self.add_node(gid, "Write Tests", "Write unit and integration tests",
                            dependencies=[n2.id] if n2 else None,
                            priority=7, estimated_duration=15.0)
        n4 = self.add_node(gid, "Review & Refine", "Review implementation and refine",
                           dependencies=[n3a.id, n3b.id] if n3a and n3b else None,
                           priority=6, estimated_duration=10.0)
        return gid

    def create_research_plan(self, goal: str, graph_id: Optional[str] = None) -> str:
        gid = graph_id or self.create_graph(goal).id
        n1 = self.add_node(gid, "Define Research Questions", "Formulate key questions to answer",
                           priority=9, estimated_duration=5.0)
        n2a = self.add_node(gid, "Search Sources", "Search for relevant information",
                            dependencies=[n1.id] if n1 else None,
                            priority=8, estimated_duration=20.0)
        n2b = self.add_node(gid, "Collect Data", "Gather and organize found data",
                            dependencies=[n1.id] if n1 else None,
                            priority=8, estimated_duration=15.0)
        n3 = self.add_node(gid, "Synthesize Findings", "Combine and analyze collected information",
                           dependencies=[n2a.id, n2b.id] if n2a and n2b else None,
                           priority=7, estimated_duration=15.0)
        n4 = self.add_node(gid, "Generate Report", "Create comprehensive research report",
                           dependencies=[n3.id] if n3 else None,
                           priority=6, estimated_duration=10.0)
        return gid

    def create_deploy_plan(self, goal: str, graph_id: Optional[str] = None) -> str:
        gid = graph_id or self.create_graph(goal).id
        n1 = self.add_node(gid, "Verify Build", "Verify the build is clean",
                           priority=9, estimated_duration=10.0)
        n2a = self.add_node(gid, "Run Tests", "Run all test suites",
                            dependencies=[n1.id] if n1 else None,
                            priority=8, estimated_duration=15.0)
        n2b = self.add_node(gid, "Prepare Deployment Package", "Package the application",
                            dependencies=[n1.id] if n1 else None,
                            priority=8, estimated_duration=10.0)
        n3 = self.add_node(gid, "Deploy", "Execute deployment",
                           dependencies=[n2a.id, n2b.id] if n2a and n2b else None,
                           priority=7, estimated_duration=20.0)
        n4 = self.add_node(gid, "Verify Deployment", "Health check the deployed version",
                           dependencies=[n3.id] if n3 else None,
                           priority=6, estimated_duration=10.0)
        return gid
