from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import time
from typing import Any, Callable

from aetheros_automation.models.models import TaskStatus
from aetheros_automation.orchestrator.types import (
    AgentAssignment,
    OrchestrationTask,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 600.0
_POLL_INTERVAL = 5.0
_DEFAULT_MAX_ITERATIONS = 30


def _looks_like_structured_error(text: str) -> bool:
    """Cheap heuristic: an output that is mostly an exception/traceback should
    not be treated as a successful task result."""
    lowered = (text or "").lower()
    markers = (
        "traceback (most recent call last)",
        "error: ",
        "exception: ",
        "failed to ",
        "unexpected error",
    )
    return any(marker in lowered for marker in markers)


class AgentExecutionEngine:
    """Real execution engine for ``TaskOrchestrator``.

    Unlike the legacy ``ExecutionEngine`` (which simulated tool calls), this
    engine spawns an actual ``AIAgent`` per task and runs
    ``run_conversation()`` under a hard timeout.  It is interface-compatible
    with ``ExecutionEngine`` so it can be dropped straight into
    ``TaskOrchestrator(execution_engine=...)``::

        orchestrator = TaskOrchestrator(execution_engine=AgentExecutionEngine())

    Both the agent constructor and the run loop are injectable so tests can
    exercise the engine without touching the network.
    """

    def __init__(
        self,
        agent_factory: Callable | None = None,
        runner: Callable | None = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        poll_interval: float = _POLL_INTERVAL,
        quiet_mode: bool = True,
        enabled_toolsets: list[str] | None = None,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        system_prompt_builder: Callable | None = None,
        emit_events: bool = True,
    ):
        self._agent_factory = agent_factory
        self._runner = runner
        self._timeout_seconds = timeout_seconds
        self._poll_interval = poll_interval
        self._quiet_mode = quiet_mode
        self._enabled_toolsets = list(enabled_toolsets) if enabled_toolsets else None
        self._max_iterations = max_iterations
        self._system_prompt_builder = system_prompt_builder
        self._emit_events = emit_events

        self._execution_contexts: dict[str, dict[str, Any]] = {}
        self._event_handlers: dict[str, list[Callable]] = {}

    # ── event bus (mirrors ExecutionEngine so orchestrator bridging works) ──

    def on(self, event: str, handler: Callable):
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable):
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass

    def _emit(self, event: str, data: dict[str, Any]):
        if not self._emit_events:
            return
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                logger.exception("Event handler failed for %s", event)

    def get_execution_context(self, task_id: str, agent_id: str) -> dict[str, Any] | None:
        return self._execution_contexts.get(f"{task_id}:{agent_id}")

    def get_all_contexts(self) -> dict[str, dict[str, Any]]:
        return dict(self._execution_contexts)

    # ── execution ────────────────────────────────────────────────────────

    async def execute_task(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = context or {}
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        self._emit("tool.called", {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "tools": agent.tools,
        })

        self._security_register(agent)
        self._security_audit(
            "WORKFLOW_STARTED",
            message=f"Task started: {task.id} by agent {agent.agent_id}",
            details={"task_id": task.id, "agent_id": agent.agent_id,
                     "role": agent.role.value},
        )

        started = time.time()
        child = None
        try:
            child = await self._build_agent(task, agent, ctx)
            run_result = await self._run_agent(child, task, agent, ctx)
        except Exception as exc:
            logger.exception("Agent execution failed for task %s", task.id)
            run_result = {
                "final_response": None,
                "messages": [],
                "api_calls": 0,
                "completed": False,
                "interrupted": False,
                "error": str(exc),
            }

        duration = time.time() - started

        final_response = run_result.get("final_response") or ""
        completed = bool(run_result.get("completed", False))
        interrupted = bool(run_result.get("interrupted", False))
        api_calls = int(run_result.get("api_calls", 0) or 0)
        error = run_result.get("error") or ""

        if error or (final_response and _looks_like_structured_error(final_response)):
            status = "failed"
        elif interrupted:
            status = "interrupted"
        elif completed or final_response:
            status = "completed"
        else:
            status = "failed"

        summary = final_response or (
            f"Task '{task.name}' executed by {agent.role.value} agent "
            f"({agent.model or 'default'} / {agent.provider or 'default'})."
        )

        usage = self._collect_usage(child, run_result)

        result_data = {
            "task_id": task.id,
            "task_name": task.name,
            "agent_id": agent.agent_id,
            "agent_role": agent.role.value,
            "model": agent.model,
            "provider": agent.provider,
            "result": {
                "summary": summary,
                "final_response": final_response,
                "api_calls": api_calls,
                "error": error or None,
                **usage,
            },
            "summary": summary,
            "status": status,
            "duration": duration,
            "api_calls": api_calls,
            **usage,
        }

        self._execution_contexts[f"{task.id}:{agent.agent_id}"] = {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "result": result_data,
            "completed_at": time.time(),
        }

        self._security_audit(
            "WORKFLOW_COMPLETED" if status == "completed" else "WORKFLOW_FAILED",
            severity="info" if status == "completed" else "error",
            message=f"Task finished: {task.id} ({status})",
            details={"task_id": task.id, "agent_id": agent.agent_id,
                     "status": status, "duration": duration},
        )

        self._emit("tool.completed", {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "result": result_data,
        })

        return result_data

    # ── agent construction ──────────────────────────────────────────────

    async def _build_agent(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> Any:
        if self._agent_factory is not None:
            return self._agent_factory(task=task, agent=agent, context=context)
        return await self._default_agent_factory(task, agent, context)

    def build_system_prompt(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> str:
        if self._system_prompt_builder is not None:
            return self._system_prompt_builder(task=task, agent=agent, context=context)

        role = agent.role.value
        instructions = (agent.instructions or "").strip()
        personality = (agent.personality or "").strip()
        lines = [
            f"You are a {role} agent executing a single task for the Aetheros "
            "mission orchestrator.",
            f"Your task: {task.name}",
            f"Task description: {task.description}",
        ]
        if instructions:
            lines.append(f"Operational instructions:\n{instructions}")
        if personality:
            lines.append(f"Personality/approach:\n{personality}")
        if agent.tools:
            lines.append(
                "Relevant tool areas: " + ", ".join(sorted(agent.tools))
            )
        previous = context.get("previous_results")
        if isinstance(previous, dict) and previous:
            lines.append("Results from earlier tasks you may use as context:")
            for tid, res in previous.items():
                lines.append(f"- {tid}: {str(res)[:400]}")
        lines.append(
            "When done, respond with a concise summary of what you accomplished "
            "and any notable findings."
        )
        return "\n".join(lines)

    async def _default_agent_factory(
        self,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> Any:
        """Construct a headless AIAgent (cron-style) using the configured
        runtime provider.  Lazy imports keep module import cheap for tests."""
        from run_agent import AIAgent
        from aetheros_cli.runtime_provider import (
            resolve_runtime_provider,
            format_runtime_provider_error,
        )
        from aetheros_cli.auth import AuthError

        try:
            runtime = resolve_runtime_provider(requested=agent.provider or None)
        except (AuthError, Exception) as exc:
            raise RuntimeError(format_runtime_provider_error(exc)) from exc

        system_prompt = self.build_system_prompt(task, agent, context)

        return AIAgent(
            model=agent.model or "",
            api_key=runtime.get("api_key"),
            base_url=runtime.get("base_url"),
            provider=runtime.get("provider"),
            api_mode=runtime.get("api_mode"),
            acp_command=runtime.get("command"),
            acp_args=runtime.get("args"),
            max_iterations=self._max_iterations,
            enabled_toolsets=self._enabled_toolsets,
            quiet_mode=self._quiet_mode,
            ephemeral_system_prompt=system_prompt,
            skip_context_files=True,
            skip_memory=True,
            load_soul_identity=False,
            platform="automation",
            session_id=f"mission-{task.id}",
        )

    # ── run loop ─────────────────────────────────────────────────────────

    async def _run_agent(
        self,
        child: Any,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if self._runner is not None:
            return self._runner(
                agent=child, task=task, assignment=agent, context=context
            )
        return await self._default_runner(child, task, agent, context)

    async def _default_runner(
        self,
        child: Any,
        task: OrchestrationTask,
        agent: AgentAssignment,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run ``child.run_conversation`` in a worker thread with a hard
        timeout.  On timeout the child is asked to interrupt; the result is
        reported as a failure rather than hanging the orchestrator."""
        user_message = task.description or task.name
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            initializer=_install_non_interactive_approval,
            initargs=(self._quiet_mode,),
        )
        self._emit("agent.spawned", {
            "task_id": task.id,
            "agent_id": agent.agent_id,
            "role": agent.role.value,
            "model": agent.model,
        })
        try:
            future = executor.submit(
                child.run_conversation,
                user_message=user_message,
                task_id=task.id,
            )
            try:
                return await asyncio.wait_for(
                    asyncio.shield(future), timeout=self._timeout_seconds
                )
            except asyncio.TimeoutError:
                _request_interrupt(child)
                api_calls = _count_api_calls(child)
                try:
                    partial = future.result(timeout=self._poll_interval)
                    if isinstance(partial, dict):
                        return partial
                except Exception:
                    pass
                return {
                    "final_response": None,
                    "messages": [],
                    "api_calls": api_calls,
                    "completed": False,
                    "interrupted": True,
                    "error": (
                        f"Task timed out after {self._timeout_seconds}s "
                        f"({api_calls} API call(s) completed)"
                    ),
                }
        finally:
            executor.shutdown(wait=False)

    def _collect_usage(
        self, child: Any, run_result: dict[str, Any]
    ) -> dict[str, Any]:
        usage: dict[str, Any] = {}
        if child is not None:
            try:
                summary = child.get_activity_summary()
                if isinstance(summary, dict):
                    if "api_call_count" in summary:
                        usage["api_call_count"] = summary["api_call_count"]
                    if "max_iterations" in summary:
                        usage["max_iterations"] = summary["max_iterations"]
            except Exception:
                pass
        tokens = run_result.get("usage") or run_result.get("tokens")
        if tokens:
            usage["tokens"] = tokens
        cost = run_result.get("cost")
        if cost:
            usage["cost"] = cost
        return usage

    # ── security integration ────────────────────────────────────────────

    def _security_register(self, agent: AgentAssignment) -> None:
        try:
            from aetheros_automation.orchestrator.security import register_agent
            register_agent(agent.agent_id, role=agent.role.value)
        except Exception:  # pragma: no cover - defensive
            pass

    def _security_audit(self, event: str, *, severity: str = "info",
                        message: str = "",
                        details: dict[str, Any] | None = None) -> None:
        try:
            from aetheros_automation.orchestrator.security import audit
            audit(event, severity=severity, message=message, details=details)
        except Exception:  # pragma: no cover - defensive
            pass


def _request_interrupt(child: Any) -> None:
    try:
        if hasattr(child, "interrupt"):
            child.interrupt()
        elif hasattr(child, "_interrupt_requested"):
            child._interrupt_requested = True
    except Exception:
        pass


def _count_api_calls(child: Any) -> int:
    try:
        summary = child.get_activity_summary()
        if isinstance(summary, dict):
            return int(summary.get("api_call_count", 0) or 0)
    except Exception:
        pass
    return 0


def _install_non_interactive_approval(quiet_mode: bool = True):
    """Make sure a headless subagent never falls back to ``input()`` for
    approvals (which would deadlock a non-interactive process).  Mirrors
    delegate_tool's worker-thread initializer (tools.terminal_tool
    set_approval_callback)."""
    import logging as _logging

    _logging.getLogger(__name__)
    try:
        from tools.terminal_tool import set_approval_callback
    except Exception:
        return
    try:

        def _auto_deny(command: str, description: str, **kwargs) -> str:
            _logging.getLogger(__name__).warning(
                "Automation subagent auto-denied dangerous command: %s (%s)",
                command, description,
            )
            return "deny"

        def _auto_approve(command: str, description: str, **kwargs) -> str:
            _logging.getLogger(__name__).warning(
                "Automation subagent auto-approved dangerous command: %s (%s)",
                command, description,
            )
            return "once"

        set_approval_callback(_auto_deny if quiet_mode else _auto_approve)
    except Exception:
        pass
