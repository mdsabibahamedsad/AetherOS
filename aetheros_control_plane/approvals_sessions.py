"""Approvals + JIT elevation (§13-14), sessions (§50-51), org RBAC/ABAC (§48).

Approvals are scoped, time-limited, action/resource/identity-specific —
never blanket "approve everything forever". JIT grants temporary scopes
that auto-expire. Sessions support expiry/revocation/idle-timeout and
step-up authentication for high-risk actions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import ControlPlaneError, FailureCode
from .scopes import ScopeSet


@dataclass
class Approval:
    id: str
    action: str
    resource: str
    identity_id: str
    scope: str = ""
    task_id: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 600)
    used: bool = False
    one_time: bool = True


class ApprovalEngine:
    def __init__(self) -> None:
        self._pending: Dict[str, Approval] = {}
        self._decided: Dict[str, bool] = {}

    def request(self, action: str, resource: str, identity_id: str,
                task_id: str = "", ttl: float = 600) -> Approval:
        ap = Approval(id=f"apr_{uuid.uuid4().hex[:10]}", action=action,
                      resource=resource, identity_id=identity_id,
                      scope=f"{action}:{resource}", task_id=task_id,
                      expires_at=time.time() + ttl)
        self._pending[ap.id] = ap
        return ap

    def decide(self, approval_id: str, granted: bool) -> bool:
        ap = self._pending.get(approval_id)
        if ap is None:
            return False
        self._decided[approval_id] = granted
        return True

    def consume(self, approval_id: str, action: str, resource: str,
                identity_id: str) -> bool:
        """Bind approval to the exact action/resource/identity (§13)."""
        ap = self._pending.get(approval_id)
        if ap is None or not self._decided.get(approval_id, False):
            return False
        if time.time() > ap.expires_at:
            return False
        if ap.used and ap.one_time:
            return False
        if (ap.action, ap.resource, ap.identity_id) != (
                action, resource, identity_id):
            return False
        ap.used = True
        return True


class JITManager:
    """Temporary privilege elevation (§14). No permanent escalation."""

    def __init__(self) -> None:
        self._temp: Dict[str, ScopeSet] = {}

    def elevate(self, identity_id: str, scopes: List[str],
                duration: float = 900, tenant: str = "default") -> None:
        ss = self._temp.setdefault(identity_id, ScopeSet())
        for s in scopes:
            ss.grant(s, expires_in=duration, tenant=tenant)

    def scopes_for(self, identity_id: str) -> ScopeSet:
        return self._temp.get(identity_id, ScopeSet())


# ---------------------------------------------------------------------------
# Sessions (§50) + step-up (§51)
# ---------------------------------------------------------------------------

@dataclass
class Session:
    id: str
    identity_id: str
    device_id: str = ""
    tenant: str = "default"
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    scopes: List[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    auth_strength: str = "password"
    stepped_up_until: float = 0.0
    revoked: bool = False


class SessionManager:
    def __init__(self, idle_timeout: float = 1800) -> None:
        self._sessions: Dict[str, Session] = {}
        self.idle_timeout = idle_timeout

    def create(self, identity_id: str, scopes: Optional[List[str]] = None,
               device_id: str = "", tenant: str = "default",
               ttl: float = 3600) -> Session:
        s = Session(id=f"ses_{uuid.uuid4().hex[:10]}",
                    identity_id=identity_id, device_id=device_id,
                    tenant=tenant, scopes=list(scopes or []),
                    expires_at=time.time() + ttl)
        self._sessions[s.id] = s
        return s

    def get(self, session_id: str) -> Optional[Session]:
        s = self._sessions.get(session_id)
        if s is None or s.revoked or time.time() > s.expires_at:
            return None
        if time.time() - s.last_seen > self.idle_timeout:
            s.revoked = True
            return None
        s.last_seen = time.time()
        return s

    def revoke(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].revoked = True

    def revoke_identity(self, identity_id: str) -> int:
        n = 0
        for s in self._sessions.values():
            if s.identity_id == identity_id and not s.revoked:
                s.revoked = True
                n += 1
        return n

    def step_up(self, session_id: str, duration: float = 300) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.stepped_up_until = time.time() + duration
        s.auth_strength = "step-up"
        return True

    def is_stepped_up(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        return bool(s and time.time() < s.stepped_up_until)


# ---------------------------------------------------------------------------
# RBAC + ABAC (§47-48)
# ---------------------------------------------------------------------------

RBAC_ROLES = ("owner", "admin", "developer", "operator", "researcher",
              "viewer", "auditor")

_ROLE_CAPS = {
    "owner": ["*"],
    "admin": ["*.read", "*.write", "agent.delegate", "*.execute"],
    "developer": ["*.read", "filesystem.write", "terminal.execute",
                  "agent.delegate"],
    "operator": ["*.read", "*.execute"],
    "researcher": ["*.read", "browser.*", "memory.read"],
    "viewer": ["*.read"],
    "auditor": ["audit.read", "*.read"],
}


class OrgEngine:
    def __init__(self) -> None:
        self._roles: Dict[str, List[str]] = {}  # identity -> roles
        self._attrs: Dict[str, Dict[str, str]] = {}

    def assign_role(self, identity_id: str, role: str) -> None:
        if role not in RBAC_ROLES:
            raise ValueError(f"unknown role {role}")
        self._roles.setdefault(identity_id, [])
        if role not in self._roles[identity_id]:
            self._roles[identity_id].append(role)

    def set_attributes(self, identity_id: str, attrs: Dict[str, str]) -> None:
        self._attrs[identity_id] = dict(attrs)

    def allowed(self, identity_id: str, capability: str,
                required_attrs: Optional[Dict[str, str]] = None) -> bool:
        import fnmatch
        for role in self._roles.get(identity_id, []):
            for pat in _ROLE_CAPS.get(role, []):
                if fnmatch.fnmatchcase(capability, pat):
                    if required_attrs:
                        mine = self._attrs.get(identity_id, {})
                        if not all(mine.get(k) == v
                                   for k, v in required_attrs.items()):
                            continue
                    return True
        return False
