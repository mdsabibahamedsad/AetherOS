"""Tool Runtime Manager.

Central registry and lifecycle manager for all tool runtimes.
Handles registration, loading, unloading, health checks, permissions,
versioning, execution, timeouts, cancellation, and metrics.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import enum
import json
import logging
import signal
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolStatus,
    ToolRiskLevel,
    ToolCategory,
    ToolRegistryAdapter,
)
from tool_runtime.permission import PermissionSystem, RiskLevel, get_permission_system
from tool_runtime.safety import SafetyEngine, get_safety_engine
from tool_runtime.observability import ObservabilityCollector, get_observability_collector

logger = logging.getLogger(__name__)


class RuntimeState(enum.Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"


class ExecutionRequest:
    """Captures a pending tool execution request for tracking and approval."""

    def __init__(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
        request_id: Optional[str] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.tool_name = tool_name
        self.params = params
        self.context = context
        self.created_at = time.time()
        self.approved: Optional[bool] = None
        self.result: Optional[ToolResult] = None
        self.future: Optional[concurrent.futures.Future] = None


class LegacyToolWrapper(ToolInterface):
    """Wraps an existing tools/registry.py ToolEntry into ToolInterface."""

    def __init__(self, entry):
        from tool_runtime.interface import ToolCategory, ToolRiskLevel

        cat = self._detect_category(entry.name, entry.toolset)
        risk = self._detect_risk(entry.name, entry.toolset)
        meta = ToolMetadata(
            id=entry.name,
            name=entry.name,
            description=entry.description or entry.schema.get("description", ""),
            category=cat,
            risk_level=risk,
            version="1.0.0",
            requires_approval=risk in (ToolRiskLevel.SYSTEM, ToolRiskLevel.ADMIN, ToolRiskLevel.CREDENTIAL),
            timeout_seconds=120.0,
        )
        super().__init__(meta)
        self._entry = entry

    def _detect_category(self, name: str, toolset: str) -> ToolCategory:
        toolset_map = {
            "file": ToolCategory.FILESYSTEM,
            "terminal": ToolCategory.TERMINAL,
            "code_execution": ToolCategory.PYTHON,
            "browser": ToolCategory.BROWSER,
            "desktop": ToolCategory.DESKTOP,
        }
        for prefix, cat in toolset_map.items():
            if toolset == prefix or name.startswith(prefix):
                return cat
        name_map = {
            "read": ToolCategory.FILESYSTEM, "write": ToolCategory.FILESYSTEM,
            "edit": ToolCategory.FILESYSTEM, "search": ToolCategory.FILESYSTEM,
            "git": ToolCategory.GIT, "terminal": ToolCategory.TERMINAL,
            "browser": ToolCategory.BROWSER, "web": ToolCategory.UTILITY,
        }
        for prefix, cat in name_map.items():
            if name.startswith(prefix):
                return cat
        return ToolCategory.UTILITY

    def _detect_risk(self, name: str, toolset: str) -> ToolRiskLevel:
        if any(kw in name for kw in ("delete", "remove", "format", "shutdown", "write")):
            return ToolRiskLevel.WRITE
        if any(kw in name for kw in ("exec", "terminal", "shell", "run", "bash")):
            return ToolRiskLevel.EXECUTE
        if any(kw in name for kw in ("credential", "token", "key", "secret", "password")):
            return ToolRiskLevel.CREDENTIAL
        if any(kw in name for kw in ("admin", "sudo", "install", "system")):
            return ToolRiskLevel.ADMIN
        if any(kw in name for kw in ("web", "http", "fetch", "download", "network")):
            return ToolRiskLevel.NETWORK
        return ToolRiskLevel.READ

    def schema(self) -> Dict[str, Any]:
        return dict(self._entry.schema)

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        schema = self._entry.schema
        required = schema.get("parameters", {}).get("required", [])
        for req in required:
            if req not in params:
                errors.append(f"Missing required parameter: {req}")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        try:
            start = time.time()
            result_str = self._entry.handler(params, **context)
            elapsed = (time.time() - start) * 1000
            data = json.loads(result_str) if isinstance(result_str, str) else result_str
            if isinstance(data, dict) and data.get("error"):
                return ToolResult.fail(data["error"], duration_ms=elapsed)
            return ToolResult.ok(data, duration_ms=elapsed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000 if 'start' in dir() else 0
            return ToolResult.fail(f"{type(e).__name__}: {e}", duration_ms=elapsed)

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["toolset"] = self._entry.toolset
        base["requires_env"] = list(self._entry.requires_env)
        return base


class ToolRuntimeManager:
    """Central manager for all tool runtimes.

    Responsibilities:
        - Register and load tools
        - Unload tools
        - Health checks
        - Permission verification
        - Versioning
        - Execution with timeouts and cancellation
        - Metrics collection
    """

    def __init__(self):
        self._state = RuntimeState.STOPPED
        self._runtimes: Dict[str, ToolInterface] = {}
        self._permission = get_permission_system()
        self._safety = get_safety_engine()
        self._observability = get_observability_collector()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=20, thread_name_prefix="tool_runtime"
        )
        self._running: Dict[str, ExecutionRequest] = {}
        self._history: List[Dict[str, Any]] = []
        self._max_history = 10000
        self._lock = threading.RLock()
        self._adapter: Optional[ToolRegistryAdapter] = None
        self._start_time: Optional[float] = None

    # --- Lifecycle ---

    def start(self) -> None:
        with self._lock:
            if self._state == RuntimeState.RUNNING:
                return
            self._state = RuntimeState.STARTING
            logger.info("Tool Runtime Manager starting...")
            self._adapter = ToolRegistryAdapter()
            legacy_tools = self._adapter.wrap_all()
            for name, tool in legacy_tools.items():
                self._runtimes[name] = tool
            self._start_time = time.time()
            self._state = RuntimeState.RUNNING
            logger.info("Tool Runtime Manager started with %d tools", len(self._runtimes))

    def stop(self) -> None:
        with self._lock:
            self._state = RuntimeState.STOPPING
            logger.info("Tool Runtime Manager stopping...")
            for req_id, req in list(self._running.items()):
                if req.future and not req.future.done():
                    req.future.cancel()
            self._executor.shutdown(wait=False)
            self._runtimes.clear()
            self._state = RuntimeState.STOPPED
            logger.info("Tool Runtime Manager stopped")

    @property
    def state(self) -> RuntimeState:
        return self._state

    # --- Runtime Registration ---

    def register_runtime(self, runtime: ToolInterface) -> None:
        with self._lock:
            self._runtimes[runtime.id()] = runtime
            logger.info("Registered runtime: %s (%s)", runtime.name(), runtime.id())

    def unregister_runtime(self, runtime_id: str) -> Optional[ToolInterface]:
        with self._lock:
            runtime = self._runtimes.pop(runtime_id, None)
            if runtime:
                logger.info("Unregistered runtime: %s", runtime_id)
            return runtime

    def get_runtime(self, tool_name: str) -> Optional[ToolInterface]:
        with self._lock:
            return self._runtimes.get(tool_name)

    def list_runtimes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": r.id(),
                    "name": r.name(),
                    "description": r.description(),
                    "category": r.metadata.category.value,
                    "risk_level": r.metadata.risk_level.value,
                    "version": r.metadata.version,
                    "requires_approval": r.metadata.requires_approval,
                }
                for r in self._runtimes.values()
            ]

    def get_runtime_count(self) -> int:
        with self._lock:
            return len(self._runtimes)

    # --- Health ---

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._runtimes)
            healthy = 0
            unhealthy = []
            for name, runtime in self._runtimes.items():
                try:
                    h = runtime.health()
                    if h.get("healthy", False):
                        healthy += 1
                    else:
                        unhealthy.append(name)
                except Exception as e:
                    unhealthy.append(f"{name}: {e}")
            return {
                "state": self._state.value,
                "total_runtimes": total,
                "healthy_runtimes": healthy,
                "unhealthy_runtimes": unhealthy,
                "running_executions": len(self._running),
                "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
                "history_count": len(self._history),
            }

    # --- Execution ---

    def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
        request_id: Optional[str] = None,
    ) -> ToolResult:
        context = context or {}
        request = ExecutionRequest(tool_name, params, context, request_id)
        runtime = self.get_runtime(tool_name)
        if not runtime:
            return ToolResult.fail(f"Unknown tool: {tool_name}")

        obs_start = time.time()

        # 1. Validate
        validation_errors = runtime.validate(params)
        if validation_errors:
            return ToolResult.fail(f"Validation errors: {'; '.join(validation_errors)}")

        # 2. Authorize
        authorized, reason = runtime.authorize(context)
        if not authorized:
            return ToolResult.fail(f"Not authorized: {reason or 'Access denied'}")

        # 3. Permission check
        perm_result = self._permission.check(tool_name, runtime.metadata, context)
        if not perm_result.allowed:
            return ToolResult.fail(f"Permission denied: {perm_result.reason}")

        # 4. Safety check
        safety_result = self._safety.check(tool_name, params, runtime.metadata)
        if not safety_result.safe:
            return ToolResult.fail(
                f"Safety block: {safety_result.reason}",
                metadata={"safety_verdict": safety_result.to_dict()},
            )

        # 5. Approval if needed
        if runtime.metadata.requires_approval:
            self._observability.record_approval_request(tool_name, request.request_id)

        # 6. Execute
        timeout = timeout_seconds or runtime.metadata.timeout_seconds
        with self._lock:
            self._running[request.request_id] = request

        try:
            future = self._executor.submit(runtime.execute, params, context)
            request.future = future
            result = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            result = ToolResult.timeout(f"Tool {tool_name} timed out after {timeout}s")
        except Exception as e:
            result = ToolResult.fail(f"Execution error: {type(e).__name__}: {e}")
        finally:
            with self._lock:
                self._running.pop(request.request_id, None)

        result.metadata["tool_name"] = tool_name
        result.metadata["request_id"] = request.request_id

        obs_elapsed = (time.time() - obs_start) * 1000
        self._observability.record_execution(
            tool_name=tool_name,
            success=result.success,
            duration_ms=obs_elapsed,
            category=runtime.metadata.category.value,
            risk_level=runtime.metadata.risk_level.value,
        )

        self._add_history(request, result)
        return result

    def execute_async(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> str:
        """Submit execution and return a request_id for later status/cancel."""
        context = context or {}
        request = ExecutionRequest(tool_name, params, context)
        with self._lock:
            self._running[request.request_id] = request
        future = self._executor.submit(self.execute, tool_name, params, context, timeout_seconds, request.request_id)
        request.future = future
        return request.request_id

    def get_execution_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            req = self._running.get(request_id)
            if req:
                return {
                    "request_id": req.request_id,
                    "tool_name": req.tool_name,
                    "status": "running" if req.future and not req.future.done() else "completed",
                    "created_at": req.created_at,
                }
            return None

    def cancel_execution(self, request_id: str) -> bool:
        with self._lock:
            req = self._running.get(request_id)
            if req and req.future and not req.future.done():
                cancelled = req.future.cancel()
                if cancelled:
                    logger.info("Cancelled execution %s (%s)", request_id, req.tool_name)
                return cancelled
            return False

    def _add_history(self, request: ExecutionRequest, result: ToolResult) -> None:
        entry = {
            "request_id": request.request_id,
            "tool_name": request.tool_name,
            "params": request.params,
            "success": result.success,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": result.status.value,
        }
        with self._lock:
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        tool_name: Optional[str] = None,
        success_only: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self._history)
        if tool_name:
            entries = [e for e in entries if e["tool_name"] == tool_name]
        if success_only is not None:
            entries = [e for e in entries if e["success"] == success_only]
        return entries[offset:offset + limit]

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._history)
            if total == 0:
                return {"total_executions": 0}
            successes = sum(1 for h in self._history if h["success"])
            failures = total - successes
            durations = [h["duration_ms"] for h in self._history]
            return {
                "total_executions": total,
                "successful": successes,
                "failed": failures,
                "success_rate": round(successes / total * 100, 2) if total > 0 else 0,
                "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
            }


# Global singleton
_runtime_manager_instance: Optional[ToolRuntimeManager] = None


def get_runtime_manager() -> ToolRuntimeManager:
    global _runtime_manager_instance
    if _runtime_manager_instance is None:
        _runtime_manager_instance = ToolRuntimeManager()
    return _runtime_manager_instance
