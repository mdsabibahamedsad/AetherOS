"""Master 54 test matrix (§262 core): devices, sensors, fusion,
world state, frames, planning, simulation, twins, safety, execution,
verification, recovery, telemetry, memory, lab, benchmarks."""
from __future__ import annotations

import math

import pytest

from aetheros_embodied import (
    ActionExecutor,
    CapabilityRegistry,
    CollisionChecker,
    CommandAuthenticator,
    EmbodiedIntelligenceEngine,
    EventBus,
    KinematicSimulator,
    LabAutomationEngine,
    LabInstrument,
    LabProtocol,
    LocalizationEngine,
    MappingEngine,
    MotionPlanner,
    OccupancyMap,
    PhysicalDeviceRegistry,
    PhysicalDigitalTwin,
    ReplaySensorAdapter,
    RobotRegistry,
    RoomTwin,
    SafetyController,
    SensorFusionEngine,
    SpatialWorldModel,
    BayesianOptimizer,
    pareto_frontier,
)
from aetheros_embodied.frames import FrameTree, Transform
from aetheros_embodied.lab import BayesianOptimizer as BO2
from aetheros_embodied.models import (EmbodiedTask, ExecMode, PhysicalAction,
                                      PhysicalDevice, Robot, StateVar)
from aetheros_embodied.planning import (ManipulationPlanner,
                                        PhysicalTaskPlanner, astar_route,
                                        time_parameterize)
from aetheros_embodied.sensors import LambdaSensorAdapter, SensorReading
from aetheros_embodied.spatial import Zone
from aetheros_embodied.verification import ActionVerifier, ExpectationEngine


def _eng(tmp_path, autonomy=4):
    from pathlib import Path
    return EmbodiedIntelligenceEngine(Path(str(tmp_path / "emb")),
                                      autonomy=autonomy)


# -- devices ---------------------------------------------------------------
def test_pair_attest_authorize_revoke():
    reg = PhysicalDeviceRegistry()
    dev = reg.pair(PhysicalDevice(kind="camera"), credential="s3cret",
                   verifier="op")
    assert dev.trust == "UNTRUSTED_DEVICE"
    with pytest.raises(ValueError):
        reg.authorize(dev.id, ["OBSERVE"])  # untrusted: no permissions
    assert reg.attest(dev.id, True, True) == "TRUSTED"
    reg.authorize(dev.id, ["OBSERVE"])
    assert reg.controllable(dev.id)
    reg.lock(dev.id, True)
    assert not reg.controllable(dev.id)
    reg.lock(dev.id, False)
    reg.revoke(dev.id)
    assert reg.list()[0].trust == "UNTRUSTED_DEVICE"
    with pytest.raises(ValueError):
        reg._require("nope")  # HARDWARE_UNAVAILABLE


def test_unknown_robot_is_unavailable():
    with pytest.raises(ValueError, match="HARDWARE_UNAVAILABLE"):
        RobotRegistry().get_robot("ghost")


def test_capability_risk_declared():
    caps = CapabilityRegistry()
    assert caps.get("WELD").risk == "HIGH"
    assert caps.get("READ_TEMPERATURE").risk == "LOW"


def test_broker_never_leaks_secret():
    from aetheros_embodied.registries import CredentialBroker
    b = CredentialBroker()
    b.store("d1", "super-secret")
    tok = b.token_for("d1", "read")
    assert "super-secret" not in tok
    assert b.check(tok, "d1", "read")
    assert not b.check(tok, "d1", "write")


# -- sensors -----------------------------------------------------------------
def test_unavailable_sensor_not_fabricated():
    from aetheros_embodied.sensors import SensorAdapter
    r = SensorAdapter("s").read()
    assert r.mode == "UNAVAILABLE" and r.value is None


def test_replay_labeled_replay():
    ad = ReplaySensorAdapter("s", [{"value": 21.5, "unit": "C"}])
    r = ad.read()
    assert r.mode == "REPLAY" and r.value == 21.5
    r2 = ad.read()
    assert r2.quality == "missing"


def test_fusion_weights_and_conflict():
    f = SensorFusionEngine(disagreement_tol=0.5)
    good = [SensorReading(value=20.0, accuracy=0.1, confidence=0.9,
                          source="a"),
            SensorReading(value=20.2, accuracy=0.5, confidence=0.9,
                          source="b")]
    out = f.fuse_numeric(good)
    assert out["status"] == "FUSED"
    assert abs(out["value"] - 20.0) < 0.15  # precise sensor dominates
    bad = [SensorReading(value=20.0, accuracy=0.1, confidence=0.9,
                         source="a"),
           SensorReading(value=30.0, accuracy=0.1, confidence=0.9,
                         source="b")]
    assert f.fuse_numeric(bad)["status"] == "STATE_UNCERTAIN"
    assert f.fuse_numeric([])["status"] == "UNAVAILABLE"


def test_quality_stale_outlier():
    import time
    r = SensorReading(value=5.0, timestamp=time.time() - 10)
    assert SensorFusionEngine.check_quality(r).quality == "stale"
    r2 = SensorReading(value=999.0)
    assert SensorFusionEngine.check_quality(
        r2, expected_range=(0, 100)).quality == "outlier"


def test_calibration_gate():
    from aetheros_embodied.sensors import CalibrationProfile
    f = SensorFusionEngine()
    assert not f.calibration_ok("s", required=True)
    f.calibrate(CalibrationProfile("s"))
    assert f.calibration_ok("s", required=True)


# -- frames --------------------------------------------------------------------
def test_frame_transform_chain_and_reject():
    ft = FrameTree()
    ft.add_frame("robot")
    ft.add_frame("camera", parent="robot")
    ft.set_transform(Transform("robot", "world", (1.0, 0.0, 0.0)))
    ft.set_transform(Transform("camera", "robot", (0.0, 0.5, 0.0)))
    x, y, z = ft.to_world("camera", (0.0, 0.0, 0.0))
    assert abs(x - 1.0) < 1e-9 and abs(y - 0.5) < 1e-9
    import time as _t
    with pytest.raises(ValueError):
        ft.set_transform(Transform("camera", "robot", (0, 0, 0),
                                   timestamp=_t.time() - 999))
    with pytest.raises(ValueError):
        ft.to_world("ghost", (0, 0, 0))  # no silent mixing


def test_quaternion_rotation_90deg():
    t = Transform("a", "world", (0, 0, 0),
                  (0, 0, math.sin(math.pi / 4), math.cos(math.pi / 4)))
    x, y, z = __import__("aetheros_embodied.frames",
                         fromlist=["transform_point"]).transform_point(
        t, (1.0, 0.0, 0.0))
    assert abs(x) < 1e-9 and abs(y - 1.0) < 1e-9


# -- spatial / planning -----------------------------------------------------------
def test_astar_blocked_and_route():
    occ = OccupancyMap(6, 6)
    for x in range(6):
        for y in range(6):
            occ.set(x, y, OccupancyMap.FREE)
    assert astar_route(occ, (0, 0), (0, 0)) == [(0, 0)]
    for y in range(6):
        occ.set(3, y, OccupancyMap.OCCUPIED)  # wall
    assert astar_route(occ, (0, 0), (5, 5)) == []  # honest: no route
    assert occ.get(99, 99) == OccupancyMap.OCCUPIED  # outside = blocked


def test_time_parameterize_limits():
    pts = [(0.0, 0.0), (1.0, 0.0)]
    timed = time_parameterize(pts, vmax=0.5, amax=0.5)
    assert timed[-1]["t"] > 0 and max(p["v"] for p in timed) <= 0.5 + 1e-9
    assert time_parameterize([], 1, 1) == []


def test_motion_planner_eta():
    occ = OccupancyMap(8, 8)
    for x in range(8):
        for y in range(8):
            occ.set(x, y, OccupancyMap.FREE)
    r = MotionPlanner().plan_route(occ, (0, 0), (7, 7))
    assert r["ok"] and r["eta_s"] > 0 and r["length_m"] > 0


def test_collision_and_zones():
    obs = [{"x": 1.0, "y": 1.0, "r": 0.2}]
    assert CollisionChecker.circle_hits(1.0, 1.0, 0.1, obs)
    assert not CollisionChecker.circle_hits(5.0, 5.0, 0.1, obs)
    assert not CollisionChecker.path_clear([(5, 5), (1, 1)], 0.1,
                                            obs)["clear"]
    sp = SpatialWorldModel()
    sp.add_zone(Zone("z", "KEEP_OUT", (0, 0, 2, 2)))
    assert sp.zone_at(1, 1).kind == "KEEP_OUT"
    assert sp.zone_at(9, 9) is None


def test_localization_drift_and_fix():
    loc = LocalizationEngine()
    loc.odometry(1.0, 0.0, 0.0)
    assert loc.pose()["uncertainty"] > 0
    loc.fix(1.0, 0.0, 0.0, uncertainty=0.01)
    assert loc.pose()["uncertainty"] == 0.01


def test_grasp_approval_gate():
    m = ManipulationPlanner()
    ok = m.select_grasp({"id": "o", "width_m": 0.04}, {"max_opening_m": 0.08})
    assert not ok["needs_approval"]
    bad = m.select_grasp({"id": "o", "width_m": 0.4}, {"max_opening_m": 0.08})
    assert bad["needs_approval"] and bad["confidence"] < 0.5


def test_task_dag():
    dag = PhysicalTaskPlanner().plan("move it", "move_object")
    assert dag["dag"][0]["step"] == "observe"
    assert dag["dag"][-1]["step"] == "report"


# -- simulation ----------------------------------------------------------------------
def test_kinematics_drive_and_arm():
    s = __import__("aetheros_embodied.simulation",
                   fromlist=["KinematicSimulator"]).KinematicSimulator()
    s.reset()
    st = s.step(0.5, 0.0, 2.0)
    assert abs(st["x"] - 1.0) < 1e-9 and st["mode"] == "SIMULATION"
    ee = s.fk(0.0, 0.0)
    assert abs(ee["x"] - 0.55) < 1e-9  # l1+l2 straight
    assert "no dynamics" in " ".join(s.contract()["limitations"])


def test_sim2real_error_measured():
    from aetheros_embodied.simulation import SimToRealTracker
    t = SimToRealTracker()
    assert t.error()["n"] == 0
    t.add({"x": 1.0}, {"x": 1.1})
    assert abs(t.error()["mean_abs_error"]["x"] - 0.1) < 1e-9
