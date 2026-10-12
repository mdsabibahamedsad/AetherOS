"""Memory lifecycle: classification, promotion, TTL/decay, conflicts,
dedup/merge, consolidation, correction and stale detection (P17-18, P21,
P24-26, P48-55)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent.memory_os.models import (
    CONFIDENCE_ORDER,
    DECAY_EXEMPT_TYPES,
    MemoryItem,
    MemoryStatus,
    MemoryType,
    FeedbackKind,
)


@dataclass
class PromotionDecision:
    approved: bool
    reason: str
    item: Optional[MemoryItem] = None


class Lifecycle:
    def __init__(self, store):
        self._store = store

    # -- promotion (P18) ---------------------------------------------------------

    def promote(
        self,
        item: MemoryItem,
        *,
        to_scope: str = "user",
        approver_confirmed: bool = False,
    ) -> PromotionDecision:
        """conversation → working → episodic → candidate → approved.

        Automatic promotion stops at CANDIDATE unless a human explicitly
        confirmed (P18/P20). Session-scope items never auto-promote (P16).
        """
        if item.scope.value == "session":
            return PromotionDecision(False, "session memory never promotes automatically")
        if item.status == MemoryStatus.CANDIDATE:
            if not approver_confirmed:
                return PromotionDecision(
                    False, "candidate requires explicit user approval", item
                )
            item.status = MemoryStatus.ACTIVE
            item.scope = type(item.scope)(to_scope)
            item.updated_at = time.time()
            self._store.upsert_item(item, actor="lifecycle", note="approved")
            return PromotionDecision(True, "approved by user", item)
        if item.status == MemoryStatus.ACTIVE:
            return PromotionDecision(True, "already active", item)
        return PromotionDecision(False, f"status {item.status.value} not promotable", item)

    # -- conflicts / supersede (P25) ----------------------------------------------

    def detect_conflict(self, item: MemoryItem) -> Optional[MemoryItem]:
        """Same semantic_key + different content hash among ACTIVE items."""
        if not item.semantic_key:
            return None
        for other in self._store.query_items(semantic_key=item.semantic_key):
            if other.memory_id == item.memory_id:
                continue
            if other.status != MemoryStatus.ACTIVE:
                continue
            if other.content_hash != item.content_hash:
                return other
        return None

    def supersede(self, old: MemoryItem, new: MemoryItem) -> MemoryItem:
        old.status = MemoryStatus.SUPERSEDED
        old.updated_at = time.time()
        new.valid_from = new.valid_from or time.time()
        if old.valid_until is None:
            old.valid_until = new.valid_from  # P28: historical validity retained
        self._store.upsert_item(old, actor="lifecycle", note="superseded")
        return new

    # -- dedup / merge (P48) --------------------------------------------------------

    def find_duplicate(self, item: MemoryItem) -> Optional[MemoryItem]:
        for other in self._store.query_items(types=[item.type.value]):
            if other.memory_id == item.memory_id:
                continue
            if other.status != MemoryStatus.ACTIVE:
                continue
            if other.content_hash == item.content_hash:
                return other
            if item.summary and other.summary and item.summary == other.summary \
                    and other.semantic_key == item.semantic_key and item.semantic_key:
                return other
        return None

    def merge_into(self, dup_source: MemoryItem, keep: MemoryItem) -> MemoryItem:
        """Merge only when same meaning/entity and compatible provenance (P48)."""
        keep.importance = min(1.0, max(keep.importance, dup_source.importance))
        keep.provenance.evidence_ids.extend(dup_source.provenance.evidence_ids)
        keep.metadata.setdefault("merged_from", []).append(dup_source.memory_id)
        dup_source.status = MemoryStatus.MERGED
        dup_source.updated_at = time.time()
        self._store.upsert_item(dup_source, actor="lifecycle", note="merged")
        self._store.upsert_item(keep, actor="lifecycle", note="merge-target")
        return keep

    # -- expiry / decay / gc (P21, P50) ------------------------------------------------

    def expire_sweep(self, now: Optional[float] = None) -> List[str]:
        now = now or time.time()
        expired: List[str] = []
        for item in self._store.query_items(statuses=[MemoryStatus.ACTIVE], limit=10000):
            if item.is_expired(now) or not item.temporally_valid(now):
                item.status = MemoryStatus.EXPIRED
                item.updated_at = now
                self._store.upsert_item(item, actor="gc", note="expired")
                expired.append(item.memory_id)
        return expired

    def purge_expired(self) -> int:
        return self._store.purge_status(MemoryStatus.EXPIRED)

    def decay_candidates(self, *, min_importance: float = 0.35,
                         idle_days: float = 30.0,
                         now: Optional[float] = None) -> List[MemoryItem]:
        """Low-value temporary memories eligible for archival (P50).

        Never decays explicit preferences, procedures/workflows/system items.
        """
        now = now or time.time()
        out: List[MemoryItem] = []
        for item in self._store.query_items(statuses=[MemoryStatus.ACTIVE], limit=10000):
            if item.type in DECAY_EXEMPT_TYPES:
                continue
            if item.preference_kind.value == "explicit":
                continue
            idle = (now - max(item.last_accessed_at, item.created_at)) / 86400.0
            if idle >= idle_days and item.importance < min_importance:
                out.append(item)
        return out

    def archive(self, item: MemoryItem) -> MemoryItem:
        item.status = MemoryStatus.ARCHIVED
        item.updated_at = time.time()
        self._store.upsert_item(item, actor="gc", note="archived")
        return item

    def restore(self, item: MemoryItem) -> MemoryItem:
        if item.status in (MemoryStatus.ARCHIVED, MemoryStatus.EXPIRED):
            item.status = MemoryStatus.ACTIVE
            item.expires_at = None
            item.updated_at = time.time()
            self._store.upsert_item(item, actor="gc", note="restored")
        return item

    # -- feedback / correction (P52-53) ---------------------------------------------------

    def apply_feedback(self, item: MemoryItem, kind: FeedbackKind) -> MemoryItem:
        if kind is FeedbackKind.USEFUL:
            item.importance = min(1.0, item.importance + 0.1)
            item.revalidate_after = None
        elif kind is FeedbackKind.INCORRECT:
            item.status = MemoryStatus.SUPERSEDED
            below = [
                c for c, v in CONFIDENCE_ORDER.items()
                if v < CONFIDENCE_ORDER[item.confidence]
            ]
            item.confidence = max(below, key=lambda c: CONFIDENCE_ORDER[c]) if below \
                else item.confidence
        elif kind is FeedbackKind.OUTDATED:
            item.needs_revalidation_marker = True  # advisory only
            item.revalidate_after = time.time() - 1
        elif kind is FeedbackKind.IRRELEVANT:
            item.importance = max(0.0, item.importance - 0.2)
        elif kind is FeedbackKind.PRIVATE:
            from agent.memory_os.models import Sensitivity
            item.sensitivity = Sensitivity.SENSITIVE
        item.updated_at = time.time()
        self._store.upsert_item(item, actor="user-feedback", note=kind.value)
        return item

    def invalidate_derived(self, root_id: str, derived_ids: List[str]) -> int:
        """P53 — corrections cascade into derived memories."""
        n = 0
        for did in derived_ids:
            d = self._store.get_item(did)
            if d and d.status == MemoryStatus.ACTIVE:
                d.status = MemoryStatus.SUPERSEDED
                d.updated_at = time.time()
                self._store.upsert_item(d, actor="correction", note=f"derived-of-{root_id}")
                n += 1
        return n

    # -- stale detection / revalidation (P54-55) ---------------------------------------------

    def stale_candidates(self, *, now: Optional[float] = None,
                         volatile_age_days: float = 60.0) -> List[MemoryItem]:
        now = now or time.time()
        out = []
        for item in self._store.query_items(statuses=[MemoryStatus.ACTIVE], limit=10000):
            if item.needs_revalidation(now):
                out.append(item)
                continue
            if item.type in ({MemoryType.TEMPORAL, MemoryType.RESEARCH}):
                age = (now - item.updated_at) / 86400.0
                if age > volatile_age_days:
                    out.append(item)
        return out

    def mark_revalidated(self, item: MemoryItem, ok: bool) -> MemoryItem:
        if ok:
            item.revalidate_after = time.time() + 30 * 86400
            item.updated_at = time.time()
        else:
            item.status = MemoryStatus.SUPERSEDED
            item.updated_at = time.time()
        self._store.upsert_item(item, actor="revalidation", note=str(ok))
        return item

    # -- consolidation (P49) -------------------------------------------------------------

    def consolidate(self, *, min_events: int = 3,
                    now: Optional[float] = None) -> List[MemoryItem]:
        """Fold repeated EPISODIC events about one semantic_key into one durable
        SEMANTIC memory while retaining provenance of every source event."""
        now = now or time.time()
        produced: List[MemoryItem] = []
        buckets: Dict[str, List[MemoryItem]] = {}
        for it in self._store.query_items(types=["episodic"], limit=10000):
            if it.status != MemoryStatus.ACTIVE or not it.semantic_key:
                continue
            buckets.setdefault(it.semantic_key, []).append(it)
        for key, events in buckets.items():
            if len(events) < min_events:
                continue
            sources = sorted(events, key=lambda e: e.created_at)
            content = (
                f"Consolidated from {len(sources)} episodes: "
                + " | ".join(e.summary or e.content[:80] for e in sources[-5:])
            )
            merged = MemoryItem(
                type=MemoryType.SEMANTIC,
                content=content,
                summary=f"consolidated:{key}",
                source_type=sources[-1].source_type,
                scope=sources[-1].scope,
                owner=sources[-1].owner,
                project_id=sources[-1].project_id,
                confidence=max((e.confidence for e in sources), key=lambda c: CONFIDENCE_ORDER[c]),
                importance=min(1.0, max(e.importance for e in sources) + 0.1),
                status=MemoryStatus.CANDIDATE,   # still needs approval (P18)
                semantic_key=key,
                created_at=now,
                updated_at=now,
            )
            merged.provenance.origin_event = "consolidation"
            merged.provenance.evidence_ids = [e.memory_id for e in sources]
            self._store.upsert_item(merged, actor="consolidation", note=key)
            produced.append(merged)
        return produced
