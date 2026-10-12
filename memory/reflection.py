"""
Reflection Engine — analyzes completed workflows and learns from outcomes.

After every completed workflow or significant event, the reflection engine:
  1. Analyzes what succeeded and what failed
  2. Records lessons learned
  3. Updates procedural memory with improved strategies
  4. Improves future planning and execution
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.procedural import ProceduralMemory, Procedure
from memory.semantic import SemanticMemory

logger = logging.getLogger(__name__)


@dataclass
class Reflection:
    """A recorded reflection from a completed workflow.

    Attributes:
        id: Unique reflection ID
        goal: The original goal/workflow
        outcome: What happened (success, partial, failed)
        successes: What went well
        failures: What went wrong
        lessons: Lessons learned
        procedural_updates: Suggested procedure improvements
        duration_seconds: How long the workflow took
        task_count: Number of tasks in the workflow
        tags: Categorization tags
        timestamp: When the reflection was made
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    goal: str = ""
    outcome: str = "success"
    successes: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    procedural_updates: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    task_count: int = 0
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReflectionEngine:
    """Analyzes completed workflows and generates reflections.

    Reflections can be used to update procedural memory, improve
    planning strategies, and provide feedback to the learning engine.

    Usage:
        engine = ReflectionEngine(store, procedural_memory, semantic_memory)
        reflection = engine.reflect_on_workflow(
            goal="Build auth system",
            outcome="success",
            successes=["Implemented JWT tokens"],
            failures=["Rate limiting was tricky"],
        )
        recommendations = engine.get_actionable_recommendations()
    """

    def __init__(self, store: MemoryStore,
                 procedural_memory: Optional[ProceduralMemory] = None,
                 semantic_memory: Optional[SemanticMemory] = None):
        self._store = store
        self._procedural = procedural_memory
        self._semantic = semantic_memory
        self._lock = threading.RLock()
        self._reflect_hooks: List[Callable[[Reflection], None]] = []

    # ------------------------------------------------------------------
    # Reflection recording
    # ------------------------------------------------------------------

    def reflect_on_workflow(self, goal: str, outcome: str,
                            successes: List[str] = None,
                            failures: List[str] = None,
                            lessons: List[str] = None,
                            duration_seconds: float = 0.0,
                            task_count: int = 0,
                            tags: List[str] = None) -> Reflection:
        """Record a reflection on a completed workflow.

        Generates a reflection, stores it, and optionally updates
        procedural and semantic memory with insights.

        Returns the generated Reflection.
        """
        if outcome in ("success", "completed"):
            lessons = lessons or successes or []
        else:
            lessons = lessons or failures or []

        reflection = Reflection(
            goal=goal[:500],
            outcome=outcome,
            successes=successes or [],
            failures=failures or [],
            lessons=lessons or [],
            duration_seconds=duration_seconds,
            task_count=task_count,
            tags=tags or ["reflection"],
        )

        # Store the reflection
        self._store.save(
            key=f"reflection:{reflection.id}",
            value=reflection,
            memory_type="reflection",
            scope=MemoryScope.GLOBAL,
            tags=reflection.tags + ["reflection"],
            metadata={
                "goal": reflection.goal[:200],
                "outcome": reflection.outcome,
                "lesson_count": len(reflection.lessons),
            },
            importance=0.7 if outcome == "success" else 0.9,
            source="reflection",
        )

        # Update procedural memory with lessons
        if self._procedural and lessons:
            self._update_procedural_memory(reflection)

        # Update semantic memory with outcomes
        if self._semantic:
            self._update_semantic_memory(reflection)

        # Notify hooks
        for hook in self._reflect_hooks:
            try:
                hook(reflection)
            except Exception as exc:
                logger.warning("Reflection: hook failed: %s", exc)

        logger.info(
            "Reflection: recorded '%s' (%s) with %d lessons",
            goal[:60], outcome, len(lessons),
        )
        return reflection

    def reflect_task_outcome(self, task_description: str, outcome: str,
                             error: str = "") -> Reflection:
        """Reflect on a single task outcome."""
        failures = [error] if error else []
        successes = [outcome] if outcome == "success" else []
        return self.reflect_on_workflow(
            goal=task_description,
            outcome=outcome,
            successes=successes,
            failures=failures,
            lessons=[outcome if outcome == "success" else error] if (outcome or error) else [],
            task_count=1,
        )

    # ------------------------------------------------------------------
    # Procedural memory updates
    # ------------------------------------------------------------------

    def _update_procedural_memory(self, reflection: Reflection) -> None:
        """Update procedural memory based on reflection insights."""
        if not self._procedural:
            return

        if reflection.outcome == "success" and reflection.successes:
            # Record successful strategies as procedures
            for i, success in enumerate(reflection.successes[:3]):
                proc = Procedure(
                    name=f"Strategy: {success[:100]}",
                    description=f"Learned from: {reflection.goal[:200]}",
                    steps=[success],
                    context=reflection.goal[:200],
                    expected_outcome="Success",
                    success_rate=0.8,
                    tags=["reflection", "learned"],
                )
                self._procedural.record(proc)

        if reflection.outcome in ("failed", "partial") and reflection.failures:
            # Record anti-patterns
            for failure in reflection.failures[:3]:
                proc = Procedure(
                    name=f"Avoid: {failure[:100]}",
                    description=f"Failed approach from: {reflection.goal[:200]}",
                    steps=[f"Avoid: {failure}"],
                    context=reflection.goal[:200],
                    expected_outcome="Avoid this approach",
                    success_rate=0.1,
                    tags=["reflection", "anti-pattern"],
                )
                self._procedural.record(proc)

    def _update_semantic_memory(self, reflection: Reflection) -> None:
        """Update semantic memory with outcome knowledge."""
        if not self._semantic:
            return

        for lesson in reflection.lessons:
            if lesson:
                self._semantic.learn(
                    subject=reflection.goal[:100],
                    predicate="lesson",
                    object=lesson[:200],
                    confidence=0.7 if reflection.outcome == "success" else 0.5,
                    source="reflection",
                )

    def get_recent(self, limit: int = 20) -> List[Reflection]:
        """Get the most recent reflections."""
        entries = self._store.search(
            memory_type="reflection",
            limit=limit,
        )
        return [e.value for e in entries if isinstance(e.value, Reflection)]

    def get_by_outcome(self, outcome: str, limit: int = 20) -> List[Reflection]:
        """Get reflections filtered by outcome."""
        entries = self._store.search(
            memory_type="reflection",
            limit=100,
        )
        return [
            e.value for e in entries
            if isinstance(e.value, Reflection) and e.value.outcome == outcome
        ][:limit]

    def get_lessons(self, limit: int = 50) -> List[str]:
        """Get all recorded lessons across reflections."""
        reflections = self.get_recent(limit=limit)
        lessons = []
        for r in reflections:
            lessons.extend(r.lessons)
        return lessons

    def get_recommendations(self, context: str = "",
                            limit: int = 5) -> List[str]:
        """Get actionable recommendations based on past reflections."""
        reflections = self.get_recent(limit=50)
        # Filter by context
        if context:
            ctx_lower = context.lower()
            reflections = [
                r for r in reflections
                if ctx_lower in r.goal.lower()
                or any(ctx_lower in l.lower() for l in r.lessons)
            ]

        # Extract recommendations
        recs = []
        for r in reflections:
            if r.outcome == "success" and r.successes:
                recs.extend(r.successes[:2])
            elif r.outcome in ("failed", "partial") and r.failures:
                recs.append(f"Avoid: {r.failures[0]}")

        return recs[:limit]

    def subscribe(self, hook: Callable[[Reflection], None]) -> Callable:
        """Subscribe to reflection events.

        Hooks are called after every reflection is recorded.
        Returns an unsubscribe function.
        """
        with self._lock:
            self._reflect_hooks.append(hook)

        def unsubscribe():
            with self._lock:
                if hook in self._reflect_hooks:
                    self._reflect_hooks.remove(hook)

        return unsubscribe

    def get_stats(self) -> Dict[str, Any]:
        """Get reflection engine statistics."""
        reflections = self.get_recent(limit=10000)
        successes = sum(1 for r in reflections if r.outcome in ("success", "completed"))
        failures = sum(1 for r in reflections if r.outcome in ("failed", "error"))
        return {
            "total_reflections": len(reflections),
            "successes": successes,
            "failures": failures,
            "total_lessons": sum(len(r.lessons) for r in reflections),
        }
