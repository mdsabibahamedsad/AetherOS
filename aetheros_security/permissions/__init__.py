"""
Permission Engine for AetherOS
==============================

Granular permission system with Zero Trust architecture.

Permission Format: "category:action"
Examples:
    - filesystem:read
    - network:connect
    - terminal:execute
    - memory:write

Usage::

    from aetheros_security.permissions import PermissionEngine

    engine = PermissionEngine()
    engine.grant("filesystem:read", "my-plugin", duration="session")
    allowed = engine.check("filesystem:read", "my-plugin")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PermissionStatus(Enum):
    """Permission status."""
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    REVOKED = "revoked"


class RiskLevel(Enum):
    """Risk levels for permissions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PermissionRequest:
    """A permission request."""
    permission: str
    requester: str
    reason: str = ""
    timestamp: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    scope: str = ""
    duration: str = "session"


@dataclass
class PermissionGrant:
    """A granted permission."""
    permission: str
    grantee: str
    granted_at: float = 0.0
    expires_at: float = 0.0
    duration: str = "session"
    reason: str = ""
    granted_by: str = "user"


@dataclass
class PermissionRule:
    """A permission rule."""
    permission: str
    requester_pattern: str  # Regex pattern or exact match
    action: str  # "allow", "deny", "ask"
    conditions: Dict[str, Any] = field(default_factory=dict)


class PermissionEngine:
    """Granular permission engine with Zero Trust.

    Usage::

        engine = PermissionEngine()

        # Grant permission
        engine.grant("filesystem:read", "my-plugin", duration="session")

        # Check permission
        allowed = engine.check("filesystem:read", "my-plugin")

        # Revoke permission
        engine.revoke("filesystem:read", "my-plugin")
    """

    def __init__(self) -> None:
        self._grants: Dict[str, Dict[str, PermissionGrant]] = {}
        self._rules: List[PermissionRule] = []
        self._pending_requests: List[PermissionRequest] = []
        self._callbacks: Dict[str, Callable] = {}
        self._audit_log: List[Dict[str, Any]] = []

        # Load persisted permissions
        self._load_permissions()

    def _load_permissions(self) -> None:
        """Load persisted permissions."""
        try:
            from aetheros_constants import get_aetheros_home
            perm_file = get_aetheros_home() / "permissions.json"
            if perm_file.exists():
                with open(perm_file, encoding="utf-8") as f:
                    data = json.load(f)
                # Restore grants
                for key, grant_data in data.get("grants", {}).items():
                    parts = key.split("|")
                    if len(parts) == 2:
                        perm, grantee = parts
                        self._grants.setdefault(perm, {})[grantee] = PermissionGrant(
                            permission=perm,
                            grantee=grantee,
                            granted_at=grant_data.get("granted_at", 0),
                            expires_at=grant_data.get("expires_at", 0),
                            duration=grant_data.get("duration", "session"),
                            reason=grant_data.get("reason", ""),
                        )
        except Exception as exc:
            logger.debug("Could not load permissions: %s", exc)

    def _save_permissions(self) -> None:
        """Persist permissions to disk."""
        try:
            from aetheros_constants import get_aetheros_home
            perm_file = get_aetheros_home() / "permissions.json"
            data = {"grants": {}}
            for perm, grants in self._grants.items():
                for grantee, grant in grants.items():
                    key = f"{perm}|{grantee}"
                    data["grants"][key] = {
                        "granted_at": grant.granted_at,
                        "expires_at": grant.expires_at,
                        "duration": grant.duration,
                        "reason": grant.reason,
                    }
            with open(perm_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("Could not save permissions: %s", exc)

    def check(
        self,
        permission: str,
        requester: str,
        *,
        auto_grant: bool = False,
    ) -> bool:
        """Check if a permission is granted.

        Args:
            permission: Permission to check (e.g., "filesystem:read").
            requester: Who is requesting.
            auto_grant: If True, auto-grant low-risk permissions.

        Returns:
            True if permission is granted.
        """
        # Check if grant exists and is valid
        grants = self._grants.get(permission, {})
        grant = grants.get(requester)

        if grant:
            # Check expiry
            if grant.expires_at > 0 and time.time() > grant.expires_at:
                # Permission expired
                del grants[requester]
                self._log_audit(permission, requester, "expired")
                return False
            return True

        # Check rules
        for rule in self._rules:
            if self._matches_rule(rule, permission, requester):
                if rule.action == "allow":
                    return True
                elif rule.action == "deny":
                    self._log_audit(permission, requester, "denied_by_rule")
                    return False
                elif rule.action == "ask":
                    return self._ask_user(permission, requester)

        # Zero Trust: deny by default
        self._log_audit(permission, requester, "denied_default")
        return False

    def _matches_rule(
        self,
        rule: PermissionRule,
        permission: str,
        requester: str,
    ) -> bool:
        """Check if a rule matches."""
        import re

        # Check permission match
        if rule.permission != "*" and rule.permission != permission:
            return False

        # Check requester pattern
        try:
            if re.match(rule.requester_pattern, requester):
                return True
        except re.error:
            if rule.requester_pattern == requester:
                return True

        return False

    def grant(
        self,
        permission: str,
        requester: str,
        *,
        duration: str = "session",
        reason: str = "",
    ) -> bool:
        """Grant a permission.

        Args:
            permission: Permission to grant.
            requester: Who receives the permission.
            duration: How long the permission lasts.
            reason: Why the permission was granted.

        Returns:
            True if successful.
        """
        now = time.time()
        expires_at = self._calculate_expiry(duration)

        grant = PermissionGrant(
            permission=permission,
            grantee=requester,
            granted_at=now,
            expires_at=expires_at,
            duration=duration,
            reason=reason,
        )

        self._grants.setdefault(permission, {})[requester] = grant
        self._save_permissions()
        self._log_audit(permission, requester, "granted", duration=duration, reason=reason)

        logger.info("Permission granted: %s to %s (duration: %s)", permission, requester, duration)
        return True

    def _calculate_expiry(self, duration: str) -> float:
        """Calculate expiry time from duration."""
        now = time.time()
        durations = {
            "once": 0,  # Will be revoked after use
            "session": 0,  # Will be revoked on session end
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "permanent": float("inf"),
        }
        seconds = durations.get(duration, 0)
        return now + seconds if seconds > 0 else 0

    def revoke(
        self,
        permission: str,
        requester: str,
    ) -> bool:
        """Revoke a permission.

        Args:
            permission: Permission to revoke.
            requester: Who loses the permission.

        Returns:
            True if successful.
        """
        grants = self._grants.get(permission, {})
        if requester in grants:
            del grants[requester]
            self._save_permissions()
            self._log_audit(permission, requester, "revoked")
            logger.info("Permission revoked: %s from %s", permission, requester)
            return True
        return False

    def request(
        self,
        permission: str,
        requester: str,
        *,
        reason: str = "",
        duration: str = "session",
    ) -> bool:
        """Request a permission (triggers user prompt if needed).

        Args:
            permission: Permission to request.
            requester: Who is requesting.
            reason: Why the permission is needed.
            duration: Requested duration.

        Returns:
            True if permission is granted.
        """
        # Check if already granted
        if self.check(permission, requester):
            return True

        # Create request
        request = PermissionRequest(
            permission=permission,
            requester=requester,
            reason=reason,
            timestamp=time.time(),
            risk_level=self._assess_risk(permission),
            duration=duration,
        )

        # Log the request
        self._log_audit(
            permission,
            requester,
            "requested",
            reason=reason,
            risk_level=request.risk_level.value,
        )

        # Ask user
        granted = self._ask_user(permission, requester, reason=reason, risk_level=request.risk_level)

        if granted:
            self.grant(permission, requester, duration=duration, reason=reason)

        return granted

    def _assess_risk(self, permission: str) -> RiskLevel:
        """Assess the risk level of a permission."""
        high_risk = {
            "terminal:execute",
            "filesystem:write",
            "filesystem:delete",
            "network:connect",
            "docker:run",
            "ssh:execute",
            "desktop:control",
            "keyboard:input",
            "mouse:control",
        }

        medium_risk = {
            "filesystem:read",
            "clipboard:read",
            "clipboard:write",
            "browser:navigate",
            "camera:capture",
            "microphone:record",
            "memory:write",
            "knowledge:write",
            "git:push",
        }

        if permission in high_risk:
            return RiskLevel.HIGH
        elif permission in medium_risk:
            return RiskLevel.MEDIUM
        elif "delete" in permission or "write" in permission:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _ask_user(
        self,
        permission: str,
        requester: str,
        *,
        reason: str = "",
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> bool:
        """Ask user for permission."""
        # Check for callback
        callback = self._callbacks.get("ask_permission")
        if callback:
            return callback(permission, requester, reason=reason, risk_level=risk_level)

        # Default: log and deny in non-interactive mode
        logger.warning(
            "Permission request: %s by %s (reason: %s, risk: %s)",
            permission, requester, reason, risk_level.value,
        )
        return False

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for permission events."""
        self._callbacks[event] = callback

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a permission rule."""
        self._rules.append(rule)

    def get_grants(
        self,
        requester: Optional[str] = None,
    ) -> List[PermissionGrant]:
        """Get all grants, optionally filtered by requester."""
        grants = []
        for perm_grants in self._grants.values():
            for grantee, grant in perm_grants.items():
                if requester is None or grantee == requester:
                    # Check if still valid
                    if grant.expires_at == 0 or time.time() <= grant.expires_at:
                        grants.append(grant)
        return grants

    def get_pending_requests(self) -> List[PermissionRequest]:
        """Get pending permission requests."""
        return list(self._pending_requests)

    def revoke_all(self, requester: str) -> int:
        """Revoke all permissions for a requester.

        Returns:
            Number of permissions revoked.
        """
        count = 0
        for perm in list(self._grants.keys()):
            if requester in self._grants[perm]:
                del self._grants[perm][requester]
                count += 1
        if count > 0:
            self._save_permissions()
            self._log_audit("*", requester, "revoked_all")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get permission statistics."""
        total_grants = sum(len(g) for g in self._grants.values())
        return {
            "total_permissions": len(self._grants),
            "total_grants": total_grants,
            "rules": len(self._rules),
            "pending_requests": len(self._pending_requests),
        }

    def _log_audit(
        self,
        permission: str,
        requester: str,
        action: str,
        **kwargs,
    ) -> None:
        """Log an audit event."""
        entry = {
            "timestamp": time.time(),
            "permission": permission,
            "requester": requester,
            "action": action,
            **kwargs,
        }
        self._audit_log.append(entry)

        # Keep only last 10000 entries
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

    def export_audit_log(self, path: str) -> bool:
        """Export audit log to file."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._audit_log, f, indent=2)
            return True
        except Exception:
            return False


# Global permission engine
_permission_engine: PermissionEngine | None = None


def get_permission_engine() -> PermissionEngine:
    """Return the global PermissionEngine singleton."""
    global _permission_engine
    if _permission_engine is None:
        _permission_engine = PermissionEngine()
    return _permission_engine
