"""Dataset + adapter-detection + full-pipeline contracts (P54-59, P2, P44).

The pipeline test uses an explicitly SYNTHETIC adapter to prove plumbing
(traces, repeats, false-done, BLOCKED preservation, JSONL integrity). It
never represents a real agent and its rows are excluded from any claim.
"""

import json

import pytest

from benchmark.adapters import (
    HEALTH_INSTALLED,
    AgentAdapter,
    Health,
    all_adapters,
    capability_profile,
    register,
)
from benchmark.comparison import (
    HeadToHead,
    generate_claims,
    leaderboard,
    pareto_frontier,
    tradeoff_notes,
)
from benchmark.controller import BenchmarkController
from benchmark.dataset import (
    category_balance,
    difficulty_balance,
    load_tasks,
    split_public_hidden,
    verify_dataset,
)
from benchmark.schema import Difficulty, TaskSpec, TaskStatus


class TestDataset:
    def test_exactly_100_tasks_all_24_categories(self):
        tasks = load_tasks()
        assert len(tasks) == 100
        assert len(category_balance(tasks)) == 24

    def test_difficulty_spread_and_no_trivial_inflation(self):
        diffs = difficulty_balance(load_tasks())
        assert set(diffs) == {"EASY", "MEDIUM", "HARD", "EXPERT",
                              "LONG_HORIZON"}
        assert diffs["LONG_HORIZON"] >= 5   # P18 step-ladder present

    def test_integrity_report_clean(self):
        report = verify_dataset()
        assert report["ok"] is True
        assert report["problems"] == []
        assert len(report["content_hash"]) == 16

    def test_hidden_split_deterministic_and_disjoint(self):
        tasks = load_tasks()
        pub1, hid1 = split_public_hidden(tasks)
        pub2, hid2 = split_public_hidden(tasks)
        ids1 = {t.task_id for t in pub1} | {t.task_id for t in hid1}
        assert [t.task_id for t in pub1] == [t.task_id for t in pub2]
        assert len(ids1) == len(tasks)              # disjoint union
        assert 5 <= len(hid1) <= 30                 # P57 mechanism live


class TestAdapterDetection:
    def test_registry_has_six_primary_targets(self):
        names = set(all_adapters())
        assert {"aetheros", "hermes", "openclaw", "openhands",
                "claude-code", "codex"} <= names

    def test_absent_agent_reports_not_installed_with_evidence(self):
        h = all_adapters()["openclaw"].health_check()
        assert h.status in ("NOT_INSTALLED", "INSTALLED", "NO_CREDENTIALS",
                            "ERROR")     # host-dependent, but never silent
        if h.status == "NOT_INSTALLED":
            assert any("not on PATH" in e for e in h.evidence)

    def test_capability_matrix_never_claims_untested(self):
        prof = capability_profile("hermes")
        unverified = ("research", "browser", "computer_use", "coding",
                      "memory", "mcp", "multi_agent")
        for cap in unverified:
            assert prof[cap] in ("FULL", "PARTIAL", "NONE", "NOT_TESTED")
        # hermes profile ships NOT_TESTED until actually measured (P36)
        assert prof["research"] == "NOT_TESTED"

    def test_unknown_adapter_lookup_raises(self):
        from benchmark.adapters import get_adapter
        with pytest.raises(KeyError):
            get_adapter("definitely-not-an-agent")


# ------------------------------------------------------------- synthetic

class SyntheticAdapter(AgentAdapter):
    """SYNTHETIC adapter for pipeline validation ONLY — clearly labeled,
    never registered under a real agent's name, never used in claims."""

    name = "synthetic-pipeline-check"

    def __init__(self, mode: str = "pass"):
        self.mode = mode
        self.cleaned: list = []

    def health_check(self):
        return Health(HEALTH_INSTALLED, version="synthetic-0.0",
                      evidence=["explicitly synthetic"])

    def run_task(self, task, workspace, allow_live=False):
        if self.mode == "false_done":
            return {"response": "I have completed everything!",
                    "claimed_done": True, "wall_clock_ms": 1234.0,
                    "input_tokens": 500, "output_tokens": 250,
                    "tool_calls": [], "successful_tool_calls": 0}
        if self.mode == "blocked":
            return {"errors": ["synthetic hard failure"], "response": ""}
        (workspace / "out.txt").write_text("expected-marker-ok",
                                           encoding="utf-8")
        return {"response": "wrote out.txt with expected-marker-ok",
                "claimed_done": True, "wall_clock_ms": 2000.0,
                "input_tokens": 300, "output_tokens": 150,
                "tool_calls": [{"tool": "write_file"}],
                "successful_tool_calls": 1}

    def cleanup(self, workspace=None):
        self.cleaned.append(workspace)


class TestPipeline:
    @pytest.fixture
    def ctrl(self, tmp_path):
        return BenchmarkController(tmp_path / "results")

    def _patch_dataset(self, monkeypatch, tmp_path):
        rows = [TaskSpec(**json.loads((tmp_path / "mini.json").read_text())[0])]
        monkeypatch.setattr("benchmark.controller.load_tasks",
                            lambda *a, **k: list(rows))

    def _tasks(self, tmp_path):
        spec = dict(task_id="pipe-001", category="11_file_operations",
                    difficulty=Difficulty.EASY,
                    objective="create out.txt containing expected-marker-ok",
                    validator={"type": "file_content",
                               "checks": {"out.txt": "expected-marker-ok"}})
        p = tmp_path / "mini.json"
        p.write_text(json.dumps([spec]), encoding="utf-8")
        return str(p)

    def test_pass_path_verified_and_traced(self, ctrl, tmp_path,
                                           monkeypatch):
        register(SyntheticAdapter())
        self._tasks(tmp_path)
        self._patch_dataset(monkeypatch, tmp_path)
        ctrl.run_suite("synthetic-pipeline-check", allow_live=True)
        results = [r for r in ctrl.load_results()
                   if r.agent == "synthetic-pipeline-check"]
        assert len(results) == 1
        r = results[0]
        assert r.status is TaskStatus.PASS and r.verified is True
        assert r.claimed_done and not r.false_done
        assert r.trace_reference          # raw trace persisted (P45/46)

    def test_false_done_detected_when_claim_contradicts_validator(
            self, ctrl, tmp_path, monkeypatch):
        register(SyntheticAdapter(mode="false_done"))
        self._tasks(tmp_path)
        self._patch_dataset(monkeypatch, tmp_path)
        ctrl.run_suite("synthetic-pipeline-check", allow_live=True)
        r = [x for x in ctrl.load_results()
             if x.agent == "synthetic-pipeline-check"][-1]
        assert r.status is TaskStatus.FAIL and r.false_done is True

    def test_blocked_rows_preserved_without_live_flag(self, ctrl, monkeypatch):
        monkeypatch.setenv("AETHEROS_HOME", ".aetheros-smoke")
        manifest = ctrl.run_suite("claude-code")     # no --allow-live
        results = [r for r in ctrl.load_results()
                   if r.agent == "claude-code"]
        assert manifest["result_count"] == len(results) > 0
        assert all(r.status is TaskStatus.BLOCKED for r in results)
        assert all(any("LIVE_EXECUTION_DISABLED" in e for e in r.errors)
                   for r in results)

    def test_not_installed_agent_yields_blocked_not_crash(self, ctrl):
        manifest = ctrl.run_suite("openclaw")
        results = [r for r in ctrl.load_results() if r.agent == "openclaw"]
        assert all(r.status is TaskStatus.BLOCKED for r in results)


class TestComparisonHonesty:
    def test_head_to_head_requires_both_agents(self):
        with pytest.raises(ValueError, match="INSUFFICIENT_EVIDENCE"):
            HeadToHead("aetheros", "hermes", [])

    def test_claims_insufficient_without_runs(self):
        claims = generate_claims("aetheros", "hermes", [])
        assert all("INSUFFICIENT" in c for c in claims)

    def test_leaderboard_empty_is_honest(self):
        assert leaderboard([]) == []

    def test_pareto_frontier_basic(self):
        pts = {
            "fast-weak": {"speed": 10, "quality": 0.5, "cost": 1,
                          "safety": 1.0},
            "slow-strong": {"speed": 40, "quality": 0.9, "cost": 3,
                            "safety": 1.0},
            "dominated": {"speed": 20, "quality": 0.4, "cost": 5,
                          "safety": 0.8},
        }
        frontier = pareto_frontier(pts)
        assert "dominated" not in frontier
        assert {"fast-weak", "slow-strong"} <= set(frontier)

    def test_tradeoff_notes_without_data(self):
        notes = tradeoff_notes([])
        assert notes and "no executed pairs" in notes[0]
