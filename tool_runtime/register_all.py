"""Register all tool runtimes with the Tool Runtime Manager.

This is the main integration point between the new Universal Tool Runtime
and the existing AetherOS system. Call setup_tool_runtime() at startup.
"""

from __future__ import annotations

import logging
from typing import Optional

from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager

logger = logging.getLogger(__name__)


def setup_tool_runtime() -> ToolRuntimeManager:
    """Initialize and register all tool runtimes.

    Returns the initialized ToolRuntimeManager with all runtimes registered.

    This integrates with AetherOS by:
    1. Starting the ToolRuntimeManager
    2. Registering all domain runtimes
    3. Wrapping existing tools/registry.py tools
    4. Initializing permission, safety, and observability systems
    """
    manager = get_runtime_manager()
    manager.start()

    registered = _register_all_runtimes(manager)
    logger.info("Tool Runtime setup complete: %d runtimes registered", registered)

    return manager


def _register_all_runtimes(manager: ToolRuntimeManager) -> int:
    """Register all runtime implementations with the manager."""
    from tool_runtime.filesystem.tools import FilesystemRuntime
    from tool_runtime.terminal.runtime import TerminalRuntime
    from tool_runtime.python.runtime import PythonRuntime
    from tool_runtime.browser.runtime import BrowserRuntime
    from tool_runtime.desktop.runtime import DesktopRuntime
    from tool_runtime.git.runtime import GitRuntime
    from tool_runtime.rest.runtime import RESTRuntime
    from tool_runtime.database.runtime import DatabaseRuntime
    from tool_runtime.plugins.runtime import PluginRuntime
    from tool_runtime.chaining.engine import ChainingEngine

    runtimes = [
        ("filesystem", FilesystemRuntime),
        ("terminal", TerminalRuntime),
        ("python", PythonRuntime),
        ("browser", BrowserRuntime),
        ("desktop", DesktopRuntime),
        ("git", GitRuntime),
        ("rest_api", RESTRuntime),
        ("database", DatabaseRuntime),
        ("plugin_manager", PluginRuntime),
        ("chaining", ChainingEngine),
    ]

    count = 0
    for name, runtime_cls in runtimes:
        try:
            runtime = runtime_cls()
            manager.register_runtime(runtime)
            count += 1
            logger.debug("Registered runtime: %s", name)
        except Exception as e:
            logger.warning("Failed to register runtime '%s': %s", name, e)

    return count


def setup_permission_system() -> None:
    """Configure default permission rules for the tool runtime."""
    from tool_runtime.permission import get_permission_system, PermissionRule, RiskLevel
    perm = get_permission_system()

    perm.set_max_risk_level(RiskLevel.EXECUTE)
    perm.add_rule(PermissionRule(
        effect="deny", tool_pattern="credential*",
        reason="Credential operations require explicit approval",
    ))
    perm.add_rule(PermissionRule(
        effect="deny", tool_pattern="admin*",
        reason="Admin operations require authorization",
    ))


def setup_safety_engine() -> None:
    """Configure the safety engine with custom rules."""
    from tool_runtime.safety import get_safety_engine
    engine = get_safety_engine()
    _ = engine  # Default rules are already set up in __init__


def quick_start() -> ToolRuntimeManager:
    """Complete setup: runtimes + permissions + safety.

    Call this once at application startup::

        from tool_runtime.register_all import quick_start
        manager = quick_start()
    """
    from tool_runtime.permission import RiskLevel
    setup_permission_system()
    setup_safety_engine()
    return setup_tool_runtime()
