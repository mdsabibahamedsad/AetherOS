"""Capability permission engine (sections 12-14).

Catalog with risk R0-R5, scopes, default policy, approval + audit flags.
Scoped evaluation: filesystem paths, network domains, browser origins —
wildcards denied unless explicitly granted. Pure evaluation (no I/O).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class Risk(str):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"


@dataclass(frozen=True)
class PermissionDef:
    name: str
    risk: str
    scope_kind: str  # none|paths|domains|origins|named
    default: str  # allow|deny|approve
    approval: bool
    audit: bool
    description: str = ""


CATALOG: Dict[str, PermissionDef] = {
    "filesystem.read": PermissionDef("filesystem.read", Risk.R1, "paths", "approve", True, True),
    "filesystem.write": PermissionDef("filesystem.write", Risk.R3, "paths", "approve", True, True),
    "filesystem.delete": PermissionDef("filesystem.delete", Risk.R3, "paths", "approve", True, True),
    "network.request": PermissionDef("network.request", Risk.R2, "domains", "approve", True, True),
    "network.websocket": PermissionDef("network.websocket", Risk.R2, "domains", "approve", True, True),
    "shell.execute": PermissionDef("shell.execute", Risk.R4, "none", "deny", True, True),
    "browser.read": PermissionDef("browser.read", Risk.R1, "origins", "approve", True, True),
    "browser.navigate": PermissionDef("browser.navigate", Risk.R2, "origins", "approve", True, True),
    "browser.click": PermissionDef("browser.click", Risk.R3, "origins", "approve", True, True),
    "browser.type": PermissionDef("browser.type", Risk.R3, "origins", "approve", True, True),
    "browser.download": PermissionDef("browser.download", Risk.R3, "origins", "approve", True, True),
    "computer.read": PermissionDef("computer.read", Risk.R2, "none", "approve", True, True),
    "computer.input": PermissionDef("computer.input", Risk.R4, "none", "deny", True, True),
    "computer.screenshot": PermissionDef("computer.screenshot", Risk.R2, "none", "approve", True, True),
    "clipboard.read": PermissionDef("clipboard.read", Risk.R1, "none", "approve", True, True),
    "clipboard.write": PermissionDef("clipboard.write", Risk.R1, "none", "approve", True, True),
    "microphone.read": PermissionDef("microphone.read", Risk.R2, "none", "deny", True, True),
    "camera.read": PermissionDef("camera.read", Risk.R2, "none", "deny", True, True),
    "notifications.send": PermissionDef("notifications.send", Risk.R1, "none", "allow", False, True),
    "secrets.read_scoped": PermissionDef("secrets.read_scoped", Risk.R5, "named", "deny", True, True),
    "memory.read": PermissionDef("memory.read", Risk.R1, "named", "approve", True, True),
    "memory.write": PermissionDef("memory.write", Risk.R3, "named", "approve", True, True),
    "research.search": PermissionDef("research.search", Risk.R2, "domains", "approve", True, True),
    "research.fetch": PermissionDef("research.fetch", Risk.R2, "domains", "approve", True, True),
    "automation.create": PermissionDef("automation.create", Risk.R3, "none", "approve", True, True),
    "automation.execute": PermissionDef("automation.execute", Risk.R4, "none", "deny", True, True),
    "mcp.connect": PermissionDef("mcp.connect", Risk.R2, "named", "approve", True, True),
    "mcp.tool.execute": PermissionDef("mcp.tool.execute", Risk.R3, "named", "approve", True, True),
    "agent.spawn": PermissionDef("agent.spawn", Risk.R4, "none", "deny", True, True),
    "ui.register": PermissionDef("ui.register", Risk.R1, "none", "approve", False, True),
}


@dataclass
class Grant:
    permission: str
    scope: Dict[str, Any] = field(default_factory=dict)
    granted_by: str = ""
    granted_at: float = 0.0


def normalize_requested(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, str):
        return [{"permission": raw, "scope": {}}]
    if isinstance(raw, dict) and raw.get("permission"):
        return [{"permission": raw["permission"],
                 "scope": {k: v for k, v in raw.items() if k != "permission"}}]
    return []


def _scope_allows(perm: str, scope: Dict[str, Any], action: Dict[str, Any]) -> bool:
    kind = CATALOG[perm].scope_kind if perm in CATALOG else "none"
    if kind == "none":
        return True
    if kind == "paths":
        patterns = scope.get("paths", [])
        target = str(action.get("path", ""))
        if not patterns or not target:
            return False
        if "**" in patterns or "*" in patterns:
            return bool(scope.get("wildcard_approved", False))
        norm = target.replace("\\", "/")
        return any(fnmatch.fnmatch(norm, pat.replace("\\", "/")) for pat in patterns)
    if kind == "domains":
        domains = [d.lower() for d in scope.get("domains", [])]
        host = str(action.get("host", "")).lower()
        if not domains or not host:
            return False
        if "*" in domains:
            return bool(scope.get("wildcard_approved", False))
        return any(host == d or host.endswith("." + d) for d in domains)
    if kind == "origins":
        origins = scope.get("origins", [])
        origin = str(action.get("origin", ""))
        if not origins or not origin:
            return False
        if "*" in origins:
            return bool(scope.get("wildcard_approved", False))
        return any(fnmatch.fnmatch(origin, o) for o in origins)
    if kind == "named":
        names = scope.get("names", scope.get("scopes", []))
        return str(action.get("name", "")) in names
    return False


class PermissionEngine:
    """Evaluates granted capabilities. Enforcement lives in the runtime."""

    def risk_of(self, permission: str) -> str:
        return CATALOG[permission].risk if permission in CATALOG else Risk.R5

    def is_known(self, permission: str) -> bool:
        return permission in CATALOG

    def requires_approval(self, permission: str) -> bool:
        return CATALOG.get(permission, PermissionDef(permission, Risk.R5, "none",
                                                     "deny", True, True)).approval

    def check(self, grants: List[Grant], permission: str,
              action: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if permission not in CATALOG:
            return {"allowed": False, "reason": f"unknown permission: {permission}"}
        for grant in grants:
            if grant.permission != permission:
                continue
            if _scope_allows(permission, grant.scope, action or {}):
                return {"allowed": True, "reason": "grant covers action"}
        return {"allowed": False, "reason": f"no grant covers {permission}"}

    def review_groups(self, requested: List[Any]) -> Dict[str, List[str]]:
        """Group requested permissions by risk for the review UI."""
        groups: Dict[str, List[str]] = {"LOW RISK": [], "MEDIUM RISK": [],
                                        "HIGH RISK": [], "CRITICAL": []}
        for item in requested:
            for norm in normalize_requested(item):
                perm = norm["permission"]
                risk = self.risk_of(perm)
                label = ("LOW RISK" if risk in (Risk.R0, Risk.R1)
                         else "MEDIUM RISK" if risk == Risk.R2
                         else "HIGH RISK" if risk in (Risk.R3,)
                         else "CRITICAL")
                groups[label].append(perm)
        return groups
