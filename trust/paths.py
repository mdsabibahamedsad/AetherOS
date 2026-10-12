"""Path-aware governance (§15): execution paths, cumulative risk,
privilege accumulation, path anomaly. Agent behavior is
path-dependent — harmless steps can compose into harmful sequences."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import Risk, risk_at_least, risk_order


class ExecutionPathTracker:
    """Per-task ordered action history with cumulative risk."""

    def __init__(self) -> None:
        self._paths: Dict[str, List[Dict]] = {}

    def record(self, task_id: str, action_id: str, capability: str,
               resource: str, risk: Risk,
               data_classes: Optional[List[str]] = None) -> None:
        self._paths.setdefault(task_id, []).append({
            "action_id": action_id, "capability": capability,
            "resource": resource, "risk": risk.value,
            "data": list(data_classes or [])})

    def path(self, task_id: str) -> Tuple[str, ...]:
        return tuple(a["action_id"] for a in self._paths.get(task_id, []))

    def cumulative_risk(self, task_id: str) -> Risk:
        """Max observed level bumped one step when 3+ R2+ actions chain —
        sequences escalate even when each step looks benign."""
        levels = [Risk(a["risk"]) for a in self._paths.get(task_id, [])]
        if not levels:
            return Risk.R0_INFORMATIONAL
        top = max(levels, key=lambda r: _order(r))
        elevated = [r for r in levels
                    if risk_at_least(r, Risk.R2_REVERSIBLE_LOCAL)]
        if len(elevated) >= 3:
            order = list(Risk)
            top = order[min(order.index(top) + 1, len(order) - 1)]
        return top

    def privilege_accumulation(self, task_id: str) -> Dict[str, List[str]]:
        """Distinct capabilities/resources touched — the deputy's view."""
        caps, res = set(), set()
        for a in self._paths.get(task_id, []):
            caps.add(a["capability"])
            res.add(a["resource"])
        return {"capabilities": sorted(caps), "resources": sorted(res)}

    def data_flow(self, task_id: str) -> List[Tuple[str, str]]:
        """(source, data-class) pairs in order — feeds DLP path checks."""
        out = []
        for a in self._paths.get(task_id, []):
            for d in a["data"]:
                out.append((a["resource"], d))
        return out

    def anomaly(self, task_id: str) -> List[str]:
        """Heuristic path anomalies: rapid privilege spread, read->exfil
        shapes, repeated denied-then-variant retries."""
        notes = []
        acc = self.privilege_accumulation(task_id)
        if len(acc["capabilities"]) >= 6:
            notes.append("rapid privilege spread across capabilities")
        flow = self.data_flow(task_id)
        classes = [d for _, d in flow]
        if "secret" in classes and any(
                c.startswith(("network", "email", "http"))
                for c in acc["capabilities"]):
            notes.append("secret touched then external capability used")
        return notes


def _order(level: Risk) -> int:
    return risk_order(level)
