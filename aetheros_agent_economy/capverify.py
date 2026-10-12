"""Capability verification + advertisement + drift (spec sections 13-15).

Advertised information is UNTRUSTED until verified where possible.
Statuses: DECLARED (claimed) / OBSERVED (seen in outcomes) / VERIFIED
(evidence-backed). Never treat DECLARED as VERIFIED. Changes to
capabilities/versions/endpoints/scopes trigger re-verification.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_agent_market.store import JsonStore

VERIFICATION_STATUS = ("DECLARED", "OBSERVED", "VERIFIED")
VERIFICATION_SOURCES = ("agent_card", "protocol", "benchmark", "history",
                        "probe", "attestation", "provider_evidence")


@dataclass
class CapabilityAttestation:
    capability_id: str
    agent_id: str
    status: str = "DECLARED"  # DECLARED|OBSERVED|VERIFIED
    sources: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityAttestation":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Advertisement:
    """One provider advertisement batch. Stored verbatim + marked untrusted."""

    advertisement_id: str = ""
    agent_id: str = ""
    capabilities: List[Dict[str, Any]] = field(default_factory=list)
    capacity: Dict[str, Any] = field(default_factory=dict)
    pricing: Dict[str, Any] = field(default_factory=dict)
    sla: Dict[str, Any] = field(default_factory=dict)
    regions: List[str] = field(default_factory=list)
    data_policies: List[str] = field(default_factory=list)
    trusted: bool = False  # always False on intake
    received_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _new_id(prefix: str) -> str:
    import secrets
    return f"{prefix}-{secrets.token_hex(8)}"


class CapabilityVerificationEngine:
    """Grades capability claims using live evidence sources."""

    def __init__(self, home: Path, market_flow=None) -> None:
        self._attest = JsonStore(Path(home) / "capability_attestations.json")
        self._ads = JsonStore(Path(home) / "capability_advertisements.json")
        self._flow = market_flow

    # -- advertisement intake (untrusted) ----------------------------------
    def advertise(self, agent_id: str, payload: Dict[str, Any]) -> Advertisement:
        if not agent_id or len(agent_id) > 160:
            raise ValueError("invalid agent_id")
        if not isinstance(payload, dict):
            raise ValueError("advertisement payload must be an object")
        caps = payload.get("capabilities", []) or []
        if not isinstance(caps, list) or len(caps) > 100:
            raise ValueError("capabilities must be a list (<=100)")
        ad = Advertisement(
            advertisement_id=_new_id("ad"), agent_id=agent_id,
            capabilities=[c for c in caps if isinstance(c, dict)][:100],
            capacity=payload.get("capacity", {}) if isinstance(
                payload.get("capacity"), dict) else {},
            pricing=payload.get("pricing", {}) if isinstance(
                payload.get("pricing"), dict) else {},
            sla=payload.get("sla", {}) if isinstance(
                payload.get("sla"), dict) else {},
            regions=[str(r)[:80] for r in (payload.get("regions", []) or [])][:20],
            data_policies=[str(d)[:80] for d in (payload.get("data_policies", []) or [])][:20],
            trusted=False)
        self._ads.put(ad.advertisement_id, ad.to_dict())
        # Every advertised capability starts at DECLARED (never higher).
        for cap in ad.capabilities:
            cid = str(cap.get("capability_id", ""))
            if cid:
                self._set_status(agent_id, cid, "DECLARED",
                                 sources=["advertisement"],
                                 detail={"advertisement_id": ad.advertisement_id})
        return ad

    # -- verification -------------------------------------------------------
    def _key(self, agent_id: str, capability_id: str) -> str:
        return f"{agent_id}::{capability_id}"

    def _set_status(self, agent_id: str, capability_id: str, status: str,
                    sources: Optional[List[str]] = None,
                    evidence_refs: Optional[List[str]] = None,
                    detail: Optional[Dict[str, Any]] = None) -> CapabilityAttestation:
        if status not in VERIFICATION_STATUS:
            raise ValueError(f"bad status: {status!r}")
        key = self._key(agent_id, capability_id)
        raw = self._attest.get(key)
        att = CapabilityAttestation.from_dict(raw) if raw else CapabilityAttestation(
            capability_id=capability_id, agent_id=agent_id)
        # Status only moves by evidence, and VERIFIED requires >=2 sources
        # with at least one of {benchmark, history, probe}.
        if status == "VERIFIED":
            strong = {"benchmark", "history", "probe"}
            have = set(att.sources) | set(sources or [])
            if not (strong & have) or len(have) < 2:
                raise ValueError(
                    "VERIFIED requires >=2 sources incl. benchmark/history/probe")
        att.status = status
        for s in (sources or []):
            if s in VERIFICATION_SOURCES and s not in att.sources:
                att.sources.append(s)
        for e in (evidence_refs or []):
            if e not in att.evidence_refs:
                att.evidence_refs.append(e)
        if detail:
            att.detail.update(detail)
        att.updated_at = time.time()
        self._attest.put(key, att.to_dict())
        return att

    def mark_observed(self, agent_id: str, capability_id: str,
                      evidence_ref: str = "") -> CapabilityAttestation:
        """A real successful outcome was seen (call from settlement paths)."""
        return self._set_status(agent_id, capability_id, "OBSERVED",
                                sources=["history"],
                                evidence_refs=[evidence_ref] if evidence_ref else [])

    def verify(self, agent_id: str, capability_id: str,
               sources: List[str],
               evidence_refs: Optional[List[str]] = None) -> CapabilityAttestation:
        """Promote to VERIFIED when evidence rules pass (raises otherwise)."""
        return self._set_status(agent_id, capability_id, "VERIFIED",
                                sources=sources, evidence_refs=evidence_refs)

    def status(self, agent_id: str, capability_id: str) -> CapabilityAttestation:
        raw = self._attest.get(self._key(agent_id, capability_id))
        if raw:
            return CapabilityAttestation.from_dict(raw)
        return CapabilityAttestation(capability_id=capability_id, agent_id=agent_id)

    # -- evidence-backed auto-grading ----------------------------------------
    def grade_from_history(self, agent_id: str, capability_id: str,
                           min_verified_successes: int = 3) -> CapabilityAttestation:
        """OBSERVED/VERIFIED purely from verified outcome counts.

        Reads the market reputation engine: only `verified` provenance
        counts. No name-based inference, no self-reports.
        """
        if self._flow is None:
            raise ValueError("grade_from_history needs market flow (evidence source)")
        profile = self._flow.reputation.profile(agent_id)
        verified = None
        for m in ("verified_success", "task_success"):
            metric = profile.metrics.get(m)
            if metric and metric.get("provenance") == "verified" \
                    and metric.get("sample_count", 0) >= min_verified_successes \
                    and metric.get("value", 0.0) >= 0.8:
                verified = metric
                break
        if verified is not None:
            return self._set_status(
                agent_id, capability_id, "VERIFIED",
                sources=["history", "benchmark"] if verified.get("sample_count", 0) >= 10
                else ["history", "attestation"],
                detail={"verified_value": verified.get("value"),
                        "samples": verified.get("sample_count")})
        # Fall back: any verified samples at all => OBSERVED.
        for m in ("verified_success", "task_success"):
            metric = profile.metrics.get(m)
            if metric and metric.get("provenance") == "verified" \
                    and metric.get("sample_count", 0) >= 1:
                return self._set_status(agent_id, capability_id, "OBSERVED",
                                        sources=["history"])
        return self.status(agent_id, capability_id)

    # -- drift detection -------------------------------------------------------
    def detect_drift(self, agent_id: str,
                     current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare a fresh advertisement/card snapshot vs the last one.

        Detects: capability added/removed/changed, version/endpoint/
        security-scope changes. Any drift => reverify_required.
        """
        if not isinstance(current, dict):
            raise ValueError("snapshot must be an object")
        key = f"snapshot::{agent_id}"
        prior_raw = self._ads.get(key)
        drift: List[Dict[str, str]] = []
        if prior_raw is None:
            self._ads.put(key, {"snapshot": current, "at": time.time()})
            return {"drift": [], "reverify_required": False,
                    "reason": "first snapshot recorded"}
        prior = prior_raw.get("snapshot", {})
        for field in ("capabilities", "version", "endpoint", "security_scopes",
                      "url", "auth_schemes"):
            old, new = prior.get(field), current.get(field)
            if old != new:
                drift.append({"field": field, "kind": self._drift_kind(field, old, new)})
        self._ads.put(key, {"snapshot": current, "at": time.time()})
        return {"drift": drift, "reverify_required": bool(drift),
                "reason": f"{len(drift)} changed field(s)" if drift else "no drift"}

    @staticmethod
    def _drift_kind(field: str, old: Any, new: Any) -> str:
        if old is None:
            return "added"
        if new is None:
            return "removed"
        return "changed"
