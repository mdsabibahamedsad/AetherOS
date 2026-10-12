"""Causal engine (Phase J, §18-21, §52-53, §139, §186): edges labeled
HYPOTHESIS until validated by rule/domain evidence, controlled
intervention, or safe experiment. Temporal precedence alone NEVER
promotes to causal (§19). do(A) runs against simulator/twin, never the
real environment directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import CausalEdge


class CausalModel:
    def __init__(self):
        self.edges: Dict[str, CausalEdge] = {}

    @staticmethod
    def _key(src: str, dst: str) -> str:
        return f"{src}→{dst}"

    def hypothesize(self, src: str, dst: str, scope: str = "",
                    strength: float = 0.3) -> CausalEdge:
        edge = CausalEdge(src, dst, strength=strength, confidence=0.2,
                          source="hypothesis", scope=scope,
                          status="HYPOTHESIS")
        self.edges[self._key(src, dst)] = edge
        return edge

    def add_evidence(self, src: str, dst: str, kind: str,
                     reference: str, weight: float = 0.2) -> CausalEdge:
        """kind: rule | domain | experiment | intervention | observation.
        Observation-only evidence can raise confidence but NEVER validate
        (§19: correlation ≠ causation)."""
        edge = self.edges.get(self._key(src, dst)) or self.hypothesize(
            src, dst)
        edge.evidence.append(f"{kind}:{reference}")
        edge.confidence = min(1.0, edge.confidence + weight)
        if kind in ("rule", "domain", "experiment", "intervention"):
            edge.source = kind
            if edge.confidence >= 0.6:
                edge.status = "VALIDATED"
        return edge

    def intervene(self, src: str, dst: str,
                  runner: Any) -> Dict[str, Any]:
        """do(src): run intervention via provided simulator callable;
        runner(src_value_on/off) -> dst observed or not."""
        try:
            with_on = runner(True)
            with_off = runner(False)
        except Exception as exc:
            return {"validated": False, "reason": f"runner failed: {exc}"}
        if with_on and not with_off:
            edge = self.add_evidence(src, dst, "intervention",
                                     "do() contrast", weight=0.4)
            return {"validated": edge.status == "VALIDATED",
                    "confidence": edge.confidence}
        return {"validated": False,
                "reason": "no contrast between do(src) and ¬do(src)"}

    def downgrade(self, src: str, dst: str, reason: str = "") -> None:
        edge = self.edges.get(self._key(src, dst))
        if edge:
            edge.confidence = max(0.0, edge.confidence - 0.3)
            edge.status = "HYPOTHESIS"
            if reason:
                edge.evidence.append(f"downgrade:{reason}")

    def graph(self) -> List[Dict[str, Any]]:
        return [{"src": e.src, "dst": e.dst, "strength": e.strength,
                 "confidence": e.confidence, "source": e.source,
                 "status": e.status, "evidence": e.evidence,
                 "scope": e.scope} for e in self.edges.values()]
