"""Workspace manager — CRUD, lifecycle, membership."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_cloud.models import (
    Workspace, WorkspaceMember, WorkspaceType, WorkspaceStatus,
    WorkspaceRole, InviteCode, generate_id, now,
)
from aetheros_cloud.config import CloudConfigManager
from aetheros_cloud.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspace lifecycle, membership, and persistence.

    Uses SQLite via Hermes SessionDB when available, falls back to JSON file.
    """

    def __init__(
        self,
        config: Optional[CloudConfigManager] = None,
        audit: Optional[AuditLogger] = None,
        data_dir: Optional[Path] = None,
    ):
        self._config = config or CloudConfigManager()
        self._audit = audit
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "workspaces"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: Dict[str, Workspace] = {}
        self._active_workspace_id: Optional[str] = None

    # ── CRUD ────────────────────────────────────────────────────────

    def create_workspace(
        self,
        name: str,
        description: str = "",
        type: WorkspaceType = WorkspaceType.PERSONAL,
        owner_id: str = "",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Workspace:
        ws = Workspace(
            id=generate_id("ws"),
            name=name,
            description=description,
            type=type,
            owner_id=owner_id or self._config.get("user_id", ""),
            settings=settings or {},
            created_at=now(),
            updated_at=now(),
        )
        ws.members.append(WorkspaceMember(
            user_id=ws.owner_id,
            display_name="Owner",
            role=WorkspaceRole.OWNER,
            joined_at=now(),
        ))
        self._workspaces[ws.id] = ws
        self._persist(ws)
        self._audit_log("workspace.created", {"workspace_id": ws.id, "name": name})
        logger.info("Created workspace %s: %s", ws.id, name)
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            ws = self._load(workspace_id)
        return ws

    def list_workspaces(self, type_filter: Optional[WorkspaceType] = None) -> List[Workspace]:
        self._load_all()
        if type_filter:
            return [w for w in self._workspaces.values() if w.type == type_filter]
        return list(self._workspaces.values())

    def update_workspace(self, workspace_id: str, **kwargs) -> Optional[Workspace]:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return None
        for k, v in kwargs.items():
            if hasattr(ws, k) and k not in ("id", "created_at", "owner_id"):
                setattr(ws, k, v)
        ws.updated_at = now()
        self._persist(ws)
        self._audit_log("workspace.updated", {"workspace_id": workspace_id, "changes": list(kwargs.keys())})
        return ws

    def archive_workspace(self, workspace_id: str) -> bool:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return False
        ws.status = WorkspaceStatus.ARCHIVED
        ws.archived_at = now()
        ws.updated_at = now()
        self._persist(ws)
        self._audit_log("workspace.archived", {"workspace_id": workspace_id})
        return True

    def delete_workspace(self, workspace_id: str) -> bool:
        ws = self._workspaces.pop(workspace_id, None)
        if ws is None:
            return False
        self._remove_file(workspace_id)
        self._audit_log("workspace.deleted", {"workspace_id": workspace_id})
        return True

    # ── Membership ──────────────────────────────────────────────────

    def add_member(
        self, workspace_id: str, user_id: str,
        display_name: str = "", role: WorkspaceRole = WorkspaceRole.MEMBER,
    ) -> Optional[WorkspaceMember]:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return None
        member = WorkspaceMember(
            user_id=user_id,
            display_name=display_name or user_id,
            role=role,
            joined_at=now(),
        )
        ws.members.append(member)
        ws.updated_at = now()
        self._persist(ws)
        self._audit_log("workspace.member.added", {"workspace_id": workspace_id, "user_id": user_id})
        return member

    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return False
        ws.members = [m for m in ws.members if m.user_id != user_id]
        ws.updated_at = now()
        self._persist(ws)
        self._audit_log("workspace.member.removed", {"workspace_id": workspace_id, "user_id": user_id})
        return True

    def set_member_role(self, workspace_id: str, user_id: str, role: WorkspaceRole) -> bool:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return False
        for m in ws.members:
            if m.user_id == user_id:
                m.role = role
                ws.updated_at = now()
                self._persist(ws)
                self._audit_log("workspace.member.role_changed", {
                    "workspace_id": workspace_id, "user_id": user_id, "new_role": role.value,
                })
                return True
        return False

    def get_members(self, workspace_id: str) -> List[WorkspaceMember]:
        ws = self.get_workspace(workspace_id)
        return ws.members if ws else []

    def has_permission(self, workspace_id: str, user_id: str, required_role: WorkspaceRole) -> bool:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return False
        role_hierarchy = {
            WorkspaceRole.GUEST: 0,
            WorkspaceRole.MEMBER: 1,
            WorkspaceRole.DEVELOPER: 2,
            WorkspaceRole.MANAGER: 3,
            WorkspaceRole.ADMINISTRATOR: 4,
            WorkspaceRole.OWNER: 5,
        }
        for m in ws.members:
            if m.user_id == user_id:
                return role_hierarchy.get(m.role, 0) >= role_hierarchy.get(required_role, 0)
        return False

    # ── Active workspace ────────────────────────────────────────────

    @property
    def active_workspace(self) -> Optional[Workspace]:
        if self._active_workspace_id:
            return self.get_workspace(self._active_workspace_id)
        workspaces = self.list_workspaces()
        return workspaces[0] if workspaces else None

    def set_active_workspace(self, workspace_id: str) -> bool:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return False
        self._active_workspace_id = workspace_id
        self._config.update(workspace_id=workspace_id)
        return True

    # ── Invites ─────────────────────────────────────────────────────

    def create_invite(
        self, workspace_id: str, role: str = "member",
        max_uses: int = 0, expires_in: Optional[int] = None,
    ) -> Optional[InviteCode]:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            return None
        import uuid
        invite = InviteCode(
            id=generate_id("inv"),
            workspace_id=workspace_id,
            role=role,
            code=uuid.uuid4().hex[:12],
            created_by=self._config.get("user_id", ""),
            max_uses=max_uses,
            expires_at=(now() + expires_in) if expires_in else None,
            created_at=now(),
        )
        self._audit_log("workspace.invite.created", {"workspace_id": workspace_id, "code": invite.code[:8]})
        return invite

    def redeem_invite(self, code: str, user_id: str) -> Optional[Workspace]:
        return None  # TODO: load from shared backend

    # ── Persistence ─────────────────────────────────────────────────

    def _persist(self, ws: Workspace):
        path = self._data_dir / f"{ws.id}.json"
        import dataclasses
        from enum import Enum
        def _serialize(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: _serialize(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            return obj
        path.write_text(json.dumps(_serialize(ws), indent=2, default=str))

    def _load(self, workspace_id: str) -> Optional[Workspace]:
        path = self._data_dir / f"{workspace_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            ws = self._deserialize_workspace(data)
            self._workspaces[workspace_id] = ws
            return ws
        except Exception as e:
            logger.error("Failed to load workspace %s: %s", workspace_id, e)
            return None

    def _load_all(self):
        for path in self._data_dir.glob("*.json"):
            ws_id = path.stem
            if ws_id not in self._workspaces:
                self._load(ws_id)

    def _remove_file(self, workspace_id: str):
        path = self._data_dir / f"{workspace_id}.json"
        if path.exists():
            path.unlink()

    def _deserialize_workspace(self, data: dict) -> Workspace:
        members = []
        for m in data.get("members", []):
            role_val = m.get("role", "member")
            try:
                role = WorkspaceRole(role_val)
            except ValueError:
                role = WorkspaceRole.MEMBER
            members.append(WorkspaceMember(
                user_id=m.get("user_id", ""),
                email=m.get("email", ""),
                display_name=m.get("display_name", ""),
                role=role,
                joined_at=m.get("joined_at", 0.0),
                permissions=m.get("permissions", []),
                is_active=m.get("is_active", True),
            ))
        type_val = data.get("type", "personal")
        try:
            wtype = WorkspaceType(type_val)
        except ValueError:
            wtype = WorkspaceType.PERSONAL
        status_val = data.get("status", "active")
        try:
            wstatus = WorkspaceStatus(status_val)
        except ValueError:
            wstatus = WorkspaceStatus.ACTIVE
        return Workspace(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            type=wtype,
            status=wstatus,
            owner_id=data.get("owner_id", ""),
            members=members,
            settings=data.get("settings", {}),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            archived_at=data.get("archived_at"),
            max_members=data.get("max_members", 10),
            storage_quota=data.get("storage_quota", 1073741824),
            storage_used=data.get("storage_used", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def _audit_log(self, event: str, details: dict):
        if self._audit:
            self._audit.log(event=event, actor_id=self._config.get("user_id", ""), details=details)
