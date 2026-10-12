"""
Agent Registry — component/agent/tool registry for the AetherOS Kernel.

Maintains a runtime-queryable catalog of:
  - Registered agents and their capabilities
  - Available tools (from tools/registry, MCP, plugins)
  - Active plugins
  - MCP servers
  - Model providers

Allows runtime discovery — components can find each other without
hard-coded references.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


@dataclass
class ComponentEntry:
    """Entry for a registered component in the kernel registry.

    Attributes:
        name: Unique component name
        kind: Component kind (agent, tool, plugin, mcp_server, provider)
        version: Version string
        description: Human-readable description
        metadata: Arbitrary metadata dict
        available: Whether the component is currently available
        registered_at: Timestamp of registration
        health_check: Optional callable() -> bool
    """
    name: str
    kind: str  # "agent", "tool", "plugin", "mcp_server", "provider"
    version: str = "0.1.0"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    available: bool = True
    registered_at: float = field(default_factory=time.time)
    health_check: Optional[Callable[[], bool]] = None


class AgentRegistry:
    """Runtime registry for kernel components.

    Provides service discovery — components can find each other
    through the registry rather than direct imports.

    Usage:
        registry = AgentRegistry(event_bus)
        registry.register(ComponentEntry(name="my-agent", kind="agent"))
        found = registry.find(name="my-agent")
        agents = registry.list_kind("agent")
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._entries: Dict[str, ComponentEntry] = {}
        # kind -> set of names
        self._kind_index: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, entry: ComponentEntry) -> ComponentEntry:
        """Register a component. Overwrites existing entries with the same name."""
        with self._lock:
            existing = self._entries.get(entry.name)
            self._entries[entry.name] = entry
            self._kind_index.setdefault(entry.kind, set()).add(entry.name)

        if existing:
            logger.debug("Registry: updated '%s' (%s)", entry.name, entry.kind)
        else:
            logger.info(
                "Registry: registered '%s' as %s", entry.name, entry.kind,
            )

        if self._event_bus:
            self._event_bus.emit_async("registry.registered", {
                "name": entry.name,
                "kind": entry.kind,
            })

        return entry

    def deregister(self, name: str) -> bool:
        """Remove a component from the registry. Returns True if found."""
        with self._lock:
            entry = self._entries.pop(name, None)
            if entry is None:
                return False
            kind_set = self._kind_index.get(entry.kind)
            if kind_set:
                kind_set.discard(name)
        logger.info("Registry: deregistered '%s' (%s)", name, entry.kind)

        if self._event_bus:
            self._event_bus.emit_async("registry.deregistered", {
                "name": name, "kind": entry.kind,
            })
        return True

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[ComponentEntry]:
        """Get a component by name."""
        with self._lock:
            return self._entries.get(name)

    def find(self, *, name: str = None, kind: str = None,
             available_only: bool = True) -> List[ComponentEntry]:
        """Find components matching optional filters."""
        with self._lock:
            results = list(self._entries.values())

        if name:
            results = [e for e in results if e.name == name]
        if kind:
            results = [e for e in results if e.kind == kind]
        if available_only:
            results = [e for e in results if e.available]

        # Sort by name for determinism
        results.sort(key=lambda e: (e.kind, e.name))
        return results

    def list_kind(self, kind: str, available_only: bool = True) -> List[ComponentEntry]:
        """List all components of a given kind."""
        return self.find(kind=kind, available_only=available_only)

    def list_agents(self) -> List[ComponentEntry]:
        """List all registered agents."""
        return self.list_kind("agent")

    def list_tools(self) -> List[ComponentEntry]:
        """List all registered tools."""
        return self.list_kind("tool")

    def list_plugins(self) -> List[ComponentEntry]:
        """List all registered plugins."""
        return self.list_kind("plugin")

    def list_providers(self) -> List[ComponentEntry]:
        """List all registered model providers."""
        return self.list_kind("provider")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_kinds(self) -> List[str]:
        """Return all distinct component kinds in the registry."""
        with self._lock:
            return sorted(self._kind_index.keys())

    def count_by_kind(self) -> Dict[str, int]:
        """Return counts of components per kind."""
        with self._lock:
            return {
                kind: len(names)
                for kind, names in self._kind_index.items()
            }

    def has_component(self, name: str) -> bool:
        """Check if a component name is registered."""
        with self._lock:
            return name in self._entries

    def mark_unavailable(self, name: str) -> bool:
        """Mark a component as unavailable without removing it."""
        with self._lock:
            entry = self._entries.get(name)
            if entry is None:
                return False
            entry.available = False
        return True

    def mark_available(self, name: str) -> bool:
        """Mark a component as available again."""
        with self._lock:
            entry = self._entries.get(name)
            if entry is None:
                return False
            entry.available = True
        return True

    def set_metadata(self, name: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a registered component."""
        with self._lock:
            entry = self._entries.get(name)
            if entry is None:
                return False
            entry.metadata.update(metadata)
        return True

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the entire registry."""
        entries = self.find(available_only=False)
        return {
            "total": len(entries),
            "by_kind": self.count_by_kind(),
            "entries": [
                {
                    "name": e.name,
                    "kind": e.kind,
                    "version": e.version,
                    "description": e.description,
                    "available": e.available,
                }
                for e in entries
            ],
        }

    # ------------------------------------------------------------------
    # Integration with existing Aetheros systems
    # ------------------------------------------------------------------

    def discover_from_tool_registry(self) -> int:
        """Sync tools from the existing tools.registry into the kernel registry.

        Returns the number of tools discovered.
        """
        try:
            from tools.registry import registry as _tool_registry
            tool_names = _tool_registry.get_all_tool_names()
            registered_count = 0
            for name in tool_names:
                toolset = _tool_registry.get_toolset_for_tool(name)
                emoji = _tool_registry.get_emoji(name)
                schema = _tool_registry.get_schema(name)
                self.register(ComponentEntry(
                    name=name,
                    kind="tool",
                    description=(schema.get("description", "") if schema else ""),
                    version="1.0.0",
                    metadata={
                        "toolset": toolset or "unknown",
                        "emoji": emoji,
                    },
                ))
                registered_count += 1
            logger.info(
                "Registry: discovered %d tools from tool registry",
                registered_count,
            )
            return registered_count
        except Exception as exc:
            logger.warning("Registry: tool discovery failed: %s", exc)
            return 0

    def discover_from_plugins(self) -> int:
        """Sync plugins from the existing plugin system.

        Returns the number of plugins discovered.
        """
        try:
            from aetheros_cli.plugins import (
                discover_plugins, get_all_plugin_manifests,
            )
            discover_plugins()
            manifests = get_all_plugin_manifests()
            count = 0
            for manifest in manifests:
                self.register(ComponentEntry(
                    name=manifest.name,
                    kind="plugin",
                    version=manifest.version or "0.1.0",
                    description=manifest.description or "",
                ))
                count += 1
            logger.info("Registry: discovered %d plugins", count)
            return count
        except Exception as exc:
            logger.warning("Registry: plugin discovery failed: %s", exc)
            return 0

    def discover_from_mcp(self) -> int:
        """Sync MCP servers from the MCP tool system.

        Returns the number of MCP servers discovered.
        """
        try:
            from tools.mcp_tool import get_active_mcp_servers
            servers = get_active_mcp_servers()
            count = 0
            for server in servers:
                name = getattr(server, "name", str(server))
                self.register(ComponentEntry(
                    name=f"mcp:{name}",
                    kind="mcp_server",
                    description=f"MCP server: {name}",
                    metadata={"server_name": name},
                ))
                count += 1
            logger.info("Registry: discovered %d MCP servers", count)
            return count
        except Exception as exc:
            logger.warning("Registry: MCP discovery failed: %s", exc)
            return 0

    def discover_all(self) -> Dict[str, int]:
        """Run all discovery methods and return counts."""
        return {
            "tools": self.discover_from_tool_registry(),
            "plugins": self.discover_from_plugins(),
            "mcp_servers": self.discover_from_mcp(),
        }
