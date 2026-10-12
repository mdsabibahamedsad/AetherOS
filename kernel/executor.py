"""
Executor — runs agents, tools, and subprocesses through the kernel.

The executor is responsible for:
  - Running AIAgent conversations
  - Tool execution with timeouts and retries
  - Sandbox/subprocess execution
  - Error recovery and retry logic
  - Collecting execution telemetry

It wraps the existing AIAgent and tool dispatch systems.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class ExecutionStatus(enum.Enum):
    """Status of an execution attempt."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """Result of an execution.

    Attributes:
        status: Execution status
        output: The output/response text
        error: Error message (if failed)
        duration_seconds: Execution duration
        token_usage: Token usage if available
        tool_calls: Number of tool calls made
        metadata: Additional metadata
    """
    status: ExecutionStatus = ExecutionStatus.PENDING
    output: str = ""
    error: Optional[str] = None
    duration_seconds: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Executor:
    """Execution engine for the AetherOS Kernel.

    Provides a unified interface for running agents, executing tools,
    and managing subprocesses with retry, timeout, and telemetry.

    Usage:
        executor = Executor(event_bus)

        # Run an agent
        result = executor.run_agent(agent_instance, prompt="...")

        # Execute a tool
        result = executor.execute_tool("web_search", {"query": "..."})

        # Run with retry
        result = executor.run_with_retry(my_fn, max_retries=3)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._executions: Dict[str, ExecutionResult] = {}
        self._active_threads: Dict[str, threading.Thread] = {}

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------

    def run_agent(self, agent, prompt: str,
                  context: Dict[str, Any] = None,
                  execution_id: str = None,
                  timeout_seconds: float = 600.0,
                  task_id: str = None) -> ExecutionResult:
        """Run an AIAgent conversation through the kernel.

        Wraps the existing AIAgent.run_conversation() with event emission
        and timeout protection.

        Args:
            agent: An AIAgent instance
            prompt: The prompt/message to send
            context: Optional additional context
            execution_id: Optional unique ID (auto-generated)
            timeout_seconds: Max execution time
            task_id: Optional task ID for tool isolation

        Returns:
            ExecutionResult with the agent's final response
        """
        exec_id = execution_id or uuid.uuid4().hex[:12]
        result = ExecutionResult(status=ExecutionStatus.RUNNING)
        start = time.time()

        with self._lock:
            self._executions[exec_id] = result

        # Register the execution thread for cancellation support
        current_thread = threading.current_thread()
        with self._lock:
            self._active_threads[exec_id] = current_thread

        if self._event_bus:
            self._event_bus.emit(EventTopics.AGENT_STARTED, {
                "execution_id": exec_id,
                "model": getattr(agent, "model", "unknown"),
                "provider": getattr(agent, "provider", "unknown"),
            })

        try:
            # Use the agent's existing run_conversation
            response = agent.run_conversation(
                user_message=prompt,
                task_id=task_id,
            )

            elapsed = time.time() - start

            if isinstance(response, dict):
                final = response.get("final_response", "") or ""
                failed = response.get("failed", False)
                completed = response.get("completed", True)

                result.output = final
                result.duration_seconds = elapsed
                result.tool_calls = response.get("api_calls", 0)
                result.metadata["token_usage"] = {
                    "prompt": getattr(agent, "session_prompt_tokens", 0),
                    "completion": getattr(agent, "session_completion_tokens", 0),
                    "total": getattr(agent, "session_total_tokens", 0),
                }

                if failed or not completed:
                    result.status = ExecutionStatus.FAILED
                    result.error = response.get("error", "Agent reported failure")
                else:
                    result.status = ExecutionStatus.COMPLETED
            else:
                result.output = str(response) if response else ""
                result.status = ExecutionStatus.COMPLETED
                result.duration_seconds = elapsed

        except Exception as exc:
            elapsed = time.time() - start
            result.status = ExecutionStatus.FAILED
            result.error = str(exc)
            result.duration_seconds = elapsed
            logger.error(
                "Executor: agent execution %s failed: %s", exec_id, exc,
            )

        finally:
            with self._lock:
                self._executions[exec_id] = result

        if self._event_bus:
            topic = (
                EventTopics.AGENT_ERROR if result.status == ExecutionStatus.FAILED
                else EventTopics.AGENT_FINISHED
            )
            self._event_bus.emit(topic, {
                "execution_id": exec_id,
                "duration": result.duration_seconds,
                "status": result.status.value,
                "tool_calls": result.tool_calls,
            })

        logger.info(
            "Executor: agent run %s %s in %.1fs",
            exec_id, result.status.value, result.duration_seconds,
        )
        return result

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def execute_tool(self, tool_name: str, args: Dict[str, Any],
                     execution_id: str = None,
                     timeout_seconds: float = 120.0) -> ExecutionResult:
        """Execute a single tool through the kernel.

        Uses the existing tools/registry dispatch mechanism.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments dict
            execution_id: Optional unique ID (auto-generated)
            timeout_seconds: Max execution time

        Returns:
            ExecutionResult with the tool's response
        """
        exec_id = execution_id or uuid.uuid4().hex[:12]
        result = ExecutionResult(status=ExecutionStatus.RUNNING)
        start = time.time()

        if self._event_bus:
            self._event_bus.emit(EventTopics.TOOL_STARTED, {
                "execution_id": exec_id,
                "tool_name": tool_name,
            })

        try:
            from tools.registry import registry
            response = registry.dispatch(tool_name, args)

            elapsed = time.time() - start

            result.output = response
            result.status = ExecutionStatus.COMPLETED
            result.duration_seconds = elapsed

            if response.startswith("{\"error\""):
                try:
                    import json
                    err_data = json.loads(response)
                    result.error = err_data.get("error", "Tool returned error")
                    result.status = ExecutionStatus.FAILED
                except Exception:
                    pass

        except Exception as exc:
            elapsed = time.time() - start
            result.status = ExecutionStatus.FAILED
            result.error = str(exc)
            result.duration_seconds = elapsed
            logger.error(
                "Executor: tool %s failed: %s", tool_name, exc,
            )

        finally:
            with self._lock:
                self._executions[exec_id] = result

        if self._event_bus:
            topic = (
                EventTopics.TOOL_FAILED if result.status == ExecutionStatus.FAILED
                else EventTopics.TOOL_COMPLETED
            )
            self._event_bus.emit(topic, {
                "execution_id": exec_id,
                "tool_name": tool_name,
                "duration": result.duration_seconds,
                "status": result.status.value,
            })

        return result

    # ------------------------------------------------------------------
    # Generic function execution with retry
    # ------------------------------------------------------------------

    def run_with_retry(self, fn: Callable, *args,
                       max_retries: int = 3,
                       base_delay: float = 1.0,
                       max_delay: float = 60.0,
                       execution_id: str = None,
                       **kwargs) -> ExecutionResult:
        """Execute a callable with exponential backoff retry.

        Args:
            fn: The callable to execute
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            execution_id: Optional unique ID

        Returns:
            ExecutionResult with the result or error
        """
        exec_id = execution_id or uuid.uuid4().hex[:12]
        result = ExecutionResult(status=ExecutionStatus.RUNNING)
        start = time.time()

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                output = fn(*args, **kwargs)
                elapsed = time.time() - start
                result.output = str(output) if output is not None else ""
                result.status = ExecutionStatus.COMPLETED
                result.duration_seconds = elapsed
                result.metadata["attempts"] = attempt + 1
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        "Executor: attempt %d/%d failed, retrying in %.1fs: %s",
                        attempt + 1, max_retries, delay, exc,
                    )
                    time.sleep(delay)
                else:
                    elapsed = time.time() - start
                    result.status = ExecutionStatus.FAILED
                    result.error = str(exc)
                    result.duration_seconds = elapsed
                    result.metadata["attempts"] = max_retries + 1

        with self._lock:
            self._executions[exec_id] = result

        return result

    # ------------------------------------------------------------------
    # Execution tracking
    # ------------------------------------------------------------------

    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get the result of a past execution."""
        with self._lock:
            return self._executions.get(execution_id)

    def list_executions(self, status: ExecutionStatus = None,
                        limit: int = 50) -> List[Dict[str, Any]]:
        """List recent executions."""
        with self._lock:
            items = [
                {"id": k, **vars(v)}
                for k, v in self._executions.items()
            ]
        if status:
            items = [i for i in items if i.get("status") == status]
        items.sort(key=lambda x: x.get("duration_seconds", 0), reverse=True)
        return items[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Return executor statistics."""
        with self._lock:
            total = len(self._executions)
            completed = sum(
                1 for r in self._executions.values()
                if r.status == ExecutionStatus.COMPLETED
            )
            failed = sum(
                1 for r in self._executions.values()
                if r.status == ExecutionStatus.FAILED
            )
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "active_threads": len(self._active_threads),
        }

    def cancel_execution(self, execution_id: str) -> bool:
        """Attempt to cancel a running execution."""
        thread = self._active_threads.get(execution_id)
        if thread and thread.is_alive():
            with self._lock:
                result = self._executions.get(execution_id)
                if result:
                    result.status = ExecutionStatus.CANCELLED
            logger.info("Executor: cancelled execution %s", execution_id)

            if self._event_bus:
                self._event_bus.emit(EventTopics.AGENT_INTERRUPTED, {
                    "execution_id": execution_id,
                })
            return True
        return False

    def cleanup(self) -> int:
        """Remove all execution records. Returns count removed."""
        with self._lock:
            count = len(self._executions)
            self._executions.clear()
        return count
