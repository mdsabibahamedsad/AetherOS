"""Granular permission system — every plugin/MCP/skill requests permissions upfront."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from hub.models import Permission

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    ALWAYS = "always"
    ASK = "ask"
    SESSION = "session"


@dataclass
class PermissionGrant:
    item_id: str
    permission: Permission
    level: PermissionLevel
    granted_at: str = ""
    reason: str = ""


class PermissionManager:
    """Manages permission requests, grants, and prompts for the user."""

    def __init__(self, store=None):
        from hub.store import HubStore
        self.store = store or HubStore()
        self._grants: dict[str, list[PermissionGrant]] = {}
        self._session_grants: dict[str, set[str]] = {}
        self._load_grants()

    def _load_grants(self):
        stored = self.store.get_setting("permission_grants", "{}")
        try:
            data = json.loads(stored)
            for item_id, grants in data.items():
                self._grants[item_id] = [
                    PermissionGrant(**g) for g in grants
                ]
        except (json.JSONDecodeError, TypeError):
            pass

    def _save_grants(self):
        data = {}
        for item_id, grants in self._grants.items():
            data[item_id] = [
                {"item_id": g.item_id, "permission": g.permission.value,
                 "level": g.level.value, "granted_at": g.granted_at,
                 "reason": g.reason}
                for g in grants
            ]
        self.store.set_setting("permission_grants", json.dumps(data))

    def check_permission(self, item_id: str, permission: Permission) -> bool:
        """Check if an item has a given permission granted."""
        grants = self._grants.get(item_id, [])
        for g in grants:
            if g.permission == permission:
                if g.level in (PermissionLevel.GRANTED, PermissionLevel.ALWAYS):
                    return True
        session_perm = self._session_grants.get(item_id, set())
        if permission.value in session_perm:
            return True
        return False

    def request_permission(self, item_id: str, permission: Permission,
                           reason: str = "") -> bool:
        """Request a permission — checks store first, then asks user."""
        if self.check_permission(item_id, permission):
            return True
        if permission in self._get_always_approved():
            self.grant(item_id, permission, PermissionLevel.GRANTED, reason)
            return True
        logger.info("Permission needed: %s -> %s (reason: %s)",
                     item_id, permission.value, reason)
        granted = self._prompt_user(item_id, permission, reason)
        if granted:
            self.grant(item_id, permission, PermissionLevel.SESSION, reason)
        return granted

    def grant(self, item_id: str, permission: Permission,
              level: PermissionLevel = PermissionLevel.GRANTED,
              reason: str = "") -> None:
        grants = self._grants.setdefault(item_id, [])
        existing = next((g for g in grants if g.permission == permission), None)
        if existing:
            existing.level = level
            existing.reason = reason
        else:
            grants.append(PermissionGrant(
                item_id=item_id, permission=permission, level=level,
                granted_at=datetime.utcnow().isoformat() + "Z", reason=reason))
            if level == PermissionLevel.SESSION:
                self._session_grants.setdefault(item_id, set()).add(permission.value)
        self._save_grants()

    def revoke(self, item_id: str, permission: Optional[Permission] = None) -> None:
        if permission:
            grants = self._grants.get(item_id, [])
            self._grants[item_id] = [g for g in grants if g.permission != permission]
        else:
            self._grants.pop(item_id, None)
        self._session_grants.pop(item_id, None)
        self._save_grants()

    def get_grants(self, item_id: str) -> list[PermissionGrant]:
        return self._grants.get(item_id, [])

    def get_all_grants(self) -> dict[str, list[PermissionGrant]]:
        return dict(self._grants)

    def check_many(self, item_id: str,
                   permissions: list[Permission]) -> dict[str, bool]:
        return {p.value: self.check_permission(item_id, p) for p in permissions}

    def request_many(self, item_id: str,
                     permissions: list[Permission],
                     reasons: list[str] = None) -> dict[str, bool]:
        results = {}
        for i, p in enumerate(permissions):
            reason = reasons[i] if reasons and i < len(reasons) else ""
            results[p.value] = self.request_permission(item_id, p, reason)
        return results

    def _get_always_approved(self) -> set[Permission]:
        return {Permission.FILESYSTEM, Permission.NOTIFICATIONS}

    def get_permission_descriptions(self) -> dict[str, str]:
        return {
            "filesystem": "Read and write files on your device",
            "network": "Make network requests to external services",
            "terminal": "Execute terminal commands",
            "git": "Access Git repositories",
            "docker": "Manage Docker containers",
            "clipboard": "Read and write clipboard contents",
            "camera": "Access your camera",
            "microphone": "Access your microphone",
            "notifications": "Send desktop notifications",
            "browser": "Control your web browser",
            "email": "Read and send emails",
            "calendar": "Access your calendar",
            "memory": "Read and write agent memory",
            "mcp": "Access MCP servers",
            "ai_providers": "Access AI model providers",
            "audio": "Play and record audio",
            "screenshot": "Take screenshots",
            "keychain": "Access stored credentials",
            "usb": "Access USB devices",
            "bluetooth": "Access Bluetooth devices",
        }

    def _prompt_user(self, item_id: str, permission: Permission,
                     reason: str) -> bool:
        """Prompt user to approve a permission. Returns True if granted."""
        try:
            from cli import _cprint
            desc = self.get_permission_descriptions().get(
                permission.value, permission.value)
            _cprint(f"  🔐 {item_id} requests permission: {permission.value}")
            _cprint(f"     {desc}")
            if reason:
                _cprint(f"     Reason: {reason}")
            _cprint(f"     Allow? (y/N/s=session/a=always) ")
            response = input().strip().lower()
            return response in ("y", "yes", "s", "session", "a", "always")
        except Exception:
            return True

    def reset_all(self) -> None:
        self._grants.clear()
        self._session_grants.clear()
        self._save_grants()
