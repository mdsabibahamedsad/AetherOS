"""Tests for aetheros_security.kill_switch (named kill switches + safe shutdown)."""

import pytest

from aetheros_security.kill_switch import (
    KillSwitch,
    KillSwitchError,
    KillSwitchRegistry,
    get_kill_switch_registry,
    get_safe_shutdown_service,
)


def _reset_global_switches() -> None:
    """Reset the global registry after tests that arm switches (no isolation)."""
    reg = get_kill_switch_registry()
    for switch in KillSwitch:
        try:
            reg.set_switch(switch, False, principal="system", reason="test reset")
        except KillSwitchError:
            pass


class TestKillSwitchRegistry:
    def test_default_off(self):
        reg = KillSwitchRegistry()
        assert not reg.is_active(KillSwitch.DISABLE_TOOL_EXECUTION)
        assert reg.active_switches() == []

    def test_elevated_principal_can_flip(self):
        reg = KillSwitchRegistry()
        assert reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
                              principal="admin", reason="incident")
        assert reg.is_active(KillSwitch.DISABLE_TOOL_EXECUTION)

    def test_system_principal_can_flip(self):
        reg = KillSwitchRegistry()
        assert reg.set_switch_by_name("disable_external_network", True,
                                      principal="system")
        assert reg.is_active_name("disable_external_network")

    def test_unelevated_principal_denied(self):
        reg = KillSwitchRegistry()
        with pytest.raises(KillSwitchError):
            reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
                           principal="agent-1")

    def test_unknown_switch_name(self):
        reg = KillSwitchRegistry()
        with pytest.raises(KillSwitchError):
            reg.set_switch_by_name("not_a_real_switch", True, principal="admin")

    def test_noop_when_unchanged(self):
        reg = KillSwitchRegistry()
        reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True, principal="admin")
        # Turning it on again when already on returns False (no change).
        assert not reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True,
                                  principal="admin")

    def test_status_report(self):
        reg = KillSwitchRegistry()
        reg.set_switch(KillSwitch.DISABLE_AUTONOMOUS_ACTIONS, True,
                       principal="security")
        status = reg.status()
        by_name = {s["switch"]: s for s in status}
        assert by_name["disable_autonomous_actions"]["active"] is True
        assert by_name["disable_autonomous_actions"]["principal"] == "security"

    def test_history(self):
        reg = KillSwitchRegistry()
        reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, True, principal="admin")
        reg.set_switch(KillSwitch.DISABLE_TOOL_EXECUTION, False, principal="admin")
        assert len(reg.history()) >= 2


class TestSafeShutdownService:
    def test_safe_shutdown_activates_switches(self):
        _reset_global_switches()
        service = get_safe_shutdown_service()
        try:
            record = service.run(principal="system", reason="test shutdown")
            assert record["stop_new_privileged_actions"] is True
            assert record["preserve_audit_evidence"] is True
            reg = get_kill_switch_registry()
            assert reg.is_active(KillSwitch.DISABLE_AUTONOMOUS_ACTIONS)
            assert reg.is_active(KillSwitch.DISABLE_TOOL_EXECUTION)
            assert reg.is_active(KillSwitch.DISABLE_AGENT_DELEGATION)
        finally:
            # Undo global side effects so later tests see a clean process.
            _reset_global_switches()
            from aetheros_security.response import get_response_manager
            get_response_manager().recover_from_stop()

    def test_shutdown_does_not_destroy_state(self):
        service = get_safe_shutdown_service()
        record = service.run(principal="system", reason="state-preservation test")
        # No destructive step is ever recorded.
        assert not any("delete" in s for s in record["steps"])
        _reset_global_switches()
        from aetheros_security.response import get_response_manager
        get_response_manager().recover_from_stop()

    def test_shutdowns_recorded(self):
        service = get_safe_shutdown_service()
        before = len(service.shutdowns())
        service.run(principal="system", reason="audit test")
        assert len(service.shutdowns()) == before + 1
        _reset_global_switches()
        from aetheros_security.response import get_response_manager
        get_response_manager().recover_from_stop()