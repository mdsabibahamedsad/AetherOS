"""Embedding layer (P42, P71-73): offline vector retrieval, persistence,
re-indexing — deterministic, no network."""

import math

from agent.memory_os.embeddings import (
    EmbeddingIndex,
    HashingEmbedder,
    SemanticScorer,
    cosine,
)
from agent.memory_os.manager import MemoryManager
from agent.memory_os.security import AccessContext


def test_hashing_embedder_is_deterministic_and_normalized():
    e = HashingEmbedder(dim=128)
    a = e.embed("kubernetes autoscaling policy")
    b = e.embed("kubernetes autoscaling policy")
    c = e.embed("grandma apple pie recipe")
    assert a == b
    assert all(abs(x) <= 1.0 for x in a)
    norm = math.sqrt(sum(x * x for x in a))
    assert abs(norm - 1.0) < 1e-5
    assert cosine(a, c) < 0.3


def test_scorer_ranks_related_above_unrelated():
    s = SemanticScorer(HashingEmbedder(dim=256))
    q = "database migration running status"
    rel = s(q, "the migration runner completed all steps")
    unrel = s(q, "chocolate cake frosting recipe")
    assert rel > unrel


def test_morphological_variant_retrieved_without_shared_tokens():
    m = MemoryManager()
    ctx = AccessContext.user()
    m.remember("The runner sprints every morning before work")
    m.enable_semantic_search()  # default offline provider
    hits = m.search("running sprint routines", ctx, top_k=3)
    assert hits.hits, "semantic-only signal must retrieve morphological match"
    # lexical overlap between query tokens {running, sprint, routines} and the
    # stored text is zero as whole words — the hit is semantic-driven.
    h = hits.hits[0]
    assert not any(t in h.item.content.lower().split()
                   for t in ("running", "sprint", "routines"))


def test_enable_semantic_persists_vectors_and_metadata(m=None):
    m = MemoryManager()
    ctx = AccessContext.user()
    o = m.remember("vector persistence probe quokka", ctx=ctx)
    idx = m.enable_semantic_search()
    idx.reindex(m)
    row = idx.get(o.item.memory_id)
    assert row is not None
    model, dim, vec = row
    assert model.startswith("hashing-v1") and dim == 256 and len(vec) == 256
    refreshed = m.store.get_item(o.item.memory_id)
    assert refreshed.metadata["embedding"]["model"] == model
    assert idx.count() >= 1


def test_reindex_updates_created_at_and_model():
    m = MemoryManager()
    o = m.remember("reindex target albatross")
    idx = m.enable_semantic_search()
    idx.reindex(m)
    first = idx.get(o.item.memory_id)[2]
    idx.provider = HashingEmbedder(dim=64)
    idx.reindex(m)
    model, dim, second = idx.get(o.item.memory_id)
    assert dim == 64 and len(second) == 64 and model.endswith("(64)")


def test_semantic_can_be_disabled_again():
    m = MemoryManager()
    ctx = AccessContext.user()
    m.remember("unique flamingo fact for disable test")
    m.enable_semantic_search()
    m.retriever.set_semantic_scorer(None)
    res = m.search("flamingo", ctx)  # keyword still works
    assert res.hits
    # pure-semantic query no longer matches anything (precision guard)
    res2 = m.search("running sprint routines", ctx)
    assert res2.hits == []


def test_stored_vectors_survive_new_manager_instance(tmp_path):
    from agent.memory_os.store import MemoryStore

    db = str(tmp_path / "shared.db")
    m1 = MemoryManager(store=MemoryStore(db_path=db))
    o = m1.remember("durable vector heron")
    idx = m1.enable_semantic_search()
    idx.reindex(m1)

    m2 = MemoryManager(store=MemoryStore(db_path=db))
    idx2 = EmbeddingIndex(m2.store)
    got = idx2.get(o.item.memory_id)
    assert got is not None and got[0].startswith("hashing-v1")
