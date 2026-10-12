"""
Plugin Registration API
=======================

Provides the unified plugin registration API for all plugin types:

- register_plugin() - Register a generic plugin
- register_agent() - Register an AI agent
- register_tool() - Register a tool plugin
- register_workflow() - Register a workflow plugin
- register_mcp() - Register an MCP server
- register_sidebar() - Register a sidebar app
- register_dashboard() - Register a dashboard card
- register_theme() - Register a theme

Usage::

    from aetheros_developer_platform.plugin_api import PluginRegistry

    registry = PluginRegistry()

    @registry.register_plugin("my-plugin")
    def my_plugin(ctx):
        ctx.tools.register_tool(...)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins that can be registered."""
    PLUGIN = "plugin"
    AGENT = "agent"
    TOOL = "tool"
    WORKFLOW = "workflow"
    MCP = "mcp"
    SIDEBAR = "sidebar"
    DASHBOARD = "dashboard"
    THEME = "theme"
    UI_PANEL = "ui_panel"
    WIDGET = "widget"
    CONNECTOR = "connector"
    KNOWLEDGE_PROVIDER = "knowledge_provider"
    MEMORY_PROVIDER = "memory_provider"
    MODEL_PROVIDER = "model_provider"
    VOICE_SKILL = "voice_skill"
    AUTOMATION_ACTION = "automation_action"


@dataclass
class PluginRegistration:
    """A registered plugin entry."""
    name: str
    plugin_type: PluginType
    handler: Callable
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """Central registry for all plugin types.

    Usage::

        registry = PluginRegistry()

        # Register a generic plugin
        @registry.register_plugin("my-plugin")
        def my_plugin(ctx):
            pass

        # Register an agent
        @registry.register_agent("my-agent")
        def my_agent(ctx):
            pass

        # Register a tool
        @registry.register_tool("my-tool", description="Does something")
        def my_tool(args, **kwargs):
            return '{"result": "ok"}'

        # Register an MCP server
        @registry.register_mcp("my-mcp")
        def my_mcp(ctx):
            pass

        # Register a workflow
        @registry.register_workflow("my-workflow")
        def my_workflow(ctx):
            pass
    """

    def __init__(self) -> None:
        self._registrations: Dict[str, PluginRegistration] = {}
        self._by_type: Dict[PluginType, List[str]] = {t: [] for t in PluginType}

    def register_plugin(
        self,
        name: str,
        *,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
        permissions: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Callable:
        """Decorator to register a generic plugin.

        Args:
            name: Plugin name.
            version: Plugin version.
            description: Plugin description.
            author: Plugin author.
            permissions: Required permissions.
            dependencies: Required dependencies.
        """
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.PLUGIN,
                handler=func,
                version=version,
                description=description,
                author=author,
                permissions=permissions or [],
                dependencies=dependencies or [],
            )
            self._register(reg)
            return func
        return decorator

    def register_agent(
        self,
        name: str,
        *,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
    ) -> Callable:
        """Decorator to register an AI agent."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.AGENT,
                handler=func,
                version=version,
                description=description,
                author=author,
            )
            self._register(reg)
            return func
        return decorator

    def register_tool(
        self,
        name: str,
        *,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        toolset: str = "sdk",
    ) -> Callable:
        """Decorator to register a tool plugin."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.TOOL,
                handler=func,
                description=description,
                metadata={
                    "parameters": parameters or {},
                    "toolset": toolset,
                },
            )
            self._register(reg)
            return func
        return decorator

    def register_workflow(
        self,
        name: str,
        *,
        version: str = "0.1.0",
        description: str = "",
    ) -> Callable:
        """Decorator to register a workflow plugin."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.WORKFLOW,
                handler=func,
                version=version,
                description=description,
            )
            self._register(reg)
            return func
        return decorator

    def register_mcp(
        self,
        name: str,
        *,
        version: str = "0.1.0",
        description: str = "",
    ) -> Callable:
        """Decorator to register an MCP server."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.MCP,
                handler=func,
                version=version,
                description=description,
            )
            self._register(reg)
            return func
        return decorator

    def register_sidebar(
        self,
        name: str,
        *,
        title: str = "",
        icon: str = "",
        position: str = "left",
    ) -> Callable:
        """Decorator to register a sidebar app."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.SIDEBAR,
                handler=func,
                description=title,
                metadata={
                    "title": title,
                    "icon": icon,
                    "position": position,
                },
            )
            self._register(reg)
            return func
        return decorator

    def register_dashboard(
        self,
        name: str,
        *,
        title: str = "",
        size: str = "medium",
    ) -> Callable:
        """Decorator to register a dashboard card."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.DASHBOARD,
                handler=func,
                description=title,
                metadata={
                    "title": title,
                    "size": size,
                },
            )
            self._register(reg)
            return func
        return decorator

    def register_theme(
        self,
        name: str,
        *,
        config: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator to register a theme."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.THEME,
                handler=func,
                metadata={"config": config or {}},
            )
            self._register(reg)
            return func
        return decorator

    def register_knowledge_provider(
        self,
        name: str,
        *,
        provider_type: str = "vector",
    ) -> Callable:
        """Decorator to register a knowledge provider."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.KNOWLEDGE_PROVIDER,
                handler=func,
                metadata={"provider_type": provider_type},
            )
            self._register(reg)
            return func
        return decorator

    def register_memory_provider(
        self,
        name: str,
        *,
        backend: str = "memory",
    ) -> Callable:
        """Decorator to register a memory provider."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.MEMORY_PROVIDER,
                handler=func,
                metadata={"backend": backend},
            )
            self._register(reg)
            return func
        return decorator

    def register_model_provider(
        self,
        name: str,
        *,
        provider_type: str = "llm",
    ) -> Callable:
        """Decorator to register a model provider."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.MODEL_PROVIDER,
                handler=func,
                metadata={"provider_type": provider_type},
            )
            self._register(reg)
            return func
        return decorator

    def register_voice_skill(
        self,
        name: str,
        *,
        commands: Optional[List[str]] = None,
    ) -> Callable:
        """Decorator to register a voice skill."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.VOICE_SKILL,
                handler=func,
                metadata={"commands": commands or []},
            )
            self._register(reg)
            return func
        return decorator

    def register_automation_action(
        self,
        name: str,
        *,
        trigger: str = "",
    ) -> Callable:
        """Decorator to register an automation action."""
        def decorator(func: Callable) -> Callable:
            reg = PluginRegistration(
                name=name,
                plugin_type=PluginType.AUTOMATION_ACTION,
                handler=func,
                metadata={"trigger": trigger},
            )
            self._register(reg)
            return func
        return decorator

    def _register(self, registration: PluginRegistration) -> None:
        """Internal registration method."""
        self._registrations[registration.name] = registration
        self._by_type[registration.plugin_type].append(registration.name)
        logger.info(
            "Registered %s: %s",
            registration.plugin_type.value,
            registration.name,
        )

    def get(self, name: str) -> Optional[PluginRegistration]:
        """Get a plugin registration by name."""
        return self._registrations.get(name)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        enabled_only: bool = True,
    ) -> List[PluginRegistration]:
        """List all registered plugins."""
        if plugin_type:
            names = self._by_type.get(plugin_type, [])
            plugins = [self._registrations[n] for n in names if n in self._registrations]
        else:
            plugins = list(self._registrations.values())

        if enabled_only:
            plugins = [p for p in plugins if p.enabled]

        return plugins

    def enable(self, name: str) -> bool:
        """Enable a plugin."""
        reg = self._registrations.get(name)
        if reg:
            reg.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a plugin."""
        reg = self._registrations.get(name)
        if reg:
            reg.enabled = False
            return True
        return False

    def unregister(self, name: str) -> bool:
        """Unregister a plugin."""
        reg = self._registrations.pop(name, None)
        if reg:
            self._by_type[reg.plugin_type].remove(name)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        stats = {
            "total": len(self._registrations),
            "enabled": sum(1 for r in self._registrations.values() if r.enabled),
            "disabled": sum(1 for r in self._registrations.values() if not r.enabled),
            "by_type": {},
        }
        for plugin_type in PluginType:
            count = len(self._by_type.get(plugin_type, []))
            if count > 0:
                stats["by_type"][plugin_type.value] = count
        return stats


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Return the global PluginRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
