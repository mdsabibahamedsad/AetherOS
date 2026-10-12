"""Budgets, spawn protection, approvals, circuit breaker (P46, P53-62)."""

import pytest

from agent.orchestration.circuit_breaker import BreakerOpen, CircuitBreaker
from agent.orchestration.swarm import (
    ApprovalBoard,
    CONSEQUENTIAL_EFFECTS,
    GlobalBudget,
    NodeBudget,
    SwarmOrchestrator,
    _BudgetExceeded,
)
from agent.orchestration.types import TaskResult


def _ok(ctx):
    return TaskResult(task_id=ctx["node"].node_key, success=True,
                      summary="done: " + ctx["node"].objective)


# -- budgets -----------------------------------------------------------------

def test_node_budget_enforcement():
    b = NodeBudget(max_tool_calls=2)
    b.consume(tool_calls=2)
    with pytest.raises(_BudgetExceeded):
        b.consume(tool_calls=1)
    t = NodeBudget(max_time_seconds=1.0, started_at=1.0)
    with pytest.raises(_BudgetExceeded):
        t.consume(at=5.0)


def test_global_budget_child_cannot_exceed_parent():
    gb = GlobalBudget(total_tool_calls=10, remaining_tool_calls=10)
    assert gb.allocate("a", 6) is True
    assert gb.allocate("b", 6) is False      # would exceed pool
    assert gb.allocate("b", 4) is True
    # P58 — only orchestrator rebalances unused allocation
    released = gb.release_unused("a")
    assert released == 6 and gb.remaining_tool_calls == 6


# -- spawn protection ------------------------------------------------------------

def _orch(**kw):
    return SwarmOrchestrator(executors={}, **kw)


def test_recursive_spawn_depth_cap():
    o = _orch()
    root = o.spawn_child(
        __import__("agent.orchestration.swarm_guards",
                   fromlist=["ExecutionIdentity"]).ExecutionIdentity(
            agent_id="root", execution_id="e0", parent_execution_id="",
            task_id="T", user_context="u"),
        child_agent="child", child_execution="e1", task_id="T",
        parent_depth=1,
    )
    from agent.orchestration.swarm_guards import ImpersonationBlocked

    with pytest.raises(ImpersonationBlocked):
        o.spawn_child(root, child_agent="grandchild",
                      child_execution="e2", task_id="T", parent_depth=3)


def test_swarm_size_cap():
    o = _orch(max_agents_per_task=1)
    from agent.orchestration.swarm_guards import ExecutionIdentity

    root = ExecutionIdentity(agent_id="r", execution_id="e0",
                             parent_execution_id="", task_id="T",
                             user_context="u")
    o._active_agents = 1
    with pytest.raises(RuntimeError):
        o.spawn_child(root, child_agent="x", child_execution="e1",
                      task_id="T", parent_depth=1)


# -- approvals ---------------------------------------------------------------------

def test_approval_fail_closed_and_single_use():
    board = ApprovalBoard(default_ttl_seconds=100)
    rid = board.request(action="side_effect:DEPLOY", task_id="n1",
                        requested_by="coding")
    # no decision -> not authorized
    assert board.authorize(action="side_effect:DEPLOY", task_id="n1",
                           requester="coding") is False
    board.decide(rid, approved_by="user-1", approve=True)
    assert board.authorize(action="side_effect:DEPLOY", task_id="n1",
                           requester="coding") is True
    # single-use scope consumed
    assert board.authorize(action="side_effect:DEPLOY", task_id="n1",
                           requester="coding") is False


def test_approval_expiration_blocks_new_actions():
    import time as _time

    board = ApprovalBoard()
    rid = board.request(action="side_effect:SEND", task_id="n2",
                        requested_by="mailer")
    board.decide(rid, approved_by="user-1", approve=True, ttl_seconds=-1)
    assert board.authorize(action="side_effect:SEND", task_id="n2",
                           requester="mailer") is False


def test_denial_is_recorded_and_never_authorizes():
    board = ApprovalBoard()
    rid = board.request(action="side_effect:PURCHASE", task_id="n3",
                        requested_by="shopper")
    assert board.decide(rid, approved_by="user-1", approve=False) is False
    assert board.authorize(action="side_effect:PURCHASE", task_id="n3",
                           requester="shopper") is False


# -- circuit breaker ---------------------------------------------------------------

def test_circuit_breaker_transitions():
    br = CircuitBreaker("provider-x", policy=__import__(
        "agent.orchestration.circuit_breaker",
        fromlist=["BreakerPolicy"]).BreakerPolicy(threshold=2,
                                                  cooldown_seconds=0.05))

    def boom():
        raise RuntimeError("down")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            br.call(boom)
    assert br.state.value == "open"
    with pytest.raises(BreakerOpen):
        br.call(lambda: "nope")            # fail fast
    import time as _t

    _t.sleep(0.06)                          # half-open window
    assert br.call(lambda: "ok") == "ok"   # probe closes it
    assert br.state.value == "closed"


# -- side-effect map ---------------------------------------------------------------

def test_consequential_set_covers_spec():
    for eff in ("DELETE", "SEND", "PUBLISH", "PURCHASE", "EXECUTE",
                "INSTALL", "DEPLOY"):
        assert eff in CONSEQUENTIAL_EFFECTS
    assert "READ" not in CONSEQUENTIAL_EFFECTS
    assert "ANALYZE" not in CONSEQUENTIAL_EFFECTS
