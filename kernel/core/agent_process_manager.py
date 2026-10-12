"""
Agent Process Manager — lifecycle management for agent processes.

Manages the runtime execution of agent processes, connecting them
to the existing AIAgent runtime while enforcing kernel boundaries.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

from kernel.core.types import (
    AgentProcess,
    AgentLifecycleState,
    AgentPriority,
    ResourceBudget,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AgentRuntime:
    """Runtime state for an executing agent."""
    process: AgentProcess
    thread: Optional[threading.Thread] = None
    agent_instance: Any = None  # AIAgent or compatible
    stop_requested: bool = False
    current_task: Optional[str] = None
    iterations: int = 0
    last_activity: float = field(default_factory=_now)
    error: Optional[str] = None


class AgentProcessManager:
    """
    Manages the lifecycle of agent processes.
    
    Bridges between the kernel's AgentProcess abstraction and
    the concrete AIAgent implementation.
    """

    def __init__(self, config, event_bus: EventBus, kernel):
        self.config = config
        self.event_bus = event_bus
        self.kernel = kernel
        self._lock = threading.RLock()
        self._runtimes: Dict[str, AgentRuntime] = {}
        self._initialization_callbacks: List[Callable[[AgentProcess], bool]] = []
        self._execution_callbacks: List[Callable[[AgentProcess, str], Any]] = []

    def register_initialization_callback(self, callback: Callable[[AgentProcess], bool]) -> None:
        """Register a callback for agent initialization."""
        self._initialization_callbacks.append(callback)

    def register_execution_callback(self, callback: Callable[[AgentProcess, str], Any]) -> None:
        """Register a callback for agent task execution."""
        self._execution_callbacks.append(callback)

    def initialize_agent(self, process: AgentProcess) -> bool:
        """Initialize an agent process."""
        logger.info("AgentProcessManager: initializing agent %s", process.agent_id)

        runtime = AgentRuntime(process=process)
        
        with self._lock:
            self._runtimes[process.agent_id] = runtime

        # Run initialization callbacks
        for callback in self._initialization_callbacks:
            try:
                if not callback(process):
                    logger.error("Initialization callback failed for %s", process.agent_id)
                    return False
            except Exception as exc:
                logger.error("Initialization callback error for %s: %s", process.agent_id, exc)
                return False

        # Create the actual agent instance
        try:
            agent_instance = self._create_agent_instance(process)
            runtime.agent_instance = agent_instance
        except Exception as exc:
            logger.error("Failed to create agent instance for %s: %s", process.agent_id, exc)
            return False

        # Transition to READY (tolerate already-READY / ADMITTED callers)
        if process.state != AgentLifecycleState.READY:
            try:
                process.transition(AgentLifecycleState.READY)
            except ValueError:
                # e.g. CREATED caller: walk the canonical path
                if process.state == AgentLifecycleState.CREATED:
                    process.transition(AgentLifecycleState.ADMITTED)
                    process.transition(AgentLifecycleState.INITIALIZING)
                    process.transition(AgentLifecycleState.READY)
                else:
                    raise
        process.started_at = _now()

        if self.event_bus:
            self.event_bus.emit("agent.ready", {
                "agent_id": process.agent_id,
                "process_id": process.process_id,
            })

        logger.info("AgentProcessManager: agent %s ready", process.agent_id)
        return True

    def _create_agent_instance(self, process: AgentProcess) -> Any:
        """Create the concrete agent instance (AIAgent), or a stub when unavailable."""
        import os

        def _stub(reason: str):
            logger.info("AgentProcessManager: using stub runtime for %s (%s)", process.agent_id, reason)

            class _StubAgent:
                def __init__(self, proc):
                    self._proc = proc
                    self.model = proc.model_policy.get("model", "stub")
                    self.provider = proc.model_policy.get("provider", "stub")

                def run_conversation(self, task, **kw):
                    return {"final_response": f"[stub] {task}", "completed": True}

            stub = _StubAgent(process)
            stub._kernel = self.kernel
            stub._process = process
            return stub

        # Default to an isolated stub runtime: constructing a real AIAgent
        # pulls provider credentials, model routing, and tool discovery, which
        # must never block kernel admission. Opt into the real agent with
        # AETHEROS_KERNEL_REAL_AGENT=1.
        if os.getenv("AETHEROS_KERNEL_REAL_AGENT", "0") != "1":
            return _stub("isolated stub runtime (set AETHEROS_KERNEL_REAL_AGENT=1 for live AIAgent)")

        try:
            # Import here to avoid circular dependency
            from run_agent import AIAgent

            # Create AIAgent with kernel-enforced configuration.
            # Tool filtering happens at capability-invocation time; the agent
            # itself is constructed with the granted capability list.
            agent = AIAgent(
                base_url=process.model_policy.get("base_url"),
                api_key=process.model_policy.get("api_key"),
                provider=process.model_policy.get("provider"),
                model=process.model_policy.get("model", ""),
                max_iterations=max(1, (process.resource_budget.llm_tokens_per_minute or 10000) // 1000),
                enabled_toolsets=list(process.authority.capabilities) if process.authority else None,
                disabled_toolsets=[],
                quiet_mode=True,
                platform="kernel",
                session_id=process.process_id,
            )

            # Store kernel reference for enforcement
            agent._kernel = self.kernel
            agent._process = process

            return agent
        except Exception as exc:
            logger.warning("AgentProcessManager: AIAgent unavailable (%s); using stub runtime", exc)

            class _StubAgent:
                def __init__(self, proc):
                    self._proc = proc
                    self.model = proc.model_policy.get("model", "stub")
                    self.provider = proc.model_policy.get("provider", "stub")

                def run_conversation(self, task, **kw):
                    return {"final_response": f"[stub] {task}", "completed": True}

            stub = _StubAgent(process)
            stub._kernel = self.kernel
            stub._process = process
            return stub

    def execute_task(self, agent_id: str, task: str) -> Any:
        """Execute a task on an agent."""
        runtime = self._runtimes.get(agent_id)
        if not runtime:
            raise ValueError(f"Agent runtime not found: {agent_id}")

        process = runtime.process
        if process.state != AgentLifecycleState.READY and process.state != AgentLifecycleState.RUNNING:
            raise ValueError(f"Agent not in executable state: {process.state}")

        process.transition(AgentLifecycleState.RUNNING)
        runtime.current_task = task
        runtime.iterations = 0

        if self.event_bus:
            self.event_bus.emit("agent.task.started", {
                "agent_id": agent_id,
                "task": task,
            })

        # Run execution callbacks
        result = None
        error = None
        for callback in self._execution_callbacks:
            try:
                result = callback(process, task)
                break
            except Exception as exc:
                error = exc
                logger.error("Execution callback error for %s: %s", agent_id, exc)

        # If no callback handled it, use default execution
        if result is None and error is None:
            try:
                result = runtime.agent_instance.run_conversation(task)
            except Exception as exc:
                error = exc

        runtime.iterations += 1
        runtime.last_activity = _now()

        if error:
            process.transition(AgentLifecycleState.FAILED)
            process.error = str(error)
            runtime.error = str(error)
            
            if self.event_bus:
                self.event_bus.emit("agent.task.failed", {
                    "agent_id": agent_id,
                    "task": task,
                    "error": str(error),
                })
            raise error
        else:
            process.transition(AgentLifecycleState.COMPLETED)
            process.completed_at = _now()
            
            if self.event_bus:
                self.event_bus.emit("agent.task.completed", {
                    "agent_id": agent_id,
                    "task": task,
                    "result": str(result)[:200] if result else "",
                })

        return result

    def terminate_agent(self, process: AgentProcess) -> None:
        """Terminate an agent process."""
        logger.info("AgentProcessManager: terminating agent %s", process.agent_id)

        runtime = self._runtimes.get(process.agent_id)
        if runtime:
            runtime.stop_requested = True
            if runtime.thread and runtime.thread.is_alive():
                runtime.thread.join(timeout=5)

            # Cleanup agent instance
            if runtime.agent_instance and hasattr(runtime.agent_instance, 'shutdown'):
                try:
                    runtime.agent_instance.shutdown()
                except Exception as exc:
                    logger.error("Error shutting down agent instance: %s", exc)

        with self._lock:
            self._runtimes.pop(process.agent_id, None)

        process.transition(AgentLifecycleState.TERMINATED)

        if self.event_bus:
            self.event_bus.emit("agent.terminated", {
                "agent_id": process.agent_id,
                "process_id": process.process_id,
            })

    def get_runtime(self, agent_id: str) -> Optional[AgentRuntime]:
        """Get the runtime for an agent."""
        with self._lock:
            return self._runtimes.get(agent_id)

    def list_runtimes(self) -> List[AgentRuntime]:
        """List all active runtimes."""
        with self._lock:
            return list(self._runtimes.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            runtimes = list(self._runtimes.values())
        
        return {
            "total_runtimes": len(runtimes),
            "by_state": {
                state.value: sum(1 for r in runtimes if r.process.state == state)
                for state in AgentLifecycleState
            },
            "total_iterations": sum(r.iterations for r in runtimes),
        }

    def shutdown(self) -> None:
        """Shutdown all agent runtimes."""
        logger.info("AgentProcessManager: shutting down")
        
        with self._lock:
            runtimes = list(self._runtimes.values())
        
        for runtime in runtimes:
            try:
                self.terminate_agent(runtime.process)
            except Exception as exc:
                logger.error("Error terminating agent %s: %s", runtime.process.agent_id, exc)