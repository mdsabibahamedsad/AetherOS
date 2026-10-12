"""macOS Accessibility (AX) normalized model (Master 65).

Companion to `aetheros_computer/uia.py` (Windows). macOS backend is the
cua-driver, which exposes the native AX tree; this module is the TYPED
contract agents use: normalized AXElement, scoped actions, verification
requirements. Live AX runs: BLOCKED — MACOS ENVIRONMENT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AXScope(str, Enum):
    AX_READ_AETHEROS = "AX_READ_AETHEROS"
    AX_READ_APP = "AX_READ_APP"
    AX_READ_DESKTOP = "AX_READ_DESKTOP"
    AX_CONTROL_AETHEROS = "AX_CONTROL_AETHEROS"
    AX_CONTROL_APP = "AX_CONTROL_APP"
    AX_CONTROL_DESKTOP = "AX_CONTROL_DESKTOP"


DEFAULT_AX_SCOPES = frozenset({AXScope.AX_READ_AETHEROS, AXScope.AX_CONTROL_AETHEROS})

READ_FOR = {
    AXScope.AX_CONTROL_AETHEROS: AXScope.AX_READ_AETHEROS,
    AXScope.AX_CONTROL_APP: AXScope.AX_READ_APP,
    AXScope.AX_CONTROL_DESKTOP: AXScope.AX_READ_DESKTOP,
}

AX_METHODS = frozenset({
    "inspect", "find", "focus", "press", "increment", "decrement",
    "setValue", "select", "expand", "collapse", "scroll", "readValue",
})

AX_CONTROL_METHODS = frozenset({
    "press", "increment", "decrement", "setValue", "select",
    "expand", "collapse", "scroll",
})


@dataclass
class AXElement:
    identifier: str
    role: str
    title: str = ""
    description: str = ""
    value: str = ""
    subrole: str = ""
    enabled: bool = True
    focused: bool = False
    selected: bool = False
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    actions: list[str] = field(default_factory=list)
    children: list["AXElement"] = field(default_factory=list)


@dataclass
class AXAction:
    action_id: str
    target_id: str
    method: str
    scopes: list[AXScope] = field(default_factory=list)
    value: str = ""
    task_id: str = ""
    agent_id: str = ""


def ax_scope_allows(scopes: list[AXScope], target: str, method: str) -> tuple[bool, str]:
    """`target`: aetheros|app|desktop. Mirrors UIA scope discipline."""
    if method not in AX_METHODS:
        return False, f"unknown AX method '{method}'"
    have = set(scopes)
    key = {"aetheros": ("AX_READ_AETHEROS", "AX_CONTROL_AETHEROS"),
           "app": ("AX_READ_APP", "AX_CONTROL_APP"),
           "desktop": ("AX_READ_DESKTOP", "AX_CONTROL_DESKTOP")}.get(target)
    if key is None:
        return False, f"unknown target '{target}'"
    read_need, control_need = (AXScope[key[0]], AXScope[key[1]])
    if method in AX_CONTROL_METHODS:
        if control_need not in have:
            return False, f"missing scope {control_need.value}"
        if read_need not in have:
            return False, f"control requires paired read scope {read_need.value}"
    elif read_need not in have:
        return False, f"missing scope {read_need.value}"
    return True, "scope permits"
