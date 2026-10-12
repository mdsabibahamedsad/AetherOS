"""
Semantic Memory — stores and retrieves structured factual knowledge.

Semantic memory holds facts, concepts, and general knowledge extracted
from conversations and workflows. Unlike episodic memory (which stores
experiences), semantic memory stores the distilled facts and knowledge
that can be referenced independently of when/how they were learned.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.memory_constants import ConfidenceLevel, PrivacyLevel, ProvenanceSource, DEFAULT_CONFIDENCE_LEVEL, DEFAULT_PRIVACY_LEVEL

logger = logging.getLogger(__name__)


@dataclass
class Fact:
    """A factual statement stored in semantic memory.

    Attributes:
        id: Unique fact ID
        subject: The subject of the fact
        predicate: The relationship/predicate
        object: The object of the fact
        confidence: How confident we are (0.0 - 1.0)
        source: Where this fact came from
        tags: Categorization tags
        created_at: When the fact was learned
        updated_at: When the fact was last updated
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.8
    source: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticMemory:
    """Stores and retrieves structured factual knowledge.

    Facts are stored as (subject, predicate, object) triples with
    confidence scores. Supports exact and fuzzy retrieval.

    Usage:
        sem = SemanticMemory(store)
        sem.learn("Python", "is_a", "programming language")
        results = sem.query("Python", "is_a")
        facts = sem.search("programming")
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"semantic:{id(self)}"
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Learning facts
    # ------------------------------------------------------------------

    def learn(self, subject: str, predicate: str, object: str,
    def learn(self, subject: str, predicate: str, object: str,
              confidence: float = 0.8, source: str = "",
              tags: List[str] = None) -> Fact:
        """Learn a new fact or update existing fact confidence. 
        
        Creates a new fact or updates an existing one with the same 
        subject-predicate-object combination by averaging confidence. 
        """
        fact = Fact(
            subject=subject, predicate=predicate, object=object,
            confidence=confidence, source=source, tags=tags or [],
        )

        # Check for existing fact
        existing = self._find_exact(subject, predicate, object)
        if existing:
            # Update confidence with decay/averaging
            fact.id = existing.id
            fact.created_at = existing.created_at
            fact.confidence = max(existing.confidence, confidence)
            fact.tags = list(set(existing.tags + fact.tags))

        self._store.save(
            key=f"fact:{fact.id}",
            value=fact,
            memory_type="semantic",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=fact.tags + [predicate, "fact"],
            metadata={
                "subject": subject,
                "predicate": predicate,
                "object": object[:100],
                "confidence": fact.confidence,
            },
            importance=min(confidence + 0.1, 1.0),
            confidence_level=ConfidenceLevel.from_float(fact.confidence),
            privacy_level=DEFAULT_PRIVACY_LEVEL,
            provenance_source=ProvenanceSource.SEMANTIC,
            provenance_agent="semantic",
            importance_override=None,
        )
        return fact
    def learn_batch(self, facts: List[Fact]) -> int:
        """Learn multiple facts at once. Returns count learned."""
        count = 0
        for fact in facts:
            self.learn(fact.subject, fact.predicate, fact.object,
                      confidence=fact.confidence, source=fact.source,
                      tags=fact.tags)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query(self, subject: str, predicate: str = "",
              min_confidence: float = 0.3) -> List[Fact]:
        """Query facts by subject and optionally predicate.

        Args:
            subject: The subject to query
            predicate: Optional predicate filter
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching Fact objects
        """
        facts = self._extract_facts(self._store.search(
            query=subject,
            memory_type="semantic",
            namespace=self._namespace,
            limit=100,
        ))

        results = []
        for fact in facts:
            if fact.subject != subject:
                continue
            if predicate and fact.predicate != predicate:
                continue
            if fact.confidence < min_confidence:
                continue
            results.append(fact)

        results.sort(key=lambda f: f.confidence, reverse=True)
        return results

    def query_object(self, predicate: str, object: str,
                     min_confidence: float = 0.3) -> List[Fact]:
        """Query facts by predicate and object (reverse lookup)."""
        entries = self._store.search(
            query=object,
            memory_type="semantic",
            namespace=self._namespace,
            limit=100,
        )
        facts = []
        for e in entries:
            fact = e.value
            if isinstance(fact, Fact):
                if fact.predicate == predicate and fact.object == object:
                    if fact.confidence >= min_confidence:
                        facts.append(fact)
        return facts

    def search(self, query: str, limit: int = 20) -> List[Fact]:
        """Search for facts by text in subject, predicate, or object."""
        entries = self._store.search(
            query=query, memory_type="semantic",
            namespace=self._namespace, limit=limit,
        )
        return self._extract_facts(entries)

    def get_all_facts(self, limit: int = 1000) -> List[Fact]:
        """Get all facts in semantic memory."""
        entries = self._store.search(
            memory_type="semantic", namespace=self._namespace, limit=limit,
        )
        return self._extract_facts(entries)

    def get_subjects(self) -> Set[str]:
        """Get all unique subjects in semantic memory."""
        facts = self.get_all_facts(limit=10000)
        return {f.subject for f in facts}

    def get_predicates(self) -> Set[str]:
        """Get all unique predicates in semantic memory."""
        facts = self.get_all_facts(limit=10000)
        return {f.predicate for f in facts}

    # ------------------------------------------------------------------
    # Confidence management
    # ------------------------------------------------------------------

    def increase_confidence(self, subject: str, predicate: str,
                            object: str, amount: float = 0.1) -> bool:
        """Increase confidence in a fact."""
        fact = self._find_exact(subject, predicate, object)
        if fact:
            new_confidence = min(fact.confidence + amount, 1.0)
            fact.confidence = new_confidence
            fact.updated_at = time.time()
            self._store.update(
                fact.id, importance=new_confidence,
                metadata={"confidence": new_confidence},
            )
            return True
        return False

    def decrease_confidence(self, subject: str, predicate: str,
                            object: str, amount: float = 0.3) -> bool:
        """Decrease confidence in a fact (correction signal)."""
        fact = self._find_exact(subject, predicate, object)
        if fact:
            fact.confidence = max(fact.confidence - amount, 0.0)
            fact.updated_at = time.time()
            self._store.update(fact.id, importance=fact.confidence)
            return True
        return False

    def forget_subject(self, subject: str) -> int:
        """Forget all facts about a subject. Returns count removed."""
        facts = self.query(subject)
        count = 0
        for fact in facts:
            self._store.delete_by_key(
                f"fact:{fact.id}",
                scope=MemoryScope.GLOBAL, namespace=self._namespace,
            )
            count += 1
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_exact(self, subject: str, predicate: str,
                    object: str) -> Optional[Fact]:
        """Find an exact subject-predicate-object match."""
        facts = self.get_all_facts(limit=10000)
        for fact in facts:
            if (fact.subject == subject and fact.predicate == predicate
                    and fact.object == object):
                return fact
        return None

    @staticmethod
    def _extract_facts(entries: List[MemoryEntry]) -> List[Fact]:
        """Extract Fact objects from memory entries."""
        facts = []
        for e in entries:
            if isinstance(e.value, Fact):
                facts.append(e.value)
        return facts

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        """Clear all semantic memory. Returns count removed."""
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        """Count stored facts."""
        return self._store.count(namespace=self._namespace)

    def stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics."""
        facts = self.get_all_facts(limit=10000)
        return {
            "total_facts": len(facts),
            "avg_confidence": (
                sum(f.confidence for f in facts) / len(facts) if facts else 0.0
            ),
            "unique_subjects": len(self.get_subjects()),
            "unique_predicates": len(self.get_predicates()),
        }
