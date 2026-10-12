"""
Consolidation Engine — merges, compresses, and promotes memories.

Handles:
  - Merging duplicate memory entries
  - Compressing large conversation histories
  - Archiving inactive memories
  - Promoting important short-term memories to long-term
  - Periodic consolidation cycles
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.summarizer import Summarizer

logger = logging.getLogger(__name__)


class ConsolidationEngine:
    """Memory consolidation — merging, compressing, promoting.

    Runs consolidation cycles to keep memory efficient and organized.

    Usage:
        engine = ConsolidationEngine(store, summarizer)
        engine.consolidate()  # Run full cycle
        engine.merge_duplicates()
        engine.promote_to_ltm()
    """

    def __init__(self, store: MemoryStore,
                 summarizer: Optional[Summarizer] = None):
        self._store = store
        self._summarizer = summarizer or Summarizer()
        self._lock = threading.RLock()
        self._consolidation_thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._stats = {
            "cycles": 0,
            "duplicates_merged": 0,
            "conversations_compressed": 0,
            "memories_promoted": 0,
            "last_cycle_duration": 0.0,
        }

    # ------------------------------------------------------------------
    # Consolidation cycle
    # ------------------------------------------------------------------

    def consolidate(self) -> Dict[str, Any]:
        """Run a full consolidation cycle.

        Performs:
          1. Merge duplicate entries
          2. Compress large conversations
          3. Promote important STM to LTM
          4. Mark outdated entries
        """
        start = time.time()
        merged = self._merge_duplicates()
        compressed = self._compress_conversations()
        promoted = self._auto_promote()

        duration = time.time() - start
        with self._lock:
            self._stats["cycles"] += 1
            self._stats["duplicates_merged"] += merged
            self._stats["conversations_compressed"] += compressed
            self._stats["memories_promoted"] += promoted
            self._stats["last_cycle_duration"] = duration

        if merged + compressed + promoted > 0:
            logger.info(
                "Consolidation: merged=%d, compressed=%d, promoted=%d in %.2fs",
                merged, compressed, promoted, duration,
            )

        return {
            "duplicates_merged": merged,
            "conversations_compressed": compressed,
            "memories_promoted": promoted,
            "duration_seconds": duration,
        }

    # ------------------------------------------------------------------
    # Duplicate merging
    # ------------------------------------------------------------------

    def _merge_duplicates(self) -> int:
        """Find and merge duplicate memory entries.

        Entries with the same key, scope, and namespace are considered
        duplicates. The older entry is kept, and the newer value is
        merged in if different.
        """
        entries = self._store.search(limit=100000)
        seen: Dict[str, MemoryEntry] = {}
        merged = 0

        for entry in entries:
            dedup_key = f"{entry.key}:{entry.scope.value}:{entry.namespace}"
            existing = seen.get(dedup_key)
            if existing:
                if existing.id != entry.id:
                    # Merge values
                    if (isinstance(existing.value, dict)
                            and isinstance(entry.value, dict)):
                        existing.value.update(entry.value)
                    elif entry.value != existing.value:
                        existing.value = f"{existing.value}\n{entry.value}"

                    existing.updated_at = time.time()
                    existing.metadata["mention_count"] = (
                        existing.metadata.get("mention_count", 1)
                        + entry.metadata.get("mention_count", 1)
                    )
                    existing.importance = max(existing.importance, entry.importance)
                    existing.tags = list(set(existing.tags + entry.tags))

                    # Remove duplicate
                    self._store.delete(entry.id)
                    merged += 1
            else:
                seen[dedup_key] = entry

        return merged

    # ------------------------------------------------------------------
    # Conversation compression
    # ------------------------------------------------------------------

    def _compress_conversations(self) -> int:
        """Compress large conversation entries."""
        entries = self._store.search(
            memory_type="short_term",
            limit=1000,
        )
        compressed = 0

        for entry in entries:
            content = str(entry.value)
            if len(content) > 5000:  # Large entries need compression
                summary = self._summarizer.summarize(content, max_chars=1000)
                self._store.update(
                    entry.id,
                    value=summary,
                    metadata={
                        "compressed": True,
                        "original_length": len(content),
                        "compressed_at": time.time(),
                    },
                )
                compressed += 1

        return compressed

    # ------------------------------------------------------------------
    # STM to LTM promotion
    # ------------------------------------------------------------------

    def _auto_promote(self) -> int:
        """Promote important short-term memories to long-term."""
        entries = self._store.search(
            memory_type="short_term",
            limit=1000,
        )
        promoted = 0

        for entry in entries:
            # Promote high-importance entries
            if (entry.importance >= 0.7
                    and not entry.metadata.get("promoted_to_ltm")):
                # Create a long-term copy
                self._store.save(
                    key=entry.key,
                    value=entry.value,
                    memory_type="long_term",
                    scope=MemoryScope.GLOBAL,
                    namespace=entry.namespace,
                    tags=entry.tags + ["promoted"],
                    metadata={
                        **entry.metadata,
                        "promoted_to_ltm": True,
                        "promoted_at": time.time(),
                        "original_stm_id": entry.id,
                    },
                    importance=entry.importance,
                    source="consolidation",
                )
                # Mark original as promoted
                self._store.update(entry.id, metadata={
                    "promoted_to_ltm": True,
                    "promoted_at": time.time(),
                })
                promoted += 1

        return promoted

    # ------------------------------------------------------------------
    # Manual operations
    # ------------------------------------------------------------------

    def merge_duplicates(self) -> int:
        """Manually trigger duplicate merge. Returns count merged."""
        return self._merge_duplicates()

    def promote_entries(self, entry_ids: List[str]) -> int:
        """Manually promote specific entries to LTM. Returns count."""
        promoted = 0
        for eid in entry_ids:
            entry = self._store.get(eid)
            if entry and entry.memory_type != "long_term":
                self._store.save(
                    key=entry.key,
                    value=entry.value,
                    memory_type="long_term",
                    scope=entry.scope,
                    namespace=entry.namespace,
                    tags=entry.tags + ["manually_promoted"],
                    importance=entry.importance,
                    source="manual",
                )
                promoted += 1
        return promoted

    # ------------------------------------------------------------------
    # Auto-consolidation
    # ------------------------------------------------------------------

    def start_auto(self, interval_minutes: float = 60.0) -> None:
        """Start automatic consolidation on a timer."""
        with self._lock:
            if self._consolidation_thread and self._consolidation_thread.is_alive():
                return
            self._stop_flag = False
            self._consolidation_thread = threading.Thread(
                target=self._auto_loop,
                args=(interval_minutes,),
                daemon=True,
                name="memory-consolidation",
            )
            self._consolidation_thread.start()
            logger.info("Consolidation: auto-consolidation started (interval=%d min)",
                       interval_minutes)

    def stop_auto(self) -> None:
        """Stop automatic consolidation."""
        self._stop_flag = True
        with self._lock:
            if self._consolidation_thread:
                self._consolidation_thread.join(timeout=5)
                self._consolidation_thread = None

    def _auto_loop(self, interval_minutes: float) -> None:
        while not self._stop_flag:
            time.sleep(interval_minutes * 60)
            if not self._stop_flag:
                try:
                    self.consolidate()
                except Exception as exc:
                    logger.error("Consolidation: auto-cycle failed: %s", exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)
