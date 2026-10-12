"""Tests for the AetherOS intelligence operating layer.

Pure unit tests: stdlib only, no network, no model calls. Run via
scripts/run_tests.sh tests/agent/test_operating_layer.py -q
"""

import os

from aetheros_automation.models.models import AgentRole, RiskLevel, TaskStatus

from agent.operating_layer import (
    EVENT_KINDS,
    MAX_AGENTS_PER_PLAN,
    ROLE_CAPABILITIES,
    GuardDecision,
    PlanStep,
    TimelineEvent,
    ToolMeta,
    VerificationCheck,
    build_result,
    build_timeline,
    check_file_contains,
    check_file_exists,
    completion_allowed,
    guard_tool_call,
    is_retryable,
    new_event,
    parse_intent,
    plan_from_intent,
    select_agents,
    store_artifact,
    verify_outcome,
)


def test_parse_intent_coding_request():
    intent = parse_intent("Fix the login bug in the repository and run tests")
    assert "coding" in intent.domains
    assert AgentRole.CODING in intent.suggested_roles
    assert AgentRole.QA in intent.suggested_roles  # verification pairing
    assert intent.objective


def test_parse_intent_destructive_flags_approval():
    intent = parse_intent("Delete the old deployment directory")
    assert intent.needs_approval
    assert intent.risk_signals


def test_parse_intent_empty_request_is_explicit():
    intent = parse_intent("   ")
    assert intent.objective == "(empty request)"


def test_plan_has_ordered_phases_with_dependencies():
    plan = plan_from_intent(parse_intent("Research the best vector database and report"))
    assert len(plan.steps) >= 8
    ids = {s.id for s in plan.steps}
    for step in plan.steps[1:]:
        assert step.dependencies, f"{step.id} must declare dependencies"
        for dep in step.dependencies:
            assert dep in ids
    assert any(s.execution_mode.value == "human_approval" for s in plan.steps)
    assert any(s.id.endswith("-verify") for s in plan.steps)


def test_plan_dict_shapes_for_orchestrator():
    plan = plan_from_intent(parse_intent("Clean up the project files"))
    shaped = plan.to_orchestrator_dict()
    assert shaped["goal"] == plan.goal
    assert len(shaped["subtasks"]) == len(plan.steps)
    assert all("agent_role" in t and "execution_mode" in t for t in shaped["subtasks"])


def test_select_agents_is_bounded():
    intent = parse_intent("Research, code, browse the docs, email the team, delete drafts")
    roles = select_agents(intent, max_agents=3)
    assert len(roles) <= 3
    assert len(set(roles)) == len(roles)


def test_role_capabilities_reference_real_tools():
    # Every capability tool name must be a non-empty string (registry
    # conformance is enforced at guard time, which fails closed).
    for role, caps in ROLE_CAPABILITIES.items():
        assert caps["tools"], role
        assert caps["permissions"], role
    assert len(ROLE_CAPABILITIES) >= 10


def test_guard_unknown_tool_fails_closed():
    meta = ToolMeta(name="nope_tool", exists=False)
    decision = guard_tool_call("nope_tool", {}, tool_meta=meta)
    assert isinstance(decision, GuardDecision)
    assert decision.denied
    assert decision.requires_approval is False


def test_guard_low_risk_tool_allowed():
    meta = ToolMeta(name="read_file", risk_level="LOW_RISK", permissions=[])
    decision = guard_tool_call("read_file", {"path": "README.md"}, tool_meta=meta)
    assert decision.allowed
    assert not decision.requires_approval


def test_guard_missing_permission_requires_approval():
    meta = ToolMeta(name="terminal", risk_level="LOW_RISK", permissions=["terminal.execute"])
    decision = guard_tool_call("terminal", {"cmd": "ls"}, tool_meta=meta, granted_permissions=[])
    assert not decision.allowed
    assert decision.requires_approval


def test_guard_high_risk_requires_approval_grant():
    meta = ToolMeta(name="terminal", risk_level="HIGH_RISK", permissions=["terminal.execute"],
                    confirmation_required=True)
    denied = guard_tool_call("terminal", {"cmd": "ls"}, tool_meta=meta,
                             granted_permissions=["terminal.execute"])
    assert denied.requires_approval
    granted = guard_tool_call("terminal", {"cmd": "ls"}, tool_meta=meta,
                              granted_permissions=["terminal.execute"],
                              approvals_granted=["terminal"])
    assert granted.allowed


def test_guard_dangerous_args_denied_without_retry():
    meta = ToolMeta(name="terminal", risk_level="LOW_RISK", permissions=[])
    decision = guard_tool_call("terminal", {"cmd": "rm -rf /"}, tool_meta=meta)
    assert decision.denied


def test_guard_path_traversal_denied():
    meta = ToolMeta(name="read_file", risk_level="LOW_RISK", permissions=[])
    decision = guard_tool_call("read_file", {"path": "../../etc/passwd"}, tool_meta=meta)
    assert decision.denied


def test_verify_outcome_requires_required_checks():
    checks = [
        VerificationCheck(id="a", description="a", required=True, passed=True),
        VerificationCheck(id="b", description="b", required=True, passed=False),
        VerificationCheck(id="c", description="c", required=False, passed=False),
    ]
    report = verify_outcome(checks)
    assert not report.passed
    assert report.required_passed == 1
    assert report.required_total == 2


def test_completion_never_assumed():
    passing = verify_outcome([VerificationCheck(id="a", description="a", passed=True)])
    failing = verify_outcome([VerificationCheck(id="a", description="a", passed=False)])
    assert completion_allowed(TaskStatus.RUNNING, passing)
    assert not completion_allowed(TaskStatus.RUNNING, failing)
    assert not completion_allowed(TaskStatus.FAILED, passing)
    assert not completion_allowed(TaskStatus.CANCELLED, passing)


def test_filesystem_checks_are_real(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello aetheros")
    assert check_file_exists(str(target)).passed
    assert check_file_contains(str(target), "aetheros").passed
    assert not check_file_contains(str(target), "missing-needle").passed
    assert not check_file_exists(str(tmp_path / "nope.txt")).passed


def test_timeline_orders_and_sanitizes():
    events = [
        TimelineEvent(ts=3.0, kind="task.completed", label="done"),
        TimelineEvent(ts=1.0, kind="task.created", label="start OPENAI_API_KEY=sk-secret-value"),
        TimelineEvent(ts=2.0, kind="tool.completed", label="tool ran", ref="terminal"),
    ]
    ordered = build_timeline(events)
    assert [e.ts for e in ordered] == [1.0, 2.0, 3.0]
    assert "sk-secret-value" not in ordered[0].label


def test_new_event_rejects_unknown_kinds():
    try:
        new_event("agent.dreamed", "x")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown event kind must raise")
    assert set(EVENT_KINDS) >= {"task.created", "task.completed", "tool.called"}


def test_build_result_derives_from_timeline():
    timeline = [
        TimelineEvent(ts=1.0, kind="agent.started", label="agent up", ref="coder"),
        TimelineEvent(ts=2.0, kind="tool.completed", label="ran tests", ref="terminal"),
        TimelineEvent(ts=3.0, kind="artifact.created", label="wrote report", ref=""),
    ]
    report = verify_outcome([VerificationCheck(id="v", description="v", passed=True)])
    result = build_result(status="completed", summary="All green", report=report,
                          timeline=timeline, artifacts=["report.md"])
    assert result.status == "completed"
    assert "terminal" in result.tools_used
    assert "coder" in result.agents_used
    assert "1/1" in result.verification
    assert result.artifacts == ["report.md"]


def test_retry_policy_never_silent_for_high_risk():
    assert is_retryable("timeout", RiskLevel.LOW)
    assert not is_retryable("timeout", RiskLevel.HIGH)
    assert not is_retryable("timeout", RiskLevel.CRITICAL)
    assert not is_retryable("unknown_weird", RiskLevel.LOW)


def test_store_artifact_uses_caller_storage():
    stored: dict = {}

    def handler(name: str, payload: bytes) -> str:
        stored[name] = payload
        return f"mem://{name}"

    meta = store_artifact(task_id="t-1", name="report.md", payload=b"hi", handler=handler)
    assert stored["report.md"] == b"hi"
    assert meta["task_id"] == "t-1"
    assert meta["location"] == "mem://report.md"
    assert meta["size"] == 2


def test_plan_step_dataclass_importable():
    step = PlanStep(id="s", name="n", detail="d", agent_role=AgentRole.FILE)
    assert step.agent_role == AgentRole.FILE
    assert MAX_AGENTS_PER_PLAN >= 3
    assert os.path.basename(__file__) == "test_operating_layer.py"
