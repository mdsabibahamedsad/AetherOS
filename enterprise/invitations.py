"""
Invitation Management
=====================

Manage invitations for users to join organizations, workspaces, and teams.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Invitation:
    """An invitation for a user to join an organization."""
    email: str
    organization_id: str
    id: str = field(default_factory=lambda: f"inv_{uuid.uuid4().hex[:12]}")
    inviter_id: str = ""
    role: str = "member"
    workspace_ids: List[str] = field(default_factory=list)
    team_ids: List[str] = field(default_factory=list)
    message: str = ""
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    token: str = ""

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = datetime.utcnow() + timedelta(days=7)
        if not self.token:
            self.token = uuid.uuid4().hex

    def accept(self) -> None:
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.utcnow()

    def decline(self) -> None:
        self.status = InvitationStatus.DECLINED

    def cancel(self) -> None:
        self.status = InvitationStatus.CANCELLED

    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "organization_id": self.organization_id,
            "role": self.role,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class InvitationManager:
    """Manage the lifecycle of invitations."""

    def __init__(self) -> None:
        self._invitations: Dict[str, Invitation] = {}

    def create(self, invitation: Invitation) -> Invitation:
        self._invitations[invitation.id] = invitation
        logger.info("Invitation created: %s → org %s", invitation.email, invitation.organization_id)
        return invitation

    def get(self, invitation_id: str) -> Optional[Invitation]:
        return self._invitations.get(invitation_id)

    def get_by_token(self, token: str) -> Optional[Invitation]:
        for inv in self._invitations.values():
            if inv.token == token:
                return inv
        return None

    def list_for_organization(self, org_id: str) -> List[Invitation]:
        return [i for i in self._invitations.values() if i.organization_id == org_id]

    def list_for_email(self, email: str) -> List[Invitation]:
        return [i for i in self._invitations.values() if i.email == email]

    def cancel(self, invitation_id: str) -> bool:
        inv = self._invitations.get(invitation_id)
        if inv and inv.status == InvitationStatus.PENDING:
            inv.cancel()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Mark expired invitations and return count."""
        count = 0
        for inv in self._invitations.values():
            if inv.status == InvitationStatus.PENDING and inv.is_expired():
                inv.status = InvitationStatus.EXPIRED
                count += 1
        return count
