"""Dedup & consolidation for the write path.

Exact-content dedup (SHA-256) prevents identical re-writes; near-duplicate
detection (token Jaccard) consolidates near-identical entries into a single
entry that preserves the best provenance/trust.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aetheros_memory_intelligence.schema import MemoryEntry


@dataclass
class DedupResult:
    deduplicated: bool = False
    duplicate_of: str = ""           # id of the kept entry
    consolidated: bool = False
    winner: Optional[MemoryEntry] = None
    losers: List[str] = field(default_factory=list)


def content_fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class DedupEngine:
    """Exact + near-duplicate detection over a set of existing entries."""

    def __init__(self, *, enabled: bool = True, near_threshold: float = 0.92) -> None:
        self.enabled = enabled
        self.near_threshold = near_threshold

    def _jaccard(self, a: str, b: str) -> float:
        ta = set(a.lower().split())
        tb = set(b.lower().split())
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)

    def find_exact(self, entries: List[MemoryEntry], content: str) -> Optional[MemoryEntry]:
        if not self.enabled:
            return None
        fp = content_fingerprint(content)
        for entry in entries:
            if entry.content and content_fingerprint(entry.content) == fp:
                return entry
        return None

    def find_near(self, entries: List[MemoryEntry], content: str, *, max_scan: int = 200) -> Optional[MemoryEntry]:
        if not self.enabled:
            return None
        best: Optional[MemoryEntry] = None
        best_score = 0.0
        for entry in entries[:max_scan]:
            score = self._jaccard(entry.content, content)
            if score > best_score:
                best_score = score
                best = entry
        if best and best_score >= self.near_threshold:
            return best
        return None

    def consolidate(self, keep: MemoryEntry, drop: MemoryEntry) -> MemoryEntry:
        """Merge ``drop`` into ``keep``, keeping the best provenance/trust.

        Returns the consolidated entry (caller persists it).
        """
        keep.content = keep.content or drop.content
        keep.summary = keep.summary or drop.summary
        keep.tags = list(dict.fromkeys(keep.tags + drop.tags))
        keep.trust = max(keep.trust, drop.trust)
        keep.confidence = max(keep.confidence, drop.confidence)
        if drop.verification != "unverified":
            keep.verification = drop.verification
        for src in drop.corroborated_by:
            if src not in keep.corroborated_by:
                keep.corroborated_by.append(src)
        keep.metadata.setdefault("consolidated_from", []).append(drop.id)
        keep.bump_version()
        return keep