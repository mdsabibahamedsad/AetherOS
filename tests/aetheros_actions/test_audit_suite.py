"""Phase 2L — AuditLogger tests: event coverage + sensitive-data redaction.

Covers: record of every pipeline event, redaction of secrets in meta (nested),
bounded ring storage, backend passthrough, and the no-sensitive-data invariant.
"""

from __future__ import annotations

import pytest

from aetheros_actions.audit import AuditLogger, _redact
from aetheros_actions.model import Action, ActionType, RiskLevel


def _act(**kw) -> Action:
    return Action(action_type=kw.get("action_type", ActionType.CLICK),
                  target=kw.get("target", "b"),
                  agent_id=kw.get("agent_id", "ag"),
                  session_id=kw.get("session_id", "ss"),
                  permission=kw.get("permission", "click"),
                  risk_level=kw.get("risk_level", RiskLevel.LOW))


class TestEventCoverage:
    def test_action_requested(self):
        log = AuditLogger()
        e = log.record(_act(), decision="PENDING")
        assert e["decision"] == "PENDING"
        assert e["action_type"] == "CLICK"

    def test_approved(self):
        log = AuditLogger()
        assert log.record(_act(), decision="ALLOW")["decision"] == "ALLOW"

    def test_denied(self):
        log = AuditLogger()
        assert log.record(_act(), decision="DENY")["decision"] == "DENY"

    def test_executed(self):
        log = AuditLogger()
        e = log.record(_act(), decision="ALLOW", ok=True, elapsed_ms=12.5)
        assert e["ok"] is True
        assert e["elapsed_ms"] == 12.5

    def test_failed(self):
        log = AuditLogger()
        e = log.record(_act(), decision="ALLOW", ok=False, error="boom")
        assert e["ok"] is False
        assert e["error"] == "boom"

    def test_decision_required_permission(self):
        log = AuditLogger()
        e = log.record(_act(permission="approve"), decision="REQUIRE_CONFIRMATION")
        assert e["permission"] == "approve"

    def test_entry_metadata(self):
        log = AuditLogger()
        e = log.record(_act(agent_id="a", session_id="s"), decision="ALLOW")
        assert e["agent_id"] == "a"
        assert e["session_id"] == "s"
        assert e["action_type"] == "CLICK"
        assert "ts" in e


class TestRedaction:
    def test_sensitive_keys_redacted(self):
        log = AuditLogger()
        e = log.record(_act(), decision="ALLOW",
                       meta={"password": "hunter2", "token": "abc", "note": "safe"})
        assert e["meta"]["password"] == "<redacted>"
        assert e["meta"]["token"] == "<redacted>"
        assert e["meta"]["note"] == "safe"

    def test_nested_redaction(self):
        log = AuditLogger()
        e = log.record(_act(), decision="DENY",
                       meta={"inner": {"api_key": "k", "api_key_name": "ok", "ok": 1}})
        assert e["meta"]["inner"]["api_key"] == "<redacted>"
        assert e["meta"]["inner"]["ok"] == 1

    def test_list_values_redacted(self):
        log = AuditLogger()
        e = log.record(_act(), decision="ALLOW", meta={"tokens": ["a", "b"], "ids": [1, 2]})
        assert e["meta"]["tokens"] == ["<redacted>", "<redacted>"]
        assert e["meta"]["ids"] == [1, 2]

    def test_secret_word_key_redacted(self):
        log = AuditLogger()
        e = log.record(_act(), decision="ALLOW", meta={"credential": "x", "password2": "y"})
        assert e["meta"]["credential"] == "<redacted>"
        assert e["meta"]["password2"] == "<redacted>"

    def test_direct_redact_helper(self):
        assert _redact({"token": "x", "safe": [1, {"password": "y"}]}) == {
            "token": "<redacted>", "safe": [1, {"password": "<redacted>"}]}


class TestStorage:
    def test_entries_append_in_order(self):
        log = AuditLogger()
        log.record(_act(), decision="PENDING")
        log.record(_act(), decision="ALLOW")
        assert [e["decision"] for e in log.entries()] == ["PENDING", "ALLOW"]

    def test_entries_limit(self):
        log = AuditLogger()
        for i in range(5):
            log.record(_act(target=f"t{i}"), decision="ALLOW")
        assert [e["target"] for e in log.entries(2)] == ["t3", "t4"]

    def test_ring_bounded(self):
        log = AuditLogger(max_entries=3)
        for i in range(10):
            log.record(_act(target=f"t{i}"), decision="ALLOW")
        assert len(log.entries()) == 3

    def test_clear(self):
        log = AuditLogger()
        log.record(_act(), decision="ALLOW")
        log.clear()
        assert log.entries() == []

    def test_record_without_action(self):
        log = AuditLogger()
        e = log.record(None, decision="PENDING")
        assert e["action_type"] == ""
        assert e["agent_id"] == ""


class TestBackend:
    def test_backend_receives_summary(self):
        class FakeBackend:
            def __init__(self):
                self.calls = []

            def record(self, **kw):
                self.calls.append(kw)

        backend = FakeBackend()
        log = AuditLogger(backend=backend)
        log.record(_act(), decision="DENY", ok=False, error="nope")
        assert len(backend.calls) == 1
        c = backend.calls[0]
        assert c["action"] == "CLICK"
        assert c["allowed"] is False
        assert c["permission"] == "click"
        assert "DENY" in c["summary"]

    def test_backend_exception_swallowed(self):
        class BrokenBackend:
            def record(self, **kw):
                raise RuntimeError("backend exploded")

        log = AuditLogger(backend=BrokenBackend())
        # must not propagate; in-memory entry still recorded.
        e = log.record(_act(), decision="ALLOW")
        assert e["decision"] == "ALLOW"
        assert len(log.entries()) == 1

    def test_backend_absent_still_records(self):
        log = AuditLogger()
        log.record(_act(), decision="ALLOW")
        assert len(log.entries()) == 1