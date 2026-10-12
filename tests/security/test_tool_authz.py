"""Tests for aetheros_security.tool_authz (tool authorization boundary)."""

import pytest

from aetheros_security.tool_authz import (
    ToolAuthOutcome,
    ToolAuthRequest,
    ToolAuthorizationService,
    get_tool_authorization_service,
)


def _service():
    service = ToolAuthorizationService()
    service.register_tool_action("filesystem_read_file", "filesystem:read")
    service.register_tool_action("filesystem_delete", "filesystem:delete")
    return service


class TestParameterValidation:
    def test_rejects_traversal(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": "../../etc/passwd"})
        assert error and "traversal" in error

    def test_rejects_null_byte(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": "notes.txt\x00"})
        assert error

    def test_rejects_unc_path(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": r"\\server\share\file.txt"})
        assert error and "UNC" in error

    def test_rejects_absolute_windows_path(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": "C:\\Windows\\system32"})
        assert error and "absolute" in error

    def test_rejects_encoded_separator(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": "%2fetc%2fpasswd"})
        assert error

    def test_rejects_ntfs_ads(self):
        service = _service()
        error = service.validate_parameters(
            "filesystem_read_file", {"path": "file.txt::$DATA"})
        assert error

    def test_rejects_unsafe_url_scheme(self):
        service = _service()
        error = service.validate_parameters(
            "web_fetch", {"url": "file:///etc/passwd"})
        assert error and "scheme" in error

    def test_rejects_empty_command(self):
        service = _service()
        error = service.validate_parameters("terminal_execute", {"command": "  "})
        assert error

    def test_custom_validator(self):
        service = _service()
        service.register_parameter_validator(
            "filesystem_read_file",
            lambda params: "bad content" if params.get("path") == "bad" else None)
        assert service.validate_parameters("filesystem_read_file",
                                          {"path": "bad"}) == "bad content"
        assert service.validate_parameters("filesystem_read_file",
                                          {"path": "good"}) is None

    def test_non_mapping_parameters(self):
        service = _service()
        assert service.validate_parameters("x", ["not", "a", "dict"])


class TestAuthorizationBoundary:
    def test_unknown_tool_denied_by_manifest_default(self):
        service = _service()
        # Unknown tool -> no manifest -> engine default deny (unknown principal).
        decision = service.check(ToolAuthRequest(
            principal="__unknown__", tool="totally_new_tool",
            action="filesystem:write", resource="/tmp/x"))
        assert decision.outcome == ToolAuthOutcome.DENY

    def test_traversal_blocked_before_authorization(self):
        service = _service()
        decision = service.check(ToolAuthRequest(
            principal="user", tool="filesystem_read_file",
            action="filesystem:read", resource="../../etc/passwd",
            parameters={"path": "../../etc/passwd"}))
        assert decision.outcome == ToolAuthOutcome.DENY
        assert "parameters" in decision.reason

    def test_manifest_deny_blocked(self):
        from aetheros_security.manifest import ToolManifest, get_manifest_registry
        registry = get_manifest_registry()
        # A manifest with no allowed filesystem scopes denies every operation.
        registry.register(ToolManifest(tool_id="blocked_tool"))
        service = _service()
        service.register_tool_action("blocked_tool", "filesystem:delete")
        decision = service.check(ToolAuthRequest(
            principal="user", tool="blocked_tool", action="filesystem:delete",
            resource="/tmp/important", parameters={"path": "/tmp/important"}))
        assert decision.outcome == ToolAuthOutcome.DENY
        assert "manifest" in decision.reason

    def test_kill_switch_blocks_tool_execution(self):
        from aetheros_security.kill_switch import (KillSwitch,
                                                   get_kill_switch_registry)
        reg = get_kill_switch_registry()
        reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
                       principal="admin", reason="test")
        try:
            service = _service()
            decision = service.check(ToolAuthRequest(
                principal="user", tool="filesystem_read_file",
                action="filesystem:read", resource="/tmp/ok",
                parameters={"path": "/tmp/ok"}))
            assert decision.outcome == ToolAuthOutcome.DENY
            assert "kill switch" in decision.reason
        finally:
            reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, False,
                           principal="admin")

    def test_action_for_defaults_to_tool_name(self):
        service = _service()
        assert service.action_for("filesystem_read_file") == "filesystem:read"
        assert service.action_for("unmapped_tool") == "unmapped_tool"

    def test_singleton(self):
        assert get_tool_authorization_service() is get_tool_authorization_service()