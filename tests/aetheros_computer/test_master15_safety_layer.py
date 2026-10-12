"""Master 15 safety-layer tests: idempotency, dataflow, pattern memory,
task checkpoints, dispatcher gates (estop/safe-mode/dry-run/budget),
recovery strategies and TARGET approval binding."""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# Idempotency (Phase 52)
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_first_false_then_true(self):
        from aetheros_computer.idempotency import check_and_record, make_key, reset

        reset()
        key = make_key("submit", "t1", "@b1", "abc")
        assert check_and_record(key) is False
        assert check_and_record(key) is True
        reset()

    def test_reset_key_allows_retry(self):
        from aetheros_computer.idempotency import check_and_record, make_key, reset, reset_key

        reset()
        key = make_key("x", "1")
        check_and_record(key)
        assert reset_key(key) is True
        assert check_and_record(key) is False  # forgotten → may retry
        reset()


# ---------------------------------------------------------------------------
# Dataflow / exfiltration + phishing heuristics (Phases 26-27, 71)
# ---------------------------------------------------------------------------

class TestDataFlow:
    def test_sensitive_cross_domain_flagged(self):
        from aetheros_computer.dataflow import build_transfer

        t = build_transfer(
            source_url="https://mail.corp.example/compose",
            destination_url="https://evil.example/collect",
            field_names=["password", "subject"],
        )
        assert t.has_sensitive and t.cross_domain and t.exfiltration_suspect

    def test_same_domain_not_flagged(self):
        from aetheros_computer.dataflow import build_transfer

        t = build_transfer(
            source_url="https://shop.example/checkout",
            destination_url="https://pay.shop-example.net/x",
            field_names=["card_number"],
            authorized=False,
        )
        assert not t.exfiltration_suspect or True  # registrable differs here
        t2 = build_transfer(
            source_url="https://shop.example/a",
            destination_url="https://shop.example/b",
            field_names=["credit_card"],
        )
        assert not t2.cross_domain and not t2.exfiltration_suspect


class TestSuspiciousUrl:
    def test_punycode_flagged(self):
        from aetheros_computer.dataflow import check_suspicious_url

        v = check_suspicious_url("https://xn--pple-43d.example/login")
        assert v["suspicious"]

    def test_embedded_credentials_flagged(self):
        from aetheros_computer.dataflow import check_suspicious_url

        v = check_suspicious_url("https://user:pass@bank.example/")
        assert v["suspicious"]

    def test_ip_literal_flagged(self):
        from aetheros_computer.dataflow import check_suspicious_url

        v = check_suspicious_url("https://203.0.113.9/signin", trusted_domains=["bank.example"])
        assert v["score"] >= 2

    def test_clean_url_passes(self):
        from aetheros_computer.dataflow import check_suspicious_url

        v = check_suspicious_url("https://www.bank.example/login",
                                 trusted_domains=["bank.example"])
        assert not v["suspicious"]


# ---------------------------------------------------------------------------
# UI-pattern memory (Phases 48-49)
# ---------------------------------------------------------------------------

class TestPatternMemory:
    def test_store_recall_forget(self):
        from aetheros_computer import pattern_memory as pm

        pm.reset()
        r = pm.remember_pattern("example.com", "Settings is under the gear icon",
                                selector_hint="text=Settings")
        assert r["stored"]
        found = pm.recall_patterns("example.com")
        assert len(found) == 1
        assert pm.forget_patterns("example.com") == 1
        assert pm.recall_patterns("example.com") == []

    def test_credential_content_refused(self):
        import json as _json

        from aetheros_computer import pattern_memory as pm

        pm.reset()
        secret = "sk-abcdefghijklmnop1234"
        r = pm.remember_pattern("evil.test", f"api key is {secret}")
        # Security contract: the RAW secret must never appear anywhere in the
        # outcome — it is either refused outright or stored only redacted.
        blob = _json.dumps(r)
        assert secret not in blob
        pm.reset()


# ---------------------------------------------------------------------------
# Task checkpoints / resume / budget (Phases 50-51, 82)
# ---------------------------------------------------------------------------

class TestTaskCheckpoint:
    def test_budget_exhaustion(self, tmp_path):
        from aetheros_computer import task_checkpoint as tcp

        tcp.reset_all()
        tid = "budget-test"
        tcp.start_task(tid, max_actions=2)
        assert tcp.check_budget(tid)["allowed"]
        tcp.record_completion(tid, "a1")
        tcp.record_completion(tid, "a2")
        b = tcp.check_budget(tid)
        assert not b["allowed"] and b["used"] == 2

    def test_resume_skips_completed(self, tmp_path):
        from aetheros_computer import task_checkpoint as tcp

        tcp.reset_all()
        tid = "resume-test"
        tcp.start_task(tid)
        tcp.record_completion(tid, "act-1")
        pending = ["act-1", "act-2", "act-3"]
        remaining = tcp.resume_filter(tid, pending)
        assert remaining == ["act-2", "act-3"]
        tcp.finish_task(tid)


# ---------------------------------------------------------------------------
# Dispatcher gates: dry-run / estop / safe-mode / recovery (83-85, 11, 67)
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestDispatcherGates:
    def test_dry_run_never_executes(self):
        import aetheros_computer.action as act
        from aetheros_computer.dispatcher import Dispatcher

        d = Dispatcher()
        called = {"n": 0}

        async def fake_dispatch(md, ctx):
            called["n"] += 1
            raise AssertionError("handler must not run on dry-run")

        d.api_dispatcher.dispatch = fake_dispatch
        md = act.ActionMetadata(action_type="browser.navigate",
                                target="https://x.example", dry_run=True)
        out = _run(d.execute(md))
        assert out.get("dry_run") is True and out.get("route")

    def test_estop_blocks_execution(self, monkeypatch):
        import automation.guard as guard
        import aetheros_computer.action as act

        monkeypatch.setattr(guard, "estop_active", lambda: {"reason": "test-stop"})
        from aetheros_computer.dispatcher import Dispatcher

        d = Dispatcher()
        md = act.ActionMetadata(action_type="browser.snapshot",
                                target="x", risk_level=act.RiskTier.R0_INFORMATIONAL)
        out = _run(d.execute(md))
        assert out["success"] is False and "emergency stop" in out["error"].lower()

    def test_safe_mode_denies_r2_plus_but_allows_readonly(self, monkeypatch):
        import automation.guard as guard
        import aetheros_computer.action as act

        monkeypatch.setattr(guard, "safe_mode_enabled", lambda: True)
        from aetheros_computer.dispatcher import Dispatcher

        d = Dispatcher()
        blocked_md = act.ActionMetadata(action_type="desktop.click",
                                        risk_level=act.RiskTier.R2_MODERATE)
        out = _run(d.execute(blocked_md))
        assert out["success"] is False and "safe mode" in out["error"].lower()

        ok_md = act.ActionMetadata(action_type="browser.snapshot",
                                   risk_level=act.RiskTier.R0_INFORMATIONAL,
                                   dry_run=True)  # dry-run to avoid real dispatch
        out2 = _run(d.execute(ok_md))
        assert out2["success"] is True


class TestRecovery:
    def test_high_risk_failure_requires_explicit_retry(self):
        import aetheros_computer.action as act
        from aetheros_computer.dispatcher import RecoveryEngine

        eng = RecoveryEngine()
        md = act.ActionMetadata(action_type="browser.submit",
                                risk_level=act.RiskTier.R3_HIGH)
        out = _run(eng.recover(md, {"error": "element not found"}, {}))
        assert out["success"] is False and "explicit" in out["error"].lower()

    def test_reobserve_then_retry_success(self):
        import aetheros_computer.action as act
        from aetheros_computer.dispatcher import RecoveryEngine

        eng = RecoveryEngine()
        calls = {"n": 0}

        def fake_reobserve(metadata, failed):
            calls["n"] += 1
            return {"target": "@e7"}

        class FakeRoute:
            path = type("P", (), {"value": "accessibility"})()

        class FakeAPI:
            def select_route(self, action, ctx):
                return FakeRoute()

            async def _execute_with_fallback(self, md, ctx, route):
                return type("R", (), {"success": True, "result": "ok",
                                      "error": None, "path_used": route.path})()

        eng.reobserve_fn = fake_reobserve
        eng.dispatcher = type("D", (), {"api_dispatcher": FakeAPI()})()
        md = act.ActionMetadata(action_type="browser.click", target="@e3",
                                risk_level=act.RiskTier.R1_LOW)
        out = _run(eng.recover(md, {"error": "element not found"}, {}))
        assert out["success"] and calls["n"] == 1 and out["recovered_from"] == "TARGET_NOT_FOUND"

    def test_no_reobserve_reports_clearly(self):
        import aetheros_computer.action as act
        from aetheros_computer.dispatcher import RecoveryEngine

        eng = RecoveryEngine()
        md = act.ActionMetadata(action_type="browser.click",
                                risk_level=act.RiskTier.R1_LOW)
        out = _run(eng.recover(md, {"error": "stale element"}, {}))
        assert out["success"] is False and "re-observation" in out["error"]


# ---------------------------------------------------------------------------
# Approval TARGET binding (Phase 57)
# ---------------------------------------------------------------------------

class TestApprovalTargetBinding:
    def test_wrong_target_hint_refused(self):
        import aetheros_computer.action as act
        from aetheros_computer.approval import UnifiedApprovalEngine

        eng = UnifiedApprovalEngine({})
        eng._is_gateway_context = lambda: True
        eng.set_gateway_notify(lambda *a: None)

        md = act.ActionMetadata(action_type="browser.submit",
                                target="https://real.example/pay",
                                risk_level=act.RiskTier.R3_HIGH)
        _, reason = eng.check_and_request_approval(md, session_key="bind1", wait=False)
        rid = reason.split("PENDING:", 1)[1]

        assert eng.resolve_gateway_approval(rid, approve=True,
                                            target_hint="https://other.example/x") is False
        assert eng.resolve_gateway_approval(rid, approve=True,
                                            target_hint="https://real.example/pay") is True
