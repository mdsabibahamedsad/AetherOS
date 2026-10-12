"""
Workspace Management
====================

Workspaces provide isolated environments within an organization
for projects, teams, and deployments.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkspaceStatus(enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    ARCHIVED = "archived"


@dataclass
class WorkspaceSettings:
    """Workspace-level configuration."""
    allow_plugins: bool = True
    allow_terminal: bool = True
    allow_network: bool = True
    allow_browser: bool = True
    max_concurrent_sessions: int = 10
    session_timeout_minutes: int = 120
    retention_days: int = 90
    resource_quotas: Dict[str, int] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class Workspace:
    """An isolated workspace within an organization.

    Workspaces group related work — projects, teams, or environments —
    and apply their own settings and resource limits.
    """
    name: str
    organization_id: str
    id: str = field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:12]}")
    display_name: str = ""
    description: str = ""
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    settings: WorkspaceSettings = field(default_factory=WorkspaceSettings)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def freeze(self) -> None:
        """Freeze the workspace — no new sessions allowed."""
        self.status = WorkspaceStatus.FROZEN
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        """Archive the workspace."""
        self.status = WorkspaceStatus.ARCHIVED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "organization_id": self.organization_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkspaceStore:
    """Persistent store for workspaces."""

    def __init__(self) -> None:
        self._workspaces: Dict[str, Workspace] = {}

    def create(self, ws: Workspace) -> Workspace:
        if ws.id in self._workspaces:
            raise ValueError(f"Workspace {ws.id} already exists")
        self._workspaces[ws.id] = ws
        return ws

    def get(self, ws_id: str) -> Optional[Workspace]:
        return self._workspaces.get(ws_id)

    def list(self, org_id: Optional[str] = None) -> List[Workspace]:
        if org_id:
            return [w for w in self._workspaces.values() if w.organization_id == org_id]
        return list(self._workspaces.values())

    def delete(self, ws_id: str) -> bool:
        if ws_id in self._workspaces:
            del self._workspaces[ws_id]
            return True
        return False
