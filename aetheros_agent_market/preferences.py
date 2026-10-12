"""User / org preferences as enforceable policy (spec sections 10 + 115).

Example: "Never delegate private documents to public agents" becomes a
real MatchRequest constraint + selection veto, not a suggestion.

Conflict hierarchy (spec 115):
security > privacy > authorization > budget > user preference > optimization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import taxonomy as T
from .store import JsonStore


@dataclass
class AgentPreferences:
    preferred_agents: List[str] = field(default_factory=list)
    blocked_agents: List[str] = field(default_factory=list)
    preferred_orgs: List[str] = field(default_factory=list)
    blocked_orgs: List[str] = field(default_factory=list)
    min_trust_rank: int = 3
    max_price_minor: Optional[int] = None
    max_latency_ms: Optional[float] = None
    max_data_class: str = "INTERNAL"   # ceiling of what may leave local
    data_residency: List[str] = field(default_factory=list)  # allowed regions
    required_sla: Dict[str, Any] = field(default_factory=dict)
    allowed_protocols: List[str] = field(default_factory=list)
    allowed_regions: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    payment_limit_minor: Optional[int] = None
    require_approval_above_minor: int = 0
    approvals_required: bool = False   # human approval for every delegation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPreferences":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


DEFAULT_PREFERENCES = AgentPreferences()


class PreferenceStore:
    """Per-scope preferences: global|user|org|project. Most specific wins,
    except security/privacy floors which only ever tighten (115)."""

    def __init__(self, home: Path) -> None:
        self._store = JsonStore(Path(home) / "preferences.json")

    def get(self, scope: str = "global", scope_id: str = "") -> AgentPreferences:
        raw = self._store.get(f"{scope}:{scope_id}")
        if not raw:
            return AgentPreferences()
        return AgentPreferences.from_dict(raw)

    def put(self, prefs: AgentPreferences, scope: str = "global",
            scope_id: str = "") -> None:
        self._store.put(f"{scope}:{scope_id}", prefs.to_dict())

    def effective(self, scopes: Optional[List[Dict[str, str]]] = None) -> AgentPreferences:
        """Merge global -> user -> org -> project. Security floors tighten."""
        merged = AgentPreferences()
        chain = [{"scope": "global", "scope_id": ""}] + (scopes or [])
        for item in chain:
            p = self.get(item.get("scope", "global"), item.get("scope_id", ""))
            if p.preferred_agents:
                merged.preferred_agents = p.preferred_agents
            merged.blocked_agents = sorted(set(merged.blocked_agents) | set(p.blocked_agents))
            if p.preferred_orgs:
                merged.preferred_orgs = p.preferred_orgs
            merged.blocked_orgs = sorted(set(merged.blocked_orgs) | set(p.blocked_orgs))
            merged.min_trust_rank = max(merged.min_trust_rank, p.min_trust_rank)
            for attr in ("max_price_minor", "max_latency_ms", "payment_limit_minor"):
                v = getattr(p, attr)
                if v is not None and (getattr(merged, attr) is None or v < getattr(merged, attr)):
                    setattr(merged, attr, v)
            # Data ceiling only tightens.
            order = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "PRIVATE", "HIGHLY_SENSITIVE"]
            if order.index(p.max_data_class) < order.index(merged.max_data_class):
                merged.max_data_class = p.max_data_class
            if p.data_residency:
                merged.data_residency = p.data_residency
            if p.required_sla:
                merged.required_sla = p.required_sla
            if p.allowed_protocols:
                merged.allowed_protocols = p.allowed_protocols
            if p.allowed_regions:
                merged.allowed_regions = p.allowed_regions
            if p.allowed_domains:
                merged.allowed_domains = p.allowed_domains
            merged.require_approval_above_minor = max(
                merged.require_approval_above_minor, p.require_approval_above_minor)
            merged.approvals_required = merged.approvals_required or p.approvals_required
        return merged


def apply_preferences(req: T.MatchRequest, prefs: AgentPreferences) -> T.MatchRequest:
    """Fold preferences into a discovery request (real policy)."""
    req.min_trust_rank = max(req.min_trust_rank, prefs.min_trust_rank)
    if prefs.max_price_minor is not None:
        req.max_price_minor = prefs.max_price_minor if req.max_price_minor is None \
            else min(req.max_price_minor, prefs.max_price_minor)
    if prefs.max_latency_ms is not None:
        req.max_latency_ms = prefs.max_latency_ms if req.max_latency_ms is None \
            else min(req.max_latency_ms, prefs.max_latency_ms)
    req.exclude_agents = sorted(set(req.exclude_agents) | set(prefs.blocked_agents))
    # Data ceiling: request may only LOWER sensitivity, never raise it.
    order = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "PRIVATE", "HIGHLY_SENSITIVE"]
    if order.index(prefs.max_data_class) < order.index(req.data_class):
        req.data_class = prefs.max_data_class
    if prefs.allowed_protocols:
        req.protocols = prefs.allowed_protocols
    if prefs.allowed_regions:
        req.allowed_regions = prefs.allowed_regions
    return req


def preference_veto(agent_id: str, org_id: str, prefs: AgentPreferences) -> Optional[str]:
    """Hard vetoes evaluated at selection time. Returns reason or None."""
    if agent_id in prefs.blocked_agents:
        return f"agent {agent_id} is user-blocked"
    if org_id and org_id in prefs.blocked_orgs:
        return f"organization {org_id} is user-blocked"
    return None
