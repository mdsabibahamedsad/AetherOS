from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowNodeType(Enum):
    OPEN_URL = "open_url"
    SEARCH = "search"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    EXTRACT = "extract"
    SCREENSHOT = "screenshot"
    NAVIGATE = "navigate"
    CONDITION = "condition"
    LOOP = "loop"
    VARIABLE = "variable"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    WEBHOOK = "webhook"
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    SAVE_FILE = "save_file"
    EXTRACT_DATA = "extract_data"
    FILTER = "filter"


@dataclass
class WorkflowNode:
    id: str
    type: WorkflowNodeType
    label: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    connections: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    id: str
    name: str
    nodes: list[WorkflowNode] = field(default_factory=list)
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "draft"
    schedule: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class WorkflowExecution:
    id: str
    workflow_id: str
    status: str = "pending"
    current_node_id: str = ""
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


class BrowserWorkflowEngine:
    def __init__(self, browser_facade):
        self._browser_facade = browser_facade
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._variables: dict[str, Any] = {}

    def create_workflow(self, name: str, description: str = "") -> Workflow:
        wf = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        self._workflows[wf.id] = wf
        return wf

    def add_node(self, workflow_id: str, node_type: WorkflowNodeType, label: str = "", config: dict | None = None) -> WorkflowNode | None:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return None
        node = WorkflowNode(
            id=str(uuid.uuid4()),
            type=node_type,
            label=label or node_type.value,
            config=config or {},
        )
        wf.nodes.append(node)
        wf.updated_at = datetime.utcnow().isoformat()
        return node

    def connect_nodes(self, workflow_id: str, from_node_id: str, to_node_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return False
        from_node = next((n for n in wf.nodes if n.id == from_node_id), None)
        if from_node is None:
            return False
        if to_node_id not in from_node.connections:
            from_node.connections.append(to_node_id)
        wf.updated_at = datetime.utcnow().isoformat()
        return True

    def remove_node(self, workflow_id: str, node_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return False
        wf.nodes = [n for n in wf.nodes if n.id != node_id]
        for n in wf.nodes:
            n.connections = [c for c in n.connections if c != node_id]
        wf.updated_at = datetime.utcnow().isoformat()
        return True

    def update_node_config(self, workflow_id: str, node_id: str, config: dict) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return False
        node = next((n for n in wf.nodes if n.id == node_id), None)
        if node is None:
            return False
        node.config.update(config)
        wf.updated_at = datetime.utcnow().isoformat()
        return True

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    def set_schedule(self, workflow_id: str, schedule: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return False
        wf.schedule = schedule
        wf.updated_at = datetime.utcnow().isoformat()
        return True

    async def execute_workflow(self, workflow_id: str, session_id: str, variables: dict | None = None) -> WorkflowExecution:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            status="running",
            started_at=datetime.utcnow().isoformat(),
        )
        self._executions[execution.id] = execution

        self._variables = dict(variables or {})
        browser = self._browser_facade.browser_manager._sessions.get(session_id)

        try:
            for node in wf.nodes:
                execution.current_node_id = node.id
                result = await self._execute_node(node, browser, session_id)
                execution.results[node.id] = result

                if node.type == WorkflowNodeType.CONDITION and not result.get("passed", True):
                    break

                if node.type == WorkflowNodeType.LOOP:
                    max_iterations = node.config.get("max_iterations", 10)
                    for _ in range(max_iterations):
                        loop_result = await self._execute_node(node, browser, session_id)
                        execution.results[f"{node.id}_loop_{_}"] = loop_result
                        if not loop_result.get("continue", True):
                            break

            execution.status = "completed"
        except Exception as e:
            execution.status = "failed"
            execution.errors.append(str(e))
            logger.error("Workflow execution failed: %s", e)
        finally:
            execution.completed_at = datetime.utcnow().isoformat()

        return execution

    async def _execute_node(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        try:
            handler = getattr(self, f"_handle_{node.type.value}", None)
            if handler is None:
                return {"error": f"No handler for {node.type.value}"}
            return await handler(node, browser, session_id)
        except Exception as e:
            logger.error("Node %s failed: %s", node.id, e)
            raise

    async def _handle_open_url(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        url = self._resolve_variables(node.config.get("url", ""))
        if browser is None:
            return {"error": "No active browser"}
        await browser.navigate(url)
        return {"url": url, "status": "navigated"}

    async def _handle_search(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        query = self._resolve_variables(node.config.get("query", ""))
        if browser is None:
            return {"error": "No active browser"}
        search_url = self._browser_facade.web_search_manager.get_search_url(query)
        await browser.navigate(search_url)
        return {"query": query, "url": search_url}

    async def _handle_click(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        selector = node.config.get("selector", "")
        if browser is None:
            return {"error": "No active browser"}
        await browser.click(selector)
        return {"selector": selector}

    async def _handle_type(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        selector = node.config.get("selector", "")
        text = self._resolve_variables(node.config.get("text", ""))
        if browser is None:
            return {"error": "No active browser"}
        await browser.type_text(selector, text)
        return {"selector": selector, "text_length": len(text)}

    async def _handle_select(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        selector = node.config.get("selector", "")
        value = node.config.get("value", "")
        if browser is None:
            return {"error": "No active browser"}
        await browser.execute_js(f"document.querySelector('{selector}').value = '{value}'")
        return {"selector": selector, "value": value}

    async def _handle_scroll(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        selector = node.config.get("selector", "")
        if browser is None:
            return {"error": "No active browser"}
        await browser.scroll_to(selector)
        return {"selector": selector}

    async def _handle_wait(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        seconds = node.config.get("seconds", 1)
        await asyncio.sleep(seconds)
        return {"waited": seconds}

    async def _handle_extract(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        selector = node.config.get("selector", "")
        attribute = node.config.get("attribute", "text")
        if browser is None:
            return {"error": "No active browser"}
        if attribute == "text":
            text = await browser.get_text(selector)
            return {"selector": selector, "value": text}
        result = await browser.execute_js(
            f"() => document.querySelector('{selector}')?.getAttribute('{attribute}')"
        )
        return {"selector": selector, "value": result}

    async def _handle_screenshot(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        if browser is None:
            return {"error": "No active browser"}
        screenshot_bytes = await browser.screenshot()
        return {"screenshot_size": len(screenshot_bytes)}

    async def _handle_navigate(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        direction = node.config.get("direction", "forward")
        if browser is None:
            return {"error": "No active browser"}
        if direction == "back":
            await browser.execute_js("() => window.history.back()")
        else:
            await browser.execute_js("() => window.history.forward()")
        return {"direction": direction}

    async def _handle_condition(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        expression = node.config.get("expression", "")
        try:
            result = bool(eval(expression, {"__builtins__": {}}, self._variables))
            return {"expression": expression, "passed": result, "result": result}
        except Exception as e:
            return {"expression": expression, "passed": False, "error": str(e)}

    async def _handle_variable(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        name = node.config.get("name", "")
        value = node.config.get("value", "")
        self._variables[name] = value
        return {"variable": name, "value": value}

    async def _handle_download(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        url = self._resolve_variables(node.config.get("url", ""))
        dest = node.config.get("destination", "")
        if browser is None:
            return {"error": "No active browser"}
        await browser.download_file(url, dest)
        return {"url": url, "destination": dest}

    async def _handle_webhook(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        webhook_url = node.config.get("webhook_url", "")
        payload = node.config.get("payload", {})
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=30)
        return {"status_code": resp.status_code, "url": webhook_url}

    async def _handle_save_file(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        content = self._resolve_variables(node.config.get("content", ""))
        filepath = node.config.get("filepath", "")
        from pathlib import Path
        Path(filepath).write_text(content, encoding="utf-8")
        return {"filepath": filepath, "size": len(content)}

    async def _handle_send_notification(self, node: WorkflowNode, browser, session_id: str) -> dict[str, Any]:
        message = self._resolve_variables(node.config.get("message", ""))
        logger.info("Workflow notification: %s", message)
        return {"message": message}

    def _resolve_variables(self, text: str) -> str:
        if not isinstance(text, str):
            return str(text)
        for key, val in self._variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(val))
        return text

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    def list_executions(self, workflow_id: str | None = None) -> list[WorkflowExecution]:
        if workflow_id:
            return [e for e in self._executions.values() if e.workflow_id == workflow_id]
        return list(self._executions.values())

    def to_workflow_dict(self, workflow_id: str) -> dict | None:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return None
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "label": n.label,
                    "config": n.config,
                    "position": n.position,
                    "connections": n.connections,
                }
                for n in wf.nodes
            ],
            "schedule": wf.schedule,
            "status": wf.status,
            "created_at": wf.created_at,
            "updated_at": wf.updated_at,
            "tags": wf.tags,
        }
