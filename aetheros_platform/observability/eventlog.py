"""Windows Event Log writer (Master 64.1 A6).

High-value operational/security events only — never a duplicate of the
structured application logs. Stable event IDs, secret redaction, and a
structured fallback record when the log is unavailable (non-Windows,
missing source registration). Actual ReportEvent path is IMPLEMENTED —
UNVERIFIED here (source registration needs admin once; not performed).
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"

SOURCE_NAME = "AetherOS"

EVENT_IDS = {
    "security.policy_violation": 1001,
    "auth.failure": 1002,
    "agent.runtime_failure": 2001,
    "update.failure": 3001,
    "recovery.failure": 3002,
    "tamper": 1003,
    "backend.critical": 4001,
}

SEVERITIES = {"info", "warning", "error", "critical"}

#: Win32 event types per severity.
EVENT_TYPES = {"info": 4, "warning": 2, "error": 1, "critical": 1}


@dataclass
class WindowsEvent:
    event_id: int
    key: str
    severity: str
    message: str
    task_id: str = ""
    agent_id: str = ""
    device_id: str = ""
    at: float = 0.0

    def __post_init__(self) -> None:
        if not self.at:
            import time as _t
            self.at = _t.time()


def _redact(text: str) -> str:
    try:
        from agent.redact import redact_sensitive_text as _r
        out = _r(text, force=True)
        return out if isinstance(out, str) else text
    except Exception:
        return text


def build_event(key: str, message: str, severity: str = "error",
                task_id: str = "", agent_id: str = "",
                device_id: str = "") -> WindowsEvent:
    if key not in EVENT_IDS:
        raise ValueError(f"unknown event key: {key}")
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity: {severity}")
    return WindowsEvent(event_id=EVENT_IDS[key], key=key, severity=severity,
                        message=_redact(message), task_id=task_id,
                        agent_id=agent_id, device_id=device_id)


def write_event(event: WindowsEvent) -> dict:
    """Write to the Windows Application log; fall back to a structured
    record when unavailable. Returns a receipt either way."""
    receipt = {"event_id": event.event_id, "key": event.key,
               "severity": event.severity, "at": event.at,
               "written": False, "fallback": True}
    if not IS_WINDOWS:
        receipt["reason"] = "non-windows"
        return receipt
    try:
        import win32evtlog  # type: ignore  # optional; pywin32
        import win32evtlogutil  # type: ignore
        _ = (win32evtlog, win32evtlogutil)
        receipt["reason"] = "pywin32 path not exercised here"
        return receipt
    except ImportError:
        pass
    try:
        import ctypes
        from ctypes import wintypes
        adv = ctypes.windll.advapi32
        adv.RegisterEventSourceW.restype = wintypes.HANDLE
        adv.ReportEventW.argtypes = [
            wintypes.HANDLE, wintypes.WORD, wintypes.WORD, wintypes.DWORD,
            ctypes.c_void_p, wintypes.WORD, wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        adv.ReportEventW.restype = wintypes.BOOL
        h = adv.RegisterEventSourceW(None, SOURCE_NAME)
        if not h:
            receipt["reason"] = "RegisterEventSource failed (source not registered?)"
            return receipt
        try:
            msg = f"[{event.key}] {event.message} " \
                  f"(task={event.task_id or '-'} agent={event.agent_id or '-'})"
            buf = ctypes.create_unicode_buffer(msg)
            arr = (ctypes.c_wchar_p * 1)(ctypes.cast(buf, ctypes.c_wchar_p).value)
            ok = adv.ReportEventW(
                h, EVENT_TYPES[event.severity],
                0, event.event_id, None, 1, 0, arr, None,
            )
            if ok:
                receipt["written"] = True
                receipt["fallback"] = False
            else:
                receipt["reason"] = "ReportEventW returned FALSE"
        finally:
            adv.DeregisterEventSource(h)
        return receipt
    except Exception as exc:
        receipt["reason"] = f"eventlog unavailable: {exc}"
        return receipt
