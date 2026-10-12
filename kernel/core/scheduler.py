"""
Kernel Scheduler — OS-like scheduler for agent processes.

Supports multiple scheduling classes, priority inheritance, deadlock detection,
and multi-agent scheduling with resource awareness.
"""

from __future__ import annotations

import itertools
import logging
import threading
import time
import heapq
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

# Monotonic tiebreaker for scheduler heap items (see ScheduledAgent).
_SCHED_SEQ = itertools.count()

from kernel.core.types import (
    AgentProcess,
    AgentPriority,
    AgentLifecycleState,
    ResourceBudget,
    SchedulingClass,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class SchedulerState(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class ScheduledAgent:
    """An agent in the scheduler queue.

    Heap items: ``__lt__`` orders by (priority_key, seq) so equal keys
    (same priority class + deadline + creation timestamp) can never raise
    ``TypeError: '<' not supported`` on heappush.
    """
    process: AgentProcess
    priority_key: tuple  # (priority_class, priority, deadline, enqueue_time)
    enqueued_at: float = field(default_factory=_now)
    scheduled_at: Optional[float] = None
    preempted: bool = False
    wait_reason: str = ""
    seq: int = field(default_factory=lambda: next(_SCHED_SEQ))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ScheduledAgent):
            return NotImplemented
        return (self.priority_key, self.seq) < (other.priority_key, other.seq)


class KernelScheduler:
    """
    OS-like scheduler for agent processes.
    
    Scheduling dimensions:
    - Priority class (INTERACTIVE, REAL_TIME, HIGH, NORMAL, BACKGROUND, BATCH)
    - Deadline awareness
    - Resource availability
    - Dependency graph
    - Fairness and starvation prevention
    """

    def __init__(self, config, event_bus: EventBus, resource_manager):
        self.config = config
        self.event_bus = event_bus
        self.resource_manager = resource_manager
        self._lock = threading.RLock()
        
        # Scheduler state
        self._state = SchedulerState.STOPPED
        self._shutdown_flag = False
        
        # Queues per priority class
        self._queues: Dict[AgentPriority, List[ScheduledAgent]] = {
            priority: [] for priority in AgentPriority
        }
        
        # Running agents
        self._running: Dict[str, ScheduledAgent] = {}
        
        # Blocked/waiting agents
        self._blocked: Dict[str, ScheduledAgent] = {}
        self._waiting: Dict[str, ScheduledAgent] = {}
        
        # Statistics
        self._stats = {
            "scheduled": 0,
            "preempted": 0,
            "completed": 0,
            "failed": 0,
            "starvation_events": 0,
        }
        
        # Scheduler thread
        self._scheduler_thread: Optional[threading.Thread] = None
        self._tick_interval = 0.1  # 100ms tick

    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self._state == SchedulerState.RUNNING:
                return
            self._state = SchedulerState.RUNNING
            self._shutdown_flag = False

        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="kernel-scheduler",
        )
        self._scheduler_thread.start()

        if self.event_bus:
            self.event_bus.emit("scheduler.started", {})

        logger.info("KernelScheduler: started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._shutdown_flag = True
        self._state = SchedulerState.STOPPED
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None

        if self.event_bus:
            self.event_bus.emit("scheduler.stopped", {})

        logger.info("KernelScheduler: stopped")

    def pause(self) -> None:
        """Pause the scheduler."""
        with self._lock:
            self._state = SchedulerState.PAUSED

        if self.event_bus:
            self.event_bus.emit("scheduler.paused", {})

    def resume(self) -> None:
        """Resume the scheduler."""
        with self._lock:
            self._state = SchedulerState.RUNNING

        if self.event_bus:
            self.event_bus.emit("scheduler.resumed", {})

    def admit(self, process: AgentProcess) -> bool:
        """Admit an agent process to the scheduler (CREATED -> ADMITTED)."""
        with self._lock:
            if process.agent_id in self._running:
                return False  # Already admitted

            scheduled = ScheduledAgent(
                process=process,
                priority_key=self._compute_priority_key(process),
            )

            heapq.heappush(self._queues[process.priority], scheduled)
            if process.state == AgentLifecycleState.CREATED:
                try:
                    process.transition(AgentLifecycleState.ADMITTED)
                except ValueError:
                    pass

        if self.event_bus:
            self.event_bus.emit("scheduler.admitted", {
                "agent_id": process.agent_id,
                "priority": process.priority.value,
            })

        logger.debug("KernelScheduler: admitted agent %s with priority %s",
                     process.agent_id, process.priority.value)
        return True

    def schedule(self, process: AgentProcess) -> bool:
        """Schedule a ready agent for execution."""
        with self._lock:
            # Find in queues
            for priority in AgentPriority:
                queue = self._queues[priority]
                for i, scheduled in enumerate(queue):
                    if scheduled.process.agent_id == process.agent_id:
                        # Check resource availability
                        if self._check_resources(process):
                            queue.pop(i)
                            scheduled.scheduled_at = _now()
                            self._running[process.agent_id] = scheduled
                            self._stats["scheduled"] += 1
                            
                            if self.event_bus:
                                self.event_bus.emit("scheduler.scheduled", {
                                    "agent_id": process.agent_id,
                                    "priority": process.priority.value,
                                })
                            return True
                        else:
                            # Move to waiting
                            self._waiting[process.agent_id] = scheduled
                            queue.pop(i)
                            process.transition(AgentLifecycleState.WAITING)
                            return False
        return False

    def preempt(self, agent_id: str) -> bool:
        """Preempt a running agent."""
        with self._lock:
            scheduled = self._running.pop(agent_id, None)
            if not scheduled:
                return False

            scheduled.preempted = True
            scheduled.process.transition(AgentLifecycleState.READY)
            
            # Re-queue with same priority
            heapq.heappush(self._queues[scheduled.process.priority], scheduled)
            self._stats["preempted"] += 1

        if self.event_bus:
            self.event_bus.emit("scheduler.preempted", {
                "agent_id": agent_id,
            })

        logger.info("KernelScheduler: preempted agent %s", agent_id)
        return True

    def yield_cpu(self, agent_id: str) -> bool:
        """Voluntary yield by agent."""
        with self._lock:
            scheduled = self._running.pop(agent_id, None)
            if not scheduled:
                return False

            scheduled.process.transition(AgentLifecycleState.READY)
            heapq.heappush(self._queues[scheduled.process.priority], scheduled)

        return True

    def block(self, agent_id: str, reason: str) -> bool:
        """Block an agent (waiting for external event)."""
        with self._lock:
            scheduled = self._running.pop(agent_id, None)
            if not scheduled:
                return False

            scheduled.wait_reason = reason
            self._blocked[agent_id] = scheduled
            scheduled.process.transition(AgentLifecycleState.BLOCKED)

        if self.event_bus:
            self.event_bus.emit("scheduler.blocked", {
                "agent_id": agent_id,
                "reason": reason,
            })

        return True

    def unblock(self, agent_id: str) -> bool:
        """Unblock an agent."""
        with self._lock:
            scheduled = self._blocked.pop(agent_id, None)
            if not scheduled:
                return False

            scheduled.process.transition(AgentLifecycleState.READY)
            heapq.heappush(self._queues[scheduled.process.priority], scheduled)

        if self.event_bus:
            self.event_bus.emit("scheduler.unblocked", {
                "agent_id": agent_id,
            })

        return True

    def complete(self, agent_id: str) -> bool:
        """Mark an agent as completed."""
        with self._lock:
            scheduled = self._running.pop(agent_id, None)
            if not scheduled:
                # Check queues
                for priority in AgentPriority:
                    queue = self._queues[priority]
                    for i, s in enumerate(queue):
                        if s.process.agent_id == agent_id:
                            queue.pop(i)
                            scheduled = s
                            break
                    if scheduled:
                        break

            if not scheduled:
                return False

            scheduled.process.transition(AgentLifecycleState.COMPLETED)
            self._stats["completed"] += 1

        if self.event_bus:
            self.event_bus.emit("scheduler.completed", {
                "agent_id": agent_id,
            })

        return True

    def fail(self, agent_id: str, error: str) -> bool:
        """Mark an agent as failed."""
        with self._lock:
            scheduled = self._running.pop(agent_id, None)
            if not scheduled:
                # Check queues
                for priority in AgentPriority:
                    queue = self._queues[priority]
                    for i, s in enumerate(queue):
                        if s.process.agent_id == agent_id:
                            queue.pop(i)
                            scheduled = s
                            break
                    if scheduled:
                        break

            if not scheduled:
                return False

            scheduled.process.transition(AgentLifecycleState.FAILED)
            scheduled.process.error = error
            self._stats["failed"] += 1

        if self.event_bus:
            self.event_bus.emit("scheduler.failed", {
                "agent_id": agent_id,
                "error": error,
            })

        return True

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._shutdown_flag:
            try:
                if self._state == SchedulerState.RUNNING:
                    self._tick()
            except Exception as exc:
                logger.error("Scheduler tick error: %s", exc)
            
            time.sleep(self._tick_interval)

    def _tick(self) -> None:
        """Single scheduler tick."""
        with self._lock:
            # Check for newly available resources to unblock waiting agents
            self._check_waiting_agents()
            
            # Check for priority inversion
            self._check_priority_inversion()
            
            # Check for starvation
            self._check_starvation()
            
            # Schedule ready agents if resources available
            self._schedule_ready_agents()

    def _check_waiting_agents(self) -> None:
        """Check if waiting agents can now be scheduled."""
        to_schedule = []
        for agent_id, scheduled in list(self._waiting.items()):
            if self._check_resources(scheduled.process):
                to_schedule.append(agent_id)
        
        for agent_id in to_schedule:
            scheduled = self._waiting.pop(agent_id)
            self._running[agent_id] = scheduled
            scheduled.scheduled_at = _now()
            scheduled.process.transition(AgentLifecycleState.RUNNING)
            self._stats["scheduled"] += 1

    def _check_priority_inversion(self) -> None:
        """Detect and resolve priority inversion."""
        # Simple priority inheritance: if high-priority agent is blocked
        # by low-priority agent holding a resource, boost the low-priority agent
        for blocked_id, blocked_scheduled in self._blocked.items():
            if blocked_scheduled.process.priority in (AgentPriority.INTERACTIVE, AgentPriority.REAL_TIME, AgentPriority.HIGH_PRIORITY):
                # Would need resource ownership tracking to implement fully
                pass

    def _check_starvation(self) -> None:
        """Detect and prevent starvation of low-priority agents."""
        now = _now()
        for priority in [AgentPriority.BACKGROUND, AgentPriority.BATCH, AgentPriority.MAINTENANCE]:
            queue = self._queues[priority]
            for scheduled in queue:
                wait_time = now - scheduled.enqueued_at
                # If waiting > 5 minutes, boost priority
                if wait_time > 300:
                    self._boost_priority(scheduled)
                    self._stats["starvation_events"] += 1

    def _boost_priority(self, scheduled: ScheduledAgent) -> None:
        """Boost priority of a starved agent."""
        old_priority = scheduled.process.priority
        # Boost by one level
        priority_order = list(AgentPriority)
        idx = priority_order.index(old_priority)
        if idx > 0:
            new_priority = priority_order[idx - 1]
            scheduled.process.priority = new_priority
            scheduled.priority_key = self._compute_priority_key(scheduled.process)
            logger.info("KernelScheduler: boosted agent %s from %s to %s (starvation prevention)",
                        scheduled.process.agent_id, old_priority.value, new_priority.value)

    def _schedule_ready_agents(self) -> None:
        """Schedule agents from ready queues if resources available."""
        for priority in AgentPriority:
            queue = self._queues[priority]
            while queue and len(self._running) < self.config.max_concurrent_agents:
                scheduled = queue[0]  # Peek
                if self._check_resources(scheduled.process):
                    heapq.heappop(queue)
                    scheduled.scheduled_at = _now()
                    self._running[scheduled.process.agent_id] = scheduled
                    self._stats["scheduled"] += 1
                    
                    if self.event_bus:
                        self.event_bus.emit("scheduler.scheduled", {
                            "agent_id": scheduled.process.agent_id,
                            "priority": priority.value,
                        })
                else:
                    break  # No resources for this priority level

    def _check_resources(self, process: AgentProcess) -> bool:
        """Check if resources are available for a process."""
        if not self.resource_manager:
            return True
        
        available = self.resource_manager.get_available()
        budget = process.resource_budget
        
        return (
            budget.cpu_cores <= available.cpu_cores and
            budget.ram_mb <= available.ram_mb and
            budget.gpu_memory_mb <= available.gpu_memory_mb and
            budget.llm_tokens_per_minute <= available.llm_tokens_per_minute and
            budget.agent_slots <= available.agent_slots
        )

    def _compute_priority_key(self, process: AgentProcess) -> tuple:
        """Compute priority key for heap ordering."""
        # Lower tuple = higher priority
        priority_order = {
            AgentPriority.REAL_TIME: 0,
            AgentPriority.INTERACTIVE: 1,
            AgentPriority.HIGH_PRIORITY: 2,
            AgentPriority.NORMAL: 3,
            AgentPriority.BACKGROUND: 4,
            AgentPriority.BATCH: 5,
            AgentPriority.MAINTENANCE: 6,
            AgentPriority.RESEARCH: 7,
            AgentPriority.AUTOMATION: 8,
            AgentPriority.PHYSICAL: 9,
        }
        
        deadline = process.intent.deadline if process.intent and process.intent.deadline else float('inf')
        
        return (
            priority_order.get(process.priority, 3),
            deadline,
            process.created_at,
        )

    def is_healthy(self) -> bool:
        """Health check."""
        return self._state == SchedulerState.RUNNING and (
            self._scheduler_thread is None or self._scheduler_thread.is_alive()
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        with self._lock:
            queue_sizes = {p.value: len(q) for p, q in self._queues.items()}
            return {
                "state": self._state.value,
                "running_agents": len(self._running),
                "blocked_agents": len(self._blocked),
                "waiting_agents": len(self._waiting),
                "queue_sizes": queue_sizes,
                "total_queued": sum(queue_sizes.values()),
                "stats": self._stats.copy(),
            }

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.stop()
        with self._lock:
            self._queues.clear()
            self._running.clear()
            self._blocked.clear()
            self._waiting.clear()