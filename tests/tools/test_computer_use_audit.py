"""Tests for the computer_use audit log."""

from __future__ import annotations

import json
import os

import pytest

from tools.computer_use.audit import (
    ComputerUseAuditLog,
    _REDACTED,
    get_audit_log,
    reset_audit_for_tests,
)


@pytest.fixture(autouse=True)
def _fresh_audit(tmp_path):
    reset_audit_for_tests()
    # The default path already resolves under the per-test $AETHEROS_HOME
    # (conftest), so file-writing tests are safe without patching
    # `_default_path` — and patching it here would defeat
    # `test_default_path_is_profile_aware`, which asserts the real layout.
    yield
    reset_audit_for_tests()


class TestAuditLog:
    def test_record_appends_memory_entry(self):
        log = ComputerUseAuditLog()
        log.record(action="click", allowed=True, ok=True, permission="mouse_control",
                   summary="click element #3")
        entries = log.entries()
        assert len(entries) == 1
        assert entries[0]["action"] == "click"
        assert entries[0]["allowed"] is True
        assert entries[0]["ok"] is True
        assert entries[0]["permission"] == "mouse_control"

    def test_record_redacts_sensitive_meta(self):
        log = ComputerUseAuditLog()
        log.record(action="type", allowed=True,
                   meta={"element": 7, "text": "my-secret-password", "nested": {"value": "x"}})
        meta = log.entries()[0]["meta"]
        assert meta["element"] == 7
        assert meta["text"] == _REDACTED
        assert meta["nested"]["value"] == _REDACTED

    def test_record_never_logs_clipboard_payloads(self):
        log = ComputerUseAuditLog()
        log.record(action="copy_clipboard", allowed=True,
                   meta={"clipboard": "top-secret", "text": "top-secret"})
        meta = log.entries()[0]["meta"]
        assert meta["clipboard"] == _REDACTED
        assert meta["text"] == _REDACTED

    def test_writes_jsonl_file(self):
        log = ComputerUseAuditLog()
        log.record(action="list_windows", allowed=True)
        assert log._path is not None
        lines = open(log._path, encoding="utf-8").read().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["action"] == "list_windows"

    def test_disabled_log_records_nothing(self):
        log = ComputerUseAuditLog(enabled=False)
        log.record(action="click", allowed=True)
        assert log.entries() == []
        assert log.enabled is False

    def test_clear_empties_memory_and_file(self):
        log = ComputerUseAuditLog()
        log.record(action="click", allowed=True)
        log.clear()
        assert log.entries() == []
        if log._path and os.path.exists(log._path):
            assert open(log._path, encoding="utf-8").read() == ""

    def test_default_path_is_profile_aware(self):
        log = ComputerUseAuditLog()
        if log._path:
            assert "logs" in log._path
            assert "computer_use_audit.jsonl" in log._path

    def test_record_never_raises_with_bad_meta(self):
        log = ComputerUseAuditLog()
        log.record(action="click", allowed=True, meta={"weird": object()})
        assert len(log.entries()) == 1


class TestAuditSingleton:
    def test_singleton_is_shared(self):
        assert get_audit_log() is get_audit_log()

    def test_reset_rebuilds(self):
        log = get_audit_log()
        reset_audit_for_tests()
        assert get_audit_log() is not log
