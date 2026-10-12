"""Kinematic simulation (§113-115): differential-drive base +
2-link planar arm forward kinematics, simulator contract, domain
randomization, hardware-in-the-loop guards. Simulations are labeled;
sim2real error is measured, never assumed zero."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional


class KinematicSimulator:
    """Deterministic kinematics. Dynamics (slip, friction, backlash)
    are NOT modeled — stated in every contract."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.x, self.y, self.theta = 0.0, 0.0, 0.0
        self.joints = [0.0, 0.0]
        self.link_lengths = (0.3, 0.25)
        self.noise = 0.0  # set >0 only via domain randomization

    # -- contract (§114) ------------------------------------------------
    def contract(self) -> Dict[str, Any]:
        return {"state": ["x", "y", "theta", "joints"],
                "actions": ["drive", "set_joints"],
                "transition": "ideal kinematics + optional gaussian noise",
                "observation": "exact state + noise",
                "uncertainty": f"noise={self.noise}",
                "limitations": ["no dynamics", "no slip", "no contact",
                                "noise is gaussian-only"]}

    def reset(self, x: float = 0.0, y: float = 0.0,
              theta: float = 0.0) -> Dict[str, float]:
        self.x, self.y, self.theta = x, y, theta
        return self.observe()

    def step(self, v: float, omega: float,
             dt: float) -> Dict[str, float]:
        """Differential-drive integration."""
        self.theta += omega * dt
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        return self.observe()

    def set_joints(self, j1: float, j2: float) -> Dict[str, float]:
        self.joints = [j1, j2]
        return {"j1": j1, "j2": j2,
                "ee": self.fk(j1, j2)}

    def fk(self, j1: float, j2: float) -> Dict[str, float]:
        l1, l2 = self.link_lengths
        x = l1 * math.cos(j1) + l2 * math.cos(j1 + j2)
        y = l1 * math.sin(j1) + l2 * math.sin(j1 + j2)
        return {"x": x, "y": y}

    def observe(self) -> Dict[str, float]:
        n = (lambda: self.rng.gauss(0, self.noise)) if self.noise else (lambda: 0.0)
        return {"x": self.x + n(), "y": self.y + n(),
                "theta": self.theta + n(),
                "mode": "SIMULATION"}

    def randomize(self, noise: float = 0.01) -> None:
        """Domain randomization hook (§123): only noise today."""
        self.noise = noise


class SimToRealTracker:
    def __init__(self) -> None:
        self.pairs: List[Dict[str, Any]] = []

    def add(self, predicted: Dict[str, float],
            actual: Dict[str, float]) -> None:
        self.pairs.append({"predicted": predicted, "actual": actual})

    def error(self) -> Dict[str, Any]:
        if not self.pairs:
            return {"n": 0, "note": "no pairs — gap unknown, do not assume"}
        keys = {k for p in self.pairs for k in p["predicted"]}
        out = {}
        for k in keys:
            diffs = [abs(p["predicted"].get(k, 0.0) - p["actual"].get(k, 0.0))
                     for p in self.pairs]
            out[k] = sum(diffs) / len(diffs)
        return {"n": len(self.pairs), "mean_abs_error": out}
