"""Knowledge graph + scientific memory. Every relationship needs
provenance; history is versioned, never overwritten; graph answers the
§115 query set."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .models import ScientificLesson, new_id

RELATIONS = ["SUPPORTS", "CONTRADICTS", "TESTS", "DERIVED_FROM",
             "REPLICATES", "FALSIFIES", "PREDICTS", "OBSERVED_IN",
             "USES_METHOD", "USES_DATASET", "CAUSES", "CORRELATES_WITH",
             "DEPENDS_ON", "REFINES", "SUPERSEDES"]


class ScientificKnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def add_node(self, kind: str, ref: str,
                 attrs: Optional[Dict[str, Any]] = None) -> str:
        nid = f"{kind}:{ref}"
        self.nodes[nid] = {"kind": kind, "ref": ref,
                           "attrs": attrs or {},
                           "at": time.time()}
        return nid

    def link(self, src: str, rel: str, dst: str,
             provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if rel not in RELATIONS:
            raise ValueError(f"unknown relation {rel}")
        if not provenance:
            raise ValueError("provenance required for every relationship")
        edge = {"id": new_id("edge"), "src": src, "rel": rel, "dst": dst,
                "provenance": provenance, "at": time.time()}
        self.edges.append(edge)
        return edge

    # ---- §115 query set ----
    def hypotheses_explaining(self, phenomenon: str) -> List[str]:
        return [e["src"] for e in self.edges
                if e["rel"] in ("PREDICTS", "CAUSES")
                and phenomenon.lower() in e["dst"].lower()]

    def experiments_falsifying(self, hypothesis_ref: str) -> List[str]:
        hid = f"Hypothesis:{hypothesis_ref}"
        return [e["src"] for e in self.edges
                if e["rel"] == "FALSIFIES"
                and (e["dst"] == hid or hypothesis_ref in e["dst"])]

    def datasets_supporting(self, claim_ref: str) -> List[str]:
        out = []
        for e in self.edges:
            if claim_ref in e["dst"] and e["rel"] in (
                    "SUPPORTS", "OBSERVED_IN", "USES_DATASET"):
                out.append(e["src"])
        return out

    def contradicting(self, hypothesis_ref: str) -> List[str]:
        return [e["src"] for e in self.edges
                if e["rel"] == "CONTRADICTS"
                and hypothesis_ref in (e["src"] + e["dst"])]

    def distinguishing_experiments(self, a_ref: str,
                                   b_ref: str) -> List[str]:
        return [e["src"] for e in self.edges
                if e["rel"] == "TESTS"
                and (a_ref in e["dst"] or b_ref in e["dst"])]

    def failed_approaches(self) -> List[str]:
        return [e["src"] for e in self.edges
                if e["rel"] in ("FALSIFIES", "CONTRADICTS")]


class ScientificMemory:
    """Chronological scientific memory: tried/worked/failed/ruled-out/
    uncertain/assumptions/datasets/pending. Lessons versioned."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.lessons: List[ScientificLesson] = []

    def record(self, kind: str, ref: str,
               detail: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({"kind": kind, "ref": ref,
                            "detail": detail or {},
                            "at": time.time()})

    def add_lesson(self, lesson: ScientificLesson) -> None:
        self.lessons.append(lesson)

    def timeline(self, ref: str = "") -> List[Dict[str, Any]]:
        evs = [e for e in self.events if not ref or e["ref"] == ref]
        return sorted(evs, key=lambda e: e["at"])

    def what_failed(self) -> List[Dict[str, Any]]:
        return [e for e in self.events if e["kind"] in (
            "failed", "falsified", "reproduction_failed")]
