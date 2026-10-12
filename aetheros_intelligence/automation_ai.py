"""
Automation AI for AetherOS Intelligence Engine.

Observes repetitive tasks and suggests automation.
Never automates without explicit user approval.

Works with the AetherOS automation engine.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskObservation:
    """An observed task that may be automatable."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    pattern: str = ""
    frequency: int = 1
    avg_duration_ms: float = 0.0
    last_observed: float = field(default_factory=time.time)
    first_observed: float = field(default_factory=time.time)
    approved: bool = False
    automated: bool = False
    automation_script: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AutomationAI:
    """Observes tasks and suggests automations with user approval.

    Usage::

        ai = AutomationAI()

        # Observe a task
        ai.observe_task("deploy", "Deploy to staging", duration_ms=45000)

        # Get automation suggestions
        suggestions = ai.get_suggestions()

        # Approve and generate automation
        ai.approve_automation(observation_id)
        script = ai.generate_automation(observation_id)
    """

    def __init__(self) -> None:
        self._observations: Dict[str, TaskObservation] = {}

    # ------------------------------------------------------------------
    # Task observation
    # ------------------------------------------------------------------

    def observe_task(self, name: str, description: str = "",
                     pattern: str = "",
                     duration_ms: float = 0.0) -> Dict[str, Any]:
        """Record a task observation.

        If a similar task was already observed, increments frequency
        and updates the average duration.
        """
        existing = self._find_matching(name, pattern)

        if existing:
            old_avg = existing.avg_duration_ms
            old_freq = existing.frequency
            existing.frequency += 1
            existing.avg_duration_ms = (
                (old_avg * old_freq + duration_ms) / existing.frequency
            )
            existing.last_observed = time.time()
            logger.debug("Updated observation: %s (freq=%d)",
                         name, existing.frequency)
            return self._to_dict(existing)

        observation = TaskObservation(
            name=name,
            description=description,
            pattern=pattern or name,
            avg_duration_ms=duration_ms,
        )
        self._observations[observation.id] = observation
        logger.info("New task observation: %s (%.1fs)", name, duration_ms / 1000)
        return self._to_dict(observation)

    def observe_batch(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Observe multiple tasks at once."""
        return [
            self.observe_task(
                name=t.get("name", "task"),
                description=t.get("description", ""),
                pattern=t.get("pattern", ""),
                duration_ms=t.get("duration_ms", 0.0),
            )
            for t in tasks
        ]

    def _find_matching(self, name: str, pattern: str) -> Optional[TaskObservation]:
        """Find an existing observation that matches."""
        for obs in self._observations.values():
            if obs.name == name or (pattern and obs.pattern == pattern):
                return obs
            if obs.pattern and pattern and obs.pattern.lower() == pattern.lower():
                return obs
            if not obs.approved and not obs.automated:
                if self._similar(name, obs.name) > 0.8:
                    return obs
        return None

    def _similar(self, a: str, b: str) -> float:
        """Simple string similarity (0.0 - 1.0)."""
        a = a.lower()
        b = b.lower()
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    # ------------------------------------------------------------------
    # Automation suggestions
    # ------------------------------------------------------------------

    def get_suggestions(self, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """Get tasks that are good candidates for automation."""
        suggestions = []
        for obs in self._observations.values():
            if obs.approved or obs.automated:
                continue
            if obs.frequency < min_frequency:
                continue

            time_saved = obs.avg_duration_ms * obs.frequency
            suggestions.append({
                "id": obs.id,
                "name": obs.name,
                "frequency": obs.frequency,
                "avg_duration_ms": round(obs.avg_duration_ms, 0),
                "total_time_saved_ms": round(time_saved, 0),
                "total_time_saved_human": self._format_duration(time_saved),
                "automation_difficulty": self._estimate_difficulty(obs),
                "confidence": min(0.5 + obs.frequency * 0.1, 0.95),
            })

        suggestions.sort(key=lambda s: s["frequency"], reverse=True)
        return suggestions

    def _estimate_difficulty(self, obs: TaskObservation) -> str:
        """Estimate how difficult automation would be."""
        if len(obs.name) < 15:
            return "easy"
        if obs.frequency > 5:
            return "easy"
        if obs.avg_duration_ms < 10000:
            return "easy"
        return "medium"

    def _format_duration(self, ms: float) -> str:
        """Format milliseconds to human-readable."""
        seconds = ms / 1000
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.0f}m"
        hours = minutes / 60
        return f"{hours:.1f}h"

    # ------------------------------------------------------------------
    # Approval & automation
    # ------------------------------------------------------------------

    def approve_automation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        """Approve automation for a specific task."""
        obs = self._observations.get(observation_id)
        if not obs:
            return None
        obs.approved = True
        logger.info("Approved automation for: %s", obs.name)
        return self._to_dict(obs)

    def generate_automation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        """Generate an automation script for an approved observation."""
        obs = self._observations.get(observation_id)
        if not obs:
            return None
        if not obs.approved:
            return {"error": "Task not yet approved for automation"}

        script = self._generate_script(obs)
        obs.automated = True
        obs.automation_script = script
        logger.info("Generated automation for: %s", obs.name)
        return {
            "id": obs.id,
            "name": obs.name,
            "script": script,
            "type": "shell",
            "language": "bash",
        }

    def _generate_script(self, obs: TaskObservation) -> str:
        """Generate a simple automation script for the observed task."""
        name_slug = obs.name.lower().replace(" ", "_")
        return "\n".join([
            f"# Automation for: {obs.name}",
            f"# Generated by AetherOS Automation AI",
            f"# Frequency: {obs.frequency}x, Avg duration: {obs.avg_duration_ms:.0f}ms",
            "",
            f"echo 'Running: {obs.name}'",
            f"# TODO: Implement automation for {obs.name}",
            f"echo 'Complete: {obs.name}'",
        ])

    # ------------------------------------------------------------------
    # Status & management
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get overall automation AI status."""
        total = len(self._observations)
        approved = sum(1 for o in self._observations.values() if o.approved)
        automated = sum(1 for o in self._observations.values() if o.automated)
        pending = total - approved - automated

        return {
            "total_observations": total,
            "approved_for_automation": approved,
            "automated": automated,
            "pending_review": pending,
            "suggestions_available": len(self.get_suggestions()),
        }

    def get_observations(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all observations, optionally filtered."""
        observations = self._observations.values()
        return [self._to_dict(o) for o in observations]

    def reject_observation(self, observation_id: str) -> bool:
        """Reject an automation suggestion."""
        return self._observations.pop(observation_id, None) is not None

    def clear_observations(self) -> None:
        self._observations.clear()

    def _to_dict(self, obs: TaskObservation) -> Dict[str, Any]:
        return {
            "id": obs.id,
            "name": obs.name,
            "description": obs.description,
            "pattern": obs.pattern,
            "frequency": obs.frequency,
            "avg_duration_ms": round(obs.avg_duration_ms, 0),
            "last_observed": obs.last_observed,
            "first_observed": obs.first_observed,
            "approved": obs.approved,
            "automated": obs.automated,
            "automation_script": obs.automation_script[:200] if obs.automation_script else "",
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "observations": len(self._observations),
            "approved": sum(1 for o in self._observations.values() if o.approved),
            "automated": sum(1 for o in self._observations.values() if o.automated),
            "pending": sum(1 for o in self._observations.values()
                          if not o.approved and not o.automated),
        }
