"""Store layer: CRUD, FTS, versions, audit chain integrity."""

import time

import pytest

from agent.memory_os.models import (
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    Provenance,
)
from agent.memory_os.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(db_path=str(tmp_path / "m.db"))
    yield s
    s.close()


def test_upsert_get_roundtrip(store):
    item = MemoryItem(content="deploy via approved workflow",
                      type=MemoryType.PROCEDURAL, scope=MemoryScope.PROJECT,
                      project_id="web")
    store.upsert_item(item, actor="test")
    loaded = store.get_item(item.memory_id)
    assert loaded is not None
    assert loaded.content == item.content
    assert loaded.type is MemoryType.PROCEDURAL
    assert loaded.provenance is not None


def test_fts_finds_keyword_matches_only(store):
    a = MemoryItem(content="kubernetes cluster autoscaling notes")
    b = MemoryItem(content="grandma apple pie recipe")
    for it in (a, b):
        store.upsert_item(it)
    hits = dict(store.fts_search("kubernetes autoscaling"))
    assert a.memory_id in hits
    assert b.memory_id not in hits


def test_fts_empty_and_garbage_queries_are_safe(store):
    assert store.fts_search("") == []
    assert store.fts_search("   !!! ??? ") == []


def test_versions_recorded_on_change(store):
    item = MemoryItem(content="v1 content")
    store.upsert_item(item, actor="t")
    v2 = item.with_content("v2 content")
    store.upsert_item(v2, actor="t", note="edit")
    versions = store.versions(item.memory_id)
    assert any(v["version"] == 2 for v in versions)


def test_delete_removes_item_fts_and_versions(store):
    item = MemoryItem(content="to be deleted")
    store.upsert_item(item)
    v2 = item.with_content("edited")
    store.upsert_item(v2)
    assert store.delete_item(item.memory_id) is True
    assert store.get_item(item.memory_id) is None
    assert store.fts_search("deleted") == []
    assert store.versions(item.memory_id) == []


def test_audit_chain_detects_tampering(store):
    store.audit.append("create", "user", target="a")
    store.audit.append("update", "user", target="a")
    assert store.audit.verify() is True
    # tamper: rewrite an action in place
    store._conn.execute("UPDATE audit_log SET action='forged' WHERE seq=1")
    store._conn.commit()
    assert store.audit.verify() is False


def test_counters(store):
    store.bump_counter("queries", 2)
    store.bump_counter("queries")
    assert store.get_counter("queries") == 3


def test_working_slots_roundtrip(store):
    store.set_slot("sess1", "objective", {"value": ["ship v2"]})
    assert store.get_slot("sess1", "objective") == {"value": ["ship v2"]}
    store.clear_slots("sess1")
    assert store.get_slot("sess1", "objective") is None


def test_entity_merge_moves_edges(store):
    now = time.time()
    store.upsert_entity({"entity_id": "e1", "etype": "person", "name": "Ada",
                         "canonical_key": "ada", "confidence": 0.5,
                         "resolution": "separate", "merged_into": "",
                         "created_at": now, "updated_at": now, "meta": "{}"})
    store.upsert_entity({"entity_id": "e2", "etype": "person", "name": "A.",
                         "canonical_key": "a", "confidence": 0.5,
                         "resolution": "separate", "merged_into": "",
                         "created_at": now, "updated_at": now, "meta": "{}"})
    store.add_edge({"edge_id": "x", "src_kind": "entity", "src_id": "e2",
                    "dst_kind": "item", "dst_id": "i9", "rel": "mentions",
                    "evidence_item_id": "", "confidence": 0.5,
                    "created_at": now, "valid_from": None,
                    "valid_until": None, "status": "active"})
    store.merge_entity("e1", "e2")
    dropped = store.get_entity("e2")
    assert dropped["resolution"] == "merged" and dropped["merged_into"] == "e1"
    edge = store.all_edges()[0]
    assert edge["src_id"] == "e1"


def test_purge_status_removes_terminal_rows(store):
    item = MemoryItem(content="gone soon", status=MemoryStatus.EXPIRED)
    store.upsert_item(item)
    n = store.purge_status(MemoryStatus.EXPIRED)
    assert n == 1
    assert store.get_item(item.memory_id) is None
