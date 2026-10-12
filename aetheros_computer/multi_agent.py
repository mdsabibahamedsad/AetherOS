"""
Multi-agent computer-use roles (Master 15 Phases 86-88).

Minimal, additive contract over MASTER 11's existing delegation:

- ``ExecutorGate``: only the designated executor principal may dispatch
  external actions; planners/researchers calling execute() are refused.
- ``IndependentVerifier``: after a high-risk completion, an optional verifier
  callable receives a SAFE summary (no secrets) and must confirm; refusal
  marks the run FAILED_UNVERIFIED rather than silently successful.

Pure orchestration policy — no new agents, no duplicate delegation.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from aetheros_computer.action import RiskTier


class ExecutorGate:
    """Bind which principal may perform external actions."""

    def __init__(self, authorized_executor: str):
        self._authorized = str(authorized_executor)
        self._lock = threading.Lock()

    @property
    def authorized(self) -> str:
        with self._lock:
            return self._authorized

    def reauthorize(self, principal: str) -> None:
        with self._lock:
            self._authorized = str(principal)

    def check_execute_allowed(self, principal: str, risk_value: int = 0) -> Dict[str, Any]:
        """Read-only/observation actions bypass the gate; everything else
        requires the bound executor identity."""
        if risk_value < 2:
            return {"allowed": True, "reason": "read-only action"}
        if str(principal) == self._authorized:
            return {"allowed": True, "reason": ""}
        return {"allowed": False,
                "reason": f"principal '{principal}' is not the authorized "
                          f"executor '{self._authorized}'"}


class IndependentVerifier:
    """Optional post-execution verification for high-risk completions."""

    def __init__(self, verify_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
                 threshold: int = RiskTier.R3_HIGH.value):
        self.verify_fn = verify_fn
        self.threshold = threshold

    def applies(self, risk_value: int) -> bool:
        return risk_value >= self.threshold and self.verify_fn is not None

    def verify_completion(self, safe_summary: Dict[str, Any]) -> Dict[str, Any]:
        if not self.applies(int(safe_summary.get("risk_value", 0))):
            return {"verified": True, "skipped": True}
        try:
            ok = bool(self.verify_fn(safe_summary))
        except Exception as exc:
            return {"verified": False, "error": f"verifier raised: {exc}"}
        return {"verified": ok,
                **({} if ok else {"error": "independent verifier refused completion"})}


def make_safe_summary(metadata: Any, result: Any) -> Dict[str, Any]:
    """Summary safe for cross-agent consumption: ids + hashes only."""
    from aetheros_computer.events_stream import safe_target_hash

    return {
        "action_id": getattr(metadata, "action_id", ""),
        "task_id": getattr(metadata, "task_id", ""),
        "action": getattr(metadata, "action_type", ""),
        "risk_value": int(getattr(getattr(metadata, "risk_level", None),
                                  "value", 0)),
        "target_hash": safe_target_hash(getattr(metadata, "target", "")),
        "success": bool(result.get("success")) if isinstance(result, dict) else False,
    }


__all__ = [
    "ExecutorGate",
    "IndependentVerifier",
    "make_safe_summary",
]
