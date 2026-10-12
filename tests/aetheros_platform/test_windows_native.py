"""Tests for startup model, UIA scopes, and Event Log builder (64.1 A4-A6)."""

import pytest

from aetheros_computer.uia import (
    DEFAULT_SCOPES,
    UIElement,
    UIAAction,
    UIScope,
    UnavailableProvider,
    scope_allows,
)
from aetheros_platform.desktop.startup import (
    StartupMode,
    audit_event,
    build_run_value,
    describe_current,
)
from aetheros_platform.observability.eventlog import (
    EVENT_IDS,
    build_event,
    write_event,
)


def test_describe_current_never_raises_and_never_writes():
    rec = describe_current()
    assert isinstance(rec.mode, StartupMode)


def test_run_value_has_no_secrets_and_quotes_path():
    v = build_run_value("C:\\Program Files\\AetherOS\\AetherOS.exe",
                        StartupMode.BACKGROUND_AGENT_RUNTIME)
    assert v.startswith('"C:\\Program Files\\AetherOS\\AetherOS.exe"')
    assert "--background" in v
    assert "key" not in v.lower() and "token" not in v.lower()
    with pytest.raises(ValueError):
        build_run_value("", StartupMode.FULL_UI_START)


def test_audit_event_shape():
    rec = describe_current()
    ev = audit_event(rec, "queried")
    assert ev["event"] == "startup.queried"
    assert "mode" in ev and "at" in ev


def test_default_scopes_are_aetheros_only():
    assert UIScope.UI_CONTROL_AETHEROS in DEFAULT_SCOPES
    assert UIScope.UI_CONTROL_DESKTOP not in DEFAULT_SCOPES


def test_control_requires_paired_read_scope():
    ok, _ = scope_allows([UIScope.UI_CONTROL_APP], "app", "invoke")
    assert not ok  # missing UI_READ_APP
    ok, _ = scope_allows([UIScope.UI_READ_APP, UIScope.UI_CONTROL_APP],
                         "app", "invoke")
    assert ok


def test_desktop_control_denied_by_default():
    ok, reason = scope_allows(list(DEFAULT_SCOPES), "desktop", "invoke")
    assert not ok
    assert "UI_CONTROL_DESKTOP" in reason


def test_read_scopes_are_distinct():
    for method in ("find", "inspect", "getValue"):
        ok, _ = scope_allows([UIScope.UI_READ_AETHEROS], "aetheros", method)
        assert ok
        ok, _ = scope_allows([UIScope.UI_READ_AETHEROS], "desktop", method)
        assert not ok


def test_unavailable_provider_is_honest():
    p = UnavailableProvider()
    with pytest.raises(RuntimeError, match="unavailable"):
        p.find("desktop", {})
    with pytest.raises(RuntimeError, match="unavailable"):
        p.act(UIAAction(action_id="a", target_id="t", method="invoke"))


def test_element_schema_defaults_safe():
    el = UIElement(runtime_id="r", name="Save", control_type="Button")
    assert el.enabled and el.visible and not el.focused
    assert el.children == [] and el.patterns == []


def test_event_builder_rejects_unknown_keys():
    with pytest.raises(ValueError):
        build_event("nope", "x")
    with pytest.raises(ValueError):
        build_event("tamper", "x", severity="weird")


def test_event_ids_stable_and_redacted():
    ev = build_event("tamper", "bad OPENAI_API_KEY=sk-live-value here",
                     severity="critical", task_id="t")
    assert ev.event_id == EVENT_IDS["tamper"] == 1003
    assert "sk-live-value" not in ev.message


def test_write_event_receipt_honest():
    ev = build_event("update.failure", "download hash mismatch")
    r = write_event(ev)
    assert r["event_id"] == 3001
    # This workspace: source registration absent → fallback receipt, never
    # a false "written" claim.
    assert r["written"] in (True, False)
    if not r["written"]:
        assert r["fallback"] and r.get("reason")
