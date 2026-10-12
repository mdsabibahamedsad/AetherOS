"""Foresight controller + uncertainty (Phases H, §30-39, §74, §88,
§96-99, §143-145): explicit SIMULATE-or-not decision via Value of
Information; horizon penalty; calibration (Brier score, reliability);
safe default STOP/ASK/APPROVAL on uncertain high-risk (§74).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import PredictionConfidence, SimulationBudget


class ForesightDecision(str):
    SIMULATE = "simulate"
    DO_NOT_SIMULATE = "do_not_simulate"
    SIMULATE_SHALLOW = "simulate_shallow"
    SIMULATE_DEEP = "simulate_deep"
    REQUEST_MORE_INFORMATION = "request_more_information"
    ASK_USER = "ask_user"


class ForesightController:
    """§33-34: VoI = expected benefit − simulation cost; negative → skip."""

    def __init__(self, sim_cost_per_branch: float = 0.01,
                 uncertainty_threshold: float = 0.4):
        self.sim_cost = sim_cost_per_branch
        self.threshold = uncertainty_threshold
        self.decisions = 0

    def decide(self, risk: float, uncertainty: float, reversibility: float,
               budget: Optional[SimulationBudget] = None,
               stakes: float = 0.5) -> Dict[str, Any]:
        """stakes: value of getting the decision right (0..1)."""
        self.decisions += 1
        budget = budget or SimulationBudget()
        voi = stakes * uncertainty - self.sim_cost * budget.max_branches
        if risk >= 0.8 and uncertainty >= self.threshold:
            return {"decision": ForesightDecision.ASK_USER,
                    "voi": voi, "reason": "high risk + high uncertainty "
                                          "(§74 safe default)"}
        if voi <= 0 and risk < 0.3:
            return {"decision": ForesightDecision.DO_NOT_SIMULATE,
                    "voi": voi, "reason": "VoI negative, low risk"}
        if risk >= 0.6 or uncertainty >= 0.6:
            depth = min(budget.max_depth, 5 if risk < 0.85 else 10)
            return {"decision": ForesightDecision.SIMULATE_DEEP,
                    "voi": voi, "depth": depth,
                    "reason": "elevated risk/uncertainty"}
        if uncertainty >= self.threshold:
            return {"decision": ForesightDecision.REQUEST_MORE_INFORMATION,
                    "voi": voi,
                    "reason": "uncertainty reducible by observation (§35)"}
        return {"decision": ForesightDecision.SIMULATE_SHALLOW,
                "voi": voi, "depth": 2, "reason": "routine check"}


def horizon_confidence(base: float, horizon: int,
                       growth: float = 0.15) -> float:
    """Uncertainty grows with horizon; never magically improves (§88)."""
    return max(0.0, base * (1.0 - min(0.95, growth * (horizon - 1))))


class Calibrator:
    """§39/§143: Brier score + reliability buckets over (confidence,
    correct) pairs. Raw frequencies labeled as simulation frequencies."""

    def __init__(self):
        self.records: List[tuple] = []

    def record(self, confidence: float, correct: bool) -> None:
        self.records.append((max(0.0, min(1.0, confidence)), bool(correct)))

    def brier(self) -> Optional[float]:
        if not self.records:
            return None
        n = len(self.records)
        return sum((c - (1.0 if ok else 0.0)) ** 2
                   for c, ok in self.records) / n

    def reliability(self, buckets: int = 5) -> List[Dict[str, Any]]:
        out = []
        for i in range(buckets):
            lo, hi = i / buckets, (i + 1) / buckets
            pts = [ok for c, ok in self.records if lo <= c < hi
                   or (hi == 1.0 and c == 1.0)]
            out.append({"bucket": [lo, hi], "n": len(pts),
                        "accuracy": (sum(pts) / len(pts)) if pts else None})
        return out

    def diagnosis(self) -> str:
        b = self.brier()
        if b is None:
            return "no data — confidence uncalibrated, do not trust"
        if b > 0.25:
            return "overconfident — downgrade trust, gather evidence"
        if b < 0.05 and len(self.records) < 20:
            return "possibly lucky — small sample, stay cautious"
        return "calibrated within observed range"
