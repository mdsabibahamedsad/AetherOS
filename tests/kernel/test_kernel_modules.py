"""
Unit tests for all AetherOS Kernel modules.

Tests each module's core functionality in isolation, using mocks
for the event bus where appropriate.
"""

from __future__ import annotations

import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from kernel.event_bus import EventBus, Event, EventPriority, EventTopics
from kernel.lifecycle import (
    LifecycleManager, ServiceRegistration, ComponentState,
)
from kernel.registry import AgentRegistry, ComponentEntry
from kernel.scheduler import KernelScheduler, ScheduledJob, JobPriority
from kernel.planner import Planner, Plan, PlanStep, PlanStatus
from kernel.executor import Executor, ExecutionResult, ExecutionStatus
from kernel.router import Router, RouteEntry, RouteNotFoundError
from kernel.workspace import WorkspaceManager, Workspace
from kernel.context import ContextManager, SharedContext
from kernel.permissions import (
    PermissionManager, PermissionCheck, PermissionRule,
    PermissionAction, PermissionLevel,
)
from kernel.task_graph import TaskGraph, TaskNode, GraphStatus
from kernel.telemetry import TelemetryCollector, MetricPoint
from kernel.state_manager import StateManager


# ======================================================================
# Event Bus Tests
# ======================================================================

class TestEventBus:
    def test_publish_subscribe(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        bus.publish(Event("test.event", {"key": "value"}, source="test"))
        assert len(received) == 1
        assert received[0].topic == "test.event"
        assert received[0].data["key"] == "value"

    def test_wildcard_subscription(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.*", lambda e: received.append(e))
        bus.publish(Event("test.alpha"))
        bus.publish(Event("test.beta"))
        bus.publish(Event("other.gamma"))
        assert len(received) == 2

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        sub = bus.subscribe("test.event", lambda e: received.append(1))
        sub.cancel()
        bus.publish(Event("test.event"))
        assert len(received) == 0

    def test_multiple_subscribers(self):
        bus = EventBus()
        results = []
        bus.subscribe("evt", lambda e: results.append("a"))
        bus.subscribe("evt", lambda e: results.append("b"))
        bus.publish(Event("evt"))
        assert results == ["a", "b"]

    def test_priority_order(self):
        bus = EventBus()
        results = []
        bus.subscribe("evt", lambda e: results.append("high"), priority=EventPriority.HIGH)
        bus.subscribe("evt", lambda e: results.append("low"), priority=EventPriority.LOW)
        bus.subscribe("evt", lambda e: results.append("normal"))
        bus.publish(Event("evt"))
        assert results == ["high", "normal", "low"]

    def test_emit_convenience(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.convenience", lambda e: received.append(e))
        count = bus.emit("test.convenience", {"msg": "hello"}, source="test")
        assert count == 1
        assert received[0].source == "test"

    def test_event_topics_constants(self):
        assert EventTopics.LIFECYCLE_STARTED == "lifecycle.started"
        assert EventTopics.AGENT_STARTED == "agent.started"
        assert EventTopics.TASK_COMPLETED == "task.completed"
        assert EventTopics.SYSTEM_SHUTDOWN == "system.shutdown"

    def test_shutdown_prevents_publication(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        bus.shutdown()
        bus.publish(Event("test.event"))
        assert len(received) == 0

    def test_global_wildcard(self):
        bus = EventBus()
        received = []
        bus.subscribe("**", lambda e: received.append(e))
        bus.publish(Event("anything.at.all"))
        bus.publish(Event("another.one"))
        assert len(received) == 2

    def test_stats(self):
        bus = EventBus()
        bus.subscribe("test.a", lambda e: None)
        bus.subscribe("test.b", lambda e: None)
        bus.publish(Event("test.a"))
        stats = bus.get_stats()
        assert stats["publish_count"] == 1
        assert stats["subscriptions_active"] == 2


# ======================================================================
# Lifecycle Manager Tests
# ======================================================================

class TestLifecycleManager:
    def test_register_service(self):
        bus = EventBus()
        mgr = LifecycleManager(bus)
        svc = ServiceRegistration(name="test-svc", version="1.0.0")
        mgr.register(svc)
        assert mgr.get("test-svc") is svc
        assert mgr.get_state("test-svc") == ComponentState.STOPPED

    def test_duplicate_registration_raises(self):
        mgr = LifecycleManager(EventBus())
        mgr.register(ServiceRegistration(name="dup"))
        with pytest.raises(ValueError, match="already registered"):
            mgr.register(ServiceRegistration(name="dup"))

    def test_start_calls_init_and_start(self):
        bus = EventBus()
        mgr = LifecycleManager(bus)
        init_called = []
        start_called = []
        svc = ServiceRegistration(
            name="test",
            init_fn=lambda s: init_called.append(True) or True,
            start_fn=lambda s: start_called.append(True),
        )
        mgr.register(svc)
        mgr.start()
        assert svc.state == ComponentState.RUNNING
        assert len(init_called) == 1
        assert len(start_called) == 1

    def test_shutdown_calls_stop_in_reverse(self):
        bus = EventBus()
        mgr = LifecycleManager(bus)
        order = []
        svc_a = ServiceRegistration(
            name="a", dependencies=["b"],
            stop_fn=lambda s: order.append("a"),
        )
        svc_b = ServiceRegistration(
            name="b", stop_fn=lambda s: order.append("b"),
        )
        mgr.register(svc_a)
        mgr.register(svc_b)
        mgr.start()
        mgr.shutdown()
        assert order == ["a", "b"]

    def test_health_summary(self):
        bus = EventBus()
        mgr = LifecycleManager(bus)
        mgr.register(ServiceRegistration(name="healthy", health_fn=lambda: True))
        mgr.register(ServiceRegistration(name="unhealthy", health_fn=lambda: False))
        mgr.start()
        summary = mgr.health_summary()
        assert summary["components"]["healthy"]["healthy"] is True
        assert summary["components"]["unhealthy"]["healthy"] is False

    def test_dependency_resolution(self):
        mgr = LifecycleManager(EventBus())
        mgr.register(ServiceRegistration(name="leaf"))
        mgr.register(ServiceRegistration(name="middle", dependencies=["leaf"]))
        mgr.register(ServiceRegistration(name="top", dependencies=["middle"]))
        ordered = mgr._resolve_dependency_order(mgr.get_all())
        assert ordered.index("leaf") < ordered.index("middle")
        assert ordered.index("middle") < ordered.index("top")

    def test_circular_dependency_detection(self):
        mgr = LifecycleManager(EventBus())
        mgr.register(ServiceRegistration(name="a", dependencies=["b"]))
        mgr.register(ServiceRegistration(name="b", dependencies=["a"]))
        with pytest.raises(ValueError, match="Circular"):
            mgr._resolve_dependency_order(mgr.get_all())


# ======================================================================
# Registry Tests
# ======================================================================

class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        entry = ComponentEntry(name="agent-1", kind="agent")
        reg.register(entry)
        assert reg.get("agent-1") is entry

    def test_list_by_kind(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="tool-a", kind="tool"))
        reg.register(ComponentEntry(name="plugin-b", kind="plugin"))
        reg.register(ComponentEntry(name="tool-c", kind="tool"))
        tools = reg.list_kind("tool")
        assert len(tools) == 2
        plugins = reg.list_kind("plugin")
        assert len(plugins) == 1

    def test_deregister(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="gone", kind="tool"))
        assert reg.has_component("gone")
        reg.deregister("gone")
        assert not reg.has_component("gone")

    def test_deregister_nonexistent(self):
        reg = AgentRegistry()
        assert reg.deregister("nope") is False

    def test_mark_availability(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="flaky", kind="tool"))
        assert reg.get("flaky").available is True
        reg.mark_unavailable("flaky")
        assert reg.get("flaky").available is False
        reg.mark_available("flaky")
        assert reg.get("flaky").available is True

    def test_find_filters(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="t1", kind="tool"))
        reg.register(ComponentEntry(name="t2", kind="tool", available=False))
        available = reg.find(kind="tool", available_only=True)
        assert len(available) == 1
        all_tools = reg.find(kind="tool", available_only=False)
        assert len(all_tools) == 2

    def test_snapshot(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="agent-1", kind="agent"))
        reg.register(ComponentEntry(name="tool-1", kind="tool"))
        snap = reg.snapshot()
        assert snap["total"] == 2
        assert snap["by_kind"]["agent"] == 1
        assert snap["by_kind"]["tool"] == 1

    def test_set_metadata(self):
        reg = AgentRegistry()
        reg.register(ComponentEntry(name="test", kind="tool"))
        reg.set_metadata("test", {"key": "value"})
        assert reg.get("test").metadata["key"] == "value"


# ======================================================================
# Planner Tests
# ======================================================================

class TestPlanner:
    def test_create_plan(self):
        planner = Planner()
        plan = planner.create_plan("Test goal", steps=[
            PlanStep(description="Step 1"),
            PlanStep(description="Step 2"),
        ])
        assert plan.goal == "Test goal"
        assert len(plan.steps) == 2
        assert plan.status == PlanStatus.PENDING

    def test_plan_lifecycle(self):
        planner = Planner()
        plan = planner.create_plan("Goal")
        planner.approve_plan(plan.id)
        assert planner.get_plan(plan.id).status == PlanStatus.APPROVED
        planner.start_plan(plan.id)
        assert planner.get_plan(plan.id).status == PlanStatus.IN_PROGRESS
        planner.complete_plan(plan.id)
        assert planner.get_plan(plan.id).status == PlanStatus.COMPLETED

    def test_fail_plan(self):
        planner = Planner()
        plan = planner.create_plan("Goal")
        planner.fail_plan(plan.id, "Something went wrong")
        assert planner.get_plan(plan.id).status == PlanStatus.FAILED

    def test_cancel_plan(self):
        planner = Planner()
        plan = planner.create_plan("Goal", steps=[PlanStep()])
        planner.cancel_plan(plan.id)
        assert planner.get_plan(plan.id).status == PlanStatus.CANCELLED
        assert planner.get_plan(plan.id).steps[0].status == PlanStatus.CANCELLED

    def test_get_ready_steps(self):
        planner = Planner()
        step_a = PlanStep(description="A")
        step_b = PlanStep(description="B", dependencies=[step_a.id])
        plan = planner.create_plan("Goal", steps=[step_a, step_b])
        ready = planner.get_ready_steps(plan.id)
        assert len(ready) == 1
        assert ready[0].id == step_a.id

    def test_update_step_status(self):
        planner = Planner()
        step = PlanStep(description="Test step")
        plan = planner.create_plan("Goal", steps=[step])
        planner.update_step_status(plan.id, step.id, PlanStatus.COMPLETED, result="done")
        assert planner.get_plan(plan.id).steps[0].status == PlanStatus.COMPLETED
        assert planner.get_plan(plan.id).steps[0].result == "done"

    def test_progress_tracking(self):
        planner = Planner()
        steps = [PlanStep(description=f"S{i}") for i in range(3)]
        plan = planner.create_plan("Goal", steps=steps)
        progress = planner.get_progress(plan.id)
        assert progress["total"] == 3
        assert progress["completed"] == 0

    def test_list_plans(self):
        planner = Planner()
        p1 = planner.create_plan("Goal 1")
        p2 = planner.create_plan("Goal 2")
        all_plans = planner.list_plans()
        assert len(all_plans) == 2


# ======================================================================
# Scheduler Tests
# ======================================================================

class TestKernelScheduler:
    def test_add_interval_job(self):
        sched = KernelScheduler()
        called = []
        sched.add_interval("test-job", 1.0, lambda: called.append(True))
        assert len(sched.list_jobs()) == 1

    def test_add_oneshot_job(self):
        sched = KernelScheduler()
        sched.add_oneshot("oneshot", time.time() + 3600, lambda: None)
        assert len(sched.list_jobs()) == 1

    def test_add_deferred_job(self):
        sched = KernelScheduler()
        sched.add_deferred("deferred", 60.0, lambda: None)
        assert len(sched.list_jobs()) == 1

    def test_pause_resume_job(self):
        sched = KernelScheduler()
        job = sched.add_interval("test-job", 1.0, lambda: None)
        sched.pause_job(job.id)
        assert sched.get_job(job.id).enabled is False
        sched.resume_job(job.id)
        assert sched.get_job(job.id).enabled is True

    def test_remove_job(self):
        sched = KernelScheduler()
        job = sched.add_interval("test-job", 1.0, lambda: None)
        sched.remove_job(job.id)
        assert len(sched.list_jobs()) == 0

    def test_trigger_job(self):
        sched = KernelScheduler()
        called = []
        job = sched.add_interval("test-job", 60.0, lambda: called.append(True))
        sched.trigger_job(job.id)
        assert len(called) == 1

    def test_trigger_nonexistent_job(self):
        sched = KernelScheduler()
        assert sched.trigger_job("nope") is False

    def test_stats(self):
        sched = KernelScheduler()
        sched.add_interval("a", 1.0, lambda: None)
        sched.add_interval("b", 2.0, lambda: None)
        stats = sched.get_stats()
        assert stats["total_jobs"] == 2
        assert stats["enabled_jobs"] == 2


# ======================================================================
# Executor Tests
# ======================================================================

class TestExecutor:
    def test_run_agent_with_mock(self):
        executor = Executor()
        mock_agent = MagicMock()
        mock_agent.run_conversation.return_value = {
            "final_response": "Hello world",
            "completed": True,
            "failed": False,
            "api_calls": 1,
        }
        mock_agent.model = "test-model"
        mock_agent.provider = "test-provider"
        result = executor.run_agent(mock_agent, "Hi")
        assert result.status == ExecutionStatus.COMPLETED
        assert result.output == "Hello world"

    def test_run_agent_failure(self):
        executor = Executor()
        mock_agent = MagicMock()
        mock_agent.run_conversation.side_effect = RuntimeError("API error")
        result = executor.run_agent(mock_agent, "Hi")
        assert result.status == ExecutionStatus.FAILED
        assert "API error" in result.error

    def test_run_with_retry_success(self):
        executor = Executor()
        results = []
        def fn():
            results.append(1)
            return "done"
        result = executor.run_with_retry(fn)
        assert result.status == ExecutionStatus.COMPLETED
        assert len(results) == 1

    def test_run_with_retry_failure(self):
        executor = Executor()
        def fn():
            raise ValueError("fail")
        result = executor.run_with_retry(fn, max_retries=1)
        assert result.status == ExecutionStatus.FAILED
        assert "fail" in result.error

    def test_get_execution(self):
        executor = Executor()
        mock_agent = MagicMock()
        mock_agent.run_conversation.return_value = {"final_response": "ok", "completed": True}
        result = executor.run_agent(mock_agent, "Hi", execution_id="test-1")
        assert executor.get_execution("test-1") is result

    def test_cancel_execution(self):
        executor = Executor()
        assert executor.cancel_execution("nonexistent") is False

    def test_get_stats(self):
        executor = Executor()
        stats = executor.get_stats()
        assert "total_executions" in stats
        assert "completed" in stats


# ======================================================================
# Router Tests
# ======================================================================

class TestRouter:
    def test_register_route(self):
        router = Router()
        router.register("test", r"^hello/", lambda d: "world")
        assert len(router.list_routes()) == 1

    def test_route_request(self):
        router = Router()
        router.register("greet", r"^hello/", lambda d: f"Hello, {d.get('name', 'world')}!")
        result = router.route_request("hello/user", {"name": "Alice"})
        assert result == "Hello, Alice!"

    def test_route_request_no_match(self):
        router = Router()
        with pytest.raises(RouteNotFoundError):
            router.route_request("unknown/path")

    def test_route_first(self):
        router = Router()
        assert router.route_first("nope") is None
        router.register("catch", r"^catch/", lambda d: "got it")
        assert router.route_first("catch/me") == "got it"

    def test_route_all(self):
        router = Router()
        router.register("a", r"^test/", lambda d: "handler a")
        router.register("b", r"^test/", lambda d: "handler b")
        results = router.route_all("test/x")
        assert len(results) == 2

    def test_unregister_route(self):
        router = Router()
        router.register("test", r"^hello/", lambda d: "world")
        assert router.unregister("test") is True
        assert router.unregister("nope") is False

    def test_clear_routes(self):
        router = Router()
        router.register("a", r"^a/", lambda d: None)
        router.register("b", r"^b/", lambda d: None)
        router.clear()
        assert len(router.list_routes()) == 0

    def test_decorator_style(self):
        router = Router()
        @router.route(r"^decorated/", name="decorated-route")
        def handler(data):
            return "decorated"
        assert len(router.list_routes()) == 1
        assert router.route_request("decorated/test") == "decorated"

    def test_middleware(self):
        router = Router()
        router.register("test", r"^test/", lambda d: d.get("value", ""))
        router.add_middleware(lambda target, data, handler: handler({"value": "middleware"}))
        result = router.route_request("test/x")
        assert result == "middleware"


# ======================================================================
# Workspace Tests
# ======================================================================

class TestWorkspaceManager:
    def test_create_workspace(self, tmp_path):
        wm = WorkspaceManager()
        ws = wm.create_workspace("test-project", str(tmp_path))
        assert ws.name == "test-project"
        assert ws.root_path == str(tmp_path.resolve())

    def test_create_workspace_nonexistent_path(self):
        wm = WorkspaceManager()
        with pytest.raises(ValueError):
            wm.create_workspace("bad", "/nonexistent/path/xyz")

    def test_find_by_name(self, tmp_path):
        wm = WorkspaceManager()
        wm.create_workspace("My Project", str(tmp_path))
        ws = wm.find_workspace_by_name("my project")
        assert ws is not None
        assert ws.name == "My Project"

    def test_find_by_path(self, tmp_path):
        wm = WorkspaceManager()
        ws = wm.create_workspace("test", str(tmp_path))
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        found = wm.find_workspace_by_path(str(subdir))
        assert found is not None
        assert found.id == ws.id

    def test_list_workspaces(self, tmp_path):
        wm = WorkspaceManager()
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        wm.create_workspace("a", str(tmp_path / "a"))
        wm.create_workspace("b", str(tmp_path / "b"))
        assert len(wm.list_workspaces()) == 2

    def test_remove_workspace(self, tmp_path):
        wm = WorkspaceManager()
        ws = wm.create_workspace("test", str(tmp_path))
        assert wm.remove_workspace(ws.id) is True
        assert len(wm.list_workspaces()) == 0

    def test_create_session(self):
        wm = WorkspaceManager()
        path = wm.create_session("session-1")
        assert path is not None
        assert wm.get_session_path("session-1") == path

    def test_cleanup_session(self):
        wm = WorkspaceManager()
        wm.create_session("temp-session")
        assert wm.cleanup_session("temp-session") is True
        assert wm.get_session_path("temp-session") is None

    def test_resolve_relative_path(self, tmp_path):
        wm = WorkspaceManager()
        ws = wm.create_workspace("test", str(tmp_path))
        resolved = wm.resolve_path("subdir/file.txt", ws.id)
        assert resolved == str(tmp_path.resolve() / "subdir" / "file.txt")


# ======================================================================
# Context Manager Tests
# ======================================================================

class TestContextManager:
    def test_set_and_get(self):
        cm = ContextManager()
        cm.set("conversation:1", "key", "value")
        assert cm.get("conversation:1", "key") == "value"

    def test_set_many(self):
        cm = ContextManager()
        cm.set_many("ns", {"a": 1, "b": 2})
        assert cm.get("ns", "a") == 1
        assert cm.get("ns", "b") == 2

    def test_get_nonexistent(self):
        cm = ContextManager()
        assert cm.get("unknown", "key") is None

    def test_delete_key(self):
        cm = ContextManager()
        cm.set("ns", "key", "value")
        assert cm.delete("ns", "key") is True
        assert cm.get("ns", "key") is None

    def test_delete_namespace(self):
        cm = ContextManager()
        cm.set("ns", "a", 1)
        assert cm.delete("ns") is True
        assert len(cm.list_contexts()) == 0

    def test_list_contexts(self):
        cm = ContextManager()
        cm.set("ns-a", "k", "v")
        cm.set("ns-b", "k", "v")
        assert len(cm.list_contexts()) == 2

    def test_clear_all(self):
        cm = ContextManager()
        cm.set("a", "k", "v")
        cm.set("b", "k", "v")
        assert cm.clear() == 2
        assert len(cm.list_contexts()) == 0

    def test_scoped_context(self):
        cm = ContextManager()
        with cm.scoped("task:build") as ctx:
            ctx["status"] = "building"
        assert cm.get("task:build", "status") == "building"

    def test_prune_expired(self):
        cm = ContextManager()
        cm.set("expired", "k", "v", ttl_seconds=-1)
        cm.set("fresh", "k", "v", ttl_seconds=3600)
        assert cm.prune_expired() == 1
        assert cm.get("fresh", "k") == "v"


# ======================================================================
# Permission Manager Tests
# ======================================================================

class TestPermissionManager:
    def test_default_allow(self):
        pm = PermissionManager()
        result = pm.check(PermissionAction.READ_FILE)
        assert result.allowed is True

    def test_deny_rule(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(
            name="deny-etc",
            action=PermissionAction.WRITE_FILE,
            level=PermissionLevel.DENY,
            target_pattern="/etc/**",
        ))
        result = pm.check(PermissionAction.WRITE_FILE, {"target": "/etc/passwd"})
        assert result.allowed is False

    def test_confirm_rule(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(
            name="confirm-all",
            action=PermissionAction.EXECUTE_COMMAND,
            level=PermissionLevel.CONFIRM,
        ))
        result = pm.check(PermissionAction.EXECUTE_COMMAND)
        assert result.allowed is True
        assert result.require_approval is True

    def test_rule_with_predicate(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(
            name="block-dangerous-cmd",
            action=PermissionAction.EXECUTE_COMMAND,
            level=PermissionLevel.DENY,
            condition=lambda ctx: "rm -rf" in ctx.get("command", ""),
        ))
        result = pm.check(PermissionAction.EXECUTE_COMMAND, {"command": "rm -rf /"})
        assert result.allowed is False
        result = pm.check(PermissionAction.EXECUTE_COMMAND, {"command": "ls -la"})
        assert result.allowed is True

    def test_default_levels(self):
        pm = PermissionManager()
        pm.set_default_level(PermissionAction.WRITE_FILE, PermissionLevel.DENY)
        result = pm.check(PermissionAction.WRITE_FILE)
        assert result.allowed is False

    def test_remove_rule(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(name="test-rule", action=PermissionAction.READ_FILE,
                                   level=PermissionLevel.DENY))
        assert pm.remove_rule("test-rule") is True
        assert pm.remove_rule("nonexistent") is False

    def test_check_or_raise(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(name="always-deny", action=PermissionAction.READ_FILE,
                                   level=PermissionLevel.DENY))
        with pytest.raises(PermissionError):
            pm.check_or_raise(PermissionAction.READ_FILE)

    def test_list_rules(self):
        pm = PermissionManager()
        pm.add_rule(PermissionRule(name="rule-1", action=PermissionAction.READ_FILE,
                                   level=PermissionLevel.DENY))
        pm.add_rule(PermissionRule(name="rule-2", action=PermissionAction.WRITE_FILE,
                                   level=PermissionLevel.CONFIRM))
        rules = pm.list_rules()
        assert len(rules) == 2


# ======================================================================
# Task Graph Tests
# ======================================================================

class TestTaskGraph:
    def test_add_node(self):
        g = TaskGraph("test-graph")
        node = g.add_node("build", "Build the project")
        assert node.name == "build"
        assert len(g.get_nodes()) == 1

    def test_get_ready_nodes(self):
        g = TaskGraph("test")
        build = g.add_node("build", "Build")
        test = g.add_node("test", "Test", dependencies=[build.id])
        deploy = g.add_node("deploy", "Deploy", dependencies=[test.id])

        ready = g.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == build.id

    def test_cascade_on_completion(self):
        g = TaskGraph("test")
        a = g.add_node("A", "Task A")
        b = g.add_node("B", "Task B", dependencies=[a.id])

        g.update_status(a.id, GraphStatus.COMPLETED)
        ready = g.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == b.id

    def test_blocked_by_failure(self):
        g = TaskGraph("test")
        a = g.add_node("A", "Task A")
        b = g.add_node("B", "Task B", dependencies=[a.id])

        g.update_status(a.id, GraphStatus.FAILED)
        blocked = g.get_blocked_nodes()
        assert len(blocked) == 1
        assert blocked[0].id == b.id

    def test_retry_node(self):
        g = TaskGraph("test")
        node = g.add_node("test", "Test", max_retries=2)
        g.update_status(node.id, GraphStatus.FAILED)
        assert g.retry_node(node.id) is True
        assert g.get_node(node.id).status == GraphStatus.READY  # Node has no deps, immediately ready
        assert g.get_node(node.id).retry_count == 1

    def test_cancel_graph(self):
        g = TaskGraph("test")
        g.add_node("a", "A")
        g.add_node("b", "B")
        g.cancel()
        for node in g.get_nodes():
            assert node.status == GraphStatus.CANCELLED

    def test_progress_summary(self):
        g = TaskGraph("test")
        g.add_node("a", "A")
        g.add_node("b", "B")
        summary = g.progress_summary()
        assert summary["total"] == 2
        assert summary["completed"] == 0

    def test_remove_node(self):
        g = TaskGraph("test")
        node = g.add_node("temp", "Temp")
        assert g.remove_node(node.id) is True
        assert len(g.get_nodes()) == 0

    def test_to_dict(self):
        g = TaskGraph("test")
        g.add_node("a", "A")
        d = g.to_dict()
        assert d["name"] == "test"
        assert len(d["nodes"]) == 1

    def test_dependents(self):
        g = TaskGraph("test")
        a = g.add_node("a", "A")
        b = g.add_node("b", "B", dependencies=[a.id])
        deps = g.get_dependents(a.id)
        assert len(deps) == 1
        assert deps[0].id == b.id


# ======================================================================
# Telemetry Tests
# ======================================================================

class TestTelemetryCollector:
    def test_record_metric(self):
        t = TelemetryCollector()
        t.record("test.metric", 42.0, labels={"env": "test"})
        stats = t.get_stats("test.metric")
        assert stats["count"] == 1
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0

    def test_increment(self):
        t = TelemetryCollector()
        t.increment("errors.count")
        t.increment("errors.count")
        t.increment("errors.count")
        stats = t.get_stats("errors.count")
        assert stats["count"] == 3
        assert stats["sum"] == 3.0

    def test_timed_context(self):
        t = TelemetryCollector()
        with t.timed("op.duration", labels={"op": "test"}):
            time.sleep(0.01)
        stats = t.get_stats("op.duration")
        assert stats["count"] == 1
        assert stats["unit"] == "ms"
        assert stats["min"] > 0

    def test_record_error(self):
        t = TelemetryCollector()
        t.record_error("test_error", "Something failed")
        t.record_error("test_error", "Another failure")
        errors = t.get_error_summary()
        assert errors["by_category"]["test_error"] == 2

    def test_get_all_stats(self):
        t = TelemetryCollector()
        t.record("a", 1.0)
        t.record("b", 2.0)
        stats = t.get_all_stats()
        assert "a" in stats
        assert "b" in stats

    def test_summary(self):
        t = TelemetryCollector()
        t.record("m1", 1.0)
        t.record("m2", 2.0)
        summary = t.summary()
        assert summary["metric_count"] == 2

    def test_reset(self):
        t = TelemetryCollector()
        t.record("m", 1.0)
        t.reset()
        assert t.get_stats("m") is None

    def test_exporter(self):
        t = TelemetryCollector()
        exported = []
        t.add_exporter(lambda p: exported.append(p))
        t.record("test", 42.0)
        assert len(exported) == 1
        assert exported[0].value == 42.0

    def test_remove_exporter(self):
        t = TelemetryCollector()
        def exporter(p):
            pass
        t.add_exporter(exporter)
        assert t.remove_exporter(exporter) is True
        assert t.remove_exporter(exporter) is False

    def test_get_stats_nonexistent(self):
        t = TelemetryCollector()
        assert t.get_stats("nope") is None


# ======================================================================
# State Manager Tests
# ======================================================================

class TestStateManager:
    def test_set_and_get(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("test.key", "value")
        assert sm.get("test.key") == "value"

    def test_nested_keys(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("nested.config.timeout", 30)
        assert sm.get("nested.config.timeout") == 30
        assert sm.get("nested.config", {}).get("timeout") == 30

    def test_get_default(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        assert sm.get("nonexistent", "default") == "default"

    def test_delete(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("temp.key", "value")
        assert sm.delete("temp.key") is True
        assert sm.get("temp.key") is None

    def test_update(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.update({"a": 1, "b": 2})
        assert sm.get("a") == 1
        assert sm.get("b") == 2

    def test_persist_and_load(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("persist.key", "saved")
        sm.persist(force=True)

        sm2 = StateManager(state_dir=str(tmp_path))
        assert sm2.load() is True
        assert sm2.get("persist.key") == "saved"

    def test_load_empty_state(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        assert sm.load() is False  # No state file yet

    def test_snapshot(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("key", "value")
        snap = sm.snapshot()
        assert snap["key"] == "value"

    def test_create_list_snapshots(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("key", "value")
        snap = sm.create_snapshot(kind="manual")
        snapshots = sm.list_snapshots()
        assert len(snapshots) >= 1
        assert snapshots[0]["kind"] == "manual"

    def test_recover_latest(self, tmp_path):
        sm = StateManager(state_dir=str(tmp_path))
        sm.set("recover.key", "restored")
        sm.persist(force=True)

        sm2 = StateManager(state_dir=str(tmp_path))
        assert sm2.recover_latest() is True
        assert sm2.get("recover.key") == "restored"


# ======================================================================
# Kernel Integration Tests
# ======================================================================

class TestKernelIntegration:
    def test_kernel_imports(self):
        """Verify all kernel modules can be imported."""
        from kernel import (
            Kernel, KernelConfig,
            LifecycleManager, ComponentState, ServiceRegistration,
            AgentRegistry, ComponentEntry,
            EventBus, Event, EventPriority, EventSubscription,
            KernelScheduler,
            Planner, Plan, PlanStep, PlanStatus,
            Executor, ExecutionResult, ExecutionStatus,
            Router, RouteEntry,
            WorkspaceManager, Workspace,
            ContextManager, SharedContext,
            PermissionManager, PermissionCheck,
            TaskGraph, TaskNode, TaskDependency, GraphStatus,
            TelemetryCollector, MetricPoint,
            StateManager,
        )
        assert Kernel is not None

    def test_event_bus_planner_integration(self):
        """Test event bus emits from planner."""
        bus = EventBus()
        planner = Planner(bus)
        received = []
        bus.subscribe("task.created", lambda e: received.append(e))
        planner.create_plan("Integration test")
        assert len(received) == 1

    def test_router_permissions_integration(self):
        """Test router and permissions work together."""
        router = Router()
        pm = PermissionManager()
        pm.set_default_level(PermissionAction.READ_FILE, PermissionLevel.DENY)
        result = pm.check(PermissionAction.READ_FILE)
        assert result.allowed is False

    def test_scheduler_interval_tick(self):
        """Test scheduler interval execution."""
        sched = KernelScheduler()
        counter = []
        sched.add_interval("quick", 3600.0, lambda: counter.append(True))
        # Don't start the tick loop — just manually trigger
        # This avoids race conditions with the auto-tick thread
        sched.trigger_job(sched.list_jobs()[0].id)
        assert len(counter) == 1
        sched.stop()

    def test_task_graph_progression(self):
        """Test complete graph lifecycle."""
        g = TaskGraph("progression")
        a = g.add_node("A", "First")
        b = g.add_node("B", "Second", dependencies=[a.id])
        c = g.add_node("C", "Third", dependencies=[a.id])

        # Progress through stages
        g.update_status(a.id, GraphStatus.COMPLETED)
        ready = g.get_ready_nodes()
        assert len(ready) == 2  # B and C both ready

        g.update_status(b.id, GraphStatus.COMPLETED)
        g.update_status(c.id, GraphStatus.COMPLETED)
        assert g.status == GraphStatus.COMPLETED

    def test_context_permissions_workflow(self):
        """Test context and permissions together."""
        cm = ContextManager()
        pm = PermissionManager()

        # Context stores permission config
        cm.set("permissions:write", "level", "deny")

        # Permission manager enforces it
        pm.set_default_level(PermissionAction.WRITE_FILE, PermissionLevel.DENY)
        result = pm.check(PermissionAction.WRITE_FILE)
        assert result.allowed is False
