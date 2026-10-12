from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from aetheros_automation.models.models import ApprovalRequest, Task, TaskStep

logger = logging.getLogger(__name__)

MessageHandler = Callable[..., Any]


class AutomationMCPServer:
    """Minimal MCP-compatible JSON-RPC server over TCP.

    Exposes automation engine capabilities as tools that an MCP client
    (e.g. the model's tool-use loop) can discover and invoke.
    """

    # Mapping of tool name → handler function
    _TOOL_MAP: dict[str, MessageHandler] = {}

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._server: asyncio.AbstractServer | None = None
        self._host = "127.0.0.1"
        self._port = 9100

        self._build_tool_map()

    def _build_tool_map(self) -> None:
        self._TOOL_MAP = {
            "automation_run_task": self._handle_run_task,
            "automation_create_task": self._handle_create_task,
            "automation_list_tasks": self._handle_list_tasks,
            "automation_cancel_task": self._handle_cancel_task,
            "automation_get_status": self._handle_get_status,
            "automation_get_approvals": self._handle_get_approvals,
            "automation_approve": self._handle_approve,
            "automation_emergency_stop": self._handle_emergency_stop,
            "automation_get_task": self._handle_get_task,
            "automation_pause_task": self._handle_pause_task,
            "automation_resume_task": self._handle_resume_task,
        }

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    async def start(self, host: str = "127.0.0.1", port: int = 9100) -> None:
        self._host = host
        self._port = port

        self._server = await asyncio.start_server(
            self._client_connected,
            host=host,
            port=port,
        )

        addr = self._server.sockets[0].getsockname() if self._server.sockets else (host, port)
        logger.info("MCP server listening on %s:%s", *addr)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("MCP server stopped")

    # ------------------------------------------------------------------
    # connection handler
    # ------------------------------------------------------------------

    async def _client_connected(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername", ("unknown", 0))
        logger.debug("MCP client connected: %s", peer)

        try:
            while True:
                raw = await reader.readline()
                if not raw:
                    break

                line = raw.decode("utf-8").strip()
                if not line:
                    continue

                response = await self._handle_request(line)
                if response is not None:
                    payload = json.dumps(response, default=str) + "\n"
                    writer.write(payload.encode("utf-8"))
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        except ConnectionResetError:
            logger.debug("MCP client disconnected: %s", peer)
        except Exception:
            logger.exception("MCP connection error: %s", peer)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # request dispatch
    # ------------------------------------------------------------------

    async def _handle_request(self, raw: str) -> dict[str, Any] | None:
        """Parse and dispatch a JSON-RPC request.

        Expected format:
          {"jsonrpc": "2.0", "method": "<tool_name>", "params": {...}, "id": <id>}
        """
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            return self._error(None, -32700, f"Parse error: {exc}")

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "list_tools":
            return self._response(req_id, self._list_tools())

        handler = self._TOOL_MAP.get(method)
        if handler is None:
            return self._error(req_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(params)
            return self._response(req_id, result)
        except Exception as exc:
            logger.exception("Handler failed for %s", method)
            return self._error(req_id, -32603, str(exc))

    # ------------------------------------------------------------------
    # tool handlers
    # ------------------------------------------------------------------

    async def _handle_run_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("task_id", "")
        task = self._engine.get_task(task_id)
        if task is None:
            return {"error": f"Task {task_id} not found"}

        result = await self._engine.run_task(task)
        return {"task_id": result.id, "status": result.status.value if result.status else "unknown"}

    async def _handle_create_task(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "MCP Task")
        description = params.get("description", "")
        agent_str = params.get("agent", "coordinator")

        from aetheros_automation.models.models import AgentRole

        agent_role = AgentRole.COORDINATOR
        try:
            agent_role = AgentRole(agent_str)
        except ValueError:
            pass

        steps_raw = params.get("steps", [])
        steps = [
            TaskStep(
                id=f"step_{i}",
                name=s.get("name", ""),
                action=s.get("action", ""),
                params=s.get("params", {}),
            )
            for i, s in enumerate(steps_raw)
        ]

        task = self._engine.create_task(
            name=name,
            description=description,
            agent_role=agent_role,
            steps=steps,
        )
        return {"task_id": task.id, "name": task.name, "status": task.status.value if task.status else "pending"}

    async def _handle_list_tasks(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        status_str = params.get("status")
        from aetheros_automation.models.models import TaskStatus

        status_filter = None
        if status_str:
            try:
                status_filter = TaskStatus(status_str)
            except ValueError:
                return [{"error": f"Unknown status: {status_str}"}]

        tasks = self._engine.list_tasks(status_filter)
        return [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value if t.status else "unknown",
                "agent": t.agent.value if t.agent else None,
                "progress": t.progress,
                "created_at": t.created_at,
            }
            for t in tasks
        ]

    async def _handle_cancel_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("task_id", "")
        if not task_id:
            return {"error": "task_id is required"}
        await self._engine.cancel_task(task_id)
        return {"success": True, "task_id": task_id}

    async def _handle_get_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("task_id", "")
        task = self._engine.get_task(task_id)
        if task is None:
            return {"error": f"Task {task_id} not found"}
        return {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value if task.status else "unknown",
            "agent": task.agent.value if task.agent else None,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "action": s.action,
                    "status": s.status.value if s.status else "unknown",
                }
                for s in task.steps
            ],
            "progress": task.progress,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    async def _handle_pause_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("task_id", "")
        await self._engine.pause_task(task_id)
        return {"success": True, "task_id": task_id}

    async def _handle_resume_task(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params.get("task_id", "")
        await self._engine.resume_task(task_id)
        return {"success": True, "task_id": task_id}

    async def _handle_get_status(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        return self._engine.get_status()

    async def _handle_get_approvals(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        _ = params
        mgr = getattr(self._engine, "approvals", None)
        if mgr is None:
            return []
        pending = await mgr.get_pending()
        return [
            {
                "id": a.id,
                "task_id": a.task_id,
                "action": a.action,
                "description": a.description,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in pending
        ]

    async def _handle_approve(self, params: dict[str, Any]) -> dict[str, Any]:
        approval_id = params.get("approval_id", "")
        approved = params.get("approved", True)
        reason = params.get("reason", "")

        mgr = getattr(self._engine, "approvals", None)
        if mgr is None:
            return {"error": "Approval manager not available"}

        result = await mgr.respond(approval_id, bool(approved), reason)
        return {"success": result, "approval_id": approval_id}

    async def _handle_emergency_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        _ = params
        await self._engine.stop()
        return {"success": True, "message": "Emergency stop executed"}

    # ------------------------------------------------------------------
    # tool listing
    # ------------------------------------------------------------------

    def _list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "automation_run_task",
                "description": "Execute a task that has already been created",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the task to run"}
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "automation_create_task",
                "description": "Create a new automation task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "agent": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "action": {"type": "string"},
                                    "params": {"type": "object"},
                                },
                            },
                        },
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "automation_list_tasks",
                "description": "List all tasks, optionally filtered by status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Optional status filter"}
                    },
                },
            },
            {
                "name": "automation_cancel_task",
                "description": "Cancel a running or pending task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"}
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "automation_get_status",
                "description": "Get overall engine status",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "automation_get_approvals",
                "description": "List pending approval requests",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "automation_approve",
                "description": "Approve or deny a pending approval request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "approval_id": {"type": "string"},
                        "approved": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": ["approval_id", "approved"],
                },
            },
            {
                "name": "automation_emergency_stop",
                "description": "Immediately stop the engine and cancel all tasks",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "automation_get_task",
                "description": "Get detailed information about a specific task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"}
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "automation_pause_task",
                "description": "Pause a running task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"}
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "automation_resume_task",
                "description": "Resume a paused task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"}
                    },
                    "required": ["task_id"],
                },
            },
        ]

    # ------------------------------------------------------------------
    # JSON-RPC helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _response(req_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
