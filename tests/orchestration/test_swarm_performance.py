"""P92 — orchestration performance measurements with contention-safe
ceilings; correctness asserted alongside timing."""

import time

from agent.orchestration.catalog import get_specialists, select_team
from agent.orchestration.swarm import SwarmOrchestrator
from agent.orchestration.types import TaskResult


def _res(ctx):
    return TaskResult(task_id=ctx["node"].node_key, success=True,
                      summary="ok")


def test_planning_and_agent_startup_latency():
    o = SwarmOrchestrator(executors={"w": _res}, checkpoint_dir=None,
                          sleeper=lambda s: None)
    t0 = time.time()
    for i in range(200):
        o.add_node(f"n{i}", objective=f"objective {i}", agent_id="w",
                   required_capabilities={"FILE_READ"})
    planning_s = time.time() - t0
    assert planning_s < 2.0, f"planning too slow: {planning_s:.2f}s"

    t1 = time.time()
    s = o.run()
    exec_s = time.time() - t1
    assert s["completed"] == 200
    # per-node scheduling overhead amortized well below a second each
    assert exec_s / 200 < 0.05, f"dispatch too slow: {exec_s/200:.4f}s/node"


def test_parallel_efficiency_threads_beat_sequential():
    def make_orch(parallel):
        return SwarmOrchestrator(
            executors={"sleeper": lambda ctx: (
                time.sleep(0.05), _res(ctx))[1]},
            max_parallel=parallel, checkpoint_dir=None,
            sleeper=lambda s: None)

    graph = [(f"p{i}", "sleeper") for i in range(8)]

    seq = SwarmOrchestrator(
        executors={"sleeper": lambda ctx: (time.sleep(0.05), _res(ctx))[1]},
        max_parallel=1, checkpoint_dir=None, sleeper=lambda s: None)
    for k, a in graph:
        seq.add_node(k, objective=k, agent_id=a,
                     required_capabilities={"FILE_READ"})
    t0 = time.time()
    seq.run()
    sequential = time.time() - t0

    par = make_orch(4)
    for k, a in graph:
        par.add_node(k, objective=k, agent_id=a,
                     required_capabilities={"FILE_READ"})
    t1 = time.time()
    par.run()
    parallel = time.time() - t1

    assert parallel < sequential * 0.8, \
        f"no parallel speedup: seq={sequential:.2f}s par={parallel:.2f}s"


def test_team_selection_latency_trivial():
    t0 = time.time()
    for _ in range(500):
        select_team(frozenset({"WEB_SEARCH", "RESEARCH", "TEST_EXECUTE",
                               "CODE_EDIT"}))
    elapsed = time.time() - t0
    assert elapsed < 2.0
    assert len(get_specialists()) == 15
