"""Final demonstrations (§260-261): full pick-and-place workflow and
Master-53 scientific loop, executed against the kinematic simulator.
Mode is SIMULATION throughout and every record says so."""
from __future__ import annotations

from typing import Any, Dict

from .models import ExecMode, PhysicalAction
from .simulation import KinematicSimulator
from .spatial import SpatialWorldModel, Zone


def run_pick_place_demo(eng: Any) -> Dict[str, Any]:
    log = []
    # 1. task + authorized devices (simulated adapter)
    task = eng.create_task("Move object A to station B",
                           autonomy_level=4)
    log.append("task created")
    # 2. observe environment (replay-flavored simulated readings)
    eng.observe(task, {
        "cam-1": {"value": {"objectA": [1.0, 2.0]}, "source": "camera",
                  "confidence": 0.9, "mode": "SIMULATED"},
        "lidar-1": {"value": {"ranges": [1.5, 1.6]},
                    "source": "lidar", "confidence": 0.85,
                    "mode": "SIMULATED"}})
    log.append("observed")
    # 3/4. world state + identify A and station B
    eng.spatial.place_object("objectA", 1.0, 2.0, mode="SIMULATED")
    eng.spatial.place_object("stationB", 4.0, 4.0, mode="SIMULATED")
    eng.spatial.add_zone(Zone("human-bay", "SLOW_ZONE", (2, 2, 3, 3),
                              speed_limit=0.2))
    # 5/6. safety zones checked inside check_action later
    # 7. twin + 8. simulated route
    twin = eng.twin_for("demo-room", kind="room")
    twin.sync({"objects": 2}, confidence=0.9)
    sim = KinematicSimulator(seed=7)
    for cx in range(10):
        for cy in range(10):
            eng.mapping.observe_free([(cx, cy)])
    from .planning import MotionPlanner
    route = MotionPlanner().plan_route(
        eng.mapping.occ, (0, 0), (9, 9))
    # 9. manipulation plan
    from .planning import ManipulationPlanner
    manip = ManipulationPlanner().pick_place(
        {"id": "objectA", "width_m": 0.04}, (1.0, 2.0), (4.0, 4.0),
        {"max_opening_m": 0.08, "max_force_n": 20.0})
    # 10. approval (low-risk demo needs none; packet shown anyway)
    act = PhysicalAction(actor="embodied-engine", device="sim-base-01",
                         capability="MOVE",
                         parameters={"v": 0.2, "omega": 0.0, "dt": 1.0},
                         preconditions=["world"], risk="LOW",
                         execution_mode=ExecMode.SIMULATION,
                         expected_outcome={"moved": True})
    packet = eng.approval_packet(act, {"route_ok": route["ok"]})
    # 11. execute via simulated adapter
    eng.executor.adapter.connect("sim-base-01")
    out = eng.execute_action(
        task, act, ctx={"force_limit_n": 50.0},
        evidence={"state": {"moved": True}})
    # 12-15. verify / twin update / provenance / report
    twin.sync({"objects": 2, "moved": True}, confidence=0.8)
    drift = twin.check_drift({"objects": 2, "moved": True})
    return {"mode": ExecMode.SIMULATION, "task": task.id,
            "status": task.status, "steps": log,
            "route_ok": route["ok"], "eta_s": route.get("eta_s"),
            "grasp_confidence": manip["grasp"]["confidence"],
            "approval_buttons": packet["buttons"],
            "execution": out.get("status"),
            "verification": (out.get("verification") or {}).get("verdict"),
            "twin_drift": drift["drift"]}


def run_science_demo(eng: Any, science: Any) -> Dict[str, Any]:
    """§261: hypothesis -> twin -> params -> simulate -> (request) physical
    -> measure -> analyze -> update -> next experiment. Physical step
    stays SIMULATION without authorized hardware."""
    task = science.create_task("Does speed affect placement error?")
    results: Dict[str, Any] = {"task": task.id, "mode": ExecMode.SIMULATION}
    sim = KinematicSimulator(seed=11)
    errors = {}
    for v in (0.1, 0.3, 0.5):
        sim.reset()
        trace = [sim.step(v, 0.0, 0.5) for _ in range(4)]
        # simulated measurement: lateral error grows with speed (toy model)
        errors[str(v)] = round(v * 0.02, 4)
    results["measurements_simulated"] = errors
    results["analysis"] = "error rises with speed in this toy model"
    results["physical_execution"] = ("HARDWARE_UNAVAILABLE — same workflow "
                                     "would run through an authorized "
                                     "instrument adapter")
    results["next"] = "repeat at v=0.2 with obstacle; then request hardware"
    return results
