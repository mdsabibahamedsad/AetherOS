"""Multidimensional trust engine (spec section 6).

Dimensions: identity, security, execution, economic, evidence,
behavioral, organizational. Each signal carries source/type/value/
confidence/timestamp/evidence/decay. Recent verified behavior outweighs
ancient behavior; security incidents hit hard and decay slowly.

Trust NEVER equals capability and NEVER alone authorizes: the output is
one input (with provenance) to the selection + policy pipeline.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

# Per-dimension aggregation weights for signal sources (deterministic).
_SOURCE_WEIGHT = {
    "verification": 1.0,
    "outcome": 0.9,
    "security": 1.0,
    "organization": 0.8,
    "user": 0.6,
    "attestation": 0.5,
}

# Security incident kinds and their penalty (applied to security dim).
_INCIDENT_PENALTY = {
    "prompt_injection": -0.6,
    "exfiltration": -0.9,
    "malicious_artifact": -0.8,
    "unauthorized_behavior": -0.7,
    "policy_violation": -0.4,
    "overcharge": -0.3,
}

MIN_SIGNALS_FOR_CONFIDENCE = 2


class AgentTrustEngine:
    def __init__(self, home: Path) -> None:
        self._signals = JsonStore(Path(home) / "trust_signals.json")

    def record_signal(self, signal: S.TrustSignal) -> S.TrustSignal:
        if signal.dimension not in S.TRUST_DIMENSIONS:
            raise ValueError(f"bad dimension: {signal.dimension!r}")
        if not (-1.0 <= signal.value <= 1.0):
            raise ValueError("signal value must be in [-1, 1]")
        if not (0.0 <= signal.confidence <= 1.0):
            raise ValueError("signal confidence must be in [0, 1]")
        if not signal.signal_id:
            signal.signal_id = S.new_id("sig")
        self._signals.put(signal.signal_id, signal.to_dict())
        return signal

    def record_outcome(self, agent_id: str, dimension: str, success: bool,
                       evidence_ref: str = "", source: str = "outcome") -> S.TrustSignal:
        return self.record_signal(S.TrustSignal(
            agent_id=agent_id, dimension=dimension, source=source,
            kind="task_success" if success else "task_failure",
            value=0.5 if success else -0.5, confidence=0.7,
            evidence_ref=evidence_ref))

    def record_incident(self, agent_id: str, kind: str,
                        evidence_ref: str = "") -> S.TrustSignal:
        penalty = _INCIDENT_PENALTY.get(kind, -0.5)
        return self.record_signal(S.TrustSignal(
            agent_id=agent_id, dimension="security", source="security",
            kind=kind, value=penalty, confidence=0.9,
            evidence_ref=evidence_ref, decay_half_life_days=180.0))

    def _agent_signals(self, agent_id: str,
                       dimension: Optional[str] = None) -> List[S.TrustSignal]:
        out = []
        for raw in self._signals.values():
            try:
                sig = S.TrustSignal.from_dict(raw)
            except ValueError:
                continue
            if sig.agent_id != agent_id:
                continue
            if dimension and sig.dimension != dimension:
                continue
            out.append(sig)
        return out

    def dimension_score(self, agent_id: str, dimension: str,
                        at: Optional[float] = None) -> Dict[str, Any]:
        """Weighted decayed aggregate + provenance. No signals => score 0,
        confidence 0 (never invent trust)."""
        sigs = self._agent_signals(agent_id, dimension)
        if not sigs:
            return {"dimension": dimension, "score": 0.0, "confidence": 0.0,
                    "samples": 0, "provenance": []}
        num = 0.0
        den = 0.0
        prov = []
        for sig in sigs:
            w = _SOURCE_WEIGHT.get(sig.source, 0.4) * sig.confidence
            v = sig.decayed_value(at)
            num += w * v
            den += w
            prov.append({"signal_id": sig.signal_id, "source": sig.source,
                         "kind": sig.kind, "decayed_value": round(v, 4),
                         "at": sig.created_at, "evidence_ref": sig.evidence_ref})
        score = num / den if den else 0.0
        confidence = min(1.0, len(sigs) / max(MIN_SIGNALS_FOR_CONFIDENCE, 1) * 0.5
                         + (den / (den + 2.0)) * 0.5)
        return {"dimension": dimension, "score": round(score, 4),
                "confidence": round(confidence, 4), "samples": len(sigs),
                "provenance": prov}

    def ranks(self, agent_ids: List[str],
              at: Optional[float] = None) -> Dict[str, float]:
        """Single-pass overall scores for many agents (scale path)."""
        return {a: s["overall"]
                for a, s in self.summaries(agent_ids, at).items()}

    def summaries(self, agent_ids: List[str],
                  at: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Batched overall+confidence per agent, single pass (scale path).
        Same aggregation math as profile(); per-signal provenance is
        available via profile() for single agents."""
        by_agent: Dict[str, Dict[str, List[S.TrustSignal]]] = {}
        wanted = set(agent_ids)
        for raw in self._signals.values():
            if raw.get("agent_id") not in wanted:
                continue
            try:
                sig = S.TrustSignal.from_dict(raw)
            except ValueError:
                continue
            by_agent.setdefault(sig.agent_id, {}).setdefault(
                sig.dimension, []).append(sig)
        out: Dict[str, Dict[str, Any]] = {}
        for agent_id in agent_ids:
            num = den = 0.0
            samples = 0
            for dim_sigs in by_agent.get(agent_id, {}).values():
                d_num = sum(_SOURCE_WEIGHT.get(s.source, 0.4) * s.confidence
                            * s.decayed_value(at) for s in dim_sigs)
                d_den = sum(_SOURCE_WEIGHT.get(s.source, 0.4) * s.confidence
                            for s in dim_sigs)
                conf = min(1.0, len(dim_sigs) / max(MIN_SIGNALS_FOR_CONFIDENCE, 1) * 0.5
                           + (d_den / (d_den + 2.0)) * 0.5)
                num += (d_num / d_den if d_den else 0.0) * conf
                den += conf
                samples += len(dim_sigs)
            out[agent_id] = {"overall": round(num / den, 4) if den else 0.0,
                             "confidence": round(den / len(S.TRUST_DIMENSIONS), 4),
                             "samples": samples}
        return out

    def profile(self, agent_id: str,
                at: Optional[float] = None) -> Dict[str, Any]:
        dims = {d: self.dimension_score(agent_id, d, at) for d in S.TRUST_DIMENSIONS}
        # Overall is the confidence-weighted mean — exposed WITH components.
        num = sum(d["score"] * d["confidence"] for d in dims.values())
        den = sum(d["confidence"] for d in dims.values())
        return {"agent_id": agent_id, "dimensions": dims,
                "overall": round(num / den, 4) if den else 0.0,
                "overall_confidence": round(den / len(dims), 4) if dims else 0.0}
