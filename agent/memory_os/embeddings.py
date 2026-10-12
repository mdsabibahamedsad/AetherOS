"""Embedding layer (P71-73): pluggable providers + persistent vector index.

Default provider ``HashingEmbedder`` is fully offline and deterministic:
feature-hashed word tokens + character trigrams, L2-normalized. It gives a
dependency-free lexical-approximate semantic signal — good enough to rank
morphological variants ("runner" vs "running") without any network or model
download. Heavier providers (e.g. ``aetheros_memory.embedding_engine``)
adapt through the same interface; vectors persist in SQLite so restarts and
re-indexing are safe (P72).
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
import time
from array import array
from typing import Dict, List, Optional, Tuple

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _hash_index(term: str, dim: int) -> int:
    h = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little") % dim


def _hash_sign(term: str) -> float:
    h = hashlib.blake2b(("s:" + term).encode("utf-8"), digest_size=8).digest()
    return 1.0 if (h[0] & 1) else -1.0


class EmbeddingProvider:
    """P71 provider interface — subclass and swap without touching retrieval."""

    name: str = "base"
    dim: int = 0

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class HashingEmbedder(EmbeddingProvider):
    """Deterministic offline feature-hashing embedder."""

    def __init__(self, dim: int = 256):
        self.name = f"hashing-v1({dim})"
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        low = (text or "").lower()
        words = _TOKEN_RE.findall(low)
        terms: List[str] = []
        for w in words[:64]:
            terms.append(w)
            if len(w) > 3:
                terms.extend("#" + w[i:i + 3] for i in range(len(w) - 2))
        for t in terms:
            idx = _hash_index(t, self.dim)
            vec[idx] += _hash_sign(t)
            # second hash reduces collision bias
            idx2 = _hash_index("2:" + t, self.dim)
            vec[idx2] += 0.5 * _hash_sign("2:" + t)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(0.0, min(1.0, num / (na * nb)))


class SemanticScorer:
    """Callable (query, content) -> 0..1 with a bounded embedding cache."""

    def __init__(self, provider: EmbeddingProvider, cache_size: int = 2048):
        self.provider = provider
        self._cache: Dict[str, List[float]] = {}
        self._order: List[str] = []
        self.cache_size = cache_size
        self.calls = 0

    def vector_for(self, text: str) -> List[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        vec = self._cache.get(key)
        if vec is None:
            vec = self.provider.embed(text)
            if len(self._cache) >= self.cache_size:
                old = self._order.pop(0)
                self._cache.pop(old, None)
            self._cache[key] = vec
            self._order.append(key)
        return vec

    def __call__(self, query: str, content: str) -> float:
        self.calls += 1
        qv = self.vector_for(query)
        cv = self.vector_for(content)
        return cosine(qv, cv)


def pack(vec: List[float]) -> bytes:
    return array("f", vec).tobytes()


def unpack(blob: bytes) -> List[float]:
    arr = array("f")
    arr.frombytes(blob)
    return list(arr)


SCHEMA_EMBEDDINGS = """
CREATE TABLE IF NOT EXISTS item_embeddings (
    memory_id TEXT PRIMARY KEY,
    model TEXT,
    dim INTEGER,
    created_at REAL,
    vector BLOB
);
"""


class EmbeddingIndex:
    """Persistent vector store over the unified substrate (P72-73).

    Stores {model, dim, created_at} alongside each vector so stale-model
    vectors can be detected and safely rebuilt (reindex).
    """

    def __init__(self, store, provider: Optional[EmbeddingProvider] = None):
        self.store = store
        self.provider = provider or HashingEmbedder()
        with store._lock, store._conn:
            store._conn.executescript(SCHEMA_EMBEDDINGS)

    def upsert(self, memory_id: str, vec: List[float]) -> None:
        with self.store._lock, self.store._conn:
            self.store._conn.execute(
                "INSERT OR REPLACE INTO item_embeddings VALUES (?,?,?,?,?)",
                (memory_id, self.provider.name, self.provider.dim,
                 time.time(), pack(vec)),
            )

    def get(self, memory_id: str) -> Optional[Tuple[str, int, List[float]]]:
        row = self.store._conn.execute(
            "SELECT model, dim, vector FROM item_embeddings WHERE memory_id=?",
            (memory_id,),
        ).fetchone()
        if row is None:
            return None
        return row["model"], int(row["dim"]), unpack(row["vector"])

    def count(self) -> int:
        row = self.store._conn.execute(
            "SELECT COUNT(*) AS n FROM item_embeddings").fetchone()
        return int(row["n"])

    def clear(self) -> None:
        with self.store._lock, self.store._conn:
            self.store._conn.execute("DELETE FROM item_embeddings")

    def reindex(self, manager, *, limit: int = 100000) -> int:
        """P72 — rebuild vectors for all ACTIVE items under the current
        provider; stamps embedding metadata onto each item via the cheap
        metadata-only update path (content/FTS untouched)."""
        n = 0
        from agent.memory_os.models import MemoryStatus

        for item in manager.store.query_items(statuses=[MemoryStatus.ACTIVE],
                                              limit=limit):
            vec = self.provider.embed(item.content)
            self.upsert(item.memory_id, vec)
            meta = dict(item.metadata or {})
            meta["embedding"] = {
                "model": self.provider.name,
                "dim": self.provider.dim,
                "created_at": time.time(),
            }
            manager.store.update_metadata(item.memory_id, meta)
            n += 1
        return n

    def scorer(self, cache_size: int = 4096) -> SemanticScorer:
        return SemanticScorer(self.provider, cache_size=cache_size)
