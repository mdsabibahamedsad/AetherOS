"""Reality checker + prediction errors + updater (Phases F-G,
§40-45, §91, §125-132, §182-189): expected observation declared BEFORE
action; expected-vs-actual compared after; divergence thresholds drive
replan/stop; TOCTOU via stateVersion recheck; updates never resurrect
trust without evidence.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .models import ErrorClass, PredictionError


def classify_error(prediction: Dict[str, Any],
                   observation: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic diff → error class + severity (§41, §130)."""
    diff = {}
    keys = set(prediction) | set(observation)
    for k in keys:
        if prediction.get(k) != observation.get(k):
            diff[k] = {"predicted": prediction.get(k),
                       "observed": observation.get(k)}
    n = len(diff)
    severity = ("minor" if n == 0 else "moderate" if n <= 2 else "major"
                if n <= 5 else "critical")
    eclass = ErrorClass.STATE_ERROR.value
    if any("caus" in k for k in diff):
        eclass = ErrorClass.CAUSAL_ERROR.value
    elif any("time" in k or "order" in k for k in diff):
        eclass = ErrorClass.TEMPORAL_ERROR.value
    elif any("entit" in k for k in diff):
        eclass = ErrorClass.ENTITY_ERROR.value
    return {"difference": diff, "severity": severity,
            "error_class": eclass}


class RealityChecker:
    def __init__(self):
        self.expectations: Dict[str, Dict[str, Any]] = {}
        self.errors: List[PredictionError] = []
        self.divergence_count = 0
        # policy hook: returns True if STOP required on critical
        self.critical_stop = True

    def expect(self, action_id: str,
               expected: Dict[str, Any]) -> None:
        self.expectations[action_id] = dict(expected)

    def check(self, action_id: str, observed: Dict[str, Any],
              model_version: str = "") -> PredictionError:
        predicted = self.expectations.pop(action_id, {})
        res = classify_error(predicted, observed)
        err = PredictionError(
            prediction=predicted, observation=dict(observed),
            difference=res["difference"], severity=res["severity"],
            error_class=res["error_class"], model_version=model_version)
        self.errors.append(err)
        if res["severity"] in ("major", "critical"):
            self.divergence_count += 1
        return err

    def action_for(self, err: PredictionError) -> str:
        """§131-132: major → replan; critical → stop/approval/incident."""
        if err.severity == "critical":
            return "stop" if self.critical_stop else "approval"
        if err.severity == "major":
            return "replan"
        if err.severity == "moderate":
            return "note"
        return "none"


class WorldModelUpdater:
    """§45: update state/confidence/dynamics/hypotheses from errors."""

    def __init__(self):
        self.updates = 0

    def update(self, tracker: Dict[str, Any],
               err: PredictionError) -> Dict[str, Any]:
        """tracker: {'trust': float, 'failures': int} per model key."""
        self.updates += 1
        if err.severity in ("major", "critical"):
            tracker["trust"] = max(0.0, tracker.get("trust", 0.8) - 0.2)
            tracker["failures"] = tracker.get("failures", 0) + 1
        elif err.severity == "minor" and not err.difference:
            tracker["trust"] = min(1.0, tracker.get("trust", 0.8) + 0.02)
        return tracker


def toctou_recheck(get_version: Callable[[], int],
                   planned_version: int) -> bool:
    """§126-127: True if plan is stale and must fail/replan."""
    try:
        return get_version() != planned_version
    except Exception:
        return True  # fail closed on unreadable version
