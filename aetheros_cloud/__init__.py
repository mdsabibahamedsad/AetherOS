"""Aether Cloud — multi-device, multi-user workspace and collaboration layer."""

from __future__ import annotations

from aetheros_cloud.models import (
    CloudConfig, CloudMode, CloudProvider,
    Workspace, WorkspaceType, WorkspaceStatus, WorkspaceRole,
    Team, TeamMember, TeamRole,
    Project, ProjectStatus,
    SyncItem, SyncAction, SyncStatus, SyncConflict,
    RemoteTarget, RemoteStatus, RemoteProvider,
    ShareLink, SharePermission,
    AuditEntry,
    StorageBackend, StorageProvider,
    NotificationChannel, NotificationEvent,
)

from aetheros_cloud.workspace.manager import WorkspaceManager
from aetheros_cloud.team.manager import TeamManager
from aetheros_cloud.sync.engine import SyncEngine
from aetheros_cloud.remote.manager import RemoteManager
from aetheros_cloud.storage.base import StorageManager
from aetheros_cloud.audit.logger import AuditLogger
from aetheros_cloud.notifications.dispatcher import NotificationDispatcher
from aetheros_cloud.plugins.registry import CloudPluginRegistry
from aetheros_cloud.collaboration.presence import PresenceManager
from aetheros_cloud.api.router import CloudAPIRouter
from aetheros_cloud.cli.commands import CloudCLI

__all__ = [
    "CloudConfig", "CloudMode", "CloudProvider",
    "Workspace", "WorkspaceType", "WorkspaceStatus", "WorkspaceRole",
    "Team", "TeamMember", "TeamRole",
    "Project", "ProjectStatus",
    "SyncItem", "SyncAction", "SyncStatus", "SyncConflict",
    "RemoteTarget", "RemoteStatus", "RemoteProvider",
    "ShareLink", "SharePermission",
    "AuditEntry",
    "StorageBackend", "StorageProvider",
    "NotificationChannel", "NotificationEvent",
    "WorkspaceManager",
    "TeamManager",
    "SyncEngine",
    "RemoteManager",
    "StorageManager",
    "AuditLogger",
    "NotificationDispatcher",
    "CloudPluginRegistry",
    "PresenceManager",
    "CloudAPIRouter",
    "CloudCLI",
]

from aetheros_cloud.config import CloudConfigManager
