"""Reputation engine (spec sections 7 + 8).

Multidimensional metrics with value/confidence/sampleCount/timeWindow/
provenance. Weighted evidence: verified outcomes > observed metrics >
third-party attestations > raw user feedback. Attack defenses: identity
weighting, verified-transaction weighting, minimum samples, temporal
decay, org-correlation flags, reviewer diversity, dispute handling.

Never permanently blacklists on one noisy signal: low-confidence
metrics surface 'insufficient_evidence' instead of a verdict.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas as S
from .store import JsonStore

# Provenance weights for metric aggregation (deterministic).
_PROVENANCE_WEIGHT = {
    "verified": 1.0,
    "observed": 0.7,
    "attestation": 0.5,
    "user_feedback": 0.35,
    "security": 1.0,
}

MIN_SAMPLES_DEFAULT = 3
MIN_REVIEWERS_FOR_CONSENSUS = 3
DECAY_HALF_LIFE_DAYS = 45.0

# Raw observations stored per agent per metric: list of
# {value, provenance, weight_hint, reviewer, org, at, tx_ref}.
# tx_ref (verified transaction id) boosts weight (verified weighting).


class ReputationEngine:
    def __init__(self, home: Path) -> None:
        self._obs = JsonStore(Path(home) / "reputation_obs.json")
        self._incidents: List[Dict[str, Any]] = []

    # -- recording ------------------------------------------------------
    def record(self, agent_id: str, metric: str, value: float,
               provenance: str = "observed", reviewer: str = "",
               org: str = "", tx_ref: str = "",
               at: Optional[float] = None) -> Dict[str, Any]:
        if metric not in S.REPUTATION_METRICS:
            raise ValueError(f"unknown metric: {metric!r}")
        if provenance not in _PROVENANCE_WEIGHT:
            raise ValueError(f"bad provenance: {provenance!r}")
        if not (0.0 <= value <= 1.0):
            raise ValueError("metric value must be in [0, 1]")
        entry = {"obs_id": S.new_id("obs"), "agent_id": agent_id, "metric": metric,
                 "value": value, "provenance": provenance, "reviewer": reviewer,
                 "org": org, "tx_ref": tx_ref, "at": at or time.time()}
        self._obs.put(entry["obs_id"], entry)
        return entry

    def record_task_outcome(self, agent_id: str, success: bool,
                            latency_ms: Optional[float] = None,
                            verified: bool = False, tx_ref: str = "",
                            sla_met: Optional[bool] = None) -> None:
        prov = "verified" if verified else "observed"
        self.record(agent_id, "task_success", 1.0 if success else 0.0,
                    provenance=prov, tx_ref=tx_ref)
        if verified:
            self.record(agent_id, "verified_success", 1.0 if success else 0.0,
                        provenance="verified", tx_ref=tx_ref)
        if latency_ms is not None:
            # latency stored as attainment vs 60s budget (deterministic).
            attain = max(0.0, min(1.0, 1.0 - latency_ms / 60000.0))
            self.record(agent_id, "latency", attain, provenance="observed", tx_ref=tx_ref)
        if sla_met is not None:
            self.record(agent_id, "sla_adherence", 1.0 if sla_met else 0.0,
                        provenance=prov, tx_ref=tx_ref)

    def record_security_incident(self, agent_id: str, kind: str,
                                 tx_ref: str = "") -> None:
        self.record(agent_id, "security", 0.0, provenance="security", tx_ref=tx_ref)
        self._incidents.append({"agent_id": agent_id, "kind": kind,
                                "tx_ref": tx_ref, "at": time.time()})

    def record_policy_violation(self, agent_id: str, tx_ref: str = "") -> None:
        self.record(agent_id, "policy_compliance", 0.0,
                    provenance="security", tx_ref=tx_ref)

    # -- aggregation ------------------------------------------------------
    def _observations(self, agent_id: str, metric: str,
                      window_days: float = 90.0) -> List[Dict[str, Any]]:
        cutoff = time.time() - window_days * 86400.0
        out = []
        for raw in self._obs.values():
            if raw.get("agent_id") != agent_id or raw.get("metric") != metric:
                continue
            if raw.get("at", 0) < cutoff:
                continue
            out.append(raw)
        return out

    def _aggregate(self, obs: List[Dict[str, Any]],
                   window_days: float) -> S.Metric:
        if not obs:
            return S.Metric(value=0.0, confidence=0.0, sample_count=0,
                            time_window_days=int(window_days), provenance="none")
        num = 0.0
        den = 0.0
        reviewers: Dict[str, int] = {}
        for o in obs:
            age_days = max(0.0, (time.time() - o["at"]) / 86400.0)
            decay = 0.5 ** (age_days / DECAY_HALF_LIFE_DAYS)
            w = _PROVENANCE_WEIGHT[o["provenance"]] * decay
            if o.get("tx_ref"):
                w *= 1.25  # verified-transaction weighting
            num += w * o["value"]
            den += w
            if o.get("reviewer"):
                reviewers[o["reviewer"]] = reviewers.get(o["reviewer"], 0) + 1
        value = num / den if den else 0.0
        # Confidence: sample depth x reviewer diversity x recency mass.
        diversity = min(1.0, len(reviewers) / MIN_REVIEWERS_FOR_CONSENSUS) \
            if reviewers else 0.6
        depth = min(1.0, len(obs) / 10.0)
        confidence = round(min(1.0, 0.5 * depth + 0.3 * diversity + 0.2 * min(1.0, den / 5.0)), 4)
        dominant = max(set(o["provenance"] for o in obs),
                       key=lambda p: sum(1 for o in obs if o["provenance"] == p))
        return S.Metric(value=round(value, 4), confidence=confidence,
                        sample_count=len(obs), time_window_days=int(window_days),
                        provenance=dominant)

    def metric(self, agent_id: str, metric: str,
               window_days: float = 30.0) -> S.Metric:
        return self._aggregate(
            self._observations(agent_id, metric, window_days * 3), window_days)

    def profiles_for(self, agent_ids: List[str],
                     window_days: float = 30.0) -> Dict[str, S.ReputationProfile]:
        """Single grouping pass for many agents (scale path)."""
        cutoff = time.time() - window_days * 3 * 86400.0
        grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for raw in self._obs.values():
            if raw.get("agent_id") not in agent_ids or raw.get("at", 0) < cutoff:
                continue
            grouped.setdefault(raw["agent_id"], {}).setdefault(
                raw["metric"], []).append(raw)
        out: Dict[str, S.ReputationProfile] = {}
        for agent_id in agent_ids:
            per_metric = grouped.get(agent_id, {})
            metrics = {m: self._aggregate(per_metric.get(m, []),
                                          window_days).to_dict()
                       for m in S.REPUTATION_METRICS}
            flags: List[str] = []
            if sum(m["sample_count"] for m in metrics.values()) < 3:
                flags.append("insufficient_evidence")
            out[agent_id] = S.ReputationProfile(agent_id=agent_id,
                                                metrics=metrics, flags=flags)
        return out

    def profile(self, agent_id: str,
                window_days: float = 30.0) -> S.ReputationProfile:
        batched = self.profiles_for([agent_id], window_days)[agent_id]
        obs = [o for o in self._obs.values() if o.get("agent_id") == agent_id]
        batched.flags.extend(self._anomaly_flags(agent_id, obs))
        return batched

    # -- attack defense ----------------------------------------------------
    def _anomaly_flags(self, agent_id: str,
                       obs: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Heuristic, explainable flags — never auto-blacklist."""
        flags: List[str] = []
        if obs is None:
            obs = [o for o in self._obs.values() if o.get("agent_id") == agent_id]
        if not obs:
            return flags
        # Review bombing / spam: burst of same-provenance feedback in 1h.
        by_hour: Dict[str, int] = {}
        for o in obs:
            if o.get("provenance") == "user_feedback":
                bucket = str(int(o["at"] // 3600))
                by_hour[bucket] = by_hour.get(bucket, 0) + 1
        if any(c >= 10 for c in by_hour.values()):
            flags.append("suspected_review_burst")
        # Single-org dominance (Sybil/collusion hint): >80% from one org.
        orgs: Dict[str, int] = {}
        for o in obs:
            if o.get("org"):
                orgs[o["org"]] = orgs.get(o["org"], 0) + 1
        if orgs and max(orgs.values()) / max(len(obs), 1) > 0.8 and len(obs) >= 5:
            flags.append("single_org_dominance")
        # Reciprocal-rating hint is computed cross-agent by audit tooling;
        # here we flag perfect-score-only histories with tiny diversity.
        fb = [o for o in obs if o.get("provenance") == "user_feedback"]
        if len(fb) >= 5 and all(o["value"] == 1.0 for o in fb) \
                and len({o.get("reviewer") for o in fb}) < 2:
            flags.append("suspected_reciprocal_ratings")
        return flags

    def reviewer_diversity(self, agent_id: str, metric: str = "user_satisfaction") -> int:
        obs = self._observations(agent_id, metric, 365.0)
        return len({o.get("reviewer") for o in obs if o.get("reviewer")})
