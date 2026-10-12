"""Discovery synthesis, replication, red-team, debate, reports,
quality gate, language guards, numeric verification. DISCOVERY is a
gated state machine — no state skipping; 'discovered' language only
passes the gate."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import (DiscoveryStatus, ExperimentResult, Hypothesis,
                     HypothesisStatus, ScientificDiscovery)

STATES = ["IDEA", "HYPOTHESIS", "TESTABLE", "EXPERIMENT_DESIGNED",
          "EXPERIMENT_EXECUTED", "EVIDENCE_COLLECTED", "ANALYZED",
          "SUPPORTED", "FALSIFIED", "INCONCLUSIVE", "REPLICATED",
          "VALIDATED"]


class QualityGate:
    CHECKS = ["evidence_exists", "source_verified", "reproducible",
              "prediction_tested", "alternatives_considered",
              "contradictions_checked", "statistics_valid",
              "independently_replicated", "novelty_searched",
              "human_review_if_required"]

    def evaluate(self, discovery: ScientificDiscovery,
                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = context or {}
        results = {}
        results["evidence_exists"] = bool(discovery.evidence_ids)
        results["source_verified"] = bool(ctx.get("sources_verified"))
        results["reproducible"] = discovery.reproducibility in (
            "REPRODUCED", "INDEPENDENTLY_REPRODUCED")
        results["prediction_tested"] = bool(
            discovery.supporting_experiments)
        results["alternatives_considered"] = bool(
            ctx.get("alternatives_considered"))
        results["contradictions_checked"] = bool(
            ctx.get("contradictions_checked"))
        results["statistics_valid"] = bool(ctx.get("statistics_valid"))
        results["independently_replicated"] = (
            discovery.reproducibility == "INDEPENDENTLY_REPRODUCED")
        results["novelty_searched"] = (
            discovery.novelty_assessment != "UNCERTAIN")
        results["human_review_if_required"] = (
            not ctx.get("human_review_required", False)
            or bool(ctx.get("human_reviewed")))
        passed = all(results.values())
        return {"checks": results, "passed": passed,
                "blocking": [k for k, v in results.items() if not v]}


class DiscoverySynthesizer:
    def __init__(self):
        self.gate = QualityGate()

    def propose(self, task_id: str, claim: str, claim_id: str,
                evidence_ids: List[str],
                experiments: List[str]) -> ScientificDiscovery:
        disc = ScientificDiscovery(
            task_id=task_id, title=claim[:120], claim=claim,
            claim_id=claim_id, evidence_ids=list(evidence_ids),
            supporting_experiments=list(experiments),
            confidence={"evidence": "unknown", "measurement": "unknown",
                        "model": "unknown", "statistical": "unknown",
                        "replication": "none",
                        "novelty": "unknown",
                        "external_validity": "unknown"})
        disc.state_history.append({"state": "IDEA"})
        return disc

    def advance(self, disc: ScientificDiscovery, to_state: str,
                note: str = "") -> ScientificDiscovery:
        order = ["IDEA", "HYPOTHESIS", "TESTABLE", "EXPERIMENT_DESIGNED",
                 "EXPERIMENT_EXECUTED", "EVIDENCE_COLLECTED", "ANALYZED"]
        current = disc.state_history[-1]["state"] if disc.state_history else "IDEA"
        terminal = {"SUPPORTED", "FALSIFIED", "INCONCLUSIVE", "REPLICATED",
                    "VALIDATED"}
        if to_state in terminal:
            if current != "ANALYZED" and not (
                    current == "EVIDENCE_COLLECTED" and to_state in (
                        "SUPPORTED", "FALSIFIED", "INCONCLUSIVE")):
                raise ValueError(
                    f"cannot skip to {to_state} from {current}")
        elif to_state in order:
            if order.index(to_state) > order.index(current) + 1:
                raise ValueError(
                    f"cannot skip states: {current} -> {to_state}")
        else:
            raise ValueError(f"unknown state {to_state}")
        disc.state_history.append({"state": to_state, "note": note})
        mapping = {"SUPPORTED": DiscoveryStatus.PRELIMINARY,
                   "REPLICATED": DiscoveryStatus.REPLICATED,
                   "VALIDATED": DiscoveryStatus.VALIDATED,
                   "FALSIFIED": DiscoveryStatus.REJECTED,
                   "INCONCLUSIVE": DiscoveryStatus.CONTESTED}
        if to_state in mapping:
            disc.status = mapping[to_state]
        return disc

    def validate(self, disc: ScientificDiscovery,
                 context: Dict[str, Any]) -> Dict[str, Any]:
        verdict = self.gate.evaluate(disc, context)
        if verdict["passed"]:
            self.advance(disc, "VALIDATED", "quality gate passed")
            disc.status = DiscoveryStatus.VALIDATED
        return verdict


class ReplicationEngine:
    def plan(self, experiment_id: str, levels: List[str]) -> List[str]:
        return [f"replicate {experiment_id} via {lvl}" for lvl in levels]


class RedTeamScientist:
    QUESTIONS = ["What could make this conclusion wrong?",
                 "What confounders remain?",
                 "What alternative explanation exists?",
                 "What measurement error exists?",
                 "What hidden assumption exists?",
                 "What prior work contradicts this?",
                 "What experiment would most efficiently falsify it?"]

    def interrogate(self, claim: str,
                    evidence: List[str]) -> Dict[str, Any]:
        return {"claim": claim,
                "objections": [
                    "single-context evidence; external validity uncertain",
                    "confounders may remain uncontrolled",
                    "measurement error unquantified",
                    "independent replication absent — strongest gap"],
                "kill_test": "pre-registered independent replication with "
                             "distinct implementation",
                "evidence_count": len(evidence)}


def debate(hypothesis: Hypothesis,
           reviews: List[Any]) -> Dict[str, Any]:
    pros = [r.strongest_argument for r in reviews
            if getattr(r, "strongest_argument", "")]
    cons = [r.strongest_counterargument for r in reviews
            if getattr(r, "strongest_counterargument", "")]
    return {"hypothesis": hypothesis.id, "for": pros, "against": cons,
            "verdict": "UNDECIDED — evidence decides, not debate winners"}


class ReportGenerator:
    SECTIONS = ["question", "background", "evidence", "gaps",
                "hypotheses", "design", "methods", "results",
                "statistics", "falsification", "limitations",
                "alternatives", "replication", "novelty", "conclusions",
                "open_questions", "next_experiments", "citations"]

    def research_report(self, task: Any, landscape: Any,
                        hypotheses: List[Hypothesis],
                        results: List[ExperimentResult]) -> Dict[str, Any]:
        return {
            "question": task.question,
            "background": [c.text for c in landscape.claims],
            "hypotheses": [
                {"statement": h.statement, "status": h.status,
                 "label": "UNVALIDATED HYPOTHESIS"
                 if h.status == HypothesisStatus.PROPOSED else h.status}
                for h in hypotheses],
            "results": [{"experiment": r.experiment_id,
                         "type": r.execution_type,
                         "outcome": r.falsification_outcome,
                         "interpretation": r.interpretation_label}
                        for r in results],
            "citations": [{"source": c.source_id, "text": c.text}
                          for c in landscape.claims],
            "limitations": ["evidence threshold not yet met"
                            if not results else "see per-result limits"],
        }

    def discovery_report(self, disc: ScientificDiscovery) -> Dict[str, Any]:
        return {"claim": disc.claim,
                "status": disc.status,
                "evidence": disc.evidence_ids,
                "experiments": disc.supporting_experiments,
                "contradictions": disc.contradicting_evidence,
                "confidence": disc.confidence,
                "limitations": disc.limitations,
                "replication": disc.reproducibility}


_CAUSAL_RE = re.compile(r"\b(causes?|caused by|drives?|leads? to)\b", re.I)


def check_causal_language(text: str, causal_evidence: bool) -> Dict[str, Any]:
    hits = _CAUSAL_RE.findall(text)
    if hits and not causal_evidence:
        return {"ok": False,
                "rewrite": "X is associated with Y / evidence consistent "
                           "with X affecting Y",
                "hits": hits}
    return {"ok": True, "hits": hits}


def check_discovery_language(text: str, gate_passed: bool) -> Dict[str, Any]:
    if re.search(r"\bwe discovered\b", text, re.I) and not gate_passed:
        return {"ok": False,
                "rewrite": "candidate finding / preliminary finding / "
                           "observed pattern / supported hypothesis"}
    return {"ok": True}


def verify_numeric_claims(report_numbers: Dict[str, float],
                           source_numbers: Dict[str, float]) -> Dict[str, Any]:
    mismatches = {k: (v, source_numbers.get(k))
                  for k, v in report_numbers.items()
                  if source_numbers.get(k) != v}
    return {"mismatches": mismatches,
            "status": "REPORT_BLOCKED" if mismatches else "OK"}
