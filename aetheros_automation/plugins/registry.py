from __future__ import annotations

import importlib.util
import logging
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable

from aetheros_automation.models.models import FileOperation

logger = logging.getLogger(__name__)

# Type alias for action handlers
ActionHandler = Callable[..., Any]


class AutomationPlugin(ABC):
    """Base class for automation plugins.

    Subclasses must set *name* and implement :meth:`execute`.
    """

    name: str = ""

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:
        ...


class AutomationPluginRegistry:
    """Central registry for plugin-driven actions, desktop interactions,
    browser automation, and workflow node types.

    Actions are registered by name and dispatched at runtime so core code
    never needs to import plugin modules directly.
    """

    def __init__(self) -> None:
        self._actions: dict[str, tuple[str, ActionHandler]] = {}
        self._desktop_actions: dict[str, ActionHandler] = {}
        self._browser_actions: dict[str, ActionHandler] = {}
        self._workflow_nodes: dict[str, type[AutomationPlugin]] = {}
        self._plugins: dict[str, AutomationPlugin] = {}

    # ------------------------------------------------------------------
    # registration
    # ------------------------------------------------------------------

    def register_action(
        self,
        name: str,
        handler: ActionHandler,
        category: str = "general",
    ) -> None:
        """Register *handler* under *name* in the given *category*."""
        if name in self._actions:
            logger.warning("Overwriting existing action: %s", name)
        self._actions[name] = (category, handler)
        logger.debug("Registered action '%s' (category=%s)", name, category)

    def register_desktop_action(self, name: str, handler: ActionHandler) -> None:
        """Register a desktop-specific action (file open, notification, etc.)."""
        if name in self._desktop_actions:
            logger.warning("Overwriting desktop action: %s", name)
        self._desktop_actions[name] = handler
        logger.debug("Registered desktop action '%s'", name)

    def register_browser_action(self, name: str, handler: ActionHandler) -> None:
        """Register a browser-automation action (click, fill, navigate, etc.)."""
        if name in self._browser_actions:
            logger.warning("Overwriting browser action: %s", name)
        self._browser_actions[name] = handler
        logger.debug("Registered browser action '%s'", name)

    def register_workflow_node(
        self, name: str, handler_class: type[AutomationPlugin]
    ) -> None:
        """Register a workflow node type that can be dropped into a DAG."""
        if name in self._workflow_nodes:
            logger.warning("Overwriting workflow node: %s", name)
        self._workflow_nodes[name] = handler_class
        logger.debug("Registered workflow node '%s'", name)

    def register_plugin(self, plugin: AutomationPlugin) -> None:
        """Register a full plugin instance."""
        if plugin.name in self._plugins:
            logger.warning("Overwriting plugin: %s", plugin.name)
        self._plugins[plugin.name] = plugin
        logger.debug("Registered plugin '%s'", plugin.name)

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------

    async def execute_action(
        self,
        name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a registered action by name.

        Resolution order:
          1. Plugin instance method
          2. General action handler
          3. Desktop action
          4. Browser action

        Raises ``KeyError`` if *name* is not found.
        """
        params = params or {}

        # plugin instance
        for plugin in self._plugins.values():
            if hasattr(plugin, name):
                return getattr(plugin, name)(**params)

        # general action
        entry = self._actions.get(name)
        if entry is not None:
            _, handler = entry
            result = handler(**params)
            if hasattr(result, "__await__"):
                return await result
            return result

        # desktop action
        handler = self._desktop_actions.get(name)
        if handler is not None:
            result = handler(**params)
            if hasattr(result, "__await__"):
                return await result
            return result

        # browser action
        handler = self._browser_actions.get(name)
        if handler is not None:
            result = handler(**params)
            if hasattr(result, "__await__"):
                return await result
            return result

        raise KeyError(f"Action '{name}' not found in any registry category")

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def list_actions(self, category: str | None = None) -> list[str]:
        """Return registered action names, optionally filtered by *category*."""
        if category is None:
            return list(self._actions.keys())
        return [
            name
            for name, (cat, _) in self._actions.items()
            if cat == category
        ]

    def list_desktop_actions(self) -> list[str]:
        return list(self._desktop_actions.keys())

    def list_browser_actions(self) -> list[str]:
        return list(self._browser_actions.keys())

    def list_workflow_nodes(self) -> list[str]:
        return list(self._workflow_nodes.keys())

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())

    def get_workflow_node(self, name: str) -> type[AutomationPlugin] | None:
        return self._workflow_nodes.get(name)

    # ------------------------------------------------------------------
    # discovery
    # ------------------------------------------------------------------

    def import_discovery(self, path: str) -> None:
        """Scan *path* for Python packages/modules and import each one.

        Each imported module is expected to call :meth:`register_action`,
        :meth:`register_desktop_action`, etc. at import time to wire itself
        into the registry.
        """
        scan_path = os.path.abspath(path)
        if not os.path.isdir(scan_path):
            logger.warning("Plugin discovery path does not exist: %s", scan_path)
            return

        logger.info("Scanning for plugins in %s", scan_path)

        for entry in sorted(os.listdir(scan_path)):
            entry_path = os.path.join(scan_path, entry)

            # Single-file module
            if entry.endswith(".py") and entry != "__init__.py":
                mod_name = entry[:-3]
                self._load_module(mod_name, entry_path)
                continue

            # Package directory
            pkg_init = os.path.join(entry_path, "__init__.py")
            if os.path.isdir(entry_path) and os.path.isfile(pkg_init):
                self._load_module(f"aetheros_plugin_{entry}", pkg_init)
                continue

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _load_module(self, name: str, path: str) -> Any:
        """Import a single file as a module."""
        if not os.path.isfile(path):
            logger.debug("Skipping %s — not a file", path)
            return None

        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                logger.warning("Could not create spec for %s", path)
                return None

            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            logger.debug("Loaded plugin module %s from %s", name, path)
            return mod
        except Exception:
            logger.exception("Failed to load plugin module %s from %s", name, path)
            return None
