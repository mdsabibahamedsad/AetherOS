"""P94 chaos: seeded fault injection — safe recovery invariants hold."""

from agent.orchestration.chaos import ChaosHarness
from agent.orchestration.swarm import SwarmOrchestrator
from agent.orchestration.types import FailureType, TaskResult


def _res(ctx):
    return TaskResult(task_id=ctx["node"].node_key, success=True,
                      summary="completed despite chaos")


def _run_chaos(fail_plan, nodes, *, seed=42, random_rate=0.0):
    o = SwarmOrchestrator(
        executors={a: ChaosHarness(_res, fail_plan=fail_plan, seed=seed,
                                   random_failure_rate=random_rate)
                   for a in nodes["agents"]},
        max_parallel=2,
        checkpoint_dir=None,
        sleeper=lambda s: None,
    )
    for key, agent in nodes["graph"]:
        o.add_node(key, objective=key, agent_id=agent,
                   required_capabilities={"FILE_READ"})
    summary = o.run()
    return o, summary


def test_chaos_planned_failures_recover_safely():
    o, s = _run_chaos(
        fail_plan={("n1", 1): ConnectionError("net"),
                   ("n2", 1): TimeoutError()},
        nodes={"agents": ["w"], "graph": [("n1", "w"), ("n2", "w")]},
    )
    assert s["completed"] == 2
    assert all(n.status == "COMPLETED" and n.attempts >= 1
               for n in o.nodes.values())


def test_chaos_random_storm_never_hangs_and_terminates():
    agents = [f"w{i}" for i in range(3)]
    graph = [(f"task{i}", agents[i % 3]) for i in range(12)]
    o, s = _run_chaos(
        fail_plan={}, nodes={"agents": agents, "graph": graph},
        seed=99, random_rate=0.4,
    )
    # termination + no half-states
    assert s["total"] == 12
    states = {n.status for n in o.nodes.values()}
    assert not ({"RUNNING", "ASSIGNED"} & states)


def test_chaos_permanent_failure_reported_honestly():
    """A node that always fails must end FAILED — never COMPLETED."""

    class AlwaysFails:
        def __call__(self, ctx):
            raise RuntimeError("permanent misconfiguration")

    o = SwarmOrchestrator(executors={"doomed": AlwaysFails()},
                          checkpoint_dir=None, sleeper=lambda s: None)
    n = o.add_node("n", objective="x", agent_id="doomed",
                   required_capabilities={"FILE_READ"})
    o.run()
    assert n.status == "FAILED"
    assert not n.verified


def test_chaos_orchestrator_restart_via_checkpoint(tmp_path):
    calls = {"side": 0}

    def side_effect_task(ctx):
        calls["side"] += 1
        return TaskResult(task_id=ctx["node"].node_key, success=True,
                          summary="side effect executed once")

    ck = tmp_path / "ck"
    o = SwarmOrchestrator(executors={"side": side_effect_task},
                          checkpoint_dir=str(ck), sleeper=lambda s: None)
    o.add_node("only", objective="one-shot", agent_id="side",
               required_capabilities={"FILE_READ"})
    o.run()
    files = list(ck.glob("swarm-*.json"))
    assert files

    # orchestrator "crashes"; a new instance resumes from latest checkpoint
    o2 = SwarmOrchestrator(executors={"side": side_effect_task},
                           checkpoint_dir=str(ck), sleeper=lambda s: None)
    o2.add_node("only", objective="one-shot", agent_id="side",
                required_capabilities={"FILE_READ"})
    assert o2.restore(str(files[-1])) is True
    o2.run()
    # P50/P51: the completed node was NOT re-executed
    assert calls["side"] == 1


def test_failure_type_classification_available():
    assert FailureType.AGENT_ERROR.value == "agent_error"
