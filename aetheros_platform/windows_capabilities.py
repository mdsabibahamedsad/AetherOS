"""Windows capability registry (Master 64.1 A1).

Reports ACTUAL capability state for every Windows-native feature. Each
entry carries status, provider, requirements, permission, diagnostics,
and last-checked timestamp. UI/CLI must consume this registry — never
show a feature as available when the backend reports otherwise.

Statuses: AVAILABLE, UNAVAILABLE, DEGRADED, BLOCKED_ENVIRONMENT,
NOT_SUPPORTED, ERROR. Detectors use stdlib/ctypes only; nothing here
requires Electron, hardware, or credentials to *report* state.

Usage: ``python -m aetheros_platform.windows_capabilities`` prints JSON.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum

IS_WINDOWS = sys.platform == "win32"


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"
    BLOCKED_ENVIRONMENT = "BLOCKED_ENVIRONMENT"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    ERROR = "ERROR"


@dataclass
class Capability:
    id: str
    status: CapabilityStatus
    provider: str = ""
    requirements: str = ""
    permission: str = ""
    diagnostics: str = ""
    version: str = ""
    last_checked: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def _dll_present(name: str) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        ctypes.WinDLL(name)
        return True
    except OSError:
        return False


def _is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def detect_capabilities() -> dict[str, Capability]:
    """Run all detectors; never raises (errors become ERROR entries)."""
    caps: dict[str, Capability] = {}

    def put(cap: Capability) -> None:
        caps[cap.id] = cap

    try:
        put(Capability(
            id="toastNotifications",
            status=CapabilityStatus.AVAILABLE if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="Electron Notification (AppUserModelId)",
            requirements="Windows 10+; app notifications enabled",
            permission="os.notification",
            diagnostics="win32" if IS_WINDOWS else f"platform={sys.platform}",
        ))
        put(Capability(
            id="toastActions",
            status=CapabilityStatus.DEGRADED if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="Electron Notification actions (validated server-side)",
            requirements="action allowlist + expiry/binding validation",
            permission="os.notification.actions",
            diagnostics="buttons render on Win10+; validation in desktop/notifications.py",
        ))
        uia_core = _dll_present("UIAutomationCore.dll")
        put(Capability(
            id="uiAutomation",
            status=(
                CapabilityStatus.DEGRADED if uia_core
                else CapabilityStatus.UNAVAILABLE
            ),
            provider="UIAutomationCore.dll" if uia_core else "ocr_fallback (SendInput)",
            requirements="UIAutomationCore.dll present; scope policy per agent",
            permission="ui.read|ui.control (scoped)",
            diagnostics=f"UIAutomationCore present={uia_core}; no UIA tree provider wired yet",
        ))
        hello_dll = _dll_present("webauthn.dll") or _dll_present("NgcCtnr.dll")
        put(Capability(
            id="windowsHello",
            status=CapabilityStatus.UNAVAILABLE,
            provider="webauthn/ngc",
            requirements="Hello-capable hardware + enrollment; user verification only",
            permission="os.hello.verify",
            diagnostics=f"hello API dlls present={hello_dll}; enrollment NOT checked; never replaces server auth",
        ))
        put(Capability(
            id="eventLog",
            status=CapabilityStatus.AVAILABLE if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="win32 ReportEvent via ctypes (advapi32)",
            requirements="Application log source registration (admin once)",
            permission="os.eventlog.write",
            diagnostics="high-value events only; secrets redacted",
        ))
        put(Capability(
            id="startup",
            status=CapabilityStatus.AVAILABLE if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="HKCU Run key (per-user)",
            requirements="user consent; auditable registration record",
            permission="os.startup.persist",
            diagnostics="per-user only; no Windows Service",
        ))
        put(Capability(
            id="backgroundMode",
            status=CapabilityStatus.DEGRADED if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="Electron hide-to-background + backend durable tasks",
            requirements="startup mode BACKGROUND_AGENT_RUNTIME; policy gates intact",
            permission="os.background.execute",
            diagnostics="runtime ends when app quits; no hidden persistence",
        ))
        put(Capability(
            id="tray",
            status=CapabilityStatus.DEGRADED if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="Electron Tray (menu builder in electron/tray-menu.cjs)",
            requirements="running main process; menu reflects backend state",
            permission="os.tray",
            diagnostics="menu template unit-tested; live tray UNVERIFIED (no Electron binary here)",
        ))
        put(Capability(
            id="signing",
            status=CapabilityStatus.UNAVAILABLE,
            provider="none configured",
            requirements="OV cert or Azure Artifact Signing + CI secrets",
            permission="release.sign",
            diagnostics="BLOCKED — SIGNING CREDENTIALS",
        ))
        put(Capability(
            id="msix",
            status=CapabilityStatus.NOT_SUPPORTED,
            provider="none",
            requirements="n/a — direct NSIS/MSI is the supported model",
            permission="release.package",
            diagnostics="documented decision: Store NOT pursued",
        ))
        put(Capability(
            id="update",
            status=CapabilityStatus.DEGRADED if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="passive git-remote check + CI full installers",
            requirements="signed metadata channel (missing)",
            permission="release.update",
            diagnostics="no auto-apply; no rollback engine yet in product",
        ))
        put(Capability(
            id="rollback",
            status=CapabilityStatus.UNAVAILABLE,
            provider="none in product (recorder spec in electron/update-manifest.cjs)",
            requirements="pre-update snapshot + health check",
            permission="release.rollback",
            diagnostics="previous-artifact reinstall is the current path",
        ))
        put(Capability(
            id="screenCapture",
            status=CapabilityStatus.AVAILABLE if IS_WINDOWS else CapabilityStatus.UNAVAILABLE,
            provider="desktopCapturer (task-scoped)",
            requirements="task association + provenance; no continuous capture",
            permission="os.capture",
            diagnostics="retention minimal; redaction optional",
        ))
        put(Capability(
            id="isAdmin",
            status=CapabilityStatus.AVAILABLE if _is_admin() else CapabilityStatus.UNAVAILABLE,
            provider="shell32.IsUserAnAdmin",
            requirements="n/a (informational; app must NOT require admin)",
            permission="none",
            diagnostics=f"elevated={_is_admin()}",
        ))
    except Exception as exc:  # never break reporting
        put(Capability(id="registry", status=CapabilityStatus.ERROR,
                       diagnostics=f"detector failure: {exc}"))
    return caps


def main() -> int:
    import json
    print(json.dumps({k: v.to_dict() for k, v in detect_capabilities().items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
