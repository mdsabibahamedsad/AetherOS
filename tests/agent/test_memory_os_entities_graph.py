"""Entity resolution (P10-11) and knowledge graph provenance (P13-14)."""

import pytest

from agent.memory_os.entities import EntityRegistry
from agent.memory_os.graph import KnowledgeGraph
from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    Confidence,
    MemoryItem,
    RelationshipType,
    Resolution,
)
from agent.memory_os.security import AccessContext


@pytest.fixture
def mgr():
    return MemoryManager()


def test_same_type_alias_resolves_merged(mgr):
    reg = EntityRegistry(mgr.store)
    first = reg.resolve("Ada Lovelace", etype="person")
    second = reg.resolve("ada lovelace", etype="person")
    assert first["resolution"] in (Resolution.SEPARATE, Resolution.MERGED)
    assert second["resolution"] is Resolution.MERGED
    assert second["entity"]["entity_id"] == first["entity"]["entity_id"]


def test_identifier_beats_name(mgr):
    reg = EntityRegistry(mgr.store)
    a = reg.resolve("ACME", etype="organization", identifier="acme-gmbh-2026")
    b = reg.resolve("Acme Corporation", etype="organization",
                    identifier="acme-gmbh-2026")
    assert b["resolution"] is Resolution.MERGED
    assert b["basis"] == "identifier"


def test_namespace_repo_match(mgr):
    reg = EntityRegistry(mgr.store)
    a = reg.resolve("aetheros", etype="repository", repo="github.com/aetheros/core")
    b = reg.resolve("AetherOS core", etype="repository",
                    repo="github.com/aetheros/core")
    assert b["resolution"] is Resolution.MERGED


def test_same_name_different_type_stays_uncertain():
    m = MemoryManager()
    reg = EntityRegistry(m.store)
    person = reg.resolve("Phoenix", etype="person")
    place = reg.resolve("Phoenix", etype="location")
    assert place["resolution"] is Resolution.UNCERTAIN
    assert person["entity"]["entity_id"] != place["entity"]["entity_id"]


def test_explicit_merge_then_separate(mgr):
    reg = EntityRegistry(mgr.store)
    e1 = reg.resolve("Bob", etype="person")["entity"]
    e2 = reg.create(etype="person", name="Robert")
    assert reg.merge(e1["entity_id"], e2["entity_id"])
    resolved = reg.get(e2["entity_id"])
    assert resolved["entity_id"] == e1["entity_id"]
    assert reg.separate(e1["entity_id"]) >= 1
    child = mgr.store.get_entity(e2["entity_id"])
    assert child["resolution"] == "separate"


def test_edges_carry_provenance_and_confidence(mgr):
    ctx = AccessContext.user()
    o = mgr.remember("Alice owns the deploy pipeline", ctx=ctx,
                     confidence=Confidence.CONFIRMED)
    reg = EntityRegistry(mgr.store)
    alice = reg.resolve("Alice", etype="person")["entity"]
    pipe = reg.resolve("deploy-pipeline", etype="technology")["entity"]
    kg = KnowledgeGraph(mgr.store, reg)
    edge = kg.relate("entity", alice["entity_id"], RelationshipType.OWNS,
                     "entity", pipe["entity_id"],
                     evidence_item_id=o.item.memory_id, confidence=0.9)
    assert edge["evidence_item_id"] == o.item.memory_id
    neigh = kg.neighbors("entity", alice["entity_id"])
    assert any(e["rel"] == "owns" for e in neigh)


def test_subgraph_depth_bounded(mgr):
    reg = EntityRegistry(mgr.store)
    ids = [reg.resolve(f"N{i}", etype="project")["entity"]["entity_id"]
           for i in range(4)]
    kg = KnowledgeGraph(mgr.store, reg)
    for a, b in zip(ids, ids[1:]):
        kg.relate("entity", a, RelationshipType.RELATED_TO, "entity", b)
    sg1 = kg.subgraph("entity", ids[0], depth=1)
    sg2 = kg.subgraph("entity", ids[0], depth=3)
    assert len(sg2["nodes"]) > len(sg1["nodes"])
    assert len(sg1["edges"]) <= 2


def test_contradiction_edge_queryable_and_purge_on_forget(mgr):
    m = MemoryManager()
    reg = EntityRegistry(m.store)
    kg = m.graph
    a = reg.resolve("Claim A", etype="document")["entity"]
    b = reg.resolve("Claim B", etype="document")["entity"]
    kg.relate("entity", a["entity_id"], RelationshipType.CONTRADICTS,
              "entity", b["entity_id"], confidence=0.8)
    assert len(kg.contradicting_edges(b["entity_id"])) == 1
    # right-to-forget purges touching edges
    item = MemoryItem(content="temp")
    m.store.upsert_item(item)
    m.link("item", item.memory_id, RelationshipType.MENTIONS,
           "entity", a["entity_id"])
    report = m.forget(item.memory_id, AccessContext.user())
    assert report["graph_edges"] >= 1
