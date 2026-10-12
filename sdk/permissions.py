"""
Permission Model
================

Extensions declare the permissions they need at install time. The user
(or enterprise policy) grants or denies them. Permissions are:

- **Explicit** — extensions must declare them upfront
- **Auditable** — every permission check is logged
- **Revocable** — permissions can be revoked at runtime
- **Granular** — filesystem:read is separate from filesystem:write

Permission categories:

    filesystem:*      Read/write files in sandbox or globally
    network:*         Make HTTP/network requests
    clipboard:*       Read/write system clipboard
    microphone:*      Access microphone
    camera:*          Access camera
    notifications:*   Send desktop/OS notifications
    workspace:*       Read workspace metadata
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Permission:
    """A single, typed permission.

    Format: ``<category>:<action>``

    Examples:
        ``filesystem:read`` — read files
        ``filesystem:write`` — write files
        ``network:connect`` — make outbound network connections
        ``clipboard:read`` — read clipboard contents
        ``clipboard:write`` — write to clipboard
        ``microphone:access`` — access microphone
        ``camera:access`` — access camera
        ``notifications:send`` — send notifications
        ``workspace:read`` — read workspace/project metadata
    """
    name: str

    def __post_init__(self) -> None:
        """Validate permission format."""
        if not isinstance(self.name, str) or ":" not in self.name:
            raise ValueError(
                f"Invalid permission format: '{self.name}'. "
                f"Must be '<category>:<action>' (e.g. 'filesystem:read')."
            )

    @property
    def category(self) -> str:
        return self.name.split(":", 1)[0]

    @property
    def action(self) -> str:
        return self.name.split(":", 1)[1]


# Standard permission sets
PERMISSION_FILESYSTEM_READ = Permission("filesystem:read")
PERMISSION_FILESYSTEM_WRITE = Permission("filesystem:write")
PERMISSION_NETWORK_CONNECT = Permission("network:connect")
PERMISSION_CLIPBOARD_READ = Permission("clipboard:read")
PERMISSION_CLIPBOARD_WRITE = Permission("clipboard:write")
PERMISSION_MICROPHONE = Permission("microphone:access")
PERMISSION_CAMERA = Permission("camera:access")
PERMISSION_NOTIFICATIONS = Permission("notifications:send")
PERMISSION_WORKSPACE_READ = Permission("workspace:read")

class PermissionSet:
    """An immutable set of permissions.

    Supports union, intersection, and containment checks.
    """

    def __init__(self, permissions: Optional[List[Permission]] = None) -> None:
        self._perms: Set[str] = {p.name for p in (permissions or [])}

    def has(self, permission: Permission) -> bool:
        """Check whether this set includes *permission*.

        Supports wildcard: ``permission.name == "filesystem:*"`` matches
        any ``filesystem:*`` permission.
        """
        if "*" in permission.name:
            cat = permission.name.split(":")[0]
            return any(p.startswith(f"{cat}:") for p in self._perms)
        return permission.name in self._perms

    def add(self, permission: Permission) -> "PermissionSet":
        """Return a new PermissionSet with *permission* added."""
        return PermissionSet([Permission(p) for p in self._perms | {permission.name}])

    def remove(self, permission: Permission) -> "PermissionSet":
        """Return a new PermissionSet with *permission* removed."""
        return PermissionSet([Permission(p) for p in self._perms - {permission.name}])

    def union(self, other: "PermissionSet") -> "PermissionSet":
        """Return the union of two permission sets."""
        return PermissionSet([Permission(p) for p in self._perms | other._perms])

    def intersection(self, other: "PermissionSet") -> "PermissionSet":
        """Return the intersection of two permission sets."""
        return PermissionSet([Permission(p) for p in self._perms & other._perms])

    def contains(self, other: "PermissionSet") -> bool:
        """Return True if this set includes all permissions in *other*."""
        return other._perms.issubset(self._perms)

    def list(self) -> List[Permission]:
        """Return sorted list of permissions."""
        return sorted(
            [Permission(p) for p in self._perms],
            key=lambda x: x.name,
        )

    def __repr__(self) -> str:
        return f"PermissionSet({sorted(self._perms)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PermissionSet):
            return NotImplemented
        return self._perms == other._perms

    def __bool__(self) -> bool:
        return bool(self._perms)


# Permission groups for common use cases
PERMISSION_FILESYSTEM_ALL = PermissionSet([
    PERMISSION_FILESYSTEM_READ,
    PERMISSION_FILESYSTEM_WRITE,
])

PERMISSION_CLIPBOARD_ALL = PermissionSet([
    PERMISSION_CLIPBOARD_READ,
    PERMISSION_CLIPBOARD_WRITE,
])


@dataclass
class PermissionAuditEntry:
    """A single audited permission check."""
    extension: str
    permission: str
    granted: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""


class PermissionAudit:
    """Audit trail for permission requests and grants.

    Tracks every permission check so the user can review what extensions
    are accessing.
    """

    def __init__(self) -> None:
        self._entries: List[PermissionAuditEntry] = []
        # Cache of granted permissions per extension
        self._grants: Dict[str, Set[str]] = {}

    def request(
        self,
        extension: str,
        permission: Permission,
        reason: str = "",
    ) -> bool:
        """Request a permission. Returns True if granted.

        In a headless/gateway context, returns True automatically for
        permissions declared in the extension's manifest (they were
        pre-approved at install time).
        """
        # Check if already granted
        if extension in self._grants and permission.name in self._grants[extension]:
            self._entries.append(PermissionAuditEntry(
                extension=extension,
                permission=permission.name,
                granted=True,
                reason="cached grant",
            ))
            return True

        # Check manifest declarations
        if self._is_declared(extension, permission):
            self._grant(extension, permission)
            self._entries.append(PermissionAuditEntry(
                extension=extension,
                permission=permission.name,
                granted=True,
                reason="declared in manifest",
            ))
            return True

        # In non-interactive mode, deny undeclared permissions
        import sys
        if not sys.stdin.isatty():
            self._entries.append(PermissionAuditEntry(
                extension=extension,
                permission=permission.name,
                granted=False,
                reason="non-interactive: permission not pre-declared",
            ))
            return False

        # Interactive prompt
        try:
            answer = input(
                f"\nExtension '{extension}' requests permission: "
                f"[bold]{permission.name}[/bold]\n"
                f"  Reason: {reason or 'not specified'}\n"
                f"  Grant? [y/N] "
            ).strip().lower()
            granted = answer in {"y", "yes"}
            if granted:
                self._grant(extension, permission)
            self._entries.append(PermissionAuditEntry(
                extension=extension,
                permission=permission.name,
                granted=granted,
                reason=f"user response: {answer}",
            ))
            return granted
        except (EOFError, KeyboardInterrupt):
            return False

    def _grant(self, extension: str, permission: Permission) -> None:
        self._grants.setdefault(extension, set()).add(permission.name)

    def _is_declared(self, extension: str, permission: Permission) -> bool:
        """Check if a permission was declared in the extension's manifest."""
        try:
            from extensions.manager import get_extension_manager
            mgr = get_extension_manager()
            ext = mgr.get_extension(extension)
            if ext and ext.manifest:
                return permission.name in (ext.manifest.permissions or [])
        except Exception:
            pass
        return False

    def get_entries(self, extension: Optional[str] = None) -> List[PermissionAuditEntry]:
        """Return audit entries, optionally filtered by extension name."""
        if extension:
            return [e for e in self._entries if e.extension == extension]
        return list(self._entries)

    def get_grants(self, extension: str) -> Set[str]:
        """Return the set of granted permission names for an extension."""
        return set(self._grants.get(extension, set()))

    def revoke(self, extension: str, permission: Permission) -> None:
        """Revoke a previously granted permission."""
        if extension in self._grants:
            self._grants[extension].discard(permission.name)
        self._entries.append(PermissionAuditEntry(
            extension=extension,
            permission=permission.name,
            granted=False,
            reason="explicitly revoked",
        ))

    def revoke_all(self, extension: str) -> None:
        """Revoke all permissions for an extension."""
        if extension in self._grants:
            for perm in list(self._grants[extension]):
                self._entries.append(PermissionAuditEntry(
                    extension=extension,
                    permission=perm,
                    granted=False,
                    reason="all revoked",
                ))
            self._grants[extension].clear()
