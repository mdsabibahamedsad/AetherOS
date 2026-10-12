"""Cloud plugin registry — workspace, team, org, and cloud service modules."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from aetheros_cloud.models import WorkspaceType

logger = logging.getLogger(__name__)


class CloudPlugin:
    """Base class for cloud plugins."""

    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    workspace_types: List[WorkspaceType] = []
    dependencies: List[str] = []

    def on_load(self, registry: "CloudPluginRegistry"):
        """Called when plugin is registered."""

    def on_unload(self):
        """Called when plugin is removed."""


class CloudPluginRegistry:
    """Registry for cloud plugins that extend workspace/team/org capabilities.

    Follows the same pattern as the existing Hermes plugin system
    (aetheros_cli/plugins.py) but scoped to cloud-layer extensions.
    """

    def __init__(self):
        self._plugins: Dict[str, CloudPlugin] = {}
        self._storage_handlers: Dict[str, Callable] = {}
        self._auth_handlers: Dict[str, Callable] = {}
        self._sync_handlers: Dict[str, Callable] = {}
        self._webhook_handlers: Dict[str, List[Callable]] = {}
        self._api_routes: List[Dict[str, Any]] = []
        self._init_builtin_plugins()

    def register(self, plugin: CloudPlugin):
        if plugin.name in self._plugins:
            logger.warning("Plugin %s already registered; skipping", plugin.name)
            return
        self._plugins[plugin.name] = plugin
        plugin.on_load(self)
        logger.info("Registered cloud plugin: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str):
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.on_unload()
            logger.info("Unregistered cloud plugin: %s", name)

    def get_plugin(self, name: str) -> Optional[CloudPlugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[CloudPlugin]:
        return list(self._plugins.values())

    def register_storage_handler(self, provider: str, handler: Callable):
        self._storage_handlers[provider] = handler

    def get_storage_handler(self, provider: str) -> Optional[Callable]:
        return self._storage_handlers.get(provider)

    def register_auth_handler(self, provider: str, handler: Callable):
        self._auth_handlers[provider] = handler

    def get_auth_handler(self, provider: str) -> Optional[Callable]:
        return self._auth_handlers.get(provider)

    def register_sync_handler(self, entity_type: str, handler: Callable):
        self._sync_handlers[entity_type] = handler

    def get_sync_handler(self, entity_type: str) -> Optional[Callable]:
        return self._sync_handlers.get(entity_type)

    def register_webhook(self, event: str, handler: Callable):
        self._webhook_handlers.setdefault(event, []).append(handler)

    def dispatch_webhook(self, event: str, data: dict):
        for handler in self._webhook_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error("Webhook handler failed for %s: %s", event, e)

    def register_api_route(self, method: str, path: str, handler: Callable, auth_required: bool = True):
        self._api_routes.append({
            "method": method,
            "path": path,
            "handler": handler,
            "auth_required": auth_required,
        })

    def get_api_routes(self) -> List[Dict[str, Any]]:
        return list(self._api_routes)

    # ── Built-in plugin: Virtual Collaboration ─────────────────────

    def _init_builtin_plugins(self):
        class _CollaborationPlugin(CloudPlugin):
            name = "virtual_collaboration"
            description = "Real-time collaboration: presence, cursors, live editing"
            version = "1.0.0"
            workspace_types = [WorkspaceType.TEAM, WorkspaceType.ORGANIZATION, WorkspaceType.ENTERPRISE]

        class _RemoteExecPlugin(CloudPlugin):
            name = "remote_execution"
            description = "Remote execution: SSH, Docker, K8s, Cloud VM agents"
            version = "1.0.0"
            workspace_types = [WorkspaceType.PERSONAL, WorkspaceType.TEAM, WorkspaceType.ORGANIZATION]

        class _StoragePlugin(CloudPlugin):
            name = "cloud_storage"
            description = "Multi-backend cloud storage (S3, R2, GDrive, Dropbox, Azure)"
            version = "1.0.0"
            workspace_types = list(WorkspaceType)

        class _AuditPlugin(CloudPlugin):
            name = "audit_trail"
            description = "Immutable audit logging for compliance and monitoring"
            version = "1.0.0"
            workspace_types = [WorkspaceType.ORGANIZATION, WorkspaceType.ENTERPRISE]

        for p in [_CollaborationPlugin(), _RemoteExecPlugin(), _StoragePlugin(), _AuditPlugin()]:
            self.register(p)
