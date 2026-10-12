"""Behavior contracts for the model_tools PEP wiring (Master 12).

The PEP is gated by ``security.control_plane.tool_authorization``:

- gate OFF (default) → dispatch passes through untouched (legacy semantics);
  no identity registry / token manager is ever consulted.
- gate ON → a provisioned context is validated fail-closed
  (inactive principal / invalid session / principal mismatch all deny),
  then the ToolAuthorizationService decision is enforced
  (DENY / APPROVAL_REQUIRED / CHALLENGE short-circuit, ALLOW proceeds).
  An ABSENT context falls through so embedders that never provision
  identities keep working.
"""

import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

import model_tools
from aetheros_security.runtime import (
    SecurityContext,
    clear_security_context,
    get_security_context,
    set_security_context,
)
from aetheros_security.tool_authz import (
    ToolAuthDecision,
    ToolAuthOutcome,
)


@pytest.fixture(autouse=True)
def _isolated_security_context():
    clear_security_context()
    yield
    clear_security_context()


def _enable_gate(monkeypatch):
    monkeypatch.setattr(model_tools, "_tool_authorization_enabled", lambda: True)


def _disable_gate(monkeypatch):
    monkeypatch.setattr(model_tools, "_tool_authorization_enabled", lambda: False)


def _ctx(token="valid-token-format", principal="user:alice"):
    return SecurityContext(
        principal=principal,
        user_id=principal.split(":", 1)[-1],
        agent_id="agent:test",
        session_token=token,
        delegation_depth=0,
        mission="test-mission",
        task="test-task",
        attributes={},
    )


def _active_identity_registry():
    reg = MagicMock()
    reg.is_principal_active.return_value = True
    return reg


def _token_manager(sub="user:alice", error=None):
    mgr = MagicMock()
    if error is not None:
        mgr.validate.side_effect = error
    else:
        payload = MagicMock()
        payload.sub = sub
        mgr.validate.return_value = payload
    return mgr


def _authz_service(decision=None, error=None):
    svc = MagicMock()
    if error is not None:
        svc.check.side_effect = error
    else:
        svc.check.return_value = decision
    return svc


def _decision(outcome, reason="", approval_id=""):
    return ToolAuthDecision(
        outcome=outcome,
        principal="user:alice",
        tool="any_tool",
        action="tool:any_tool",
        reason=reason,
        approval_id=approval_id,
    )


# ---------------------------------------------------------------------------
# Gate-off semantics (default posture)
# ---------------------------------------------------------------------------


def test_gate_off_skips_all_security_evaluation(monkeypatch):
    """Gate off: dispatch errors are tool-level, never security-level."""
    from model_tools import handle_function_call

    _disable_gate(monkeypatch)
    with patch("aetheros_security.identity.get_identity_registry") as mock_reg:
        result = handle_function_call("nonexistent_tool_xyz", {}, task_id="t")

    mock_reg.assert_not_called()
    payload = json.loads(result)
    assert "nonexistent_tool_xyz" in payload["error"]
    assert "Security check failed" not in result


def test_default_gate_is_off():
    """Contract: tool authorization is opt-in until soak-tested."""
    from aetheros_cli.config import DEFAULT_CONFIG

    value = DEFAULT_CONFIG["security"]["control_plane"]["tool_authorization"]
    assert value is False


# ---------------------------------------------------------------------------
# Gate-on semantics
# ---------------------------------------------------------------------------


def test_gate_on_without_context_falls_through(monkeypatch):
    """Absent context under an enabled gate → legacy passthrough."""
    from model_tools import handle_function_call

    assert get_security_context().principal == ""
    _enable_gate(monkeypatch)
    result = handle_function_call("nonexistent_tool_xyz", {}, task_id="t")

    assert "nonexistent_tool_xyz" in json.loads(result)["error"]


def test_gate_on_inactive_principal_denied(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: MagicMock(is_principal_active=MagicMock(return_value=False)),
    )

    result = handle_function_call("any_tool", {}, task_id="t")
    assert json.loads(result)["error"] == "Principal not active or revoked"


def test_gate_on_invalid_session_denied_fail_closed(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx(token="bad-token"))
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(error=Exception("signature invalid")),
    )

    result = handle_function_call("any_tool", {}, task_id="t")
    assert "Invalid or expired session" in json.loads(result)["error"]


def test_gate_on_principal_mismatch_denied(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx(principal="user:alice"))
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(sub="user:mallory"),
    )

    result = handle_function_call("any_tool", {}, task_id="t")
    assert json.loads(result)["error"] == "Session token principal mismatch"


def test_gate_on_allow_proceeds_to_dispatch(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(),
    )
    monkeypatch.setattr(
        "aetheros_security.tool_authz.ToolAuthorizationService",
        lambda: _authz_service(_decision(ToolAuthOutcome.ALLOW)),
    )

    result = handle_function_call("nonexistent_tool_xyz", {}, task_id="t")
    payload = json.loads(result)
    # Past every security gate; failure is the plain unknown-tool error.
    assert "nonexistent_tool_xyz" in payload["error"]
    for forbidden in (
        "Access denied",
        "Approval required",
        "Challenge required",
        "Security check failed",
    ):
        assert forbidden not in result


def test_gate_on_deny_outcome_enforced(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(),
    )
    monkeypatch.setattr(
        "aetheros_security.tool_authz.ToolAuthorizationService",
        lambda: _authz_service(
            _decision(ToolAuthOutcome.DENY, reason="denied by policy")
        ),
    )

    payload = json.loads(handle_function_call("any_tool", {}, task_id="t"))
    assert payload["error_type"] == "authorization_denied"
    assert "denied by policy" in payload["error"]
    assert payload["details"]["outcome"] == "deny"


def test_gate_on_approval_required_outcome_enforced(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(),
    )
    monkeypatch.setattr(
        "aetheros_security.tool_authz.ToolAuthorizationService",
        lambda: _authz_service(
            _decision(ToolAuthOutcome.APPROVAL_REQUIRED, approval_id="approval-123")
        ),
    )

    payload = json.loads(handle_function_call("any_tool", {}, task_id="t"))
    assert payload["error_type"] == "approval_required"
    assert payload["approval_id"] == "approval-123"


def test_gate_on_challenge_outcome_enforced(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(),
    )
    monkeypatch.setattr(
        "aetheros_security.tool_authz.ToolAuthorizationService",
        lambda: _authz_service(_decision(ToolAuthOutcome.CHALLENGE)),
    )

    payload = json.loads(handle_function_call("any_tool", {}, task_id="t"))
    assert payload["error_type"] == "challenge_required"


def test_gate_on_policy_engine_error_fails_closed(monkeypatch):
    from model_tools import handle_function_call

    _enable_gate(monkeypatch)
    set_security_context(_ctx())
    monkeypatch.setattr(
        "aetheros_security.identity.get_identity_registry",
        lambda: _active_identity_registry(),
    )
    monkeypatch.setattr(
        "aetheros_security.tokens.get_token_manager",
        lambda: _token_manager(),
    )
    monkeypatch.setattr(
        "aetheros_security.tool_authz.ToolAuthorizationService",
        lambda: _authz_service(error=RuntimeError("policy store offline")),
    )

    result = handle_function_call("any_tool", {}, task_id="t")
    assert "Security check failed" in json.loads(result)["error"]
