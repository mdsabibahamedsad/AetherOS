"""Tests for the computer_use permission system."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from tools.computer_use.permissions import (
    ACTION_PERMISSIONS,
    ComputerUsePermissions,
    PERMISSION_DESCRIPTIONS,
    Permission,
    PermissionDeniedError,
    get_permissions,
    permission_for_action,
    reset_permissions_for_tests,
)


@pytest.fixture(autouse=True)
def _fresh_permissions():
    reset_permissions_for_tests()
    yield
    reset_permissions_for_tests()


class TestPermissionVocabulary:
    def test_closed_vocabulary(self):
        assert Permission.SCREEN_READ.value == "screen_read"
        assert Permission.MOUSE_CONTROL.value == "mouse_control"
        assert Permission.KEYBOARD_CONTROL.value == "keyboard_control"
        assert Permission.WINDOW_CONTROL.value == "window_control"
        assert Permission.CLIPBOARD_READ.value == "clipboard_read"
        assert Permission.CLIPBOARD_WRITE.value == "clipboard_write"
        assert Permission.APPLICATION_CONTROL.value == "application_control"
        assert Permission.ACCESSIBILITY_CONTROL.value == "accessibility_control"

    def test_every_permission_has_a_description(self):
        for p in Permission:
            assert PERMISSION_DESCRIPTIONS[p], f"missing description for {p}"


class TestActionBinding:
    def test_bindings_are_complete_for_known_actions(self):
        """Every action in the tool schema maps to a permission (invariant)."""
        from tools.computer_use.schema import COMPUTER_USE_SCHEMA
        actions = set(COMPUTER_USE_SCHEMA["parameters"]["properties"]["action"]["enum"])
        unbound = [a for a in actions if permission_for_action(a) is None]
        # `wait` binds to screen_read; ensure nothing is unbound.
        assert unbound == []

    def test_known_bindings(self):
        assert permission_for_action("capture") is Permission.SCREEN_READ
        assert permission_for_action("click") is Permission.MOUSE_CONTROL
        assert permission_for_action("type") is Permission.KEYBOARD_CONTROL
        assert permission_for_action("read_clipboard") is Permission.CLIPBOARD_READ
        assert permission_for_action("copy_clipboard") is Permission.CLIPBOARD_WRITE
        assert permission_for_action("focus_window") is Permission.WINDOW_CONTROL
        assert permission_for_action("focus_app") is Permission.APPLICATION_CONTROL

    def test_unbound_action_is_allowed(self):
        store = ComputerUsePermissions()
        assert store.check("no_such_action").allowed


class TestDefaultPolicy:
    def test_allow_all_by_default(self):
        store = ComputerUsePermissions()
        for p in Permission:
            assert store.is_granted(p)
        assert store.check("capture").allowed
        assert store.check("read_clipboard").allowed

    def test_revoke_denies(self):
        store = ComputerUsePermissions()
        store.revoke(Permission.CLIPBOARD_READ)
        assert not store.is_granted(Permission.CLIPBOARD_READ)
        assert store.check("read_clipboard").allowed is False
        assert store.check("read_clipboard").permission is Permission.CLIPBOARD_READ
        # Unrelated permissions unaffected.
        assert store.is_granted(Permission.MOUSE_CONTROL)

    def test_revoke_then_grant_restores(self):
        store = ComputerUsePermissions()
        store.revoke(Permission.MOUSE_CONTROL)
        assert not store.check("click").allowed
        store.grant(Permission.MOUSE_CONTROL)
        assert store.check("click").allowed


class TestStrictMode:
    def test_strict_denies_ungranted(self):
        store = ComputerUsePermissions(strict=True)
        assert not store.check("capture").allowed
        assert not store.check("read_clipboard").allowed

    def test_strict_allows_granted(self):
        store = ComputerUsePermissions(strict=True)
        store.grant(Permission.SCREEN_READ)
        assert store.check("capture").allowed
        assert not store.check("copy_clipboard").allowed

    def test_granted_reports_effective_set(self):
        store = ComputerUsePermissions(strict=True)
        store.grant(Permission.SCREEN_READ)
        store.grant(Permission.MOUSE_CONTROL)
        assert store.granted() == {Permission.SCREEN_READ, Permission.MOUSE_CONTROL}

    def test_set_strict_runtime_toggle(self):
        store = ComputerUsePermissions()
        store.set_strict(True)
        assert store.check("capture").allowed is False
        store.set_strict(False)
        assert store.check("capture").allowed

    def test_require_raises_on_denied(self):
        store = ComputerUsePermissions(strict=True)
        with pytest.raises(PermissionDeniedError) as exc:
            store.require("capture")
        assert exc.value.permission is Permission.SCREEN_READ

    def test_require_passes_on_granted(self):
        store = ComputerUsePermissions(strict=True)
        store.grant(Permission.SCREEN_READ)
        store.require("capture")  # must not raise


class TestEnvDrivenSingleton:
    def test_strict_from_env(self):
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "1"}, clear=False):
            reset_permissions_for_tests()
            assert get_permissions().strict_mode is True
        with patch.dict(os.environ, {"AETHEROS_COMPUTER_USE_STRICT": "0"}, clear=False):
            reset_permissions_for_tests()
            assert get_permissions().strict_mode is False

    def test_singleton_is_shared(self):
        assert get_permissions() is get_permissions()

    def test_reset_rebuilds(self):
        store = get_permissions()
        reset_permissions_for_tests()
        assert get_permissions() is not store
