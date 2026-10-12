"""Dataset integrity (P30-31), diagnostics/RCA discipline (P55-60),
improvement proposal safety (P61-66), knowledge base (P80-81),
rollout/rollback (P9, P68-71) and trends (P93-94)."""

import pytest

from agent.quality.datasets import (
    DatasetIntegrityError,
    DatasetRegistry,
)
from agent.quality.diagnostics import (
    ChangeRecord,
    DiagnosticEngine,
    FailureRecord,
)
from agent.quality.gates import GateInput, ReleaseGateEngine
from agent.quality.improvement import (
    FailureSignal,
    ProposalEngine,
    UnsafeAutoApply,
)
from agent.quality.knowledge import (
    KnownIssuesDatabase,
    RegressionKnowledgeBase,
    seed_documented_issues,
)
from agent.quality.models import (
    ChangeProposal,
    ChangeRisk,
    GateStatus,
    KnownIssue,
    KnowledgeEntry,
    RolloutStage,
)
from agent.quality.rollout import RolloutController, RolloutPolicy
from agent.quality.trends import TrendTracker


class TestDatasets:
    def test_create_then_add_version_requires_change_note(self):
        reg = DatasetRegistry()
        reg.create(name="golden-core", records=[{"id": 1}],
                   source="repo", license="MIT", schema="v1")
        with pytest.raises(DatasetIntegrityError):
            reg.add_version("golden-core", records=[{"id": 2}],
                            change_note="")

    def test_identical_content_rejected(self):
        reg = DatasetRegistry()
        reg.create(name="d", records=[{"a": 1}], source="s",
                   license="l", schema="x")
        with pytest.raises(DatasetIntegrityError, match="identical"):
            reg.add_version("d", records=[{"a": 1}], change_note="no-op")

    def test_versions_are_immutable_history(self):
        reg = DatasetRegistry()
        reg.create(name="d", records=[{"a": 1}], source="s",
                   license="l", schema="x")
        reg.add_version("d", records=[{"a": 2}], change_note="bump a")
        v1, v2 = reg.history("d")
        assert v1.records == [{"a": 1}] and v1.version == 1
        assert v2.version == 2 and v2.change_note == "bump a"

    def test_tamper_detection(self):
        reg = DatasetRegistry()
        reg.create(name="d", records=[{"secret": "orig"}], source="s",
                   license="l", schema="x")
        reg.latest("d").records[0]["secret"] = "tampered"
        assert not reg.verify_integrity("d", 1)

    def test_duplicate_create_refused(self):
        reg = DatasetRegistry()
        reg.create(name="d", records=[], source="s", license="l", schema="x")
        with pytest.raises(DatasetIntegrityError, match="already exists"):
            reg.create(name="d", records=[], source="s", license="l",
                       schema="x")


class TestDiagnostics:
    def _failure(self, when=1000.0):
        return FailureRecord(
            failure_id="f1", what="tool timeout", where="terminal",
            when=when, task_id="task-7", agent_id="ag-1", tool_id="terminal",
            commit="cafe123", release="2.0", environment="win32",
            raw_error="TimeoutExpired")

    def test_full_correlation_map(self):
        d = DiagnosticEngine().correlate(self._failure())
        assert d["task"] == ["task-7"] and d["commit"] == ["cafe123"]
        assert d["environment"] == ["win32"]

    def test_diagnosis_never_claims_cause_without_evidence(self):
        diag = DiagnosticEngine().diagnose(self._failure())
        assert diag.confidence == "UNKNOWN"
        assert "undetermined" in diag.likely_cause

    def test_evidence_backed_confidence_preserved(self):
        diag = DiagnosticEngine().diagnose(
            self._failure(), evidence=["log line 42 shows retry storm"],
            likely_cause="provider rate limit", confidence="LIKELY")
        assert diag.confidence == "LIKELY"
        assert any("log line 42" in e for e in diag.evidence)

    def test_latest_commit_not_auto_blamed_but_listed_as_candidate(self):
        eng = DiagnosticEngine(changes=[
            ChangeRecord(commit="aaa", description="tweak terminal",
                         components=["terminal"], timestamp=900.0),
            ChangeRecord(commit="bbb", description="unrelated docs change",
                         components=["docs"], timestamp=999.0),
            ChangeRecord(commit="ccc", description="rewrite gateway",
                         components=["gateway"], timestamp=995.0),
        ])
        related = eng.related_changes(self._failure(when=1000.0))
        # only component-overlapping changes; newest-first among them;
        # unrelated-but-newer commit is NOT included
        commits = [c.commit for c, _why in related]
        assert commits == ["aaa"]
        reasons = [why for _, why in related]
        assert all("touches failed component" in r for r in reasons)

    def test_report_contains_all_required_sections(self):
        diag = DiagnosticEngine().diagnose(
            self._failure(), impact="one task lost",
            recommended_action="raise provider timeout to 30s")
        report = DiagnosticEngine().render_report(diag)
        for key in ("WHAT:", "WHERE:", "WHEN:", "IMPACT:", "CAUSE:",
                    "ACTION:"):
            assert key in report


class TestProposalSafety:
    def test_signals_derive_proposals_with_thresholds(self):
        eng = ProposalEngine()
        props = eng.from_signals([
            FailureSignal(kind="repeated_failure", component="cron",
                          count=3, last_message="tick crash"),
            FailureSignal(kind="repeated_failure", component="cron",
                          count=1, last_message="once only"),
        ])
        assert len(props) == 1
        assert props[0].components == ["cron"]

    def test_security_finding_always_escalates_to_critical(self):
        eng = ProposalEngine()
        (p,) = eng.from_signals([
            FailureSignal(kind="security_finding", component="authz",
                          count=1, last_message="token leak path")])
        assert p.risk is ChangeRisk.CRITICAL
        assert p.requires_human_approval

    def test_apply_refuses_non_allowlisted_change(self):
        eng = ProposalEngine(safe_actions={
            "formatting": lambda p: "formatted"})
        rogue = ChangeProposal(
            description="rewrite auth middleware", reason="seems fine",
            components=["authentication"], expected_benefit="speed",
            evidence=["benchmark x"], rollback_plan="git revert",
            author="agent", auto_applicable=True)
        with pytest.raises(UnsafeAutoApply):
            eng.apply(rogue)

    def test_apply_executes_allowlisted_trivial_fix(self):
        executed = []
        eng = ProposalEngine(safe_actions={
            "clear_safe_cache": lambda p: executed.append(p) or "cleared"})
        ok = ChangeProposal(
            description="clear_safe_cache: stale tool schema cache",
            reason="schema drift after upgrade", components=["cache"],
            expected_benefit="fresh schemas", evidence=["hash mismatch"],
            rollback_plan="none needed; cache regenerates",
            author="quality-engine", auto_applicable=True)
        # risk stays TRIVIAL (cache is not a critical component)
        assert not ok.requires_human_approval
        assert eng.apply(ok) == "cleared"
        assert executed


class TestKnowledgeAndGates:
    def test_seed_creates_open_documented_issues(self):
        db = KnownIssuesDatabase()
        seed_documented_issues(db)
        assert len(db.open_issues()) >= 5
        assert db.get("KI-WINDOWS-PTY").severity == "high"

    def test_close_issue_removes_from_open(self):
        db = KnownIssuesDatabase()
        seed_documented_issues(db)
        assert db.close("KI-DISPLAY-STRINGS")
        assert all(i.issue_id != "KI-DISPLAY-STRINGS"
                   for i in db.open_issues())

    def test_kb_lookup_by_component_and_failure(self):
        kb = RegressionKnowledgeBase()
        kb.add(KnowledgeEntry(failure="PTY spawn hang", cause="winpty pipe",
                              fix="use ConPTY bridge", test="test_pty",
                              version="2.0", component="terminal"))
        assert kb.lookup_by_component("Terminal")
        assert kb.lookup_by_failure("pty")

    def test_missing_gate_is_block_not_pass(self):
        sc = ReleaseGateEngine().evaluate(inputs=[
            GateInput(gate="FUNCTIONAL", checks_passed=3)],
            rollback_available=True)
        by_name = {g.gate: g for g in sc.gates}
        assert by_name["FUNCTIONAL"].status is GateStatus.PASS
        assert by_name["SECURITY"].status is GateStatus.BLOCK
        assert by_name["SECURITY"].blocking_reason == "gate never evaluated"
        assert not sc.ready

    def test_security_findings_block_release(self):
        inputs = [GateInput(gate=n, checks_passed=5) for n in
                  ("FUNCTIONAL", "SECURITY", "PERFORMANCE", "RELIABILITY",
                   "COMPATIBILITY", "INSTALLER", "DOCUMENTATION")]
        sc = ReleaseGateEngine().evaluate(
            inputs, security_findings=["CVE-sim in dep X"])
        sec = next(g for g in sc.gates if g.gate == "SECURITY")
        assert sec.status is GateStatus.BLOCK

    def test_all_green_with_rollback_is_ready(self):
        inputs = [GateInput(gate=n, checks_passed=5) for n in
                  ("FUNCTIONAL", "SECURITY", "PERFORMANCE", "RELIABILITY",
                   "COMPATIBILITY", "INSTALLER", "DOCUMENTATION")]
        sc = ReleaseGateEngine().evaluate(
            inputs, rollback_available=True, tests_passed=100)
        assert sc.ready

    def test_unavailable_rollback_degrades_to_warn_not_ready_claim(self):
        inputs = [GateInput(gate=n, checks_passed=5) for n in
                  ("FUNCTIONAL", "SECURITY", "PERFORMANCE", "RELIABILITY",
                   "COMPATIBILITY", "INSTALLER", "DOCUMENTATION")]
        sc = ReleaseGateEngine().evaluate(inputs, rollback_available=False)
        assert sc.ready  # WARN does not hard-block...
        assert sc.rollback_available is False  # ...but is honestly recorded

    def test_open_critical_known_issues_recorded_on_scorecard(self):
        inputs = [GateInput(gate=n, checks_passed=5) for n in
                  ("FUNCTIONAL", "SECURITY", "PERFORMANCE", "RELIABILITY",
                   "COMPATIBILITY", "INSTALLER", "DOCUMENTATION")]
        issues = [KnownIssue(issue_id="KI-CRIT", title="data loss risk",
                             severity="critical", workaround="restore backup")]
        sc = ReleaseGateEngine().evaluate(
            inputs, known_issues=issues, rollback_available=True)
        assert "KI-CRIT" in sc.known_issues


class TestRollout:
    POLICY = RolloutPolicy()

    def _controller(self):
        return RolloutController(policy=self.POLICY, flags={"new_path": True})

    def test_flag_boolean_and_percent_semantics(self):
        ctl = RolloutController(flags={"on": True, "half": 50})
        assert ctl.flag_enabled("on") is True
        assert ctl.flag_enabled("half", percent_env=25) is True
        assert ctl.flag_enabled("half", percent_env=80) is False
        assert ctl.flag_enabled("missing") is False

    def test_staged_advance_to_full(self):
        ctl = self._controller()
        ctl.start("9.9")
        healthy = {"error_rate": 0.01, "latency_p95_ms": 300.0,
                   "task_success_rate": 0.97, "security_events": 0}
        ctl.advance(healthy)   # canary -> medium
        assert ctl.state.stage is RolloutStage.MEDIUM
        ctl.advance(healthy)   # medium -> full
        assert ctl.state.stage is RolloutStage.FULL

    def test_breach_triggers_auto_rollback_with_validation(self):
        ctl = self._controller()
        ctl.start("9.9")
        bad = {"error_rate": 0.40, "task_success_rate": 0.60,
               "security_events": 2}
        state = ctl.advance(bad)
        assert state.rolled_back and state.stage is RolloutStage.NONE
        assert state.validation["service_health"] is False
        assert state.validation["security_state"] is False
        assert any("ROLLBACK" in e for e in ctl.events)

    def test_success_slo_breach_also_blocks(self):
        ctl = self._controller()
        ctl.start("9.9")
        state = ctl.advance({"task_success_rate": 0.5})
        assert state.breached and state.rolled_back


class TestTrends:
    def test_quiet_until_min_points(self):
        tt = TrendTracker()
        for v in (10, 20, 30):
            assert tt.record("error_rate", v) is None

    def test_lower_is_better_deterioration_alerts(self):
        tt = TrendTracker()
        last = None
        for v in (10, 10, 10, 10, 50, 50, 50, 50):
            last = tt.record("error_rate", v)
        assert last is not None and last.kind == "deterioration"

    def test_higher_is_better_direction_respected(self):
        tt = TrendTracker(lower_is_better={"throughput": False})
        last = None
        for v in (100, 100, 100, 100, 10, 10, 10, 10):
            last = tt.record("throughput", v)
        assert last is not None and last.kind == "deterioration"

    def test_improvement_does_not_alert(self):
        tt = TrendTracker()
        last = None
        for v in (50, 50, 50, 50, 10, 10, 10, 10):
            last = tt.record("error_rate", v)
        assert last is None

    def test_summary_shape(self):
        tt = TrendTracker()
        tt.record("cost_usd", 1.0)
        s = tt.summary()["cost_usd"]
        assert s["points"] == 1 and s["latest"] == 1.0
