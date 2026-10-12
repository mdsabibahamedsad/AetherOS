"""
Role-Based Access Control (RBAC)
================================

Configurable roles and permissions across engineering, memory,
cluster, plugins, marketplace, administration, approvals, audit,
and settings domains.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Permission:
    """A named, scoped permission with a human-readable description."""
    name: str
    description: str = ""
    domain: str = ""

    def __str__(self) -> str:
        return self.name


# Domain-scoped permission constants
PERM_ENGINEERING_READ = Permission("engineering:read", "Read engineering data", "engineering")
PERM_ENGINEERING_WRITE = Permission("engineering:write", "Modify engineering data", "engineering")
PERM_ENGINEERING_DELETE = Permission("engineering:delete", "Delete engineering data", "engineering")
PERM_ENGINEERING_APPROVE = Permission("engineering:approve", "Approve engineering changes", "engineering")

PERM_MEMORY_READ = Permission("memory:read", "Read memory entries", "memory")
PERM_MEMORY_WRITE = Permission("memory:write", "Write memory entries", "memory")
PERM_MEMORY_DELETE = Permission("memory:delete", "Delete memory entries", "memory")

PERM_CLUSTER_READ = Permission("cluster:read", "Read cluster state", "cluster")
PERM_CLUSTER_WRITE = Permission("cluster:write", "Modify cluster state", "cluster")
PERM_CLUSTER_MANAGE = Permission("cluster:manage", "Manage cluster nodes", "cluster")

PERM_PLUGINS_INSTALL = Permission("plugins:install", "Install plugins", "plugins")
PERM_PLUGINS_REMOVE = Permission("plugins:remove", "Remove plugins", "plugins")
PERM_PLUGINS_CONFIGURE = Permission("plugins:configure", "Configure plugins", "plugins")

PERM_MARKETPLACE_SEARCH = Permission("marketplace:search", "Search marketplace", "marketplace")
PERM_MARKETPLACE_PUBLISH = Permission("marketplace:publish", "Publish to marketplace", "marketplace")
PERM_MARKETPLACE_APPROVE = Permission("marketplace:approve", "Approve marketplace items", "marketplace")

PERM_ADMIN_USERS = Permission("admin:users", "Manage users", "admin")
PERM_ADMIN_ORG = Permission("admin:org", "Manage organization settings", "admin")
PERM_ADMIN_BILLING = Permission("admin:billing", "Manage billing", "admin")

PERM_APPROVE_POLICY = Permission("approve:policy", "Approve policy exceptions", "approvals")
PERM_APPROVE_DEPLOYMENT = Permission("approve:deployment", "Approve deployments", "approvals")
PERM_APPROVE_WORKFLOW = Permission("approve:workflow", "Approve workflow execution", "approvals")

PERM_AUDIT_READ = Permission("audit:read", "Read audit logs", "audit")
PERM_AUDIT_EXPORT = Permission("audit:export", "Export audit logs", "audit")

PERM_SETTINGS_READ = Permission("settings:read", "Read settings", "settings")
PERM_SETTINGS_WRITE = Permission("settings:write", "Modify settings", "settings")


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

@dataclass
class Role:
    """A named collection of permissions."""
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    inherits: List[str] = field(default_factory=list)
    is_builtin: bool = False

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def add_permission(self, permission: Permission) -> None:
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        self.permissions.discard(permission)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permissions": sorted(p.name for p in self.permissions),
            "inherits": self.inherits,
            "is_builtin": self.is_builtin,
        }


# Built-in roles
BUILTIN_ROLES: Dict[str, Role] = {
    "admin": Role(
        name="admin",
        description="Full administrative access",
        permissions={
            PERM_ENGINEERING_READ, PERM_ENGINEERING_WRITE, PERM_ENGINEERING_DELETE, PERM_ENGINEERING_APPROVE,
            PERM_MEMORY_READ, PERM_MEMORY_WRITE, PERM_MEMORY_DELETE,
            PERM_CLUSTER_READ, PERM_CLUSTER_WRITE, PERM_CLUSTER_MANAGE,
            PERM_PLUGINS_INSTALL, PERM_PLUGINS_REMOVE, PERM_PLUGINS_CONFIGURE,
            PERM_MARKETPLACE_SEARCH, PERM_MARKETPLACE_PUBLISH, PERM_MARKETPLACE_APPROVE,
            PERM_ADMIN_USERS, PERM_ADMIN_ORG, PERM_ADMIN_BILLING,
            PERM_APPROVE_POLICY, PERM_APPROVE_DEPLOYMENT, PERM_APPROVE_WORKFLOW,
            PERM_AUDIT_READ, PERM_AUDIT_EXPORT,
            PERM_SETTINGS_READ, PERM_SETTINGS_WRITE,
        },
        is_builtin=True,
    ),
    "developer": Role(
        name="developer",
        description="Development access — build and test",
        permissions={
            PERM_ENGINEERING_READ, PERM_ENGINEERING_WRITE,
            PERM_MEMORY_READ, PERM_MEMORY_WRITE,
            PERM_CLUSTER_READ,
            PERM_PLUGINS_INSTALL, PERM_PLUGINS_CONFIGURE,
            PERM_MARKETPLACE_SEARCH,
            PERM_SETTINGS_READ,
        },
        is_builtin=True,
    ),
    "operator": Role(
        name="operator",
        description="Operations access — deploy and monitor",
        permissions={
            PERM_ENGINEERING_READ,
            PERM_CLUSTER_READ, PERM_CLUSTER_WRITE,
            PERM_PLUGINS_INSTALL,
            PERM_MARKETPLACE_SEARCH,
            PERM_AUDIT_READ,
            PERM_SETTINGS_READ,
            PERM_APPROVE_DEPLOYMENT, PERM_APPROVE_WORKFLOW,
        },
        is_builtin=True,
    ),
    "viewer": Role(
        name="viewer",
        description="Read-only access",
        permissions={
            PERM_ENGINEERING_READ,
            PERM_MEMORY_READ,
            PERM_CLUSTER_READ,
            PERM_MARKETPLACE_SEARCH,
            PERM_AUDIT_READ,
            PERM_SETTINGS_READ,
        },
        is_builtin=True,
    ),
    "auditor": Role(
        name="auditor",
        description="Audit log access",
        permissions={
            PERM_AUDIT_READ, PERM_AUDIT_EXPORT,
            PERM_SETTINGS_READ,
        },
        is_builtin=True,
    ),
}


@dataclass
class RoleBinding:
    """Links a subject (user/group/SA) to a role within a scope."""
    subject_id: str
    role_name: str
    scope: str  # e.g. "org:org1", "ws:ws1", "global"
    id: str = ""
    subject_type: str = "user"  # user, group, service_account


class RBACManager:
    """Manages roles, permissions, and access decisions.

    Usage::

        rbac = RBACManager()
        rbac.assign_role("user:alice", "admin", "org:acme")
        allowed = rbac.check_access("user:alice", PERM_ADMIN_USERS, "org:acme")
    """

    def __init__(self) -> None:
        self._roles: Dict[str, Role] = dict(BUILTIN_ROLES)
        self._bindings: List[RoleBinding] = []

    def register_role(self, role: Role) -> None:
        """Register a custom role."""
        self._roles[role.name] = role

    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        role = self._roles.get(name)
        if role:
            return role
        # Check inheritance chain
        for r in self._roles.values():
            if name in r.inherits:
                return self._roles.get(name)
        return None

    def list_roles(self) -> List[Role]:
        return list(self._roles.values())

    def assign_role(
        self,
        subject_id: str,
        role_name: str,
        scope: str,
        subject_type: str = "user",
    ) -> RoleBinding:
        """Assign a role to a subject within a scope."""
        if role_name not in self._roles:
            raise ValueError(f"Unknown role: {role_name}")
        binding = RoleBinding(
            subject_id=subject_id,
            role_name=role_name,
            scope=scope,
            subject_type=subject_type,
            id=f"rb_{subject_id}_{role_name}_{scope}",
        )
        self._bindings.append(binding)
        logger.info("Assigned role %s to %s in scope %s", role_name, subject_id, scope)
        return binding

    def unassign_role(self, subject_id: str, role_name: str, scope: str) -> bool:
        """Remove a role assignment."""
        for binding in self._bindings:
            if (binding.subject_id == subject_id
                    and binding.role_name == role_name
                    and binding.scope == scope):
                self._bindings.remove(binding)
                return True
        return False

    def get_subject_roles(self, subject_id: str) -> List[RoleBinding]:
        """Get all role bindings for a subject."""
        return [b for b in self._bindings if b.subject_id == subject_id]

    def get_subject_permissions(
        self,
        subject_id: str,
        scope: str = "",
    ) -> Set[Permission]:
        """Get all permissions a subject has within a scope.

        Respects inherited roles and builds a union of all matching bindings.
        """
        perms: Set[Permission] = set()
        for binding in self._bindings:
            if binding.subject_id != subject_id:
                continue
            if scope and not binding.scope == scope and binding.scope != "global":
                continue
            role = self._roles.get(binding.role_name)
            if role:
                perms.update(role.permissions)
        return perms

    def check_access(
        self,
        subject_id: str,
        permission: Permission,
        scope: str = "",
    ) -> bool:
        """Check if a subject has a specific permission within a scope."""
        return permission in self.get_subject_permissions(subject_id, scope)

    def check_any_access(
        self,
        subject_id: str,
        permissions: List[Permission],
        scope: str = "",
    ) -> bool:
        """Check if a subject has at least one of the given permissions."""
        subject_perms = self.get_subject_permissions(subject_id, scope)
        return any(p in subject_perms for p in permissions)

    def has_role(self, subject_id: str, role_name: str, scope: str = "") -> bool:
        """Check if a subject has a specific role."""
        return any(
            b.subject_id == subject_id
            and b.role_name == role_name
            and (not scope or b.scope == scope or b.scope == "global")
            for b in self._bindings
        )
