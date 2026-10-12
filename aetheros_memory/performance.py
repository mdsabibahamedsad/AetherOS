"""Memory Performance — caching, batch processing, background indexing, and compaction.

Provides a TTL cache with LRU eviction, batch processor, background
indexer thread, compaction engine, and a top-level orchestrator.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from aetheros_memory.embedding_engine import EmbeddingEngine
from aetheros_memory.memory_manager import MemoryManager, MemoryRecord

logger = logging.getLogger("aetheros_memory.performance")


class CacheLayer:
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0) -> None:
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float, float]] = {}
        self._access_order: List[str] = []
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expiry, _ = entry
            if expiry > 0 and time.time() > expiry:
                self._cache.pop(key, None)
                self._access_order = [k for k in self._access_order if k != key]
                self._misses += 1
                return None
            self._access_order = [k for k in self._access_order if k != key]
            self._access_order.append(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        expiry = 0.0
        if ttl is None:
            ttl = self._default_ttl
        if ttl > 0:
            expiry = time.time() + ttl
        with self._lock:
            if key in self._cache:
                self._access_order = [k for k in self._access_order if k != key]
            elif len(self._cache) >= self._max_size:
                oldest = self._access_order.pop(0) if self._access_order else None
                if oldest is not None:
                    self._cache.pop(oldest, None)
            self._cache[key] = (value, expiry, time.time())
            self._access_order.append(key)

    def invalidate(self, key: str) -> bool:
        with self._lock:
            existed = key in self._cache
            self._cache.pop(key, None)
            self._access_order = [k for k in self._access_order if k != key]
            return existed

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "default_ttl": self._default_ttl,
            }


class BatchProcessor:
    def __init__(self, batch_size: int = 32) -> None:
        self._batch_size = batch_size

    def process(
        self,
        items: List[Any],
        batch_size: Optional[int] = None,
        processor_fn: Optional[Callable[[List[Any]], List[Any]]] = None,
    ) -> List[Any]:
        if not items:
            return []
        if processor_fn is None:
            return list(items)
        bs = batch_size or self._batch_size
        results: List[Any] = []
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            batch_results = processor_fn(batch)
            results.extend(batch_results)
        return results

    def process_with_progress(
        self,
        items: List[Any],
        batch_size: Optional[int] = None,
        processor_fn: Optional[Callable[[List[Any]], List[Any]]] = None,
        callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Any]:
        if not items:
            if callback:
                callback(0, 0)
            return []
        if processor_fn is None:
            if callback:
                callback(len(items), len(items))
            return list(items)
        bs = batch_size or self._batch_size
        total = len(items)
        processed = 0
        results: List[Any] = []
        for i in range(0, total, bs):
            batch = items[i:i + bs]
            batch_results = processor_fn(batch)
            results.extend(batch_results)
            processed += len(batch)
            if callback:
                callback(processed, total)
        return results


class BackgroundIndexer:
    def __init__(self, memory_manager: MemoryManager, embedding_engine: Optional[EmbeddingEngine] = None) -> None:
        self._memory_manager = memory_manager
        self._embedding_engine = embedding_engine or memory_manager.embedding_engine
        self._lock = threading.RLock()
        self._queue: List[str] = []
        self._processing: Set[str] = set()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._total_indexed = 0
        self._total_errors = 0

    def start(self, interval: float = 5.0) -> None:
        if self._thread is not None and self._thread.is_alive():
            logger.warning("BackgroundIndexer already running")
            return
        self._stop_event.clear()

        def _loop() -> None:
            logger.info("BackgroundIndexer started (interval=%ss)", interval)
            while not self._stop_event.is_set():
                try:
                    self.process_queue()
                except Exception as exc:
                    logger.warning("BackgroundIndexer error: %s", exc)
                self._stop_event.wait(interval)

        self._thread = threading.Thread(target=_loop, daemon=True, name="memory-indexer")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._thread = None
        logger.info("BackgroundIndexer stopped")

    def queue_memory(self, memory_id: str) -> None:
        with self._lock:
            if memory_id not in self._queue and memory_id not in self._processing:
                self._queue.append(memory_id)

    def queue_batch(self, memory_ids: List[str]) -> None:
        with self._lock:
            for mid in memory_ids:
                if mid not in self._queue and mid not in self._processing:
                    self._queue.append(mid)

    def process_queue(self) -> int:
        batch: List[str] = []
        with self._lock:
            to_process = self._queue[:32]
            self._queue = self._queue[32:]
            for mid in to_process:
                self._processing.add(mid)
            batch = to_process

        if not batch:
            return 0

        count = 0
        for memory_id in batch:
            try:
                record = self._memory_manager.retrieve(memory_id)
                if record is None:
                    continue
                if not record.embedding or len(record.embedding) == 0:
                    result = self._embedding_engine.embed(record.content)
                    record.embedding = result.vector
                    self._memory_manager.update(memory_id, embedding=result.vector)
                with self._lock:
                    self._total_indexed += 1
                count += 1
            except Exception as exc:
                with self._lock:
                    self._total_errors += 1
                logger.debug("Indexing failed for %s: %s", memory_id, exc)

        with self._lock:
            for mid in batch:
                self._processing.discard(mid)

        return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "queue_size": len(self._queue),
                "processing": len(self._processing),
                "total_indexed": self._total_indexed,
                "total_errors": self._total_errors,
                "is_running": self._thread is not None and self._thread.is_alive(),
            }


class CompactionEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._total_compactions = 0
        self._total_removed = 0
        self._schedule_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def compact(self, memory_manager: MemoryManager, strategy: str = "hybrid") -> Dict[str, int]:
        results: Dict[str, int] = {
            "removed_expired": 0,
            "removed_low_importance": 0,
            "removed_stale": 0,
            "removed_low_access": 0,
            "total_removed": 0,
        }
        now = time.time()
        to_delete: List[str] = []

        with memory_manager._lock:
            for record in list(memory_manager._memories.values()):
                if record.archived:
                    continue

                if strategy in ("age", "hybrid"):
                    age_days = (now - record.created_at) / 86400
                    if age_days > 30 and not record.pinned and record.importance < 0.3:
                        to_delete.append(record.id)
                        results["removed_stale"] += 1
                        continue

                if strategy in ("importance", "hybrid"):
                    if record.importance < 0.1 and not record.pinned and record.access_count == 0:
                        to_delete.append(record.id)
                        results["removed_low_importance"] += 1
                        continue

                if strategy in ("access_count", "hybrid"):
                    if record.access_count == 0 and (now - record.created_at) > 604800 and not record.pinned:
                        to_delete.append(record.id)
                        results["removed_low_access"] += 1
                        continue

        for mid in to_delete:
            if memory_manager.delete(mid):
                results["total_removed"] += 1

        if strategy == "age":
            results["removed_low_importance"] = 0
            results["removed_low_access"] = 0
        elif strategy == "importance":
            results["removed_stale"] = 0
            results["removed_low_access"] = 0
        elif strategy == "access_count":
            results["removed_stale"] = 0
            results["removed_low_importance"] = 0

        compact_result = memory_manager.compact()
        results["removed_expired"] += compact_result.get("removed_expired", 0)
        results["total_removed"] += compact_result.get("removed_expired", 0)

        with self._lock:
            self._total_compactions += 1
            self._total_removed += results["total_removed"]

        return results

    def estimate_savings(self, memory_manager: MemoryManager) -> Dict[str, Any]:
        now = time.time()
        stale_count = 0
        low_imp_count = 0
        low_access_count = 0
        expired_count = 0
        total_size = 0

        with memory_manager._lock:
            for record in memory_manager._memories.values():
                content_size = len(record.content.encode("utf-8"))
                total_size += content_size
                age_days = (now - record.created_at) / 86400
                if age_days > 30 and not record.pinned and record.importance < 0.3:
                    stale_count += 1
                if record.importance < 0.1 and not record.pinned and record.access_count == 0:
                    low_imp_count += 1
                if record.access_count == 0 and (now - record.created_at) > 604800 and not record.pinned:
                    low_access_count += 1
                if record.ttl > 0 and (now - record.updated_at) > record.ttl:
                    expired_count += 1

        total_removable = stale_count + low_imp_count + low_access_count + expired_count
        total_memories = len(memory_manager._memories) or 1
        estimated_bytes_per_record = total_size // total_memories if total_memories else 0
        savings_bytes = total_removable * estimated_bytes_per_record

        return {
            "total_memories": len(memory_manager._memories),
            "stale_candidates": stale_count,
            "low_importance_candidates": low_imp_count,
            "low_access_candidates": low_access_count,
            "expired_candidates": expired_count,
            "total_removable": total_removable,
            "removable_percentage": round(total_removable / total_memories * 100, 2),
            "estimated_savings_bytes": savings_bytes,
        }

    def schedule(self, interval: float, memory_manager: MemoryManager) -> None:
        if self._schedule_thread is not None and self._schedule_thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            logger.info("CompactionEngine scheduled (interval=%ss)", interval)
            while not self._stop_event.is_set():
                self._stop_event.wait(interval)
                try:
                    result = self.compact(memory_manager, strategy="hybrid")
                    if result["total_removed"] > 0:
                        logger.info("Compaction removed %d memories", result["total_removed"])
                except Exception as exc:
                    logger.warning("Scheduled compaction failed: %s", exc)

        self._schedule_thread = threading.Thread(target=_loop, daemon=True, name="memory-compaction")
        self._schedule_thread.start()


class MemoryPerformance:
    def __init__(
        self,
        memory_manager: MemoryManager,
        embedding_engine: Optional[EmbeddingEngine] = None,
    ) -> None:
        self._memory_manager = memory_manager
        self._embedding_engine = embedding_engine or memory_manager.embedding_engine
        self._cache = CacheLayer(max_size=5000, default_ttl=300.0)
        self._batch_processor = BatchProcessor(batch_size=32)
        self._indexer = BackgroundIndexer(memory_manager, self._embedding_engine)
        self._compaction = CompactionEngine()

    def start_background_indexing(self, interval: float = 5.0) -> None:
        self._indexer.start(interval)

    def stop_background_indexing(self) -> None:
        self._indexer.stop()

    def start_auto_compaction(self, interval: float = 3600.0, strategy: str = "hybrid") -> None:
        self._compaction.schedule(interval, self._memory_manager)

    def get_cache_stats(self) -> Dict[str, Any]:
        return self._cache.stats()

    def get_indexer_stats(self) -> Dict[str, Any]:
        return self._indexer.stats()

    def get_compaction_stats(self) -> Dict[str, Any]:
        with self._compaction._lock:
            return {
                "total_compactions": self._compaction._total_compactions,
                "total_removed": self._compaction._total_removed,
            }

    def batch_embed(self, texts: List[str]) -> List[Any]:
        return self._batch_processor.process(
            texts,
            batch_size=32,
            processor_fn=lambda batch: self._embedding_engine.embed_batch(batch),
        )
