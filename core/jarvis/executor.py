from __future__ import annotations

import os
import sys
import time
import json
import uuid
import logging
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutorCapability(Enum):
    TERMINAL = "terminal"
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    MCP = "mcp"
    AGENT = "agent"
    SKILL = "skill"
    PYTHON = "python"
    GATEWAY = "gateway"
    DESKTOP = "desktop"
    NETWORK = "network"
    SEARCH = "search"
    VISION = "vision"


@dataclass
class ExecutorTask:
    id: str
    type: str
    description: str = ""
    status: str = "pending"
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    cancel_token: threading.Event = field(default_factory=threading.Event)


class UnifiedExecutor:
    def __init__(self):
        self._tasks: dict[str, ExecutorTask] = {}
        self._lock = threading.Lock()
        self._capabilities: dict[str, bool] = {
            cap.value: True for cap in ExecutorCapability
        }
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, capability: str, handler: Callable):
        self._handlers[capability] = handler
        self._capabilities[capability] = True

    def is_available(self, capability: str) -> bool:
        return self._capabilities.get(capability, False)

    def set_available(self, capability: str, available: bool):
        self._capabilities[capability] = available

    def get_availability(self) -> dict[str, bool]:
        return dict(self._capabilities)

    def create_task(self, task_type: str, description: str = "",
                    metadata: Optional[dict] = None) -> ExecutorTask:
        task = ExecutorTask(
            id=f"exec-{uuid.uuid4().hex[:12]}",
            type=task_type,
            description=description,
            metadata=metadata or {},
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def run_terminal(self, command: str, cwd: Optional[str] = None,
                     timeout: Optional[float] = None,
                     background: bool = False) -> ExecutorTask:
        task = self.create_task("terminal", f"Run: {command[:80]}", {
            "command": command, "cwd": cwd, "background": background
        })
        task.status = "running"
        task.started_at = time.time()

        def _run():
            try:
                result = subprocess.run(
                    command, shell=True, cwd=cwd,
                    capture_output=True, text=True,
                    timeout=timeout if timeout and not background else None,
                )
                task.result = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
                task.status = "completed" if result.returncode == 0 else "failed"
                if result.returncode != 0:
                    task.error = result.stderr[:500]
            except subprocess.TimeoutExpired:
                task.status = "failed"
                task.error = "Command timed out"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                task.completed_at = time.time()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        if not background:
            thread.join(timeout=timeout or 120)
        return task

    def run_python(self, code: str, globals_dict: Optional[dict] = None) -> ExecutorTask:
        task = self.create_task("python", "Execute Python code")
        task.status = "running"
        task.started_at = time.time()
        try:
            local_vars = {}
            exec(code, globals_dict or {}, local_vars)
            task.result = {"locals": {k: str(v) for k, v in local_vars.items() if not k.startswith("_")}}
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        finally:
            task.completed_at = time.time()
        return task

    def run_mcp(self, server: str, tool: str, params: Optional[dict] = None) -> ExecutorTask:
        task = self.create_task("mcp", f"MCP {server}.{tool}", {
            "server": server, "tool": tool, "params": params
        })
        handler = self._handlers.get("mcp")
        if handler:
            try:
                task.status = "running"
                task.started_at = time.time()
                task.result = handler(server=server, tool=tool, params=params)
                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                task.completed_at = time.time()
        else:
            task.status = "failed"
            task.error = "MCP handler not registered"
        return task

    def run_agent(self, agent_type: str, goal: str, context: Optional[dict] = None) -> ExecutorTask:
        task = self.create_task("agent", f"Agent {agent_type}: {goal[:60]}", {
            "agent_type": agent_type, "goal": goal, "context": context
        })
        handler = self._handlers.get("agent")
        if handler:
            try:
                task.status = "running"
                task.started_at = time.time()
                task.result = handler(agent_type=agent_type, goal=goal, context=context)
                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                task.completed_at = time.time()
        else:
            task.status = "failed"
            task.error = "Agent handler not registered"
        return task

    def run_skill(self, skill_name: str, params: Optional[dict] = None) -> ExecutorTask:
        task = self.create_task("skill", f"Skill: {skill_name}", {
            "skill_name": skill_name, "params": params
        })
        handler = self._handlers.get("skill")
        if handler:
            try:
                task.status = "running"
                task.started_at = time.time()
                task.result = handler(skill_name=skill_name, params=params)
                task.status = "completed"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                task.completed_at = time.time()
        else:
            task.status = "failed"
            task.error = "Skill handler not registered"
        return task

    def get_task(self, task_id: str) -> Optional[ExecutorTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_active_tasks(self) -> list[ExecutorTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "running"]

    def get_all_tasks(self) -> list[ExecutorTask]:
        with self._lock:
            return list(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == "running":
                task.cancel_token.set()
                task.status = "cancelled"
                return True
            return False

    def complete_task(self, task_id: str, result: Optional[Any] = None) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed"
                task.result = result
                task.completed_at = time.time()
                return True
            return False

    def fail_task(self, task_id: str, error: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "failed"
                task.error = error
                task.completed_at = time.time()
                return True
            return False
