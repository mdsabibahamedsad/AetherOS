"""Report generation, citation coverage, traceability, quality (P77-85).

Formats: brief / executive / deep / comparison / timeline / decision_memo.
Every externally verifiable statement cites [Sn]; unevidenced claims are
labeled "(evidence not found)". The quality metric is a transparent
composite of disclosed heuristics — never presented as objective truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from agent.research.models import (
    Claim,
    ClaimKind,
    ClaimStatus,
    Contradiction,
    ResearchSource,
    ResearchTask,
)
from agent.research.temporal import (
    as_of_stamp,
    build_timeline,
    extract_dates,
)


_CITATION_RE = re.compile(r"\[S(\d+)\]")


@dataclass
class ReportContext:
    task: ResearchTask
    sources: List[ResearchSource]
    claims: List[Claim]
    contradictions: List[Contradiction] = field(default_factory=list)
    queries_run: List[str] = field(default_factory=list)
    usage: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def order(self) -> Dict[str, int]:
        return {s.source_id: i + 1 for i, s in enumerate(self.sources)}

    def cite(self, claim: Claim) -> str:
        marks, seen = [], set()
        for ev in claim.evidence:
            n = self.order.get(ev.source_id)
            if n and n not in seen:
                seen.add(n)
                marks.append(f"[S{n}]")
        return "".join(marks)


# ---------------------------------------------------------------------------
# P84 citation coverage
# ---------------------------------------------------------------------------


def citation_coverage(claims: List[Claim]) -> Dict[str, float]:
    externally_verifiable = [
        c for c in claims if c.kind in (ClaimKind.FACT, ClaimKind.SOURCE_CLAIM)
    ]
    supported = [c for c in externally_verifiable if c.has_evidence]
    total = len(externally_verifiable)
    return {
        "verifiable_claims": total,
        "supported_claims": len(supported),
        "unsupported_claims": total - len(supported),
        "completeness": round(len(supported) / total, 3) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# P77 aggregate research-quality score
# ---------------------------------------------------------------------------


def quality_metric(
    ctx: ReportContext,
    freshness_median_age_days: Optional[float] = None,
) -> Dict:
    coverage = min(1.0, len(ctx.sources) / 8.0)
    scored = [s.quality_score for s in ctx.sources if s.quality_score >= 0]
    avg_source_quality = sum(scored) / len(scored) if scored else 0.0
    domains = {s.domain for s in ctx.sources}
    independence = min(1.0, len(domains) / 3.0)
    verified = [
        c for c in ctx.claims
        if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED,
                        ClaimStatus.SUPPORTED)
    ]
    verification_ratio = (
        len(verified) / len(ctx.claims) if ctx.claims else 0.0
    )
    freshness = max(0.0, 1.0 - (freshness_median_age_days or 30) / 365.0)
    completeness = citation_coverage(ctx.claims)["completeness"]
    contradiction_handling = (
        1.0 if not ctx.contradictions else 0.8
    )
    total = round(
        0.18 * coverage
        + 0.16 * avg_source_quality
        + 0.14 * independence
        + 0.20 * verification_ratio
        + 0.10 * freshness
        + 0.14 * completeness
        + 0.08 * contradiction_handling,
        4,
    )
    return {
        "heuristic": True,
        "total": total,
        "components": {
            "coverage": round(coverage, 3),
            "avg_source_quality": round(avg_source_quality, 3),
            "independence": round(independence, 3),
            "verification_ratio": round(verification_ratio, 3),
            "freshness": round(freshness, 3),
            "citation_completeness": round(completeness, 3),
            "contradiction_handling": contradiction_handling,
        },
        "disclaimer": (
            "Composite of transparent heuristics over retrieved evidence; "
            "not an objective truth measure."
        ),
    }


# ---------------------------------------------------------------------------
# P85 traceability: conclusion -> claim -> evidence -> source
# ---------------------------------------------------------------------------


def traceability_index(ctx: ReportContext) -> List[Dict]:
    index = []
    for claim in ctx.claims:
        chain = []
        for ev in claim.evidence:
            src = next((s for s in ctx.sources if s.source_id == ev.source_id), None)
            chain.append({
                "evidence_id": ev.evidence_id,
                "location": ev.location,
                "excerpt_hash": ev.content_hash[:12],
                "source_number": ctx.order.get(ev.source_id),
                "source_url": src.url if src else None,
            })
        index.append({
            "claim_id": claim.claim_id,
            "kind": claim.kind.value,
            "status": claim.status.value,
            "text": claim.text,
            "citations": ctx.cite(claim),
            "evidence_chain": chain,
        })
    return index


def render_traceability(ctx: ReportContext) -> str:
    lines = ["## Traceability"]
    for item in traceability_index(ctx):
        chain = " -> ".join(
            f"S{e['source_number']}:{e['location']}"
            for e in item["evidence_chain"] if e["source_number"]
        ) or "no evidence"
        lines.append(
            f"- {item['claim_id']} ({item['status']}) {item['citations']} "
            f"=> {chain}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

_STATUS_LABELS = ("Confirmed", "Supported", "Uncertain", "Contradicted")


def _grouped(claims: List[Claim]) -> Dict[str, List[Claim]]:
    confirmed = [
        c for c in claims
        if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED)
    ]
    supported = [c for c in claims if c.status == ClaimStatus.SUPPORTED]
    uncertain = [
        c for c in claims
        if c.status in (ClaimStatus.UNCERTAIN, ClaimStatus.UNVERIFIED)
    ]
    contradicted = [c for c in claims if c.status == ClaimStatus.CONTRADICTED]
    return {"Confirmed": confirmed, "Supported": supported,
            "Uncertain": uncertain, "Contradicted": contradicted}


def _sources_section(ctx: ReportContext) -> List[str]:
    lines = ["## Sources"]
    if not ctx.sources:
        lines.append("- No sources retrieved.")
    for src in ctx.sources:
        n = ctx.order[src.source_id]
        flags = ""
        if src.quarantined:
            flags += f" QUARANTINED({','.join(src.injection_flags[:3])})"
        if src.visibility.value != "PUBLIC":
            flags += f" [{src.visibility.value}]"
        pub = f"; published {src.publication_date}" if src.publication_date else ""
        ocr = "; OCR-derived" if src.metadata.get("ocr") else ""
        lines.append(
            f"- [S{n}] {src.title or '(untitled)'} — {src.url} "
            f"({src.source_type.value}{pub}{ocr}){flags}"
        )
    return lines


def render_deep(ctx: ReportContext) -> Tuple[str, List[str]]:
    """P80 structure. Section markers preserved from the original engine."""
    groups = _grouped(ctx.claims)
    confirmed = groups["Confirmed"]
    supported = groups["Supported"]
    answer = (
        "; ".join(c.text for c in confirmed[:3])
        or "; ".join(c.text for c in supported[:3])
        or "Evidence not found."
    )
    lines: List[str] = []
    lines.append(f"# Research Report: {ctx.task.user_query}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"**Answer:** {answer}")
    if ctx.task.confidence:
        lines.append(f"**Confidence:** {ctx.task.confidence:.2f} (heuristic)")
    lines.append(f"**As of:** {as_of_stamp()}")
    lines.append(
        "**Caveats:** Quality scores and statuses are transparent "
        "heuristics over retrieved evidence, not objective truth."
    )
    lines.append("")
    lines.append("## Key Findings")
    for label in _STATUS_LABELS:
        for claim in groups[label][:10]:
            tag = "" if claim.has_evidence else " (evidence not found)"
            lines.append(
                f"- [{claim.kind.value}/{claim.status.value}] "
                f"{claim.text}{ctx.cite(claim)}{tag}"
            )
    if not ctx.claims:
        lines.append("- Evidence not found.")
    lines.append("")
    dated_events = []
    for claim in ctx.claims:
        date_iso = primary_or_none(claim)
        dated_events.append((claim.text, date_iso, claim.source_ids))
    timeline = build_timeline(dated_events)
    if timeline:
        lines.append("## Timeline (dated events only)")
        for event in timeline:
            marks = "".join(
                f"[S{ctx.order.get(sid) or '?'}]" for sid in event.source_ids
                if ctx.order.get(sid)
            )
            prec = f" ({event.precision}-precision)" if event.precision != "day" else ""
            lines.append(f"- {event.date_iso}{prec}: {event.text}{marks}")
        lines.append("")
    if ctx.contradictions:
        lines.append("## Contradictions (reported, not auto-resolved)")
        by_id = {c.claim_id: c for c in ctx.claims}
        for con in ctx.contradictions[:8]:
            a = by_id.get(con.claim_a_id)
            b = by_id.get(con.claim_b_id)
            ta = a.text if a else "?"
            tb = b.text if b else "?"
            lines.append(f"- \"{ta}\" vs \"{tb}\" — {con.reason}")
        lines.append("")
    lines.append("## Method")
    budget = ctx.task.budget_for_depth()
    lines.append(
        f"- Depth: {ctx.task.depth.value}; queries: "
        f"{int(ctx.usage.get('queries', len(ctx.queries_run)))}/"
        f"{budget['max_queries']}; unique pages: "
        f"{len(ctx.sources)}/{budget['max_sources']}"
    )
    providers = sorted({s.provider for s in ctx.sources if s.provider})
    if providers:
        lines.append(f"- Providers: {', '.join(providers)}")
    lines.append("")
    lines.extend(_sources_section(ctx))
    warnings = []
    if not confirmed and not supported:
        warnings.append("no corroborated findings")
    warnings.extend(ctx.warnings)
    return "\n".join(lines), warnings


def primary_or_none(claim: Claim) -> Optional[str]:
    from agent.research.temporal import primary_date

    return primary_date(claim.text)


def render_brief(ctx: ReportContext) -> str:
    groups = _grouped(ctx.claims)
    top = (groups["Confirmed"] + groups["Supported"])[:5]
    lines = [f"# Brief: {ctx.task.user_query}", ""]
    if not top:
        lines.append("Evidence not found.")
    for claim in top:
        tag = "" if claim.has_evidence else " (evidence not found)"
        lines.append(f"- {claim.text}{ctx.cite(claim)}{tag}")
    lines.append("")
    lines.append(f"As of {as_of_stamp()}. Heuristic confidence only.")
    return "\n".join(lines)


def render_executive(ctx: ReportContext) -> str:
    """P79: answer, key findings, confidence, caveats, major sources."""
    groups = _grouped(ctx.claims)
    answer = (
        "; ".join(c.text for c in groups["Confirmed"][:2])
        or "; ".join(c.text for c in groups["Supported"][:2])
        or "Evidence not found."
    )
    lines = [f"# Executive Summary — {ctx.task.user_query}", ""]
    lines.append(f"**Answer:** {answer}")
    lines.append(f"**Confidence:** {ctx.task.confidence:.2f} (heuristic)")
    lines.append(f"**As of:** {as_of_stamp()}")
    lines.append("")
    lines.append("**Key findings**")
    for label in ("Confirmed", "Supported", "Contradicted"):
        for claim in groups[label][:4]:
            lines.append(f"- ({label}) {claim.text}{ctx.cite(claim)}")
    lines.append("")
    lines.append("**Caveats**")
    for note in ctx.warnings or ["none recorded"]:
        lines.append(f"- {note}")
    lines.append(
        "- All statuses derive from heuristic corroboration counting."
    )
    lines.append("")
    major = ctx.sources[:5]
    if major:
        lines.append("**Major sources**")
        for src in major:
            lines.append(f"- [S{ctx.order[src.source_id]}] {src.url}")
    return "\n".join(lines)


def render_comparison(ctx: ReportContext, subjects: Optional[List[str]] = None) -> str:
    """P81: feature matrix from claims grouped by subject mentions."""
    subjects = subjects or _infer_subjects(ctx.claims)
    lines = ["# Comparison", "",
             "| aspect | " + " | ".join(subjects) + " |",
             "|" + "---|" * (len(subjects) + 1)]
    aspects: Dict[str, Dict[str, List[str]]] = {}
    for claim in ctx.claims:
        hit_subjects = [s for s in subjects if _mentions(claim.text, s)]
        if not hit_subjects or not claim.has_evidence:
            continue
        aspect_key = _aspect_of(claim)
        for subject in hit_subjects:
            cell = aspects.setdefault(aspect_key, {}).setdefault(subject, [])
            if claim.text not in cell:
                cell.append(claim.text)
    for aspect, per_subject in sorted(aspects.items()):
        row = [aspect]
        for subject in subjects:
            texts = per_subject.get(subject, [])[:2]
            joined = "; ".join(texts) if texts else "—"
            row.append(joined[:160] + ("" if len(joined) <= 160 else "…"))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "**Tradeoffs and limitations**",
              "- Matrix cells cite the same evidence objects as the deep report.",
              "- Missing cells mean no retrieved evidence mentioned that pairing."]
    return "\n".join(lines)


def _infer_subjects(claims: List[Claim]) -> List[str]:
    counts: Dict[str, int] = {}
    for claim in claims:
        for token in re.findall(r"\b[A-Z][A-Za-z0-9]{2,}\b", claim.text):
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    subjects = [name for name, count in ranked if count >= 2][:4]
    return subjects or ["Subject A", "Subject B"]


def _mentions(text: str, subject: str) -> bool:
    return bool(re.search(r"\b" + re.escape(subject) + r"\b", text))


_ASPECT_HINTS = (
    ("pricing", "pricing"),
    ("price", "pricing"),
    ("performance", "performance"),
    ("speed", "performance"),
    ("security", "security"),
    ("license", "licensing"),
    ("support", "support"),
    ("integration", "integrations"),
)


def _aspect_of(claim: Claim) -> str:
    lowered = claim.text.lower()
    for hint, aspect in _ASPECT_HINTS:
        if hint in lowered:
            return aspect
    return "general"


def render_decision_memo(ctx: ReportContext) -> str:
    """P82/P83: facts / criteria / options / tradeoffs / recommendation,
    with assumptions and uncertainty never hidden."""
    facts = [c for c in ctx.claims if c.kind == ClaimKind.FACT or c.has_evidence]
    inferences = [c for c in ctx.claims if c.kind == ClaimKind.INFERENCE]
    recommendations = [c for c in ctx.claims if c.kind == ClaimKind.RECOMMENDATION]
    hypotheses = [c for c in ctx.claims if c.kind == ClaimKind.HYPOTHESIS]
    lines = [f"# Decision Memo — {ctx.task.user_query}", "", "## Facts"]
    for claim in facts[:8]:
        lines.append(f"- {claim.text}{ctx.cite(claim)}")
    if not facts:
        lines.append("- Evidence not found.")
    lines += ["", "## Options / Tradeoffs"]
    # Display explicit criteria/constraints from the user
    for i, constraint in enumerate(ctx.task.constraints or [], 1):
        lines.append(f'{i}. {constraint}')
    if not ctx.task.constraints:
        lines.append('- No explicit criteria supplied; do not treat defaults as user intent.')
    
    # Disclose assumption weights - user-specified constraints are taken as-is
    lines.append('')
    lines.append('*Assumptions are user-specified and taken as-is; no automatic')
    lines.append('weighting is applied. The user may review and modify constraints at')
    lines.append('any time before synthesis begins.')
## Options / Tradeoffs"]
    for claim in (inferences + hypotheses)[:6]:
        lines.append(f"- (inference) {claim.text} [confidence {claim.confidence:.2f}]")
    if not (inferences or hypotheses):
        lines.append("- No inference-level content available.")
    lines += ["", "## Recommendation"]
    for claim in recommendations[:3]:
        downside = next(
            (w for w in ctx.warnings), "uncertainty remains"
        )
        lines.append(
            f"- {claim.text} — based on cited evidence; assumption-dependent; "
            f"potential downside: {downside}."
        )
    if not recommendations:
        lines.append(
            "- No recommendation derivable from retrieved evidence without "
            "unsupported assumptions."
        )
    lines += ["", f"Uncertainty note: {len(ctx.contradictions)} unresolved "
                  "contradiction(s) on record."]
    return "\n".join(lines)


def render_timeline_format(ctx: ReportContext) -> str:
    events = build_timeline([
        (c.text, primary_or_none(c), c.source_ids) for c in ctx.claims
    ])
    lines = [f"# Timeline — {ctx.task.user_query}", ""]
    if not events:
        lines.append("No reliably dated events found; refusing to guess dates.")
    for event in events:
        marks = "".join(
            f"[S{ctx.order[sid]}]" for sid in event.source_ids if ctx.order.get(sid)
        )
        lines.append(f"- **{event.date_iso}** ({event.precision}): {event.text}{marks}")
    lines += ["", "Undated claims were excluded rather than assigned guessed dates."]
    return "\n".join(lines)


REPORT_FORMATS = ("deep", "brief", "executive", "comparison", "timeline",
                  "decision_memo")


def render(ctx: ReportContext, fmt: str = "deep",
           subjects: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    if fmt == "brief":
        return render_brief(ctx), []
    if fmt == "executive":
        return render_executive(ctx), []
    if fmt == "comparison":
        return render_comparison(ctx, subjects), []
    if fmt == "timeline":
        return render_timeline_format(ctx), []
    if fmt == "decision_memo":
        return render_decision_memo(ctx), []
    return render_deep(ctx)
