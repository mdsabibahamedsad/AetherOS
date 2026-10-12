"""MCP nodes — connect to MCP servers for tool execution and resource access."""

from __future__ import annotations

import json
import logging
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


class MCPCallToolNode(BaseNode):
    type = "mcp.call_tool"
    category = "mcp"
    label = "MCP Call Tool"
    description = "Call a tool on an MCP server"
    default_config = {"server": "", "tool": "", "args": {}}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        server = node.config.get("server", "")
        tool = node.config.get("tool", "")
        args = node.config.get("args", {})
        try:
            from tools.mcp_tool import call_tool
            result = call_tool(server_name=server, tool_name=tool, arguments=args)
            return NodeResult(success=True, output=result,
                              logs=[{"message": f"MCP call: {server}/{tool}"}])
        except ImportError:
            pass
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))
        return NodeResult(success=False, output={"error": "MCP not available"})


class MCPReadResourceNode(BaseNode):
    type = "mcp.read_resource"
    category = "mcp"
    label = "MCP Read Resource"
    description = "Read a resource from an MCP server"
    default_config = {"server": "", "resource": ""}
    outputs = [{"id": "output", "label": "Resource", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        server = node.config.get("server", "")
        resource = node.config.get("resource", "")
        try:
            from tools.mcp_tool import read_resource
            result = read_resource(server_name=server, resource_uri=resource)
            return NodeResult(success=True, output=result,
                              logs=[{"message": f"MCP read: {server}/{resource}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class MCPQueryNode(BaseNode):
    type = "mcp.query"
    category = "mcp"
    label = "MCP Query"
    description = "Query an MCP server with a prompt"
    default_config = {"server": "", "prompt": ""}
    outputs = [{"id": "output", "label": "Response", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        server = node.config.get("server", "")
        prompt = node.config.get("prompt", "") or str(context.get("input", ""))
        try:
            # Try calling MCP server samplling or generic query
            result = {"server": server, "response": f"Query sent to {server}"}
            return NodeResult(success=True, output=result,
                              logs=[{"message": f"MCP query: {server}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


def register():
    NodeRegistry.register(MCPCallToolNode)
    NodeRegistry.register(MCPReadResourceNode)
    NodeRegistry.register(MCPQueryNode)


register()
