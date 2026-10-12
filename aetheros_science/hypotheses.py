"""Phases 3-4: hypothesis generation/diversification, novelty,
critique teams, falsification, exploration control. Generated
hypotheses are UNVALIDATED by construction; novelty verdicts describe
corpus search results, never 'discovery'."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import (FalsificationCriteria, Hypothesis, HypothesisReview,
                     HypothesisStatus)

STRATEGIES = ["EXPLANATORY", "MECHANISTIC", "CAUSAL", "ALTERNATIVE",
              "CONTRARIAN", "BOUNDARY_CONDITION", "ANALOGICAL",
              "CROSS_DOMAIN", "FIRST_PRINCIPLES", "DATA_DRIVEN",
              "SIMULATION_DERIVED", "LITERATURE_DERIVED", "ANOMALY_DRIVEN"]

_STRATEGY_TEMPLATE = {
    "EXPLANATORY": "The phenomenon occurs because {factor} drives {target}.",
    "MECHANISTIC": "A stepwise mechanism via {factor} produces {target}.",
    "CAUSAL": "Intervening on {factor} changes {target} (do-operator testable).",
    "ALTERNATIVE": "Alternatively, {target} arises without {factor}, via {alt}.",
    "CONTRARIAN": "Contrary to background assumptions, {factor} suppresses {target}.",
    "BOUNDARY_CONDITION": "{factor} affects {target} only outside regime R.",
    "ANALOGICAL": "By ANALOGY (not evidence) to {alt}, {factor} shapes {target}.",
    "CROSS_DOMAIN": "A mechanism borrowed from {alt} may govern {factor}->{target}.",
    "FIRST_PRINCIPLES": "From invariants/constraints: {factor} bounds {target}.",
    "DATA_DRIVEN": "Observed covariation suggests {factor} tracks {target}.",
    "SIMULATION_DERIVED": "SIMULATION suggests {factor} influences {target}; untested in reality.",
    "LITERATURE_DERIVED": "Prior work hints {factor} relates to {target}; needs replication.",
    "ANOMALY_DRIVEN": "An anomalous case implicates {factor} in {target}.",
}


class HypothesisEngine:
    def generate(self, task_id: str, factors: List[str], target: str,
                 strategies: Optional[List[str]] = None) -> List[Hypothesis]:
        out = []
        for i, strat in enumerate(strategies or STRATEGIES):
            factor = factors[i % max(len(factors), 1)] if factors else "unknown factor"
            alt = factors[(i + 1) % max(len(factors), 1)] if len(factors) > 1 else "another pathway"
            stmt = _STRATEGY_TEMPLATE[strat].format(
                factor=factor, target=target or "the phenomenon", alt=alt)
            if strat in ("ANALOGICAL", "CROSS_DOMAIN"):
                stmt = "ANALOGY: " + stmt
            if strat == "SIMULATION_DERIVED":
                stmt = "SIMULATION: " + stmt
            out.append(Hypothesis(
                task_id=task_id, statement=stmt,
                mechanism=f"{strat} mechanism sketch for {factor}",
                assumptions=[f"{strat} framing assumptions"],
                predictions=[f"measurable change in {target} when {factor} varies"],
                variables={"independent": [factor],
                           "dependent": [target or "phenomenon"],
                           "confounders": [], "controls": []},
                causal_claims=[f"{factor} -> {target}"] if strat in (
                    "CAUSAL", "MECHANISTIC", "FIRST_PRINCIPLES") else [],
                strategy=strat, status=HypothesisStatus.PROPOSED,
                uncertainty="high", evidence_strength="E0"))
        return out


class HypothesisDiversifier:
    def diversify(self, hypotheses: List[Hypothesis]) -> Dict[str, Any]:
        by_strategy: Dict[str, List[str]] = {}
        for h in hypotheses:
            by_strategy.setdefault(h.strategy, []).append(h.id)
        fams: Dict[str, str] = {}
        for h in hypotheses:
            key = (h.variables.get("independent", ["?"])[0]
                   if h.variables.get("independent") else "?")
            fams[h.id] = f"family:{key}"
            h.family = fams[h.id]
        coverage = len(by_strategy) / max(len(STRATEGIES), 1)
        return {"families": fams, "strategy_coverage": by_strategy,
                "diversity": round(coverage, 3),
                "single_idea_warning": coverage < 0.3}


class NoveltyAnalyzer:
    """Compares against a searched corpus. Verdicts describe the search,
    never declare discovery."""

    @staticmethod
    def _tokens(text: str) -> set:
        return set(re.findall(r"[a-z]{4,}", text.lower()))

    def analyze(self, hypothesis: Hypothesis,
                corpus: List[str]) -> Dict[str, str]:
        if not corpus:
            return {"verdict": "UNCERTAIN",
                    "statement": "No corpus searched; novelty unknown."}
        h = self._tokens(hypothesis.statement + " " + hypothesis.mechanism)
        best, best_j = 0.0, ""
        for doc in corpus:
            d = self._tokens(doc)
            union = h | d
            j = len(h & d) / max(len(union), 1)
            if j > best:
                best, best_j = j, doc[:120]
        if best > 0.6:
            verdict = "DUPLICATE"
        elif best > 0.4:
            verdict = "KNOWN"
        elif best > 0.25:
            verdict = "KNOWN_VARIANT"
        elif best > 0.12:
            verdict = "POTENTIALLY_NOVEL"
        else:
            verdict = "NOVEL"
        hypothesis.novelty = verdict
        hypothesis.novelty_confidence = (
            "low" if verdict in ("NOVEL", "UNCERTAIN") else "medium")
        return {"verdict": verdict,
                "statement": "No matching prior work was found in the "
                             "searched corpus." if verdict == "NOVEL" else
                             f"Closest corpus match (similarity {best:.2f}): {best_j}",
                "confidence": hypothesis.novelty_confidence}


class HypothesisCritic:
    """Structured skeptic review. No majority vote; evidence decides."""

    def review(self, hypothesis: Hypothesis,
               landscape_claims: Optional[List[str]] = None,
               reviewer: str = "SkepticAgent") -> HypothesisReview:
        indep = hypothesis.variables.get("independent", ["?"])[0]
        dep = (hypothesis.variables.get("dependent", ["?"])[0]
               if hypothesis.variables.get("dependent") else "?")
        return HypothesisReview(
            hypothesis_id=hypothesis.id,
            strongest_argument=f"Predicts measurable change in {dep}.",
            strongest_counterargument=(
                f"Confounders uncontrolled; {indep} may merely correlate "
                f"with {dep}."),
            missing_evidence=[f"controlled measurement of {dep} under "
                              f"intervention on {indep}"],
            confounders=["unmeasured common causes", "selection effects"],
            alternative_explanations=["reverse causation", "common cause",
                                      "measurement artifact"],
            falsification_test=(
                f"Intervene on {indep}; if {dep} shows no meaningful "
                f"change under controlled conditions, weaken."),
            reproducibility_concerns=["single-context observation"],
            safety_concerns=[],
            confidence="unknown", reviewer=reviewer)


class FalsificationEngine:
    def criteria(self, hypothesis: Hypothesis) -> FalsificationCriteria:
        indep = (hypothesis.variables.get("independent", ["factor"])[0])
        dep = (hypothesis.variables.get("dependent", ["outcome"])[0]
               if hypothesis.variables.get("dependent") else "outcome")
        return FalsificationCriteria(
            hypothesis_id=hypothesis.id,
            weaken_observation=(f"Intervention on {indep} yields small or "
                                f"inconsistent change in {dep}."),
            falsify_observation=(f"Controlled intervention on {indep} "
                                 f"produces no meaningful change in {dep}; "
                                 f"the hypothesis is weakened/falsified."),
            support_observation=(f"Replicated, controlled change in {dep} "
                                 f"following intervention on {indep}."),
            inconclusive_observation="Noisy measurement or broken controls; "
                                     "repeat with tighter protocol.")

    @staticmethod
    def judge(hypothesis: Hypothesis, outcome: str,
              effect_size: float = 0.0) -> str:
        if outcome == "FALSIFIES" or (
                outcome == "WEAKENS" and abs(effect_size) < 0.1):
            return (HypothesisStatus.FALSIFIED if outcome == "FALSIFIES"
                    else HypothesisStatus.WEAKENED)
        if outcome == "SUPPORTS":
            return HypothesisStatus.SUPPORTED
        return HypothesisStatus.INCONCLUSIVE


class ExplorationController:
    MODES = ["localSearch", "globalSearch", "crossDomainSearch",
             "contrarianSearch", "randomizedSearch",
             "firstPrinciplesSearch", "analogySearch"]

    def select(self, hypotheses: List[Hypothesis],
               budget: Dict[str, float]) -> Dict[str, object]:
        strats = {h.strategy for h in hypotheses}
        missing = [m for m in
                   ["CONTRARIAN", "CROSS_DOMAIN", "FIRST_PRINCIPLES",
                    "ANOMALY_DRIVEN"] if m not in strats]
        return {"recommended_modes": (
            ["contrarianSearch", "crossDomainSearch",
             "firstPrinciplesSearch"] if missing else ["globalSearch"]),
                "missing_strategies": missing,
                "explore_uncertain": True,
                "note": "explore high-information alternatives, not only "
                        "the most likely hypothesis"}
