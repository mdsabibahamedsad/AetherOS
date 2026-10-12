"""
Task Allocator — assigns tasks to the best-suited agent types.

Evaluates agent capabilities, current workload, estimated completion time,
tool availability, priority, and resource limits to make optimal assignments.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus
from swarm.registry import SwarmAgentRegistry, AgentTypeProfile
from swarm.planner import AgentTask, AgentTaskStatus

logger = logging.getLogger(__name__)


@dataclass
class Assignment:
    """The result of assigning a task to an agent type.

    Attributes:
        task_id: The assigned task ID
        plan_id: The plan containing the task
        agent_type: The agent type assigned
        confidence: Confidence score (0.0 - 1.0)
        reasoning: Why this agent type was chosen
        estimated_duration: Estimated completion time in seconds
        assigned_at: When the assignment was made
    """
    task_id: str = ""
    plan_id: str = ""
    agent_type: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    estimated_duration: float = 0.0
    assigned_at: float = field(default_factory=time.time)


class TaskAllocator:
    """Allocates tasks to agent types based on capability fit and workload.

    Usage:
        allocator = TaskAllocator(agent_registry, event_bus)
        assignment = allocator.find_best_agent(task, plan_id)
    """

    def __init__(
        self,
        agent_registry: SwarmAgentRegistry,
        event_bus: Optional[EventBus] = None,
    ):
        self._registry = agent_registry
        self._event_bus = event_bus
        self._lock = threading.RLock()
        # Track current assignments per agent type
        self._active_count: Dict[str, int] = {}
        # Track completed assignments for stats
        self._assignments: List[Assignment] = []

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def find_best_agent(self, task: AgentTask,
                        plan_id: str = "") -> Optional[Assignment]:
        """Find the best agent type for a task.

        Evaluates all registered agent types against the task's requirements
        and selects the best match based on:
          1. Capability match (required capabilities)
          2. Tool availability
          3. Current workload
          4. Speed rating
          5. Cost efficiency

        Returns an Assignment or None if no suitable agent is found.
        """
        candidates = self._find_candidates(task)
        if not candidates:
            logger.warning(
                "TaskAllocator: no agent type found for task '%s' (needs: %s)",
                task.description[:60], task.required_capabilities,
            )
            return None

        # Score candidates
        scored = []
        for profile, match_count in candidates:
            score = self._score_assignment(profile, task, match_count)
            scored.append((score, profile))

        scored.sort(key=lambda x: -x[0])

        best_profile = scored[0][1] if scored else None
        if best_profile is None:
            return None

        # Track the assignment
        with self._lock:
            self._active_count[best_profile.name] = \
                self._active_count.get(best_profile.name, 0) + 1

        estimated = self._estimate_duration(task, best_profile)

        assignment = Assignment(
            task_id=task.id,
            plan_id=plan_id,
            agent_type=best_profile.name,
            confidence=scored[0][0] / 100.0 if scored else 0.0,
            reasoning=self._build_reasoning(best_profile, task),
            estimated_duration=estimated,
        )

        with self._lock:
            self._assignments.append(assignment)

        logger.info(
            "TaskAllocator: assigned task '%s' to '%s' (score=%.1f)",
            task.description[:60], best_profile.name, scored[0][0],
        )

        if self._event_bus:
            self._event_bus.emit_async("swarm.task_assigned", {
                "task_id": task.id,
                "plan_id": plan_id,
                "agent_type": best_profile.name,
                "confidence": assignment.confidence,
            })

        return assignment

    def find_best_agent_for_goal(
        self, goal: str,
        required_capabilities: Set[str],
    ) -> Optional[AgentTypeProfile]:
        """Find the best agent type for a free-form goal without a task object."""
        candidates = self._registry.find_by_capabilities(required_capabilities)
        if not candidates:
            return None

        scored = []
        for profile in candidates:
            match_count = len(required_capabilities & profile.capabilities)
            score = (
                match_count * 20
                - profile.cost_per_call
                + (10 - profile.speed_rating) * 5
                - self._active_count.get(profile.name, 0) * 10
            )
            scored.append((score, profile))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None

    def release_assignment(self, agent_type: str) -> None:
        """Release an assignment (called when task completes/fails)."""
        with self._lock:
            current = self._active_count.get(agent_type, 0)
            if current > 0:
                self._active_count[agent_type] = current - 1

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _find_candidates(self, task: AgentTask) -> List:
        """Find agent types that could handle this task."""
        candidates = []
        if task.preferred_agent_type:
            profile = self._registry.get(task.preferred_agent_type)
            if profile:
                match = len(task.required_capabilities & profile.capabilities)
                if match > 0 or not task.required_capabilities:
                    candidates.append((profile, match))
                    return candidates

        # Find by capability match
        matching = self._registry.find_by_capabilities(
            task.required_capabilities,
            min_match=1,
        )
        for profile in matching:
            match = len(task.required_capabilities & profile.capabilities)
            candidates.append((profile, match))

        return candidates

    def _score_assignment(self, profile: AgentTypeProfile,
                          task: AgentTask, match_count: int) -> float:
        """Score how well an agent type fits a task.

        Returns a score where higher is better.
        """
        score = 0.0

        # Capability match (most important)
        score += match_count * 25.0

        # Tool availability
        if task.context.get("required_tools"):
            tool_overlap = len(
                set(task.context["required_tools"]) & set(profile.supported_tools)
            )
            score += tool_overlap * 10.0

        # Speed bonus
        score += (10 - profile.speed_rating) * 5.0

        # Cost efficiency
        score -= profile.cost_per_call * 0.5

        # Workload penalty
        active = self._active_count.get(profile.name, 0)
        if active >= profile.max_concurrent:
            score -= 100.0  # Overloaded
        score -= active * 10.0

        # Priority bonus for high-priority tasks
        if task.priority <= 20:
            score += profile.priority * 0.5

        return max(score, 0.0)

    def _estimate_duration(self, task: AgentTask,
                           profile: AgentTypeProfile) -> float:
        """Estimate task duration based on agent type and task complexity."""
        base = 30.0  # minimum 30 seconds
        complexity = len(task.description) / 100.0
        speed_factor = profile.speed_rating / 5.0
        return max(base * speed_factor * max(complexity, 1.0), 30.0)

    @staticmethod
    def _build_reasoning(profile: AgentTypeProfile,
                         task: AgentTask) -> str:
        """Build a human-readable reasoning string for the assignment."""
        matched = profile.capabilities & task.required_capabilities
        parts = [
            f"Agent '{profile.name}' matches {len(matched)}/{len(task.required_capabilities)} "
            f"required capabilities: {', '.join(sorted(matched))}",
            f"Cost: {profile.cost_per_call}, Speed: {profile.speed_rating}/10",
        ]
        if profile.supported_tools:
            parts.append(f"Available tools: {len(profile.supported_tools)}")
        return "; ".join(parts)

    # ------------------------------------------------------------------
    # State & statistics
    # ------------------------------------------------------------------

    def get_workload(self) -> Dict[str, int]:
        """Get the current workload count per agent type."""
        with self._lock:
            return dict(self._active_count)

    def get_stats(self) -> Dict[str, Any]:
        """Return allocator statistics."""
        with self._lock:
            return {
                "total_assignments": len(self._assignments),
                "active_assignments": len(self._active_count),
                "workload": dict(self._active_count),
            }

    def reset(self) -> None:
        """Reset all tracking state."""
        with self._lock:
            self._active_count.clear()
            self._assignments.clear()
