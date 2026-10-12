"""Tool Calling — universal interface for filesystem, browser, desktop, terminal, python, gateway, MCP, voice, vision.

Everything through one unified API.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.tools")


class ToolDomain(enum.Enum):
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    DESKTOP = "desktop"
    TERMINAL = "terminal"
    PYTHON = "python"
    GATEWAY = "gateway"
    MCP = "mcp"
    VOICE = "voice"
    VISION = "vision"
    CODE = "code"
    WEB = "web"
    CUSTOM = "custom"


@dataclass
class ToolCall:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: ToolDomain = ToolDomain.CUSTOM
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 60.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "name": self.name,
            "arguments": self.arguments,
            "metadata": self.metadata,
            "timeout": self.timeout,
        }


@dataclass
class ToolResult:
    success: bool = True
    output: str = ""
    error: str = ""
    data: Any = None
    elapsed_ms: float = 0.0
    tool_call_id: str = ""
    permission_denied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "tool_call_id": self.tool_call_id,
            "permission_denied": self.permission_denied,
        }


ToolHandler = Callable[[ToolCall], ToolResult]


class ToolCallingInterface:
    """Universal tool calling interface.

    All tools — filesystem, browser, desktop, terminal, python, gateway,
    MCP, voice, vision — go through this one API.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: Dict[str, ToolHandler] = {}
        self._domain_handlers: Dict[ToolDomain, Dict[str, ToolHandler]] = {}
        self._history: List[ToolResult] = []
        self._max_history: int = 500
        self._permissions: Dict[str, bool] = {}
        self._max_concurrent: int = 10
        self._active_calls: int = 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(
        self,
        name: str,
        handler: ToolHandler,
        domain: ToolDomain = ToolDomain.CUSTOM,
    ) -> None:
        with self._lock:
            self._handlers[name] = handler
            if domain not in self._domain_handlers:
                self._domain_handlers[domain] = {}
            self._domain_handlers[domain][name] = handler
        logger.info("Tool registered: %s (%s)", name, domain.value)

    def register_domain_handler(
        self,
        domain: ToolDomain,
        handler: ToolHandler,
    ) -> None:
        self.register_tool(f"domain:{domain.value}", handler, domain)

    def unregister_tool(self, name: str) -> bool:
        with self._lock:
            return self._handlers.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        domain: Optional[ToolDomain] = None,
        timeout: float = 60.0,
    ) -> ToolResult:
        tool_call = ToolCall(
            name=name,
            domain=domain or ToolDomain.CUSTOM,
            arguments=arguments or {},
            timeout=timeout,
        )
        return self.execute_call(tool_call)

    def execute_call(self, tool_call: ToolCall) -> ToolResult:
        with self._lock:
            if self._active_calls >= self._max_concurrent:
                return ToolResult(success=False, error="Max concurrent tool calls reached", tool_call_id=tool_call.id)
            self._active_calls += 1

        start = time.monotonic()
        result = ToolResult(tool_call_id=tool_call.id)

        try:
            handler = self._find_handler(tool_call)
            if not handler:
                raise ValueError(f"Tool not found: {tool_call.name}")

            if not self._check_permission(tool_call.name):
                result.permission_denied = True
                result.error = f"Permission denied for tool: {tool_call.name}"
                result.success = False
                return result

            raw_result = handler(tool_call)

            if isinstance(raw_result, ToolResult):
                result = raw_result
            else:
                result.success = True
                result.output = str(raw_result)
                result.data = raw_result

        except Exception as exc:
            result.success = False
            result.error = str(exc)
            logger.error("Tool call failed: %s: %s", tool_call.name, exc)

        result.elapsed_ms = (time.monotonic() - start) * 1000

        with self._lock:
            self._active_calls -= 1
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        return result

    def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        return [self.execute_call(tc) for tc in tool_calls]

    # ------------------------------------------------------------------
    # Domain tools
    # ------------------------------------------------------------------

    def list_tools(self, domain: Optional[ToolDomain] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if domain:
                handlers = self._domain_handlers.get(domain, {})
                return [{"name": n, "domain": domain.value} for n in handlers]
            return [{"name": n, "domain": "custom"} for n in self._handlers]

    def list_domains(self) -> List[str]:
        with self._lock:
            return [d.value for d in self._domain_handlers]

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def grant_permission(self, tool_name: str) -> None:
        with self._lock:
            self._permissions[tool_name] = True

    def revoke_permission(self, tool_name: str) -> None:
        with self._lock:
            self._permissions[tool_name] = False

    def _check_permission(self, tool_name: str) -> bool:
        with self._lock:
            perm = self._permissions.get(tool_name)
            return True if perm is None else perm

    # ------------------------------------------------------------------
    # Built-in tools
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        self.register_tool("echo", lambda tc: ToolResult(success=True, output=json.dumps(tc.arguments)), ToolDomain.CUSTOM)
        self.register_tool("ping", lambda tc: ToolResult(success=True, output="pong"), ToolDomain.CUSTOM)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 20) -> List[ToolResult]:
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_handler(self, tool_call: ToolCall) -> Optional[ToolHandler]:
        with self._lock:
            handler = self._handlers.get(tool_call.name)
            if handler:
                return handler
            domain_dict = self._domain_handlers.get(tool_call.domain)
            if domain_dict:
                return domain_dict.get(tool_call.name)
            return None

    def set_max_concurrent(self, count: int) -> None:
        with self._lock:
            self._max_concurrent = count

    def health_check(self) -> bool:
        with self._lock:
            return len(self._handlers) > 0

    def summary(self) -> str:
        with self._lock:
            domains = len(self._domain_handlers)
            total_tools = len(self._handlers)
            history = len(self._history)
            success_rate = sum(1 for r in self._history if r.success) / max(len(self._history), 1) * 100
        return (
            f"Tool Calling Interface: {total_tools} tools across {domains} domains, "
            f"{history} calls ({success_rate:.0f}% success)"
        )