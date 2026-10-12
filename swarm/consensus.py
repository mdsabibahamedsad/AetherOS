"""
Consensus Engine — reaches agreements when multiple agents disagree.

When agents produce conflicting results, the consensus engine:
  1. Collects evidence from each agent
  2. Compares confidence levels
  3. Conducts a weighted vote
  4. Allows a reviewer agent to override
  5. Produces a final decision

Designed to be optional — consensus is only triggered when
conflicting outputs are detected by the result merger.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """The result of a consensus decision.

    Attributes:
        id: Unique consensus ID
        topic: What was being decided
        decision: The final decision/result
        confidence: Overall confidence (0.0 - 1.0)
        votes: How each agent voted
        evidence: Supporting evidence collected
        override_by: If a reviewer overrode the vote
        resolved_at: When consensus was reached
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = ""
    decision: Any = None
    confidence: float = 0.0
    votes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    override_by: Optional[str] = None
    resolved_at: float = field(default_factory=time.time)


@dataclass
class Vote:
    """A single agent's vote in a consensus.

    Attributes:
        agent_id: The voting agent
        choice: The agent's choice/answer
        confidence: Agent's confidence (0.0 - 1.0)
        reasoning: Why the agent chose this
        evidence: Supporting evidence
    """
    agent_id: str
    choice: Any
    confidence: float = 0.5
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)


class ConsensusEngine:
    """Reaches consensus among multiple agents on a given topic.

    Supports weighted voting, evidence collection, and reviewer overrides.

    Usage:
        engine = ConsensusEngine(event_bus)
        result = engine.resolve(
            topic="What should the error handling strategy be?",
            votes=[vote1, vote2, vote3],
        )
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._history: List[ConsensusResult] = []

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, topic: str, votes: List[Vote],
                reviewer_override: Optional[Callable[[str, List[Vote]], Any]] = None,
                min_confidence: float = 0.3,
                weighted: bool = True) -> ConsensusResult:
        """Resolve a set of votes into a consensus decision.

        Args:
            topic: What is being decided
            votes: List of votes from agents
            reviewer_override: Optional callable that can override the vote
            min_confidence: Minimum confidence to consider a vote
            weighted: Whether to weight votes by confidence

        Returns:
            ConsensusResult with the final decision
        """
        if not votes:
            return ConsensusResult(
                topic=topic,
                decision=None,
                confidence=0.0,
                votes={},
            )

        # Filter low-confidence votes
        valid_votes = [v for v in votes if v.confidence >= min_confidence]
        if not valid_votes:
            # Fall back to all votes if all are low confidence
            valid_votes = votes

        # Count votes with optional weighting
        if weighted:
            decision, confidence = self._weighted_vote(valid_votes)
        else:
            decision, confidence = self._simple_vote(valid_votes)

        # Build evidence list
        evidence = []
        for v in valid_votes:
            for ev in v.evidence:
                evidence.append({
                    "agent_id": v.agent_id,
                    "evidence": ev,
                    "confidence": v.confidence,
                })

        # Check for reviewer override
        override_by = None
        if reviewer_override and len(valid_votes) > 1:
            try:
                override = reviewer_override(topic, valid_votes)
                if override is not None:
                    decision = override
                    override_by = "reviewer"
                    confidence = max(confidence, 0.9)
                    logger.info(
                        "Consensus: reviewer override on '%s'", topic[:60],
                    )
            except Exception as exc:
                logger.warning("Consensus: reviewer override failed: %s", exc)

        # Build votes dict
        votes_dict = {
            v.agent_id: {
                "choice": v.choice,
                "confidence": v.confidence,
                "reasoning": v.reasoning,
            }
            for v in valid_votes
        }

        result = ConsensusResult(
            topic=topic,
            decision=decision,
            confidence=confidence,
            votes=votes_dict,
            evidence=evidence,
            override_by=override_by,
        )

        with self._lock:
            self._history.append(result)

        if self._event_bus:
            self._event_bus.emit_async("swarm.consensus_resolved", {
                "topic": topic[:100],
                "confidence": confidence,
                "vote_count": len(votes),
                "override": override_by is not None,
            })

        logger.info(
            "Consensus: resolved '%s' with %.0f%% confidence (%d votes%s)",
            topic[:60], confidence * 100, len(votes),
            f", overridden by {override_by}" if override_by else "",
        )

        return result

    # ------------------------------------------------------------------
    # Voting methods
    # ------------------------------------------------------------------

    @staticmethod
    def _weighted_vote(votes: List[Vote]) -> tuple:
        """Weighted voting — each vote's influence is scaled by confidence.

        Returns (decision, overall_confidence).
        """
        # Group choices by similarity (string-based grouping)
        choice_groups: Dict[str, List[Vote]] = {}
        for v in votes:
            key = str(v.choice).strip().lower()[:100]
            choice_groups.setdefault(key, []).append(v)

        # Score each group by weighted confidence
        best_score = -1.0
        best_choice = None
        total_confidence = sum(v.confidence for v in votes)

        for choice_key, group in choice_groups.items():
            score = sum(v.confidence for v in group)
            if score > best_score:
                best_score = score
                best_choice = group[0].choice  # Use original format

        if best_choice is None:
            return (None, 0.0)

        overall = best_score / total_confidence if total_confidence > 0 else 0.0
        return (best_choice, min(overall, 1.0))

    @staticmethod
    def _simple_vote(votes: List[Vote]) -> tuple:
        """Simple majority voting.

        Returns (decision, overall_confidence).
        """
        choice_counts: Dict[str, List[Vote]] = {}
        for v in votes:
            key = str(v.choice).strip().lower()[:100]
            choice_counts.setdefault(key, []).append(v)

        best_count = 0
        best_choice = None
        for choice_key, group in choice_counts.items():
            if len(group) > best_count:
                best_count = len(group)
                best_choice = group[0].choice

        if best_choice is None:
            return (None, 0.0)

        overall = best_count / len(votes) if votes else 0.0
        return (best_choice, overall)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 10) -> List[ConsensusResult]:
        """Get recent consensus results."""
        with self._lock:
            return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get consensus engine statistics."""
        with self._lock:
            return {
                "total_resolutions": len(self._history),
                "average_confidence": (
                    sum(r.confidence for r in self._history) / len(self._history)
                    if self._history else 0.0
                ),
                "overrides": sum(1 for r in self._history if r.override_by),
            }

    def clear_history(self) -> None:
        """Clear consensus history."""
        with self._lock:
            self._history.clear()
