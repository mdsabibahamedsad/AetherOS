"""Memory write pipeline.

A single choke point for every entry entering the fabric:

    validate -> classify -> defense (poison/injection/secret) -> dedup ->
    conflict-check -> version -> seal -> persist -> audit

The pipeline returns a ``WriteOutcome`` describing exactly what happened
(accepted / deduplicated / blocked / quarantined / conflict-flagged) so
callers and the audit log can reason about it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_memory_intelligence.boundaries import AccessContext, MemoryBoundaries
from aetheros_memory_intelligence.dedup import DedupEngine
from aetheros_memory_intelligence.defense import (
    DefenseResult,
    DefenseVerdict,
    InjectionDefense,
    classify_content_type,
)
from aetheros_memory_intelligence.provenance import ProvenanceRecord
from aetheros_memory_intelligence.retention import RetentionManager
from aetheros_memory_intelligence.schema import MemoryEntry, validate_entry
from aetheros_memory_intelligence.store import MemoryStore
from aetheros_memory_intelligence.types import MemoryOrigin, MemoryState, MemoryType
from aetheros_memory_intelligence.versioning import ConflictDetector, VersionHistory


@dataclass
class WriteOutcome:
    """Result of a write-pipeline run."""

    action: str = "accepted"   # accepted | deduplicated | consolidated | blocked | quarantined | conflict
    entry: Optional[MemoryEntry] = None
    deduplicated: bool = False
    duplicate_of: str = ""
    blocked_reasons: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    quarantine_reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.action == "accepted"


class WritePipeline:
    """Orchestrates the write path.  All gates are overridable for tests."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        boundaries: Optional[MemoryBoundaries] = None,
        defense: Optional[InjectionDefense] = None,
        dedup: Optional[DedupEngine] = None,
        conflicts: Optional[ConflictDetector] = None,
        versions: Optional[VersionHistory] = None,
        retention: Optional[RetentionManager] = None,
        enabled_flags: Optional[Dict[str, bool]] = None,
        provenance_factory: Optional[Callable[[MemoryEntry], ProvenanceRecord]] = None,
    ) -> None:
        self._store = store
        self._boundaries = boundaries or MemoryBoundaries()
        self._defense = defense or InjectionDefense()
        self._dedup = dedup or DedupEngine()
        self._conflicts = conflicts or ConflictDetector()
        self._versions = versions or VersionHistory()
        self._retention = retention or RetentionManager()
        self._flags = enabled_flags or {}
        self._provenance_factory = provenance_factory

    def _flag(self, name: str) -> bool:
        # Individual flags default to enabled unless explicitly disabled.
        return self._flags.get(name, True)

    def process(
        self,
        entry: MemoryEntry,
        actor: AccessContext,
        *,
        provenance: Optional[ProvenanceRecord] = None,
        auto_classify: bool = True,
    ) -> WriteOutcome:
        # 1. Validate schema.
        problems = validate_entry(entry)
        if problems:
            return WriteOutcome(action="blocked", entry=entry, blocked_reasons=problems)

        # 2. Boundary authorization.
        try:
            self._boundaries.enforce_write(entry, actor)
        except PermissionError as exc:
            return WriteOutcome(action="blocked", entry=entry, blocked_reasons=[str(exc)])

        # 3. Auto-classify content type if caller didn't set a meaningful type.
        if auto_classify and entry.memory_type == MemoryType.SEMANTIC and not entry.summary:
            ctype = classify_content_type(entry.content)
            if ctype == "instruction":
                entry.memory_type = MemoryType.PROCEDURAL
            elif ctype == "opinion":
                entry.metadata.setdefault("content_class", "opinion")
                entry.confidence = min(entry.confidence, 0.5) if entry.confidence else 0.3

        # 4. Poison / injection / secret defense.
        if self._flag("poison_defense_enabled") or self._flag("secret_scan_enabled"):
            defense = self._defense.inspect(
                entry.content,
                origin=entry.origin.value,
            )
            if defense.verdict == DefenseVerdict.BLOCKED:
                return WriteOutcome(
                    action="blocked", entry=entry,
                    blocked_reasons=[f"defense: {'; '.join(defense.reasons)}"],
                )
            if defense.verdict == DefenseVerdict.SUSPICIOUS:
                # Quarantine suspicious external content; keep it out of the
                # live retrieval index by marking the state and preserving the
                # reasons (the entry is still persisted, but flagged).
                entry.state = MemoryState.QUARANTINED
                if defense.sanitized_content != entry.content:
                    entry.content = defense.sanitized_content
                entry.metadata["defense_reasons"] = defense.reasons
                entry.metadata["defense_rules"] = defense.triggered_rules
                quarantine_reason = "; ".join(defense.reasons)

        # 5. Dedup against existing entries.
        existing = self._store.all()
        if self._flag("dedup_enabled"):
            exact = self._dedup.find_exact(existing, entry.content)
            if exact is not None:
                if entry.trust > exact.trust:
                    # Keep the higher-trust copy: consolidate.
                    winner = self._dedup.consolidate(entry, exact)
                    self._store.save(winner)
                    self._store.delete(exact.id)
                    return WriteOutcome(action="consolidated", entry=winner)
                return WriteOutcome(action="deduplicated", entry=entry, duplicate_of=exact.id)
            near = self._dedup.find_near(existing, entry.content)
            if near is not None:
                winner = self._dedup.consolidate(near, entry)
                self._store.save(winner)
                return WriteOutcome(action="consolidated", entry=winner)

        # 6. Conflict detection (same semantic key, divergent content).
        conflicts = self._conflicts.find_conflicts(existing + [entry])
        entry_conflicts = [c for c in conflicts if c.entry_a == entry.id or c.entry_b == entry.id]

        # 7. Versioning.
        if self._flag("versioning_enabled") and entry.id in {e.id for e in existing}:
            prev = next(e for e in existing if e.id == entry.id)
            if prev.content != entry.content:
                entry.bump_version()

        # 7b. Attach provenance BEFORE sealing so the checksum covers it.
        if provenance is not None:
            entry.metadata["provenance"] = provenance.to_dict()

        # 8. Seal + persist.
        entry.seal()
        self._store.save(entry)
        if self._flag("versioning_enabled"):
            self._versions.record(entry, actor=actor.user_id or actor.agent_id)

        if entry.state == MemoryState.QUARANTINED:
            return WriteOutcome(
                action="quarantined",
                entry=entry,
                quarantine_reason=quarantine_reason,
            )
        if entry_conflicts:
            return WriteOutcome(
                action="conflict",
                entry=entry,
                conflicts=[c.reason for c in entry_conflicts],
            )
        return WriteOutcome(action="accepted", entry=entry)