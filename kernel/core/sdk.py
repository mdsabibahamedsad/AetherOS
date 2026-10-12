"""
AetherOS Agent Kernel 1.0 — Developer SDK (§106).

Thin, typed, authority-enforcing facade over AgentKernel. All calls route
through the kernel's admission / authority / policy / security pipeline;
the SDK never bypasses it.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from kernel.core.kernel import AgentKernel, get_kernel
from kernel.core.types import (
    AgentProcess,
    AuthorityGrant,
    CapabilityDescriptor,
    CapabilityInvocation,
    Checkpoint,
    ICapabilityProvider,
    Intent,
    ResourceBudget,
)


class KernelSDK:
    """Internal/external capability SDK for the Agent Kernel."""

    def __init__(self, kernel: AgentKernel = None):
        self._kernel = kernel or get_kernel()

    @property
    def kernel(self) -> AgentKernel:
        return self._kernel

    # -- agents -----------------------------------------------------------
    def spawn(self, objective: str, actor: str = "human",
              capabilities: List[str] = None, parent_agent_id: str = None) -> AgentProcess:
        """kernel.agents.spawn(): admit intent + create agent process."""
        intent = Intent(actor=actor, objective=objective,
                        requested_capabilities=list(capabilities or []))
        return self._kernel.create_agent_process(intent, parent_agent_id=parent_agent_id)

    def inspect(self, agent_id: str) -> Optional[AgentProcess]:
        """kernel.agents.inspect()"""
        return self._kernel.get_agent_process(agent_id)

    def pause(self, agent_id: str) -> bool:
        return self._kernel.pause_agent(agent_id)

    def resume(self, agent_id: str) -> bool:
        return self._kernel.resume_agent(agent_id)

    def cancel(self, agent_id: str, reason: str = "sdk cancel") -> bool:
        return self._kernel.stop_agent(agent_id, reason=reason)

    # -- capabilities ------------------------------------------------------
    def request(self, agent_id: str, capability_id: str,
                inputs: Dict[str, Any] = None, intent_id: str = "") -> CapabilityInvocation:
        """kernel.capabilities.request(): full syscall pipeline."""
        return self._kernel.invoke_capability(agent_id, capability_id, inputs or {}, intent_id=intent_id)

    def register_capability(self, descriptor: CapabilityDescriptor,
                            provider: ICapabilityProvider) -> None:
        self._kernel.register_capability(descriptor, provider)

    # -- resources ----------------------------------------------------------
    def allocate(self, agent_id: str, budget: ResourceBudget):
        return self._kernel.resource_manager.allocate(agent_id, budget)

    # -- memory (scope-aware; agent_id is always the caller) ----------------
    def memory_read(self, agent_id: str, key: str, scope: str = "working") -> Any:
        from kernel.core.memory_manager import MemoryScope
        return self._kernel.memory_manager.read(agent_id, MemoryScope(scope), key)

    def memory_write(self, agent_id: str, key: str, value: Any, scope: str = "working") -> bool:
        from kernel.core.memory_manager import MemoryScope
        return bool(self._kernel.memory_manager.write(agent_id, MemoryScope(scope), key, value))

    # -- events ---------------------------------------------------------------
    def subscribe(self, topic: str, callback: Callable) -> Any:
        return self._kernel.event_bus.subscribe(topic, callback)

    # -- checkpoints ------------------------------------------------------------
    def checkpoint(self, agent_id: str) -> Checkpoint:
        return self._kernel.create_checkpoint(agent_id)

    # -- policy / audit ------------------------------------------------------------
    def evaluate_policy(self, intent: Intent) -> Any:
        return self._kernel.policy_engine.evaluate_intent(intent)

    def audit(self, action: str, actor_id: str = "sdk", target: str = "",
                outcome: str = "ok", data: Dict[str, Any] = None) -> Any:
        return self._kernel.audit_engine.log(
            event_type="sdk.audit", actor_id=actor_id, action=action,
            target=target, outcome=outcome, details=data or {},
        )

    def status(self) -> Dict[str, Any]:
        return self._kernel.status()

    # -- capsules ---------------------------------------------------------------
    @property
    def capsules(self: "KernelSDK") -> Any:
        """capsules.* API: create/inspect/pause/resume/checkpoint/restore/
        migrate/quarantine/destroy/list/resources/permissions/trace/replay."""
        from kernel.core.hypervisor.api import CapsuleAPI
        return CapsuleAPI(self._kernel.hypervisor)
