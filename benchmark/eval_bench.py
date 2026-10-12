"""EvalBench (§205): real measured eval overhead. Runs the three
built-in suites + trace/redact throughput + experiment comparison.
Prints actual p50/p95-style aggregates. No invented numbers.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from aetheros_self_improvement import SelfImprovementEngine
from aetheros_self_improvement.models import AgentTrace, EvalTask
from aetheros_self_improvement.suites import run_suite


def _time(fn, n=200):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return {"n": n, "p50_ms": round(xs[n // 2], 3),
            "p95_ms": round(xs[int(n * 0.95) - 1], 3)}


def main():
    eng = SelfImprovementEngine(Path(tempfile.mkdtemp()), plane=None,
                                autonomy="I5")
    trace = AgentTrace(task_id="bench", user_intent="benchmark run",
                       final_outcome="ok", agent_identity="bench")
    out = {"trace_record": _time(lambda: eng.traces.record(trace))}
    eng2 = SelfImprovementEngine(Path(tempfile.mkdtemp()), plane=None,
                                 autonomy="I5")
    for name in ("capability", "regression", "security"):
        t0 = time.perf_counter()
        res = run_suite(eng2, name, trials=2)
        out[f"suite_{name}"] = {
            "trials": res["trials"], "passed": res["passed"],
            "hard_gate_failures": res["hard_gate_failures"],
            "wall_ms": round((time.perf_counter() - t0) * 1000, 1)}
    t = EvalTask(id="b", inputs={"text": "Hi"}, expected_outcome="HI",
                 success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    from aetheros_self_improvement.suites import EXECUTORS
    out["experiment_compare"] = _time(
        lambda: eng2.runner.compare(eng2.runner.create(
            [t], {"mode": "upper"}, {"mode": "upper"})), n=50)
    out["drift_observe"] = _time(
        lambda: eng2.drift.observe("latency", "lat", 101.0), n=500)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
