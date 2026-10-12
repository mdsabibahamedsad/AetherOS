"""Evidence chain, Bayes, reproducibility, negative memory.
Strength E0-E6 is an internal taxonomy, not a universal standard.
Consensus never outweighs one good contradictory experiment."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from .models import DatasetVersion, Evidence, ReplicationRecord, new_id

STRENGTH_ORDER = ["E0", "E1", "E2", "E3", "E4", "E5", "E6"]


def stronger(a: str, b: str) -> bool:
    return STRENGTH_ORDER.index(a) > STRENGTH_ORDER.index(b)


class EvidenceEngine:
    WEIGHTS = {"method": 0.25, "directness": 0.2, "independence": 0.2,
               "replication": 0.15, "uncertainty": 0.1, "recency": 0.1}

    def __init__(self):
        self.store: Dict[str, Evidence] = {}
        self.claim_links: Dict[str, List[str]] = {}

    def add(self, ev: Evidence) -> Evidence:
        self.store[ev.id] = ev
        self.claim_links.setdefault(ev.claim_id, []).append(ev.id)
        return ev

    def for_claim(self, claim_id: str) -> List[Evidence]:
        return [self.store[i] for i in self.claim_links.get(claim_id, [])
                if i in self.store]

    def strength_for_claim(self, claim_id: str) -> str:
        best = "E0"
        for ev in self.for_claim(claim_id):
            if stronger(ev.strength, best):
                best = ev.strength
        return best

    def weight(self, ev: Evidence) -> float:
        ind = 1.0 if ev.independence == "independent" else (
            0.3 if ev.independence.startswith("derived") else 0.5)
        rep = {"unknown": 0.4, "none": 0.3, "rerun": 0.6,
               "independent": 1.0}.get(ev.reproducibility, 0.4)
        method = {"DIRECT_OBSERVATION": 1.0, "EXPERIMENTAL_RESULT": 0.95,
                  "COMPUTATIONAL_RESULT": 0.8, "DATASET": 0.8,
                  "STATISTICAL_RESULT": 0.75, "SIMULATION_RESULT": 0.4,
                  "LITERATURE": 0.6, "META_ANALYSIS": 0.7,
                  "THEORETICAL_DERIVATION": 0.6,
                  "EXPERT_ASSESSMENT": 0.4, "MODEL_PREDICTION": 0.25,
                  "USER_PROVIDED_DATA": 0.5}.get(ev.type, 0.4)
        return round(0.25 * method + 0.2 * method + 0.2 * ind
                     + 0.15 * rep + 0.1 * 0.5 + 0.1 * 0.7, 3)

    def check_contradiction(self, claim_id: str) -> bool:
        # contradiction is recorded on claims by ContradictionEngine;
        # engine-level helper: any evidence marked contradicting?
        return any("contradict" in (e.measurement + e.methodology).lower()
                   for e in self.for_claim(claim_id))


class BayesianUpdater:
    """Beta-Binomial conjugate update for binary outcomes. Honest scope:
    only valid where the problem fits this formulation; otherwise the
    engine records QUALITATIVE/MECHANISTIC analysis instead."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0):
        self.alpha = alpha
        self.beta = beta
        self.updates: List[Dict[str, Any]] = []

    def prior_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def update(self, successes: int, trials: int,
               evidence_weight: float = 1.0,
               note: str = "") -> Dict[str, Any]:
        w = max(0.0, min(1.0, evidence_weight))
        self.alpha += successes * w
        self.beta += (trials - successes) * w
        rec = {"prior": self.prior_mean(), "successes": successes,
               "trials": trials, "weight": w,
               "posterior": self.prior_mean(), "note": note}
        self.updates.append(rec)
        return rec


class ReproducibilityEngine:
    MODES = ["SAME_SETUP", "SEED", "IMPLEMENTATION", "MODEL",
             "DATASET", "AGENT", "ENVIRONMENT"]
    INDEPENDENT_MODES = {"IMPLEMENTATION", "MODEL", "DATASET", "AGENT",
                         "ENVIRONMENT"}

    def __init__(self):
        self.records: List[ReplicationRecord] = []

    def record(self, experiment_id: str, original_ref: str, mode: str,
               outcome: str, details: Optional[Dict[str, Any]] = None
               ) -> ReplicationRecord:
        rec = ReplicationRecord(
            experiment_id=experiment_id, original_result_ref=original_ref,
            mode=mode, outcome=outcome, details=details or {},
            independent=(mode in self.INDEPENDENT_MODES
                         and outcome == "MATCHED"))
        self.records.append(rec)
        return rec

    def score(self, experiment_id: str) -> Dict[str, Any]:
        recs = [r for r in self.records
                if r.experiment_id == experiment_id]
        matched = sum(1 for r in recs if r.outcome == "MATCHED")
        indep = sum(1 for r in recs if r.independent)
        components = {
            "environment_documented": any(
                r.details.get("manifest") for r in recs),
            "successful_reruns": matched,
            "independent_reruns": indep,
            "total_attempts": len(recs)}
        return {"components": components,
                "note": "components shown; no single-number reduction"}


class NegativeResultMemory:
    """Failed approaches persist so the system never silently retries
    the same failure. Queried before proposing experiments."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def add(self, hypothesis: str, experiment: str, conditions: str,
            failure: str, reason: str, confidence: str = "medium",
            reproducibility: str = "single-run") -> Dict[str, Any]:
        entry = {"hypothesis": hypothesis, "experiment": experiment,
                 "conditions": conditions, "failure": failure,
                 "reason": reason, "confidence": confidence,
                 "reproducibility": reproducibility}
        self.entries.append(entry)
        return entry

    def matches(self, hypothesis: str, conditions: str) -> List[Dict[str, Any]]:
        h, c = hypothesis.lower(), conditions.lower()
        return [e for e in self.entries
                if h in e["hypothesis"].lower()
                or c in e["conditions"].lower()]
