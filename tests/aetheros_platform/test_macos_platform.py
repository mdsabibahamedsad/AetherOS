"""Tests for macOS platform modules (Master 65).

All cross-platform: path logic, TCC policy, AX scopes, Keychain
contract, entitlements audit. Live macOS behavior is BLOCKED, so tests
assert structure, policy, and honesty — never hardware outcomes.
"""

import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from aetheros_computer.ax import (
    AXAction,
    AXElement,
    AXScope,
    DEFAULT_AX_SCOPES,
    ax_scope_allows,
)
from aetheros_platform.macos_keychain import (
    KeychainItem,
    MemoryBackend,
    PlaintextFallbackForbidden,
    UnavailableBackend,
    KeychainError,
    require_keychain_or_fail,
)
from aetheros_platform.macos_paths import macos_paths, secrets_may_live_here
from aetheros_platform.macos_tcc import (
    TCCState,
    default_capabilities,
    degraded_message,
    should_request,
)


def test_macos_paths_follow_library_conventions(tmp_path):
    p = macos_paths(home=tmp_path)
    assert p.cache.parts[-2:] == ("Caches", "AetherOS")
    assert p.logs.parts[-2:] == ("Logs", "AetherOS")
    assert p.config.parts[-2:] == ("Application Support", "AetherOS")
    assert p.artifacts != p.backups != p.data
    assert not secrets_may_live_here("cache")
    assert not secrets_may_live_here("logs")
    assert secrets_may_live_here("config")


def test_tcc_defaults_claim_nothing():
    caps = default_capabilities()
    assert set(caps) >= {"accessibility", "screenRecording", "microphone",
                         "camera", "automation", "filesFolders", "fullDisk"}
    for cap in caps.values():
        assert cap.state == TCCState.NOT_DETERMINED
        assert cap.why_needed and cap.settings_anchor


def test_tcc_request_policy_no_spam():
    caps = default_capabilities()
    assert should_request(caps["camera"], feature_invoked=True)
    assert not should_request(caps["camera"], feature_invoked=False)
    caps["camera"].state = TCCState.DENIED
    assert not should_request(caps["camera"], feature_invoked=True)
    assert "System Settings" in degraded_message(caps["camera"])


def test_ax_control_needs_paired_scope():
    ok, _ = ax_scope_allows([AXScope.AX_CONTROL_APP], "app", "press")
    assert not ok
    ok, _ = ax_scope_allows([AXScope.AX_READ_APP, AXScope.AX_CONTROL_APP],
                            "app", "press")
    assert ok
    ok, reason = ax_scope_allows(list(DEFAULT_AX_SCOPES), "desktop", "press")
    assert not ok and "AX_CONTROL_DESKTOP" in reason
    ok, _ = ax_scope_allows(list(DEFAULT_AX_SCOPES), "aetheros", "readValue")
    assert ok


def test_ax_unknown_method_or_target_rejected():
    ok, _ = ax_scope_allows(list(DEFAULT_AX_SCOPES), "aetheros", "click-pixel")
    assert not ok
    ok, _ = ax_scope_allows(list(DEFAULT_AX_SCOPES), "mars", "press")
    assert not ok


def test_ax_element_schema():
    el = AXElement(identifier="a", role="AXButton", title="Save")
    assert el.enabled and not el.focused and el.children == []


def test_keychain_round_trip_and_rotation():
    b = MemoryBackend()
    b.store(KeychainItem(service="s", account="a"), "v1")
    assert b.read("s", "a") == "v1"
    b.store(KeychainItem(service="s", account="a"), "v2")
    assert b.read("s", "a") == "v2"
    assert b.delete("s", "a") and not b.delete("s", "a")
    with pytest.raises(KeychainError):
        b.read("s", "a")


def test_keychain_rejects_bad_items_and_empties():
    b = MemoryBackend()
    with pytest.raises(KeychainError):
        b.store(KeychainItem(service="", account="a"), "x")
    with pytest.raises(KeychainError):
        b.store(KeychainItem(service="s", account="a", access="world"), "x")
    with pytest.raises(KeychainError):
        b.store(KeychainItem(service="s", account="a"), "")


def test_no_plaintext_fallback():
    with pytest.raises(PlaintextFallbackForbidden):
        require_keychain_or_fail(None)
    u = UnavailableBackend()
    with pytest.raises(KeychainError):
        u.read("s", "a")


def test_entitlements_audit_passes_live():
    repo = Path(__file__).resolve().parent.parent.parent
    r = subprocess.run([sys.executable, "scripts/macos_entitlements_audit.py"],
                       capture_output=True, text=True, cwd=repo, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


def test_entitlements_files_have_no_get_task_allow():
    repo = Path(__file__).resolve().parent.parent.parent
    for name in ("entitlements.mac.plist", "entitlements.mac.inherit.plist"):
        with open(repo / "apps/desktop/electron" / name, "rb") as fh:
            data = plistlib.load(fh)
        assert data.get("com.apple.security.get-task-allow") is not True
