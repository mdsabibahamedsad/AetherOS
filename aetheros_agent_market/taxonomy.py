"""Capability taxonomy + deterministic matching (spec section 3).

Deterministic constraints FIRST (exact capability, protocol, modality,
trust, cost, latency, geography, data class, availability, version).
Keyword overlap is a secondary relevance signal — never the only filter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# Canonical taxonomy: category -> capabilities. Service capabilities MUST
# use these ids (or dotted extensions) to be exactly matchable.
TAXONOMY: Dict[str, List[str]] = {
    "research": [
        "research.web_search", "research.deep_research", "research.market_research",
        "research.academic_search", "research.source_compare", "research.citation_verify",
    ],
    "coding": [
        "coding.code_write", "coding.code_review", "coding.software_testing",
        "coding.refactor", "coding.infra_diagnostics",
    ],
    "documents": [
        "documents.extract", "documents.classify", "documents.summarize",
        "documents.translate", "documents.legal_extract",
    ],
    "media": [
        "media.image_analysis", "media.video_process", "media.audio_transcribe",
    ],
    "data": [
        "data.analyze", "data.spreadsheet_analyze", "data.visualize", "data.clean",
    ],
    "browser": [
        "browser.automate", "browser.scrape", "browser.test",
    ],
    "support": [
        "support.customer_support", "support.triage",
    ],
}

# Keyword aliases -> taxonomy ids (secondary signal only).
KEYWORD_INDEX: Dict[str, List[str]] = {
    "research": ["research.web_search", "research.deep_research", "research.market_research"],
    "market": ["research.market_research"],
    "coding": ["coding.code_write", "coding.code_review", "coding.refactor"],
    "code": ["coding.code_write", "coding.code_review", "coding.refactor"],
    "testing": ["coding.software_testing", "browser.test"],
    "test": ["coding.software_testing", "browser.test"],
    "legal": ["documents.legal_extract"],
    "extract": ["documents.extract", "documents.legal_extract"],
    "translate": ["documents.translate"],
    "translation": ["documents.translate"],
    "image": ["media.image_analysis"],
    "video": ["media.video_process"],
    "spreadsheet": ["data.spreadsheet_analyze"],
    "financial": ["data.spreadsheet_analyze", "research.market_research"],
    "browser": ["browser.automate", "browser.scrape"],
    "automation": ["browser.automate"],
    "support": ["support.customer_support"],
    "classify": ["documents.classify"],
    "diagnostics": ["coding.infra_diagnostics"],
    "infrastructure": ["coding.infra_diagnostics"],
    "summarize": ["documents.summarize"],
    "citation": ["research.citation_verify"],
    "academic": ["research.academic_search"],
}

ALL_CAPABILITIES: Set[str] = {c for caps in TAXONOMY.values() for c in caps}


def normalize_capability(cap: str) -> str:
    return cap.strip().lower().replace("-", "_").replace(" ", "_")


def expand_query_terms(query: str) -> Set[str]:
    """Map free text to candidate taxonomy ids (secondary signal)."""
    terms = {t.strip().lower() for t in query.replace(",", " ").split() if t.strip()}
    out: Set[str] = set()
    for term in terms:
        if term in ALL_CAPABILITIES:
            out.add(term)
        for kw, caps in KEYWORD_INDEX.items():
            if kw in term or term in kw:
                out.update(caps)
    return out


@dataclass
class MatchRequest:
    query: str = ""
    exact_capabilities: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)      # must support one of
    modalities: List[str] = field(default_factory=list)
    min_trust_rank: int = 0
    max_price_minor: Optional[int] = None
    max_latency_ms: Optional[float] = None
    allowed_regions: List[str] = field(default_factory=list)
    data_class: str = "INTERNAL"                            # required ceiling
    availability: List[str] = field(default_factory=lambda: ["available", "limited"])
    exclude_agents: List[str] = field(default_factory=list)
    only_agents: List[str] = field(default_factory=list)


_DATA_ORDER = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "PRIVATE", "HIGHLY_SENSITIVE"]


def data_class_allows(agent_classes: List[str], required: str) -> bool:
    """Agent must accept the required class or a HIGHER (more sensitive) one."""
    if not agent_classes:
        return False
    try:
        need = _DATA_ORDER.index(required.upper())
    except ValueError:
        return False
    for cls in agent_classes:
        try:
            if _DATA_ORDER.index(cls.upper()) >= need:
                return True
        except ValueError:
            continue
    return False


@dataclass
class CapabilityHit:
    service_id: str
    agent_id: str
    exact: bool
    keyword_score: float
    reasons: List[str] = field(default_factory=list)


def match_service(service: Dict[str, Any], req: MatchRequest,
                  agent_trust_rank: int = 0,
                  price_minor: Optional[int] = None,
                  latency_ms: Optional[float] = None,
                  regions: Optional[List[str]] = None) -> Optional[CapabilityHit]:
    """Deterministic constraint pipeline. Returns None when rejected.

    Order: identity/org filters -> exact capability -> protocol ->
    modality -> trust -> cost -> latency -> geography -> data class ->
    availability. Keyword relevance only ranks survivors.
    """
    agent_id = str(service.get("agent_id", ""))
    service_id = str(service.get("service_id", ""))
    if req.only_agents and agent_id not in req.only_agents:
        return None
    if agent_id in req.exclude_agents:
        return None

    caps = service.get("capabilities", []) or []
    cap_ids = set()
    for c in caps:
        if isinstance(c, dict):
            cap_ids.add(normalize_capability(str(c.get("capability_id", ""))))
        else:
            cap_ids.add(normalize_capability(str(c)))

    reasons: List[str] = []
    exact = False
    if req.exact_capabilities:
        wanted = {normalize_capability(c) for c in req.exact_capabilities}
        matched = wanted & cap_ids
        # dotted-prefix match: "research" matches "research.web_search"
        for w in wanted - matched:
            if any(c == w or c.startswith(w + ".") for c in cap_ids):
                matched.add(w)
        if not matched:
            return None
        exact = True
        reasons.append(f"exact capability: {sorted(matched)}")

    if req.protocols:
        supported = {str(p).upper() for p in service.get("supported_protocols", [])}
        if not supported.intersection({p.upper() for p in req.protocols}):
            return None
        reasons.append("protocol compatible")

    if req.modalities:
        supported = {str(m).lower() for m in service.get("supported_modalities", [])}
        if not supported.intersection({m.lower() for m in req.modalities}):
            return None
        reasons.append("modality compatible")

    if agent_trust_rank < req.min_trust_rank:
        return None
    if req.min_trust_rank:
        reasons.append(f"trust rank {agent_trust_rank} >= {req.min_trust_rank}")

    if req.max_price_minor is not None and price_minor is not None:
        if price_minor > req.max_price_minor:
            return None
        reasons.append(f"price {price_minor} <= {req.max_price_minor}")

    if req.max_latency_ms is not None and latency_ms is not None:
        if latency_ms > req.max_latency_ms:
            return None
        reasons.append(f"latency {latency_ms} <= {req.max_latency_ms}")

    if req.allowed_regions and regions is not None:
        blocked = [r for r in regions if r not in req.allowed_regions]
        if blocked:
            return None
        reasons.append("region allowed")

    agent_classes: List[str] = []
    for c in caps:
        if isinstance(c, dict):
            agent_classes.extend([str(x) for x in c.get("data_classes", [])])
    if not data_class_allows(agent_classes, req.data_class):
        return None
    reasons.append(f"data class {req.data_class} accepted")

    if str(service.get("availability", "unknown")) not in req.availability:
        return None
    if service.get("status") not in ("published",):
        return None

    # Secondary relevance signal only.
    query_ids = expand_query_terms(req.query) if req.query else set()
    keyword_score = 0.0
    if query_ids:
        overlap = query_ids & cap_ids
        keyword_score = len(overlap) / max(len(query_ids), 1)
        reasons.append(f"keyword overlap {len(overlap)}/{len(query_ids)}")

    return CapabilityHit(service_id=service_id, agent_id=agent_id,
                         exact=exact, keyword_score=keyword_score,
                         reasons=reasons)
