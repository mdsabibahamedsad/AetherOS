"""Core data models for the Aether Cloud layer."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ───────────────────────────────────────────────────────────────────

class CloudMode(Enum):
    LOCAL = "local"
    SELF_HOSTED = "self_hosted"
    OFFICIAL = "official"


class CloudProvider(Enum):
    OFFICIAL = "official"
    SELF_HOSTED = "self_hosted"
    CUSTOM = "custom"


class WorkspaceType(Enum):
    PERSONAL = "personal"
    TEAM = "team"
    ORGANIZATION = "organization"
    ENTERPRISE = "enterprise"
    TEMPORARY = "temporary"
    GUEST = "guest"


class WorkspaceStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class WorkspaceRole(Enum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    DEVELOPER = "developer"
    MEMBER = "member"
    GUEST = "guest"


class TeamRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class ProjectStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SyncAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CONFLICT = "conflict"


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


class RemoteProvider(Enum):
    SSH = "ssh"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CLOUD_VM = "cloud_vm"
    MODAL = "modal"
    CUSTOM = "custom"


class RemoteStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TERMINATED = "terminated"


class SharePermission(Enum):
    READ = "read"
    EDIT = "edit"
    ADMIN = "admin"


class StorageProvider(Enum):
    LOCAL = "local"
    AETHER_CLOUD = "aether_cloud"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    S3 = "s3"
    CLOUDFLARE_R2 = "cloudflare_r2"
    AZURE_BLOB = "azure_blob"


class NotificationChannel(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationEvent(Enum):
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    MEMBER_JOINED = "member.joined"
    MEMBER_LEFT = "member.left"
    SHARE_CREATED = "share.created"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    AUDIT_ALERT = "audit.alert"
    SYSTEM_ALERT = "system.alert"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    MENTION = "mention"
    COMMENT = "comment"


# ── Core Data Classes ───────────────────────────────────────────────────────


@dataclass
class CloudConfig:
    mode: CloudMode = CloudMode.LOCAL
    provider: CloudProvider = CloudProvider.CUSTOM
    endpoint: str = ""
    api_key: str = ""
    workspace_id: str = ""
    user_id: str = ""
    sync_interval: int = 30
    offline_mode: bool = True
    auto_sync: bool = True
    conflict_strategy: str = "last_write_wins"
    encryption_enabled: bool = True


@dataclass
class Workspace:
    id: str = ""
    name: str = ""
    description: str = ""
    type: WorkspaceType = WorkspaceType.PERSONAL
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    owner_id: str = ""
    members: List[WorkspaceMember] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    archived_at: Optional[float] = None
    max_members: int = 10
    storage_quota: int = 1073741824  # 1 GB
    storage_used: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceMember:
    user_id: str = ""
    email: str = ""
    display_name: str = ""
    role: WorkspaceRole = WorkspaceRole.MEMBER
    joined_at: float = 0.0
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class Team:
    id: str = ""
    name: str = ""
    description: str = ""
    workspace_id: str = ""
    members: List[TeamMember] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    settings: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class TeamMember:
    user_id: str = ""
    email: str = ""
    display_name: str = ""
    role: TeamRole = TeamRole.MEMBER
    joined_at: float = 0.0
    permissions: List[str] = field(default_factory=list)


@dataclass
class Project:
    id: str = ""
    name: str = ""
    description: str = ""
    workspace_id: str = ""
    team_id: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    owner_id: str = ""
    template: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    archived_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncItem:
    id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    action: SyncAction = SyncAction.CREATE
    status: SyncStatus = SyncStatus.PENDING
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    checksum: str = ""
    created_at: float = 0.0
    synced_at: Optional[float] = None
    device_id: str = ""
    workspace_id: str = ""


@dataclass
class SyncConflict:
    id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    local_version: int = 0
    remote_version: int = 0
    local_data: Dict[str, Any] = field(default_factory=dict)
    remote_data: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: float = 0.0
    resolved_at: Optional[float] = None
    resolved_by: str = ""


@dataclass
class RemoteTarget:
    id: str = ""
    name: str = ""
    provider: RemoteProvider = RemoteProvider.SSH
    host: str = ""
    port: int = 22
    username: str = ""
    key_path: str = ""
    status: RemoteStatus = RemoteStatus.DISCONNECTED
    workspace_id: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    last_seen: Optional[float] = None


@dataclass
class ShareLink:
    id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    permission: SharePermission = SharePermission.READ
    created_by: str = ""
    workspace_id: str = ""
    expires_at: Optional[float] = None
    is_revoked: bool = False
    code: str = ""
    created_at: float = 0.0
    access_count: int = 0


@dataclass
class AuditEntry:
    id: str = ""
    event: str = ""
    actor_id: str = ""
    actor_type: str = ""
    target_type: str = ""
    target_id: str = ""
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    workspace_id: str = ""
    severity: str = "info"
    created_at: float = 0.0


@dataclass
class StorageBackend:
    id: str = ""
    provider: StorageProvider = StorageProvider.LOCAL
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    workspace_id: str = ""
    is_primary: bool = False
    created_at: float = 0.0
    last_verified: Optional[float] = None


@dataclass
class DeploymentRecord:
    id: str = ""
    name: str = ""
    entity_type: str = ""
    entity_id: str = ""
    target_id: str = ""
    status: str = "pending"
    config: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: Optional[float] = None
    workspace_id: str = ""
    deployed_by: str = ""


@dataclass
class CollaborationSession:
    id: str = ""
    workspace_id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    participants: List[str] = field(default_factory=list)
    cursors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    is_live: bool = False
    created_at: float = 0.0


@dataclass
class SharedKnowledge:
    id: str = ""
    workspace_id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    access_count: int = 0
    is_pinned: bool = False


@dataclass
class InviteCode:
    id: str = ""
    workspace_id: str = ""
    team_id: str = ""
    role: str = ""
    code: str = ""
    created_by: str = ""
    max_uses: int = 0
    use_count: int = 0
    expires_at: Optional[float] = None
    is_revoked: bool = False
    created_at: float = 0.0


def generate_id(prefix: str = "") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now() -> float:
    return time.time()


# Shared knowledge store types that sync across devices
SYNCABLE_TYPES = [
    "project",
    "setting",
    "knowledge",
    "memory",
    "plugin",
    "agent",
    "task",
    "workflow",
    "theme",
    "preference",
    "document",
    "note",
    "collection",
]
