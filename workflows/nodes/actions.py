"""Action nodes — execute shell commands, file operations, scripts, and tool calls."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Any

from workflows.nodes.base import BaseNode, NodeRegistry, NodeResult
from workflows.models import WorkflowNode, WorkflowConfig

logger = logging.getLogger(__name__)


class ShellCommandNode(BaseNode):
    type = "action.shell"
    category = "action"
    label = "Shell Command"
    description = "Run a shell command"
    default_config = {"command": "", "timeout": 30}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        command = node.config.get("command", "")
        timeout = node.config.get("timeout", 30)
        try:
            proc = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return NodeResult(success=proc.returncode == 0,
                              output={"stdout": stdout.decode(), "stderr": stderr.decode(),
                                      "returncode": proc.returncode},
                              logs=[{"message": f"Shell: exit {proc.returncode}"}])
        except asyncio.TimeoutError:
            return NodeResult(success=False, output={"error": "Command timed out"},
                              error=f"Timed out after {timeout}s")


class HTTPRequestNode(BaseNode):
    type = "action.http"
    category = "action"
    label = "HTTP Request"
    description = "Make an HTTP request"
    default_config = {"url": "", "method": "GET", "headers": {}, "body": ""}
    outputs = [{"id": "output", "label": "Response", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        import httpx
        url = node.config.get("url", "")
        method = node.config.get("method", "GET").upper()
        headers = node.config.get("headers", {})
        body = node.config.get("body", "")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(method, url, headers=headers,
                                            content=body if method in ("POST", "PUT", "PATCH") else None)
                return NodeResult(success=resp.is_success, output={
                    "status": resp.status_code, "headers": dict(resp.headers),
                    "body": resp.text,
                }, logs=[{"message": f"HTTP {method} {url} → {resp.status_code}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class FileWriteNode(BaseNode):
    type = "action.file_write"
    category = "action"
    label = "Write File"
    description = "Write content to a file"
    default_config = {"path": "", "content": "", "append": False}
    outputs = [{"id": "output", "label": "File Info", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        path = node.config.get("path", "")
        content = node.config.get("content", "") or str(context.get("input", ""))
        append = node.config.get("append", False)
        try:
            mode = "a" if append else "w"
            with open(path, mode) as f:
                f.write(content)
            return NodeResult(success=True, output={"path": path, "size": len(content), "mode": mode},
                              logs=[{"message": f"Wrote {len(content)}B to {path}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class FileReadNode(BaseNode):
    type = "action.file_read"
    category = "action"
    label = "Read File"
    description = "Read content from a file"
    default_config = {"path": ""}
    outputs = [{"id": "output", "label": "Content", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        path = node.config.get("path", "")
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            return NodeResult(success=True, output=content,
                              logs=[{"message": f"Read {len(content)}B from {path}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class WebSearchNode(BaseNode):
    type = "action.web_search"
    category = "action"
    label = "Web Search"
    description = "Search the web for information"
    default_config = {"num_results": 5}
    outputs = [{"id": "output", "label": "Results", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        query = context.get("input", "")
        try:
            from tools.search_tools import web_search
            results = web_search(query, num_results=node.config.get("num_results", 5))
            return NodeResult(success=True, output=results,
                              logs=[{"message": f"Web search: {query}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class WebScrapeNode(BaseNode):
    type = "action.web_scrape"
    category = "action"
    label = "Web Scrape"
    description = "Extract content from a URL"
    default_config = {"url": ""}
    outputs = [{"id": "output", "label": "Content", "type": "string"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        url = node.config.get("url", "") or str(context.get("input", ""))
        try:
            from tools.web_scrape import scrape_url
            content = scrape_url(url)
            return NodeResult(success=True, output=content,
                              logs=[{"message": f"Scraped {url}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class SendNotificationNode(BaseNode):
    type = "action.notify"
    category = "action"
    label = "Send Notification"
    description = "Send a notification (email, message, etc.)"
    default_config = {"channel": "", "recipient": "", "message": ""}
    outputs = [{"id": "output", "label": "Sent", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        channel = node.config.get("channel", "")
        recipient = node.config.get("recipient", "")
        message = node.config.get("message", "") or str(context.get("input", ""))
        return NodeResult(success=True, output={
            "channel": channel, "recipient": recipient, "sent": True,
        }, logs=[{"message": f"Notification sent via {channel}"}])


class CallToolNode(BaseNode):
    type = "action.call_tool"
    category = "action"
    label = "Call Tool"
    description = "Call a registered AetherOS tool"
    default_config = {"tool": "", "params": {}}
    outputs = [{"id": "output", "label": "Result", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        tool_name = node.config.get("tool", "")
        params = node.config.get("params", {})
        try:
            from model_tools import handle_function_call
            result = handle_function_call(tool_name, json.dumps(params))
            return NodeResult(success=True, output=str(result),
                              logs=[{"message": f"Tool call: {tool_name}"}])
        except Exception as e:
            return NodeResult(success=False, output={"error": str(e)}, error=str(e))


class DatabaseQueryNode(BaseNode):
    type = "action.database"
    category = "action"
    label = "Database Query"
    description = "Execute a database query"
    default_config = {"connection": "", "query": ""}
    outputs = [{"id": "output", "label": "Results", "type": "any"}]

    async def execute(self, node: WorkflowNode, context: dict,
                      workflow: WorkflowConfig, engine=None) -> NodeResult:
        import sqlite3
        conn_str = node.config.get("connection", "sqlite:///:memory:")
        query = node.config.get("query", "")
        if conn_str.startswith("sqlite:///"):
            db_path = conn_str[10:]
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description or []]
                results = [dict(zip(cols, row)) for row in rows]
                conn.close()
                return NodeResult(success=True, output=results,
                                  logs=[{"message": f"DB query: {len(results)} rows"}])
            except Exception as e:
                return NodeResult(success=False, output={"error": str(e)}, error=str(e))
        return NodeResult(success=False, output={"error": "Unsupported database"},
                          error="Only sqlite supported")


def register():
    NodeRegistry.register(ShellCommandNode)
    NodeRegistry.register(HTTPRequestNode)
    NodeRegistry.register(FileWriteNode)
    NodeRegistry.register(FileReadNode)
    NodeRegistry.register(WebSearchNode)
    NodeRegistry.register(WebScrapeNode)
    NodeRegistry.register(SendNotificationNode)
    NodeRegistry.register(CallToolNode)
    NodeRegistry.register(DatabaseQueryNode)


register()
