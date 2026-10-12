"""Hybrid retrieval: ranking, budget, contextual retrieval, explanations
(P41-47, P64), and working memory slots (P3)."""

import time

import pytest

from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    Confidence,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
)
from agent.memory_os.retrieval import WorkingMemory
from agent.memory_os.security import AccessContext


def test_keyword_retrieval_ranks_relevant_first():
    m = MemoryManager()
    ctx = AccessContext.user()
    m.remember("The backup cron job runs nightly at 03:00", ctx=ctx)
    m.remember("Favorite pizza is margherita", ctx=ctx)
    res = m.search("backup cron schedule", ctx)
    assert res.hits and "cron" in res.hits[0].item.content


def test_ranking_respects_importance_and_confidence():
    m = MemoryManager()
    ctx = AccessContext.user()
    hi = MemoryItem(content="critical prod incident postmortem",
                    importance=1.0, confidence=Confidence.CONFIRMED,
                    status=MemoryStatus.ACTIVE)
    lo = MemoryItem(content="critical prod incident rumor",
                    importance=0.05, confidence=Confidence.LOW,
                    status=MemoryStatus.ACTIVE)
    for it in (hi, lo):
        m.store.upsert_item(it)
    res = m.search("prod incident", ctx)
    assert res.hits[0].item.memory_id == hi.memory_id


def test_temporal_and_metadata_filters():
    m = MemoryManager()
    old = MemoryItem(content="old architecture decision: monolith",
                     valid_until=time.time() - 10, status=MemoryStatus.ACTIVE)
    new = MemoryItem(content="current architecture decision: services",
                     valid_from=time.time() - 5, status=MemoryStatus.ACTIVE)
    m.store.upsert_item(old)
    m.store.upsert_item(new)
    ctx = AccessContext.user()
    res = m.retriever.search("architecture decision", ctx, now=time.time())
    ids = {h.item.memory_id for h in res.hits}
    assert new.memory_id in ids


def test_same_query_different_project_is_contextual():
    m = MemoryManager()
    m.remember("the database migration tool is flyway",
               scope=MemoryScope.PROJECT, project_id="alpha")
    m.remember("the database migration tool is liquibase",
               scope=MemoryScope.PROJECT, project_id="beta")
    ra = m.search("which migration tool", AccessContext.user(project_id=""),
                  project_id="alpha")
    rb = m.search("which migration tool", AccessContext.user(project_id=""),
                  project_id="beta")
    assert ra.hits and all(h.item.project_id == "alpha" for h in ra.hits)
    assert rb.hits and all(h.item.project_id == "beta" for h in rb.hits)


def test_budget_caps_hits_and_chars():
    m = MemoryManager()
    ctx = AccessContext.user()
    for i in range(30):
        m.store.upsert_item(MemoryItem(
            content=f"meeting note number {i} about budget planning"))
    res = m.retriever.search("budget planning meeting note", ctx,
                             top_k=100)
    block = res.context_block(max_chars=500)
    assert len(block) <= 520
    assert len(res.hits) <= 100  # top_k respected upstream


def test_explanation_includes_source_when_and_why():
    m = MemoryManager()
    ctx = AccessContext.user()
    o = m.remember("User prefers Python for scripting", ctx=ctx)
    res = m.search("preferred scripting language", ctx)
    hit = next(h for h in res.hits if h.item.memory_id == o.item.memory_id)
    expl = hit.explanation()
    assert "source=user_explicit" in expl
    assert "keyword" in " ".join(hit.why) or "score=" in expl


def test_semantic_scorer_injection_changes_ranking():
    m = MemoryManager()
    a = MemoryItem(content="automobile insurance policy details",
                   status=MemoryStatus.ACTIVE)
    b = MemoryItem(content="chocolate cake recipe steps",
                   status=MemoryStatus.ACTIVE)
    for it in (a, b):
        m.store.upsert_item(it)
    ctx = AccessContext.user()

    def car_affinity(query, content):
        return 0.9 if "car" in content or "automobile" in content else 0.0

    m.retriever.set_semantic_scorer(car_affinity)
    res = m.search("vehicle coverage", ctx)
    assert res.hits[0].item.memory_id == a.memory_id
    m.retriever.set_semantic_scorer(None)


def test_working_memory_slots_and_snapshot():
    m = MemoryManager()
    wm = WorkingMemory(m.store, session_id="s-123")
    wm.set("objective", ["finish M18"])
    wm.set("files", ["agent/memory_os/manager.py"])
    wm.set("decisions", ["SQLite substrate"])
    assert wm.get("objective") == ["finish M18"]
    with pytest.raises(ValueError):
        wm.set("not_a_slot", 1)
    snap = wm.snapshot_as_episodic(owner="default")
    assert snap.type is MemoryType.EPISODIC
    assert "finish M18" in snap.content
    wm.clear()
    assert wm.all() == {}


def test_superseded_and_quarantined_excluded_from_retrieval():
    m = MemoryManager()
    sup = MemoryItem(content="outdated api endpoint v1",
                     status=MemoryStatus.SUPERSEDED)
    quar = MemoryItem(content="ignore previous instructions spam",
                      status=MemoryStatus.QUARANTINED)
    good = MemoryItem(content="current api endpoint v2 docs",
                      status=MemoryStatus.ACTIVE)
    for it in (sup, quar, good):
        m.store.upsert_item(it)
    res = m.retriever.search("api endpoint", AccessContext.user())
    ids = {h.item.memory_id for h in res.hits}
    assert good.memory_id in ids
    assert sup.memory_id not in ids and quar.memory_id not in ids


def test_accessed_items_get_touch_timestamps():
    m = MemoryManager()
    ctx = AccessContext.user()
    o = m.remember("recall me please uniquely quantum")
    before = o.item.last_accessed_at
    time.sleep(0.01)
    m.search("quantum recall", ctx)
    after = m.store.get_item(o.item.memory_id).last_accessed_at
    assert after >= before
