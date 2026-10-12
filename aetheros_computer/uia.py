"""Windows UI Automation normalized model (Master 64.1 A5).

 STATUS: schema + scopes + provider interface IMPLEMENTED and tested;
 live UIA tree provider UNVERIFIED (no native UIA bridge wired; Windows
 reports ocr_fallback per platform_caps). Agents must prefer
 semantic > automationId > visual > coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class UIScope(str, Enum):
    UI_READ_AETHEROS = "UI_READ_AETHEROS"
    UI_READ_APP = "UI_READ_APP"
    UI_READ_DESKTOP = "UI_READ_DESKTOP"
    UI_CONTROL_AETHEROS = "UI_CONTROL_AETHEROS"
    UI_CONTROL_APP = "UI_CONTROL_APP"
    UI_CONTROL_DESKTOP = "UI_CONTROL_DESKTOP"


DEFAULT_SCOPES = frozenset({UIScope.UI_READ_AETHEROS, UIScope.UI_CONTROL_AETHEROS})

READ_SCOPE_FOR = {
    UIScope.UI_CONTROL_AETHEROS: UIScope.UI_READ_AETHEROS,
    UIScope.UI_CONTROL_APP: UIScope.UI_READ_APP,
    UIScope.UI_CONTROL_DESKTOP: UIScope.UI_READ_DESKTOP,
}


@dataclass
class UIElement:
    runtime_id: str
    name: str
    control_type: str
    automation_id: str = ""
    class_name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    enabled: bool = True
    visible: bool = True
    focused: bool = False
    value: str = ""
    patterns: list[str] = field(default_factory=list)
    children: list["UIElement"] = field(default_factory=list)


@dataclass
class UIAAction:
    action_id: str
    target_id: str
    method: str  # invoke|toggle|select|expand|collapse|setValue|scroll|focus
    scopes: list[UIScope] = field(default_factory=list)
    value: str = ""


ALLOWED_METHODS = frozenset({
    "inspect", "find", "focus", "invoke", "toggle", "select",
    "expand", "collapse", "setValue", "scroll", "getValue",
})

CONTROL_METHODS = frozenset({
    "invoke", "toggle", "select", "expand", "collapse", "setValue", "scroll",
})


def scope_allows(scopes: list[UIScope], target_app: str, method: str) -> tuple[bool, str]:
    """Check a UIA action against scopes. `target_app`: aetheros|app|desktop."""
    have = set(scopes)
    if method in CONTROL_METHODS:
        need = {"aetheros": UIScope.UI_CONTROL_AETHEROS,
                "app": UIScope.UI_CONTROL_APP,
                "desktop": UIScope.UI_CONTROL_DESKTOP}[target_app]
        if need not in have:
            return False, f"missing scope {need.value}"
        read_need = READ_SCOPE_FOR[need]
        if read_need not in have:
            return False, f"control requires paired read scope {read_need.value}"
    else:
        need = {"aetheros": UIScope.UI_READ_AETHEROS,
                "app": UIScope.UI_READ_APP,
                "desktop": UIScope.UI_READ_DESKTOP}[target_app]
        if need not in have:
            return False, f"missing scope {need.value}"
    return True, "scope permits"


class UIAProvider:
    """Interface for native UIA bridges. No COM crosses this boundary —
    providers return normalized UIElement trees only."""

    def find(self, root: str, query: dict[str, Any]) -> list[UIElement]:
        raise NotImplementedError

    def act(self, action: UIAAction) -> dict[str, Any]:
        raise NotImplementedError


class UnavailableProvider(UIAProvider):
    """Honest fallback: reports unavailability instead of fake elements."""

    def __init__(self, reason: str = "no UIA provider wired (ocr_fallback active)"):
        self.reason = reason

    def find(self, root: str, query: dict[str, Any]) -> list[UIElement]:
        raise RuntimeError(f"UIA unavailable: {self.reason}")

    def act(self, action: UIAAction) -> dict[str, Any]:
        raise RuntimeError(f"UIA unavailable: {self.reason}")
