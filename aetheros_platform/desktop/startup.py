"""Windows startup configuration (Master 64.1 A4).

Explicit, auditable, per-user persistence. Modes: DISABLED, START_ON_LOGIN,
START_MINIMIZED, BACKGROUND_AGENT_RUNTIME, FULL_UI_START. No silent
persistence: every registration produces an audit record with mechanism,
owner, and timestamp, and can be repaired/removed. No Windows Service is
created. Live registry writes happen only on win32 via winreg; elsewhere
the mechanism reports UNAVAILABLE. Actual OS registration effect is
IMPLEMENTED — UNVERIFIED in this workspace (no packaged app to register).
"""

from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum

IS_WINDOWS = sys.platform == "win32"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AetherOS"


class StartupMode(str, Enum):
    DISABLED = "DISABLED"
    START_ON_LOGIN = "START_ON_LOGIN"
    START_MINIMIZED = "START_MINIMIZED"
    BACKGROUND_AGENT_RUNTIME = "BACKGROUND_AGENT_RUNTIME"
    FULL_UI_START = "FULL_UI_START"


@dataclass
class StartupRecord:
    mode: StartupMode
    mechanism: str = ""
    owner: str = ""
    created_at: float = 0.0
    enabled: bool = False
    app_path: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


def describe_current() -> StartupRecord:
    """Read the per-user Run key; never writes."""
    if not IS_WINDOWS:
        return StartupRecord(mode=StartupMode.DISABLED, mechanism="non-windows")
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            minimized = "--minimized" in str(value)
            background = "--background" in str(value)
            mode = (StartupMode.BACKGROUND_AGENT_RUNTIME if background
                    else StartupMode.START_MINIMIZED if minimized
                    else StartupMode.FULL_UI_START)
            return StartupRecord(mode=mode, mechanism="HKCU Run key",
                                 enabled=True, app_path=str(value),
                                 created_at=time.time())
    except FileNotFoundError:
        return StartupRecord(mode=StartupMode.DISABLED,
                             mechanism="HKCU Run key (absent)")
    except OSError as exc:
        return StartupRecord(mode=StartupMode.DISABLED,
                             mechanism=f"HKCU Run key (unreadable: {exc})")


def build_run_value(exe_path: str, mode: StartupMode) -> str:
    """Build the Run-key command line. No secrets ever embedded."""
    if not exe_path:
        raise ValueError("exe_path required")
    quoted = f'"{exe_path}"'
    if mode == StartupMode.START_MINIMIZED:
        return f"{quoted} --minimized"
    if mode == StartupMode.BACKGROUND_AGENT_RUNTIME:
        return f"{quoted} --background"
    return quoted


def audit_event(record: StartupRecord, action: str) -> dict:
    return {
        "event": f"startup.{action}",
        "mode": record.mode.value,
        "mechanism": record.mechanism,
        "owner": record.owner,
        "enabled": record.enabled,
        "at": time.time(),
    }
