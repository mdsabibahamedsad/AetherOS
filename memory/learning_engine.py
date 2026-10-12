"""
Learning Engine — continuous improvement from experience.

The learning engine improves AetherOS capabilities by learning from:
  - Completed tasks (what worked, what didn't)
  - User corrections (feedback signals)
  - Agent outcomes (success/failure patterns)
  - Tool results (which tools work best for which tasks)
  - Execution history (latency, error patterns)
  - Code reviews (quality patterns)

It does NOT retrain language models. Instead it improves:
  - Planning (better goal decomposition)
  - Retrieval (better memory ranking)
  - Tool selection (which tool for which task)
  - Execution strategy (parallelism, retry policies)
  - Memory ranking (importance scoring)

The learning engine feeds insights into:
  - EpisodicMemory (experiences)
  - SemanticMemory (facts about what works)
  - ProceduralMemory (how-to procedures)
  - ReflectionEngine (lessons learned)
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.episodic import EpisodicMemory, Episode
from memory.semantic import SemanticMemory, Fact
from memory.procedural import ProceduralMemory, Procedure
from memory.reflection import ReflectionEngine, Reflection

logger = logging.getLogger(__name__)


@dataclass
class LearningSample:
    """A single learning observation.

    Attributes:
        id: Unique ID
        category: Category (planning, tool_selection, retrieval, execution, memory)
        observation: What was observed
        context: The context in which it was observed
        outcome: What happened (success, failure)
        confidence: How confident we are (0.0 - 1.0)
        timestamp: When observed
        metadata: Additional data
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    category: str = "general"
    observation: str = ""
    context: str = ""
    outcome: str = "success"
    confidence: float = 0.7
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """Continuous learning from experience.

    Collects learning samples from various sources and uses them to
    improve planning, retrieval, tool selection, execution strategies,
    and memory ranking.

    Usage:
        engine = LearningEngine(store, episodic_memory, semantic_memory,
                                procedural_memory, reflection_engine)
        engine.observe(LearningSample(
            category="tool_selection",
            observation="web_search works better than browser for fact lookup",
            outcome="success",
        ))
        insights = engine.get_insights(category="tool_selection")
    """

    def __init__(self, store: MemoryStore,
                 episodic_memory: Optional[EpisodicMemory] = None,
                 semantic_memory: Optional[SemanticMemory] = None,
                 procedural_memory: Optional[ProceduralMemory] = None,
                 reflection_engine: Optional[ReflectionEngine] = None):
        self._store = store
        self._episodic = episodic_memory
        self._semantic = semantic_memory
        self._procedural = procedural_memory
        self._reflection = reflection_engine
        self._lock = threading.RLock()
        self._learn_hooks: List[Callable[[LearningSample], None]] = []

    # ------------------------------------------------------------------
        # Observation
    # ------------------------------------------------------------------

    def observe(self, sample: LearningSample) -> None:
        """Record a learning observation.

        Stores the observation and feeds it to the appropriate
        memory subsystem based on category.
        """
        # Store the sample
        self._store.save(
            key=f"learn:{sample.id}",
            value=sample,
            memory_type="learning",
            scope=MemoryScope.GLOBAL,
            tags=[sample.category, "learning", sample.outcome],
            metadata={
                "category": sample.category,
                "outcome": sample.outcome,
                "observation": sample.observation[:200],
            },
            importance=0.7 if sample.outcome == "success" else 0.9,
            source="learning",
        )

        # Feed to memory subsystems
        self._feed_episodic(sample)
        self._feed_semantic(sample)
        self._feed_procedural(sample)
        self._feed_reflection(sample)

        # Notify hooks
        for hook in self._learn_hooks:
            try:
                hook(sample)
            except Exception as exc:
                logger.warning("Learning: hook failed: %s", exc)

        logger.debug(
            "Learning: observed '%s' [%s] (%s)",
            sample.observation[:60], sample.category, sample.outcome,
        )

    def observe_tool_result(self, tool_name: str, task: str,
                            success: bool, duration: float = 0.0) -> None:
        """Observe the result of a tool execution."""
        self.observe(LearningSample(
            category="tool_selection",
            observation=f"Tool '{tool_name}' for task '{task}' "
                       f"{'succeeded' if success else 'failed'}",
            context=f"Tool: {tool_name}, Task: {task}",
            outcome="success" if success else "failure",
        ))

    def observe_agent_outcome(self, agent_type: str, goal: str,
                              outcome: str, duration: float = 0.0) -> None:
        """Observe the outcome of an agent execution."""
        self.observe(LearningSample(
            category="execution",
            observation=f"Agent '{agent_type}' {outcome}: {goal[:100]}",
            context=f"Agent: {agent_type}, Goal: {goal[:200]}",
            outcome=outcome,
        ))

    def observe_user_correction(self, original: str, corrected: str) -> None:
        """Observe a user correction."""
        self.observe(LearningSample(
            category="planning",
            observation=f"User corrected: '{original[:100]}' → '{corrected[:100]}'",
            context=f"Original: {original[:200]}",
            outcome="correction",
            confidence=0.9,
        ))

    def observe_task_result(self, task_description: str, success: bool,
                            strategy: str = "") -> None:
        """Observe the result of a task execution."""
        self.observe(LearningSample(
            category="execution",
            observation=f"Task '{task_description[:100]}' "
                       f"{'completed' if success else 'failed'}",
            context=f"Strategy: {strategy}",
            outcome="success" if success else "failure",
        ))

    # ------------------------------------------------------------------
    # Feed memory subsystems
    # ------------------------------------------------------------------

    def _feed_episodic(self, sample: LearningSample) -> None:
        """Feed the sample to episodic memory."""
        if not self._episodic:
            return
        episode = Episode(
            summary=sample.observation[:200],
            context=sample.context[:500],
            outcome=sample.outcome,
            importance=sample.confidence,
            tags=[sample.category, "learning"],
        )
        self._episodic.record(episode)

    def _feed_semantic(self, sample: LearningSample) -> None:
        """Feed the sample to semantic memory."""
        if not self._semantic:
            return
        self._semantic.learn(
            subject=sample.category,
            predicate="outcome",
            object=sample.outcome,
            confidence=sample.confidence,
            source="learning",
        )
        if sample.observation:
            self._semantic.learn(
                subject=sample.observation[:200],
                predicate="context",
                object=sample.context[:200],
                confidence=sample.confidence,
                source="learning",
            )

    def _feed_procedural(self, sample: LearningSample) -> None:
        """Feed the sample to procedural memory."""
        if not self._procedural or sample.outcome != "success":
            return
        proc = Procedure(
            name=sample.observation[:200],
            description=f"Learned from {sample.category} observation",
            steps=[sample.observation],
            context=sample.context[:200],
            success_rate=sample.confidence,
            tags=["learning", sample.category],
        )
        self._procedural.record(proc)

    def _feed_reflection(self, sample: LearningSample) -> None:
        """Feed the sample to the reflection engine."""
        if not self._reflection:
            return
        self._reflection.reflect_task_outcome(
            task_description=sample.observation[:200],
            outcome=sample.outcome,
        )

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def get_insights(self, category: str = "",
                     limit: int = 20) -> List[Dict[str, Any]]:
        """Get learning insights, optionally filtered by category.

        Returns structured insights about what works and what doesn't.
        """
        entries = self._store.search(
            memory_type="learning",
            limit=100,
        )
        samples = [e.value for e in entries if isinstance(e.value, LearningSample)]

        if category:
            samples = [s for s in samples if s.category == category]

        samples.sort(key=lambda s: (s.confidence, s.timestamp), reverse=True)

        insights = []
        for s in samples[:limit]:
            insights.append({
                "category": s.category,
                "observation": s.observation,
                "outcome": s.outcome,
                "confidence": s.confidence,
                "timestamp": s.timestamp,
            })
        return insights

    def get_successful_strategies(self, category: str = "",
                                  limit: int = 10) -> List[str]:
        """Get strategies that have been observed to succeed."""
        samples = self.get_insights(category=category, limit=100)
        return [
            s["observation"] for s in samples
            if s["outcome"] == "success"
        ][:limit]

    def get_failure_patterns(self, category: str = "",
                             limit: int = 10) -> List[str]:
        """Get patterns that have been observed to fail."""
        samples = self.get_insights(category=category, limit=100)
        return [
            s["observation"] for s in samples
            if s["outcome"] == "failure"
        ][:limit]

    def get_best_tool_for_task(self, task: str) -> Optional[str]:
        """Get the best tool for a given task based on past observations."""
        samples = self.get_insights(category="tool_selection", limit=50)
        tool_scores: Dict[str, float] = {}
        for s in samples:
            if "Tool '" not in s["observation"]:
                continue
            parts = s["observation"].split("'")
            if len(parts) >= 2:
                tool = parts[1]
                score = s["confidence"] * (1.0 if s["outcome"] == "success" else -0.5)
                tool_scores[tool] = tool_scores.get(tool, 0) + score

        if not tool_scores:
            return None
        return max(tool_scores, key=tool_scores.get)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def subscribe(self, hook: Callable[[LearningSample], None]) -> Callable:
        """Subscribe to learning events."""
        with self._lock:
            self._learn_hooks.append(hook)

        def unsubscribe():
            with self._lock:
                if hook in self._learn_hooks:
                    self._learn_hooks.remove(hook)

        return unsubscribe

    def get_stats(self) -> Dict[str, Any]:
        """Get learning engine statistics."""
        entries = self._store.search(memory_type="learning", limit=10000)
        samples = [e.value for e in entries if isinstance(e.value, LearningSample)]
        by_category: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        for s in samples:
            by_category[s.category] = by_category.get(s.category, 0) + 1
            by_outcome[s.outcome] = by_outcome.get(s.outcome, 0) + 1
        return {
            "total_samples": len(samples),
            "by_category": by_category,
            "by_outcome": by_outcome,
        }
