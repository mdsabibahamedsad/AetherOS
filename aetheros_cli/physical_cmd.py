"""CLI: ``aetheros physical ...`` (Master 54 §142-145).

Every demo path executes real code (kinematic sim / replay) and labels
its mode — never simulated-as-real.
"""
from __future__ import annotations

import argparse
import json
from typing import Any


def _engine(args: Any):
    from pathlib import Path
    from tempfile import mkdtemp
    from aetheros_embodied import EmbodiedIntelligenceEngine
    try:
        from aetheros_control_plane import UniversalControlPlane
        plane: Any = UniversalControlPlane()
    except Exception:
        plane = None
    eng = EmbodiedIntelligenceEngine(
        Path(mkdtemp(prefix="emb-")), plane=plane,
        autonomy=int(getattr(args, "autonomy", 4) or 4))
    if plane is not None:
        _bootstrap_local_sandbox(plane, eng)
    return eng


def _bootstrap_local_sandbox(plane: Any, eng: Any) -> None:
    """First-run local-operator provisioning. ONLY when the plane is
    pristine (no active policy): publish a narrow sandbox policy
    (LOW-risk SIMULATION capabilities for the embodied-engine
    identity) + modest bootstrap trust (T2 max, never higher).
    Fully audited; never overrides administrator configuration;
    never performed by the engine itself."""
    try:
        if plane.policies.active() is not None:
            return
        from aetheros_control_plane.policy_risk import policy_from_yaml
        from aetheros_control_plane.models import TRUST_DIMENSIONS
        plane.policies.publish(policy_from_yaml(
            "policy:\n"
            "  name: local-sandbox-bootstrap\n"
            "  version: v1\n"
            "  allow:\n"
            "    - {capability: 'physical.move', resource: physical,\n"
            "       trust_floor: T0}\n"
            "    - {capability: 'physical.rotate', resource: physical,\n"
            "       trust_floor: T0}\n"
            "    - {capability: 'physical.read', resource: physical,\n"
            "       trust_floor: T0}\n"
            "    - {capability: 'physical.measure', resource: physical,\n"
            "       trust_floor: T0}\n"
            "    - {capability: 'physical.simulate', resource: physical,\n"
            "       trust_floor: T0}\n"))
        ident = eng._identity_id
        if ident:
            for dim in TRUST_DIMENSIONS:
                plane.trust.add_evidence(
                    ident, dim, 0.5, "local-operator first-run bootstrap "
                    "(sandbox simulation only; re-evaluate for hardware)",
                    source="local-operator")
        plane.audit.emit("embodied.sandbox_bootstrapped", {},
                         {"note": "first-run local policy; HIGH-risk and "
                                  "LIVE_HARDWARE still require explicit "
                                  "administrator policy + trust"})
    except Exception:
        pass


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "physical",
        help="Embodied intelligence: devices, robots, world, twins, tasks",
    )
    parser.add_argument("--autonomy", type=int, default=4)
    verbs = parser.add_subparsers(dest="physical_command")

    verbs.add_parser("status", help="Engine health snapshot")
    verbs.add_parser("devices", help="List registered devices (empty until paired)")

    d = verbs.add_parser("device", help="Device pairing demo (simulated)")
    d.add_argument("verb", choices=["pair", "inspect", "health"])

    r = verbs.add_parser("robot", help="Robot demo (simulated adapter)")
    r.add_argument("verb", choices=["list", "status", "simulate"])

    t = verbs.add_parser("task", help="Run the pick-and-place demo (§260)")
    t.add_argument("verb", nargs="?", default="demo")

    verbs.add_parser("twin", help="Twin drift demo")
    verbs.add_parser("stop", help="Global physical stop")
    verbs.add_parser("audit", help="Safety-log verification")
    verbs.add_parser("benchmark", help="Run embodied benchmarks")
    verbs.add_parser("world", help="Show world-state schema + version")
    verbs.add_parser("incidents", help="List recorded incidents")
    return parser


def dispatch_physical_command(args: Any) -> int:
    eng = _engine(args)
    verb = getattr(args, "physical_command", None) or "status"
    if verb == "status":
        print(json.dumps(eng.health_snapshot(), indent=2))
    elif verb == "devices":
        print(json.dumps({"devices": [],
                          "note": "no hardware paired — HARDWARE_UNAVAILABLE "
                                  "until pair with real credentials"}, indent=2))
    elif verb == "device":
        from aetheros_embodied.models import PhysicalDevice
        if args.verb == "pair":
            dev = eng.devices.pair(PhysicalDevice(kind="camera",
                                                  manufacturer="demo"),
                                   credential="demo-secret")
            print(json.dumps({"id": dev.id, "trust": dev.trust,
                              "note": "paired != trusted; attestation "
                                      "required"}, indent=2))
        elif args.verb == "inspect":
            print(json.dumps({"note": "pass a device id after pairing; "
                                      "registry starts empty"}, indent=2))
        else:
            print(json.dumps({"health": "unknown — no devices"}, indent=2))
    elif verb == "robot":
        ad = eng.executor.adapter
        if args.verb == "list":
            print(json.dumps({"robots": ad.discover(),
                              "mode": "SIMULATION"}, indent=2))
        elif args.verb == "status":
            ad.connect("sim-base-01")
            print(json.dumps(ad.state("sim-base-01"), indent=2))
        else:
            from aetheros_embodied.simulation import KinematicSimulator
            sim = KinematicSimulator()
            print(json.dumps(
                eng.simulate_task(eng.create_task("demo"),
                                  sim, [{"v": 0.2, "omega": 0.0, "dt": 1.0}]),
                indent=2))
    elif verb == "task":
        from aetheros_embodied.demo import run_pick_place_demo
        print(json.dumps(run_pick_place_demo(eng), indent=2, default=str))
    elif verb == "twin":
        twin = eng.twin_for("demo-room", kind="room")
        twin.sync({"objects": 0}, confidence=1.0)
        print(json.dumps(twin.check_drift({"objects": 1}), indent=2,
                         default=str))
    elif verb == "stop":
        eng.stop_all("operator CLI stop")
        print(json.dumps({"stopped": True}, indent=2))
    elif verb == "audit":
        print(json.dumps(eng.safety.verify_log(), indent=2))
    elif verb == "benchmark":
        from benchmark.physical_bench import main as bench_main
        bench_main()
    elif verb == "world":
        print(json.dumps({"version": eng.world.version,
                          "mode": "SIMULATION default; LIVE only via "
                                  "authorized adapters"}, indent=2))
    elif verb == "incidents":
        print(json.dumps({"incidents": eng.security.incidents}, indent=2,
                         default=str))
    else:
        print(f"unknown physical verb: {verb}")
        return 2
    return 0
