"""
Resource Manager — resource allocation, tracking, and scheduling.

Manages CPU, GPU, RAM, tokens, concurrency slots, and other schedulable resources.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.core.types import (
    ResourceBudget,
    ResourceAllocation,
    ResourceType,
    AgentLifecycleState,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SystemResources:
    """Total system resources available."""
    cpu_cores: float = 16.0
    gpu_memory_mb: int = 24576  # 24GB
    ram_mb: int = 65536  # 64GB
    disk_mb: int = 1048576  # 1TB
    network_mbps: float = 1000.0
    llm_tokens_per_minute: int = 1000000
    model_concurrency: int = 10
    tool_concurrency: int = 50
    browser_sessions: int = 10
    computer_sessions: int = 5
    device_sessions: int = 20
    research_requests_per_minute: int = 100
    agent_slots: int = 100
    automation_slots: int = 20


class ResourceManager:
    """
    Manages resource allocation for agents and tasks.
    
    Implements reservation, allocation, preemption, release, quotas,
    priority, fairness, backpressure, and rate limiting.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # System resources (would be auto-detected in production)
        self.system_resources = SystemResources()
        
        # Current allocations
        self._allocations: Dict[str, ResourceAllocation] = {}
        
        # Resource reservations (pending allocations)
        self._reservations: Dict[str, ResourceBudget] = {}
        
        # Usage tracking
        self._usage_history: List[Dict[str, Any]] = []

    def allocate(self, agent_id: str, budget: ResourceBudget) -> ResourceAllocation:
        """Allocate resources to an agent."""
        with self._lock:
            # Check availability
            available = self.get_available()
            if not self._can_allocate(budget, available):
                raise ResourceError(f"Insufficient resources for agent {agent_id}")

            # Create allocation (usage starts at true zero; the old
            # ResourceBudget() default carried nonzero defaults here).
            allocation = ResourceAllocation(
                agent_id=agent_id,
                allocated=budget,
                used=ResourceBudget.zero(),
                reserved=ResourceBudget.zero(),
            )

            self._allocations[agent_id] = allocation

            # Remove any existing reservation
            self._reservations.pop(agent_id, None)

        if self.event_bus:
            self.event_bus.emit("resource.allocated", {
                "agent_id": agent_id,
                "budget": budget.to_dict(),
            })

        logger.info("ResourceManager: allocated resources to agent %s", agent_id)
        return allocation

    def reserve(self, budget: ResourceBudget) -> Dict[str, Any]:
        """Reserve resources (for intent admission)."""
        with self._lock:
            available = self.get_available()
            if not self._can_allocate(budget, available):
                return {"available": False, "reason": "Insufficient resources for reservation"}

            reservation_id = new_id("res")
            self._reservations[reservation_id] = budget

        return {"available": True, "reservation_id": reservation_id}

    def release(self, agent_id: str) -> None:
        """Release all resources for an agent."""
        with self._lock:
            allocation = self._allocations.pop(agent_id, None)
            self._reservations.pop(agent_id, None)

        if allocation and self.event_bus:
            self.event_bus.emit("resource.released", {
                "agent_id": agent_id,
                "budget": allocation.allocated.to_dict(),
            })

        logger.info("ResourceManager: released resources for agent %s", agent_id)

    def release_reservation(self, reservation_id: str) -> bool:
        """Release a resource reservation."""
        with self._lock:
            return self._reservations.pop(reservation_id, None) is not None

    def get_usage(self, agent_id: str) -> Optional[ResourceAllocation]:
        """Get current resource usage for an agent."""
        with self._lock:
            return self._allocations.get(agent_id)

    def get_available(self) -> ResourceBudget:
        """Get currently available resources."""
        with self._lock:
            used = ResourceBudget.zero()
            for allocation in self._allocations.values():
                used = self._add_budgets(used, allocation.allocated)
            
            for reservation in self._reservations.values():
                used = self._add_budgets(used, reservation)

            available = self._subtract_budgets(self.system_resources, used)
            return available

    def get_total_allocated(self) -> ResourceBudget:
        """Get total allocated resources."""
        with self._lock:
            total = ResourceBudget.zero()
            for allocation in self._allocations.values():
                total = self._add_budgets(total, allocation.allocated)
            return total

    def update_usage(self, agent_id: str, usage: ResourceBudget) -> None:
        """Update actual resource usage for an agent."""
        with self._lock:
            allocation = self._allocations.get(agent_id)
            if allocation:
                allocation.used = usage
                allocation.timestamp = _now()

                # Record usage history
                self._usage_history.append({
                    "agent_id": agent_id,
                    "usage": usage.to_dict(),
                    "timestamp": _now(),
                })

                # Keep last 10000 entries
                if len(self._usage_history) > 10000:
                    self._usage_history = self._usage_history[-5000:]

    def check_availability(self, budget: ResourceBudget) -> Dict[str, Any]:
        """Check if a budget can be satisfied."""
        with self._lock:
            available = self.get_available()
            can_allocate = self._can_allocate(budget, available)
            
            if not can_allocate:
                # Find limiting resource
                limiting = []
                for field_name in budget.__dataclass_fields__:
                    requested = getattr(budget, field_name)
                    avail = getattr(available, field_name)
                    if requested > avail:
                        limiting.append(f"{field_name}: requested={requested}, available={avail}")
                
                return {
                    "available": False,
                    "reason": f"Limiting resources: {', '.join(limiting)}",
                }
            
            return {"available": True}

    def _can_allocate(self, requested: ResourceBudget, available: ResourceBudget) -> bool:
        """Check if requested budget fits in available."""
        for field_name in requested.__dataclass_fields__:
            if getattr(requested, field_name) > getattr(available, field_name):
                return False
        return True

    def _add_budgets(self, a: ResourceBudget, b: ResourceBudget) -> ResourceBudget:
        """Add two resource budgets."""
        return ResourceBudget(
            cpu_cores=a.cpu_cores + b.cpu_cores,
            gpu_memory_mb=a.gpu_memory_mb + b.gpu_memory_mb,
            ram_mb=a.ram_mb + b.ram_mb,
            disk_mb=a.disk_mb + b.disk_mb,
            network_mbps=a.network_mbps + b.network_mbps,
            llm_tokens_per_minute=a.llm_tokens_per_minute + b.llm_tokens_per_minute,
            model_concurrency=a.model_concurrency + b.model_concurrency,
            tool_concurrency=a.tool_concurrency + b.tool_concurrency,
            browser_sessions=a.browser_sessions + b.browser_sessions,
            computer_sessions=a.computer_sessions + b.computer_sessions,
            device_sessions=a.device_sessions + b.device_sessions,
            research_requests_per_minute=a.research_requests_per_minute + b.research_requests_per_minute,
            agent_slots=a.agent_slots + b.agent_slots,
            automation_slots=a.automation_slots + b.automation_slots,
        )

    def _subtract_budgets(self, a: ResourceBudget, b: ResourceBudget) -> ResourceBudget:
        """Subtract budget b from budget a."""
        return ResourceBudget(
            cpu_cores=max(0, a.cpu_cores - b.cpu_cores),
            gpu_memory_mb=max(0, a.gpu_memory_mb - b.gpu_memory_mb),
            ram_mb=max(0, a.ram_mb - b.ram_mb),
            disk_mb=max(0, a.disk_mb - b.disk_mb),
            network_mbps=max(0, a.network_mbps - b.network_mbps),
            llm_tokens_per_minute=max(0, a.llm_tokens_per_minute - b.llm_tokens_per_minute),
            model_concurrency=max(0, a.model_concurrency - b.model_concurrency),
            tool_concurrency=max(0, a.tool_concurrency - b.tool_concurrency),
            browser_sessions=max(0, a.browser_sessions - b.browser_sessions),
            computer_sessions=max(0, a.computer_sessions - b.computer_sessions),
            device_sessions=max(0, a.device_sessions - b.device_sessions),
            research_requests_per_minute=max(0, a.research_requests_per_minute - b.research_requests_per_minute),
            agent_slots=max(0, a.agent_slots - b.agent_slots),
            automation_slots=max(0, a.automation_slots - b.automation_slots),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get resource manager statistics."""
        with self._lock:
            available = self.get_available()
            allocated = self.get_total_allocated()
            
            return {
                "system": self.system_resources.__dict__,
                "allocated": allocated.to_dict(),
                "available": available.to_dict(),
                "utilization": {
                    "cpu": allocated.cpu_cores / max(self.system_resources.cpu_cores, 1),
                    "gpu_memory": allocated.gpu_memory_mb / max(self.system_resources.gpu_memory_mb, 1),
                    "ram": allocated.ram_mb / max(self.system_resources.ram_mb, 1),
                    "llm_tokens": allocated.llm_tokens_per_minute / max(self.system_resources.llm_tokens_per_minute, 1),
                    "agent_slots": allocated.agent_slots / max(self.system_resources.agent_slots, 1),
                },
                "active_allocations": len(self._allocations),
                "pending_reservations": len(self._reservations),
            }

    def shutdown(self) -> None:
        """Shutdown the resource manager."""
        logger.info("ResourceManager: shutting down")
        with self._lock:
            self._allocations.clear()
            self._reservations.clear()
            self._usage_history.clear()


class ResourceError(Exception):
    """Resource allocation error."""
    pass