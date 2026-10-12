"""Master 51 test matrix (§203): traces, redaction, evals, failures,
lessons, experiments, canary, rollback, drift, budgets, privacy."""
from __future__ import annotations

import pytest

from aetheros_self_improvement import SelfImprovementEngine
from aetheros_self_improvement.deploy import DeploymentController
from aetheros_self_improvement.experiments import (BudgetExceeded,
                                                   ExperimentRunner,
                                                   env_fingerprint)
from aetheros_self_improvement.failures import (FailureAnalyzer,
                                                RootCauseAnalyzer,
                                                classify_severity)
from aetheros_self_improvement.graders_eval import (EvalDataset,
                                                    EvaluationEngine,
                                                    ensemble)
from aetheros_self_improvement.lessons import LessonEngine
from aetheros_self_improvement.models import AgentTrace, EvalTask
from aetheros_self_improvement.monitoring import (DriftDetector,
                                                  eval_health,
                                                  metric_integrity)
from aetheros_self_improvement.suites import EXECUTORS, run_suite
from aetheros_self_improvement.traces import RedactionEngine, TraceStore


def _eng(tmp_path, autonomy="I5"):
    return SelfImprovementEngine(tmp_path / "intel", plane=None,
                                 autonomy=autonomy)


# -- traces ---------------------------------------------------------------
def test_trace_creation_and_persistence(tmp_path):
    eng = _eng(tmp_path)
    tid = eng.observe({"task_id": "t1", "user_intent": "add 2+3",
                       "final_outcome": "5", "agent_identity": "a1"})
    assert tid
    rows = eng.traces.list("default")
    assert len(rows) == 1 and rows[0]["redacted"] is True


def test_trace_redaction_removes_secrets(tmp_path):
    eng = _eng(tmp_path)
    tid = eng.observe({"task_id": "t9",
                       "user_intent": "use key sk-abcdefgh12345678 please",
                       "final_outcome": "done",
                       "tool_calls": [{"tool": "x", "args":
                                       "pw password=supersecret1"}]})
    rows = eng.traces.list("default")
    blob = str(rows[0])
    assert "sk-abcdefgh12345678" not in blob
    assert "supersecret1" not in blob


def test_private_mode_blocks_collection(tmp_path):
    eng = _eng(tmp_path)
    eng.traces.private_mode = True
    assert eng.observe({"task_id": "t", "final_outcome": "x"}) is None
    assert eng.traces.list("default") == []


def test_tenant_isolation(tmp_path):
    store = TraceStore(tmp_path / "t")
    store.record(AgentTrace(task_id="a", tenant="tenant-a",
                            final_outcome="ok"))
    assert store.list("tenant-b") == []
    assert len(store.list("tenant-a")) == 1


def test_retention_purge(tmp_path):
    import time
    store = TraceStore(tmp_path / "t")
    old = AgentTrace(task_id="old", tenant="d", final_outcome="x")
    old.timestamp = time.time() - 40 * 86400
    store.record(old)
    store.record(AgentTrace(task_id="new", tenant="d", final_outcome="y"))
    assert store.purge_older_than("d", 30.0) == 1
    assert len(store.list("d")) == 1


# -- graders / evals ---------------------------------------------------------
def test_deterministic_grader_modes():
    t = EvalTask(id="t", inputs={}, expected_outcome=42,
                 success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    assert ensemble(t, 42, {})["passed"] is True
    assert ensemble(t, 43, {})["passed"] is False
    t2 = EvalTask(id="t2", inputs={}, expected_outcome="ell",
                  success_criteria={"mode": "contains"},
                  graders=["deterministic"])
    assert ensemble(t2, "hello", {})["passed"] is True


def test_hard_gate_cannot_be_overridden():
    t = EvalTask(id="s", inputs={},
                 security_requirements=["no_shell"],
                 failure_criteria=["x"],
                 graders=["static_analysis"])
    bad = ensemble(t, "import os\nos.system('rm -rf /')", {})
    assert bad["hard_gate_failed"] == ["static_analysis"]
    assert bad["passed"] is False


def test_model_grader_unavailable_not_fake():
    from aetheros_self_improvement.graders_eval import ModelGrader
    from aetheros_self_improvement.graders_eval import GraderUnavailable
    with pytest.raises(GraderUnavailable):
        ModelGrader().grade(EvalTask(id="m", inputs={}), "x", {})


def test_multi_trial_aggregation():
    eng = EvaluationEngine()
    t = EvalTask(id="a", inputs={"op": "add", "a": 1, "b": 2},
                 expected_outcome=3, success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    rows = eng.run_task(t, EXECUTORS["arithmetic"], trials=5, seed=1)
    agg = EvaluationEngine.aggregate(rows)
    assert agg["trials"] == 5 and agg["success_rate"] == 1.0
    assert agg["total_tokens"] == 25


def test_capability_and_regression_suites(tmp_path):
    eng = _eng(tmp_path)
    cap = run_suite(eng, "capability")
    assert cap["trials"] == 6 and cap["hard_gate_failures"] == 0
    reg = run_suite(eng, "regression")
    assert reg["passed"] == reg["trials"]


def test_security_suite_gate_bites(tmp_path):
    eng = _eng(tmp_path)
    sec = run_suite(eng, "security")
    assert sec["hard_gate_failures"] >= 1  # dirty variant must fail


# -- failures ------------------------------------------------------------------
def test_failure_detection_and_severity():
    fa = FailureAnalyzer()
    rec = fa.from_trace({"trace_id": "t", "tenant": "d",
                         "errors": [{"message": "boom"}],
                         "user_intent": "do x"}, "tool_execution",
                        {"task_failed": True})
    assert rec.severity == "F3"
    assert classify_severity({"security_violation": True,
                              "critical": True}) == "F5"
    assert classify_severity({}) == "F0"


def test_root_cause_divergence_walk():
    fa = FailureAnalyzer()
    trace = {"trace_id": "t", "tool_calls": [
        {"tool": "search", "result": "ok"},
        {"tool": "browser", "error": "timeout"}],
        "retries": 3, "user_intent": "x", "final_outcome": "fail"}
    rec = fa.from_trace(trace, "tool_execution", {"task_failed": True})
    cause = RootCauseAnalyzer().analyze(trace, rec)
    assert cause.divergence_step == 1
    assert cause.could_detect_earlier is True
    assert cause.evidence


def test_counterfactual_actually_runs():
    out = RootCauseAnalyzer().counterfactual(
        {"a": 1}, lambda i, c: {"outcome": i["a"] + c.get("b", 0)},
        {"v1": {"b": 1}, "v2": {"b": 2}})
    assert out["v1"]["outcome"] == 2 and out["v2"]["outcome"] == 3


def test_clustering_and_hotspots():
    fa = FailureAnalyzer()
    for _ in range(3):
        fa.from_trace({"trace_id": "t", "errors": [{"message": "e"}]},
                      "tool_execution", {"task_failed": True})
    assert fa.cluster()[0]["count"] == 3
    assert fa.hotspots()["by_class"]["tool_execution"] == 3


# -- lessons ---------------------------------------------------------------------
def test_lesson_lifecycle_validation():
    le = LessonEngine(min_evidence=2)
    lesson = le.propose("o", "g", "task", "t1", ["tr1"])
    assert lesson.status == "unverified"
    le.add_evidence(lesson.id, "tr2")
    assert lesson.status == "supported"
    assert le.validate(lesson.id) is True


def test_lesson_conflict_not_silent_overwrite():
    le = LessonEngine()
    a = le.propose("o", "do X", "project", "p1", ["t1"])
    b = le.propose("o", "do Y", "project", "p1", ["t2"])
    assert a.status == "contradicted" and b.status == "contradicted"
    assert len(le.conflicts) == 1


def test_lesson_expiration_and_global_gate():
    le = LessonEngine(min_evidence=1)
    lesson = le.propose("o", "g", "task", "t", ["t1"])
    le.add_evidence(lesson.id, "t2")  # §167: multiple independent examples
    le.validate(lesson.id)
    assert le.promote_global(lesson.id) is False  # missing reviews
    assert le.promote_global(lesson.id, True, True, True) is True
    assert lesson.scope == "global_candidate"
    lesson.expires_at = 1.0
    assert le.expire_stale() == [lesson.id]


# -- experiments -------------------------------------------------------------------
def test_experiment_baseline_comparison_and_isolation(tmp_path):
    eng = _eng(tmp_path)
    t = EvalTask(id="x", inputs={"text": "Hi"},
                 expected_outcome="HI",
                 success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    exp = eng.runner.create([t], {"mode": "upper"}, {"mode": "upper"})
    res = eng.runner.run(exp, [t], EXECUTORS["transform"], trials=2)
    assert res["status"] == "done"
    comp = eng.runner.compare(exp)
    assert comp["success_delta"] == 1.0 - 1.0
    assert "workdir" in exp.results  # isolated temp workspace


def test_experiment_budget_enforced(tmp_path):
    eng = _eng(tmp_path)
    t = EvalTask(id="x", inputs={"text": "Hi"},
                 expected_outcome="HI",
                 success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    exp = eng.runner.create([t], {}, {}, budgets={"maxTrials": 1,
                                                  "maxTime": 60.0})
    with pytest.raises(BudgetExceeded):
        eng.runner.run(exp, [t], EXECUTORS["transform"], trials=2)


def test_experiment_cancel_and_env_fingerprint(tmp_path):
    eng = _eng(tmp_path)
    exp = eng.runner.create([], {}, {})
    eng.runner.cancel(exp.id)
    assert eng.runner.run(exp, [], EXECUTORS["transform"])["status"] \
        == "cancelled"
    fp = env_fingerprint()
    assert {"os", "python", "fabric"} <= set(fp)


# -- deploy --------------------------------------------------------------------------
def test_promotion_ladder_and_rollback():
    dc = DeploymentController()
    dep = dc.stage_deployment("p1", "v1", "a", "r")
    for stage in ("sandbox", "shadow", "canary", "limited", "general"):
        dc.promote(dep, approval_id="apr")
        assert dep.stage == stage
    assert dep.traffic_pct == 100.0
    verdict = dc.check_metrics(dep, {"success_rate": 0.9},
                               {"success_rate": 0.5, "violations": 0,
                                "mean_latency_ms": 10,
                                "cost_usd": 0.1})
    assert verdict["rollback"] is True
    assert dep.state == "rolled_back"
    assert dc.rollback_log and dc.rollback_log[0]["trigger"] == "automatic"


def test_config_rollback_returns_known_good():
    dc = DeploymentController()
    dc.publish_config("prompt", "v1", {"text": "old"})
    dc.publish_config("prompt", "v2", {"text": "new"})
    dc.active["prompt"] = "v2"
    assert dc.rollback_config("prompt", "v1", "op", "bad v2") is True
    assert dc.active["prompt"] == "v1"


def test_drift_and_eval_health():
    dd = DriftDetector(rel_threshold=0.2)
    dd.set_baseline("latency", 100.0)
    assert dd.observe("latency", "latency", 105.0) is None
    ev = dd.observe("latency", "latency", 200.0)
    assert ev is not None and ev.kind == "latency"
    assert eval_health([1.0, 1.0, 0.99])["saturated"] is True
    assert metric_integrity({"target_metric": 1, "success_rate": 0.9},
                            {"target_metric": 2,
                             "success_rate": 0.5})["gaming_suspected"] is True
