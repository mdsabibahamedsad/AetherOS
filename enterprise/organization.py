"""
Organization Management
=======================

Organizations, workspaces, teams, projects, membership, and settings.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrganizationStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    PENDING = "pending"
    ARCHIVED = "archived"


class OrganizationRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    BILLING = "billing"


@dataclass
class OrganizationMember:
    """A member of an organization with their assigned role."""
    user_id: str
    email: str
    display_name: str = ""
    role: OrganizationRole = OrganizationRole.MEMBER
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[str] = None
    teams: List[str] = field(default_factory=list)
    permissions_override: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role.value,
            "joined_at": self.joined_at.isoformat(),
            "invited_by": self.invited_by,
            "teams": self.teams,
        }


@dataclass
class OrganizationSettings:
    """Organization-level configuration."""
    max_workspaces: int = 50
    max_teams: int = 100
    max_members: int = 500
    allow_guest_access: bool = False
    require_2fa: bool = False
    session_timeout_minutes: int = 480
    audit_retention_days: int = 365
    allowed_domains: List[str] = field(default_factory=list)
    sso_enabled: bool = False
    sso_provider: str = ""
    features: Dict[str, bool] = field(default_factory=dict)


@dataclass
class Organization:
    """Top-level organizational unit.

    An organization owns workspaces, teams, members, and configuration.
    """
    name: str
    id: str = field(default_factory=lambda: f"org_{uuid.uuid4().hex[:16]}")
    display_name: str = ""
    description: str = ""
    status: OrganizationStatus = OrganizationStatus.PENDING
    settings: OrganizationSettings = field(default_factory=OrganizationSettings)
    members: Dict[str, OrganizationMember] = field(default_factory=dict)
    workspace_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_member(
        self,
        user_id: str,
        email: str,
        role: OrganizationRole = OrganizationRole.MEMBER,
        invited_by: Optional[str] = None,
    ) -> OrganizationMember:
        """Add a member to the organization."""
        if user_id in self.members:
            raise ValueError(f"User {user_id} is already a member")
        member = OrganizationMember(
            user_id=user_id,
            email=email,
            role=role,
            invited_by=invited_by,
        )
        self.members[user_id] = member
        self.updated_at = datetime.utcnow()
        return member

    def remove_member(self, user_id: str) -> bool:
        """Remove a member from the organization."""
        if user_id not in self.members:
            return False
        del self.members[user_id]
        self.updated_at = datetime.utcnow()
        return True

    def get_member(self, user_id: str) -> Optional[OrganizationMember]:
        """Get a member by user ID."""
        return self.members.get(user_id)

    def has_member(self, user_id: str) -> bool:
        """Check if a user is a member."""
        return user_id in self.members

    def suspend(self) -> None:
        """Suspend the organization."""
        self.status = OrganizationStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the organization."""
        self.status = OrganizationStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        """Archive the organization."""
        self.status = OrganizationStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    def create_workspace(
        self,
        name: str,
        display_name: str = "",
        description: str = "",
    ) -> Any:
        """Create a workspace within this organization."""
        # Lazy import to avoid circular dependency
        from enterprise.workspace import Workspace
        ws = Workspace(
            name=name,
            organization_id=self.id,
            display_name=display_name or name,
            description=description,
        )
        self.workspace_ids.append(ws.id)
        self.updated_at = datetime.utcnow()
        return ws

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status.value,
            "member_count": len(self.members),
            "workspace_count": len(self.workspace_ids),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class OrganizationStore:
    """Persistent store for organizations.

    In-memory implementation for development. In production, this
    would back to a database via the kernel's state system.
    """

    def __init__(self) -> None:
        self._orgs: Dict[str, Organization] = {}

    def create(self, org: Organization) -> Organization:
        """Store a new organization."""
        if org.id in self._orgs:
            raise ValueError(f"Organization {org.id} already exists")
        self._orgs[org.id] = org
        logger.info("Created organization: %s (%s)", org.name, org.id)
        return org

    def get(self, org_id: str) -> Optional[Organization]:
        """Get an organization by ID."""
        return self._orgs.get(org_id)

    def get_by_name(self, name: str) -> Optional[Organization]:
        """Find an organization by name."""
        for org in self._orgs.values():
            if org.name == name:
                return org
        return None

    def list(self, status: Optional[OrganizationStatus] = None) -> List[Organization]:
        """List all organizations, optionally filtered by status."""
        if status:
            return [o for o in self._orgs.values() if o.status == status]
        return list(self._orgs.values())

    def update(self, org: Organization) -> None:
        """Update an existing organization."""
        if org.id not in self._orgs:
            raise ValueError(f"Organization {org.id} not found")
        org.updated_at = datetime.utcnow()
        self._orgs[org.id] = org

    def delete(self, org_id: str) -> bool:
        """Delete an organization."""
        if org_id not in self._orgs:
            return False
        del self._orgs[org_id]
        logger.info("Deleted organization: %s", org_id)
        return True
