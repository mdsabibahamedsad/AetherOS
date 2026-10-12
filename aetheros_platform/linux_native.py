"""Linux portal + D-Bus + secret-service models (Master 66).

Portals: availability is session-dependent (Wayland/GNOME/KDE expose
more than headless/XFCE). This module models expectations + validates
portal call shapes; live portal I/O needs a Linux desktop (BLOCKED).
D-Bus: strict allowlist — service/interface/method + arg validation;
arbitrary calls rejected. Secrets: Secret Service abstraction with
no-plaintext rule (mirrors macOS Keychain contract).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum


class PortalStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    SESSION_DEPENDENT = "SESSION_DEPENDENT"


@dataclass(frozen=True)
class Portal:
    id: str  # fileChooser|openUri|screenshot|screenCast|remoteDesktop|notification
    status: PortalStatus
    reason: str = ""


def expected_portals(session_type: str, desktop: str) -> dict[str, Portal]:
    """Heuristic expectations (honest baseline; live probing on-device)."""
    d = desktop.lower()
    modern = any(k in d for k in ("gnome", "kde", "plasma"))
    out: dict[str, Portal] = {}
    for pid in ("fileChooser", "openUri", "screenshot", "screenCast",
                "remoteDesktop", "notification"):
        if session_type == "headless":
            out[pid] = Portal(pid, PortalStatus.UNAVAILABLE, "no display session")
        elif session_type == "wayland" and modern:
            out[pid] = Portal(pid, PortalStatus.SESSION_DEPENDENT,
                              "probe org.freedesktop.portal.* on-device")
        elif session_type == "x11":
            out[pid] = Portal(pid, PortalStatus.SESSION_DEPENDENT,
                              "native paths preferred on X11; portals optional")
        else:
            out[pid] = Portal(pid, PortalStatus.UNAVAILABLE, "unknown session")
    return out


#: Allowed D-Bus surface. Everything else is rejected.
DBUS_ALLOWLIST = {
    "org.freedesktop.portal.Desktop": {"org.freedesktop.portal.Screenshot",
                                       "org.freedesktop.portal.FileChooser",
                                       "org.freedesktop.portal.OpenURI",
                                       "org.freedesktop.portal.Notification"},
    "org.freedesktop.Notifications": {"org.freedesktop.Notifications"},
    "org.freedesktop.secrets": {"org.freedesktop.Secret.Service"},
}

_OBJECT_PATH_RE = re.compile(r"^/[A-Za-z0-9_]+(/[A-Za-z0-9_]+)*$")


@dataclass
class DBusCall:
    service: str
    interface: str
    method: str
    object_path: str = "/"
    args: tuple = ()


def validate_dbus(call: DBusCall) -> tuple[bool, str]:
    if call.service not in DBUS_ALLOWLIST:
        return False, f"service not allowlisted: {call.service}"
    if call.interface not in DBUS_ALLOWLIST[call.service]:
        return False, f"interface not allowlisted: {call.interface}"
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", call.method):
        return False, f"bad method name: {call.method}"
    if not _OBJECT_PATH_RE.match(call.object_path):
        return False, f"bad object path: {call.object_path}"
    for a in call.args:
        if isinstance(a, str) and (";" in a or "`" in a or "$(" in a):
            return False, "shell metacharacters in args"
    return True, "allowlisted"


class SecretError(Exception):
    pass


class SecretBackend:
    def set(self, collection: str, label: str, secret: str) -> None:
        raise NotImplementedError

    def get(self, collection: str, label: str) -> str:
        raise NotImplementedError

    def delete(self, collection: str, label: str) -> bool:
        raise NotImplementedError


class UnavailableSecretBackend(SecretBackend):
    def __init__(self, reason: str = "no Secret Service on this host"):
        self.reason = reason

    def set(self, collection: str, label: str, secret: str) -> None:
        raise SecretError(self.reason)

    def get(self, collection: str, label: str) -> str:
        raise SecretError(self.reason)

    def delete(self, collection: str, label: str) -> bool:
        raise SecretError(self.reason)


class MemorySecretBackend(SecretBackend):
    """Test-only. Production uses Secret Service; never plaintext files."""

    def __init__(self) -> None:
        self._d: dict[tuple[str, str], str] = {}

    def set(self, collection: str, label: str, secret: str) -> None:
        if not collection or not label:
            raise SecretError("collection and label required")
        if not secret:
            raise SecretError("refusing empty secret")
        self._d[(collection, label)] = secret

    def get(self, collection: str, label: str) -> str:
        try:
            return self._d[(collection, label)]
        except KeyError:
            raise SecretError("no such secret")

    def delete(self, collection: str, label: str) -> bool:
        return self._d.pop((collection, label), None) is not None
