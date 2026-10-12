"""
Capability Manager — capability registration, discovery, and metadata.

Implements the Capability ABI: every capability exposes machine-readable
metadata that feeds planner, router, scheduler, governance, UI, benchmarks.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.core.types import (
    CapabilityDescriptor,
    CapabilityRiskLevel,
    DataClassification,
    ResourceBudget,
    ICapabilityProvider,
    new_id,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class CapabilityRegistration:
    """Internal registration record."""
    descriptor: CapabilityDescriptor
    provider: ICapabilityProvider
    registered_at: float = field(default_factory=lambda: __import__('time').time())
    enabled: bool = True
    invocation_count: int = 0
    error_count: int = 0
    last_invoked: Optional[float] = None


class CapabilityManager:
    """
    Manages capability registration, discovery, and metadata.
    
    Capabilities are the syscall layer of the Agent Kernel.
    Every capability must be registered with a descriptor before use.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._capabilities: Dict[str, CapabilityRegistration] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # tag -> capability_ids
        self._provider_index: Dict[str, Set[str]] = {}  # provider -> capability_ids

    def register(self, descriptor: CapabilityDescriptor, provider: ICapabilityProvider) -> None:
        """Register a capability with its provider."""
        if not descriptor.capability_id:
            descriptor.capability_id = new_id("cap")

        registration = CapabilityRegistration(
            descriptor=descriptor,
            provider=provider,
        )

        with self._lock:
            self._capabilities[descriptor.capability_id] = registration
            self._provider_index.setdefault(descriptor.provider, set()).add(descriptor.capability_id)

            # Index by tags
            for tag in descriptor.tags:
                self._capability_index.setdefault(tag, set()).add(descriptor.capability_id)

        logger.info("CapabilityManager: registered %s (v%s) from %s",
                    descriptor.capability_id, descriptor.version, descriptor.provider)

        if self.event_bus:
            self.event_bus.emit("capability.registered", {
                "capability_id": descriptor.capability_id,
                "version": descriptor.version,
                "provider": descriptor.provider,
                "risk_level": descriptor.side_effects[0].value if descriptor.side_effects else "read_only",
            })

    def unregister(self, capability_id: str) -> bool:
        """Unregister a capability."""
        with self._lock:
            reg = self._capabilities.pop(capability_id, None)
            if not reg:
                return False

            self._provider_index.get(reg.descriptor.provider, set()).discard(capability_id)
            for tag in reg.descriptor.tags:
                self._capability_index.get(tag, set()).discard(capability_id)

        if self.event_bus:
            self.event_bus.emit("capability.unregistered", {
                "capability_id": capability_id,
            })

        return True

    def get_descriptor(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        """Get a capability descriptor."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            return reg.descriptor if reg else None

    def get_provider(self, capability_id: str) -> Optional[ICapabilityProvider]:
        """Get a capability provider."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            return reg.provider if reg else None

    def list_capabilities(
        self,
        provider: str = "",
        tag: str = "",
        risk_level: CapabilityRiskLevel = None,
        enabled_only: bool = True,
    ) -> List[CapabilityDescriptor]:
        """List capabilities with optional filters."""
        with self._lock:
            capabilities = list(self._capabilities.values())

        if enabled_only:
            capabilities = [c for c in capabilities if c.enabled]

        if provider:
            capabilities = [c for c in capabilities if c.descriptor.provider == provider]

        if tag:
            capabilities = [c for c in capabilities if tag in c.descriptor.tags]

        if risk_level:
            capabilities = [c for c in capabilities if risk_level in c.descriptor.side_effects]

        return [c.descriptor for c in capabilities]

    def find_capabilities(
        self,
        query: str = "",
        required_authority: List[str] = None,
        max_latency: str = "",
        max_cost: str = "",
    ) -> List[CapabilityDescriptor]:
        """Find capabilities matching criteria."""
        with self._lock:
            capabilities = list(self._capabilities.values())

        if query:
            query_lower = query.lower()
            capabilities = [
                c for c in capabilities
                if query_lower in c.descriptor.capability_id.lower()
                or query_lower in c.descriptor.description.lower()
            ]

        if required_authority:
            capabilities = [
                c for c in capabilities
                if all(a in c.descriptor.required_authority for a in required_authority)
            ]

        if max_latency:
            latency_order = {"fast": 0, "normal": 1, "slow": 2}
            max_order = latency_order.get(max_latency, 2)
            capabilities = [
                c for c in capabilities
                if latency_order.get(c.descriptor.latency_class, 1) <= max_order
            ]

        if max_cost:
            cost_order = {"free": 0, "low": 1, "medium": 2, "high": 3}
            max_order = cost_order.get(max_cost, 3)
            capabilities = [
                c for c in capabilities
                if cost_order.get(c.descriptor.cost_class, 0) <= max_order
            ]

        return [c.descriptor for c in capabilities]

    def enable_capability(self, capability_id: str) -> bool:
        """Enable a capability."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            if not reg:
                return False
            reg.enabled = True
        return True

    def disable_capability(self, capability_id: str) -> bool:
        """Disable a capability."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            if not reg:
                return False
            reg.enabled = False
        return True

    def record_invocation(self, capability_id: str, success: bool = True) -> None:
        """Record a capability invocation for metrics."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            if reg:
                reg.invocation_count += 1
                if not success:
                    reg.error_count += 1
                reg.last_invoked = __import__('time').time()

    def get_capability_stats(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a capability."""
        with self._lock:
            reg = self._capabilities.get(capability_id)
            if not reg:
                return None
            return {
                "capability_id": capability_id,
                "invocations": reg.invocation_count,
                "errors": reg.error_count,
                "error_rate": reg.error_count / max(reg.invocation_count, 1),
                "last_invoked": reg.last_invoked,
                "enabled": reg.enabled,
            }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all capabilities."""
        with self._lock:
            return {
                cid: self.get_capability_stats(cid)
                for cid in self._capabilities.keys()
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            total = len(self._capabilities)
            enabled = sum(1 for c in self._capabilities.values() if c.enabled)
            by_provider: Dict[str, int] = {}
            by_risk: Dict[str, int] = {}
            total_invocations = 0
            total_errors = 0

            for reg in self._capabilities.values():
                by_provider[reg.descriptor.provider] = by_provider.get(reg.descriptor.provider, 0) + 1
                if reg.descriptor.side_effects:
                    risk = reg.descriptor.side_effects[0].value
                    by_risk[risk] = by_risk.get(risk, 0) + 1
                total_invocations += reg.invocation_count
                total_errors += reg.error_count

        return {
            "total_capabilities": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "by_provider": by_provider,
            "by_risk_level": by_risk,
            "total_invocations": total_invocations,
            "total_errors": total_errors,
            "overall_error_rate": total_errors / max(total_invocations, 1),
        }

    def shutdown(self) -> None:
        """Shutdown the capability manager."""
        logger.info("CapabilityManager: shutting down")
        with self._lock:
            self._capabilities.clear()
            self._capability_index.clear()
            self._provider_index.clear()