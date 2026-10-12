"""P95 — larger-volume performance verification (own file: own subprocess
budget under the per-file parallel runner)."""

import time

from agent.memory_os.embeddings import HashingEmbedder
from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    RelationshipType,
)
from agent.memory_os.security import AccessContext


def test_3k_item_store_and_60_hybrid_searches():
    m = MemoryManager()
    ctx = AccessContext.user()
    t0 = time.time()
    for i in range(2500):
        m.store.upsert_item(MemoryItem(
            content=f"service_{i % 25} release note {i}: latency p99 "
                    f"{i % 900}ms region eu-west-{i % 4} owner team-{i % 12}",
            summary=f"release note {i}",
            type=MemoryType.PROJECT if i % 2 else MemoryType.EPISODIC,
            scope=MemoryScope.PROJECT,
            project_id=f"proj-{i % 10}",
        ))
    insert_s = time.time() - t0

    t1 = time.time()
    for q in range(50):
        res = m.retriever.search(f"service_{q % 25} release latency", ctx,
                                 top_k=5)
        assert res.hits
    search_s = time.time() - t1

    assert insert_s < 45.0, f"bulk insert too slow: {insert_s:.1f}s"
    assert search_s / 50 < 0.25, f"search too slow: {search_s/50:.3f}s avg"


def test_embedding_index_build_at_scale():
    m = MemoryManager()
    for i in range(600):
        m.store.upsert_item(MemoryItem(
            content=f"embed corpus document {i}: topic {i % 40} with "
                    f"body text tokens alpha beta gamma {i}",
            status=MemoryStatus.ACTIVE,
        ))
    t0 = time.time()
    idx = m.enable_semantic_search()
    n = idx.reindex(m)
    elapsed = time.time() - t0
    assert n == 600
    assert idx.count() == 600
    assert elapsed < 8.0, f"embedding build too slow: {elapsed:.1f}s"
    # provider sanity after scale build
    assert isinstance(idx.provider, HashingEmbedder)
