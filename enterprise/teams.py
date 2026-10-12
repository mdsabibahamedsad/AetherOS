"""
Team Management
===============

Teams are groups of users within an organization that share
workspace access and permissions.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TeamRole(enum.Enum):
    LEAD = "lead"
    MEMBER = "member"


@dataclass
class TeamMember:
    """A member within a team with their team-specific role."""
    user_id: str
    role: TeamRole = TeamRole.MEMBER
    joined_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Team:
    """A named group of users within an organization."""
    name: str
    organization_id: str
    id: str = field(default_factory=lambda: f"team_{uuid.uuid4().hex[:12]}")
    display_name: str = ""
    description: str = ""
    members: Dict[str, TeamMember] = field(default_factory=dict)
    workspace_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def add_member(self, user_id: str, role: TeamRole = TeamRole.MEMBER) -> TeamMember:
        if user_id in self.members:
            raise ValueError(f"User {user_id} is already in team {self.name}")
        member = TeamMember(user_id=user_id, role=role)
        self.members[user_id] = member
        self.updated_at = datetime.utcnow()
        return member

    def remove_member(self, user_id: str) -> bool:
        if user_id not in self.members:
            return False
        del self.members[user_id]
        self.updated_at = datetime.utcnow()
        return True

    def add_workspace(self, workspace_id: str) -> None:
        if workspace_id not in self.workspace_ids:
            self.workspace_ids.append(workspace_id)
            self.updated_at = datetime.utcnow()

    def remove_workspace(self, workspace_id: str) -> None:
        if workspace_id in self.workspace_ids:
            self.workspace_ids.remove(workspace_id)
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "organization_id": self.organization_id,
            "member_count": len(self.members),
            "workspace_count": len(self.workspace_ids),
        }
