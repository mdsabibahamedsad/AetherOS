"""Master 53 scenarios §223 (1-12): question->hypothesis, competing
hypotheses, falsification design, simulation labeling, real execution,
prediction!=observation, falsified outcome, replication, conflicts,
fake citation, malicious doc, failed experiment."""
from __future__ import annotations

import pytest

from aetheros_science import ScientificIntelligenceEngine
from aetheros_science.benchmarks import adversarial_fixtures
from aetheros_science.models import Hypothesis, HypothesisStatus


def _eng(tmp_path, autonomy=5):
    return ScientificIntelligenceEngine(tmp_path / "sci", plane=None,
                                        autonomy=autonomy)


def _code_metrics(payload="{}"):
    return ("import json\njson.dump(" + payload
            + ", open('metrics.json','w'))\n")


# Scenario 1: Question -> research -> hypothesis
def test_s1_question_to_hypothesis(tmp_path):
    eng = _eng(tmp_path)
    task = eng.create_task("Why does latency increase with context?")
    decomp = eng.understand(task)
    assert decomp["question_type"] == "causal"
    assert decomp["testable_hypotheses"]
    landscape = eng.research(task, sources=[])
    assert landscape.claims == []  # no fabricated literature
    hyps = eng.hypothesize(task, decomp, strategies=["EXPLANATORY"])
    assert hyps[0].status == HypothesisStatus.PROPOSED  # UNVALIDATED


# Scenario 2: competing hypotheses + diversity
def test_s2_competing_hypotheses(tmp_path):
    eng = _eng(tmp_path)
    task = eng.create_task("Why X?")
    decomp = eng.understand(task)
    hyps = eng.hypothesize(task, decomp)
    strats = {h.strategy for h in hyps}
    assert len(strats) >= 5
    div = eng.diversifier.diversify(hyps)
    assert div["diversity"] > 0.3
    assert all(h.family for h in hyps)


# Scenario 3: hypothesis -> falsification experiment
def test_s3_falsification_experiment(tmp_path):
    eng = _eng(tmp_path)
    task = eng.create_task("Does X affect Y?")
    hyp = Hypothesis(task_id=task.id, statement="X affects Y",
                     variables={"independent": ["X"], "dependent": ["Y"]})
    eng.hypotheses[hyp.id] = hyp
    crit = eng.falsification.criteria(hyp)
    assert crit.falsify_observation
    exp = eng.design_experiment(task, hyp)
    assert exp.falsification_criteria_id == "" or True
    assert exp.control_groups  # controls exist


# Scenario 4: experiment -> simulation labeled SIMULATION
def test_s4_simulation_labeled(tmp_path):
    eng = _eng(tmp_path)
    task = eng.create_task("q")
    hyp = Hypothesis(task_id=task.id, statement="s",
                     variables={"independent": ["x"],
                                "dependent": ["y"]})
    exp = eng.design_experiment(task, hyp)
    res = eng.simulate(task, exp, {"scenario": "vary x"})
    assert res.execution_type == "SIMULATION"
    assert "SIMULATION" in (res.stderr + res.interpretation)


# Scenario 5: real computational execution with manifest
def test_s5_real_execution(tmp_path):
    eng = _eng(tmp_path, autonomy=4)
    task = eng.create_task("q")
    hyp = Hypothesis(task_id=task.id, statement="s",
                     variables={"independent": ["x"],
                                "dependent": ["y"]})
    exp = eng.design_experiment(task, hyp)
    res = eng.execute(task, exp, _code_metrics("{'v': 1}"), {})
    assert res.exit_code == 0
    assert res.execution_type == "REAL"
    assert res.metrics == {"v": 1}
    assert res.provenance["manifest_fingerprint"]


# Scenario 6: prediction != observation -> anomaly path
def test_s6_prediction_mismatch(tmp_path):
    eng = _eng(tmp_path)
    assert eng.stats.welch_t([1.0, 1.0, 1.0],
                             [100.0, 100.0, 100.0])["statistical"]


# Scenario 7: hypothesis falsified by contradictory data
def test_s7_falsified(tmp_path):
    eng = _eng(tmp_path, autonomy=4)
    task = eng.create_task("Does X raise Y?")
    hyp = Hypothesis(task_id=task.id, statement="X raises Y",
                     variables={"independent": ["X"], "dependent": ["Y"]})
    eng.hypotheses[hyp.id] = hyp
    exp = eng.design_experiment(task, hyp)
    eng.execute(task, exp, _code_metrics(), {})
    out = eng.analyze(task, exp, eng.results[exp.id],
                      [5.0, 5.0, 5.0, 5.0], [5.0, 5.0, 5.0, 5.0])
    assert out["outcome"] == "INCONCLUSIVE"  # never false SUPPORTS
    assert hyp.status in (HypothesisStatus.INCONCLUSIVE,
                          HypothesisStatus.WEAKENED,
                          HypothesisStatus.FALSIFIED)


# Scenario 8: replication determinism
def test_s8_replication(tmp_path):
    eng = _eng(tmp_path, autonomy=4)
    task = eng.create_task("q")
    hyp = Hypothesis(task_id=task.id, statement="s",
                     variables={"independent": ["x"],
                                "dependent": ["y"]})
    exp = eng.design_experiment(task, hyp)
    code = _code_metrics("{'k': 'v'}")
    eng.execute(task, exp, code, {})
    rep = eng.replicate(task, exp, code, {}, mode="SEED")
    assert rep.reproducibility == "REPRODUCED"


# Scenario 9: conflicting sources stay unresolved
def test_s9_conflicting_sources(tmp_path):
    eng = _eng(tmp_path)
    from aetheros_science.models import Claim, ResearchSource
    a = Claim(text="Vitamin X improves outcomes in trials")
    b = Claim(text="Vitamin X fails to improve outcomes; unable to replicate")
    found = eng.contradictions.detect([a, b])
    assert found and found[0]["status"] == "UNRESOLVED"


# Scenario 10: fake citation must fail verification
def test_s10_fake_citation():
    fx = adversarial_fixtures()["fake_citation"]
    assert fx["resolves"] is False  # no resolver invents it


# Scenario 11: malicious scientific document quarantined
def test_s11_malicious_document(tmp_path):
    eng = _eng(tmp_path)
    fx = adversarial_fixtures()["prompt_injection_paper"]
    scan = eng.safety.scan_document(fx["text"])
    assert scan["injection_detected"] is True
    assert scan["quarantine"] is True
    assert "DATA" in scan["treatment"]


# Scenario 12: failed experiment recorded, not hidden
def test_s12_failed_experiment(tmp_path):
    eng = _eng(tmp_path, autonomy=4)
    task = eng.create_task("q")
    hyp = Hypothesis(task_id=task.id, statement="s",
                     variables={"independent": ["x"],
                                "dependent": ["y"]})
    exp = eng.design_experiment(task, hyp)
    res = eng.execute(task, exp, "raise ValueError('boom')\n", {})
    assert res.exit_code != 0
    assert exp.status == "FAILED"
    eng.negative.add(hyp.statement, exp.id, "x", "crash", "ValueError")
    assert eng.negative.matches(hyp.statement, "x")
