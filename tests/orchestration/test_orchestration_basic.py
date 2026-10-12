"""Basic tests for the AetherOS Orchestration Layer."""

import pytest
import asyncio
from agent.orchestration import (
    TaskSpec,
    TaskBudget,
    TaskStatus,
    TaskPriority,
    AgentRole,
    AgentIdentity,
    AgentCapabilities,
    AgentMetadata,
    create_task_spec,
    create_task_budget,
    can_transition,
    is_terminal_status,
)


class TestTypes:
    """Test core type definitions."""

    def test_task_spec_creation(self):
        """Test creating a TaskSpec."""
        task = create_task_spec(
            goal="Test goal",
            description="Test description",
            priority=TaskPriority.HIGH,
        )
        assert task.goal == "Test goal"
        assert task.description == "Test description"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.task_id.startswith("task-")

    def test_task_budget_creation(self):
        """Test creating a TaskBudget."""
        budget = create_task_budget(
            max_time_seconds=1800,
            max_tokens=50000,
            max_cost_usd=5.0,
        )
        assert budget.max_time_seconds == 1800
        assert budget.max_tokens == 50000
        assert budget.max_cost_usd == 5.0

    def test_agent_identity(self):
        """Test AgentIdentity creation."""
        identity = AgentIdentity(role=AgentRole.RESEARCH, name="TestAgent")
        assert identity.role == AgentRole.RESEARCH
        assert identity.name == "TestAgent"
        assert identity.agent_id.startswith("agent-")
        assert identity.instance_id.startswith("inst-")

    def test_agent_capabilities(self):
        """Test AgentCapabilities."""
        caps = AgentCapabilities()
        caps.add("web_search")
        caps.add("research", {"detail": "deep"})
        assert caps.has("web_search")
        assert caps.has("research")
        assert not caps.has("coding")
        assert caps.get("research") == {"detail": "deep"}

    def test_status_transitions(self):
        """Test valid status transitions."""
        assert can_transition(TaskStatus.PENDING, TaskStatus.QUEUED)
        assert can_transition(TaskStatus.QUEUED, TaskStatus.READY)
        assert can_transition(TaskStatus.READY, TaskStatus.RUNNING)
        assert can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)
        assert can_transition(TaskStatus.RUNNING, TaskStatus.FAILED)
        assert can_transition(TaskStatus.RUNNING, TaskStatus.PAUSED)
        assert can_transition(TaskStatus.PAUSED, TaskStatus.RUNNING)

        # Invalid transitions
        assert not can_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)
        assert not can_transition(TaskStatus.FAILED, TaskStatus.COMPLETED)
        assert not can_transition(TaskStatus.PENDING, TaskStatus.RUNNING)

    def test_terminal_statuses(self):
        """Test terminal status detection."""
        assert is_terminal_status(TaskStatus.COMPLETED)
        assert is_terminal_status(TaskStatus.FAILED)
        assert is_terminal_status(TaskStatus.CANCELLED)
        assert is_terminal_status(TaskStatus.TIMEOUT)
        assert is_terminal_status(TaskStatus.EMERGENCY_STOPPED)

        assert not is_terminal_status(TaskStatus.PENDING)
        assert not is_terminal_status(TaskStatus.RUNNING)
        assert not is_terminal_status(TaskStatus.PAUSED)

    def test_agent_metadata(self):
        """Test AgentMetadata."""
        meta = AgentMetadata(
            description="Test agent",
            author="Test",
            tags=["test", "demo"],
            supported_platforms=["linux", "macos"],
            model_requirements=["gpt-4", "claude-3"],
        )
        assert meta.description == "Test agent"
        assert "test" in meta.tags
        assert "linux" in meta.supported_platforms
        assert "gpt-4" in meta.model_requirements


class TestAgentInterface:
    """Test agent interface definitions."""

    def test_agent_interface_structure(self):
        """Test that AgentInterface has required methods."""
        from agent.orchestration.agent_interface import AgentInterface
        import inspect

        # Check required methods exist
        methods = [m for m in dir(AgentInterface) if not m.startswith('_')]
        required = ['identity', 'capabilities', 'metadata', 'state',
                    'initialize', 'shutdown', 'health_check',
                    'execute_task', 'cancel_task',
                    'supports_capability', 'get_capability_detail',
                    'get_active_tasks', 'get_task_status',
                    'update_config', 'get_config']

        for req in required:
            assert req in methods, f"Missing method: {req}"


class TestCapabilityInference:
    """Test capability inference from text."""

    def test_infer_capabilities(self):
        """Test inferring capabilities from goal text."""
        from agent.orchestration.decomposition import CapabilityInference

        caps = CapabilityInference.infer_capabilities("research and write a report about AI")
        assert "web_search" in caps
        assert "research" in caps
        assert "file_write" in caps  # "write" maps to file_write

        caps = CapabilityInference.infer_capabilities("write code and run tests")
        assert "code_execution" in caps
        assert "coding" in caps
        assert "testing" in caps

    def test_infer_roles(self):
        """Test inferring agent roles from goal text."""
        from agent.orchestration.decomposition import CapabilityInference

        roles = CapabilityInference.infer_roles("research the topic and write a report")
        assert "research" in roles
        assert "writer" in roles

        roles = CapabilityInference.infer_roles("debug the code and fix bugs")
        assert "developer" in roles


class TestDecomposition:
    """Test task decomposition."""

    def test_rule_based_decomposition(self):
        """Test rule-based task decomposition."""
        from agent.orchestration.decomposition import RuleBasedDecomposer, SubtaskSpec

        subtasks = RuleBasedDecomposer.decompose("research and write a report")
        assert len(subtasks) > 0
        assert all(isinstance(s, SubtaskSpec) for s in subtasks)
        assert any("research" in s.goal.lower() for s in subtasks)
        assert any("write" in s.goal.lower() for s in subtasks)

    def test_hybrid_decomposer(self):
        """Test hybrid decomposer."""
        from agent.orchestration.decomposition import HybridDecomposer, DecompositionConfig

        config = DecompositionConfig(max_subtasks=5)
        decomposer = HybridDecomposer()
        decomposer.set_config(config)

        import asyncio
        result = asyncio.run(decomposer.decompose("research AI trends and write summary"))
        assert len(result.subtasks) > 0
        assert result.total_estimated_time > 0


class TestTaskGraph:
    """Test task graph operations."""

    def test_create_graph(self):
        """Test creating a task graph."""
        from agent.orchestration.task_graph import TaskGraphManager, TaskSpec, TaskPriority

        manager = TaskGraphManager()
        graph = manager.create_graph("test-graph")

        task1 = TaskSpec(task_id="task-1", goal="Task 1", priority=TaskPriority.HIGH)
        task2 = TaskSpec(task_id="task-2", goal="Task 2", priority=TaskPriority.NORMAL)

        assert manager.add_task("test-graph", task1)
        assert manager.add_task("test-graph", task2)

        assert manager.add_dependency("test-graph", "task-1", "task-2")

        deps = manager.get_dependencies("test-graph", "task-2")
        assert "task-1" in deps

    def test_cycle_detection(self):
        """Test cycle detection in task graph."""
        from agent.orchestration.task_graph import TaskGraphManager, TaskSpec, CycleDetectedError

        manager = TaskGraphManager()
        graph = manager.create_graph("cycle-test")

        task1 = TaskSpec(task_id="a", goal="A")
        task2 = TaskSpec(task_id="b", goal="B")
        task3 = TaskSpec(task_id="c", goal="C")

        manager.add_task("cycle-test", task1)
        manager.add_task("cycle-test", task2)
        manager.add_task("cycle-test", task3)

        manager.add_dependency("cycle-test", "a", "b")
        manager.add_dependency("cycle-test", "b", "c")

        # This should raise CycleDetectedError
        with pytest.raises(CycleDetectedError):
            manager.add_dependency("cycle-test", "c", "a")

    def test_execution_plan(self):
        """Test execution plan computation."""
        from agent.orchestration.task_graph import TaskGraphManager, TaskSpec, TaskPriority

        manager = TaskGraphManager()
        graph = manager.create_graph("plan-test")

        tasks = [
            TaskSpec(task_id="t1", goal="First"),
            TaskSpec(task_id="t2", goal="Second"),
            TaskSpec(task_id="t3", goal="Third"),
        ]

        for t in tasks:
            manager.add_task("plan-test", t)

        manager.add_dependency("plan-test", "t1", "t2")
        manager.add_dependency("plan-test", "t2", "t3")

        plan = manager.compute_execution_plan("plan-test")
        assert plan is not None
        assert plan.total_levels == 3
        assert plan.levels[0] == ["t1"]
        assert plan.levels[1] == ["t2"]
        assert plan.levels[2] == ["t3"]


class TestTaskLifecycle:
    """Test task lifecycle management."""

    @pytest.mark.asyncio
    async def test_lifecycle_transitions(self):
        """Test valid lifecycle transitions."""
        from agent.orchestration.task_lifecycle import TaskStatus, create_task, get_lifecycle_manager

        lifecycle = get_lifecycle_manager()
        task = create_task("Test task")
        task_id = task.task_id

        # Valid transitions
        assert await lifecycle.transition(task_id, TaskStatus.QUEUED)
        assert await lifecycle.transition(task_id, TaskStatus.READY)
        assert await lifecycle.transition(task_id, TaskStatus.RUNNING)
        assert await lifecycle.transition(task_id, TaskStatus.COMPLETED)

        # Check final status
        final_task = lifecycle.get_task(task_id)
        assert final_task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_invalid_transition(self):
        """Test invalid transition is rejected."""
        from agent.orchestration.task_lifecycle import TaskStatus, create_task, get_lifecycle_manager

        lifecycle = get_lifecycle_manager()
        task = create_task("Test task")
        task_id = task.task_id

        await lifecycle.transition(task_id, TaskStatus.COMPLETED)

        # Cannot transition from terminal state
        result = await lifecycle.transition(task_id, TaskStatus.RUNNING)
        assert result is False

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        """Test convenience lifecycle methods."""
        from agent.orchestration.task_lifecycle import TaskStatus, create_task, get_lifecycle_manager

        lifecycle = get_lifecycle_manager()
        task = create_task("Test task")
        task_id = task.task_id

        await lifecycle.queue_task(task_id)
        assert lifecycle.get_task(task_id).status == TaskStatus.QUEUED

        await lifecycle.mark_ready(task_id)
        assert lifecycle.get_task(task_id).status == TaskStatus.READY

        await lifecycle.start_task(task_id)
        assert lifecycle.get_task(task_id).status == TaskStatus.RUNNING

        await lifecycle.complete_task(task_id, result="Done")
        assert lifecycle.get_task(task_id).status == TaskStatus.COMPLETED


class TestApproval:
    """Test approval system."""

    @pytest.mark.asyncio
    async def test_approval_request(self):
        """Test creating and responding to approval."""
        from agent.orchestration.approval import ApprovalManager, ApprovalAction, ApprovalResponse, ApprovalScope

        manager = ApprovalManager()

        request = await manager.request_approval(
            task_id="task-1",
            agent_id="agent-1",
            action=ApprovalAction.FILE_DELETE,
            description="Delete important file",
            details={"path": "/important/file.txt"},
        )

        assert request.status == "pending"
        assert request.action == ApprovalAction.FILE_DELETE

        # Respond
        result = manager.respond_to_approval(
            request.request_id,
            ApprovalResponse.APPROVE_ONCE,
            "user-1",
        )
        assert result is True

        # Check approval
        approved, response = manager.check_approval(
            ApprovalAction.FILE_DELETE,
            task_id="task-1",
            agent_id="agent-1",
        )
        assert approved is True
        assert response == ApprovalResponse.APPROVE_ONCE


class TestBudget:
    """Test budget management."""

    def test_budget_manager(self):
        """Test budget manager."""
        from agent.orchestration.budget import BudgetManager, BudgetType, BudgetLimit, BudgetAction

        manager = BudgetManager()

        task_id = "test-task"
        budget = TaskBudget(max_time_seconds=100, max_cost_usd=5.0)
        manager.set_task_budget(task_id, budget)

        # Record usage within limits
        assert manager.record_usage(task_id, BudgetType.TIME, 10)
        assert manager.record_usage(task_id, BudgetType.COST, 1.0)

        # Check remaining
        assert manager.get_remaining(task_id, BudgetType.TIME) == 90
        assert manager.get_remaining(task_id, BudgetType.COST) == 4.0

    def test_budget_exceeded(self):
        """Test budget exceeded handling."""
        from agent.orchestration.budget import BudgetManager, BudgetType, BudgetAction

        manager = BudgetManager()
        task_id = "test-task"
        budget = TaskBudget(max_time_seconds=100)
        manager.set_task_budget(task_id, budget)

        # Exceed time budget
        assert not manager.record_usage(task_id, BudgetType.TIME, 150)

        status = manager.get_budget_status(task_id)
        assert status["time"]["used"] >= status["time"]["limit"]


class TestRecovery:
    """Test recovery system."""

    @pytest.mark.asyncio
    async def test_checkpoint_manager(self):
        """Test checkpoint creation and restoration."""
        from agent.orchestration.recovery import CheckpointManager, CheckpointType, TaskSpec

        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            manager = CheckpointManager(checkpoint_dir=temp_dir)

            task = TaskSpec(goal="Test task", required_capabilities=["test"])
            task.metadata["plan_id"] = "plan-1"

            checkpoint = await manager.create_checkpoint(task, CheckpointType.TASK_START)
            assert checkpoint.checkpoint_id.startswith("cp-")

            # Load checkpoint
            loaded = await manager.load_checkpoint(checkpoint.checkpoint_id)
            assert loaded is not None
            assert loaded.task_id == task.task_id

            # Latest checkpoint
            latest = await manager.get_latest_checkpoint(task.task_id)
            assert latest.checkpoint_id == checkpoint.checkpoint_id
        finally:
            shutil.rmtree(temp_dir)

    def test_retry_handler(self):
        """Test retry handler."""
        from agent.orchestration.recovery import RetryHandler, RetryPolicy, FailureType

        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        handler = RetryHandler(policy)

        # Should retry
        assert handler.should_retry(FailureType.TIMEOUT, 0)
        assert handler.should_retry(FailureType.RATE_LIMIT, 1)

        # Should not retry
        assert not handler.should_retry(FailureType.AUTH_ERROR, 0)
        assert not handler.should_retry(FailureType.TIMEOUT, 3)  # Max attempts

        # Delay calculation
        delay = handler.get_delay(0)
        assert delay > 0

        delay = handler.get_delay(1)
        assert delay > handler.get_delay(0)  # Exponential


class TestQueue:
    """Test task queue."""

    @pytest.mark.asyncio
    async def test_basic_queue(self):
        """Test basic queue operations."""
        from agent.orchestration.queue import TaskQueue, TaskSpec, TaskPriority

        queue = TaskQueue()

        task = TaskSpec(goal="Test", priority=TaskPriority.HIGH)
        await queue.enqueue(task)

        assert queue.get_size() == 1

        entry = await queue.dequeue()
        assert entry is not None
        assert entry.task.goal == "Test"

    @pytest.mark.asyncio
    async def test_priority_queue(self):
        """Test priority ordering."""
        from agent.orchestration.queue import TaskQueue, TaskSpec, TaskPriority

        queue = TaskQueue()

        low = TaskSpec(goal="Low", priority=TaskPriority.LOW)
        high = TaskSpec(goal="High", priority=TaskPriority.HIGH)

        await queue.enqueue(low)
        await queue.enqueue(high)

        # High priority should come first
        entry = await queue.dequeue()
        assert entry.task.goal == "High"

        entry = await queue.dequeue()
        assert entry.task.goal == "Low"

    @pytest.mark.asyncio
    async def test_cancel(self):
        """Test task cancellation."""
        from agent.orchestration.queue import TaskQueue, TaskSpec

        queue = TaskQueue()

        task = TaskSpec(goal="Test")
        await queue.enqueue(task)

        assert await queue.cancel(task.task_id)
        assert queue.get_size() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])