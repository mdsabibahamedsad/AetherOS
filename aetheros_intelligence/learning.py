"""
Learning System for AetherOS Intelligence Engine.

Allows users to explicitly approve learning of:
    - Preferred coding style
    - Preferred workflow
    - Favorite tools
    - Common commands
    - Workspace habits
    - Frequently used prompts

Never learns automatically without explicit user permission.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class LearningCategory(Enum):
    CODING_STYLE = "coding_style"
    WORKFLOW = "workflow"
    FAVORITE_TOOLS = "favorite_tools"
    COMMON_COMMANDS = "common_commands"
    WORKSPACE_HABITS = "workspace_habits"
    FREQUENT_PROMPTS = "frequent_prompts"
    GENERIC = "generic"


@dataclass
class LearningSample:
    """A single learning observation approved by the user."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: LearningCategory = LearningCategory.GENERIC
    observation: str = ""
    pattern: str = ""
    context: str = ""
    frequency: int = 1
    confidence: float = 0.5
    approved: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """User-approved learning system.

    Records observations across categories and only applies them
    after explicit user approval. Never learns automatically.

    Usage::

        learning = LearningEngine()

        # Record an observation
        learning.observe("coding_style", "Uses snake_case for variables")

        # Show pending observations for approval
        pending = learning.get_pending()

        # Approve a specific learning
        learning.approve(sample_id)

        # Get learned patterns for a category
        patterns = learning.get_learned("coding_style")
    """

    def __init__(self) -> None:
        self._samples: Dict[str, LearningSample] = {}
        self._learned: Dict[LearningCategory, List[Dict[str, Any]]] = {}
        self._store_path = get_aetheros_home() / "intelligence" / "learning"
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self, category: str, observation: str,
                pattern: str = "",
                context: str = "",
                auto_approve: bool = False) -> Dict[str, Any]:
        """Record a learning observation for later approval.

        Args:
            category: Learning category (coding_style, workflow, etc.)
            observation: What was observed
            pattern: The extracted pattern/rule
            context: Context where the observation was made
            auto_approve: If True, immediately approve (user must have opted in)

        Returns:
            The created sample dict.
        """
        try:
            cat = LearningCategory(category)
        except ValueError:
            cat = LearningCategory.GENERIC

        sample = LearningSample(
            category=cat,
            observation=observation,
            pattern=pattern or observation,
            context=context,
            approved=auto_approve,
        )
        self._samples[sample.id] = sample

        if auto_approve:
            self._apply_sample(sample)

        self._save()
        logger.debug("Recorded learning observation: %s", category)
        return self._sample_to_dict(sample)

    def observe_batch(self, observations: List[Dict[str, str]],
                      auto_approve: bool = False) -> List[Dict[str, Any]]:
        """Record multiple observations at once."""
        return [
            self.observe(
                category=obs.get("category", "generic"),
                observation=obs.get("observation", ""),
                pattern=obs.get("pattern", ""),
                context=obs.get("context", ""),
                auto_approve=auto_approve,
            )
            for obs in observations
        ]

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def get_pending(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all observations pending user approval."""
        samples = self._samples.values()
        if category:
            try:
                cat = LearningCategory(category)
                samples = [s for s in samples if s.category == cat]
            except ValueError:
                pass
        return [
            self._sample_to_dict(s)
            for s in samples if not s.approved
        ]

    def approve(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """Approve a specific learning observation."""
        sample = self._samples.get(sample_id)
        if not sample:
            return None
        if sample.approved:
            return self._sample_to_dict(sample)

        sample.approved = True
        sample.updated_at = time.time()
        self._apply_sample(sample)
        self._save()
        logger.info("Approved learning: %s", sample.observation[:60])
        return self._sample_to_dict(sample)

    def approve_all(self, category: str = None) -> int:
        """Approve all pending observations, optionally filtered by category."""
        pending = self.get_pending(category)
        count = 0
        for p in pending:
            result = self.approve(p["id"])
            if result:
                count += 1
        return count

    def reject(self, sample_id: str) -> bool:
        """Reject and discard a learning observation."""
        sample = self._samples.pop(sample_id, None)
        if sample:
            self._save()
            logger.info("Rejected learning: %s", sample.observation[:60])
            return True
        return False

    def reject_all(self, category: str = None) -> int:
        """Reject all pending observations, optionally filtered."""
        pending = self.get_pending(category)
        count = 0
        for p in pending:
            if self.reject(p["id"]):
                count += 1
        return count

    # ------------------------------------------------------------------
    # Learned patterns
    # ------------------------------------------------------------------

    def get_learned(self, category: str) -> List[Dict[str, Any]]:
        """Get all learned patterns for a category."""
        try:
            cat = LearningCategory(category)
        except ValueError:
            return []
        return self._learned.get(cat, [])

    def get_all_learned(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all learned patterns organized by category."""
        return {
            cat.value: patterns
            for cat, patterns in self._learned.items()
            if patterns
        }

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of what has been learned."""
        summary = {}
        for cat in LearningCategory:
            patterns = self._learned.get(cat, [])
            pending = len([
                s for s in self._samples.values()
                if s.category == cat and not s.approved
            ])
            summary[cat.value] = {
                "learned_count": len(patterns),
                "pending_count": pending,
            }
        return summary

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_sample(self, sample: LearningSample) -> None:
        """Apply a learned pattern to the knowledge base."""
        if sample.category not in self._learned:
            self._learned[sample.category] = []

        existing = next(
            (p for p in self._learned[sample.category]
             if p["pattern"] == sample.pattern),
            None,
        )
        if existing:
            existing["frequency"] = existing.get("frequency", 1) + 1
            existing["confidence"] = min(existing.get("confidence", 0.5) + 0.1, 0.99)
            existing["updated_at"] = time.time()
        else:
            self._learned[sample.category].append({
                "pattern": sample.pattern,
                "observation": sample.observation,
                "frequency": 1,
                "confidence": sample.confidence,
                "context": sample.context,
                "created_at": sample.created_at,
                "updated_at": time.time(),
            })

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        data = {
            "samples": [
                {
                    "id": s.id,
                    "category": s.category.value,
                    "observation": s.observation,
                    "pattern": s.pattern,
                    "context": s.context,
                    "frequency": s.frequency,
                    "confidence": s.confidence,
                    "approved": s.approved,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                }
                for s in self._samples.values()
            ],
            "learned": {
                cat.value: patterns
                for cat, patterns in self._learned.items()
            },
        }
        path = self._store_path / "learning.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        path = self._store_path / "learning.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for sdata in data.get("samples", []):
                try:
                    sample = LearningSample(
                        id=sdata.get("id", uuid.uuid4().hex[:12]),
                        category=LearningCategory(sdata.get("category", "generic")),
                        observation=sdata.get("observation", ""),
                        pattern=sdata.get("pattern", ""),
                        context=sdata.get("context", ""),
                        frequency=sdata.get("frequency", 1),
                        confidence=sdata.get("confidence", 0.5),
                        approved=sdata.get("approved", False),
                        created_at=sdata.get("created_at", 0.0),
                        updated_at=sdata.get("updated_at", 0.0),
                    )
                    self._samples[sample.id] = sample
                except Exception as exc:
                    logger.warning("Failed to load learning sample: %s", exc)

            for cat_name, patterns in data.get("learned", {}).items():
                try:
                    cat = LearningCategory(cat_name)
                    self._learned[cat] = patterns
                except ValueError:
                    pass
        except Exception as exc:
            logger.warning("Failed to load learning data: %s", exc)

    @staticmethod
    def _sample_to_dict(sample: LearningSample) -> Dict[str, Any]:
        return {
            "id": sample.id,
            "category": sample.category.value,
            "observation": sample.observation,
            "pattern": sample.pattern,
            "context": sample.context,
            "frequency": sample.frequency,
            "confidence": sample.confidence,
            "approved": sample.approved,
            "created_at": sample.created_at,
            "updated_at": sample.updated_at,
        }

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._samples)
        approved = sum(1 for s in self._samples.values() if s.approved)
        pending = total - approved
        return {
            "total_observations": total,
            "approved": approved,
            "pending_approval": pending,
            "categories_learned": len(self._learned),
            "learned_patterns": sum(len(v) for v in self._learned.values()),
        }
