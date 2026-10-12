"""Adversarial research, bias detection, and source diversity (P74-76).

The disprove phase actively searches for counter-evidence against the
strongest findings BEFORE the report is finalized. Bias metrics are
disclosed as measured heuristics — never claimed to be neutrality.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from agent.research.models import (
    Claim,
    ClaimStatus,
    ResearchSource,
)
from agent.research.urlnorm import registrable_domain


DISPROVE_TEMPLATES = (
    "\"{subject}\" criticism problems failures",
    "\"{subject}\" does not work limitations",
    "counterexample OR debunked \"{subject}\"",
    "\"{subject}\" disputed evidence",
)


@dataclass
class DisproveTask:
    claim_id: str
    subject: str
    queries: List[str] = field(default_factory=list)


def build_disprove_tasks(claims: List[Claim], top_k: int = 3) -> List[DisproveTask]:
    """Counter-evidence queries for the strongest claims only."""
    strong = [
        c for c in claims
        if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED,
                        ClaimStatus.SUPPORTED)
    ]
    tasks = []
    for claim in strong[:top_k]:
        words = [w for w in re.findall(r"[A-Za-z][a-zA-Z]{3,}", claim.text)]
        subject = " ".join(words[:6]) or claim.text[:60]
        tasks.append(
            DisproveTask(
                claim_id=claim.claim_id,
                subject=subject,
                queries=[t.format(subject=subject) for t in DISPROVE_TEMPLATES],
            )
        )
    return tasks


def absorb_disprove_result(claim: Claim, counter_claim_text: str,
                           source_id: str) -> bool:
    """If a disprove query surfaced contradicting content, mark BOTH sides
    CONTRADICTED (never auto-pick). Returns True when absorbed."""
    from agent.research.models import detect_contradiction

    signal = detect_contradiction(claim.text, counter_claim_text) or \
        detect_contradiction(counter_claim_text, claim.text)
    if not signal:
        return False
    counter = Claim(
        text=counter_claim_text.strip().rstrip("."),
        status=ClaimStatus.CONTRADICTED,
        source_ids=[source_id],
        confidence=0.4,
    )
    claim.status = ClaimStatus.CONTRADICTED
    claim.updated_at = time.time()
    return True


# ---------------------------------------------------------------------------
# P75 bias metrics — disclosed heuristics, not neutrality claims
# ---------------------------------------------------------------------------


@dataclass
class BiasReport:
    single_source_ratio: float
    top_publisher_share: float
    recency_skew_years: float
    type_spread: int
    domain_count: int
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"single-source claims {self.single_source_ratio:.0%}; "
            f"largest publisher {self.top_publisher_share:.0%} of sources; "
            f"{self.domain_count} distinct domains; "
            f"median age {self.recency_skew_years:.1f}y"
        )


def detect_bias(sources: List[ResearchSource],
                claims: List[Claim]) -> BiasReport:
    total_sources = len(sources)
    domains = {}
    publishers = {}
    years = []
    for src in sources:
        domains[registrable_domain(src.url)] = domains.get(
            registrable_domain(src.url), 0
        ) + 1
        pub = src.publisher or registrable_domain(src.url)
        publishers[pub] = publishers.get(pub, 0) + 1
        match = re.match(r"(\d{4})", src.publication_date or "")
        if match:
            years.append(int(match.group(1)))

    supported_counts: Dict[str, int] = {}
    for claim in claims:
        for sid in claim.source_ids:
            src = next((s for s in sources if s.source_id == sid), None)
            key = registrable_domain(src.url) if src else "?"
            supported_counts[key] = supported_counts.get(key, 0) + 1

    single = sum(1 for c in claims if len(set(c.source_ids)) <= 1)
    ratio_single = single / len(claims) if claims else 0.0
    top_share = (max(publishers.values()) / total_sources) if publishers else 0.0

    current_year = time.gmtime().tm_year
    recent = [y for y in years if y]
    median_age = 0.0
    if recent:
        ages = sorted(current_year - y for y in recent)
        mid = len(ages) // 2
        median_age = float(
            ages[mid] if len(ages) % 2 else (ages[mid - 1] + ages[mid]) / 2
        )

    notes = []
    if ratio_single > 0.6 and claims:
        notes.append("selection_bias: most claims rest on one source")
    if top_share > 0.5:
        notes.append("publisher_concentration: one publisher dominates")
    if len(domains) == 1 and total_sources > 1:
        notes.append("single_domain_family: sources share a registrable domain")
    if median_age > 5:
        notes.append("recency_bias_risk: evidence skews old")

    return BiasReport(
        single_source_ratio=ratio_single,
        top_publisher_share=top_share,
        recency_skew_years=median_age,
        type_spread=len({s.source_type.value for s in sources}),
        domain_count=len(domains),
        notes=notes,
    )


def diversify_candidates(candidates: List[Tuple[str, str]],
                         max_per_domain: int = 2) -> List[Tuple[str, str]]:
    """P76: cap per-domain representation among candidate (url, title)
    pairs so one site cannot crowd out the result set."""
    counts: Dict[str, int] = {}
    kept: List[Tuple[str, str]] = []
    for url, title in candidates:
        dom = registrable_domain(url)
        n = counts.get(dom, 0)
        if n < max_per_domain:
            counts[dom] = n + 1
            kept.append((url, title))
    return kept
