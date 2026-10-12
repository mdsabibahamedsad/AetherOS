"""Phase 2: question decomposition, landscape, gaps, independence,
contradictions. No fabricated literature: the builder works over
explicitly provided sources; network search is UNAVAILABLE unless a
search tool is injected."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from .models import Claim, KnowledgeGap, ResearchLandscape, ResearchSource

QUESTION_TYPES = ["causal", "mechanistic", "predictive", "comparative",
                  "optimization", "diagnostic", "explanatory",
                  "exploratory", "design", "discovery", "replication",
                  "anomaly_investigation"]

_TYPE_HINTS = [
    ("why", "causal"), ("cause", "causal"), ("mechanism", "mechanistic"),
    ("how does", "mechanistic"), ("predict", "predictive"),
    ("better", "comparative"), ("compare", "comparative"),
    ("optim", "optimization"), ("diagnos", "diagnostic"),
    ("explain", "explanatory"), ("explore", "exploratory"),
    ("design", "design"), ("discover", "discovery"),
    ("replicat", "replication"), ("anomal", "anomaly_investigation"),
]


def classify_question(question: str) -> str:
    q = question.lower()
    for hint, kind in _TYPE_HINTS:
        if hint in q:
            return kind
    return "exploratory"


def decompose_question(question: str, known_facts: Optional[List[str]] = None,
                       background: str = "") -> Dict[str, Any]:
    """Rule-based decomposition: phenomenon, knowns, unknowns, candidate
    causal factors, testable hypothesis slots, falsification slots."""
    known = list(known_facts or [])
    if background:
        known.append(background)
    phenomenon = question.strip().rstrip("?")
    stop = {"why", "does", "do", "is", "are", "the", "a", "an", "what",
            "how", "which", "this", "that", "it", "in", "on", "of", "to"}
    tokens = [t.strip("?,. ").lower() for t in re.split(r"\s+", phenomenon)]
    keywords = [t for t in tokens if t and t not in stop][:12]
    return {
        "phenomenon": phenomenon,
        "question_type": classify_question(question),
        "known_observations": known,
        "known_mechanisms": [],
        "unknown_variables": [f"unmeasured factor related to '{k}'"
                              for k in keywords[:5]],
        "competing_explanations": [],
        "candidate_causal_factors": keywords[:6],
        "testable_hypotheses": [
            f"If '{k}' is manipulated, the phenomenon changes measurably"
            for k in keywords[:3]],
        "required_evidence": ["controlled observation of the phenomenon",
                              "measurement of candidate factors"],
        "possible_experiments": ["COMPUTATIONAL", "DATA_ANALYSIS"],
        "possible_simulations": ["DIGITAL_TWIN"],
        "expected_observations": [],
        "falsification_conditions": [
            "manipulating the candidate factor produces no measurable change"],
    }


class ResearchLandscapeBuilder:
    """Builds landscapes ONLY from provided sources. Network search must
    be injected; otherwise landscape is honestly source-less."""

    def __init__(self, search_fn: Optional[Callable] = None):
        self.search_fn = search_fn

    def build(self, task_id: str, question: str,
              sources: Optional[List[ResearchSource]] = None) -> ResearchLandscape:
        provided = list(sources or [])
        found: List[ResearchSource] = []
        if self.search_fn is not None:
            try:
                found = self.search_fn(question) or []
            except Exception:
                found = []
        landscape = ResearchLandscape(task_id=task_id,
                                      sources=provided + found)
        for src in landscape.sources:
            if src.content_excerpt:
                first = src.content_excerpt.split(".")[0][:300]
                landscape.claims.append(Claim(
                    text=first, source_id=src.id,
                    provenance={"source_kind": src.kind,
                                "retrieved_at": src.retrieved_at}))
        return landscape

    @property
    def network_status(self) -> str:
        return "AVAILABLE" if self.search_fn else "UNAVAILABLE"


class KnowledgeGapDetector:
    def rank(self, gaps: List[KnowledgeGap]) -> List[KnowledgeGap]:
        for g in gaps:
            feasibility = max(0.0, 1.0 - g.risk)
            g.priority = (g.expected_information_gain * g.importance
                          * feasibility / max(g.cost, 1e-9))
        return sorted(gaps, key=lambda g: -g.priority)

    def from_landscape(self, landscape: ResearchLandscape) -> List[KnowledgeGap]:
        gaps = [KnowledgeGap(
            description=f"open question: {q}", importance=0.6,
            uncertainty=0.7, expected_information_gain=0.6, cost=1.0)
            for q in landscape.open_questions]
        for c in landscape.contradictions:
            gaps.append(KnowledgeGap(
                description=f"contradiction: {c.get('topic', c)}",
                importance=0.8, uncertainty=0.8,
                expected_information_gain=0.8, cost=1.5))
        return self.rank(gaps)


class SourceIndependenceAnalyzer:
    """Groups sources sharing underlying evidence; counts independent
    lineages, never raw citation counts."""

    @staticmethod
    def _lineage(src: ResearchSource) -> str:
        prov = src.provenance or {}
        for key in ("paper_id", "dataset_id", "experiment_id", "doi"):
            if prov.get(key):
                return f"{key}:{prov[key]}"
        if src.doi:
            return f"doi:{src.doi}"
        authors = ",".join(sorted(src.authors)).lower() if src.authors else ""
        return f"{src.kind}:{authors}:{src.title.lower()[:60]}"

    def analyze(self, sources: List[ResearchSource]) -> Dict[str, Any]:
        groups: Dict[str, List[str]] = {}
        for src in sources:
            groups.setdefault(self._lineage(src), []).append(src.id)
        return {"independent_lineages": len(groups),
                "total_sources": len(sources),
                "groups": groups,
                "note": "strength comes from independent lineages, "
                        "not raw counts"}


class ContradictionEngine:
    """Flags textual contradictions between claims; never silently picks
    a side — records both with methodological notes."""

    _NEG = re.compile(r"\b(no|not|never|fails?|contradicts?|refutes?|"
                      r"unable to replicate)\b", re.I)

    @staticmethod
    def _stem(words: set) -> set:
        """Light suffix-strip so 'improves'/'improve' match. Heuristic,
        documented; not a linguistic claim."""
        out = set()
        for w in words:
            out.add(w)
            for suffix in ("ing", "es", "s", "ed"):
                if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                    out.add(w[: -len(suffix)])
        return out

    def detect(self, claims: List[Claim]) -> List[Dict[str, Any]]:
        out = []
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                a, b = claims[i], claims[j]
                words_a = self._stem(set(
                    re.findall(r"[a-z]{4,}", a.text.lower())))
                words_b = self._stem(set(
                    re.findall(r"[a-z]{4,}", b.text.lower())))
                shared = words_a & words_b
                neg = bool(self._NEG.search(a.text) !=
                           self._NEG.search(b.text))
                if len(shared) >= 2 and neg:
                    out.append({"claim_a": a.id, "claim_b": b.id,
                                "shared_terms": sorted(shared)[:8],
                                "status": "UNRESOLVED",
                                "note": "methodological comparison required; "
                                        "neither side selected"})
        return out
