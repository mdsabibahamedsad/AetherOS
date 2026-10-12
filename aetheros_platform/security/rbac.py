"""Role-Based Access Control — roles, permissions, policy evaluation."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

BUILTIN_ROLES = {
    "admin": {
        "description": "Full system access",
        "permissions": ["*"],
        "is_system": True,
    },
    "user": {
        "description": "Standard user access",
        "permissions": [
            "session:create", "session:read", "session:write",
            "agent:run", "agent:read",
            "workflow:run", "workflow:read",
            "tool:use",
            "knowledge:read",
            "dashboard:view",
        ],
        "is_system": True,
    },
    "developer": {
        "description": "Extended access for development",
        "permissions": [
            "session:*",
            "agent:*",
            "workflow:*",
            "plugin:install", "plugin:uninstall",
            "hub:*",
            "tool:use",
            "knowledge:*",
            "dashboard:*",
        ],
        "is_system": True,
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": [
            "session:read",
            "agent:read",
            "workflow:read",
            "knowledge:read",
            "dashboard:view",
        ],
        "is_system": True,
    },
}


class Permission:
    def __init__(self, action: str, resource: str = "*",
                 conditions: dict = None):
        self.action = action
        self.resource = resource
        self.conditions = conditions or {}

    def matches(self, action: str, resource: str) -> bool:
        return (self._match_action(action) and
                self._match_resource(resource))

    def _match_action(self, action: str) -> bool:
        if self.action == "*":
            return True
        parts = self.action.split(":")
        target = action.split(":")
        for i, p in enumerate(parts):
            if p == "*":
                return True
            if i >= len(target) or target[i] != p:
                return False
        return len(parts) == len(target)

    def _match_resource(self, resource: str) -> bool:
        if self.resource == "*":
            return True
        return self.resource == resource


@dataclass
class Role:
    name: str
    description: str = ""
    permissions: list[str] = field(default_factory=list)
    is_system: bool = False
    parent: Optional[str] = None


class RBACManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._roles: dict[str, Role] = {}
        self._init_db()
        self._load_roles()

    def _init_db(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rbac_roles (
                    name TEXT PRIMARY KEY,
                    description TEXT DEFAULT '',
                    permissions TEXT DEFAULT '[]',
                    is_system INTEGER DEFAULT 0,
                    parent TEXT
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rbac_user_roles (
                    user_id TEXT NOT NULL,
                    role_name TEXT NOT NULL,
                    PRIMARY KEY (user_id, role_name)
                )
            """)
            self._conn.commit()

    def _load_roles(self):
        for name, data in BUILTIN_ROLES.items():
            role = Role(name=name, description=data["description"],
                        permissions=data["permissions"],
                        is_system=data["is_system"])
            self._roles[name] = role
            try:
                with self._lock:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO rbac_roles "
                        "(name, description, permissions, is_system) "
                        "VALUES (?, ?, ?, ?)",
                        (name, data["description"],
                         json.dumps(data["permissions"]),
                         1 if data["is_system"] else 0))
                    self._conn.commit()
            except Exception:
                pass

    def create_role(self, name: str, description: str = "",
                     permissions: list[str] = None,
                     parent: str = None) -> Optional[Role]:
        if name in self._roles:
            return None
        role = Role(name=name, description=description,
                    permissions=permissions or [], parent=parent)
        self._roles[name] = role
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO rbac_roles "
                    "(name, description, permissions, is_system, parent) "
                    "VALUES (?, ?, ?, 0, ?)",
                    (name, description, json.dumps(permissions or []), parent))
                self._conn.commit()
        except Exception as e:
            logger.error("create_role error: %s", e)
        return role

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def list_roles(self) -> list[Role]:
        return list(self._roles.values())

    def update_role(self, name: str, permissions: list[str] = None,
                     description: str = None) -> bool:
        role = self._roles.get(name)
        if not role or role.is_system:
            return False
        if permissions is not None:
            role.permissions = permissions
        if description is not None:
            role.description = description
        try:
            with self._lock:
                self._conn.execute(
                    "UPDATE rbac_roles SET permissions=?, description=? WHERE name=?",
                    (json.dumps(role.permissions), role.description, name))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("update_role error: %s", e)
            return False

    def delete_role(self, name: str) -> bool:
        role = self._roles.get(name)
        if not role or role.is_system:
            return False
        self._roles.pop(name, None)
        try:
            with self._lock:
                self._conn.execute("DELETE FROM rbac_roles WHERE name=?", (name,))
                self._conn.execute("DELETE FROM rbac_user_roles WHERE role_name=?", (name,))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("delete_role error: %s", e)
            return False

    def assign_role(self, user_id: str, role_name: str) -> bool:
        role = self._roles.get(role_name)
        if not role:
            return False
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT OR IGNORE INTO rbac_user_roles (user_id, role_name) "
                    "VALUES (?, ?)", (user_id, role_name))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("assign_role error: %s", e)
            return False

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        try:
            with self._lock:
                self._conn.execute(
                    "DELETE FROM rbac_user_roles WHERE user_id=? AND role_name=?",
                    (user_id, role_name))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error("revoke_role error: %s", e)
            return False

    def get_user_roles(self, user_id: str) -> list[Role]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT role_name FROM rbac_user_roles WHERE user_id=?",
                (user_id,))
            return [self._roles.get(r[0]) for r in cur.fetchall() if r[0] in self._roles]

    def get_user_permissions(self, user_id: str) -> set[str]:
        permissions = set()
        roles = self.get_user_roles(user_id)
        for role in roles:
            permissions.update(role.permissions)
            if role.parent:
                parent = self._roles.get(role.parent)
                if parent:
                    permissions.update(parent.permissions)
        return permissions

    def check_permission(self, user_id: str, action: str,
                          resource: str = "*") -> bool:
        permissions = self.get_user_permissions(user_id)
        if "*" in permissions:
            return True
        for p in permissions:
            perm = Permission(p, resource)
            if perm.matches(action, resource):
                return True
        return False

    def check_any_permission(self, user_id: str,
                              actions: list[str]) -> bool:
        p = self.get_user_permissions(user_id)
        if "*" in p:
            return True
        for action in actions:
            perm = Permission(action)
            if any(perm.matches(action, r) for r in p):
                return True
        return False

    def get_inherited_permissions(self, role_name: str) -> set[str]:
        role = self._roles.get(role_name)
        if not role:
            return set()
        permissions = set(role.permissions)
        if role.parent:
            parent = self._roles.get(role.parent)
            if parent:
                permissions.update(parent.permissions)
                if parent.parent:
                    permissions.update(
                        self.get_inherited_permissions(parent.name))
        return permissions

    def get_stats(self) -> dict:
        return {
            "roles": len(self._roles),
            "system_roles": sum(1 for r in self._roles.values() if r.is_system),
            "custom_roles": sum(1 for r in self._roles.values() if not r.is_system),
        }
