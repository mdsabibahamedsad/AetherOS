"""Integration tests for the extended computer_use actions (noop backend).

Covers the dispatch wiring for the new action surface (get_screen_size,
move_mouse, clipboard, window management, capture_region, find_text), the
permission gate in strict mode, and the audit trail.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

import tools.computer_use.audit as cu_audit
import tools.computer_use.permissions as cu_perms
from tools.computer_use import tool as cu_tool


@pytest.fixture(autouse=True)
def _reset_all():
    cu_tool.reset_backend_for_tests()
    cu_perms.reset_permissions_for_tests()
    cu_audit.reset_audit_for_tests()
    with patch.dict(os.environ, {"HERMES_COMPUTER_USE_BACKEND": "noop"}, clear=False):
        yield
    cu_tool.reset_backend_for_tests()
    cu_perms.reset_permissions_for_tests()
    cu_audit.reset_audit_for_tests()


@pytest.fixture
def noop_backend():
    return cu_tool._get_backend()


def _call(args):
    out = cu_tool.handle_computer_use(args)
    assert isinstance(out, str)
    return json.loads(out)


# ---------------------------------------------------------------------------
# Extended-action dispatch
# ---------------------------------------------------------------------------

class TestExtendedDispatch:
    def test_get_screen_size(self, noop_backend):
        payload = _call({"action": "get_screen_size"})
        assert payload == {"width": 1920, "height": 1080}
        assert ("get_screen_size", {}) in noop_backend.calls

    def test_list_windows(self, noop_backend):
        payload = _call({"action": "list_windows"})
        assert payload == {"windows": [], "count": 0}
        assert ("list_windows", {}) in noop_backend.calls

    def test_get_active_window(self, noop_backend):
        payload = _call({"action": "get_active_window"})
        assert payload == {"window": {}}
        assert ("get_active_window", {}) in noop_backend.calls

    def test_move_mouse(self, noop_backend):
        payload = _call({"action": "move_mouse", "coordinate": [10, 20]})
        assert payload["ok"] is True
        assert ("move_mouse", {"x": 10, "y": 20}) in noop_backend.calls

    def test_move_mouse_requires_coordinate(self):
        payload = _call({"action": "move_mouse"})
        assert "error" in payload

    def test_read_clipboard(self, noop_backend):
        payload = _call({"action": "read_clipboard"})
        assert payload["ok"] is True
        assert payload["meta"]["text"] == "noop"
        assert ("read_clipboard", {}) in noop_backend.calls

    def test_copy_clipboard(self, noop_backend):
        payload = _call({"action": "copy_clipboard", "text": "hello"})
        assert payload["ok"] is True
        assert ("copy_clipboard", {"text": "hello"}) in noop_backend.calls

    def test_copy_clipboard_requires_text(self):
        payload = _call({"action": "copy_clipboard"})
        assert "error" in payload

    def test_clear_clipboard(self, noop_backend):
        assert _call({"action": "clear_clipboard"})["ok"] is True

    def test_focus_window(self, noop_backend):
        payload = _call({"action": "focus_window", "window_title": "Notes"})
        assert payload["ok"] is True
        assert ("focus_window", {"identifier": None, "title": "Notes", "pid": None}) \
            in noop_backend.calls

    def test_minimize_maximize_close_window(self, noop_backend):
        assert _call({"action": "minimize_window", "window_id": "0x1"})["ok"] is True
        assert _call({"action": "maximize_window", "window_title": "Notes"})["ok"] is True
        assert _call({"action": "close_window", "window_id": "0x2"})["ok"] is True
        names = [c[0] for c in noop_backend.calls]
        assert "minimize_window" in names
        assert "maximize_window" in names
        assert "close_window" in names

    def test_capture_region(self, noop_backend):
        payload = _call({"action": "capture_region",
                         "x": 0, "y": 0, "width": 320, "height": 240})
        assert payload["width"] == 320
        assert payload["height"] == 240
        assert ("capture_region", {"x": 0, "y": 0, "width": 320,
                                   "height": 240, "mode": "vision"}) in noop_backend.calls

    def test_capture_region_requires_geometry(self):
        payload = _call({"action": "capture_region", "x": 0})
        assert "error" in payload

    def test_find_text(self, noop_backend):
        payload = _call({"action": "find_text", "text": "Save"})
        assert payload == {"matches": [], "count": 0}
        assert ("find_text", {"text": "Save", "app": None}) in noop_backend.calls

    def test_find_text_requires_text(self):
        payload = _call({"action": "find_text"})
        assert "error" in payload


# ---------------------------------------------------------------------------
# Read-only vs destructive classification
# ---------------------------------------------------------------------------

class TestActionClassification:
    def test_read_only_actions_not_destructive(self):
        for action in ("capture", "capture_region", "get_screen_size",
                       "list_windows", "get_active_window", "read_clipboard",
                       "find_text", "list_apps", "wait"):
            assert action not in cu_tool._DESTRUCTIVE_ACTIONS, action

    def test_mutating_actions_are_destructive(self):
        for action in ("move_mouse", "copy_clipboard", "clear_clipboard",
                       "focus_window", "minimize_window", "maximize_window",
                       "close_window"):
            assert action in cu_tool._DESTRUCTIVE_ACTIONS, action

    def test_every_destructive_action_is_bound_to_a_permission(self):
        for action in cu_tool._DESTRUCTIVE_ACTIONS:
            assert cu_perms.permission_for_action(action) is not None, action


# ---------------------------------------------------------------------------
# Permission gate
# ---------------------------------------------------------------------------

class TestPermissionGate:
    def test_strict_mode_denies_ungranted_action(self, noop_backend):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            cu_perms.reset_permissions_for_tests()
            payload = _call({"action": "capture"})
        assert "error" in payload
        assert "requires" in payload["error"]
        # The denial is itself audited.
        entries = cu_audit.get_audit_log().entries()
        assert entries and entries[-1]["allowed"] is False
        # Nothing was dispatched.
        assert noop_backend.calls == []

    def test_strict_mode_allows_after_grant(self, noop_backend):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            cu_perms.reset_permissions_for_tests()
            cu_perms.get_permissions().grant(cu_perms.Permission.SCREEN_READ)
            payload = _call({"action": "get_screen_size"})
        assert payload["width"] == 1920

    def test_default_mode_allows(self, noop_backend):
        payload = _call({"action": "get_screen_size"})
        assert payload["width"] == 1920


# ---------------------------------------------------------------------------
# Audit integration
# ---------------------------------------------------------------------------

class TestAuditIntegration:
    def test_successful_dispatch_is_audited(self, noop_backend):
        _call({"action": "get_screen_size"})
        entries = cu_audit.get_audit_log().entries()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["action"] == "get_screen_size"
        assert entry["allowed"] is True
        assert entry["ok"] is True
        assert entry["backend"] == "_NoopBackend"
        assert "elapsed_ms" in entry

    def test_failed_action_is_audited_as_not_ok(self, noop_backend):
        _call({"action": "does_not_exist"})
        entries = cu_audit.get_audit_log().entries()
        assert entries and entries[-1]["ok"] is False

    def test_validation_failure_before_dispatch_is_audited(self, noop_backend):
        """Bad args return an error before the backend runs, but still audit."""
        _call({"action": "move_mouse"})
        entries = cu_audit.get_audit_log().entries()
        assert entries and entries[-1]["ok"] is False

    def test_audit_never_contains_clipboard_text(self, noop_backend):
        _call({"action": "copy_clipboard", "text": "super-secret-value"})
        dumped = json.dumps(cu_audit.get_audit_log().entries())
        assert "super-secret-value" not in dumped
        assert "text" not in dumped  # no payload text key survives

    def test_audit_summary_masks_clipboard_length_only(self, noop_backend):
        _call({"action": "copy_clipboard", "text": "x" * 50})
        entries = cu_audit.get_audit_log().entries()
        assert "copy_clipboard (50 chars)" in entries[-1]["summary"]


# ---------------------------------------------------------------------------
# Bounded retry on transient action failure
# ---------------------------------------------------------------------------

class _FlakyBackend(cu_tool._NoopBackend):
    """Noop backend that fails a chosen action the first N times."""

    def __init__(self, fail_action: str, failures: int = 1):
        super().__init__()
        self.fail_action = fail_action
        self.failures = failures
        self.attempts = 0

    def _maybe_fail(self, name: str) -> object:
        self.attempts += 1
        if self.fail_action == name and self.attempts <= self.failures:
            return cu_tool.ActionResult(ok=False, action=name, message="transient failure")
        return None

    def move_mouse(self, x: int, y: int) -> object:
        self.calls.append(("move_mouse", {"x": x, "y": y}))
        failed = self._maybe_fail("move_mouse")
        if failed is not None:
            return failed
        return cu_tool.ActionResult(ok=True, action="move_mouse")

    def read_clipboard(self) -> object:
        self.calls.append(("read_clipboard", {}))
        failed = self._maybe_fail("read_clipboard")
        if failed is not None:
            return failed
        return cu_tool.ActionResult(ok=True, action="read_clipboard",
                                    meta={"length": 4, "text": "noop"})


class TestBoundedRetry:
    def test_retries_once_after_transient_failure(self, monkeypatch):
        backend = _FlakyBackend("move_mouse", failures=1)
        monkeypatch.setattr(cu_tool, "_get_backend", lambda: backend)
        payload = _call({"action": "move_mouse", "coordinate": [10, 20]})
        assert payload["ok"] is True
        # First attempt failed, second succeeded.
        assert backend.attempts == 2
        # The retried action is audited once, reflecting the final outcome.
        entries = cu_audit.get_audit_log().entries()
        assert entries and entries[-1]["action"] == "move_mouse"
        assert entries[-1]["ok"] is True

    def test_gives_up_after_single_bounded_retry(self, monkeypatch):
        backend = _FlakyBackend("move_mouse", failures=99)
        monkeypatch.setattr(cu_tool, "_get_backend", lambda: backend)
        payload = _call({"action": "move_mouse", "coordinate": [10, 20]})
        assert payload["ok"] is False
        # Initial attempt + one bounded retry, no infinite loop.
        assert backend.attempts == 2
        entries = cu_audit.get_audit_log().entries()
        assert entries and entries[-1]["ok"] is False

    def test_read_only_actions_never_retry(self, monkeypatch):
        backend = _FlakyBackend("read_clipboard", failures=99)
        monkeypatch.setattr(cu_tool, "_get_backend", lambda: backend)
        payload = _call({"action": "read_clipboard"})
        assert payload["ok"] is False
        assert backend.attempts == 1

    def test_validation_errors_never_retry(self, monkeypatch):
        backend = _FlakyBackend("move_mouse", failures=99)
        monkeypatch.setattr(cu_tool, "_get_backend", lambda: backend)
        payload = _call({"action": "move_mouse"})  # missing coordinate
        assert "error" in payload
        assert backend.attempts == 0  # never reached the backend


# ---------------------------------------------------------------------------
# Schema parity with the new action surface
# ---------------------------------------------------------------------------

class TestSchema:
    def test_schema_enumerates_extended_actions(self):
        from tools.computer_use.schema import COMPUTER_USE_SCHEMA
        actions = set(COMPUTER_USE_SCHEMA["parameters"]["properties"]["action"]["enum"])
        for action in ("get_screen_size", "move_mouse", "read_clipboard",
                       "copy_clipboard", "clear_clipboard", "list_windows",
                       "get_active_window", "focus_window", "minimize_window",
                       "maximize_window", "close_window", "capture_region",
                       "find_text"):
            assert action in actions, action

    def test_schema_documents_window_and_region_params(self):
        from tools.computer_use.schema import COMPUTER_USE_SCHEMA
        props = COMPUTER_USE_SCHEMA["parameters"]["properties"]
        for param in ("window_id", "window_title", "pid", "x", "y", "width", "height"):
            assert param in props, param

    def test_schema_is_platform_universal(self):
        """The schema must not hard-code any one platform's native format."""
        from tools.computer_use.schema import COMPUTER_USE_SCHEMA
        assert COMPUTER_USE_SCHEMA["name"] == "computer_use"
        assert "computer_20251124" not in json.dumps(COMPUTER_USE_SCHEMA)
