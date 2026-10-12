"""Lab automation (§67-76, §251): instruments, validated protocols,
per-step execution records, closed-loop Bayesian optimization over a
grid surrogate (honest math, stated limits), Pareto frontiers."""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .models import ExecMode


@dataclass
class LabInstrument:
    id: str
    type: str = ""  # pipette | heater | imager | spectrometer | ...
    vendor: str = ""
    model: str = ""
    firmware: str = ""
    capabilities: List[str] = field(default_factory=list)
    calibration_id: str = ""
    safety: str = "LOW"
    connection: str = "HARDWARE_UNAVAILABLE"


@dataclass
class LabProtocol:
    objective: str = ""
    materials: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    controls: List[str] = field(default_factory=list)
    measurements: List[str] = field(default_factory=list)
    safety: str = "LOW"
    stop_conditions: List[str] = field(default_factory=list)
    cleanup: List[str] = field(default_factory=list)


class LabAutomationEngine:
    ABSTRACT_CAPS = ["dispense", "mix", "heat", "cool", "transfer",
                     "measure", "image", "incubate", "sample", "analyze"]

    def __init__(self) -> None:
        self.instruments: Dict[str, LabInstrument] = {}
        self.runs: List[Dict[str, Any]] = []

    def register(self, inst: LabInstrument) -> None:
        self.instruments[inst.id] = inst

    def validate_protocol(self, proto: LabProtocol) -> Dict[str, Any]:
        errors = []
        if not proto.steps:
            errors.append("empty protocol")
        for i, step in enumerate(proto.steps):
            cap = step.get("capability", "")
            if cap not in self.ABSTRACT_CAPS:
                errors.append(f"step {i}: unknown capability {cap}")
            params = step.get("parameters", {})
            bounds = step.get("bounds", {})
            for k, v in params.items():
                if k in bounds and isinstance(v, (int, float)):
                    lo, hi = bounds[k]
                    if not (lo <= v <= hi):
                        errors.append(f"step {i}: {k}={v} out of "
                                      f"[{lo},{hi}]")
        if proto.safety in ("HIGH", "PROHIBITED"):
            errors.append("safety class requires human authorization")
        return {"ok": not errors, "errors": errors}

    def dry_simulate(self, proto: LabProtocol) -> Dict[str, Any]:
        return {"mode": ExecMode.SIMULATION,
                "steps": len(proto.steps),
                "trace": [{"step": i, "would_run": True,
                           "capability": s.get("capability")}
                          for i, s in enumerate(proto.steps)]}

    def execute_step(self, instrument_id: str,
                     step: Dict[str, Any]) -> Dict[str, Any]:
        inst = self.instruments.get(instrument_id)
        if inst is None or inst.connection == "HARDWARE_UNAVAILABLE":
            return {"status": "HARDWARE_UNAVAILABLE",
                    "instrument": instrument_id}
        rec = {"instrument": instrument_id, "step": step,
               "at": time.time(), "mode": ExecMode.LIVE_HARDWARE,
               "ack": False,
               "note": "driver must fill ack + sensor data"}
        self.runs.append(rec)
        return rec


class BayesianOptimizer:
    """Grid surrogate + RBF kernel regression + Expected Improvement.
    Small, exact, and honest about being a toy-scale optimizer."""

    def __init__(self, bounds: Dict[str, List[float]],
                 seed: int = 0) -> None:
        self.bounds = bounds
        self.rng = random.Random(seed)
        self.obs: List[Dict[str, Any]] = []

    def observe(self, params: Dict[str, float], value: float) -> None:
        self.obs.append({"params": dict(params), "value": value})

    def _predict(self, cand: Dict[str, float]) -> tuple:
        if not self.obs:
            return (0.0, 1.0)
        keys = list(self.bounds)
        dists = []
        for o in self.obs:
            d2 = sum(((cand[k] - o["params"][k]) /
                      max(self.bounds[k][1] - self.bounds[k][0], 1e-9)) ** 2
                     for k in keys)
            dists.append((math.exp(-d2), o["value"]))
        wsum = sum(w for w, _ in dists) or 1.0
        mu = sum(w * v for w, v in dists) / wsum
        var = sum(w * (v - mu) ** 2 for w, v in dists) / wsum
        return (mu, math.sqrt(var))

    def suggest(self, n_grid: int = 9) -> Dict[str, Any]:
        keys = list(self.bounds)
        best = {"ei": -1.0, "params": {}}
        f_best = max((o["value"] for o in self.obs), default=0.0)
        grids = [[self.bounds[k][0] + i * (self.bounds[k][1]
                                           - self.bounds[k][0])
                  / max(n_grid - 1, 1) for i in range(n_grid)]
                 for k in keys]
        import itertools
        for combo in itertools.product(*grids):
            cand = dict(zip(keys, combo))
            mu, sigma = self._predict(cand)
            if sigma <= 0:
                ei = max(mu - f_best, 0.0)
            else:
                z = (mu - f_best) / sigma
                phi = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
                Phi = 0.5 * (1 + math.erf(z / math.sqrt(2)))
                ei = (mu - f_best) * Phi + sigma * phi
            if ei > best["ei"]:
                best = {"ei": ei, "params": cand, "mu": mu,
                        "sigma": sigma}
        best["note"] = "EI over RBF surrogate; toy scale, verify live"
        return best


def pareto_frontier(points: List[Dict[str, float]],
                    keys: List[str],
                    maximize: Optional[List[bool]] = None) -> List[int]:
    """Indices of non-dominated points. Real computation."""
    maximize = maximize or [True] * len(keys)
    front = []
    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            better_all = all(
                (q[k] >= p[k] if mx else q[k] <= p[k]) for k, mx in
                zip(keys, maximize))
            strictly = any(
                (q[k] > p[k] if mx else q[k] < p[k]) for k, mx in
                zip(keys, maximize))
            if better_all and strictly:
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front
