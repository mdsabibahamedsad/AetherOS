from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from aetheros_automation.models.models import Permission

logger = logging.getLogger(__name__)

_PERMISSIONS_DIR = os.path.expanduser("~/.aetheros/automation/permissions")
_PERMISSIONS_FILE = os.path.join(_PERMISSIONS_DIR, "permissions.json")


class PermissionManager:
    """Manage capability-level authorisations for the automation engine.

    Permissions are stored as a dict of ``resource → list[Grant]`` so that
    the same resource can be released by multiple permissions, or one
    permission can cover a whole resource namespace.
    """

    def __init__(self) -> None:
        os.makedirs(_PERMISSIONS_DIR, exist_ok=True)
        self._grants: dict[str, list[_Grant]] = {}
        self._pending: dict[str, _PendingPermission] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def request_permission(
        self,
        permission: Permission,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Request a new permission at runtime.

        If the permission has already been granted and is still valid the
        request is approved immediately.  Otherwise a pending entry is
        created that must be resolved via :meth:`grant`.
        """
        await self._ensure_loaded()

        resource = self._resolve_resource(permission, context)
        if self._is_granted(permission, resource):
            return True

        key = self._key(permission, resource)
        if key in self._pending:
            return False

        self._pending[key] = _PendingPermission(
            id=uuid.uuid4().hex[:12],
            permission=permission,
            resource=resource,
            context=context or {},
            created_at=time.time(),
        )
        await self._persist()
        logger.info(
            "Permission requested  permission=%s  resource=%s",
            permission.value,
            resource,
        )
        return False

    async def grant(
        self,
        permission: Permission,
        resource: str,
        duration: float | None = None,
    ) -> None:
        """Explicitly grant *permission* for *resource*.

        If *duration* is set (in seconds) the grant auto-expires after that
        window.
        """
        await self._ensure_loaded()

        key = self._key(permission, resource)
        self._pending.pop(key, None)

        now = time.time()
        grant = _Grant(
            id=uuid.uuid4().hex[:12],
            permission=permission,
            resource=resource,
            created_at=now,
            expires_at=(now + duration) if duration else None,
        )
        self._grants.setdefault(resource, []).append(grant)
        await self._persist()
        logger.info(
            "Permission granted  permission=%s  resource=%s  duration=%s",
            permission.value,
            resource,
            duration,
        )

    async def revoke(self, permission: Permission, resource: str) -> None:
        """Revoke a specific permission on *resource*."""
        await self._ensure_loaded()

        key = self._key(permission, resource)
        self._pending.pop(key, None)

        grants = self._grants.get(resource, [])
        self._grants[resource] = [
            g for g in grants
            if not (g.permission == permission and g.resource == resource)
        ]
        if not self._grants[resource]:
            self._grants.pop(resource, None)
        await self._persist()
        logger.info("Permission revoked  permission=%s  resource=%s", permission.value, resource)

    async def check(self, permission: Permission, resource: str) -> bool:
        """Return ``True`` if *permission* is currently valid for *resource*."""
        await self._ensure_loaded()
        return self._is_granted(permission, resource)

    async def list_granted(self) -> list[dict[str, Any]]:
        """Return every active grant as a list of dicts."""
        await self._ensure_loaded()
        result: list[dict[str, Any]] = []
        now = time.time()
        for resource, grants in self._grants.items():
            for g in grants:
                if g.expires_at and g.expires_at < now:
                    continue
                result.append({
                    "id": g.id,
                    "permission": g.permission.value,
                    "resource": g.resource,
                    "created_at": g.created_at,
                    "expires_at": g.expires_at,
                })
        return result

    async def list_pending(self) -> list[dict[str, Any]]:
        """Return every unresolved permission request."""
        await self._ensure_loaded()
        return [
            {
                "id": p.id,
                "permission": p.permission.value,
                "resource": p.resource,
                "context": p.context,
                "created_at": p.created_at,
            }
            for p in self._pending.values()
        ]

    async def revoke_all(self) -> None:
        """Revoke every active grant and clear pending requests."""
        self._grants.clear()
        self._pending.clear()
        await self._persist()
        logger.info("All permissions revoked")

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _is_granted(self, permission: Permission, resource: str) -> bool:
        now = time.time()
        grants = self._grants.get(resource, [])
        for g in grants:
            if g.permission != permission:
                continue
            if g.expires_at and g.expires_at < now:
                continue
            return True
        return False

    @staticmethod
    def _key(permission: Permission, resource: str) -> str:
        return f"{permission.value}:{resource}"

    @staticmethod
    def _resolve_resource(permission: Permission, context: dict[str, Any] | None) -> str:
        """Derive a resource path from the permission and context."""
        if context and "resource" in context:
            return context["resource"]
        return permission.value

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load)

    def _load(self) -> None:
        if not os.path.isfile(_PERMISSIONS_FILE):
            return
        try:
            with open(_PERMISSIONS_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            logger.exception("Failed to load permissions")
            return

        for raw in data.get("grants", []):
            try:
                perm = Permission(raw["permission"])
            except ValueError:
                continue
            g = _Grant(
                id=raw.get("id", uuid.uuid4().hex[:12]),
                permission=perm,
                resource=raw.get("resource", ""),
                created_at=raw.get("created_at", 0.0),
                expires_at=raw.get("expires_at"),
            )
            self._grants.setdefault(g.resource, []).append(g)

        for raw in data.get("pending", []):
            try:
                perm = Permission(raw["permission"])
            except ValueError:
                continue
            p = _PendingPermission(
                id=raw.get("id", uuid.uuid4().hex[:12]),
                permission=perm,
                resource=raw.get("resource", ""),
                context=raw.get("context", {}),
                created_at=raw.get("created_at", 0.0),
            )
            self._pending[self._key(p.permission, p.resource)] = p

    async def _persist(self) -> None:
        data: dict[str, Any] = {
            "grants": [
                {
                    "id": g.id,
                    "permission": g.permission.value,
                    "resource": g.resource,
                    "created_at": g.created_at,
                    "expires_at": g.expires_at,
                }
                for grants in self._grants.values()
                for g in grants
            ],
            "pending": [
                {
                    "id": p.id,
                    "permission": p.permission.value,
                    "resource": p.resource,
                    "context": p.context,
                    "created_at": p.created_at,
                }
                for p in self._pending.values()
            ],
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_json, _PERMISSIONS_FILE, data)


class _Grant:
    __slots__ = ("id", "permission", "resource", "created_at", "expires_at")

    def __init__(
        self,
        id: str,
        permission: Permission,
        resource: str,
        created_at: float,
        expires_at: float | None,
    ) -> None:
        self.id = id
        self.permission = permission
        self.resource = resource
        self.created_at = created_at
        self.expires_at = expires_at


class _PendingPermission:
    __slots__ = ("id", "permission", "resource", "context", "created_at")

    def __init__(
        self,
        id: str,
        permission: Permission,
        resource: str,
        context: dict[str, Any],
        created_at: float,
    ) -> None:
        self.id = id
        self.permission = permission
        self.resource = resource
        self.context = context
        self.created_at = created_at


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
