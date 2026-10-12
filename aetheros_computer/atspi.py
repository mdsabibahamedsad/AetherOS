"""Linux AT-SPI normalized model (Master 66).

Companion to ax.py (macOS) and uia.py (Windows): same discipline —
normalized ATSPIElement, scoped actions (read/control × aetheros/app/
desktop), control-requires-paired-read. Live AT-SPI access needs a
Linux desktop (BLOCKED); providers return typed data only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ATScope(str, Enum):
    AT_READ_AETHEROS = "AT_READ_AETHEROS"
    AT_READ_APP = "AT_READ_APP"
    AT_READ_DESKTOP = "AT_READ_DESKTOP"
    AT_CONTROL_AETHEROS = "AT_CONTROL_AETHEROS"
    AT_CONTROL_APP = "AT_CONTROL_APP"
    AT_CONTROL_DESKTOP = "AT_CONTROL_DESKTOP"


DEFAULT_AT_SCOPES = frozenset({ATScope.AT_READ_AETHEROS, ATScope.AT_CONTROL_AETHEROS})

READ_FOR = {
    ATScope.AT_CONTROL_AETHEROS: ATScope.AT_READ_AETHEROS,
    ATScope.AT_CONTROL_APP: ATScope.AT_READ_APP,
    ATScope.AT_CONTROL_DESKTOP: ATScope.AT_READ_DESKTOP,
}

AT_METHODS = frozenset({
    "discover", "children", "role", "name", "description", "value",
    "state", "bounds", "focus", "select", "expand", "collapse",
    "performAction", "setValue",
})

AT_CONTROL_METHODS = frozenset({
    "focus", "select", "expand", "collapse", "performAction", "setValue",
})


@dataclass
class ATSPIElement:
    element_id: str
    role: str
    name: str = ""
    description: str = ""
    value: str = ""
    state: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    actions: list[str] = field(default_factory=list)
    application_id: str = ""
    window_id: str = ""
    children: list["ATSPIElement"] = field(default_factory=list)


def at_scope_allows(scopes: list[ATScope], target: str, method: str) -> tuple[bool, str]:
    if method not in AT_METHODS:
        return False, f"unknown AT-SPI method '{method}'"
    key = {"aetheros": ("AT_READ_AETHEROS", "AT_CONTROL_AETHEROS"),
           "app": ("AT_READ_APP", "AT_CONTROL_APP"),
           "desktop": ("AT_READ_DESKTOP", "AT_CONTROL_DESKTOP")}.get(target)
    if key is None:
        return False, f"unknown target '{target}'"
    read_need, control_need = (ATScope[key[0]], ATScope[key[1]])
    have = set(scopes)
    if method in AT_CONTROL_METHODS:
        if control_need not in have:
            return False, f"missing scope {control_need.value}"
        if read_need not in have:
            return False, f"control requires paired read scope {read_need.value}"
    elif read_need not in have:
        return False, f"missing scope {read_need.value}"
    return True, "scope permits"
