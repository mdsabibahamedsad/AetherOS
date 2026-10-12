"""macOS TCC permission model (Master 65).

Privacy permissions are first-class capabilities with explicit states:
AVAILABLE, DENIED, NOT_DETERMINED, RESTRICTED, UNAVAILABLE,
REQUIRES_USER_ACTION. Policy: request a permission ONLY when the
feature needing it is invoked (never all at first launch), explain why,
link to Settings on denial, degrade gracefully, never spam prompts.
Live TCC queries need macOS — detectors here report structure; the
`provider` field records how each state is determined on-device.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum


class TCCState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DENIED = "DENIED"
    NOT_DETERMINED = "NOT_DETERMINED"
    RESTRICTED = "RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"
    REQUIRES_USER_ACTION = "REQUIRES_USER_ACTION"


@dataclass
class TCCCapability:
    id: str  # accessibility|screenRecording|microphone|camera|automation|filesFolders|fullDisk
    state: TCCState
    why_needed: str = ""
    settings_anchor: str = ""
    last_checked: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d


CAPABILITY_META = {
    "accessibility": (
        "Computer-use control (AX actions).",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    ),
    "screenRecording": (
        "Vision/screenshot capture for agents.",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
    ),
    "microphone": (
        "Voice input and conversations.",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    ),
    "camera": (
        "Camera input where features require it.",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera",
    ),
    "automation": (
        "Controlling other apps via Apple Events (privileged).",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
    ),
    "filesFolders": (
        "User-selected file access beyond the sandbox.",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders",
    ),
    "fullDisk": (
        "Rarely needed; request only with explicit justification.",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
    ),
}


def default_capabilities() -> dict[str, TCCCapability]:
    """Pre-permission baseline: nothing claimed granted."""
    out = {}
    for cid, (why, anchor) in CAPABILITY_META.items():
        out[cid] = TCCCapability(id=cid, state=TCCState.NOT_DETERMINED,
                                 why_needed=why, settings_anchor=anchor)
    return out


def should_request(cap: TCCCapability, feature_invoked: bool) -> bool:
    """Request only when needed, once: NOT_DETERMINED + feature invoked."""
    return cap.state == TCCState.NOT_DETERMINED and feature_invoked


def degraded_message(cap: TCCCapability) -> str:
    if cap.state == TCCState.DENIED:
        return (f"{cap.id} denied. {cap.why_needed} Enable it in System "
                f"Settings, or continue without this feature.")
    if cap.state == TCCState.RESTRICTED:
        return f"{cap.id} is restricted by device policy. This feature is unavailable."
    return f"{cap.id} is not available: {cap.state.value}."
