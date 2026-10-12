"""Universal scope system (§9).

Hierarchical ``capability:resource`` scopes with:
exact / wildcard / deny (!) / inherited (prefix) / temporary+expiring /
tenant-bound matching. Deny always overrides allow.
"""

from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Grant:
    scope: str  # e.g. "filesystem.read:/workspace/**" or "!secret.access"
    expires_at: Optional[float] = None
    tenant: str = "*"


def _expired(g: Grant) -> bool:
    return g.expires_at is not None and time.time() > g.expires_at


def _norm(scope: str) -> tuple[bool, str]:
    scope = scope.strip()
    deny = scope.startswith("!")
    if deny:
        scope = scope[1:]
    return deny, scope


def _match(pattern: str, scope: str) -> bool:
    """Match ``cap:resource`` with fnmatch on both halves; bare capability
    implies ``cap:*``. ``*`` capability matches anything in that half."""
    def split(s: str) -> tuple[str, str]:
        if ":" in s:
            c, r = s.split(":", 1)
            return c.strip(), r.strip() or "*"
        return s.strip(), "*"
    pc, pr = split(pattern)
    sc, sr = split(scope)
    return fnmatch.fnmatchcase(sc, pc) and fnmatch.fnmatchcase(sr, pr)


class ScopeSet:
    """A set of grants belonging to one identity/delegation."""

    def __init__(self, grants: Optional[List[Grant]] = None):
        self.grants: List[Grant] = list(grants or [])

    def grant(self, scope: str, expires_in: Optional[float] = None,
              tenant: str = "*") -> None:
        exp = (time.time() + expires_in) if expires_in else None
        self.grants.append(Grant(scope=scope, expires_at=exp, tenant=tenant))

    def revoke(self, scope: str) -> None:
        self.grants = [g for g in self.grants if g.scope != scope]

    def allows(self, scope: str, tenant: str = "default") -> bool:
        allowed = False
        for g in self.grants:
            if _expired(g):
                continue
            if g.tenant not in ("*", tenant):
                continue
            deny, pattern = _norm(g.scope)
            if _match(pattern, scope):
                if deny:
                    return False  # deny overrides everything
                allowed = True
        return allowed

    def is_subset_of(self, other: "ScopeSet", tenant: str = "default") -> bool:
        """Every non-deny grant here must be allowed by other (subset rule)."""
        for g in self.grants:
            deny, _ = _norm(g.scope)
            if deny or _expired(g):
                continue
            if not other.allows(g.scope, tenant):
                return False
        return True

    def active(self) -> List[Grant]:
        return [g for g in self.grants if not _expired(g)]

    def to_list(self) -> List[str]:
        return [g.scope for g in self.active()]
