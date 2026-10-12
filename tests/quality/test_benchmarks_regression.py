"""Benchmark engine + baseline store (P3, P13, P17-19, P45-47, P90-91) and
regression engine contracts (P23-27)."""

import json

import pytest

from agent.quality.benchmarks import (
    BaselineStore,
    BenchmarkCheck,
    BenchmarkEngine,
    ComparisonPolicy,
    artifact_hash,
    compare_to_baseline,
)
from agent.quality.models import (
    Baseline,
    FailureClassification,
    RunStatus,
)
from agent.quality.regression import (
    FlakyTracker,
    QuarantineRegistry,
    SuiteResult,
    classify_regressions,
    prioritize,
)


class TestBaselineStore:
    def test_record_and_latest_roundtrip(self, tmp_path):
        store = BaselineStore(persist_path=str(tmp_path / "b.json"))
        old = Baseline(baseline_id="base-old", label="production",
                       version="1.0", metrics={"m": 2.0}, created_at=100.0)
        new = Baseline(baseline_id="base-new", label="production",
                       version="2.0", metrics={"m": 3.0}, created_at=200.0)
        store.record(old)
        store.record(new)
        assert store.latest().version == "2.0"
        assert store.latest("production").metrics["m"] == 3.0
        assert len(store.all()) == 2

    def test_persistence_survives_reload(self, tmp_path):
        path = tmp_path / "b.json"
        BaselineStore(persist_path=str(path)).record(
            Baseline.create("known-good", "3.0", {"score": 0.9}))
        reloaded = BaselineStore(persist_path=str(path))
        assert reloaded.latest("known-good").metrics["score"] == 0.9

    def test_corrupt_file_starts_empty_not_crash(self, tmp_path):
        path = tmp_path / "b.json"
        path.write_text("{not json", encoding="utf-8")
        assert BaselineStore(persist_path=str(path)).all() == []


class TestBaselineComparison:
    BASE = {"task_success_rate": 0.90, "p95_latency_ms": 100.0}

    def _cmp(self, candidate, **policy_kw):
        policy = ComparisonPolicy(**policy_kw) if policy_kw else None
        return compare_to_baseline(
            Baseline.create("production", "1.0", dict(self.BASE)),
            candidate, policy)

    def test_improvement_detected(self):
        results, blocked = self._cmp({"task_success_rate": 0.99})
        assert not blocked
        assert results[0].direction == "improved"

    def test_regression_beyond_threshold_blocks(self):
        results, blocked = self._cmp({"task_success_rate": 0.50})
        assert blocked and results[0].blocked

    def test_small_noise_is_unchanged(self):
        results, _ = self._cmp({"task_success_rate": 0.902})
        assert results[0].direction == "unchanged"

    def test_latency_regression_blocks_lower_is_better_metric(self):
        _, blocked = self._cmp({"p95_latency_ms": 200.0})
        assert blocked

    def test_non_blocking_metric_regression_warns_only(self):
        results, blocked = self._cmp({"startup_time_s": 50.0})
        assert not blocked  # startup_time not in block_on_regression
        assert all(not r.blocked for r in results)

    def test_new_metric_marked_new(self):
        results, _ = self._cmp({"brand_new": 1.0})
        assert results[0].direction == "new"


class TestBenchmarkEngine:
    def _engine(self, fn, name="check_a", critical=False):
        eng = BenchmarkEngine()
        eng.register(BenchmarkCheck(
            name=name, category="functional",
            domains=frozenset({"tools"}), fn=fn, critical=critical))
        return eng

    def test_run_executes_checks_and_completes(self):
        eng = self._engine(lambda: {"score": 0.8})
        run = eng.run(target="agent-core", version="test")
        assert run.status is RunStatus.COMPLETED
        assert run.metrics[0].value == 0.8
        assert run.results["artifact_hash"]

    def test_check_failure_lands_in_failures_not_metrics(self):
        def boom():
            raise RuntimeError("no provider")
        eng = self._engine(boom)
        run = eng.run(target="x", version="y")
        assert run.status is RunStatus.COMPLETED
        assert any("boom" in f or "RuntimeError" in f for f in run.failures)
        assert run.metrics == []

    def test_publish_refuses_unexecuted_run(self):
        from agent.quality.models import EvaluationRun
        pending = EvaluationRun(target="t", version="v", environment="e",
                                dataset="d")
        with pytest.raises(ValueError, match="fabricated"):
            BenchmarkEngine.publish(pending)

    def test_publish_accepts_completed_run(self):
        eng = self._engine(lambda: {"ok": 1.0})
        published = BenchmarkEngine.publish(
            eng.run(target="t", version="v"))
        assert published["status"] == "completed"

    def test_comparison_against_baseline_attaches_verdict(self):
        eng = self._engine(lambda: {"task_success_rate": 0.1})
        base = Baseline.create("production", "1.0",
                               {"check_a.task_success_rate": 0.9})
        run = eng.run(target="t", version="v", baseline=base)
        assert run.results["blocked"] is True

    def test_artifact_hash_is_content_stable(self):
        assert artifact_hash({"a": 1}) == artifact_hash({"a": 1})
        assert artifact_hash({"a": 1}) != artifact_hash({"a": 2})

    def test_domain_and_category_filters(self):
        eng = BenchmarkEngine()
        eng.register(BenchmarkCheck(name="f", category="functional",
                                    domains=frozenset({"memory"}),
                                    fn=lambda: {}))
        eng.register(BenchmarkCheck(name="s", category="security",
                                    domains=frozenset({"tools"}),
                                    fn=lambda: {}))
        assert [c.name for c in eng.checks(domain="memory")] == ["f"]
        assert [c.name for c in eng.checks(category="security")] == ["s"]


class TestRegressionClassification:
    def test_new_failure_detected(self):
        cls = classify_regressions(
            SuiteResult.from_lists(["t1"], []),
            SuiteResult.from_lists(["t1"], ["t2"]))
        assert cls["t2"] is FailureClassification.NEW_FAILURE

    def test_fixed_failure_detected(self):
        cls = classify_regressions(
            SuiteResult.from_lists([], ["t1"]),
            SuiteResult.from_lists(["t1"], []))
        assert cls["t1"] is FailureClassification.FIXED_FAILURE

    def test_pre_existing_preserved(self):
        cls = classify_regressions(
            SuiteResult.from_lists([], ["t1"]),
            SuiteResult.from_lists([], ["t1"]))
        assert cls["t1"] is FailureClassification.PRE_EXISTING_FAILURE

    def test_flaky_overrides_pre_existing(self):
        cls = classify_regressions(
            SuiteResult.from_lists([], ["t1"]),
            SuiteResult.from_lists(["t1"], ["t1"]), known_flaky={"t1"})
        assert cls["t1"] is FailureClassification.FLAKY

    def test_environmental_marker_classification(self):
        cls = classify_regressions(
            SuiteResult.from_lists(["t"], []),
            SuiteResult.from_lists(["t"], ["t"]),
            environmental_markers=("win32-only",))
        # marker must be IN the failing test id to count
        assert cls["t"] is FailureClassification.NEW_FAILURE
        cls2 = classify_regressions(
            SuiteResult.from_lists(["t"], []),
            SuiteResult.from_lists(["t"], ["t[win32-only]"]),
            environmental_markers=("win32-only",))
        assert cls2["t[win32-only]"] is FailureClassification.ENVIRONMENTAL

    def test_expected_change_has_highest_precedence(self):
        cls = classify_regressions(
            SuiteResult.from_lists([], ["t"]),
            SuiteResult.from_lists([], ["t"]),
            known_flaky={"t"}, expected_change_tests={"t"})
        assert cls["t"] is FailureClassification.EXPECTED_CHANGE


class TestFlakyAndQuarantine:
    def test_intermittent_history_flags_flaky(self):
        ft = FlakyTracker(threshold_runs=3)
        for failed in (True, False, True):
            ft.record("t", failed)
        assert ft.is_flaky("t")

    def test_always_failing_is_not_flaky(self):
        ft = FlakyTracker()
        for _ in range(4):
            ft.record("t", True)
        assert not ft.is_flaky("t")

    def test_insufficient_history_conservative(self):
        ft = FlakyTracker(threshold_runs=5)
        for failed in (True, False):
            ft.record("t", failed)
        assert not ft.is_flaky("t")

    def test_quarantine_requires_explicit_reason(self):
        q = QuarantineRegistry()
        with pytest.raises(ValueError):
            q.quarantine("t", reason="   ")

    def test_quarantined_tests_remain_visible(self):
        q = QuarantineRegistry()
        q.quarantine("tests/b.py::t", reason="flaky: fails 1/3 runs")
        q.quarantine("tests/a.py::t", reason="timing sensitive")
        ids = [e.test_id for e in q.visible_entries()]
        assert ids == ["tests/a.py::t", "tests/b.py::t"]
        assert q.is_quarantined("tests/a.py::t")
        assert q.release("tests/a.py::t")
        assert not q.is_quarantined("tests/a.py::t")


class TestPrioritization:
    def test_order_changed_security_critical_golden_rest(self):
        order = prioritize(
            changed_modules=["mod_x"],
            test_module_map={
                "t_changed": "mod_x", "t_sec": "sec_mod",
                "t_crit": "core", "t_gold": "golden", "t_other": "zzz",
            },
            security_tests=["t_sec"],
            critical_regression_tests=["t_crit"],
            golden_tests=["t_gold"])
        assert order == ["t_changed", "t_sec", "t_crit", "t_gold", "t_other"]
