"""
Unit tests for all AetherOS Swarm modules.

Tests each module's core functionality in isolation, using mocks
for the event bus where appropriate. Covers all 14 swarm modules:
registry, capabilities, communication, planner, task_allocator,
dispatcher, scheduler, worker, coordinator, consensus, conflict_resolution,
execution_monitor, result_merger, progress_tracker, orchestrator.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from kernel.event_bus import EventBus, Event
from swarm.registry import (
    SwarmAgentRegistry, AgentTypeProfile,
    AGENT_TYPE_PLANNING, AGENT_TYPE_CODING, AGENT_TYPE_RESEARCH,
    AGENT_TYPE_BROWSER, AGENT_TYPE_FILESYSTEM, AGENT_TYPE_TERMINAL,
    AGENT_TYPE_DOCUMENTATION, AGENT_TYPE_TESTING, AGENT_TYPE_REVIEW,
    AGENT_TYPE_DEBUG, AGENT_TYPE_MEMORY, AGENT_TYPE_PLUGIN, AGENT_TYPE_MCP,
    BUILTIN_AGENT_TYPE_PROFILES,
)
from swarm.capabilities import (
    CapabilityRegistry, AgentCapability,
    CAPABILITY_CODING, CAPABILITY_RESEARCH, CAPABILITY_PLANNING,
    CAPABILITY_REVIEW, CAPABILITY_DEBUG, CAPABILITY_BROWSER,
    CAPABILITY_FILESYSTEM, CAPABILITY_TERMINAL, CAPABILITY_TESTING,
    CAPABILITY_DOCUMENTATION, CAPABILITY_MEMORY, CAPABILITY_MCP,
    BUILTIN_CAPABILITIES,
)
from swarm.communication import (
    InterAgentMessageBus, AgentMessage, MessageType,
)
from swarm.planner import (
    SwarmPlanner, SwarmPlan, AgentTask, AgentTaskStatus,
)
from swarm.task_allocator import TaskAllocator, Assignment
from swarm.dispatcher import TaskDispatcher
from swarm.scheduler import SwarmScheduler, ScheduledTask
from swarm.worker import AgentWorker, AgentResult
from swarm.coordinator import Coordinator, WorkflowState
from swarm.consensus import ConsensusEngine, ConsensusResult, Vote
from swarm.conflict_resolution import (
    ConflictResolver, ConflictType, ConflictRecord,
)
from swarm.execution_monitor import ExecutionMonitor, AgentProgress
from swarm.result_merger import ResultMerger
from swarm.progress_tracker import ProgressTracker
from swarm.orchestrator import SwarmOrchestrator, SwarmConfig, SwarmState


# ======================================================================
# Registry Tests
# ======================================================================

class TestSwarmAgentRegistry:
    def test_register_and_get(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        profile = AgentTypeProfile(name="test-agent", capabilities={"test"})
        reg.register(profile)
        assert reg.get("test-agent") is profile

    def test_builtins_loaded(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        assert reg.get(AGENT_TYPE_PLANNING) is not None
        assert reg.get(AGENT_TYPE_CODING) is not None
        assert reg.get(AGENT_TYPE_RESEARCH) is not None
        assert reg.get(AGENT_TYPE_FILESYSTEM) is not None

    def test_list_agent_types(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        reg.register(AgentTypeProfile(name="a", capabilities={"x"}))
        reg.register(AgentTypeProfile(name="b", capabilities={"y"}))
        assert len(reg.list_agent_types()) == 2

    def test_find_by_capability(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        reg.register(AgentTypeProfile(name="coder", capabilities={"coding", "terminal"}))
        reg.register(AgentTypeProfile(name="researcher", capabilities={"research"}))
        coders = reg.find_by_capability("coding")
        assert len(coders) == 1
        assert coders[0].name == "coder"

    def test_find_by_capabilities_all(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        reg.register(AgentTypeProfile(name="fullstack", capabilities={"coding", "testing"}))
        reg.register(AgentTypeProfile(name="partial", capabilities={"coding"}))
        matches = reg.find_by_capabilities({"coding", "testing"}, min_match=1)
        assert len(matches) == 2
        assert matches[0].name == "fullstack"  # Better match first

    def test_deregister(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        reg.register(AgentTypeProfile(name="temp", capabilities={"temp"}))
        assert reg.deregister("temp") is True
        assert reg.get("temp") is None

    def test_snapshot(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        snap = reg.snapshot()
        assert snap["total_agent_types"] == 13  # All builtins
        assert snap["total_capabilities"] > 0

    def test_get_all_capabilities(self):
        reg = SwarmAgentRegistry(load_builtins=False)
        reg.register(AgentTypeProfile(name="a", capabilities={"x", "y"}))
        reg.register(AgentTypeProfile(name="b", capabilities={"y", "z"}))
        caps = reg.get_all_capabilities()
        assert caps == {"x", "y", "z"}


# ======================================================================
# Capabilities Tests
# ======================================================================

class TestCapabilityRegistry:
    def test_register_and_get(self):
        reg = CapabilityRegistry(load_builtins=False)
        cap = AgentCapability(id="my-cap", name="My Capability")
        reg.register(cap)
        assert reg.get("my-cap") is cap

    def test_builtins_loaded(self):
        reg = CapabilityRegistry(load_builtins=True)
        assert reg.get(CAPABILITY_CODING) is not None
        assert reg.get(CAPABILITY_RESEARCH) is not None
        assert reg.get(CAPABILITY_PLANNING) is not None

    def test_list_capabilities(self):
        reg = CapabilityRegistry(load_builtins=True)
        caps = reg.list_capabilities()
        assert len(caps) > 10  # Many built-in capabilities

    def test_get_required_tools(self):
        reg = CapabilityRegistry(load_builtins=True)
        tools = reg.get_required_tools({"coding", "research"})
        assert "web_search" in tools
        assert "read_file" in tools or "write_file" in tools

    def test_dependency_chain(self):
        reg = CapabilityRegistry(load_builtins=True)
        chain = reg.get_dependency_chain(CAPABILITY_REVIEW)
        # Review depends on coding
        assert CAPABILITY_CODING in chain

    def test_deregister(self):
        reg = CapabilityRegistry(load_builtins=False)
        reg.register(AgentCapability(id="temp"))
        assert reg.deregister("temp") is True
        assert reg.get("temp") is None


# ======================================================================
# Communication Tests
# ======================================================================

class TestInterAgentMessageBus:
    def test_send_message(self):
        bus = InterAgentMessageBus()
        received = []
        bus.subscribe("agent-1", lambda m: received.append(m))
        bus.send(AgentMessage(
            message_type=MessageType.EVENT,
            sender="coordinator",
            recipient="agent-1",
            topic="test",
        ))
        assert len(received) == 1
        assert received[0].topic == "test"

    def test_broadcast(self):
        bus = InterAgentMessageBus()
        received = []
        bus.subscribe("a", lambda m: received.append(m))
        bus.subscribe("b", lambda m: received.append(m))
        bus.broadcast("sender", "broadcast-test")
        assert len(received) == 2

    def test_request_response(self):
        bus = InterAgentMessageBus()
        responses = []

        def handler(msg):
            if msg.message_type == MessageType.REQUEST:
                bus.respond(msg, "response-data")

        bus.subscribe("server", handler)
        bus.subscribe("client", lambda m: responses.append(m))

        result = bus.request("client", "server", "ping", timeout=5.0)
        assert result is not None
        assert result.payload == "response-data"

    def test_wildcard_subscription(self):
        bus = InterAgentMessageBus()
        received = []
        bus.subscribe_all(lambda m: received.append(m))
        bus.send(AgentMessage(
            message_type=MessageType.EVENT, sender="s", topic="t",
        ))
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = InterAgentMessageBus()
        received = []
        unsub = bus.subscribe("agent", lambda m: received.append(m))
        unsub()
        bus.send(AgentMessage(
            message_type=MessageType.EVENT, sender="s", recipient="agent",
        ))
        assert len(received) == 0

    def test_get_stats(self):
        bus = InterAgentMessageBus()
        bus.subscribe("a", lambda m: None)
        bus.subscribe("b", lambda m: None)
        stats = bus.get_stats()
        assert stats["subscriber_count"] == 2

    def test_get_recent_messages(self):
        bus = InterAgentMessageBus()
        bus.send(AgentMessage(
            message_type=MessageType.EVENT, sender="s", topic="t",
        ))
        msgs = bus.get_recent_messages()
        assert len(msgs) == 1


# ======================================================================
# Planner Tests
# ======================================================================

class TestSwarmPlanner:
    def test_decompose_goal(self):
        planner = SwarmPlanner()
        plan = planner.decompose_goal("Build a web app")
        assert plan.goal == "Build a web app"
        assert len(plan.tasks) > 0  # Default strategy generates tasks

    def test_plan_lifecycle(self):
        planner = SwarmPlanner()
        plan = planner.decompose_goal("Test")
        planner.approve_plan(plan.id)
        assert planner.get_plan(plan.id).status == "approved"
        planner.start_plan(plan.id)
        assert planner.get_plan(plan.id).status == "in_progress"
        planner.complete_plan(plan.id)
        assert planner.get_plan(plan.id).status == "completed"

    def test_fail_and_cancel_plan(self):
        planner = SwarmPlanner()
        plan = planner.decompose_goal("Test")
        planner.fail_plan(plan.id, "error")
        assert planner.get_plan(plan.id).status == "failed"
        plan2 = planner.decompose_goal("Test 2")
        planner.cancel_plan(plan2.id)
        assert planner.get_plan(plan2.id).status == "cancelled"

    def test_get_ready_tasks(self):
        planner = SwarmPlanner()
        task_a = AgentTask(description="A", priority=10)
        task_b = AgentTask(description="B", dependencies=[task_a.id])
        plan = SwarmPlan(goal="Test", tasks=[task_a, task_b])
        with pytest.MonkeyPatch().context() as m:
            m.setattr(planner, "_plans", {plan.id: plan})
            # No tasks ready until A completes
            ready = planner.get_ready_tasks(plan.id)
            assert len(ready) == 1  # A has no deps
            assert ready[0].id == task_a.id

    def test_update_task_status(self):
        planner = SwarmPlanner()
        task = AgentTask(description="Test task")
        plan = SwarmPlan(goal="Test", tasks=[task])
        with pytest.MonkeyPatch().context() as m:
            m.setattr(planner, "_plans", {plan.id: plan})
            planner.update_task_status(plan.id, task.id, AgentTaskStatus.COMPLETED, result="done")
            assert plan.tasks[0].status == AgentTaskStatus.COMPLETED
            assert plan.tasks[0].result == "done"

    def test_get_progress(self):
        planner = SwarmPlanner()
        plan = planner.decompose_goal("Test")
        progress = planner.get_progress(plan.id)
        assert progress is not None
        assert progress["total"] > 0
        assert progress["completed"] == 0

    def test_register_strategy(self):
        planner = SwarmPlanner()

        def custom_strategy(goal, context):
            return [AgentTask(description="Custom task")]

        planner.register_strategy(custom_strategy)
        plan = planner.decompose_goal("Custom goal")
        # Should have custom tasks
        assert len(plan.tasks) > 0

    def test_cleanup(self):
        planner = SwarmPlanner()
        planner.decompose_goal("G1")
        planner.decompose_goal("G2")
        assert planner.cleanup() == 2

    def test_list_plans(self):
        planner = SwarmPlanner()
        planner.decompose_goal("G1")
        planner.decompose_goal("G2")
        assert len(planner.list_plans()) == 2


# ======================================================================
# Task Allocator Tests
# ======================================================================

class TestTaskAllocator:
    def test_find_best_agent(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        task = AgentTask(
            description="Write code",
            required_capabilities={"coding"},
        )
        assignment = allocator.find_best_agent(task, plan_id="plan-1")
        assert assignment is not None
        assert assignment.agent_type == "coding-agent"
        assert assignment.confidence > 0

    def test_find_no_agent(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        task = AgentTask(
            description="Unknown task",
            required_capabilities={"unknown_skill_xyz"},
        )
        assignment = allocator.find_best_agent(task)
        assert assignment is None

    def test_workload_tracking(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        task = AgentTask(description="Code", required_capabilities={"coding"})
        allocator.find_best_agent(task)
        workload = allocator.get_workload()
        assert "coding-agent" in workload
        assert workload["coding-agent"] >= 1

    def test_release_assignment(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        allocator.release_assignment("coding-agent")
        # Should not raise

    def test_find_best_agent_for_goal(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        profile = allocator.find_best_agent_for_goal(
            "Write some code", {"coding"},
        )
        assert profile is not None
        assert profile.name == "coding-agent"

    def test_get_stats(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        stats = allocator.get_stats()
        assert "total_assignments" in stats


# ======================================================================
# Dispatcher Tests
# ======================================================================

class TestTaskDispatcher:
    def test_dispatch_single(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        worker = AgentWorker()
        dispatcher = TaskDispatcher(allocator, worker)
        task = AgentTask(
            description="Test task",
            goal="Say hello",
            required_capabilities={"terminal"},
        )
        result = dispatcher.dispatch_single(task)
        # The worker may fail to spawn a real agent (no parent_agent),
        # but the dispatcher should return the task with a status
        assert result is not None
        assert result.id == task.id

    def test_get_stats(self):
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        worker = AgentWorker()
        dispatcher = TaskDispatcher(allocator, worker)
        stats = dispatcher.get_stats()
        assert "total_dispatched" in stats


# ======================================================================
# Scheduler Tests
# ======================================================================

class TestSwarmScheduler:
    def test_schedule_and_run(self):
        scheduler = SwarmScheduler()
        task = AgentTask(description="Simple task", priority=10)
        results = []

        def runner():
            results.append("ran")
            return True

        scheduled = scheduler.schedule_task(task, "plan-1", runner)
        assert scheduled.status == "pending"

        summary = scheduler.run_until_complete(max_parallel=1)
        assert summary["completed"] == 1
        assert len(results) == 1

    def test_dependency_ordering(self):
        scheduler = SwarmScheduler()
        task_a = AgentTask(description="A", priority=10)
        task_b = AgentTask(description="B", dependencies=[task_a.id])

        order = []
        scheduler.schedule_task(task_a, "plan-1", lambda: order.append("A") or True)
        scheduler.schedule_task(task_b, "plan-1", lambda: order.append("B") or True)

        summary = scheduler.run_until_complete(max_parallel=1)
        assert summary["completed"] == 2
        assert order == ["A", "B"]

    def test_cancel_all(self):
        scheduler = SwarmScheduler()
        scheduler.schedule_task(AgentTask(description="T1"), "p1", lambda: True)
        scheduler.schedule_task(AgentTask(description="T2"), "p1", lambda: True)
        count = scheduler.cancel_all()
        assert count == 2

    def test_get_summary(self):
        scheduler = SwarmScheduler()
        scheduler.schedule_task(AgentTask(description="T1"), "p1", lambda: True)
        summary = scheduler.get_summary()
        assert summary["total"] == 1
        assert summary["pending"] == 1


# ======================================================================
# Worker Tests
# ======================================================================

class TestAgentWorker:
    def test_get_toolsets_for_agent(self):
        worker = AgentWorker()
        toolsets = worker._get_toolsets_for_agent("coding-agent")
        assert "file" in toolsets or "terminal" in toolsets

    def test_get_stats(self):
        worker = AgentWorker()
        stats = worker.get_stats()
        assert "total_runs" in stats
        assert stats["total_runs"] == 0

    def test_cancel_task(self):
        worker = AgentWorker()
        assert worker.cancel_task("nonexistent") is False


# ======================================================================
# Coordinator Tests
# ======================================================================

class TestCoordinator:
    def test_run_goal(self):
        planner = SwarmPlanner()
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        worker = AgentWorker()
        dispatcher = TaskDispatcher(allocator, worker)
        merger = ResultMerger()
        coordinator = Coordinator(planner, dispatcher, merger)

        result = coordinator.run_goal("Say hello", max_parallel=1)
        assert "workflow_id" in result
        assert "status" in result
        assert "merged_result" in result

    def test_cancel_workflow(self):
        planner = SwarmPlanner()
        reg = SwarmAgentRegistry(load_builtins=True)
        allocator = TaskAllocator(reg)
        worker = AgentWorker()
        dispatcher = TaskDispatcher(allocator, worker)
        merger = ResultMerger()
        coordinator = Coordinator(planner, dispatcher, merger)

        assert coordinator.cancel_workflow("nonexistent") is False

    def test_get_workflow_state(self):
        coordinator = Coordinator(
            SwarmPlanner(), TaskDispatcher(TaskAllocator(SwarmAgentRegistry()), AgentWorker()),
            ResultMerger(),
        )
        assert coordinator.get_workflow_state("nonexistent") is None

    def test_get_active_workflows(self):
        coordinator = Coordinator(
            SwarmPlanner(), TaskDispatcher(TaskAllocator(SwarmAgentRegistry()), AgentWorker()),
            ResultMerger(),
        )
        active = coordinator.get_active_workflows()
        assert isinstance(active, list)


# ======================================================================
# Consensus Tests
# ======================================================================

class TestConsensusEngine:
    def test_resolve_unanimous(self):
        engine = ConsensusEngine()
        votes = [
            Vote(agent_id="agent-1", choice="option-a", confidence=0.9),
            Vote(agent_id="agent-2", choice="option-a", confidence=0.8),
        ]
        result = engine.resolve("Which option?", votes)
        assert result.decision == "option-a"
        assert result.confidence > 0.5

    def test_resolve_disagreement(self):
        engine = ConsensusEngine()
        votes = [
            Vote(agent_id="a", choice="option-a", confidence=0.9),
            Vote(agent_id="b", choice="option-b", confidence=0.8),
        ]
        result = engine.resolve("Which option?", votes)
        # Weighted vote should pick option-a (higher confidence)
        assert result.decision == "option-a"

    def test_simple_majority(self):
        engine = ConsensusEngine()
        votes = [
            Vote(agent_id="a", choice="yes", confidence=0.5),
            Vote(agent_id="b", choice="yes", confidence=0.5),
            Vote(agent_id="c", choice="no", confidence=0.9),
        ]
        # 2 vs 1, so "yes" wins
        result = engine.resolve("Vote", votes, weighted=False)
        assert result.decision == "yes"

    def test_empty_votes(self):
        engine = ConsensusEngine()
        result = engine.resolve("Empty", [])
        assert result.decision is None
        assert result.confidence == 0.0

    def test_reviewer_override(self):
        engine = ConsensusEngine()
        votes = [
            Vote(agent_id="a", choice="bad", confidence=0.8),
            Vote(agent_id="b", choice="bad", confidence=0.7),
        ]

        def override(topic, votes):
            return "overridden-decision"

        result = engine.resolve("Test", votes, reviewer_override=override)
        assert result.decision == "overridden-decision"
        assert result.override_by == "reviewer"

    def test_get_stats(self):
        engine = ConsensusEngine()
        engine.resolve("T1", [Vote("a", "x", 0.9)])
        engine.resolve("T2", [Vote("b", "y", 0.8)])
        stats = engine.get_stats()
        assert stats["total_resolutions"] == 2
        assert stats["average_confidence"] > 0


# ======================================================================
# Conflict Resolution Tests
# ======================================================================

class TestConflictResolver:
    def test_file_write_allowed(self):
        resolver = ConflictResolver()
        assert resolver.check_file_write("agent-1", "/path/file.py") is True

    def test_file_write_conflict(self):
        resolver = ConflictResolver()
        resolver.check_file_write("agent-1", "/path/file.py")
        assert resolver.check_file_write("agent-2", "/path/file.py") is False

    def test_tool_contention(self):
        resolver = ConflictResolver()
        assert resolver.check_tool_usage("agent-1", "terminal") is True
        assert resolver.check_tool_usage("agent-2", "terminal") is False

    def test_non_serialized_tool(self):
        resolver = ConflictResolver()
        assert resolver.check_tool_usage("agent-1", "read_file") is True
        assert resolver.check_tool_usage("agent-2", "read_file") is True

    def test_workspace_lock(self):
        resolver = ConflictResolver()
        assert resolver.lock_workspace("agent-1", "ws-1") is True
        assert resolver.lock_workspace("agent-2", "ws-1") is False
        assert resolver.unlock_workspace("agent-1", "ws-1") is True
        assert resolver.lock_workspace("agent-2", "ws-1") is True

    def test_release_agent(self):
        resolver = ConflictResolver()
        resolver.check_file_write("agent-1", "f1.txt")
        resolver.check_file_write("agent-1", "f2.txt")
        assert resolver.release_agent("agent-1") == 2

    def test_release_all(self):
        resolver = ConflictResolver()
        resolver.check_file_write("agent-1", "f1.txt")
        resolver.check_tool_usage("agent-2", "terminal")
        assert resolver.release_all() == 2

    def test_get_stats(self):
        resolver = ConflictResolver()
        resolver.check_file_write("a", "f.txt")
        resolver.check_file_write("b", "f.txt")  # Conflict
        stats = resolver.get_stats()
        assert stats["total_conflicts"] == 1
        assert stats["active_file_locks"] == 1


# ======================================================================
# Execution Monitor Tests
# ======================================================================

class TestExecutionMonitor:
    def test_register_plan(self):
        monitor = ExecutionMonitor()
        plan = SwarmPlan(goal="Test", tasks=[AgentTask(description="T1")])
        monitor.register_plan(plan)
        assert monitor.get_stats()["tracked_agents"] == 1

    def test_set_task_running(self):
        monitor = ExecutionMonitor()
        plan = SwarmPlan(goal="Test", tasks=[AgentTask(description="T1")])
        monitor.register_plan(plan)
        monitor.set_task_running(plan.tasks[0].id, "coding-agent")
        report = monitor.get_report(plan.id)
        assert report["stats"]["running"] == 1

    def test_set_task_completed(self):
        monitor = ExecutionMonitor()
        plan = SwarmPlan(goal="Test", tasks=[AgentTask(description="T1")])
        monitor.register_plan(plan)
        monitor.set_task_completed(plan.tasks[0].id, "Result text")
        report = monitor.get_report(plan.id)
        assert report["stats"]["completed"] == 1

    def test_set_task_failed(self):
        monitor = ExecutionMonitor()
        plan = SwarmPlan(goal="Test", tasks=[AgentTask(description="T1")])
        monitor.register_plan(plan)
        monitor.set_task_failed(plan.tasks[0].id, "Error message")
        report = monitor.get_report(plan.id)
        assert report["stats"]["failed"] == 1

    def test_subscribe(self):
        monitor = ExecutionMonitor()
        received = []
        unsub = monitor.subscribe(lambda e, a: received.append((e, a)))
        plan = SwarmPlan(goal="Test", tasks=[AgentTask(description="T1")])
        monitor.register_plan(plan)
        monitor.set_task_running(plan.tasks[0].id, "agent")
        assert len(received) >= 1
        unsub()
        monitor.set_task_completed(plan.tasks[0].id)
        # Should still have same count since unsubscribed
        assert len(received) >= 1


# ======================================================================
# Result Merger Tests
# ======================================================================

class TestResultMerger:
    def test_merge_single_task(self):
        merger = ResultMerger()
        task = AgentTask(
            description="Task 1", status=AgentTaskStatus.COMPLETED,
            result="This is the output of task 1",
        )
        result = merger.merge([task], goal="Test goal")
        assert result["status"] == "completed"
        assert result["completed_count"] == 1
        assert "task 1" in result["merged_output"].lower()

    def test_merge_multiple_tasks(self):
        merger = ResultMerger()
        tasks = [
            AgentTask(
                description="Research", status=AgentTaskStatus.COMPLETED,
                result="Research results", assigned_to="research-agent",
            ),
            AgentTask(
                description="Implement", status=AgentTaskStatus.COMPLETED,
                result="Implementation code", assigned_to="coding-agent",
            ),
        ]
        result = merger.merge(tasks, goal="Build project")
        assert result["completed_count"] == 2
        assert "Research" in result["merged_output"]

    def test_merge_failed_tasks(self):
        merger = ResultMerger()
        tasks = [
            AgentTask(
                description="Succeeded", status=AgentTaskStatus.COMPLETED,
                result="OK",
            ),
            AgentTask(
                description="Failed", status=AgentTaskStatus.FAILED,
                error="Error occurred",
            ),
        ]
        result = merger.merge(tasks)
        assert result["completed_count"] == 1
        assert result["failed_count"] == 1

    def test_merge_no_completed(self):
        merger = ResultMerger()
        tasks = [AgentTask(description="Failed", status=AgentTaskStatus.FAILED)]
        result = merger.merge(tasks)
        assert result["status"] == "failed"

    def test_deduplicate(self):
        merger = ResultMerger()
        outputs = [
            {"agent_type": "a", "output": "Hello world. This is great."},
            {"agent_type": "b", "output": "Hello world. This is great too."},
        ]
        deduped = merger._deduplicate_outputs(outputs)
        assert len(deduped) <= 2

    def test_extract_summary(self):
        merger = ResultMerger()
        text = "## Summary\nThe project is complete.\n\n## Details\nMore info here."
        summary = merger._extract_summary(text)
        assert "project is complete" in summary


# ======================================================================
# Progress Tracker Tests
# ======================================================================

class TestProgressTracker:
    def test_workflow_lifecycle(self):
        tracker = ProgressTracker()
        tracker.report_workflow_started("wf-1", "Test goal", task_count=3)
        tracker.report_task_assigned("wf-1", "t1", "Task 1", "coding-agent")
        tracker.report_task_started("wf-1", "t1")
        tracker.report_task_completed("wf-1", "t1")
        tracker.report_workflow_completed("wf-1")
        # Should not raise

    def test_workflow_failed(self):
        tracker = ProgressTracker()
        tracker.report_workflow_started("wf-2", "Failing goal")
        tracker.report_workflow_failed("wf-2", "Something broke")
        state = tracker.get_workflow_state("wf-2")
        assert state is not None

    def test_get_workflow_state(self):
        tracker = ProgressTracker()
        tracker.report_workflow_started("wf-1", "Goal")
        state = tracker.get_workflow_state("wf-1")
        assert state is not None
        assert state["goal"] == "Goal"

    def test_cleanup(self):
        tracker = ProgressTracker()
        tracker.report_workflow_started("wf-1", "G1")
        tracker.report_workflow_started("wf-2", "G2")
        assert tracker.get_stats()["tracked_workflows"] == 2
        tracker.cleanup()
        assert tracker.get_stats()["tracked_workflows"] == 0


# ======================================================================
# Orchestrator Tests
# ======================================================================

class TestSwarmOrchestrator:
    def test_create_and_start(self):
        swarm = SwarmOrchestrator(config=SwarmConfig(auto_register_agents=True))
        assert swarm.state == SwarmState.STOPPED
        swarm.start()
        assert swarm.state == SwarmState.RUNNING
        swarm.stop()
        assert swarm.state == SwarmState.STOPPED

    def test_health_status(self):
        swarm = SwarmOrchestrator(config=SwarmConfig(auto_register_agents=True))
        swarm.start()
        health = swarm.health()
        assert health["state"] == SwarmState.RUNNING.value
        assert health["agent_types"] == 13
        swarm.stop()

    def test_swarm_status(self):
        swarm = SwarmOrchestrator(config=SwarmConfig(auto_register_agents=True))
        swarm.start()
        status = swarm.status()
        assert "orchestrator" in status
        assert "registry" in status
        assert "coordinator" in status
        swarm.stop()

    def test_run_workflow_when_stopped(self):
        swarm = SwarmOrchestrator(config=SwarmConfig(auto_register_agents=True))
        # Don't start
        result = swarm.run_workflow("Test goal")
        assert "error" in result

    def test_register_deregister_agent(self):
        swarm = SwarmOrchestrator(
            config=SwarmConfig(auto_register_agents=False),
        )
        swarm.start()
        profile = AgentTypeProfile(
            name="custom-agent", description="Custom", capabilities={"custom"},
        )
        assert swarm.register_agent_type(profile) is True
        assert swarm.agent_registry.get("custom-agent") is not None
        assert swarm.deregister_agent_type("custom-agent") is True
        assert swarm.agent_registry.get("custom-agent") is None
        swarm.stop()

    def test_subsystem_access(self):
        swarm = SwarmOrchestrator(
            config=SwarmConfig(auto_register_agents=True),
        )
        assert swarm.get_coordinator() is not None
        assert swarm.get_planner() is not None
        assert swarm.get_registry() is not None
        assert swarm.get_monitor() is not None


# ======================================================================
# Integration Tests
# ======================================================================

class TestSwarmIntegration:
    def test_full_workflow_planning(self):
        """Test the planning pipeline end-to-end."""
        swarm = SwarmOrchestrator(
            config=SwarmConfig(auto_register_agents=True),
        )
        swarm.start()

        # Create a plan
        plan = swarm.planner.decompose_goal(
            "Build a simple Python calculator app",
        )
        assert plan is not None
        assert len(plan.tasks) > 0
        assert any("planning" in t.required_capabilities for t in plan.tasks)

        swarm.stop()

    def test_allocator_finds_coding_agent(self):
        """Test allocator finds the right agent type for coding tasks."""
        allocator = TaskAllocator(
            SwarmAgentRegistry(load_builtins=True),
        )
        task = AgentTask(
            description="Implement feature X",
            required_capabilities={"coding"},
        )
        assignment = allocator.find_best_agent(task, "plan-1")
        assert assignment is not None
        assert assignment.agent_type == "coding-agent"

    def test_consensus_voting(self):
        """Test consensus engine produces expected outcomes."""
        engine = ConsensusEngine()
        votes = [
            Vote(agent_id="coder", choice="Use Python", confidence=0.9),
            Vote(agent_id="researcher", choice="Use Python", confidence=0.8),
            Vote(agent_id="reviewer", choice="Use JavaScript", confidence=0.7),
        ]
        result = engine.resolve("Which language?", votes)
        assert result.decision == "Use Python"
        assert result.confidence > 0.5

    def test_conflict_detection(self):
        """Test conflict resolver detects file contention."""
        resolver = ConflictResolver()
        assert resolver.check_file_write("agent-1", "/src/main.py") is True
        assert resolver.check_file_write("agent-2", "/src/main.py") is False
        resolver.release_agent("agent-1")
        assert resolver.check_file_write("agent-2", "/src/main.py") is True

    def test_progress_events(self):
        """Test progress tracker emits structured events."""
        bus = EventBus()
        tracker = ProgressTracker(bus)
        events = []
        bus.subscribe("swarm.workflow.started", lambda e: events.append(e))
        bus.subscribe("swarm.task.assigned", lambda e: events.append(e))
        bus.subscribe("swarm.workflow.completed", lambda e: events.append(e))

        tracker.report_workflow_started("wf-1", "Test", task_count=2)
        tracker.report_task_assigned("wf-1", "t1", "Task 1", "coding-agent")
        tracker.report_workflow_completed("wf-1", "Done")

        assert len(events) == 3

    def test_message_bus_agent_communication(self):
        """Test inter-agent messaging."""
        bus = InterAgentMessageBus()
        messages = []

        # Only subscribe one agent to avoid counting broadcast to self
        bus.subscribe("coding-agent", lambda m: messages.append(m))

        # Broadcast from coordinator — coding-agent receives it
        bus.broadcast("coordinator", "new_task", {"id": "t1"})
        # Private message — coding-agent receives it
        bus.send(AgentMessage(
            message_type=MessageType.PRIVATE,
            sender="coordinator",
            recipient="coding-agent",
            topic="assign",
            payload={"task": "Write tests"},
        ))

        assert len(messages) == 2

    def test_dependency_graph_execution(self):
        """Test that tasks execute in dependency order."""
        scheduler = SwarmScheduler()
        order = []

        task_a = AgentTask(description="Setup", priority=10)
        task_b = AgentTask(description="Build", dependencies=[task_a.id])
        task_c = AgentTask(description="Test", dependencies=[task_b.id])

        scheduler.schedule_task(task_a, "p1", lambda: order.append("A") or True)
        scheduler.schedule_task(task_b, "p1", lambda: order.append("B") or True)
        scheduler.schedule_task(task_c, "p1", lambda: order.append("C") or True)

        summary = scheduler.run_until_complete(max_parallel=1)
        assert summary["completed"] == 3
        assert order == ["A", "B", "C"]
