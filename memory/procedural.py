"""
Procedural Memory — stores procedures, strategies, and how-to knowledge.

Procedural memory captures successful strategies, workflows, and procedures
that have been learned through experience. It enables the system to
remember *how* to do things — not just facts (semantic) or experiences
(episodic), but the procedures themselves.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.memory_constants import ConfidenceLevel, PrivacyLevel, ProvenanceSource, DEFAULT_CONFIDENCE_LEVEL, DEFAULT_PRIVACY_LEVEL

logger = logging.getLogger(__name__)


@dataclass
class Procedure:
    """A learned procedure or strategy.

    Attributes:
        id: Unique procedure ID
        name: Procedure name
        description: What this procedure does
        steps: Ordered list of steps
        context: When to use this procedure
        prerequisites: What's needed before running
        expected_outcome: What should happen
        success_rate: How often it succeeds (0.0 - 1.0)
        execution_count: How many times it's been used
        tags: Categorization tags
        created_at: When the procedure was learned
        updated_at: When it was last updated
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    description: str = ""
    steps: List[str] = field(default_factory=list)
    context: str = ""
    prerequisites: str = ""
    expected_outcome: str = ""
    success_rate: float = 0.5
    execution_count: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProceduralMemory:
    """Stores learned procedures and strategies.

    Procedures can be recorded by reflection after successful workflows
    or explicitly taught. They are retrieved by context matching and
    ranked by success rate.

    Usage:
        proc = ProceduralMemory(store)
        proc.record(Procedure(
            name="Fix Python import errors",
            steps=["Check sys.path", "Verify package installed"],
            context="When Python says ModuleNotFoundError",
            success_rate=0.9,
        ))
        procs = proc.find_by_context("ModuleNotFoundError")
    """

    def __init__(self, store: MemoryStore, namespace: str = ""):
        self._store = store
        self._namespace = namespace or f"procedural:{id(self)}"

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, procedure: Procedure) -> MemoryEntry:
    def record(self, procedure: Procedure) -> MemoryEntry:
        """Record a procedure in memory."""
        procedure.updated_at = time.time()
        return self._store.save(
            key=f"procedure:{procedure.id}",
            value=procedure,
            memory_type="procedural",
            scope=MemoryScope.GLOBAL,
            namespace=self._namespace,
            tags=procedure.tags + ["procedure"],
            metadata={
                "name": procedure.name,
                "description": procedure.description[:200],
                "success_rate": procedure.success_rate,
                "execution_count": procedure.execution_count,
                "step_count": len(procedure.steps),
            },
            importance=procedure.success_rate,
            confidence_level=ConfidenceLevel.from_float(procedure.success_rate),
            privacy_level=DEFAULT_PRIVACY_LEVEL,
            provenance_source=ProvenanceSource.PROCEDURAL,
            provenance_agent="procedural",
            importance_override=None,
        )
    def record_from_reflection(self, name: str, description: str,
                               steps: List[str], context: str,
                               success: bool = True) -> Procedure:
        """Record a procedure learned through reflection."""
        procedure = Procedure(
            name=name, description=description, steps=steps,
            context=context, success_rate=0.7 if success else 0.3,
            tags=["reflection"],
        )
        self.record(procedure)
        return procedure

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def find_by_context(self, context: str, limit: int = 10) -> List[Procedure]:
        """Find procedures relevant to a given context."""
        entries = self._store.search(
            query=context,
            memory_type="procedural",
            namespace=self._namespace,
            limit=limit,
        )
        return self._extract_procedures(entries)

    def find_by_name(self, name: str) -> Optional[Procedure]:
        """Find a procedure by its exact name."""
        entries = self._store.search(
            query=name, memory_type="procedural",
            namespace=self._namespace, limit=10,
        )
        for e in entries:
            proc = e.value
            if isinstance(proc, Procedure) and proc.name.lower() == name.lower():
                return proc
        return None

    def get_best(self, limit: int = 10) -> List[Procedure]:
        """Get the highest-success-rate procedures."""
        entries = self._store.search(
            memory_type="procedural",
            namespace=self._namespace,
            limit=100,
        )
        procs = self._extract_procedures(entries)
        procs.sort(key=lambda p: (p.success_rate, p.execution_count), reverse=True)
        return procs[:limit]

    def get_by_tag(self, tag: str, limit: int = 20) -> List[Procedure]:
        """Get procedures by tag."""
        entries = self._store.search(
            tags=[tag], memory_type="procedural",
            namespace=self._namespace, limit=limit,
        )
        return self._extract_procedures(entries)

    def list_all(self, limit: int = 100) -> List[Procedure]:
        """List all procedures."""
        entries = self._store.search(
            memory_type="procedural", namespace=self._namespace, limit=limit,
        )
        return self._extract_procedures(entries)

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def record_success(self, procedure_id: str) -> bool:
        """Record a successful execution of a procedure."""
        entry = self._store.get_by_key(
            f"procedure:{procedure_id}",
            scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        if entry and isinstance(entry.value, Procedure):
            proc = entry.value
            proc.execution_count += 1
            # Update success rate with moving average
            prev_avg = proc.success_rate * (proc.execution_count - 1)
            proc.success_rate = (prev_avg + 1.0) / proc.execution_count
            return self._store.update(entry.id, importance=proc.success_rate,
                                     metadata={"success_rate": proc.success_rate})
        return False

    def record_failure(self, procedure_id: str) -> bool:
        """Record a failed execution of a procedure."""
        entry = self._store.get_by_key(
            f"procedure:{procedure_id}",
            scope=MemoryScope.GLOBAL, namespace=self._namespace,
        )
        if entry and isinstance(entry.value, Procedure):
            proc = entry.value
            proc.execution_count += 1
            prev_avg = proc.success_rate * (proc.execution_count - 1)
            proc.success_rate = prev_avg / proc.execution_count
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_procedures(entries: List[MemoryEntry]) -> List[Procedure]:
        procs = []
        for e in entries:
            if isinstance(e.value, Procedure):
                procs.append(e.value)
        return procs

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> int:
        return self._store.clear_namespace(self._namespace)

    def count(self) -> int:
        return self._store.count(namespace=self._namespace)
