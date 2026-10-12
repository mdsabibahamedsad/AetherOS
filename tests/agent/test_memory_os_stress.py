"""P96 — memory stress: many projects × many agents, concurrent mixed
workload, long-conversation consolidation. Bounded but well beyond smoke."""

import threading
import time

from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    FeedbackKind,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
)
from agent.memory_os.security import AccessContext


def test_many_projects_many_agents_concurrent_isolated_retrieval():
    m = MemoryManager()
    projects = [f"proj-{i}" for i in range(30)]
    for pid in projects:
        for k in range(5):
            m.remember(
                f"{pid} shared fact number {k}: deploy pipeline uses runner {k}",
                type_=MemoryType.PROJECT, scope=MemoryScope.PROJECT,
                project_id=pid, allow_agents=True,
            )
    errors = []
    isolation_violations = []

    def agent_worker(agent_idx):
        try:
            pid = projects[agent_idx % len(projects)]
            ctx = AccessContext.agent(f"agent-{agent_idx}", project_id=pid)
            for q in range(6):
                res = m.retriever.search("deploy pipeline runner", ctx, top_k=10)
                for h in res.hits:
                    if h.item.project_id and h.item.project_id != pid:
                        isolation_violations.append((agent_idx, h.item.project_id))
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=agent_worker, args=(i,))
               for i in range(10)]
    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join(60)
    elapsed = time.time() - t0
    assert not errors, f"errors: {errors[:3]}"
    assert not isolation_violations, f"leaks: {isolation_violations[:3]}"
    assert elapsed < 30.0


def test_mixed_workload_hammer_interleaved_write_read_delete_feedback():
    m = MemoryManager()
    errors = []

    def writer(seed):
        try:
            ctx = AccessContext.user("default")
            for i in range(40):
                item = MemoryItem(
                    content=f"hammer item hammer-{seed}-{i} payload alpha",
                    summary=f"hammer {seed}-{i}",
                )
                m.store.upsert_item(item)
                res = m.retriever.search(
                    f"payload alpha hammer-{seed}", ctx)
                assert isinstance(res.hits, list)
                if i % 10 == 9:
                    m.forget(item.memory_id, AccessContext.user())
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    def reader():
        try:
            ctx = AccessContext.user()
            for _ in range(50):
                m.retriever.search("hammer item payload", ctx)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    def feedbacker():
        try:
            ctx = AccessContext.user()
            items = m.list(ctx, limit=20)
            for it in items:
                m.lifecycle.apply_feedback(it, FeedbackKind.USEFUL)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = ([threading.Thread(target=writer, args=(s,)) for s in range(4)]
               + [threading.Thread(target=reader) for _ in range(2)]
               + [threading.Thread(target=feedbacker) for _ in range(2)])
    for th in threads:
        th.start()
    for th in threads:
        th.join(90)
    assert not errors, f"mixed workload errors: {errors[:3]}"


def test_long_conversation_simulation_with_periodic_consolidation():
    m = MemoryManager()
    turns = 600
    t0 = time.time()
    for i in range(turns):
        e = MemoryItem(
            content=f"conversation turn {i}: user asked about topic {i % 20}",
            summary=f"turn {i} topic {i % 20}",
            type=MemoryType.EPISODIC,
            semantic_key=f"topic-{i % 20}",
            scope=MemoryScope.USER,
        )
        e.provenance.actor = "long-run"
        m.store.upsert_item(e)
        if (i + 1) % 150 == 0:
            produced = m.lifecycle.consolidate(min_events=8)
            assert isinstance(produced, list)
    elapsed = time.time() - t0
    cands = m.list(AccessContext.user(),
                   statuses=[MemoryStatus.CANDIDATE], limit=100)
    consolidated = [c for c in cands if c.provenance.origin_event == "consolidation"]
    assert consolidated, "periodic consolidation must produce candidates"
    assert elapsed < 25.0, f"long conversation too slow: {elapsed:.1f}s"


def test_graph_traversal_200_nodes_depth2():
    import time as _time

    from agent.memory_os.models import RelationshipType

    m = MemoryManager()
    ids = []
    for i in range(200):
        ent = {'entity_id': f'g{i}', 'etype': 'project', 'name': f'G{i}',
               'canonical_key': f'g{i}', 'confidence': 0.5,
               'resolution': 'separate', 'merged_into': '',
               'created_at': _time.time(), 'updated_at': _time.time(),
               'meta': '{}'}
        m.store.upsert_entity(ent)
        ids.append(f'g{i}')
    for a, b in zip(ids, ids[1:]):
        m.link('entity', a, RelationshipType.RELATED_TO, 'entity', b,
               confidence=0.5)
    t0 = _time.time()
    sg = m.graph.subgraph('entity', ids[0], depth=2)
    elapsed = _time.time() - t0
    assert len(sg['nodes']) >= 3
    assert elapsed < 2.0
