"""Team manager — team CRUD, membership, role management."""

from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_cloud.models import (
    Team, TeamMember, TeamRole, WorkspaceRole,
    generate_id, now,
)
from aetheros_cloud.config import CloudConfigManager
from aetheros_cloud.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


class TeamManager:
    """Manages teams within workspaces."""

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
            self._data_dir = get_aetheros_home() / "cloud" / "teams"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._teams: Dict[str, Team] = {}

    # ── CRUD ────────────────────────────────────────────────────────

    def create_team(
        self,
        name: str,
        workspace_id: str,
        description: str = "",
        owner_id: str = "",
    ) -> Team:
        team = Team(
            id=generate_id("team"),
            name=name,
            description=description,
            workspace_id=workspace_id,
            created_at=now(),
            updated_at=now(),
        )
        team.members.append(TeamMember(
            user_id=owner_id or self._config.get("user_id", ""),
            display_name="Owner",
            role=TeamRole.OWNER,
            joined_at=now(),
        ))
        self._teams[team.id] = team
        self._persist(team)
        self._log_audit("team.created", {"team_id": team.id, "name": name, "workspace_id": workspace_id})
        logger.info("Created team %s in workspace %s", team.id, workspace_id)
        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        team = self._teams.get(team_id)
        if team is None:
            team = self._load(team_id)
        return team

    def list_teams(self, workspace_id: Optional[str] = None) -> List[Team]:
        self._load_all()
        if workspace_id:
            return [t for t in self._teams.values() if t.workspace_id == workspace_id]
        return list(self._teams.values())

    def update_team(self, team_id: str, **kwargs) -> Optional[Team]:
        team = self.get_team(team_id)
        if team is None:
            return None
        for k, v in kwargs.items():
            if hasattr(team, k) and k not in ("id", "created_at", "workspace_id"):
                setattr(team, k, v)
        team.updated_at = now()
        self._persist(team)
        self._log_audit("team.updated", {"team_id": team_id, "changes": list(kwargs.keys())})
        return team

    def delete_team(self, team_id: str) -> bool:
        team = self._teams.pop(team_id, None)
        if team is None:
            return False
        path = self._data_dir / f"{team_id}.json"
        if path.exists():
            path.unlink()
        self._log_audit("team.deleted", {"team_id": team_id})
        return True

    # ── Membership ──────────────────────────────────────────────────

    def add_member(self, team_id: str, user_id: str, display_name: str = "",
                   role: TeamRole = TeamRole.MEMBER) -> Optional[TeamMember]:
        team = self.get_team(team_id)
        if team is None:
            return None
        member = TeamMember(
            user_id=user_id,
            display_name=display_name or user_id,
            role=role,
            joined_at=now(),
        )
        team.members.append(member)
        team.updated_at = now()
        self._persist(team)
        self._log_audit("team.member.added", {"team_id": team_id, "user_id": user_id})
        return member

    def remove_member(self, team_id: str, user_id: str) -> bool:
        team = self.get_team(team_id)
        if team is None:
            return False
        team.members = [m for m in team.members if m.user_id != user_id]
        team.updated_at = now()
        self._persist(team)
        self._log_audit("team.member.removed", {"team_id": team_id, "user_id": user_id})
        return True

    def set_member_role(self, team_id: str, user_id: str, role: TeamRole) -> bool:
        team = self.get_team(team_id)
        if team is None:
            return False
        for m in team.members:
            if m.user_id == user_id:
                m.role = role
                team.updated_at = now()
                self._persist(team)
                self._log_audit("team.member.role_changed", {
                    "team_id": team_id, "user_id": user_id, "new_role": role.value,
                })
                return True
        return False

    def get_members(self, team_id: str) -> List[TeamMember]:
        team = self.get_team(team_id)
        return team.members if team else []

    def has_permission(self, team_id: str, user_id: str, required_role: TeamRole) -> bool:
        team = self.get_team(team_id)
        if team is None:
            return False
        hierarchy = {TeamRole.VIEWER: 0, TeamRole.MEMBER: 1, TeamRole.MANAGER: 2, TeamRole.ADMIN: 3, TeamRole.OWNER: 4}
        for m in team.members:
            if m.user_id == user_id:
                return hierarchy.get(m.role, 0) >= hierarchy.get(required_role, 0)
        return False

    # ── Persistence ─────────────────────────────────────────────────

    def _persist(self, team: Team):
        path = self._data_dir / f"{team.id}.json"
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        path.write_text(json.dumps(ser(team), indent=2, default=str))

    def _load(self, team_id: str) -> Optional[Team]:
        path = self._data_dir / f"{team_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            members = []
            for m in data.get("members", []):
                try:
                    role = TeamRole(m.get("role", "member"))
                except ValueError:
                    role = TeamRole.MEMBER
                members.append(TeamMember(
                    user_id=m.get("user_id", ""),
                    email=m.get("email", ""),
                    display_name=m.get("display_name", ""),
                    role=role,
                    joined_at=m.get("joined_at", 0.0),
                    permissions=m.get("permissions", []),
                ))
            team = Team(
                id=data.get("id", ""),
                name=data.get("name", ""),
                description=data.get("description", ""),
                workspace_id=data.get("workspace_id", ""),
                members=members,
                created_at=data.get("created_at", 0.0),
                updated_at=data.get("updated_at", 0.0),
                settings=data.get("settings", {}),
                tags=data.get("tags", []),
            )
            self._teams[team_id] = team
            return team
        except Exception as e:
            logger.error("Failed to load team %s: %s", team_id, e)
            return None

    def _load_all(self):
        for path in self._data_dir.glob("*.json"):
            tid = path.stem
            if tid not in self._teams:
                self._load(tid)

    def _log_audit(self, event: str, details: dict):
        if self._audit:
            self._audit.log(event=event, actor_id=self._config.get("user_id", ""), details=details)
