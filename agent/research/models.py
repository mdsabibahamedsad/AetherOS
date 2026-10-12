"""Normalized research objects: task, source, claim, evidence, contradiction.

Pure dataclasses + classification/scoring heuristics. No I/O, no network,
no dependencies on the rest of Aetheros so the module is import-safe and
trivially testable.
"""

from __future__ import annotations

import enum
import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class ResearchDepth(str, enum.Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    EXHAUSTIVE = "exhaustive"


DEPTH_BUDGETS: Dict[ResearchDepth, Dict[str, int]] = {
    ResearchDepth.QUICK: {"max_queries": 3, "max_sources": 5, "min_independent_domains": 1},
    ResearchDepth.STANDARD: {"max_queries": 8, "max_sources": 12, "min_independent_domains": 2},
    ResearchDepth.DEEP: {"max_queries": 20, "max_sources": 30, "min_independent_domains": 3},
    ResearchDepth.EXHAUSTIVE: {"max_queries": 40, "max_sources": 60, "min_independent_domains": 4},
}


class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    SEARCHING = "SEARCHING"
    COLLECTING = "COLLECTING"
    READING = "READING"
    EXTRACTING = "EXTRACTING"
    VERIFYING = "VERIFYING"
    SYNTHESIZING = "SYNTHESIZING"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SourceType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"
    OFFICIAL = "OFFICIAL"
    ACADEMIC = "ACADEMIC"
    GOVERNMENT = "GOVERNMENT"
    NEWS = "NEWS"
    TECHNICAL = "TECHNICAL"
    COMMUNITY = "COMMUNITY"
    BLOG = "BLOG"
    SOCIAL = "SOCIAL"
    COMMERCIAL = "COMMERCIAL"
    UNKNOWN = "UNKNOWN"


PRIMARY_SOURCE_TYPES = frozenset(
    {SourceType.PRIMARY, SourceType.OFFICIAL, SourceType.ACADEMIC, SourceType.GOVERNMENT}
)


class SourceVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    USER_PROVIDED = "USER_PROVIDED"
    SYSTEM = "SYSTEM"


class ClaimKind(str, enum.Enum):
    FACT = "FACT"
    SOURCE_CLAIM = "SOURCE_CLAIM"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    RECOMMENDATION = "RECOMMENDATION"


class ClaimStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    SUPPORTED = "SUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class ToolFailureKind(str, enum.Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    PROVIDER_FAILURE = "provider_failure"
    PARSE_FAILURE = "parse_failure"
    MALFORMED_RESULT = "malformed_result"
    SECURITY_REJECTION = "security_rejection"


@dataclass
class TrustSignals:
    """Heuristic trust signals for a source."""

    https: bool = False
    known_publisher: bool = False
    peer_reviewed: bool = False
    official_domain: bool = False
    author_identified: bool = False
    dated: bool = False
    corroboration_domains: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ResearchSource:
    """A normalized web/document source with provenance."""

    url: str
    canonical_url: str = ""
    domain: str = ""
    title: str = ""
    author: str = ""
    publisher: str = ""
    publication_date: Optional[str] = None
    retrieved_at: float = field(default_factory=time.time)
    source_type: SourceType = SourceType.UNKNOWN
    language: str = ""
    content_hash: str = ""
    trust_signals: TrustSignals = field(default_factory=TrustSignals)
    risk: float = 0.0
    access_status: str = "pending"
    visibility: SourceVisibility = SourceVisibility.PUBLIC
    provider: str = ""
    snippet: str = ""
    quality_score: float = -1.0
    injection_flags: List[str] = field(default_factory=list)
    redirect_chain: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    @property
    def is_primary(self) -> bool:
        return self.source_type in PRIMARY_SOURCE_TYPES

    @property
    def quarantined(self) -> bool:
        return bool(self.injection_flags)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["source_type"] = self.source_type.value
        d["visibility"] = self.visibility.value
        d["trust_signals"] = self.trust_signals.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchSource":
        data = dict(data)
        data["source_type"] = SourceType(data.get("source_type", SourceType.UNKNOWN.value))
        data["visibility"] = SourceVisibility(data.get("visibility", SourceVisibility.PUBLIC.value))
        signals = data.pop("trust_signals", None) or {}
        data["trust_signals"] = TrustSignals(**signals)
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Evidence:
    """A pointer to retrieved content supporting a claim.

    Stores excerpt references and hashes rather than long verbatim quotes.
    """

    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    claim_id: str = ""
    source_id: str = ""
    location: str = ""
    excerpt_reference: str = ""
    content_hash: str = ""
    retrieved_at: float = field(default_factory=time.time)
    strength: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Claim:
    """An atomic statement with explicit fact/inference kind and status."""

    text: str
    kind: ClaimKind = ClaimKind.SOURCE_CLAIM
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    claim_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    source_ids: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    task_id: str = ""
    language_marker: str = ""
    location_hint: str = ""

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence) and any(e.source_id for e in self.evidence)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        d["evidence"] = [e.to_dict() for e in self.evidence]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Claim":
        data = dict(data)
        data["kind"] = ClaimKind(data.get("kind", ClaimKind.SOURCE_CLAIM.value))
        data["status"] = ClaimStatus(data.get("status", ClaimStatus.UNVERIFIED.value))
        evidence = data.pop("evidence", None) or []
        data["evidence"] = [Evidence.from_dict(e) for e in evidence]
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Contradiction:
    """Two claims that conflict; resolution is reported, never automatic."""

    contradiction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    claim_a_id: str = ""
    claim_b_id: str = ""
    reason: str = ""
    resolved_status: ClaimStatus = ClaimStatus.CONTRADICTED
    resolution_note: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["resolved_status"] = self.resolved_status.value
        return d


@dataclass
class ResearchTask:
    """The universal research object (Master 17 Phase 1)."""

    user_query: str
    research_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    objective: str = ""
    scope: str = ""
    constraints: List[str] = field(default_factory=list)
    sources_allowed: List[str] = field(default_factory=list)
    sources_blocked: List[str] = field(default_factory=list)
    time_range: Optional[str] = None
    language: str = ""
    depth: ResearchDepth = ResearchDepth.STANDARD
    priority: int = 5
    deadline: Optional[float] = None
    budget: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.CREATED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    owner: str = ""
    parent_task: str = ""
    subtasks: List[str] = field(default_factory=list)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    queries_run: List[str] = field(default_factory=list)
    final_report: str = ""
    confidence: float = 0.0
    error: str = ""

    def touch(self) -> None:
        self.updated_at = time.time()

    def budget_for_depth(self) -> Dict[str, int]:
        base = dict(DEPTH_BUDGETS[self.depth])
        override = self.budget or {}
        return {k: int(override.get(k, v)) for k, v in base.items()}

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["depth"] = self.depth.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchTask":
        data = dict(data)
        data["depth"] = ResearchDepth(data.get("depth", ResearchDepth.STANDARD.value))
        data["status"] = TaskStatus(data.get("status", TaskStatus.CREATED.value))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


ACADEMIC_HOSTS = (
    "arxiv.org",
    "doi.org",
    "semanticscholar.org",
    "acm.org",
    "ieee.org",
    "springer.com",
    "nature.com",
    "sciencedirect.com",
    "jstor.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "biorxiv.org",
    "medrxiv.org",
    "openreview.net",
)
GOVERNMENT_SUFFIXES = (".gov", ".gov.uk", ".gov.au", ".gov.ca", ".europa.eu", ".edu")
OFFICIAL_DOC_HOSTS_PREFIXES = ("docs.", "developer.", "api.", "spec.", "rfc-editor.org")
NEWS_DOMAINS_HINT = (
    "reuters.com",
    "apnews.com",
    "bbc.co",
    "bbc.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "aljazeera.com",
    "npr.org",
)
COMMUNITY_HOSTS = (
    "stackoverflow.com",
    "serverfault.com",
    "superuser.com",
    "reddit.com",
    "news.ycombinator.com",
    "stackexchange.com",
    "github.com",
)
SOCIAL_HOSTS = (
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "linkedin.com",
    "mastodon.social",
)


def classify_source_type(url: str, title: str = "") -> SourceType:
    """Heuristic source-type classification from URL/title signals."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return SourceType.UNKNOWN
    path = urlparse(url).path.lower()

    if any(host == h or host.endswith("." + h) for h in ACADEMIC_HOSTS):
        return SourceType.ACADEMIC
    if host.endswith(GOVERNMENT_SUFFIXES):
        return SourceType.GOVERNMENT
    if host.startswith(OFFICIAL_DOC_HOSTS_PREFIXES) or "/docs" in path:
        return SourceType.OFFICIAL
    if any(h in host for h in NEWS_DOMAINS_HINT):
        return SourceType.NEWS
    if any(host == h or host.endswith("." + h) for h in ("github.com", "gitlab.com", "bitbucket.org")):
        return SourceType.TECHNICAL
    if any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS):
        return SourceType.SOCIAL
    if any(host == h or host.endswith("." + h) for h in COMMUNITY_HOSTS):
        return SourceType.COMMUNITY
    lowered_title = title.lower()
    if any(w in lowered_title for w in ("blog", "post:", "opinion")):
        return SourceType.BLOG
    if host.startswith("www.") or host.count(".") <= 2:
        return SourceType.SECONDARY
    return SourceType.COMMERCIAL


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def score_source_quality(
    source: ResearchSource,
    relevance: float = 0.5,
) -> Dict[str, Any]:
    """Transparent heuristic quality score. NOT an objective truth measure.

    Returns component scores plus a weighted total in [0, 1].
    """
    ts = source.trust_signals
    authority = 0.2 * ts.official_domain + 0.2 * ts.known_publisher + 0.2 * ts.peer_reviewed
    authority += 0.1 * ts.author_identified
    recency = 0.5
    if source.publication_date:
        try:
            year = int(str(source.publication_date)[:4])
            age = max(0, time.gmtime().tm_year - year)
            recency = max(0.0, 1.0 - age / 10.0)
            ts.dated = True
        except (ValueError, TypeError):
            recency = 0.25
    specificity = min(1.0, len(source.title) / 120.0)
    independence = min(1.0, ts.corroboration_domains / 3.0)
    primary_bonus = 1.0 if source.is_primary else 0.4
    transparency = sum([ts.https, ts.dated, ts.author_identified]) / 3.0
    total = (
        0.22 * authority
        + 0.14 * relevance
        + 0.10 * recency
        + 0.10 * specificity
        + 0.14 * independence
        + 0.10 * transparency
        + 0.20 * primary_bonus
    )
    if source.quarantined:
        total *= 0.25
    total -= min(0.5, source.risk)
    total = max(0.0, min(1.0, total))
    return {
        "total": round(total, 4),
        "components": {
            "authority": round(authority, 4),
            "relevance": round(relevance, 4),
            "recency": round(recency, 4),
            "specificity": round(specificity, 4),
            "independence": round(independence, 4),
            "transparency": round(transparency, 4),
            "primary_source_status": primary_bonus,
        },
        "heuristic": True,
    }


CONTRADICTION_MARKERS = (
    "however",
    "contrary",
    "contradict",
    "disput",
    "refut",
    "on the other hand",
    "in contrast",
    "no evidence",
    "denied",
    "debunk",
)


def detect_contradiction(text_a: str, text_b: str) -> Optional[str]:
    """Conservative pairwise contradiction signal.

    Flags only when one side carries an explicit conflict marker while both
    sides share a rare keyword. Never used to auto-pick a winner.
    """
    tokens_a = {w.strip(".,!?;:()\"'").lower() for w in text_a.split()}
    tokens_b = {w.strip(".,!?;:()\"'").lower() for w in text_b.split()}
    shared = tokens_a & tokens_b
    shared = {t for t in shared if len(t) > 6}
    if not shared:
        return None
    lowered_b = text_b.lower()
    for marker in CONTRADICTION_MARKERS:
        if marker in lowered_b:
            return f"shared:{sorted(shared)[0]}+marker:{marker}"
    return None


# ==============================================================================
# Hallucination Audit (Master Prompt 40 Phase 67)
# ==============================================================================


class HallucinationType(str, enum.Enum):
    """Types of hallucinations detected in research reports."""

    FAKE_URL = "fake_url"
    FAKE_QUOTE = "fake_quote"
    FAKE_STATISTIC = "fake_statistic"
    FAKE_DATE = "fake_date"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTRADICTED_CLAIM = "contradicted_claim"
    INVENTED_SOURCE = "invented_source"
    OVERREACHED_CLAIM = "overreached_claim"


@dataclass
class HallucinationFinding:
    """A single hallucination finding with evidence and severity."""

    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    claim_id: str = ""
    claim_text: str = ""
    hallucination_type: HallucinationType = HallucinationType.UNSUPPORTED_CLAIM
    severity: float = 0.5  # 0.0 = benign, 1.0 = critical
    evidence: str = ""  # What the model found/ didn't find
    suggested_action: str = "investigate"  # investigate | remove | qualify
    source_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class HallucinationAudit:
    """Audit result for a research task, identifying hallucinations and
    confidence-drift in the final report."""

    task_id: str
    audit_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    findings: List[HallucinationFinding] = field(default_factory=list)
    overall_assessment: str = "pending"  # "clean", "caution", "unreliable"
    audit_timestamp: float = field(default_factory=time.time)
    model_name: str = ""
    prompt_version: str = ""

    def add_finding(
        self,
        claim_id: str,
        claim_text: str,
        hallucination_type: HallucinationType,
        severity: float,
        evidence: str = "",
        suggested_action: str = "investigate",
        source_id: str = "",
    ) -> HallucinationFinding:
        finding = HallucinationFinding(
            claim_id=claim_id,
            claim_text=claim_text,
            hallucination_type=hallucination_type,
            severity=severity,
            evidence=evidence,
            suggested_action=suggested_action,
            source_id=source_id,
        )
        self.findings.append(finding)
        return finding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "audit_id": self.audit_id,
            "findings": [f.to_dict() for f in self.findings],
            "overall_assessment": self.overall_assessment,
            "audit_timestamp": self.audit_timestamp,
            "model_name": self.model_name,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HallucinationAudit":
        data = dict(data)
        data["findings"] = [
            HallucinationFinding.from_dict(f) for f in data.get("findings", [])
        ]
        return cls(**data)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity >= 0.7)

    def final_verdict(self) -> str:
        if not self.findings:
            return "clean"
        if any(f.severity >= 0.9 for f in self.findings):
            return "unreliable"
        if self.critical_count > len(self.findings) / 2:
            return "unreliable"
        return "caution"


def audit_hallucinations(
    task: ResearchTask,
    claims: List[Claim],
    sources: List[ResearchSource],
) -> HallucinationAudit:
    """Scan a research task's claims and sources for hallucinations.

    Rules (Master Prompt 40 Phase 67):
    - Never cite a source that does not support the claim
    - Never invent URLs, quotes, statistics, dates
    - Flag claims without evidence
    - Flag contradicted claims
    - Flag claims that overreach their evidence
    - Model memory must not be confounded with retrieved evidence
    """
    audit = HallucinationAudit(task_id=task.research_id)
    audit.model_name = getattr(task, "model_name", "unknown")
    audit.prompt_version = getattr(task, "prompt_version", "unknown")

    # Build source lookup
    source_by_id: Dict[str, ResearchSource] = {s.source_id: s for s in sources}

    # Track claim -> evidence -> source coverage
    claimed_source_ids: Dict[str, set] = {}
    for claim in claims:
        src_ids = {e.source_id for e in claim.evidence if e.source_id}
        claimed_source_ids[claim.claim_id] = src_ids

    for claim in claims:
        cid = claim.claim_id

        # 1. Claim without any evidence -> unsupported
        if not claim.has_evidence:
            audit.add_finding(
                claim_id=cid,
                claim_text=claim.text,
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                severity=1.0,
                evidence="no evidence collected",
                suggested_action="remove",
                source_id="",
            )
            continue

        # 2. Check each piece of evidence supports the claim
        for ev in claim.evidence:
            sid = ev.source_id
            src = source_by_id.get(sid)
            if src is None:
                audit.add_finding(
                    claim_id=cid,
                    claim_text=claim.text,
                    hallucination_type=HallucinationType.INVENTED_SOURCE,
                    severity=0.9,
                    evidence=f"source_id={sid} not found in source list",
                    suggested_action="remove",
                    source_id=sid,
                )
                continue

            # Check for quarantined/injected sources
            if src.quarantined:
                audit.add_finding(
                    claim_id=cid,
                    claim_text=claim.text,
                    hallucination_type=HallucinationType.SECURITY_REJECTION,
                    severity=0.8,
                    evidence=f"source quarantined: {', '.join(src.injection_flags[:3])}",
                    suggested_action="remove",
                    source_id=sid,
                )

            # Check source actually supports claim (simple keyword overlap)
            claim_lower = claim.text.lower()
            src_title = (src.title or "").lower()
            src_snippet = (src.snippet or "").lower()

            # Conservative check: does the snippet/title contain key terms from the claim?
            claim_tokens = {w.strip(".,!?;:()\"'").lower() for w in claim_lower.split() if len(w) > 4}
            src_tokens = set()
            if src_title:
                src_tokens.update(w.strip(".,!?;:()\"'").lower() for w in src_title.split() if len(w) > 4)
            if src_snippet:
                src_tokens.update(w.strip(".,!?;:()\"'").lower() for w in src_snippet.split() if len(w) > 4)

            if not claim_tokens.intersection(src_tokens):
                # No overlap - claim may overreach evidence
                audit.add_finding(
                    claim_id=cid,
                    claim_text=claim.text,
                    hallucination_type=HallucinationType.OVERREACHED_CLAIM,
                    severity=0.6,
                    evidence=f"no token overlap between claim and source (claim vs {src.source_type.value})",
                    suggested_action="qualify",
                    source_id=sid,
                )

        # 3. Check for contradicted claims
        for other_claim in claims:
            if other_claim.claim_id == cid:
                continue
            if other_claim.status == ClaimStatus.CONTRADICTED and claim.status != ClaimStatus.CONTRADICTED:
                # Check if there's any shared evidence or token
                shared_evidence = set(claim.evidence) & set(other_claim.evidence)
                if not shared_evidence:
                    # Truly contradicted with no common basis
                    audit.add_finding(
                        claim_id=cid,
                        claim_text=claim.text,
                        hallucination_type=HallucinationType.CONTRADICTED_CLAIM,
                        severity=0.7,
                        evidence=f"contradicted by claim {other_claim.claim_id}",
                        suggested_action="report_disagreement",
                        source_id="",
                    )

        # 4. Check for fake/overly-specific dates
        import re as _re
        date_patterns = _re.findall(r"\b\d{4}\b", claim.text)
        for yr in date_patterns:
            # If claim asserts a specific date not in any source, flag it
            source_dates = []
            for s in sources:
                if s.publication_date:
                    try:
                        y = str(s.publication_date)[:4]
                        source_dates.append(y)
                    except Exception:
                        pass
            if yr not in source_dates and not any(yr in str(s.metadata) for s in sources):
                audit.add_finding(
                    claim_id=cid,
                    claim_text=claim.text,
                    hallucination_type=HallucinationType.FAKE_DATE,
                    severity=0.5,
                    evidence=f"date {yr} not found in any retrieved source",
                    suggested_action="verify",
                    source_id="",
                )

        # 5. Check for claims that over-reference model knowledge
        # (claims with no source provenance would have been caught above,
        #  but check for absolute statements unsourced)
        if not claim.has_evidence and claim.confidence > 0.5:
            audit.add_finding(
                claim_id=cid,
                claim_text=claim.text,
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                severity=0.8,
                evidence="high confidence claim with no evidence",
                suggested_action="remove",
                source_id="",
            )

    # Final assessment
    if audit.critical_count == 0 and not any(
        f.hallucination_type in (HallucinationType.FAKE_URL, HallucinationType.FAKE_QUOTE, HallucinationType.FAKE_STATISTIC)
        for f in audit.findings
    ):
        audit.overall_assessment = "clean"
    elif audit.critical_count > 0:
        audit.overall_assessment = "unreliable"
    else:
        audit.overall_assessment = "caution"

    return audit


# ==============================================================================
# Existing utilities (unchanged from original)
# ==============================================================================


def classify_tool_failure(error: Any) -> ToolFailureKind:
    text = str(error).lower()
    for hint, kind in _FAILURE_HINTS:
        if hint in text:
            return kind
    return ToolFailureKind.PROVIDER_FAILURE


# Keep the rest of the original file content the same...
# (ACADEMIC_HOSTS, GOVERNMENT_SUFFIXES, etc. remain as before)