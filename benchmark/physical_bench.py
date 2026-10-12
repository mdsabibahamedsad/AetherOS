"""Physical benchmarks runner: prints real measured numbers from
SIMULATION mode. LIVE_HARDWARE categories report NOT TESTED."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetheros_embodied import (EmbodiedBenchmarkEngine,
                               EmbodiedIntelligenceEngine, KinematicSimulator,
                               MotionPlanner, OccupancyMap)


def main() -> None:
    eng = EmbodiedIntelligenceEngine(Path(tempfile.mkdtemp()))
    bench = EmbodiedBenchmarkEngine("SIMULATION")

    def nav() -> dict:
        occ = OccupancyMap(12, 12)
        for x in range(12):
            for y in range(12):
                occ.set(x, y, OccupancyMap.FREE)
        for x in range(3, 9):
            occ.set(x, 6, OccupancyMap.OCCUPIED)
        r = MotionPlanner().plan_route(occ, (0, 0), (11, 11))
        return {"passed": r["ok"], "eta_s": r.get("eta_s", 0)}

    bench.run("navigation", nav)

    def sim() -> dict:
        s = KinematicSimulator(seed=3)
        s.reset()
        for _ in range(10):
            s.step(0.2, 0.05, 0.1)
        st = s.observe()
        return {"passed": abs(st["x"]) > 0.05, "x": round(st["x"], 3)}

    bench.run("simulation", sim)

    def twin_drift() -> dict:
        t = eng.twin_for("b1")
        t.sync({"x": 1.0})
        d = t.check_drift({"x": 1.2})
        return {"passed": d["drift"] is True, "drift": d["drift"]}

    bench.run("twin_drift", twin_drift)

    def safety_veto() -> dict:
        from aetheros_embodied.models import PhysicalAction
        from aetheros_embodied.spatial import Zone
        eng.spatial.add_zone(Zone("z", "KEEP_OUT", (0, 0, 5, 5)))
        a = PhysicalAction(device="d", capability="MOVE",
                           parameters={"x": 1.0, "y": 1.0}, risk="LOW")
        g = eng.safety.check_action(a)
        return {"passed": g["allowed"] is False}

    bench.run("safety_veto", safety_veto)

    def estop() -> dict:
        eng.safety.emergency_stop("bench", actor="bench")
        ok = eng.safety.e_stop_active
        eng.safety.clear_estop("bench")
        return {"passed": ok and not eng.safety.e_stop_active}

    bench.run("emergency_stop", estop)

    live = EmbodiedBenchmarkEngine("LIVE_HARDWARE")
    live.run("navigation_hw", nav)
    out = {"sim": bench.summary(), "live": live.summary(),
           "safety_log": eng.safety.verify_log()}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
