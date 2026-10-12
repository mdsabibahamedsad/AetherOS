"""
Extension Context
=================

``ExtensionContext`` is the runtime facade given to every SDK-based
extension. It provides stable access to:

- Plugin metadata
- Tools (register, dispatch)
- Events (publish, subscribe)
- Permissions (declare, check)
- Logging
- Configuration
- HTTP client (sandboxed)
- File system access (sandboxed)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from sdk.api import (
    AgentAPI,
    ClusterAPI,
    EngineeringAPI,
    EventAPI,
    InteractionAPI,
    MemoryAPI,
    PluginAPI,
    ToolAPI,
    WorkflowAPI,
)
from sdk.permissions import Permission, PermissionSet
from sdk.lifecycle import PluginLifecycle, get_lifecycle

logger = logging.getLogger(__name__)


@dataclass
class ExtensionManifest:
    """Read-only metadata about the extension itself."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    sdk_version: str = ""
    aetheros_version: str = ""
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    runtime_requirements: Dict[str, Any] = field(default_factory=dict)


class ExtensionContext:
    """Runtime context provided to every SDK-based extension.

    This is the **primary interface** between extension code and the
    Aetheros runtime. Extensions receive an instance in their
    ``register(ctx)`` function.

    Usage::

        def register(ctx):
            # ctx.tools — register tools
            # ctx.events — publish/subscribe events
            # ctx.permissions — declare needed permissions
            # ctx.plugins — query other plugins
            # ctx.log — structured logging
    """

    def __init__(
        self,
        manifest: ExtensionManifest,
        extension_dir: Path,
        *,
        sandbox_enabled: bool = True,
    ) -> None:
        self._manifest = manifest
        self._extension_dir = extension_dir
        self._sandbox_enabled = sandbox_enabled
        self._permissions_granted: PermissionSet = PermissionSet()
        self._lifecycle: PluginLifecycle = get_lifecycle(manifest.name)

        # Initialize API facades
        self._plugin_api = PluginAPI(self)
        self._tool_api = ToolAPI(self)
        self._event_api = EventAPI(self)
        self._workflow_api = WorkflowAPI(self)
        self._agent_api = AgentAPI(self)
        self._memory_api = MemoryAPI(self)
        self._interaction_api = InteractionAPI(self)
        self._engineering_api = EngineeringAPI(self)
        self._cluster_api = ClusterAPI(self)

    # -- Manifest ------------------------------------------------------------

    @property
    def manifest(self) -> ExtensionManifest:
        """Read-only manifest for this extension."""
        return self._manifest

    @property
    def name(self) -> str:
        """Shortcut for ``manifest.name``."""
        return self._manifest.name

    @property
    def extension_dir(self) -> Path:
        """The directory where this extension is installed."""
        return self._extension_dir

    # -- Lifecycle -----------------------------------------------------------

    @property
    def lifecycle(self) -> PluginLifecycle:
        """Lifecycle manager for this extension."""
        return self._lifecycle

    # -- API facades ---------------------------------------------------------

    @property
    def plugins(self) -> PluginAPI:
        """Query plugin registry."""
        return self._plugin_api

    @property
    def tools(self) -> ToolAPI:
        """Register and query tools."""
        return self._tool_api

    @property
    def events(self) -> EventAPI:
        """Publish and subscribe to events."""
        return self._event_api

    @property
    def workflows(self) -> WorkflowAPI:
        """Define and execute workflows."""
        return self._workflow_api

    @property
    def agent(self) -> AgentAPI:
        """Interact with the running agent."""
        return self._agent_api

    @property
    def memory(self) -> MemoryAPI:
        """Access the memory system."""
        return self._memory_api

    @property
    def interaction(self) -> InteractionAPI:
        """Respond to user interactions."""
        return self._interaction_api

    @property
    def engineering(self) -> EngineeringAPI:
        """Access engineering subsystem."""
        return self._engineering_api

    @property
    def cluster(self) -> ClusterAPI:
        """Interact with agent clusters."""
        return self._cluster_api

    # -- Permissions ---------------------------------------------------------

    @property
    def permissions(self) -> PermissionSet:
        """Declared and granted permissions for this extension.

        Read-only from the extension's perspective — permissions are
        granted by the user at install time or through policy.
        """
        return self._permissions_granted

    def request_permission(self, permission: Permission) -> bool:
        """Request a specific permission at runtime.

        Returns True if the permission is granted, False if denied.
        In sandboxed mode, this triggers a user prompt for new permissions.
        """
        if self._permissions_granted.has(permission):
            return True
        # Permission not granted — request it
        from sdk.permissions import PermissionAudit
        audit = PermissionAudit()
        granted = audit.request(self._manifest.name, permission)
        if granted:
            self._permissions_granted = self._permissions_granted.union(
                PermissionSet([permission])
            )
        return granted

    # -- Logging -------------------------------------------------------------

    def log(self, level: str, message: str, **kwargs) -> None:
        """Structured logging with extension context.

        *level* is one of ``"debug"``, ``"info"``, ``"warning"``, ``"error"``.
        """
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn("[%s] %s", self._manifest.name, message, extra={"extension": self._manifest.name, **kwargs})

    def log_info(self, message: str, **kwargs) -> None:
        self.log("info", message, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        self.log("warning", message, **kwargs)

    def log_error(self, message: str, **kwargs) -> None:
        self.log("error", message, **kwargs)

    def log_debug(self, message: str, **kwargs) -> None:
        self.log("debug", message, **kwargs)

    # -- Configuration -------------------------------------------------------

    def get_config(self, key: str, default: Any = None) -> Any:
        """Read a config value for this extension.

        Config is read from ``config.yaml`` under
        ``extensions.<name>.<key>``.
        """
        try:
            from aetheros_cli.config import load_config
            config = load_config()
            ext_cfg = config.get("extensions", {}).get(self._manifest.name, {})
            return ext_cfg.get(key, default)
        except Exception:
            return default

    # -- HTTP client (sandboxed) ---------------------------------------------

    def http_get(self, url: str, timeout: float = 30.0) -> Optional[str]:
        """Make a sandboxed HTTP GET request.

        Requires the ``network`` permission.
        """
        if not self.request_permission(Permission("network")):
            logger.warning(
                "Extension '%s' denied: HTTP request requires 'network' permission",
                self._manifest.name,
            )
            return None
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Extension '%s' HTTP GET failed: %s", self._manifest.name, exc)
            return None

    # -- File system access (sandboxed) -------------------------------------

    def read_file(self, path: str) -> Optional[str]:
        """Read a file within the extension's sandbox directory.

        Requires the ``filesystem:read`` permission.
        Paths are resolved relative to the extension directory.
        Absolute paths or ``..`` traversal are rejected.
        """
        if not self.request_permission(Permission("filesystem:read")):
            logger.warning("Extension '%s' denied: file read requires 'filesystem:read' permission", self._manifest.name)
            return None
        resolved = self._resolve_sandbox_path(path)
        if resolved is None:
            return None
        try:
            return resolved.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Extension '%s' read_file failed: %s", self._manifest.name, exc)
            return None

    def write_file(self, path: str, content: str) -> bool:
        """Write a file within the extension's sandbox directory.

        Requires the ``filesystem:write`` permission.
        """
        if not self.request_permission(Permission("filesystem:write")):
            logger.warning("Extension '%s' denied: file write requires 'filesystem:write' permission", self._manifest.name)
            return False
        resolved = self._resolve_sandbox_path(path)
        if resolved is None:
            return False
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return True
        except Exception as exc:
            logger.warning("Extension '%s' write_file failed: %s", self._manifest.name, exc)
            return False

    def _resolve_sandbox_path(self, path: str) -> Optional[Path]:
        """Resolve a path safely within the extension sandbox.

        Returns None if the path escapes the sandbox.
        """
        candidate = (self._extension_dir / path).resolve()
        try:
            candidate.relative_to(self._extension_dir)
        except ValueError:
            logger.warning(
                "Extension '%s' attempted path traversal: %s -> %s",
                self._manifest.name, path, candidate,
            )
            return None
        return candidate

    # -- Tool registration (delegates to PluginContext) ----------------------

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        requires_env: Optional[list] = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        override: bool = False,
    ) -> None:
        """Register a tool. Delegates to the global tool registry.

        Thin wrapper matching the ``PluginContext`` interface for
        backward compatibility.
        """
        from tools.registry import registry
        registry.register(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env,
            is_async=is_async,
            description=description,
            emoji=emoji,
            override=override,
        )
        logger.debug("Extension '%s' registered tool: %s", self._manifest.name, name)
