"""Tests for toast action validation (Master 64.1 A2).

Notification payloads are untrusted: approval must re-verify live state.
"""

import time

from aetheros_platform.desktop.notifications import (
    ToastActionRequest,
    validate_toast_action,
)

NOW = 1_700_000_000.0
LIVE = {"status": "awaiting_approval", "capability": "agent.task.submit"}


def _req(**kw):
    base = dict(action_id="approve", task_id="t-1", agent_id="a-1",
                user_id="u-1", expires_at=NOW + 300,
                capability="agent.task.submit")
    base.update(kw)
    return ToastActionRequest(**base)


def test_valid_approval_passes():
    d = validate_toast_action(_req(), now=NOW, task_state=dict(LIVE),
                              is_authorized=True)
    assert d.allowed


def test_unknown_action_rejected():
    d = validate_toast_action(_req(action_id="format-drive"), now=NOW,
                              task_state=dict(LIVE), is_authorized=True)
    assert not d.allowed


def test_navigation_actions_need_no_task():
    for a in ("open", "view", "dismiss"):
        d = validate_toast_action(ToastActionRequest(action_id=a), now=NOW)
        assert d.allowed, a


def test_expired_action_rejected():
    d = validate_toast_action(_req(expires_at=NOW - 1), now=NOW,
                              task_state=dict(LIVE), is_authorized=True)
    assert not d.allowed


def test_missing_task_rejected():
    d = validate_toast_action(_req(), now=NOW, task_state=None,
                              is_authorized=True)
    assert not d.allowed


def test_already_resolved_task_rejected():
    d = validate_toast_action(_req(), now=NOW,
                              task_state={"status": "completed",
                                          "capability": "agent.task.submit"},
                              is_authorized=True)
    assert not d.allowed


def test_capability_mismatch_requires_reapproval():
    d = validate_toast_action(_req(capability="admin.wipe"), now=NOW,
                              task_state=dict(LIVE), is_authorized=True)
    assert not d.allowed


def test_unauthorized_caller_rejected():
    d = validate_toast_action(_req(), now=NOW, task_state=dict(LIVE),
                              is_authorized=False)
    assert not d.allowed


def test_policy_revocation_blocks():
    d = validate_toast_action(_req(), now=NOW, task_state=dict(LIVE),
                              is_authorized=True, policy_permits=False)
    assert not d.allowed


def test_stop_retry_require_task_binding():
    d = validate_toast_action(ToastActionRequest(action_id="stop"), now=NOW,
                              task_state=dict(LIVE), is_authorized=True)
    assert not d.allowed  # no task_id
    assert "task_id" in d.reasons[0]
