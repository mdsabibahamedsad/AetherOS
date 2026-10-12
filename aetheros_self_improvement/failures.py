"""Failure intelligence (Phase C, §7-10, §67-69): deterministic
classification by impact evidence, root-cause divergence walk, real
counterfactual re-runs, clustering + hotspots. Severity is set from
impact signals, not model judgment (§8).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from .models import (FailureRecord, FailureSeverity, RootCauseHypothesis,
                     new_id)


def classify_severity(signals: Dict[str, Any]) -> str:
    """Impact-driven severity (§8). Signals: security_violation,
    destructive, task_failed, degraded, cosmetic."""
    if signals.get("security_violation") or signals.get("destructive"):
        return FailureSeverity.F5.value if signals.get(
            "critical") else FailureSeverity.F4.value
    if signals.get("task_failed"):
        return FailureSeverity.F3.value
    if signals.get("degraded"):
        return FailureSeverity.F2.value
    if signals.get("minor"):
        return FailureSeverity.F1.value
    return FailureSeverity.F0.value


class FailureAnalyzer:
    def __init__(self):
        self.failures: List[FailureRecord] = []

    def from_trace(self, trace: Dict[str, Any],
                   failure_class: str = "tool_execution",
                   signals: Optional[Dict[str, Any]] = None) -> FailureRecord:
        signals = signals or {}
        if trace.get("errors"):
            signals.setdefault("task_failed", True)
        rec = FailureRecord(
            trace_id=str(trace.get("trace_id", "")),
            tenant=str(trace.get("tenant", "default")),
            failure_class=failure_class,
            severity=classify_severity(signals),
            what_happened=str((trace.get("errors") or [{}])[-1].get(
                "message", trace.get("final_outcome", "")))[:1000],
            what_expected=str(trace.get("user_intent", ""))[:500],
            evidence={"tool_calls": len(trace.get("tool_calls", []) or []),
                      "retries": trace.get("retries", 0),
                      "signals": signals})
        self.failures.append(rec)
        return rec

    def cluster(self) -> List[Dict[str, Any]]:
        groups: Dict[str, List[str]] = {}
        for f in self.failures:
            key = f"{f.failure_class}:{f.severity}"
            groups.setdefault(key, []).append(f.id)
        return [{"cluster": k, "count": len(v), "ids": v}
                for k, v in sorted(groups.items(),
                                   key=lambda kv: -len(kv[1]))]

    def hotspots(self) -> Dict[str, Any]:
        return {"by_class": dict(Counter(
            f.failure_class for f in self.failures)),
            "by_severity": dict(Counter(
                f.severity for f in self.failures)),
            "critical": [f.id for f in self.failures
                         if f.severity in ("F4", "F5")]}


class RootCauseAnalyzer:
    """Walk tool_calls to first error; hypothesize with evidence (§9)."""

    def analyze(self, trace: Dict[str, Any],
                failure: FailureRecord) -> RootCauseHypothesis:
        calls = trace.get("tool_calls", []) or []
        div = -1
        for i, c in enumerate(calls):
            if isinstance(c, dict) and c.get("error"):
                div = i
                break
        evidence = []
        if div >= 0:
            evidence.append(f"first error at tool_calls[{div}]: "
                            f"{calls[div].get('tool', '?')}")
        if trace.get("retries", 0) > 2:
            evidence.append(f"retries={trace['retries']}: recovery failed")
        tools = [c.get("tool") for c in calls if isinstance(c, dict)]
        alternatives = []
        if len(set(tools)) == 1 and len(tools) > 2:
            alternatives.append("different tool selection may have avoided it")
        alternatives.append("extra verification step may have caught it")
        return RootCauseHypothesis(
            failure_id=failure.id,
            root_cause=(f"{calls[div].get('tool', 'unknown')} failed: "
                        f"{calls[div].get('error', '')}"[:500]
                        if div >= 0 else "no tool error; check plan/grounding"),
            divergence_step=div,
            confidence=0.7 if div >= 0 else 0.3,
            evidence=evidence,
            could_detect_earlier=div > 0,
            alternatives=alternatives)

    def counterfactual(self, task_inputs: Dict[str, Any],
                       executor: Callable, variants: Dict[str, Dict[str, Any]],
                       grader_ctx: Optional[Dict[str, Any]] = None
                       ) -> Dict[str, Any]:
        """Actually re-run variants; never claim unrun results (§10)."""
        out = {}
        for name, cfg in variants.items():
            try:
                res = executor(dict(task_inputs), dict(cfg))
                out[name] = {"ran": True,
                             "outcome": res.get("outcome"),
                             "context": res.get("context", {})}
            except Exception as exc:
                out[name] = {"ran": True, "outcome": None,
                             "error": f"{type(exc).__name__}: {exc}"[:300]}
        return out

    def explain(self, trace: Dict[str, Any],
                failure: FailureRecord,
                cause: RootCauseHypothesis) -> str:
        lines = [f"Task: {trace.get('task_id', '?')} "
                 f"(trace {trace.get('trace_id', '?')})",
                 f"Plan/tools: {trace.get('tools_used', [])}",
                 f"Error: {failure.what_happened}",
                 f"Divergence at step {cause.divergence_step}; "
                 f"confidence {cause.confidence:.2f}",
                 f"Final: {trace.get('final_outcome', '')}"]
        return "\n".join(lines)
