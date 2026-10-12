"""
User & Identity Management
==========================

Users, groups, service accounts, and API tokens for
enterprise identity and access management.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserStatus(enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"
    PENDING = "pending"


@dataclass
class User:
    """An enterprise user with identity and access properties."""
    username: str
    email: str
    id: str = field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    display_name: str = ""
    status: UserStatus = UserStatus.PENDING
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def activate(self) -> None:
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def disable(self) -> None:
        self.status = UserStatus.DISABLED
        self.updated_at = datetime.utcnow()

    def record_login(self) -> None:
        self.last_login = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "status": self.status.value,
            "roles": self.roles,
            "groups": self.groups,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class Group:
    """A named group of users for collective permission assignment."""
    name: str
    organization_id: str
    id: str = field(default_factory=lambda: f"grp_{uuid.uuid4().hex[:12]}")
    description: str = ""
    member_ids: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_member(self, user_id: str) -> None:
        if user_id not in self.member_ids:
            self.member_ids.append(user_id)

    def remove_member(self, user_id: str) -> bool:
        if user_id in self.member_ids:
            self.member_ids.remove(user_id)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "organization_id": self.organization_id,
            "member_count": len(self.member_ids),
            "roles": self.roles,
        }


@dataclass
class ServiceAccount:
    """A non-human identity for automated processes."""
    name: str
    organization_id: str
    id: str = field(default_factory=lambda: f"sa_{uuid.uuid4().hex[:12]}")
    description: str = ""
    roles: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "organization_id": self.organization_id,
            "enabled": self.enabled,
            "roles": self.roles,
        }


def _generate_token(prefix: str = "aet") -> str:
    """Generate a secure API token."""
    raw = secrets.token_urlsafe(48)
    return f"{prefix}_{raw}"


@dataclass
class APIToken:
    """An API token for programmatic access."""
    name: str
    owner_id: str
    id: str = field(default_factory=lambda: f"tok_{uuid.uuid4().hex[:12]}")
    token_hash: str = ""
    token_prefix: str = ""
    permissions: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    revoked: bool = False

    def generate(self) -> str:
        """Generate a new token value and store its hash.

        Returns the plaintext token (only shown once).
        """
        raw = _generate_token()
        self.token_prefix = raw[:12]
        self.token_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw

    def verify(self, token: str) -> bool:
        """Verify a token against the stored hash."""
        if self.revoked:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        computed = hashlib.sha256(token.encode()).hexdigest()
        return hmac.compare_digest(computed, self.token_hash)

    def revoke(self) -> None:
        self.revoked = True

    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
