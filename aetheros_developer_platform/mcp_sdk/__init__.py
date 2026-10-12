"""
MCP SDK for AetherOS
====================

Generate, register, and manage MCP (Model Context Protocol) servers.

Features:
    - Automatic MCP server generation from tool definitions
    - Capability discovery
    - Permission system
    - Health monitoring
    - Auto-registration with AetherOS

Usage::

    from aetheros_developer_platform.mcp_sdk import MCPServerBuilder

    builder = MCPServerBuilder("my-server")
    builder.add_tool("greet", "Greet someone", {"name": "string"})
    builder.set_handler("greet", lambda args: f"Hello, {args['name']}!")
    server = builder.build()
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPCapability(Enum):
    """MCP server capabilities."""
    TOOLS = "tools"
    RESOURCES = "prompts"
    PROMPTS = "prompts"
    LOGGING = "logging"
    COMPLETIONS = "completions"


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    handler: Optional[Callable] = None


@dataclass
class MCPPrompt:
    """MCP prompt definition."""
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    handler: Optional[Callable] = None


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    capabilities: List[MCPCapability] = field(
        default_factory=lambda: [MCPCapability.TOOLS]
    )
    permissions: List[str] = field(default_factory=list)


class MCPServer:
    """MCP Server implementation.

    Usage::

        server = MCPServer("my-server")
        server.add_tool("greet", "Greet someone", {"name": "string"})
        server.set_handler("greet", lambda args: f"Hello, {args['name']}!")

        # Start serving
        server.start()
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}
        self._running = False
        self._start_time: Optional[float] = None
        self._request_count = 0
        self._error_count = 0

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def version(self) -> str:
        return self._config.version

    @property
    def is_running(self) -> bool:
        return self._running

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> None:
        """Add a tool to the server."""
        self._tools[name] = MCPTool(
            name=name,
            description=description,
            parameters=parameters or {},
            handler=handler,
        )

    def set_handler(self, tool_name: str, handler: Callable) -> None:
        """Set the handler for a tool."""
        if tool_name in self._tools:
            self._tools[tool_name].handler = handler
        else:
            raise ValueError(f"Tool '{tool_name}' not found")

    def add_resource(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "text/plain",
        handler: Optional[Callable] = None,
    ) -> None:
        """Add a resource to the server."""
        self._resources[uri] = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            handler=handler,
        )

    def add_prompt(
        self,
        name: str,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
        handler: Optional[Callable] = None,
    ) -> None:
        """Add a prompt to the server."""
        self._prompts[name] = MCPPrompt(
            name=name,
            description=description,
            arguments=arguments or [],
            handler=handler,
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        if tool.handler is None:
            raise ValueError(f"No handler for tool '{name}'")

        self._request_count += 1
        try:
            return tool.handler(arguments)
        except Exception as exc:
            self._error_count += 1
            raise

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources."""
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type,
            }
            for resource in self._resources.values()
        ]

    def read_resource(self, uri: str) -> Any:
        """Read a resource by URI."""
        resource = self._resources.get(uri)
        if not resource:
            raise ValueError(f"Resource '{uri}' not found")

        if resource.handler is None:
            return {"uri": uri, "content": ""}

        return resource.handler(uri)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts."""
        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments,
            }
            for prompt in self._prompts.values()
        ]

    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Get a prompt by name."""
        prompt = self._prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt '{name}' not found")

        if prompt.handler is None:
            return {"messages": []}

        return prompt.handler(arguments)

    def start(self) -> None:
        """Start the MCP server."""
        self._running = True
        self._start_time = time.time()
        logger.info("MCP server '%s' started", self.name)

    def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False
        logger.info("MCP server '%s' stopped", self.name)

    def get_health(self) -> Dict[str, Any]:
        """Get server health status."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "status": "healthy" if self._running else "stopped",
            "name": self.name,
            "version": self.version,
            "uptime": uptime,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export server definition as dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self._config.description,
            "capabilities": [c.value for c in self._config.capabilities],
            "tools": self.list_tools(),
            "resources": self.list_resources(),
            "prompts": self.list_prompts(),
        }


class MCPServerBuilder:
    """Builder for creating MCP servers.

    Usage::

        builder = MCPServerBuilder("my-server")
        builder.add_tool("greet", "Greet someone", {"name": "string"})
        builder.set_handler("greet", lambda args: f"Hello, {args['name']}!")
        server = builder.build()
    """

    def __init__(
        self,
        name: str,
        *,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
    ) -> None:
        self._config = MCPServerConfig(
            name=name,
            version=version,
            description=description,
            author=author,
        )
        self._tools: List[MCPTool] = []
        self._resources: List[MCPResource] = []
        self._prompts: List[MCPPrompt] = []

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None,
    ) -> "MCPServerBuilder":
        """Add a tool to the builder."""
        self._tools.append(MCPTool(
            name=name,
            description=description,
            parameters=parameters or {},
            handler=handler,
        ))
        return self

    def set_handler(self, tool_name: str, handler: Callable) -> "MCPServerBuilder":
        """Set the handler for a tool."""
        for tool in self._tools:
            if tool.name == tool_name:
                tool.handler = handler
                break
        return self

    def add_resource(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "text/plain",
        handler: Optional[Callable] = None,
    ) -> "MCPServerBuilder":
        """Add a resource to the builder."""
        self._resources.append(MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            handler=handler,
        ))
        return self

    def add_prompt(
        self,
        name: str,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
        handler: Optional[Callable] = None,
    ) -> "MCPServerBuilder":
        """Add a prompt to the builder."""
        self._prompts.append(MCPPrompt(
            name=name,
            description=description,
            arguments=arguments or [],
            handler=handler,
        ))
        return self

    def add_capability(self, capability: MCPCapability) -> "MCPServerBuilder":
        """Add a capability to the server."""
        if capability not in self._config.capabilities:
            self._config.capabilities.append(capability)
        return self

    def add_permission(self, permission: str) -> "MCPServerBuilder":
        """Add a required permission."""
        if permission not in self._config.permissions:
            self._config.permissions.append(permission)
        return self

    def build(self) -> MCPServer:
        """Build the MCP server."""
        server = MCPServer(self._config)
        for tool in self._tools:
            server.add_tool(tool.name, tool.description, tool.parameters, tool.handler)
        for resource in self._resources:
            server.add_resource(resource.uri, resource.name, resource.description, resource.mime_type, resource.handler)
        for prompt in self._prompts:
            server.add_prompt(prompt.name, prompt.description, prompt.arguments, prompt.handler)
        return server


def generate_mcp_server(
    name: str,
    tools: List[Dict[str, Any]],
    *,
    version: str = "1.0.0",
    description: str = "",
) -> MCPServer:
    """Generate an MCP server from tool definitions.

    Args:
        name: Server name.
        tools: List of tool definitions with 'name', 'description', 'parameters'.
        version: Server version.
        description: Server description.

    Returns:
        Configured MCPServer instance.
    """
    builder = MCPServerBuilder(name, version=version, description=description)

    for tool_def in tools:
        builder.add_tool(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            parameters=tool_def.get("parameters", {}),
        )

    return builder.build()


def auto_register_mcp_server(server: MCPServer) -> None:
    """Auto-register an MCP server with AetherOS.

    Args:
        server: The MCP server to register.
    """
    try:
        from aetheros_developer_platform.plugin_api import get_plugin_registry
        registry = get_plugin_registry()

        def register_fn(ctx) -> None:
            ctx.register_mcp(server.name, server)

        registry.register_mcp(
            name=server.name,
            version=server.version,
            description=server._config.description,
        )(register_fn)

        logger.info("Auto-registered MCP server: %s", server.name)
    except Exception as exc:
        logger.warning("Failed to auto-register MCP server '%s': %s", server.name, exc)
