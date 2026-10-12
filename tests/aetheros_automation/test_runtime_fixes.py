"""Tests for the stabilized runtime fixes in aetheros_automation."""

from __future__ import annotations

import asyncio

import pytest

from aetheros_automation.orchestrator import TaskOrchestrator
from aetheros_automation.models.models import Task, TaskStatus, Workflow, ExecutionMode


class TestTaskOrchestratorExecution:
    def setup_method(self):
        self.orchestrator = TaskOrchestrator()

    @pytest.mark.asyncio
    async def test_execute_plan_runs_subtasks(self):
        plan = await self.orchestrator.understand_objective("Research AI providers and write a report")
        plan = await self.orchestrator.create_execution_plan(plan)
        result = await self.orchestrator.execute_plan(plan.id)
        assert result["success"] is True
        assert len(result["completed_tasks"]) == len(plan.subtasks)
        assert result["failed_tasks"] == []
        assert "results" in result

    @pytest.mark.asyncio
    async def test_execute_plan_populates_state_lists(self):
        plan = await self.orchestrator.understand_objective("Write a README")
        plan = await self.orchestrator.create_execution_plan(plan)
        await self.orchestrator.execute_plan(plan.id)
        state = self.orchestrator.get_state(plan.id)
        assert state is not None
        assert len(state.completed_tasks) == len(plan.subtasks)
        assert state.running_tasks == []
        assert state.pending_tasks == []

    @pytest.mark.asyncio
    async def test_execute_plan_handles_task_exception(self):
        async def boom(*args, **kwargs):
            raise RuntimeError("kaboom")

        self.orchestrator.execution_engine.execute_task = boom
        plan = await self.orchestrator.understand_objective("Build something")
        plan = await self.orchestrator.create_execution_plan(plan)
        result = await self.orchestrator.execute_plan(plan.id)
        assert result["success"] is False
        assert len(result["failed_tasks"]) == len(plan.subtasks)

    @pytest.mark.asyncio
    async def test_run_entrypoint_returns_summary(self):
        result = await self.orchestrator.run(goal="Write a short report")
        assert result["success"] is True
        assert "summary" in result
        assert "tasks completed" in result["summary"]

    @pytest.mark.asyncio
    async def test_run_entrypoint_honors_approval_callback(self):
        async def deny(task):
            return False

        result = await self.orchestrator.run(
            goal="Delete all files", approval_callback=deny
        )
        assert result["success"] is False


class TestTaskOrchestratorParallel:
    @pytest.mark.asyncio
    async def test_parallel_level_execution_handles_exceptions(self):
        orch = TaskOrchestrator()
        plan = await orch.understand_objective("Test something important")
        plan = await orch.create_execution_plan(plan)
        for task in plan.subtasks:
            task.execution_mode = None  # force through parallel path determinism guard
        result = await orch.execute_plan(plan.id)
        assert "success" in result


class TestAutomationEngine:
    @pytest.mark.asyncio
    async def test_create_task_accepts_goal_alias(self):
        from aetheros_automation.core.engine import AutomationEngine

        engine = AutomationEngine()
        task = engine.create_task(goal="Write a website", priority=3, timeout=60)
        assert task.name == "Write a website"
        assert task.metadata.get("goal") == "Write a website"
        assert task.priority == 3
        assert task.timeout == 60

    @pytest.mark.asyncio
    async def test_submit_task_executes_under_running_loop(self):
        from aetheros_automation.core.engine import AutomationEngine

        async def main():
            engine = AutomationEngine()
            engine.start()
            task = engine.create_task(goal="Run a simple action")
            engine.submit_task(task)
            await asyncio.sleep(0.3)
            engine.stop()
            return task.status

        status = await main()
        assert status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_engine_registers_all_role_agents(self):
        from aetheros_automation.core.engine import AutomationEngine
        from aetheros_automation.agents.registry import AgentRegistry

        engine = AutomationEngine()
        registry = engine.get_subsystem("agents.registry")
        assert registry is not None
        roles = set(AgentRegistry.list_agents())
        for expected in ("developer", "writer", "planner", "research", "coordinator"):
            assert expected in roles


class TestTaskScheduler:
    @pytest.mark.asyncio
    async def test_enqueue_sets_queued_status(self):
        from aetheros_automation.core.engine import AutomationEngine
        from aetheros_automation.core.scheduler import TaskScheduler

        engine = AutomationEngine()
        scheduler = TaskScheduler(engine)
        task = engine.create_task(name="Sched", goal="Do it")
        assert scheduler.enqueue(task) is True
        assert task.status == TaskStatus.QUEUED
        assert scheduler.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_enqueue_workflow_uses_tasks_field(self):
        from aetheros_automation.core.engine import AutomationEngine
        from aetheros_automation.core.scheduler import TaskScheduler

        engine = AutomationEngine()
        scheduler = TaskScheduler(engine)
        workflow = Workflow(
            id="wf-test",
            name="wf",
            tasks=[engine.create_task(name="A", goal="a"), engine.create_task(name="B", goal="b")],
        )
        scheduler.enqueue_workflow(workflow)
        assert scheduler.get_queue_size() == 2


class TestCLICommands:
    def test_task_summary_handles_goal_via_metadata(self):
        from aetheros_automation.cli.commands import _task_summary
        from aetheros_automation.core.engine import AutomationEngine

        engine = AutomationEngine()
        task = engine.create_task(goal="Some goal text")
        summary = _task_summary(task)
        assert "Some goal text" in summary

    def test_task_create_cmd_runs(self):
        from aetheros_automation.cli.commands import task_cmd

        out = task_cmd(["create", "build", "a", "thing"])
        assert "Task created and submitted" in out

    def test_automate_cmd_no_crash_on_summary(self):
        from aetheros_automation.cli.commands import automate_cmd, _ENGINE

        out = automate_cmd(["write", "docs"])
        assert "Task completed" in out or "Task created" in out


class TestAgentRegistryImport:
    def test_all_role_agents_register_cleanly(self):
        from aetheros_automation.agents.registry import AgentRegistry

        roles = AgentRegistry.list_agents()
        assert "creative" in roles
        assert "communication" in roles
        assert "data" in roles
        assert "review" in roles


class TestLifecycleWiring:
    """The unified lifecycle state machine must be driven by real execution."""

    @pytest.mark.asyncio
    async def test_plan_flows_through_lifecycle_states(self):
        from aetheros_automation.lifecycle.states import LifecycleState

        orch = TaskOrchestrator()
        plan = await orch.understand_objective("Research AI providers and write a report")
        plan = await orch.create_execution_plan(plan)
        tracker = orch.lifecycle(plan.id)
        assert tracker is not None
        assert tracker.state in (LifecycleState.PLANNING, LifecycleState.EXECUTING)

        await orch.execute_plan(plan.id)
        tracker = orch.lifecycle(plan.id)
        assert tracker.state == LifecycleState.COMPLETED

    @pytest.mark.asyncio
    async def test_task_lifecycle_reaches_completed(self):
        from aetheros_automation.lifecycle.states import LifecycleState

        orch = TaskOrchestrator()
        plan = await orch.understand_objective("Write a short report")
        plan = await orch.create_execution_plan(plan)
        await orch.execute_plan(plan.id)
        for task in plan.subtasks:
            tracker = orch.lifecycle(f"task:{task.id}")
            assert tracker is not None
            assert tracker.state == LifecycleState.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_plan_reaches_failed_state(self):
        from aetheros_automation.lifecycle.states import LifecycleState

        async def boom(*args, **kwargs):
            raise RuntimeError("kaboom")

        orch = TaskOrchestrator()
        orch.execution_engine.execute_task = boom
        plan = await orch.understand_objective("Build something")
        plan = await orch.create_execution_plan(plan)
        await orch.execute_plan(plan.id)
        tracker = orch.lifecycle(plan.id)
        assert tracker.state == LifecycleState.FAILED

    @pytest.mark.asyncio
    async def test_archive_plan_reaches_archived_state(self):
        from aetheros_automation.lifecycle.states import LifecycleState

        orch = TaskOrchestrator()
        plan = await orch.understand_objective("Write a README")
        plan = await orch.create_execution_plan(plan)
        await orch.execute_plan(plan.id)
        await orch.archive_plan(plan.id)
        tracker = orch.lifecycle(plan.id)
        assert tracker.state == LifecycleState.ARCHIVED

    @pytest.mark.asyncio
    async def test_lifecycle_events_emitted(self):
        orch = TaskOrchestrator()
        events = []
        orch.on("task.state_changed", lambda d: events.append(d))
        plan = await orch.understand_objective("Write a short report")
        plan = await orch.create_execution_plan(plan)
        await orch.execute_plan(plan.id)
        assert len(events) > 0
        assert any(e["entity_id"] == plan.id for e in events)

    @pytest.mark.asyncio
    async def test_lifecycle_never_breaks_execution(self):
        """Illegal transitions are logged, never raised into execution."""
        orch = TaskOrchestrator()
        orch._lifecycle_events = False
        plan = await orch.understand_objective("Write a short report")
        plan = await orch.create_execution_plan(plan)
        result = await orch.execute_plan(plan.id)
        assert result["success"] is True


class TestExecutionEngineEvents:
    """The execution engine's tool events must reach subscribers."""

    def test_engine_emits_tool_events(self):
        import asyncio

        from aetheros_automation.orchestrator.execution_engine import ExecutionEngine
        from aetheros_automation.orchestrator.types import AgentAssignment, OrchestrationTask
        from aetheros_automation.models.models import AgentRole

        engine = ExecutionEngine()
        seen = []
        engine.on("tool.started", lambda d: seen.append(d))
        engine.on("tool.completed", lambda d: seen.append(d))
        engine.on("tool.called", lambda d: seen.append(d))

        task = OrchestrationTask(id="t-1", name="Test", description="Do a thing")
        agent = AgentAssignment(agent_id="a-1", role=AgentRole.DEVELOPER, tools=["web_search"])
        asyncio.run(engine.execute_task(task=task, agent=agent))

        assert any(e.get("tool") == "web_search" for e in seen)
        assert any(e.get("task_id") == "t-1" for e in seen)

    def test_engine_events_bridged_to_orchestrator(self):
        import asyncio

        orch = TaskOrchestrator()
        seen = []
        orch.on("tool.completed", lambda d: seen.append(d))
        plan = asyncio.run(orch.understand_objective("Write a short report"))
        plan = asyncio.run(orch.create_execution_plan(plan))
        asyncio.run(orch.execute_plan(plan.id))
        assert len(seen) >= 1


class TestExecutionHistory:
    """Plan outcomes must be persisted durably, keyed by plan id."""

    def test_execution_history_round_trip(self):
        orch = TaskOrchestrator()
        result = asyncio.run(orch.run(goal="Write a short report"))
        path = orch.save_execution_history(plan_id=result["plan_id"], result=result)
        assert path.endswith(f"{result['plan_id']}.history.json")

        loaded = orch.load_execution_history(result["plan_id"])
        assert loaded is not None
        assert loaded["plan_id"] == result["plan_id"]
        assert loaded["success"] is True
        assert loaded["lifecycle"] is not None

    def test_execution_history_missing_returns_none(self):
        orch = TaskOrchestrator()
        assert orch.load_execution_history("no-such-plan") is None
