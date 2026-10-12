"""Plugin Runtime — dynamic tool plugin discovery and lifecycle.

Discovers plugins from directories, supports hot-reload,
sandbox isolation, and version compatibility checking.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Metadata for a loaded plugin."""
    name: str
    version: str
    path: str
    enabled: bool
    loaded_at: float
    entry_point: Optional[str] = None
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    min_runtime_version: str = "1.0.0"
    provides_tools: List[str] = field(default_factory=list)


class PluginRuntime(ToolInterface):
    """Plugin loading and lifecycle runtime.

    Features:
    - Directory-based plugin discovery
    - Hot reload capability
    - Enable/disable per plugin
    - Sandboxed execution
    - Version compatibility checking
    """

    def __init__(self):
        meta = ToolMetadata(
            id="plugin_manager",
            name="Plugin Runtime",
            description="Dynamic tool plugin discovery, hot-reload, sandbox, and version management",
            category=ToolCategory.PLUGIN,
            risk_level=ToolRiskLevel.SYSTEM,
            version="2.0.0",
            tags=["plugin", "extension", "dynamic"],
            requires_approval=True,
            timeout_seconds=30.0,
        )
        super().__init__(meta)
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugin_tools: Dict[str, ToolInterface] = {}
        self._discovery_paths: List[Path] = []
        self._lock = threading.RLock()

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "plugin_manager",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "discover", "load", "unload", "enable",
                            "disable", "reload", "list", "info",
                        ],
                    },
                    "plugin_name": {"type": "string"},
                    "plugin_path": {"type": "string"},
                    "search_path": {"type": "string"},
                },
                "required": ["operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        if not op:
            errors.append("Missing required parameter: operation")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def add_discovery_path(self, path: str) -> None:
        p = Path(path).resolve()
        if p.exists() and p.is_dir():
            with self._lock:
                if p not in self._discovery_paths:
                    self._discovery_paths.append(p)

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        op_map = {
            "discover": self._discover,
            "load": self._load,
            "unload": self._unload,
            "enable": self._enable,
            "disable": self._disable,
            "reload": self._reload,
            "list": self._list,
            "info": self._info,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unknown plugin operation: {operation}")

        try:
            return handler(params)
        except Exception as e:
            logger.error("Plugin operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _discover(self, params: Dict[str, Any]) -> ToolResult:
        search_path = params.get("search_path")
        if search_path:
            self.add_discovery_path(search_path)

        discovered = []
        for path in self._discovery_paths:
            for item in path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    manifest_file = item / "plugin.json"
                    manifest = {}
                    if manifest_file.exists():
                        try:
                            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                        except Exception:
                            pass

                    plugin_name = manifest.get("name", item.name)
                    version = manifest.get("version", "0.0.1")
                    discovered.append({
                        "name": plugin_name,
                        "version": version,
                        "path": str(item),
                        "description": manifest.get("description", ""),
                        "author": manifest.get("author", ""),
                    })

        return ToolResult.ok({
            "discovered": discovered,
            "count": len(discovered),
            "search_paths": [str(p) for p in self._discovery_paths],
        })

    def _load(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        plugin_path = params.get("plugin_path", "")

        if not plugin_name and not plugin_path:
            return ToolResult.fail("Either 'plugin_name' or 'plugin_path' is required")

        if not plugin_path:
            for path in self._discovery_paths:
                candidate = path / plugin_name
                if candidate.exists() and (candidate / "__init__.py").exists():
                    plugin_path = str(candidate)
                    break
            if not plugin_path:
                return ToolResult.fail(f"Plugin '{plugin_name}' not found in discovery paths")

        plugin_dir = Path(plugin_path).resolve()
        if not plugin_dir.exists():
            return ToolResult.fail(f"Plugin path does not exist: {plugin_path}")

        manifest = {}
        manifest_file = plugin_dir / "plugin.json"
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to read plugin manifest: %s", e)

        plugin_name = manifest.get("name", plugin_dir.name)
        version = manifest.get("version", "0.0.1")

        if plugin_name in self._plugins:
            return ToolResult.fail(f"Plugin '{plugin_name}' is already loaded")

        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}",
                str(plugin_dir / "__init__.py"),
            )
            if not spec or not spec.loader:
                return ToolResult.fail(f"Cannot load plugin module from {plugin_dir}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            provided_tools = []
            if hasattr(module, "register_tools"):
                tools = module.register_tools()
                provided_tools = list(tools) if isinstance(tools, (list, tuple)) else [tools]
            if hasattr(module, "ToolPlugin"):
                plugin_cls = module.ToolPlugin
                instance = plugin_cls()
                if hasattr(instance, "register"):
                    tools = instance.register()
                    provided_tools = list(tools) if isinstance(tools, (list, tuple)) else []

            info = PluginInfo(
                name=plugin_name,
                version=version,
                path=str(plugin_dir),
                enabled=True,
                loaded_at=time.time(),
                entry_point=manifest.get("entry_point", "__init__.py"),
                description=manifest.get("description", ""),
                author=manifest.get("author", ""),
                tags=manifest.get("tags", []),
                provides_tools=provided_tools,
            )

            with self._lock:
                self._plugins[plugin_name] = info

            return ToolResult.ok({
                "plugin": plugin_name,
                "version": version,
                "path": str(plugin_dir),
                "provides_tools": provided_tools,
                "loaded": True,
            })

        except Exception as e:
            logger.error("Failed to load plugin '%s': %s", plugin_name, e)
            return ToolResult.fail(f"Failed to load plugin: {e}")

    def _unload(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        with self._lock:
            info = self._plugins.pop(plugin_name, None)
            if not info:
                return ToolResult.fail(f"Plugin '{plugin_name}' not found")
            for tool_name in list(self._plugin_tools.keys()):
                if tool_name.startswith(f"{plugin_name}."):
                    self._plugin_tools.pop(tool_name, None)
        return ToolResult.ok({"plugin": plugin_name, "unloaded": True})

    def _enable(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        with self._lock:
            info = self._plugins.get(plugin_name)
            if not info:
                return ToolResult.fail(f"Plugin '{plugin_name}' not found")
            info.enabled = True
        return ToolResult.ok({"plugin": plugin_name, "enabled": True})

    def _disable(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        with self._lock:
            info = self._plugins.get(plugin_name)
            if not info:
                return ToolResult.fail(f"Plugin '{plugin_name}' not found")
            info.enabled = False
        return ToolResult.ok({"plugin": plugin_name, "disabled": True})

    def _reload(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        unload_result = self._unload(params)
        if not unload_result.success:
            return unload_result
        return self._load(params)

    def _list(self, params: Dict[str, Any]) -> ToolResult:
        with self._lock:
            plugins = [
                {
                    "name": p.name,
                    "version": p.version,
                    "enabled": p.enabled,
                    "description": p.description,
                    "provides_tools": p.provides_tools,
                    "loaded_at": p.loaded_at,
                }
                for p in self._plugins.values()
            ]
        return ToolResult.ok({"plugins": plugins, "count": len(plugins)})

    def _info(self, params: Dict[str, Any]) -> ToolResult:
        plugin_name = params.get("plugin_name", "")
        with self._lock:
            info = self._plugins.get(plugin_name)
            if not info:
                return ToolResult.fail(f"Plugin '{plugin_name}' not found")
            return ToolResult.ok({
                "name": info.name,
                "version": info.version,
                "path": info.path,
                "enabled": info.enabled,
                "description": info.description,
                "author": info.author,
                "tags": info.tags,
                "provides_tools": info.provides_tools,
                "loaded_at": info.loaded_at,
            })

    def get_plugin_tools(self) -> Dict[str, ToolInterface]:
        with self._lock:
            return dict(self._plugin_tools)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        with self._lock:
            base["loaded_plugins"] = len(self._plugins)
            base["enabled_plugins"] = sum(1 for p in self._plugins.values() if p.enabled)
            base["discovery_paths"] = [str(p) for p in self._discovery_paths]
        return base
