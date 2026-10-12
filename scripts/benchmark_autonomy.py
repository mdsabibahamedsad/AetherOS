"""Autonomy benchmarks (sections 95-96): scheduler overhead, trigger
latency, concurrent runs. Virtual clock (no real waiting). Measured only.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aetheros_autonomy import (
    AutomationService, VirtualClock,
)


def bench_defs(n: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="autobench"))
    clock = VirtualClock(start=1_700_000_000.0)
    svc = AutomationService(root=tmp, clock=clock)
    svc.initialize()
    t0 = time.time()
    for i in range(n):
        svc.create({"name": f"auto-{i}", "trigger": {"kind": "schedule", "schedule": {
            "kind": "interval", "interval_s": 3600.0, "timezone": "UTC", "preview": ""}},
            "workflow": [{"action": "notify", "text": "tick"}],
            "tool_policy": {"tools": []}})
    create_s = time.time() - t0
    # Arm all due and tick.
    for auto in svc._store.list_autos():
        auto.enabled = True
        auto.next_run = clock.now - 1
        svc._store.save_auto(auto)
    t0 = time.time()
    started = svc._sched.tick()
    tick_s = time.time() - t0
    # Trigger latency: single event match over n defs.
    t0 = time.time()
    svc.emit({"kind": "USER_EVENT", "causal": []})
    trig_ms = (time.time() - t0) * 1000.0
    mem_kb = 0.0
    try:
        import psutil
        mem_kb = psutil.Process().memory_info().rss / 1024.0
    except ImportError:
        pass
    return {"n": n, "create_s": round(create_s, 3),
            "tick_s": round(tick_s, 3), "runs_started": len(started),
            "trigger_match_ms": round(trig_ms, 2),
            "rss_kb": round(mem_kb, 1)}


def bench_concurrent(n: int) -> dict:
    from aetheros_autonomy import BackgroundAgentRuntime, RunRecord, RunState
    done = []

    def work(run):
        time.sleep(0.005)
        run.state = RunState.COMPLETED
        done.append(run.run_id)
        return run

    rt = BackgroundAgentRuntime(work_fn=work, max_workers=8)
    t0 = time.time()
    runs = [rt.launch(RunRecord()) for _ in range(n)]
    deadline = time.time() + 60
    while len(done) < n and time.time() < deadline:
        time.sleep(0.02)
    dt = time.time() - t0
    rt.shutdown(wait=True)
    return {"concurrent_runs": n, "completed": len(done),
            "wall_s": round(dt, 3)}


if __name__ == "__main__":
    sizes = [int(a) for a in sys.argv[1:] or [100, 1000]]
    out = {"definitions": [bench_defs(n) for n in sizes],
           "concurrency": [bench_concurrent(n) for n in (10, 50, 100)]}
    print(json.dumps(out, indent=2))
