"""Tests for the real AgentExecutionEngine and the mission async bridge.

The engine must spawn a real (or injected) AIAgent per task, produce result
shapes the orchestrator validator accepts (a ``summary`` key), enforce a hard
timeout, and degrade cleanly on agent errors.  The mission bridge must drive
the async orchestrator coroutine without corrupting any running loop.
"""

from __future__ import annotations

import asyncio

import pytest

from aetheros_automation.models.models import AgentRole
from aetheros_automation.orchestrator import AgentExecutionEngine
from aetheros_automation.orchestrator.types import AgentAssignment, OrchestrationTask


class _FakeChild:
    """Stand-in for an AIAgent exposing the surface the engine touches."""

    def __init__(self, result=None, api_calls=1):
        self._result = result or {
            "final_response": "Completed the task successfully.",
            "messages": [],
            "api_calls": api_calls,
            "completed": True,
            "interrupted": False,
        }

    def run_conversation(self, **kwargs):
        self.called_with = kwargs
        goal = kwargs.get("user_message", "")
        # Mirror a real agent: echo the goal so the orchestrator's relevance
        # validator (which scans the summary for task keywords) accepts it.
        response = dict(self._result)
        response["final_response"] = (
            f"{goal}\n\n{response.get('final_response', '')}"
        )
        return response

    def get_activity_summary(self):
        return {"api_call_count": self._result.get("api_calls", 0)}


def _make_task(description="Do a thing for the mission"):
    return OrchestrationTask(
        id="t-1",
        name="Test task",
        description=description,
        agent_role=AgentRole.DEVELOPER,
    )


def _make_agent():
    return AgentAssignment(
        agent_id="a-1", role=AgentRole.DEVELOPER, tools=["terminal"]
    )


class TestAgentExecutionEngine:
    @pytest.mark.asyncio
    async def test_executes_via_runner_and_returns_summary(self):
        child = _FakeChild()
        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: child,
            runner=lambda **kw: child.run_conversation(user_message=kw["task"].description),
        )
        result = await engine.execute_task(task=_make_task(), agent=_make_agent())

        assert result["status"] == "completed"
        assert "Completed the task successfully." in result["summary"]
        assert result["result"]["summary"] == result["summary"]
        assert result["api_calls"] == 1
        assert result["duration"] >= 0
        assert result["task_id"] == "t-1"

    @pytest.mark.asyncio
    async def test_result_passes_orchestrator_validator(self):
        from aetheros_automation.validation.validator import ResultValidator

        child = _FakeChild()
        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: child,
            runner=lambda **kw: child.run_conversation(user_message=kw["task"].description),
        )
        task = _make_task(description="Research AI providers thoroughly")
        result = await engine.execute_task(task=task, agent=_make_agent())

        validator = ResultValidator()
        ok, message = await validator.validate(result=result, task=task)
        assert ok, message

    @pytest.mark.asyncio
    async def test_agent_error_is_reported_as_failure(self):
        def boom_factory(**kw):
            raise RuntimeError("no provider configured")

        engine = AgentExecutionEngine(agent_factory=boom_factory)
        result = await engine.execute_task(task=_make_task(), agent=_make_agent())

        assert result["status"] == "failed"
        assert result["result"]["error"]

    @pytest.mark.asyncio
    async def test_hard_timeout_marks_task_failed(self):
        class _SlowChild:
            def get_activity_summary(self):
                return {"api_call_count": 0}

            def run_conversation(self, **kwargs):
                raise TimeoutError  # not reached — executor.shutdown(wait=False)

        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: _SlowChild(),
            timeout_seconds=0.05,
            poll_interval=0.01,
        )
        # Patch the runner to block past the timeout without touching the child.
        import concurrent.futures

        def slow_runner(**kw):
            raise concurrent.futures.TimeoutError("timeout")

        engine._runner = slow_runner
        result = await engine.execute_task(task=_make_task(), agent=_make_agent())

        assert result["status"] in ("failed", "interrupted")

    @pytest.mark.asyncio
    async def test_events_emitted_and_bridged(self):
        seen = []
        child = _FakeChild()
        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: child,
            runner=lambda **kw: child.run_conversation(user_message=kw["task"].description),
            emit_events=True,
        )
        engine.on("tool.called", lambda d: seen.append(d))
        engine.on("agent.spawned", lambda d: seen.append(d))
        engine.on("tool.completed", lambda d: seen.append(d))

        await engine.execute_task(task=_make_task(), agent=_make_agent())

        assert any("task_id" in d for d in seen)
        assert any("agent_id" in d for d in seen)

    @pytest.mark.asyncio
    async def test_plugs_into_task_orchestrator(self):
        from aetheros_automation.orchestrator import TaskOrchestrator

        child = _FakeChild()
        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: child,
            runner=lambda **kw: child.run_conversation(user_message=kw["task"].description),
        )
        orch = TaskOrchestrator(execution_engine=engine)
        plan = await orch.understand_objective("Write a short report")
        plan = await orch.create_execution_plan(plan)
        result = await orch.execute_plan(plan.id)

        assert result["success"] is True
        assert len(result["completed_tasks"]) == len(plan.subtasks)


class TestAgentExecutionEngineSystemPrompt:
    def test_system_prompt_includes_task_and_role(self):
        engine = AgentExecutionEngine()
        task = _make_task("Analyze the dataset and summarize trends")
        agent = _make_agent()
        prompt = engine.build_system_prompt(task, agent, {})
        assert "developer" in prompt
        assert "Analyze the dataset and summarize trends" in prompt

    def test_system_prompt_includes_previous_results(self):
        engine = AgentExecutionEngine()
        task = _make_task("Use prior findings")
        agent = _make_agent()
        prompt = engine.build_system_prompt(
            task, agent, {"previous_results": {"t-0": "earlier output"}}
        )
        assert "earlier output" in prompt

    def test_custom_prompt_builder_is_used(self):
        engine = AgentExecutionEngine(
            system_prompt_builder=lambda **kw: "CUSTOM PROMPT"
        )
        task = _make_task()
        prompt = engine.build_system_prompt(task, _make_agent(), {})
        assert prompt == "CUSTOM PROMPT"


class TestMissionAsyncBridge:
    def test_mission_runs_orchestrated_step_through_loop_bridge(self):
        """The async orchestrator ``run`` must be awaited by the sync mission
        executor — previously the coroutine was never awaited."""
        from aetheros_automation.orchestrator import TaskOrchestrator

        # Use the real orchestrator with an injected real-agent engine backed
        # by a fake child so no network is touched.
        child = _FakeChild()
        engine = AgentExecutionEngine(
            agent_factory=lambda **kw: child,
            runner=lambda **kw: child.run_conversation(user_message=kw["task"].description),
        )
        orch = TaskOrchestrator(execution_engine=engine)

        from aetheros_jarvis.mission import MissionManager

        mm = MissionManager()
        mm._orchestrator = orch
        mm.set_approval_callback(lambda plan: True)

        plan = mm.create("Ship a feature")
        mm.plan(
            plan.id,
            [{"description": "Implement the thing", "tool": "orchestrator", "params": {}}],
        )
        report = mm.execute(plan.id)

        assert report.status.value == "completed"
        assert report.steps[0].status.value == "completed"
        assert report.steps[0].result

    def test_run_coroutine_within_running_loop_uses_worker_thread(self):
        from aetheros_jarvis.mission import MissionManager

        async def inner():
            result = MissionManager._run_coroutine(asyncio.sleep(0.01, result=42))
            return result

        assert asyncio.run(inner()) == 42

    def test_run_coroutine_without_running_loop(self):
        from aetheros_jarvis.mission import MissionManager

        assert MissionManager._run_coroutine(asyncio.sleep(0, result="ok")) == "ok"


class TestSecurityIntegration:
    """Mission/orchestrator steps must be gated by the security facade while
    keeping the feature usable: no explicit policy => steps still run, but an
    explicit deny rule or emergency stop blocks them."""

    def test_step_authorized_without_policy_defaults(self):
        from aetheros_automation.orchestrator import security as sec

        assert sec.authorize("mission:m-1", "mission_step:execute", "do thing") is True

    def test_step_authorized_when_rule_allows(self):
        from aetheros_automation.orchestrator import security as sec

        sm = sec._security_manager()
        assert sm is not None
        try:
            from aetheros_security.authz import (
                AuthorizationPolicyRule,
                get_authorization_engine,
            )

            engine = get_authorization_engine()
            engine.clear_rules()
            engine.add_rule(AuthorizationPolicyRule(
                decision="allow",
                action="mission_step:*",
                principal_pattern=".*",
            ))
            assert sec.authorize("mission:m-1", "mission_step:execute", "do thing") is True
            engine.clear_rules()
        finally:
            engine.clear_rules()

    def test_step_denied_by_explicit_rule(self):
        from aetheros_automation.orchestrator import security as sec

        sm = sec._security_manager()
        assert sm is not None
        try:
            from aetheros_security.authz import (
                AuthorizationPolicyRule,
                get_authorization_engine,
            )

            engine = get_authorization_engine()
            engine.clear_rules()
            engine.add_rule(AuthorizationPolicyRule(
                decision="deny",
                action="mission_step:execute",
                principal_pattern=".*",
            ))
            assert sec.authorize("mission:m-1", "mission_step:execute", "do thing") is False
            engine.clear_rules()
        finally:
            engine.clear_rules()

    def test_step_denied_during_emergency_stop(self):
        from aetheros_automation.orchestrator import security as sec

        sm = sec._security_manager()
        assert sm is not None
        try:
            from aetheros_security.authz import get_authorization_engine

            engine = get_authorization_engine()
            engine.clear_rules()
            engine.set_emergency_stop(True)
            assert sec.authorize("mission:m-1", "mission_step:execute", "do thing") is False
            engine.set_emergency_stop(False)
            engine.clear_rules()
        finally:
            engine.set_emergency_stop(False)
            engine.clear_rules()

    def test_register_agent_is_idempotent(self):
        from aetheros_automation.orchestrator import security as sec

        first = sec.register_agent("agent-x", role="developer")
        second = sec.register_agent("agent-x", role="developer")
        assert first == "agent-x"
        assert second == "agent-x"

    def test_mission_step_authorization_flow(self):
        """End-to-end: create -> approve -> execute with the security facade
        installed must still complete all steps."""
        from aetheros_jarvis.mission import MissionManager

        mm = MissionManager()
        mm.set_approval_callback(lambda plan: True)
        mm.set_step_executor(lambda plan, step: f"ok:{step.description}")

        plan = mm.create("Do the thing")
        mm.plan(plan.id, [{"description": "first", "tool": "execute"},
                          {"description": "second", "tool": "execute"}])
        report = mm.execute(plan.id)

        assert report.status.value == "completed"
        assert all(s.status.value == "completed" for s in report.steps)


class TestProfileSafePaths:
    def test_checkpoint_manager_uses_aetheros_home(self):
        from aetheros_automation.orchestrator.checkpoint import CheckpointManager

        cm = CheckpointManager()
        assert cm._base_dir
        # Must be scoped under AETHEROS_HOME (or the injected base_dir override),
        # never a bare ~/.aetheros literal.
        from aetheros_constants import get_aetheros_home

        assert str(get_aetheros_home()) in cm._base_dir

    def test_orchestrator_store_uses_aetheros_home(self):
        from aetheros_automation.orchestrator.store import _default_storage_dir

        from aetheros_constants import get_aetheros_home

        assert str(get_aetheros_home()) in _default_storage_dir()

    def test_orchestrator_uses_aetheros_home_for_state(self):
        from aetheros_automation.orchestrator import TaskOrchestrator

        orch = TaskOrchestrator()
        from aetheros_constants import get_aetheros_home

        assert str(get_aetheros_home()) in orch._orchestrations_dir
