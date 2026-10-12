"""Multi-Agent Orchestration Framework (Phase 58).

Advanced multi-agent orchestration with:
- Agent registration and discovery
- Task decomposition and delegation
- Inter-agent communication
- Consensus and voting mechanisms
- Workflow orchestration
- Agent lifecycle management
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor, Future, as_completed

from agent.multimodal.production import MetricsCollector, CircuitBreaker

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AgentState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    SPECIALIST = "specialist"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


@dataclass
class AgentCapability:
    """Agent capability description."""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    max_concurrent: int = 1
    estimated_latency_ms: float = 1000.0
    cost_per_call: float = 0.0


@dataclass
class AgentInfo:
    """Agent registration information."""
    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[AgentCapability]
    state: AgentState = AgentState.IDLE
    endpoint: str = ""
    metadata: Dict = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    current_load: int = 0
    max_load: int = 1


@dataclass
class Task:
    """Task definition for agent execution."""
    task_id: str
    name: str
    description: str
    input_data: Dict[str, Any]
    required_capabilities: List[str] = field(default_factory=list)
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    retry_count: int = 0
    max_retries: int = 3
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """Workflow definition with multiple tasks."""
    workflow_id: str
    name: str
    description: str
    tasks: List[Task] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (from_task_id, to_task_id)
    created_at: float = field(default_factory=time.time)


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, agent_info: AgentInfo):
        self.info = agent_info
        self._state = AgentState.IDLE
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=agent_info.max_load)
        self._current_tasks: Dict[str, Future] = {}
        self._shutdown = False

    @property
    def state(self) -> AgentState:
        with self._lock:
            return self._state

    @abstractmethod
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task and return result."""
        pass

    def can_handle(self, task: Task) -> bool:
        """Check if agent can handle the task."""
        for cap in self.info.capabilities:
            if all(req in cap.input_types for req in task.required_capabilities):
                return True
        return False

    def execute_async(self, task: Task) -> Future:
        """Execute task asynchronously."""
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Agent is shutting down")
            if len(self._current_tasks) >= self.info.max_load:
                raise RuntimeError("Agent at max capacity")

            future = self._executor.submit(self._execute_wrapper, task)
            self._current_tasks[task.task_id] = future
            return future

    def _execute_wrapper(self, task: Task) -> Dict:
        with self._lock:
            self._state = AgentState.RUNNING
        try:
            task.started_at = time.time()
            result = self.execute(task)
            task.completed_at = time.time()
            task.result = result
            with self._lock:
                self._state = AgentState.COMPLETED
                self._current_tasks.pop(task.task_id, None)
            return result
        except Exception as e:
            task.error = str(e)
            task.completed_at = time.time()
            with self._lock:
                self._state = AgentState.FAILED
                self._current_tasks.pop(task.task_id, None)
            raise

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "agent_id": self.info.agent_id,
                "name": self.info.name,
                "role": self.info.role.value,
                "state": self._state.value,
                "current_load": len(self._current_tasks),
                "max_load": self.info.max_load,
                "capabilities": [c.name for c in self.info.capabilities],
            }

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True
        self._executor.shutdown(wait=True)


class TaskOrchestrator:
    """Orchestrates task execution across multiple agents (Phase 58)."""

    def __init__(self, max_workers: int = 10):
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, Task] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._task_results: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._metrics = MetricsCollector("orchestrator")

    def register_agent(self, agent: BaseAgent) -> None:
        with self._lock:
            self._agents[agent.info.agent_id] = agent
            logger.info(f"Registered agent: {agent.info.name} ({agent.info.agent_id})")

    def unregister_agent(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].shutdown()
                del self._agents[agent_id]
                return True
            return False

    def submit_task(self, task: Task) -> str:
        """Submit a task for execution."""
        with self._lock:
            self._tasks[task.task_id] = task
        self._executor.submit(self._execute_task, task.task_id)
        return task.task_id

    def submit_workflow(self, workflow: Workflow) -> str:
        """Submit a workflow for execution."""
        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
            for task in workflow.tasks:
                self._tasks[task.task_id] = task

        self._executor.submit(self._execute_workflow, workflow.workflow_id)
        return workflow.workflow_id

    def _execute_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

        # Check dependencies
        if not self._check_dependencies(task):
            self._schedule_retry(task, "Dependencies not met")
            return

        # Find suitable agent
        agent = self._find_agent(task)
        if not agent:
            self._schedule_retry(task, "No suitable agent available")
            return

        try:
            future = agent.execute_async(task)
            result = future.result(timeout=task.timeout_seconds)
            with self._lock:
                self._task_results[task_id] = result
            self._metrics.counter("task_completed", labels={"agent": agent.info.agent_id})
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self._schedule_retry(task, str(e))

    def _check_dependencies(self, task: Task) -> bool:
        for dep_id in task.dependencies:
            if dep_id not in self._task_results:
                return False
            if self._task_results[dep_id].get("error"):
                return False
        return True

    def _find_agent(self, task: Task) -> Optional[BaseAgent]:
        candidates = []
        for agent in self._agents.values():
            if agent.state in (AgentState.IDLE, AgentState.RUNNING) and agent.can_handle(task):
                candidates.append(agent)

        if not candidates:
            return None

        # Prefer least loaded agent
        candidates.sort(key=lambda a: a.info.current_load)
        return candidates[0]

    def _schedule_retry(self, task: Task, error: str) -> None:
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.error = error
            logger.warning(f"Retrying task {task.task_id} ({task.retry_count}/{task.max_retries}): {error}")
            time.sleep(2 ** task.retry_count)  # Exponential backoff
            self._executor.submit(self._execute_task, task.task_id)
        else:
            logger.error(f"Task {task.task_id} failed after {task.max_retries} retries: {error}")
            with self._lock:
                self._task_results[task.task_id] = {"error": error, "failed": True}

    def _execute_workflow(self, workflow_id: str) -> None:
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return

        # Topological sort of tasks
        task_order = self._topological_sort(workflow.tasks, workflow.edges)

        # Execute tasks in order (respecting dependencies)
        for task in task_order:
            if task.task_id in self._task_results:
                continue
            self._execute_task(task.task_id)
            # Wait for completion (with timeout)
            timeout = task.timeout_seconds
            start = time.time()
            while task.task_id not in self._task_results:
                if time.time() - start > timeout:
                    break
                time.sleep(0.1)

    def _topological_sort(self, tasks: List[Task], edges: List[Tuple[str, str]]) -> List[Task]:
        """Topological sort of tasks based on dependencies."""
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}
        graph = defaultdict(list)

        for from_id, to_id in edges:
            graph[from_id].append(to_id)
            in_degree[to_id] += 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            tid = queue.pop(0)
            if tid in task_map:
                result.append(task_map[tid])
            for neighbor in graph[tid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(tasks):
            logger.warning("Cycle detected in workflow dependencies")
            return tasks  # Fallback to original order

        return result

    def get_task_result(self, task_id: str) -> Optional[Dict]:
        with self._lock:
            return self._task_results.get(task_id)

    def get_workflow_status(self, workflow_id: str) -> Dict:
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if not workflow:
                return {"error": "Workflow not found"}

            total = len(workflow.tasks)
            completed = sum(1 for t in workflow.tasks if t.task_id in self._task_results)
            failed = sum(1 for t in workflow.tasks if self._task_results.get(t.task_id, {}).get("error"))

            return {
                "workflow_id": workflow_id,
                "name": workflow.name,
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "in_progress": total - completed - failed,
                "progress": completed / total if total > 0 else 0,
            }

    def get_agent_statuses(self) -> List[Dict]:
        with self._lock:
            return [agent.get_status() for agent in self._agents.values()]

    def shutdown(self) -> None:
        for agent in self._agents.values():
            agent.shutdown()
        self._executor.shutdown(wait=True)


# Specialized Agents
class LLMReasoningAgent(BaseAgent):
    """Agent specialized in reasoning tasks."""

    def execute(self, task: Task) -> Dict[str, Any]:
        # In production, would call LLM
        prompt = task.input_data.get("prompt", "")
        context = task.input_data.get("context", "")

        # Simulated reasoning
        result = {
            "reasoning": f"Analyzed: {prompt[:100]}... with context length {len(context)}",
            "conclusion": "Simulated reasoning result",
            "confidence": 0.85,
        }
        return result


class CodeExecutionAgent(BaseAgent):
    """Agent specialized in code execution."""

    def execute(self, task: Task) -> Dict[str, Any]:
        code = task.input_data.get("code", "")
        language = task.input_data.get("language", "python")

        # In production, would execute in sandbox
        result = {
            "output": f"Executed {language} code (simulated)",
            "execution_time_ms": 100,
            "exit_code": 0,
        }
        return result


class SearchAgent(BaseAgent):
    """Agent specialized in search and retrieval."""

    def execute(self, task: Task) -> Dict[str, Any]:
        query = task.input_data.get("query", "")
        sources = task.input_data.get("sources", ["web"])

        result = {
            "results": [
                {"title": f"Result for {query}", "snippet": "Simulated search result", "url": "https://example.com"}
            ],
            "query": query,
            "sources_searched": sources,
        }
        return result


class SynthesisAgent(BaseAgent):
    """Agent specialized in synthesizing information from multiple sources."""

    def execute(self, task: Task) -> Dict[str, Any]:
        inputs = task.input_data.get("inputs", [])
        synthesis_type = task.input_data.get("type", "summary")

        # Simulate synthesis
        combined = "\n".join(str(i) for i in inputs)
        result = {
            "synthesis": f"{synthesis_type.capitalize()} of {len(inputs)} inputs",
            "combined_length": len(combined),
            "key_points": ["Point 1", "Point 2", "Point 3"],
        }
        return result


# Factory functions
def create_orchestrator() -> TaskOrchestrator:
    """Create a default orchestrator with standard agents."""
    orchestrator = TaskOrchestrator()

    # Register standard agents
    orchestrator.register_agent(LLMReasoningAgent(AgentInfo(
        agent_id="reasoner-1",
        name="LLM Reasoner",
        role=AgentRole.SPECIALIST,
        capabilities=[AgentCapability(
            name="reasoning",
            description="Complex reasoning and analysis",
            input_types=["text", "context"],
            output_types=["reasoning", "conclusion"],
        )],
    )))

    orchestrator.register_agent(CodeExecutionAgent(AgentInfo(
        agent_id="coder-1",
        name="Code Executor",
        role=AgentRole.WORKER,
        capabilities=[AgentCapability(
            name="code_execution",
            description="Execute code in sandbox",
            input_types=["code", "language"],
            output_types=["output", "execution_time"],
        )],
    )))

    orchestrator.register_agent(SearchAgent(AgentInfo(
        agent_id="searcher-1",
        name="Web Searcher",
        role=AgentRole.WORKER,
        capabilities=[AgentCapability(
            name="search",
            description="Web search and retrieval",
            input_types=["query"],
            output_types=["results"],
        )],
    )))

    orchestrator.register_agent(SynthesisAgent(AgentInfo(
        agent_id="synthesizer-1",
        name="Synthesizer",
        role=AgentRole.SPECIALIST,
        capabilities=[AgentCapability(
            name="synthesis",
            description="Synthesize multiple inputs",
            input_types=["inputs", "type"],
            output_types=["synthesis", "key_points"],
        )],
    )))

    return orchestrator


# Workflow helpers
def create_sequential_workflow(name: str, tasks: List[Task]) -> Workflow:
    """Create a sequential workflow from tasks."""
    edges = []
    for i in range(len(tasks) - 1):
        edges.append((tasks[i].task_id, tasks[i + 1].task_id))
    return Workflow(
        workflow_id=str(uuid.uuid4()),
        name=name,
        description=f"Sequential workflow: {name}",
        tasks=tasks,
        edges=edges,
    )


def create_parallel_workflow(name: str, tasks: List[Task]) -> Workflow:
    """Create a parallel workflow (all tasks independent)."""
    return Workflow(
        workflow_id=str(uuid.uuid4()),
        name=name,
        description=f"Parallel workflow: {name}",
        tasks=tasks,
        edges=[],
    )


def create_dag_workflow(name: str, tasks: List[Task], edges: List[Tuple[str, str]]) -> Workflow:
    """Create a DAG workflow with explicit dependencies."""
    return Workflow(
        workflow_id=str(uuid.uuid4()),
        name=name,
        description=f"DAG workflow: {name}",
        tasks=tasks,
        edges=edges,
    )