"""Retention, forgetting & consolidation policy for the fabric.

Retention is *policy*, not magic: each memory type has a default TTL and a
decay model; stale low-trust entries are archived (not silently destroyed)
and eventually purged.  Pinned/high-importance entries are exempt.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.types import MemoryState, MemoryType

# Per-type default TTLs (seconds).  0 = no expiry.
_DEFAULT_TTLS: Dict[MemoryType, float] = {
    MemoryType.TEMPORARY: 86400.0,          # 1 day
    MemoryType.SESSION: 604800.0,           # 7 days
    MemoryType.MISSION: 0.0,                # no expiry
    MemoryType.PREFERENCE: 0.0,
    MemoryType.WORKSPACE: 0.0,
    MemoryType.AGENT: 0.0,
    MemoryType.SYSTEM: 0.0,
    MemoryType.EPISODIC: 30 * 86400.0,      # 30 days
    MemoryType.SEMANTIC: 0.0,
    MemoryType.PROCEDURAL: 0.0,
    MemoryType.DOCUMENT: 0.0,
}


@dataclass
class RetentionPolicy:
    """Policy knobs controlling retention/forgetting."""

    enabled: bool = True
    default_ttls: Dict[str, float] = None   # keyed by MemoryType.value
    # An entry whose trust decays below this is eligible for archival.
    archive_below_trust: float = 0.25
    # Archival is permanent if trust stays below this after N days idle.
    purge_below_trust: float = 0.15
    idle_purge_days: float = 365.0
    # Pinned or importance>=threshold entries are never auto-archived.
    protect_importance: float = 0.8

    def __post_init__(self) -> None:
        default_ttls = {t.value: v for t, v in _DEFAULT_TTLS.items()}
        if self.default_ttls is None:
            self.default_ttls = default_ttls
        else:
            # Merge custom TTLS with defaults, preferring custom values
            self.default_ttls = {**default_ttls, **self.default_ttls}

    def ttl_for(self, entry: MemoryEntry) -> float:
        if entry.ttl > 0:
            return entry.ttl
        return self.default_ttls.get(entry.memory_type.value, 0.0)


class RetentionManager:
    """Applies TTL expiry, archival, and purge decisions."""

    def __init__(self, policy: Optional[RetentionPolicy] = None) -> None:
        self._policy = policy or RetentionPolicy()

    @property
    def policy(self) -> RetentionPolicy:
        return self._policy

    def is_expired(self, entry: MemoryEntry) -> bool:
        if not self._policy.enabled:
            return False
        if entry.state in (MemoryState.FORGOTTEN, MemoryState.QUARANTINED):
            return False
        ttl = self._policy.ttl_for(entry)
        if ttl <= 0:
            return False
        return (time.time() - entry.updated_at) > ttl

    def should_archive(self, entry: MemoryEntry, trust: float) -> bool:
        if not self._policy.enabled:
            return False
        if entry.state != MemoryState.ACTIVE:
            return False
        if entry.metadata.get("pinned"):
            return False
        if entry.metadata.get("importance", 0.0) >= self._policy.protect_importance:
            return False
        return trust < self._policy.archive_below_trust

    def should_purge(self, entry: MemoryEntry, trust: float) -> bool:
        if not self._policy.enabled:
            return False
        if entry.metadata.get("pinned"):
            return False
        if entry.metadata.get("importance", 0.0) >= self._policy.protect_importance:
            return False
        idle_days = (time.time() - entry.updated_at) / 86400.0
        return trust < self._policy.purge_below_trust and idle_days > self._policy.idle_purge_days

    def apply(self, entries: List[MemoryEntry], trust_fn) -> Tuple[List[MemoryEntry], List[MemoryEntry]]:
        """Split entries into (keep, forget).  Archive-eligible -> state=ARCHIVED."""
        keep: List[MemoryEntry] = []
        forget: List[MemoryEntry] = []
        for entry in entries:
            trust = trust_fn(entry)
            if self.is_expired(entry) or self.should_purge(entry, trust):
                forget.append(entry)
            elif self.should_archive(entry, trust):
                entry.state = MemoryState.ARCHIVED
                keep.append(entry)
            else:
                keep.append(entry)
        return keep, forget