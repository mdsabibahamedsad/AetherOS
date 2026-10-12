"""
Task Decomposition — converts architecture into executable engineering tasks.

Produces structured tasks that support:
  - Parallel work
  - Dependency tracking
  - Priority and estimation
  - Ownership by specialized agents
  - Progressive refinement
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class Priority(enum.IntEnum):
    """Priority levels for decomposed tasks."""
    BLOCKER = 0
    CRITICAL = 10
    HIGH = 25
    MEDIUM = 50
    LOW = 75
    NICE_TO_HAVE = 100


@dataclass
class Estimation:
    """Time and complexity estimation for a task.

    Attributes:
        complexity: Complexity rating (1-10)
        estimated_hours: Estimated person-hours
        confidence: Confidence in estimate (0.0 - 1.0)
        risk_level: Risk level (low, medium, high)
        notes: Estimation notes
    """
    complexity: int = 5
    estimated_hours: float = 1.0
    confidence: float = 0.7
    risk_level: str = "medium"
    notes: str = ""


@dataclass
class Ownership:
    """Ownership information for a task.

    Attributes:
        agent_type: Preferred agent type (e.g. "coding-agent", "testing-agent")
        capabilities: Required capabilities
        assigned_to: Who is assigned (agent ID or name)
        notes: Assignment notes
    """
    agent_type: str = ""
    capabilities: Set[str] = field(default_factory=set)
    assigned_to: str = ""
    notes: str = ""


@dataclass
class TaskDependency:
    """A dependency relationship between two tasks.

    Attributes:
        task_id: The task that depends on another
        depends_on: The task that must be completed first
        type: Dependency type (blocks, requires, relates_to)
        description: Why this dependency exists
    """
    task_id: str = ""
    depends_on: str = ""
    type: str = "requires"  # blocks, requires, relates_to
    description: str = ""


@dataclass
class DecomposedTask:
    """A single task produced by task decomposition.

    Attributes:
        id: Unique task ID
        title: Task title
        description: Detailed description
        priority: Task priority
        estimation: Time and complexity estimate
        ownership: Who should work on this
        dependencies: List of task IDs this depends on
        acceptance_criteria: Criteria for completion
        files_to_modify: Files that need changes
        generated_artifacts: Files this task will generate
        parallel_group: Group ID for parallel execution (tasks in same group run together)
        status: Task status
        subtasks: List of sub-task IDs
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    description: str = ""
    priority: Priority = Priority.MEDIUM
    estimation: Estimation = field(default_factory=Estimation)
    ownership: Ownership = field(default_factory=Ownership)
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    files_to_modify: List[str] = field(default_factory=list)
    generated_artifacts: List[str] = field(default_factory=list)
    parallel_group: str = ""
    status: str = "pending"  # pending, ready, in_progress, completed, failed, blocked
    subtasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskDecomposer:
    """Converts architecture and specifications into executable engineering tasks.

    Produces structured, dependency-tracked tasks that can be assigned to
    specialized agents for parallel execution.

    Usage:
        decomposer = TaskDecomposer(event_bus)
        tasks = decomposer.decompose(architecture_design, specification)
        for task in tasks:
            print(f"{task.title}: {task.estimation.estimated_hours}h")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._decompositions: Dict[str, List[DecomposedTask]] = {}

    def decompose(self, architecture, specification=None,
                  context: Dict[str, Any] = None) -> List[DecomposedTask]:
        """Decompose architecture into executable tasks.

        Args:
            architecture: ArchitectureDesign object (or any dict-like with module info)
            specification: Optional Specification for requirements context
            context: Additional context

        Returns:
            List of DecomposedTask objects with dependencies and priorities
        """
        tasks: List[DecomposedTask] = []
        architecture_id = getattr(architecture, 'id', uuid.uuid4().hex[:8])

        # Extract module information
        modules = []
        if hasattr(architecture, 'modules'):
            modules = architecture.modules
        else:
            # Fall back for direct module list
            modules = architecture if isinstance(architecture, list) else []

        # Extract constraints and requirements text
        requirements_text = ""
        if specification and hasattr(specification, 'goals'):
            requirements_text = str(specification.goal)

        # Create setup/skeleton task
        setup_task = DecomposedTask(
            title="Project setup and scaffolding",
            description="Initialize project structure, configuration, and dependency management",
            priority=Priority.CRITICAL,
            estimation=Estimation(complexity=2, estimated_hours=0.5, confidence=0.9),
            ownership=Ownership(agent_type="coding-agent",
                                capabilities={"coding", "project_setup"}),
            acceptance_criteria=[
                "Project structure created",
                "Dependencies configured",
                "Build system functional",
            ],
        )
        tasks.append(setup_task)

        # Create tasks for each module
        module_task_ids = {}
        for module in modules:
            module_name = getattr(module, 'name', 'Unnamed')
            module_desc = getattr(module, 'description', '')
            module_deps = getattr(module, 'dependencies', [])

            impl_task = DecomposedTask(
                title=f"Implement {module_name} module",
                description=module_desc or f"Implement the {module_name} module",
                priority=Priority.HIGH,
                estimation=Estimation(
                    complexity=5,
                    estimated_hours=self._estimate_module_hours(module_name, requirements_text),
                    confidence=0.7,
                ),
                ownership=Ownership(
                    agent_type=self._agent_type_for_module(module_name),
                    capabilities=self._capabilities_for_module(module_name),
                ),
                files_to_modify=self._files_for_module(module_name),
                acceptance_criteria=[
                    f"{module_name} module implemented",
                    f"{module_name} tests pass",
                    f"{module_name} interfaces defined",
                ],
            )

            # Add dependencies on other modules
            for dep_name in module_deps:
                if dep_name in module_task_ids:
                    impl_task.dependencies.append(module_task_ids[dep_name])

            # All implementation tasks depend on setup
            impl_task.dependencies.append(setup_task.id)

            tasks.append(impl_task)
            module_task_ids[module_name.lower()] = impl_task.id

        # Create test task
        test_task = DecomposedTask(
            title="Write comprehensive tests",
            description="Write unit tests, integration tests, and test utilities",
            priority=Priority.HIGH,
            estimation=Estimation(complexity=6, estimated_hours=3.0, confidence=0.6),
            ownership=Ownership(agent_type="testing-agent",
                                capabilities={"testing", "validation"}),
            dependencies=[t.id for t in tasks if t != setup_task],
            acceptance_criteria=[
                "All modules have unit tests",
                "Integration tests cover critical paths",
                "Test coverage meets threshold",
            ],
        )
        tasks.append(test_task)

        # Create documentation task
        doc_task = DecomposedTask(
            title="Write documentation",
            description="Document API, architecture, setup, and usage",
            priority=Priority.MEDIUM,
            estimation=Estimation(complexity=3, estimated_hours=2.0, confidence=0.7),
            ownership=Ownership(agent_type="documentation-agent",
                                capabilities={"documentation", "writing"}),
            dependencies=[t.id for t in tasks if t != setup_task],
            acceptance_criteria=[
                "API documentation generated",
                "README updated",
                "Architecture documented",
            ],
        )
        tasks.append(doc_task)

        # Store decomposition
        decomposition_id = f"{architecture_id}_{int(time.time())}"
        self._decompositions[decomposition_id] = tasks

        logger.info(
            "TaskDecomposer: decomposed into %d tasks: %s",
            len(tasks), ", ".join(t.title for t in tasks),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.tasks_decomposed", {
                "architecture_id": architecture_id,
                "task_count": len(tasks),
                "estimated_hours": sum(t.estimation.estimated_hours for t in tasks),
            })

        return tasks

    def _estimate_module_hours(self, module_name: str,
                                requirements_text: str) -> float:
        """Estimate person-hours for a module based on its type."""
        name_lower = module_name.lower()
        if "core" in name_lower:
            return 4.0
        if "api" in name_lower:
            return 3.0
        if "data" in name_lower:
            return 3.0
        if "auth" in name_lower:
            return 2.0
        if "ui" in name_lower or "frontend" in name_lower or "interface" in name_lower:
            return 4.0
        if "test" in name_lower:
            return 2.0
        return 2.0

    def _agent_type_for_module(self, module_name: str) -> str:
        """Determine the best agent type for a module."""
        name_lower = module_name.lower()
        if "test" in name_lower:
            return "testing-agent"
        if "doc" in name_lower:
            return "documentation-agent"
        return "coding-agent"

    def _capabilities_for_module(self, module_name: str) -> Set[str]:
        """Determine required capabilities for a module."""
        name_lower = module_name.lower()
        if "api" in name_lower:
            return {"coding", "api_design"}
        if "data" in name_lower:
            return {"coding", "database"}
        if "auth" in name_lower:
            return {"coding", "security"}
        if "ui" in name_lower or "frontend" in name_lower:
            return {"coding", "frontend"}
        if "test" in name_lower:
            return {"testing", "validation"}
        return {"coding"}

    def _files_for_module(self, module_name: str) -> List[str]:
        """Determine the files associated with a module."""
        name_lower = module_name.lower()
        safe_name = name_lower.replace(" ", "_")
        return [
            f"src/{safe_name}/",
            f"src/{safe_name}/__init__.py",
        ]

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def get_ready_tasks(self, tasks: List[DecomposedTask]) -> List[DecomposedTask]:
        """Get tasks whose dependencies are all satisfied.

        Args:
            tasks: List of all tasks

        Returns:
            Tasks that are ready to be worked on
        """
        completed_ids = {
            t.id for t in tasks
            if t.status == "completed"
        }

        ready = []
        for task in tasks:
            if task.status != "pending":
                continue
            if all(dep in completed_ids for dep in task.dependencies):
                ready.append(task)

        # Sort by priority (lower number = higher priority)
        ready.sort(key=lambda t: t.priority.value)
        return ready

    def get_parallel_groups(self, tasks: List[DecomposedTask]) -> Dict[str, List[DecomposedTask]]:
        """Group tasks by their parallel execution group.

        Args:
            tasks: List of all tasks

        Returns:
            Dict mapping group_id -> list of tasks in that group
        """
        groups: Dict[str, List[DecomposedTask]] = {}
        for task in tasks:
            if task.parallel_group:
                groups.setdefault(task.parallel_group, []).append(task)
            elif task.status == "pending" and not task.dependencies:
                # Tasks with no dependencies and no group are in default group
                groups.setdefault("default", []).append(task)
        return groups

    def update_task_status(self, tasks: List[DecomposedTask],
                           task_id: str, status: str) -> bool:
        """Update the status of a task.

        Args:
            tasks: List of all tasks
            task_id: ID of the task to update
            status: New status

        Returns:
            True if successful
        """
        for task in tasks:
            if task.id == task_id:
                task.status = status
                logger.debug("TaskDecomposer: task %s -> %s", task_id, status)
                return True
        return False

    def get_decomposition(self, decomposition_id: str) -> Optional[List[DecomposedTask]]:
        """Get a stored decomposition by ID."""
        return self._decompositions.get(decomposition_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get decomposer statistics."""
        total_tasks = sum(len(tasks) for tasks in self._decompositions.values())
        total_hours = sum(
            t.estimation.estimated_hours
            for tasks in self._decompositions.values()
            for t in tasks
        )
        return {
            "total_decompositions": len(self._decompositions),
            "total_tasks": total_tasks,
            "estimated_hours": total_hours,
        }
