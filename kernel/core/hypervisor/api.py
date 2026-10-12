"""
AetherOS Agent Hypervisor 1.0 — typed capsule API (§76).

    capsules.create()
    capsules.inspect()
    capsules.pause()
    capsules.resume()
    capsules.checkpoint()
    capsules.restore()
    capsules.migrate()
    capsules.quarantine()
    capsules.destroy()
    capsules.list()
    capsules.resources()
    capsules.permissions()
    capsules.trace()

All calls enforce capsule authority; dangerous operations require explicit
confirmation (`confirm=True`), never bare invocation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from kernel.core.hypervisor.types import (
    AgentCapsule,
    CapsuleSnapshot,
    ReplayMode,
    TerminationMode,
)
from kernel.core.types import Intent


class CapsuleAPI:
    """Typed facade over AgentHypervisor (the `capsules.*` surface)."""

    def __init__(self, hypervisor: Any) -> None:
        self._hypervisor = hypervisor

    def create(self, objective: str, actor: str = "human",
               profile: str = "standard",
               capabilities: Optional[List[str]] = None,
               parent_capsule_id: Optional[str] = None,
               start: bool = False) -> AgentCapsule:
        """capsules.create(): admit intent and provision a capsule."""
        intent = Intent(actor=actor, objective=objective,
                        requested_capabilities=list(capabilities or []))
        return self._hypervisor.create_capsule(
            intent, profile, parent_capsule_id=parent_capsule_id, start=start)

    def inspect(self, capsule_id: str) -> Dict[str, Any]:
        """capsules.inspect(): full capsule view (§79)."""
        return self._hypervisor.inspect_capsule(capsule_id)

    def pause(self, capsule_id: str) -> AgentCapsule:
        """capsules.pause()"""
        return self._hypervisor.pause_capsule(capsule_id)

    def resume(self, capsule_id: str) -> AgentCapsule:
        """capsules.resume()"""
        return self._hypervisor.resume_capsule(capsule_id)

    def checkpoint(self, capsule_id: str) -> CapsuleSnapshot:
        """capsules.checkpoint()"""
        return self._hypervisor.snapshot_capsule(capsule_id)

    def restore(self, snapshot_hash: str) -> AgentCapsule:
        """capsules.restore()"""
        return self._hypervisor.restore_snapshot(snapshot_hash)

    def migrate(self, capsule_id: str, destination: str = "local",
                *, confirm: bool = False) -> Dict[str, Any]:
        """capsules.migrate(): requires explicit confirmation."""
        if not confirm:
            raise PermissionError("migrate requires confirm=True")
        return self._hypervisor.migrate_capsule(capsule_id, destination)

    def quarantine(self, capsule_id: str, reason: str = "operator",
                   *, confirm: bool = False) -> AgentCapsule:
        """capsules.quarantine(): requires explicit confirmation."""
        if not confirm:
            raise PermissionError("quarantine requires confirm=True")
        return self._hypervisor.quarantine_capsule(capsule_id, reason)

    def destroy(self, capsule_id: str,
                mode: str = "graceful", *, confirm: bool = False) -> Dict[str, Any]:
        """capsules.destroy(): requires explicit confirmation."""
        if not confirm:
            raise PermissionError("destroy requires confirm=True")
        return self._hypervisor.destroy_capsule(
            capsule_id, TerminationMode(mode))

    def list(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """capsules.list()"""
        return self._hypervisor.list_capsules(state)

    def resources(self, capsule_id: str) -> Dict[str, Any]:
        """capsules.resources(): live capsule view data (§80)."""
        return self._hypervisor.capsule_resources(capsule_id)

    def permissions(self, capsule_id: str) -> Dict[str, Any]:
        """capsules.permissions(): exact authority view."""
        return self._hypervisor.capsule_permissions(capsule_id)

    def trace(self, capsule_id: str) -> Dict[str, Any]:
        """capsules.trace(): receipts + observations."""
        return self._hypervisor.capsule_trace(capsule_id)

    def replay(self, capsule_id: str,
               mode: str = "observe_only") -> Dict[str, Any]:
        """capsules.replay(): default OBSERVE_ONLY, no side effects."""
        return self._hypervisor.replay(capsule_id, ReplayMode(mode))

    def preview(self, objective: str, profile: str = "standard",
                capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Pre-launch capsule + resource preview (§84-§85)."""
        return self._hypervisor.preview(objective, profile, capabilities)

    def simulate(self, capsule_id: str, capability: str,
                 inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Policy simulator: would X be allowed, without executing (§83)."""
        return self._hypervisor.simulate(capsule_id, capability, inputs)

    def diff(self, capsule_a: str, capsule_b: str) -> Dict[str, Any]:
        """Capsule A vs B comparison (§82)."""
        return self._hypervisor.diff_capsules(capsule_a, capsule_b)

    def benchmark(self) -> Dict[str, Any]:
        """Capsule benchmark suite (§109-§110)."""
        from kernel.core.hypervisor.benchmark import run_capsule_benchmarks
        return run_capsule_benchmarks(self._hypervisor)
