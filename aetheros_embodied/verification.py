"""Verification (§37-38): command-sent != succeeded. Expectation
engine declares expected state BEFORE action; verifier compares with
independent evidence (sensor/camera/telemetry/state/ack)."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .models import PhysicalAction


class ExpectationEngine:
    def __init__(self) -> None:
        self.expected: Dict[str, Dict[str, Any]] = {}

    def expect(self, action_id: str,
               expected_state: Dict[str, Any]) -> None:
        self.expected[action_id] = dict(expected_state)

    def compare(self, action_id: str,
                observed: Dict[str, Any]) -> Dict[str, Any]:
        exp = self.expected.pop(action_id, {})
        matched = {k: observed.get(k) == v for k, v in exp.items()}
        if not exp:
            return {"verdict": "NO_EXPECTATION", "matched": {}}
        if all(matched.values()):
            return {"verdict": "VERIFIED", "matched": matched}
        if any(matched.values()):
            return {"verdict": "PARTIAL_SUCCESS", "matched": matched,
                    "missing": [k for k, v in matched.items() if not v]}
        return {"verdict": "ACTION_FAILED", "matched": matched}


class ActionVerifier:
    """Multi-source verification. ack alone is never SUCCESS."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance
        self.expectations = ExpectationEngine()

    def verify(self, action: PhysicalAction, result: Dict[str, Any],
               evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        evidence = evidence or {}
        ack = bool(result.get("ack"))
        if not ack:
            if action.execution_mode == "LIVE_HARDWARE":
                return {"verdict": "UNKNOWN_EXECUTION_STATE",
                        "reason": "no acknowledgement — not SUCCESS"}
            return {"verdict": "ACTION_FAILED",
                    "reason": result.get("reason", "no ack")}
        exp = self.expectations.expected.get(action.id)
        state = evidence.get("state", {})
        if exp:
            cmp_ = self.expectations.compare(action.id, state)
            if cmp_["verdict"] == "VERIFIED":
                return {"verdict": "VERIFIED", "sources": ["expectation"]}
            if cmp_["verdict"] == "PARTIAL_SUCCESS":
                return {"verdict": "PARTIAL_SUCCESS",
                        "missing": cmp_["missing"]}
            if not state:
                return {"verdict": "UNKNOWN_EXECUTION_STATE",
                        "reason": "ack only, no state evidence"}
            return {"verdict": "VERIFICATION_FAILED",
                    "reason": "state unchanged vs expectation"}
        if state:
            return {"verdict": "VERIFIED", "sources": ["state"]}
        if evidence.get("sensor") is not None:
            return {"verdict": "VERIFIED", "sources": ["sensor"]}
        return {"verdict": "UNKNOWN_EXECUTION_STATE",
                "reason": "ack without independent evidence"}
