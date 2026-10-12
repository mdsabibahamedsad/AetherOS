"""
AetherOS Developer Platform
============================

The unified developer platform for building, publishing, and managing
extensions for AetherOS. Equivalent to VS Code Marketplace + Docker Hub
+ MCP Registry + Hugging Face Hub, but unified inside one AI Operating System.

Architecture::

    aetheros_developer_platform/
        __init__.py          Package exports and version info
        sdk/                 Language SDKs (Python, TypeScript, JS, Go, Rust, C#, Java)
        plugin_api/          Plugin registration API (tools, agents, workflows, MCP, etc.)
        marketplace/         Marketplace UI and backend
        extension_manager/   Extension lifecycle management
        cli/                 Developer CLI tools
        web_ui/              Developer Center web interface
        developer_tools/     Live reload, inspector, debugger
        security/            Signing, verification, malware scanning
        theme_engine/        Theme system (dark, light, custom)
        ui_extensions/       UI extension points (sidebar, toolbar, etc.)
        mcp_sdk/             MCP server generation and management
        agent_sdk/           AI agent SDK (planner, researcher, developer, etc.)
        workflow_sdk/        Workflow SDK (nodes, conditions, triggers, actions)
        voice_sdk/           Voice SDK (commands, skills, wake actions)
        knowledge_sdk/       Knowledge SDK (providers, vectors, embeddings)
        model_sdk/           Model SDK (LLM, embedding, image, speech providers)
        docs/                Auto-generated documentation
        api/                 REST API for the developer platform

Usage::

    from aetheros_developer_platform import DeveloperPlatform
    from aetheros_developer_platform.sdk import SDKFactory
    from aetheros_developer_platform.plugin_api import PluginRegistry
    from aetheros_developer_platform.mcp_sdk import MCPServerBuilder
    from aetheros_developer_platform.theme_engine import ThemeManager
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# Platform version
__version__: Final[str] = "1.0.0"

# Plugin types supported
PLUGIN_TYPES = [
    "ai_agent",
    "tool_plugin",
    "workflow_plugin",
    "mcp_server",
    "model_provider",
    "memory_provider",
    "knowledge_provider",
    "voice_skill",
    "automation_action",
    "theme",
    "widget",
    "ui_panel",
    "sidebar_app",
    "dashboard_card",
    "connector",
]

# App categories
APP_CATEGORIES = [
    "official",
    "verified",
    "community",
    "private",
    "enterprise",
]

# Extension permissions
EXTENSION_PERMISSIONS = [
    "filesystem",
    "internet",
    "terminal",
    "browser",
    "clipboard",
    "microphone",
    "camera",
    "notifications",
    "knowledge",
    "memory",
    "workflow",
]


def get_platform_version() -> str:
    """Return the current platform version."""
    return __version__


def get_supported_plugin_types() -> list[str]:
    """Return list of supported plugin types."""
    return list(PLUGIN_TYPES)


def get_extension_permissions() -> list[str]:
    """Return list of extension permissions."""
    return list(EXTENSION_PERMISSIONS)


class DeveloperPlatform:
    """Main entry point for the Developer Platform.

    Usage::

        platform = DeveloperPlatform()

        # Initialize SDK
        sdk = platform.get_sdk("python")

        # Access marketplace
        marketplace = platform.get_marketplace()

        # Access theme engine
        themes = platform.get_theme_manager()
    """

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the developer platform."""
        if self._initialized:
            return

        logger.info("Initializing AetherOS Developer Platform v%s", __version__)
        self._initialized = True

    def get_sdk(self, language: str):
        """Get an SDK for the specified language."""
        from aetheros_developer_platform.sdk import SDKFactory
        return SDKFactory.create(language)

    def get_marketplace(self):
        """Get the marketplace instance."""
        from marketplace.registry import get_registry
        return get_registry()

    def get_extension_manager(self):
        """Get the extension manager."""
        from extensions.manager import get_extension_manager
        return get_extension_manager()

    def get_plugin_registry(self):
        """Get the plugin registry."""
        from aetheros_developer_platform.plugin_api import get_plugin_registry
        return get_plugin_registry()

    def get_theme_manager(self):
        """Get the theme manager."""
        from aetheros_developer_platform.theme_engine import get_theme_manager
        return get_theme_manager()

    def get_security_manager(self):
        """Get the security manager."""
        from aetheros_developer_platform.security import get_security_manager
        return get_security_manager()

    def get_dev_tools(self):
        """Get the developer tools."""
        from aetheros_developer_platform.developer_tools import get_dev_tools
        return get_dev_tools()

    def get_voice_manager(self):
        """Get the voice manager."""
        from aetheros_developer_platform.voice_sdk import get_voice_manager
        return get_voice_manager()

    def get_knowledge_manager(self):
        """Get the knowledge manager."""
        from aetheros_developer_platform.knowledge_sdk import get_knowledge_manager
        return get_knowledge_manager()

    def get_model_manager(self):
        """Get the model manager."""
        from aetheros_developer_platform.model_sdk import get_model_manager
        return get_model_manager()

    def get_docs_manager(self):
        """Get the documentation manager."""
        from aetheros_developer_platform.docs import get_docs_manager
        return get_docs_manager()

    def get_api(self):
        """Get the REST API."""
        from aetheros_developer_platform.api import get_developer_api
        return get_developer_api()

    def get_web_ui(self):
        """Get the web UI."""
        from aetheros_developer_platform.web_ui import get_web_ui
        return get_web_ui()

    def get_cli(self):
        """Get the CLI."""
        from aetheros_developer_platform.cli import DeveloperCLI
        return DeveloperCLI()
