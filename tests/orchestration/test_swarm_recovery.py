"""Recovery: classification→policy, backoff, checkpoint/resume/idempotency,
emergency stop, graceful cancel (P43-51, P84-87)."""

import json

import pytest

from agent.orchestration.swarm import (
    ApprovalBoard,
    NodeBudget,
    SideEffect,
    SwarmOrchestrator,
)
from agent.orchestration.types import FailureType, TaskResult


def _orch(tmp_path, executors):
    return SwarmOrchestrator(
        executors=executors,
        max_parallel=2,
        checkpoint_dir=str(tmp_path / "ckpt"),
        sleeper=lambda s: None,     # no real sleeping in tests
    )


def _node(o, key, agent, **kw):
    return o.add_node(key, objective=kw.pop("objective", key), agent_id=agent,
                      required_capabilities=kw.pop("required_capabilities",
                                                   {"FILE_READ"}),
                      **kw)


# -- retry classification (P44) ------------------------------------------------

def test_transient_failure_retried_then_succeeds(tmp_path):
    attempts = {"n": 0}

    def flaky(ctx):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("provider blip")
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="recovered")

    o = _orch(tmp_path, {"worker": flaky})
    _node(o, "n", "worker")
    summary = o.run()
    assert attempts["n"] == 3
    assert o.nodes["n"].status == "COMPLETED"
    assert summary["completed"] == 1


def test_non_retryable_classes_fail_immediately(tmp_path):
    calls = {"n": 0}

    def denied(ctx):
        calls["n"] += 1
        raise PermissionError("authorization failure")

    o = _orch(tmp_path, {"worker": denied})
    _node(o, "n", "worker")
    o.run()
    assert calls["n"] == 1                     # no blind retry
    assert o.nodes["n"].failure_kind is FailureType.PERMISSION_DENIED


def test_bounded_retry_gives_up_after_cap(tmp_path):
    calls = {"n": 0}

    def always_timeout(ctx):
        calls["n"] += 1
        raise TimeoutError("slow provider")

    o = _orch(tmp_path, {"worker": always_timeout})
    _node(o, "n", "worker")
    o.run()
    assert calls["n"] == 3                     # bounded (initial + 2 retries)
    assert o.nodes["n"].status == "FAILED"


def test_backoff_is_bounded_and_exponential(tmp_path):
    sleeps = []

    def fake_sleep(s):
        sleeps.append(s)

    def fail(ctx):
        raise ConnectionError()

    o = SwarmOrchestrator(executors={"w": fail}, sleeper=fake_sleep,
                          checkpoint_dir=None)
    _node(o, "n", "w")
    o.run()
    assert sleeps == [0.05, 0.1]               # 0.05 * 2^(attempt-1), cap 8


# -- checkpoint / resume (P49-50) -----------------------------------------------

def test_checkpoint_written_and_resume_skips_completed(tmp_path):
    calls = {"expensive": 0}

    def expensive(ctx):
        calls["expensive"] += 1
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="heavy work done")

    def cheap(ctx):
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="cheap")

    o = _orch(tmp_path, {"heavy": expensive, "light": cheap})
    _node(o, "heavy", "heavy")
    _node(o, "light", "light")
    o.run()
    ckpt_path = tmp_path / "ckpt"
    files = list(ckpt_path.glob("swarm-*.json"))
    assert files, "checkpoint must be written"

    # fresh orchestrator replays the same graph from checkpoint
    o2 = _orch(tmp_path, {"heavy": expensive, "light": cheap})
    o2.add_node("heavy", objective="heavy", agent_id="heavy",
                required_capabilities={"FILE_READ"})
    o2.add_node("light", objective="light", agent_id="light",
                required_capabilities={"FILE_READ"})
    restored = o2.restore(str(files[-1]))
    assert restored is True
    heavy_before = calls["expensive"]
    o2.run()
    assert calls["expensive"] == heavy_before   # P50: not repeated


def test_dependency_ordering_sequential_before_parallel(tmp_path):
    order = []

    def make(name):
        def fn(ctx):
            order.append(name)
            return TaskResult(task_id=name, success=True, summary=name)
        return fn

    o = _orch(tmp_path, {"a": make("a"), "b": make("b"), "c": make("c")})
    _node(o, "a", "a")
    _node(o, "b", "b", depends_on=["a"])
    _node(o, "c", "c")                          # independent of a/b
    o.run()
    assert order.index("b") > order.index("a")  # P12: deps respected
    assert set(order) == {"a", "b", "c"}


# -- emergency stop + graceful cancel (P85-86) -----------------------------------

def test_emergency_stop_blocks_consequential_action(tmp_path):
    board = ApprovalBoard()
    rid = board.request(action="side_effect:DEPLOY", task_id="deploy-node",
                        requested_by="deployer")

    def deployer(ctx):
        # node side effect authorization already handled by orchestrator;
        # this only runs when authorized
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="deployed")

    o = SwarmOrchestrator(executors={"deployer": deployer},
                          approval_board=board, checkpoint_dir=None,
                          sleeper=lambda s: None)
    _node(o, "deploy-node", "deployer",
          required_capabilities={"SHELL_EXECUTE"},
          side_effects={SideEffect.DEPLOY})
    o.emergency_stop()                          # P85: freeze approvals+work
    o.run()
    assert o.nodes["deploy-node"].status in ("BLOCKED", "FAILED", "CREATED")


def test_graceful_cancellation_marks_non_terminal_cancelled(tmp_path):
    def worker(ctx):
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="ok")

    o = _orch(tmp_path, {"w": worker})
    _node(o, "done-first", "w")
    _node(o, "never-starts", "w")
    o.cancelled = True                          # simulate user cancel pre-run
    result = o.run()
    assert o.nodes["never-starts"].status == "CANCELLED"


# -- idempotency keys (P51) --------------------------------------------------------

def test_same_objective_same_criteria_same_idempotency_key():
    o = SwarmOrchestrator(executors={}, checkpoint_dir=None)
    n1 = _node(o, "x1", "w", objective="build widget",
               success_criteria=["widget exists"])
    n2 = _node(o, "x2", "w", objective="build widget",
               success_criteria=["widget exists"])
    n3 = _node(o, "x3", "w", objective="build widget",
               success_criteria=["widget signed"])
    assert n1.idempotency_key == n2.idempotency_key
    assert n1.idempotency_key != n3.idempotency_key


# -- timeouts (P43) -----------------------------------------------------------------

def test_deadline_exceeded_marks_timeout(tmp_path):
    import time as _t

    def slow(ctx):
        _t.sleep(0.15)
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="too late")

    o = _orch(tmp_path, {"slow": slow})
    n = _node(o, "n", "slow", deadline_seconds=0.05)
    o.run()
    assert n.failure_kind is FailureType.TIMEOUT
    assert n.status == "FAILED"


def test_budget_exhaustion_marks_resource_exhausted(tmp_path):
    def spender(ctx):
        ctx["budget"].consume(tool_calls=50)
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="spent")

    o = _orch(tmp_path, {"spender": spender})
    n = _node(o, "n", "spender",
              budget=NodeBudget(max_tool_calls=5))
    o.run()
    assert n.failure_kind is FailureType.RESOURCE_EXHAUSTED
