"""Tests for Linux platform modules (Master 66). All cross-platform."""

import os

import pytest

from aetheros_computer.atspi import (
    ATScope,
    ATSPIElement,
    DEFAULT_AT_SCOPES,
    at_scope_allows,
)
from aetheros_platform.linux_native import (
    DBusCall,
    MemorySecretBackend,
    SecretError,
    UnavailableSecretBackend,
    expected_portals,
    validate_dbus,
)
from aetheros_platform.linux_paths import (
    detect_legacy,
    hash_file,
    linux_paths,
    plan_migration,
)
from aetheros_platform.linux_session import detect_session


def test_xdg_layout_and_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    p = linux_paths(home=tmp_path)
    assert p.config == tmp_path / "cfg" / "aetheros"
    assert p.runtime == tmp_path / "run" / "aetheros"
    assert p.logs == p.state / "logs"
    assert p.artifacts != p.backups


def test_xdg_defaults_without_env(tmp_path, monkeypatch):
    for v in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
              "XDG_STATE_HOME", "XDG_RUNTIME_DIR"):
        monkeypatch.delenv(v, raising=False)
    p = linux_paths(home=tmp_path)
    assert p.config == tmp_path / ".config" / "aetheros"
    assert p.cache == tmp_path / ".cache" / "aetheros"


def test_legacy_detection_is_readonly(tmp_path):
    leg = tmp_path / ".config" / "hermes"
    leg.mkdir(parents=True)
    (leg / "a.txt").write_text("x")
    found = detect_legacy(home=tmp_path)
    paths = [f["path"] for f in found]
    assert any("hermes" in x for x in paths)
    assert (leg / "a.txt").exists()  # untouched


def test_migration_plan_never_deletes():
    plan = plan_migration([{"path": "/home/u/.hermes", "files": 3}],
                          dest="/home/u/.local/share/aetheros")
    assert "never delete" in plan["mode"]
    assert plan["idempotent"]


def test_hash_file(tmp_path):
    f = tmp_path / "b.bin"
    f.write_bytes(b"abc")
    import hashlib
    assert hash_file(f) == hashlib.sha256(b"abc").hexdigest()


def test_session_wayland_honest():
    s = detect_session(env={"WAYLAND_DISPLAY": "wayland-0",
                            "XDG_CURRENT_DESKTOP": "GNOME"},
                       platform="linux")
    assert s.applicable and s.session_type == "wayland"
    assert s.global_capture == "unsupported"
    assert s.global_input == "unsupported"


def test_session_x11_native():
    s = detect_session(env={"DISPLAY": ":0", "XDG_SESSION_TYPE": "x11"},
                       platform="linux")
    assert s.session_type == "x11"
    assert s.global_capture == "native"


def test_session_non_linux_inapplicable():
    s = detect_session(env={}, platform="win32")
    assert not s.applicable


def test_portal_expectations():
    wl = expected_portals("wayland", "GNOME")
    assert wl["screenshot"].status.value == "SESSION_DEPENDENT"
    headless = expected_portals("headless", "")
    assert all(p.status.value == "UNAVAILABLE" for p in headless.values())


def test_dbus_allowlist():
    ok, _ = validate_dbus(DBusCall("org.freedesktop.Notifications",
                                   "org.freedesktop.Notifications",
                                   "Notify", "/org/freedesktop/Notifications"))
    assert ok
    ok, _ = validate_dbus(DBusCall("org.freedesktop.DBus",
                                   "org.freedesktop.DBus", "ListNames", "/"))
    assert not ok
    ok, _ = validate_dbus(DBusCall("org.freedesktop.Notifications",
                                   "org.freedesktop.Notifications",
                                   "Notify", "/../escape"))
    assert not ok
    ok, _ = validate_dbus(DBusCall("org.freedesktop.Notifications",
                                   "org.freedesktop.Notifications",
                                   "Notify", "/", args=("a;rm -rf /",)))
    assert not ok


def test_secret_backend_contract():
    b = MemorySecretBackend()
    b.set("c", "k", "v")
    assert b.get("c", "k") == "v"
    assert b.delete("c", "k") and not b.delete("c", "k")
    with pytest.raises(SecretError):
        b.set("c", "k", "")
    u = UnavailableSecretBackend()
    with pytest.raises(SecretError):
        u.get("c", "k")


def test_atspi_scopes():
    ok, _ = at_scope_allows([ATScope.AT_CONTROL_APP], "app", "performAction")
    assert not ok
    ok, _ = at_scope_allows([ATScope.AT_READ_APP, ATScope.AT_CONTROL_APP],
                            "app", "performAction")
    assert ok
    ok, r = at_scope_allows(list(DEFAULT_AT_SCOPES), "desktop", "performAction")
    assert not ok and "AT_CONTROL_DESKTOP" in r
    el = ATSPIElement(element_id="e", role="button", name="Save")
    assert el.children == []
