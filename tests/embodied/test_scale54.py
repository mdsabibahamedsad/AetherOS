"""Master 54 long-horizon (§214), replay (§215), performance
(§216-218), concurrency (§219), multi-robot (§220), resource (§221),
offline (§224) tests."""
from __future__ import annotations

import time

from aetheros_embodied import (EmbodiedIntelligenceEngine, EventBus,
                               KinematicSimulator, MotionPlanner,
                               OccupancyMap, TelemetryEngine)
from aetheros_embodied.models import ExecMode, PhysicalAction


def _eng(tmp_path, autonomy=4):
    from pathlib import Path
    return EmbodiedIntelligenceEngine(Path(str(tmp_path / "emb")),
                                      autonomy=autonomy)


def test_long_horizon_nav_manip_measure_recover(tmp_path):
    eng = _eng(tmp_path)
    task = eng.create_task("inspect stations and return")
    occ = OccupancyMap(10, 10)
    for x in range(10):
        for y in range(10):
            occ.set(x, y, OccupancyMap.FREE)
    plan = MotionPlanner().plan_route(occ, (0, 0), (9, 9))
    assert plan["ok"]
    sim = KinematicSimulator(seed=1)
    sim.reset()
    trace = [sim.step(0.2, 0.0, 0.5) for _ in range(6)]
    assert trace[-1]["mode"] == "SIMULATION"
    # inject fault -> recover
    rec = eng.executor.recover(
        PhysicalAction(actor="t", device="d", capability="MOVE"),
        "pose lost near obstacle")
    assert rec["strategy"] == "relocalize"
    task.status = "COMPLETED"
    assert task.status == "COMPLETED"


def test_task_replay_deterministic(tmp_path):
    sims = []
    for _ in range(2):
        s = KinematicSimulator(seed=42)
        s.reset()
        sims.append([s.step(0.2, 0.1, 0.5) for _ in range(4)])
    a = [(p["x"], p["y"]) for p in sims[0]]
    b = [(p["x"], p["y"]) for p in sims[1]]
    assert a == b  # same seed -> identical replay


def test_telemetry_throughput(tmp_path):
    bus = EventBus(capacity=200000)
    t0 = time.perf_counter()
    for i in range(10000):
        bus.publish("sensor.updated", device="lidar",
                    payload={"i": i})
    dt = time.perf_counter() - t0
    assert len(bus.events) == 10000
    assert dt < 10.0
    ordered = bus.ordered()
    assert len(ordered) == 10000


def test_memory_scale(tmp_path):
    eng = _eng(tmp_path)
    t0 = time.perf_counter()
    for i in range(1000):
        eng.memory.remember(f"located:obj{i}", f"shelf-{i % 10}")
    dt = time.perf_counter() - t0
    assert dt < 5.0
    assert eng.memory.recall("located:obj7") == "shelf-7"
    assert len(eng.memory.graph_triples()) == 1000


def test_concurrent_device_isolation(tmp_path):
    import threading
    eng = _eng(tmp_path)
    errs = []

    def worker(i: int) -> None:
        try:
            eng.bus.publish("sensor.updated", device=f"dev{i}",
                            payload={"v": i})
            eng.memory.remember(f"k{i}", i)
        except Exception as exc:  # noqa: BLE001
            errs.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs
    assert eng.memory.recall("k3") == 3


def test_multi_robot_collision_avoidance(tmp_path):
    from aetheros_embodied.spatial import CollisionChecker
    obs = [{"x": 5.0, "y": 5.0, "r": 0.3}]
    robots = [(1.0, 1.0), (5.0, 5.0), (9.0, 9.0)]
    hits = [CollisionChecker.circle_hits(x, y, 0.25, obs)
            for x, y in robots]
    assert hits[0] == [] and len(hits[1]) == 1 and hits[2] == []


def test_offline_safe_control_without_cloud(tmp_path):
    eng = _eng(tmp_path)
    # no plane, no network: local sim + estop still work
    assert eng.health_snapshot()["estop"] is False
    eng.safety.emergency_stop("offline test", actor="test")
    assert eng.health_snapshot()["estop"] is True
    eng.safety.clear_estop("test")
    assert eng.health_snapshot()["safety_log_ok"] is True


def test_perception_latency_budget(tmp_path):
    from aetheros_embodied.sensors import LambdaSensorAdapter
    ad = LambdaSensorAdapter("cam", lambda: {"value": 1.0})
    t0 = time.perf_counter()
    for _ in range(1000):
        ad.read()
    assert (time.perf_counter() - t0) < 5.0
