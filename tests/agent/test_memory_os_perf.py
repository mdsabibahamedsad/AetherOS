"""Performance (P95) and stress smoke (P96): realistic volumes with generous,
non-flaky thresholds; correctness asserted, timing reported."""

import time

from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    RelationshipType,
)
from agent.memory_os.security import AccessContext


def test_volume_store_and_retrieve_under_budget():
    m = MemoryManager()
    ctx = AccessContext.user()
    t0 = time.time()
    n = 700
    for i in range(n):
        m.store.upsert_item(MemoryItem(
            content=f"project note {i}: service_{i % 20} latency p99 "
                    f"{i}ms region eu-west-{i % 3}",
            summary=f"note {i}",
            type=MemoryType.PROJECT if i % 2 else MemoryType.EPISODIC,
            scope=MemoryScope.PROJECT,
            project_id=f"proj-{i % 5}",
        ))
    insert_s = time.time() - t0

    t1 = time.time()
    queries = 25
    for q in range(queries):
        res = m.retriever.search(f"service_{q % 20} latency", ctx, top_k=5)
        assert res.hits
    search_s = time.time() - t1

    # generous CI-safe ceilings: inserts well under 30s hard cap,
    # each search averaging under 150ms.
    assert insert_s < 25, f"bulk insert too slow: {insert_s:.1f}s"
    assert search_s / queries < 0.15, f"search too slow: {search_s/queries:.3f}s"


def test_graph_traversal_bounded_and_fast():
    m = MemoryManager()
    reg_ids = []
    for i in range(40):
        ent = {"entity_id": f"e{i}", "etype": "person", "name": f"P{i}",
               "canonical_key": f"p{i}", "confidence": 0.5,
               "resolution": "separate", "merged_into": "",
               "created_at": time.time(), "updated_at": time.time(),
               "meta": "{}"}
        m.store.upsert_entity(ent)
        reg_ids.append(f"e{i}")
    for a, b in zip(reg_ids, reg_ids[1:]):
        m.link("entity", a, RelationshipType.RELATED_TO, "entity", b)
    t0 = time.time()
    sg = m.graph.subgraph("entity", "e0", depth=3)
    elapsed = time.time() - t0
    assert sg["nodes"] and elapsed < 1.0


def test_concurrent_retrievals_smoke():
    import threading

    m = MemoryManager()
    for i in range(120):
        m.store.upsert_item(MemoryItem(
            content=f"concurrent target item {i}", status=MemoryStatus.ACTIVE))
    errors = []

    def worker(seed):
        try:
            ctx = AccessContext.user("default")
            for k in range(6):
                res = m.retriever.search(f"target item {seed + k}", ctx)
                assert isinstance(res.hits, list)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    assert not errors, f"concurrent retrieval errors: {errors[:3]}"


def test_consolidation_over_many_episodes_is_affordable():
    m = MemoryManager()
    now = time.time()
    for i in range(150):
        e = MemoryItem(content=f"episode {i}", summary=f"ep {i % 30}",
                       type=MemoryType.EPISODIC,
                       semantic_key=f"key-{i % 30}",
                       created_at=now + i, updated_at=now + i)
        m.store.upsert_item(e)
    t0 = time.time()
    produced = m.lifecycle.consolidate(min_events=5)
    elapsed = time.time() - t0
    assert produced  # 30 keys x >=5 events each
    assert elapsed < 5.0
