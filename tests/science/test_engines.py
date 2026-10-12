"""Master 53: statistics, Bayes, knowledge graph, discovery gate,
safety classification, novelty, language guards, numeric verification,
concurrency, performance smoke."""
from __future__ import annotations

import threading

import pytest

from aetheros_science import ScientificIntelligenceEngine
from aetheros_science.benchmarks import golden_fixtures
from aetheros_science.discovery import (QualityGate, check_causal_language,
                                        check_discovery_language,
                                        verify_numeric_claims)
from aetheros_science.evidence import BayesianUpdater, EvidenceEngine
from aetheros_science.knowledge import ScientificKnowledgeGraph
from aetheros_science.models import Evidence


def _eng(tmp_path, autonomy=5):
    return ScientificIntelligenceEngine(tmp_path / "sci", plane=None,
                                        autonomy=autonomy)


def test_stats_golden_and_context(tmp_path):
    eng = _eng(tmp_path)
    fx = golden_fixtures()
    comp = eng.stats.welch_t(fx["mean_shift"]["a"], fx["mean_shift"]["b"])
    assert comp["statistical"] is True
    assert "context" in comp  # p never reported bare
    assert comp["effect_magnitude"] in ("large", "medium")
    null = eng.stats.welch_t(fx["null_case"]["a"], fx["null_case"]["b"])
    assert null["statistical"] is False
    r = eng.stats.pearson(fx["perfect_corr"]["xs"],
                          fx["perfect_corr"]["ys"])
    assert abs(r["r"] - 1.0) < 1e-9
    boot = eng.stats.bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0], seed=1)
    assert boot["lo"] <= 3.0 <= boot["hi"]
    perm = eng.stats.permutation_p([1.0, 1.0], [10.0, 10.0], seed=1)
    assert 0.0 <= perm["p"] <= 1.0
    flags = eng.stats.correct_multiple([0.01, 0.04, 0.5], method="holm")
    assert flags[0] is True and flags[2] is False
    ss = eng.stats.sample_size(0.8)
    assert ss["n_per_group"] > 0 and "warning" in ss


def test_bayes_conjugate_update():
    b = BayesianUpdater()
    assert abs(b.prior_mean() - 0.5) < 1e-9
    rec = b.update(8, 10)
    assert rec["posterior"] > 0.5
    assert len(b.updates) == 1


def test_evidence_strength_and_weight(tmp_path):
    eng = _eng(tmp_path)
    ev = Evidence(claim_id="c1", type="EXPERIMENTAL_RESULT",
                  source="exp_1", independence="independent",
                  reproducibility="independent", strength="E4")
    eng.evidence.add(ev)
    assert eng.evidence.strength_for_claim("c1") == "E4"
    assert eng.evidence.weight(ev) > eng.evidence.weight(
        Evidence(claim_id="c2", type="MODEL_PREDICTION",
                 source="llm", strength="E1"))


def test_knowledge_graph_queries(tmp_path):
    eng = _eng(tmp_path)
    h = eng.graph.add_node("Hypothesis", "h1")
    e = eng.graph.add_node("Experiment", "e1")
    eng.graph.link(e, "FALSIFIES", h,
                   provenance={"by": "test", "at": "now"})
    assert eng.graph.experiments_falsifying("h1") == [e]
    with pytest.raises(ValueError):
        eng.graph.link(e, "TELEPORTS", h)  # unknown relation


def test_graph_requires_provenance(tmp_path):
    eng = _eng(tmp_path)
    with pytest.raises(ValueError):
        eng.graph.link("a", "SUPPORTS", "b", provenance=None)


def test_discovery_state_machine_no_skips(tmp_path):
    eng = _eng(tmp_path)
    disc = eng.synth.propose("t", "claim", "c1", ["e1"], ["x1"])
    with pytest.raises(ValueError):
        eng.synth.advance(disc, "VALIDATED")  # skip forbidden
    for s in ["HYPOTHESIS", "TESTABLE", "EXPERIMENT_DESIGNED",
              "EXPERIMENT_EXECUTED", "EVIDENCE_COLLECTED", "ANALYZED",
              "SUPPORTED"]:
        eng.synth.advance(disc, s)
    assert disc.status == "PRELIMINARY"  # not VALIDATED


def test_quality_gate_blocks_and_language_guards():
    from aetheros_science.models import ScientificDiscovery
    gate = QualityGate()
    disc = ScientificDiscovery(claim="X", claim_id="c",
                               evidence_ids=[], supporting_experiments=[])
    verdict = gate.evaluate(disc, {})
    assert verdict["passed"] is False
    assert check_causal_language("X causes Y",
                                 causal_evidence=False)["ok"] is False
    assert check_causal_language("X causes Y",
                                 causal_evidence=True)["ok"] is True
    assert check_discovery_language("We discovered X",
                                    gate_passed=False)["ok"] is False
    assert verify_numeric_claims({"a": 1.0}, {"a": 2.0})["status"] == \
        "REPORT_BLOCKED"
    assert verify_numeric_claims({"a": 1.0}, {"a": 1.0})["status"] == "OK"


def test_safety_classification(tmp_path):
    eng = _eng(tmp_path)
    assert eng.safety.classify("COMPUTATIONAL", ["run"]) == "COMPUTATIONAL"
    assert eng.safety.classify("PHYSICAL_LAB", ["pour"]) == \
        "REVIEW_REQUIRED"
    scan = eng.safety.scan_protocol(["synthesize sarin precursor"])
    assert scan["verdict"] == "BLOCK"
    assert eng.lab.status == "LAB_UNAVAILABLE"
    assert eng.lab.execute(["x"])["status"] == "LAB_UNAVAILABLE"


def test_novelty_never_claims_discovery(tmp_path):
    eng = _eng(tmp_path)
    from aetheros_science.models import Hypothesis
    h = Hypothesis(statement="entirely unrelated zyxwv mechanism",
                   mechanism="qqq")
    out = eng.novelty.analyze(h, [])
    assert out["verdict"] == "UNCERTAIN"
    out2 = eng.novelty.analyze(
        h, ["entirely unrelated zyxwv mechanism qqq"])
    assert out2["verdict"] in ("DUPLICATE", "KNOWN")
    assert "discovery" not in out2["statement"].lower()


def test_concurrency_no_corruption(tmp_path):
    eng = _eng(tmp_path, autonomy=4)
    errors = []

    def worker(i):
        try:
            task = eng.create_task(f"q{i}")
            from aetheros_science.models import Hypothesis
            hyp = Hypothesis(task_id=task.id, statement=f"s{i}",
                             variables={"independent": ["x"],
                                        "dependent": ["y"]})
            exp = eng.design_experiment(task, hyp, seed=i)
            eng.execute(task, exp,
                        "open('metrics.json','w').write('{\"i\":1}')", {})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert len(eng.experiments) == 6


def test_performance_smoke(tmp_path):
    import time
    eng = _eng(tmp_path)
    t0 = time.perf_counter()
    for i in range(100):
        eng.create_task(f"question {i}")
    dt = time.perf_counter() - t0
    assert dt < 10.0, f"100 tasks took {dt:.1f}s"
    assert len(eng.tasks) == 100
