"""
Garbage Collector — periodic memory cleanup and compaction.

Handles:
  - Removing expired entries
  - Applying retention policies
  - Compacting storage
  - Archiving inactive memories
  - Reporting storage statistics
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.retention import RetentionEngine, RetentionAction

logger = logging.getLogger(__name__)


class GarbageCollector:
    """Periodic memory cleanup and maintenance.

    Runs retention policies, removes expired entries, compacts storage,
    and collects statistics.

    Usage:
        gc = GarbageCollector(store, retention_engine)
        gc.run()
        gc.start_auto(interval_minutes=30)
        gc.stop_auto()
    """

    def __init__(self, store: MemoryStore,
                 retention_engine: Optional[RetentionEngine] = None):
        self._store = store
        self._retention = retention_engine or RetentionEngine()
        self._lock = threading.RLock()
        self._gc_thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._stats = {
            "runs": 0,
            "entries_removed": 0,
            "entries_archived": 0,
            "entries_promoted": 0,
            "last_run_duration": 0.0,
        }
        self._promote_callback: Optional[Callable[[MemoryEntry], None]] = None

    # ------------------------------------------------------------------
    # GC execution
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute one garbage collection cycle.

        Iterates through all memory entries, evaluates retention policies,
        and takes configured actions (delete, archive, promote).
        """
        start = time.time()
        removed = 0
        archived = 0
        promoted = 0

        # Get all entries
        all_entries = self._store.search(limit=100000)

        # Apply retention policies
        actions = self._retention.evaluate(all_entries, self._store)

        for entry, action, policy_name in actions:
            try:
                if action == RetentionAction.DELETE:
                    if self._store.delete(entry.id):
                        removed += 1

                elif action == RetentionAction.ARCHIVE:
                    # Mark as archived via metadata
                    self._store.update(entry.id, metadata={
                        "archived": True,
                        "archived_at": time.time(),
                        "archive_policy": policy_name,
                    })
                    archived += 1

                elif action == RetentionAction.PROMOTE:
                    if self._promote_callback:
                        self._promote_callback(entry)
                        promoted += 1
                    else:
                        # Default: change memory type to long_term
                        self._store.update(entry.id, metadata={
                            "promoted_to_ltm": True,
                            "promoted_at": time.time(),
                        })
                        promoted += 1

                elif action == RetentionAction.COMPRESS:
                    # Mark for compression (handled by consolidation)
                    self._store.update(entry.id, metadata={
                        "needs_compression": True,
                        "compress_at": time.time(),
                    })

            except Exception as exc:
                logger.warning("GC: action %s failed for %s: %s",
                              action.value, entry.id, exc)

        # Also remove expired entries directly
        expired_count = self._prune_expired()

        duration = time.time() - start

        with self._lock:
            self._stats["runs"] += 1
            self._stats["entries_removed"] += removed + expired_count
            self._stats["entries_archived"] += archived
            self._stats["entries_promoted"] += promoted
            self._stats["last_run_duration"] = duration

        if removed + expired_count + archived + promoted > 0:
            logger.info(
                "GC: removed=%d, archived=%d, promoted=%d, expired=%d in %.2fs",
                removed, archived, promoted, expired_count, duration,
            )

        return {
            "removed": removed,
            "archived": archived,
            "promoted": promoted,
            "expired": expired_count,
            "duration_seconds": duration,
        }

    def _prune_expired(self) -> int:
        """Remove all expired entries from the store."""
        count = 0
        entries = self._store.search(limit=100000)
        now = time.time()
        for entry in entries:
            if entry.expires_at and now > entry.expires_at:
                if self._store.delete(entry.id):
                    count += 1
        return count

    # ------------------------------------------------------------------
    # Auto-GC
    # ------------------------------------------------------------------

    def start_auto(self, interval_minutes: float = 30.0) -> None:
        """Start automatic garbage collection on a timer.

        Runs GC periodically in a background thread.
        """
        with self._lock:
            if self._gc_thread and self._gc_thread.is_alive():
                return
            self._stop_flag = False
            self._gc_thread = threading.Thread(
                target=self._auto_loop,
                args=(interval_minutes,),
                daemon=True,
                name="memory-gc",
            )
            self._gc_thread.start()
            logger.info("GC: auto-GC started (interval=%d min)", interval_minutes)

    def stop_auto(self) -> None:
        """Stop automatic garbage collection."""
        self._stop_flag = True
        with self._lock:
            if self._gc_thread:
                self._gc_thread.join(timeout=5)
                self._gc_thread = None
        logger.info("GC: auto-GC stopped")

    def _auto_loop(self, interval_minutes: float) -> None:
        """Auto-GC loop."""
        while not self._stop_flag:
            time.sleep(interval_minutes * 60)
            if not self._stop_flag:
                try:
                    self.run()
                except Exception as exc:
                    logger.error("GC: auto-GC cycle failed: %s", exc)

    def set_promote_callback(self, callback: Callable[[MemoryEntry], None]) -> None:
        """Set a callback for promotion events.

        Called when a retention policy decides to promote an entry to LTM.
        The callback should handle the actual promotion (save to LTM store).
        """
        self._promote_callback = callback

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get garbage collector statistics."""
        with self._lock:
            return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset GC statistics."""
        with self._lock:
            self._stats = {
                "runs": 0,
                "entries_removed": 0,
                "entries_archived": 0,
                "entries_promoted": 0,
                "last_run_duration": 0.0,
            }
