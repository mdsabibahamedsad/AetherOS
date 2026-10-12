"""Dispatch tests for the app-launch / capability actions (noop backend).

Covers the four new actions: get_capabilities, system_info, launch_app,
close_app — plus the permission gate in strict mode.
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
# Capability introspection
# ---------------------------------------------------------------------------

class TestCapabilityActions:
    def test_get_capabilities(self, noop_backend):
        payload = _call({"action": "get_capabilities"})
        assert isinstance(payload, dict)
        assert "capabilities" in payload
        caps = payload["capabilities"]
        assert isinstance(caps, dict)
        assert "platform" in caps
        assert isinstance(caps["actions"], list)
        assert "launch_app" in caps["actions"]
        assert ("get_capabilities", {}) in noop_backend.calls

    def test_system_info(self, noop_backend):
        payload = _call({"action": "system_info"})
        assert isinstance(payload, dict)
        assert payload["system"]["os"] == "noop"
        assert "architecture" in payload["system"]
        assert ("get_system_info", {}) in noop_backend.calls


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

class TestAppLifecycleActions:
    def test_launch_app(self, noop_backend):
        payload = _call({"action": "launch_app", "app": "notepad"})
        assert payload["ok"] is True
        assert payload["meta"]["pid"] == 4242
        assert ("launch_app", {"app": "notepad", "path": None}) in noop_backend.calls

    def test_launch_app_requires_app(self):
        payload = _call({"action": "launch_app"})
        assert "error" in payload
        assert "requires" in payload["error"]

    def test_launch_app_with_path(self, noop_backend):
        payload = _call({"action": "launch_app", "app": "code", "path": r"C:\code"})
        assert payload["ok"] is True
        assert ("launch_app", {"app": "code", "path": r"C:\code"}) in noop_backend.calls

    def test_close_app(self, noop_backend):
        payload = _call({"action": "close_app", "app": "notepad"})
        assert payload["ok"] is True
        assert ("close_app", {"app": "notepad", "pid": None}) in noop_backend.calls

    def test_close_app_requires_app(self):
        payload = _call({"action": "close_app"})
        assert "error" in payload
        assert "requires" in payload["error"]


# ---------------------------------------------------------------------------
# Strict-mode permission gates
# ---------------------------------------------------------------------------

class TestStrictPermissions:
    def test_system_info_denied_in_strict(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            payload = _call({"action": "system_info"})
        assert "error" in payload
        assert "requires" in payload["error"]

    def test_get_capabilities_denied_in_strict(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            payload = _call({"action": "get_capabilities"})
        assert "error" in payload

    def test_launch_app_denied_in_strict(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            payload = _call({"action": "launch_app", "app": "notepad"})
        assert "error" in payload

    def test_launch_app_allowed_when_permission_granted(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            cu_perms.get_permissions().grant(cu_perms.Permission.APPLICATION_CONTROL)
            payload = _call({"action": "launch_app", "app": "notepad"})
        assert payload["ok"] is True

    def test_close_app_denied_in_strict(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            payload = _call({"action": "close_app", "app": "notepad"})
        assert "error" in payload