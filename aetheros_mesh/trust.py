"""Multidimensional mesh trust engine (Master 49 sections 7, 71-74).

Trust dimensions:
- identity: Identity verification, key ownership
- security: Security posture, incident history
- execution: Task execution reliability
- economic: Payment reliability, fair pricing
- evidence: Quality of evidence provided
- organization: Organizational vetting
- network: Network behavior, connectivity
- behavior: Behavioral patterns, anomaly detection

Never collapse these into one opaque number.
"""

from __future__ import annotations

import json
import logging
import math
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .models import MeshNode, TrustDimension

logger = logging.getLogger(__name__)


# Per-dimension signal source weights (deterministic)
_SOURCE_WEIGHT = {
    "verification": 1.0,      # Cryptographic verification
    "outcome": 0.9,           # Observed task outcomes
    "security": 1.0,          # Security incidents/audits
    "organization": 0.8,      # Org vetting/attestation
    "user": 0.6,              # User feedback
    "attestation": 0.5,       # Third-party attestations
    "self_reported": 0.3,     # Self-reported (lowest weight)
}

# Dimension-specific decay half-lives (days)
_DIMENSION_DECAY = {
    TrustDimension.IDENTITY: 365.0,      # Identity is stable
    TrustDimension.SECURITY: 180.0,      # Security incidents decay slowly
    TrustDimension.EXECUTION: 90.0,      # Execution history decays moderately
    TrustDimension.ECONOMIC: 90.0,       # Economic behavior
    TrustDimension.EVIDENCE: 60.0,       # Evidence quality
    TrustDimension.ORGANIZATION: 180.0,  # Org standing
    TrustDimension.NETWORK: 30.0,        # Network behavior changes fast
    TrustDimension.BEHAVIOR: 30.0,       # Behavioral patterns
}

MIN_SIGNALS_FOR_CONFIDENCE = 2


@dataclass
class TrustSignal:
    """A single trust signal for a node."""

    signal_id: str = field(default_factory=lambda: f"sig-{uuid.uuid4().hex[:12]}")
    node_id: str = ""
    dimension: TrustDimension = TrustDimension.IDENTITY
    source: str = "self_reported"
    kind: str = ""
    value: float = 0.0          # -1.0 to 1.0
    confidence: float = 0.5     # 0.0 to 1.0
    evidence_ref: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    decay_half_life_days: float = 90.0

    def decayed_value(self, at: float = None) -> float:
        """Get time-decayed value."""
        at = at or time.time()
        age_days = max(0.0, (at - self.created_at) / 86400.0)
        decay = 0.5 ** (age_days / self.decay_half_life_days)
        return self.value * decay

    def decayed_confidence(self, at: float = None) -> float:
        """Get time-decayed confidence."""
        at = at or time.time()
        age_days = max(0.0, (at - self.created_at) / 86400.0)
        decay = 0.5 ** (age_days / self.decay_half_life_days)
        return self.confidence * decay

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["dimension"] = self.dimension.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustSignal":
        dim_val = data.pop("dimension", "identity")
        sig = cls(**{k: v for k, v in data.items() if k in {f.name for f in cls.__dataclass_fields__.values()}})
        sig.dimension = TrustDimension(dim_val)
        return sig


@dataclass
class TrustAssessment:
    """Trust assessment for a node."""

    node_id: str = ""
    dimensions: Dict[TrustDimension, Dict[str, Any]] = field(default_factory=dict)
    overall_score: float = 0.0
    overall_confidence: float = 0.0
    flags: List[str] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)

    def get_level(self) -> str:
        """Get trust level label."""
        if self.overall_score >= 0.8 and self.overall_confidence >= 0.7:
            return "trusted"
        elif self.overall_score >= 0.6 and self.overall_confidence >= 0.6:
            return "verified"
        elif self.overall_score >= 0.4:
            return "medium"
        elif self.overall_score >= 0.2:
            return "low"
        return "untrusted"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["dimensions"] = {k.value: v for k, v in self.dimensions.items()}
        return d


class MeshTrust:
    """Multidimensional trust engine for mesh nodes."""

    def __init__(self, home: Path, mesh_id: str = ""):
        self.home = Path(home)
        self.mesh_id = mesh_id
        self._signals_file = self.home / "mesh_trust_signals.json"
        self._signals: Dict[str, TrustSignal] = {}
        self._load_signals()

    def _load_signals(self) -> None:
        """Load trust signals from disk."""
        if self._signals_file.exists():
            try:
                data = json.loads(self._signals_file.read_text(encoding="utf-8"))
                for sig_data in data.get("signals", []):
                    sig = TrustSignal.from_dict(sig_data)
                    self._signals[sig.signal_id] = sig
                logger.info(f"Loaded {len(self._signals)} trust signals")
            except Exception as e:
                logger.warning(f"Failed to load trust signals: {e}")

    def _save_signals(self) -> None:
        """Save trust signals to disk."""
        try:
            self.home.mkdir(parents=True, exist_ok=True)
            data = {
                "signals": [s.to_dict() for s in self._signals.values()],
                "mesh_id": self.mesh_id,
                "saved_at": time.time(),
            }
            tmp = self._signals_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(self._signals_file)
        except Exception as e:
            logger.warning(f"Failed to save trust signals: {e}")

    def record_signal(self, signal: TrustSignal) -> TrustSignal:
        """Record a trust signal."""
        if signal.dimension not in TrustDimension:
            raise ValueError(f"bad dimension: {signal.dimension!r}")
        if not (-1.0 <= signal.value <= 1.0):
            raise ValueError("signal value must be in [-1, 1]")
        if not (0.0 <= signal.confidence <= 1.0):
            raise ValueError("signal confidence must be in [0, 1]")
        if signal.source not in _SOURCE_WEIGHT:
            raise ValueError(f"unknown source: {signal.source!r}")

        # Set dimension-appropriate decay
        signal.decay_half_life_days = _DIMENSION_DECAY.get(signal.dimension, 90.0)

        self._signals[signal.signal_id] = signal
        self._save_signals()
        return signal

    def record_identity_verification(
        self,
        node_id: str,
        verified: bool,
        method: str = "tls+issuer",
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record identity verification result."""
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.IDENTITY,
            source="verification",
            kind="identity_verified" if verified else "identity_failed",
            value=0.8 if verified else -0.8,
            confidence=0.9,
            evidence_ref=evidence_ref,
            provenance={"method": method},
        ))

    def record_security_incident(
        self,
        node_id: str,
        incident_kind: str,
        severity: float = 0.5,  # 0.0 - 1.0
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record a security incident."""
        # Negative signal for security dimension
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.SECURITY,
            source="security",
            kind=f"incident_{incident_kind}",
            value=-severity,
            confidence=0.9,
            evidence_ref=evidence_ref,
            provenance={"incident_kind": incident_kind, "severity": severity},
            decay_half_life_days=180.0,
        ))

    def record_execution_outcome(
        self,
        node_id: str,
        success: bool,
        task_class: str = "",
        latency_ms: Optional[float] = None,
        cost_usd: Optional[float] = None,
        sla_met: Optional[bool] = None,
        verified: bool = False,
        evidence_ref: str = ""
    ) -> List[TrustSignal]:
        """Record task execution outcome across relevant dimensions."""
        signals = []
        source = "outcome" if not verified else "verification"

        # Execution dimension
        signals.append(self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.EXECUTION,
            source=source,
            kind="task_success" if success else "task_failure",
            value=0.5 if success else -0.5,
            confidence=0.8 if verified else 0.6,
            evidence_ref=evidence_ref,
            provenance={"task_class": task_class, "verified": verified},
        )))

        # Latency
        if latency_ms is not None:
            # Attainment vs 60s budget
            attain = max(0.0, min(1.0, 1.0 - latency_ms / 60000.0))
            signals.append(self.record_signal(TrustSignal(
                node_id=node_id,
                dimension=TrustDimension.EXECUTION,
                source=source,
                kind="latency",
                value=(attain - 0.5) * 2,  # Map 0-1 to -1 to 1
                confidence=0.7,
                evidence_ref=evidence_ref,
                provenance={"latency_ms": latency_ms, "task_class": task_class},
            )))

        # SLA adherence
        if sla_met is not None:
            signals.append(self.record_signal(TrustSignal(
                node_id=node_id,
                dimension=TrustDimension.EXECUTION,
                source=source,
                kind="sla_adherence",
                value=0.5 if sla_met else -0.5,
                confidence=0.7,
                evidence_ref=evidence_ref,
                provenance={"sla_met": sla_met, "task_class": task_class},
            )))

        # Economic dimension
        if cost_usd is not None:
            # Fair pricing signal (simplified)
            signals.append(self.record_signal(TrustSignal(
                node_id=node_id,
                dimension=TrustDimension.ECONOMIC,
                source=source,
                kind="pricing",
                value=0.2,  # Slightly positive for transparent pricing
                confidence=0.5,
                evidence_ref=evidence_ref,
                provenance={"cost_usd": cost_usd, "task_class": task_class},
            )))

        return signals

    def record_evidence_quality(
        self,
        node_id: str,
        evidence_score: float,  # 0.0 - 1.0
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record evidence quality assessment."""
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.EVIDENCE,
            source="outcome",
            kind="evidence_quality",
            value=(evidence_score - 0.5) * 2,  # Map to -1 to 1
            confidence=0.7,
            evidence_ref=evidence_ref,
        ))

    def record_organizational_attestation(
        self,
        node_id: str,
        org_id: str,
        attested: bool,
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record organizational attestation."""
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.ORGANIZATION,
            source="organization",
            kind="org_attestation",
            value=0.7 if attested else -0.7,
            confidence=0.8,
            evidence_ref=evidence_ref,
            provenance={"org_id": org_id},
        ))

    def record_network_behavior(
        self,
        node_id: str,
        behavior_kind: str,
        value: float,  # -1.0 to 1.0
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record network behavior observation."""
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.NETWORK,
            source="observation",
            kind=f"network_{behavior_kind}",
            value=value,
            confidence=0.6,
            evidence_ref=evidence_ref,
            decay_half_life_days=30.0,
        ))

    def record_behavioral_anomaly(
        self,
        node_id: str,
        anomaly_kind: str,
        severity: float = 0.5,
        evidence_ref: str = ""
    ) -> TrustSignal:
        """Record behavioral anomaly (negative signal)."""
        return self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.BEHAVIOR,
            source="observation",
            kind=f"anomaly_{anomaly_kind}",
            value=-severity,
            confidence=0.7,
            evidence_ref=evidence_ref,
            provenance={"anomaly_kind": anomaly_kind, "severity": severity},
            decay_half_life_days=30.0,
        ))

    def _get_signals(
        self,
        node_id: str,
        dimension: Optional[TrustDimension] = None,
        at: Optional[float] = None
    ) -> List[TrustSignal]:
        """Get signals for a node, optionally filtered by dimension."""
        out = []
        for sig in self._signals.values():
            if sig.node_id != node_id:
                continue
            if dimension and sig.dimension != dimension:
                continue
            out.append(sig)
        return out

    def assess_dimension(
        self,
        node_id: str,
        dimension: TrustDimension,
        at: Optional[float] = None
    ) -> Dict[str, Any]:
        """Assess trust for a single dimension."""
        sigs = self._get_signals(node_id, dimension, at)

        if not sigs:
            return {
                "dimension": dimension.value,
                "score": 0.0,
                "confidence": 0.0,
                "samples": 0,
                "provenance": [],
            }

        at = at or time.time()
        num = 0.0
        den = 0.0
        provenance = []

        for sig in sigs:
            w = _SOURCE_WEIGHT.get(sig.source, 0.4) * sig.decayed_confidence(at)
            v = sig.decayed_value(at)
            num += w * v
            den += w
            provenance.append({
                "signal_id": sig.signal_id,
                "source": sig.source,
                "kind": sig.kind,
                "decayed_value": round(v, 4),
                "weight": round(w, 4),
                "at": sig.created_at,
                "evidence_ref": sig.evidence_ref,
            })

        score = num / den if den else 0.0
        # Confidence based on signal count, weight, and diversity
        sources = set(s.source for s in sigs)
        diversity = min(1.0, len(sources) / 3.0)
        depth = min(1.0, len(sigs) / 10.0)
        weight_mass = min(1.0, den / 5.0)
        confidence = round(0.4 * depth + 0.3 * diversity + 0.3 * weight_mass, 4)

        return {
            "dimension": dimension.value,
            "score": round(score, 4),
            "confidence": confidence,
            "samples": len(sigs),
            "provenance": provenance,
        }

    def assess_node(self, node_id: str, at: Optional[float] = None) -> TrustAssessment:
        """Full multidimensional trust assessment for a node."""
        at = at or time.time()
        dimensions = {}
        flags = []

        for dim in TrustDimension:
            dimensions[dim] = self.assess_dimension(node_id, dim, at)

        # Compute overall score (confidence-weighted mean)
        num = sum(d["score"] * d["confidence"] for d in dimensions.values())
        den = sum(d["confidence"] for d in dimensions.values())
        overall_score = num / den if den else 0.0
        overall_confidence = den / len(TrustDimension) if den else 0.0

        # Generate flags
        total_samples = sum(d["samples"] for d in dimensions.values())
        if total_samples < MIN_SIGNALS_FOR_CONFIDENCE:
            flags.append("insufficient_evidence")

        # Check for security flags
        sec = dimensions.get(TrustDimension.SECURITY, {})
        if sec.get("score", 0) < -0.3:
            flags.append("security_concerns")

        # Check for behavioral flags
        beh = dimensions.get(TrustDimension.BEHAVIOR, {})
        if beh.get("score", 0) < -0.3:
            flags.append("behavioral_anomalies")

        # Check for network flags
        net = dimensions.get(TrustDimension.NETWORK, {})
        if net.get("score", 0) < -0.3:
            flags.append("network_issues")

        return TrustAssessment(
            node_id=node_id,
            dimensions=dimensions,
            overall_score=round(overall_score, 4),
            overall_confidence=round(overall_confidence, 4),
            flags=flags,
            assessed_at=at,
        )

    def assess_nodes(self, node_ids: List[str], at: Optional[float] = None) -> Dict[str, TrustAssessment]:
        """Batch assess multiple nodes (single pass for efficiency)."""
        at = at or time.time()

        # Group signals by node and dimension in one pass
        by_node_dim: Dict[str, Dict[TrustDimension, List[TrustSignal]]] = {}
        for sig in self._signals.values():
            if sig.node_id not in node_ids:
                continue
            by_node_dim.setdefault(sig.node_id, {}).setdefault(sig.dimension, []).append(sig)

        results = {}
        for node_id in node_ids:
            dimensions = {}
            for dim in TrustDimension:
                sigs = by_node_dim.get(node_id, {}).get(dim, [])
                if not sigs:
                    dimensions[dim] = {
                        "dimension": dim.value,
                        "score": 0.0,
                        "confidence": 0.0,
                        "samples": 0,
                        "provenance": [],
                    }
                else:
                    # Aggregate (same logic as assess_dimension)
                    num = den = 0.0
                    provenance = []
                    for sig in sigs:
                        w = _SOURCE_WEIGHT.get(sig.source, 0.4) * sig.decayed_confidence(at)
                        v = sig.decayed_value(at)
                        num += w * v
                        den += w
                        provenance.append({
                            "signal_id": sig.signal_id,
                            "source": sig.source,
                            "kind": sig.kind,
                            "decayed_value": round(v, 4),
                            "weight": round(w, 4),
                            "at": sig.created_at,
                            "evidence_ref": sig.evidence_ref,
                        })
                    score = num / den if den else 0.0
                    sources = set(s.source for s in sigs)
                    diversity = min(1.0, len(sources) / 3.0)
                    depth = min(1.0, len(sigs) / 10.0)
                    weight_mass = min(1.0, den / 5.0)
                    confidence = round(0.4 * depth + 0.3 * diversity + 0.3 * weight_mass, 4)
                    dimensions[dim] = {
                        "dimension": dim.value,
                        "score": round(score, 4),
                        "confidence": confidence,
                        "samples": len(sigs),
                        "provenance": provenance,
                    }

            num = sum(d["score"] * d["confidence"] for d in dimensions.values())
            den = sum(d["confidence"] for d in dimensions.values())
            overall_score = num / den if den else 0.0
            overall_confidence = den / len(TrustDimension) if den else 0.0

            flags = []
            total_samples = sum(d["samples"] for d in dimensions.values())
            if total_samples < MIN_SIGNALS_FOR_CONFIDENCE:
                flags.append("insufficient_evidence")

            results[node_id] = TrustAssessment(
                node_id=node_id,
                dimensions=dimensions,
                overall_score=round(overall_score, 4),
                overall_confidence=round(overall_confidence, 4),
                flags=flags,
                assessed_at=at,
            )

        return results

    def rank_nodes(self, node_ids: List[str], at: Optional[float] = None) -> Dict[str, float]:
        """Rank nodes by overall trust score."""
        assessments = self.assess_nodes(node_ids, at)
        return {nid: a.overall_score for nid, a in assessments.items()}

    def get_trust_graph(self, node_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get trust relationships as a graph."""
        nodes = node_ids or list(set(s.node_id for s in self._signals.values()))
        assessments = self.assess_nodes(nodes)

        return {
            "nodes": {nid: a.to_dict() for nid, a in assessments.items()},
            "edges": [],  # Could add trust edges between nodes
            "generated_at": time.time(),
        }

    def detect_correlated_agents(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Detect potentially correlated agents (Sybil/collusion detection)."""
        # Get all signals for these nodes
        signals_by_node = {nid: [] for nid in node_ids}
        for sig in self._signals.values():
            if sig.node_id in signals_by_node:
                signals_by_node[sig.node_id].append(sig)

        correlations = []

        # Check for single-org dominance
        for i, id1 in enumerate(node_ids):
            for id2 in node_ids[i+1:]:
                sigs1 = signals_by_node.get(id1, [])
                sigs2 = signals_by_node.get(id2, [])

                # Check organization overlap
                orgs1 = set(s.provenance.get("org_id", "") for s in sigs1 if s.provenance.get("org_id"))
                orgs2 = set(s.provenance.get("org_id", "") for s in sigs2 if s.provenance.get("org_id"))

                if orgs1 & orgs2:
                    overlap = len(orgs1 & orgs2) / max(len(orgs1 | orgs2), 1)
                    if overlap > 0.5:
                        correlations.append({
                            "type": "shared_organization",
                            "nodes": [id1, id2],
                            "overlap": overlap,
                            "orgs": list(orgs1 & orgs2),
                        })

                # Check reviewer overlap (for user feedback)
                reviewers1 = set(s.provenance.get("reviewer", "") for s in sigs1
                               if s.source == "user_feedback" and s.provenance.get("reviewer"))
                reviewers2 = set(s.provenance.get("reviewer", "") for s in sigs2
                               if s.source == "user_feedback" and s.provenance.get("reviewer"))

                if reviewers1 & reviewers2:
                    overlap = len(reviewers1 & reviewers2) / max(len(reviewers1 | reviewers2), 1)
                    if overlap > 0.5 and len(reviewers1) >= 3:
                        correlations.append({
                            "type": "shared_reviewers",
                            "nodes": [id1, id2],
                            "overlap": overlap,
                            "reviewers": list(reviewers1 & reviewers2),
                        })

        return correlations

    def apply_mesh_node_trust(self, node: MeshNode) -> None:
        """Update a MeshNode's trust scores from this engine."""
        assessment = self.assess_node(node.node_id)
        for dim, data in assessment.dimensions.items():
            node.update_trust(dim, max(0.0, (data["score"] + 1.0) / 2.0))  # Map -1..1 to 0..1
        node.metadata["trust_assessment"] = assessment.to_dict()
        node.metadata["trust_level"] = assessment.get_level()


def create_trust_engine_from_market(home: Path, mesh_id: str = "") -> MeshTrust:
    """Create a MeshTrust engine that also ingests market reputation data."""
    engine = MeshTrust(home, mesh_id)

    try:
        from aetheros_agent_market.reputation import ReputationEngine
        from aetheros_agent_market.trust_engine import AgentTrustEngine

        # These would be integrated to feed signals
        # For now, just create the mesh trust engine
        logger.info("Market reputation integration available but not auto-wired")
    except ImportError:
        pass

    return engine