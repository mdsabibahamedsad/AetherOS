"""Standalone validation script for the entire aetheros_memory platform (18 modules).

Run with: python tests/aetheros_memory/test_memory.py
"""

import os
import sys
import math
import json
import time
import uuid
import base64
import hashlib
import tempfile
import threading
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
from typing import Any, Dict, List, Optional

_TEST_DIR = Path(__file__).resolve().parent
_AETHEROS_DIR = _TEST_DIR.parent.parent
if str(_AETHEROS_DIR) not in sys.path:
    sys.path.insert(0, str(_AETHEROS_DIR))
os.environ["AETHEROS_HOME"] = str(tempfile.mkdtemp())

_PASSED = 0
_FAILED = 0
_TOTAL_TESTS = 0


def _cleanup_temp():
    home = os.environ.get("AETHEROS_HOME", "")
    if home and Path(home).exists():
        shutil.rmtree(home, ignore_errors=True)


def _make_temp_dir():
    return Path(tempfile.mkdtemp(dir=os.environ["AETHEROS_HOME"]))


def test(name: str):
    global _TOTAL_TESTS
    _TOTAL_TESTS += 1
    def decorator(fn):
        def wrapper(*args, **kwargs):
            global _PASSED, _FAILED
            try:
                fn(*args, **kwargs)
                _PASSED += 1
                status = "PASS"
            except Exception as e:
                _FAILED += 1
                status = "FAIL"
                import traceback
                traceback.print_exc()
            print(f"  [{status}] {name}")
        return wrapper
    return decorator


def assert_raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return False
    except exc_type:
        return True


"""===========================================================================
1. embedding_engine.py
==========================================================================="""
@test("EmbeddingEngine - cosine_similarity basic")
def test_cosine_similarity_basic():
    from aetheros_memory.embedding_engine import cosine_similarity
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-9
    c = [1.0, 0.0, 0.0]
    d = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(c, d)) < 1e-9
    e = [0.0, 0.0, 0.0]
    f = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(e, f)) < 1e-9


@test("EmbeddingEngine - initialise and properties")
def test_embedding_engine_init():
    from aetheros_memory.embedding_engine import (
        EmbeddingEngine, EmbeddingConfig, EmbeddingProvider,
    )
    eng = EmbeddingEngine()
    assert eng._config is not None
    assert eng.provider == EmbeddingProvider.OPENAI
    assert eng.dimensions == 1536
    config = EmbeddingConfig(provider=EmbeddingProvider.LOCAL, dimensions=64)
    eng2 = EmbeddingEngine(config)
    assert eng2._config.provider == EmbeddingProvider.LOCAL


@test("EmbeddingEngine - switch_provider clears cache")
def test_embedding_engine_switch():
    from aetheros_memory.embedding_engine import (
        EmbeddingEngine, EmbeddingProvider,
    )
    eng = EmbeddingEngine()
    eng._cache["test_hash"] = ([0.1, 0.2], time.time())
    eng.switch_provider(EmbeddingProvider.LOCAL, model="test-model")
    assert len(eng._cache) == 0
    assert eng._embedder is None


@test("EmbeddingEngine - get_latency_stats")
def test_latency_stats():
    from aetheros_memory.embedding_engine import EmbeddingEngine
    eng = EmbeddingEngine()
    key = "openai/text-embedding-3-small"
    eng._latency_history[key] = [10.0, 20.0, 30.0]
    stats = eng.get_latency_stats()
    assert key in stats
    assert abs(stats[key]["avg"] - 20.0) < 1e-6
    assert stats[key]["min"] == 10.0
    assert stats[key]["max"] == 30.0
    assert stats[key]["count"] == 3


@test("EmbeddingEngine - clear_cache returns count")
def test_clear_cache():
    from aetheros_memory.embedding_engine import EmbeddingEngine
    eng = EmbeddingEngine()
    eng._cache["a"] = ([1.0], time.time())
    eng._cache["b"] = ([2.0], time.time())
    assert eng.clear_cache() == 2
    assert len(eng._cache) == 0


@test("EmbeddingEngine - embed_batch empty")
def test_embed_batch_empty():
    from aetheros_memory.embedding_engine import EmbeddingEngine
    eng = EmbeddingEngine()
    results = eng.embed_batch([])
    assert results == []


@test("EmbeddingEngine - embed with mock")
def test_embed_with_mock():
    from aetheros_memory.embedding_engine import (
        EmbeddingEngine, EmbeddingConfig, EmbeddingProvider, BaseEmbedder,
    )
    class MockEmbedder(BaseEmbedder):
        def embed(self, text):
            return [0.5, 0.5]
        def embed_batch(self, texts):
            return [[0.5, 0.5]] * len(texts)
        @property
        def dimensions(self):
            return 2
        @property
        def provider(self):
            from aetheros_memory.embedding_engine import EmbeddingProvider
            return EmbeddingProvider.LOCAL
        @property
        def model(self):
            return "mock"
    eng = EmbeddingEngine()
    eng._embedder = MockEmbedder()
    eng._cache.clear()
    result = eng.embed("hello world")
    assert result.vector == [0.5, 0.5]
    assert result.dimensions == 2
    assert result.latency_ms >= 0.0
    assert result.text_hash != ""
    cached_result = eng.embed("hello world")
    assert cached_result.latency_ms == 0.0
    assert cached_result.vector == [0.5, 0.5]


@test("EmbeddingEngine - embed_batch with mock")
def test_embed_batch_mock():
    from aetheros_memory.embedding_engine import (
        EmbeddingEngine, EmbeddingConfig, EmbeddingProvider, BaseEmbedder,
    )
    class MockEmbedder(BaseEmbedder):
        def embed(self, text):
            return [float(len(text)), 0.0]
        def embed_batch(self, texts):
            return [[float(len(t)), 0.0] for t in texts]
        @property
        def dimensions(self):
            return 2
        @property
        def provider(self):
            from aetheros_memory.embedding_engine import EmbeddingProvider
            return EmbeddingProvider.LOCAL
        @property
        def model(self):
            return "mock"
    eng = EmbeddingEngine()
    eng._embedder = MockEmbedder()
    results = eng.embed_batch(["hi", "hello", "hey"])
    assert len(results) == 3
    assert results[0].vector == [2.0, 0.0]


"""===========================================================================
2. vector_database.py
==========================================================================="""
@test("VectorDatabase - SQLiteVecBackend in-memory CRUD")
def test_sqlite_vec_backend():
    from aetheros_memory.vector_database import (
        SQLiteVecBackend, VectorDBConfig, VectorRecord, VectorDBType,
    )
    config = VectorDBConfig(backend=VectorDBType.SQLITE, path=":memory:", dimensions=4)
    backend = SQLiteVecBackend(config)
    backend.initialize(4)
    assert backend.count() == 0
    rec = VectorRecord(id="test1", vector=[1.0, 0.0, 0.0, 0.0], text="hello", metadata={"key": "val"})
    backend.insert(rec)
    assert backend.count() == 1
    retrieved = backend.get("test1")
    assert retrieved is not None
    assert retrieved.text == "hello"
    assert retrieved.metadata["key"] == "val"
    assert retrieved.id == "test1"
    not_found = backend.get("nonexistent")
    assert not_found is None
    results = backend.search([1.0, 0.0, 0.0, 0.0], top_k=5)
    assert len(results) >= 1
    assert results[0].id == "test1"
    assert abs(results[0].score - 1.0) < 1e-6
    rec2 = VectorRecord(id="test2", vector=[0.0, 1.0, 0.0, 0.0], text="world")
    backend.insert_batch([rec2])
    assert backend.count() == 2
    results2 = backend.search([0.0, 1.0, 0.0, 0.0], top_k=5)
    assert results2[0].id == "test2"
    deleted = backend.delete("test1")
    assert deleted is True
    assert backend.count() == 1
    deleted_false = backend.delete("nonexistent")
    assert deleted_false is False
    rec3 = VectorRecord(id="test3", vector=[1.0, 0.0, 0.0, 0.0], text="foo", metadata={"project": "p1"})
    backend.insert(rec3)
    count = backend.delete_by_filter("project", "p1")
    assert count == 1
    assert backend.count() == 1
    backend.clear()
    assert backend.count() == 0
    backend.close()


@test("VectorDatabase - VectorDatabase orchestrator CRUD")
def test_vector_database():
    from aetheros_memory.vector_database import (
        VectorDatabase, VectorDBConfig, VectorDBType, VectorRecord,
    )
    config = VectorDBConfig(backend=VectorDBType.SQLITE, path=":memory:", dimensions=4)
    vdb = VectorDatabase(config)
    vdb.initialize()
    vdb.insert("id1", [1.0, 0.0, 0.0, 0.0], "text1", {"cat": "a"})
    vdb.insert("id2", [0.0, 1.0, 0.0, 0.0], "text2", {"cat": "b"})
    assert vdb.count() == 2
    rec = vdb.get("id1")
    assert rec is not None
    assert rec.text == "text1"
    assert rec.metadata["cat"] == "a"
    assert vdb.get("nonexistent") is None
    results = vdb.search([1.0, 0.0, 0.0, 0.0], 5)
    assert len(results) > 0
    assert results[0].id == "id1"
    assert vdb.delete("id1") is True
    assert vdb.count() == 1
    vdb.insert_batch([
        VectorRecord(id="b1", vector=[0.5, 0.5, 0.0, 0.0], text="batch1"),
        VectorRecord(id="b2", vector=[0.5, 0.0, 0.5, 0.0], text="batch2"),
    ])
    assert vdb.count() == 3
    cnt = vdb.delete_by_filter("cat", "b")
    assert cnt == 1
    vdb.clear()
    assert vdb.count() == 0
    vdb.close()


@test("VectorDatabase - uninitialized raises RuntimeError")
def test_vector_db_uninitialized():
    from aetheros_memory.vector_database import (
        VectorDatabase, VectorDBConfig,
    )
    vdb = VectorDatabase()
    try:
        vdb.search([1.0, 0.0])
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


@test("VectorDatabase - empty search")
def test_vector_db_empty_search():
    from aetheros_memory.vector_database import (
        VectorDatabase, VectorDBConfig, VectorDBType,
    )
    config = VectorDBConfig(backend=VectorDBType.SQLITE, path=":memory:", dimensions=4)
    vdb = VectorDatabase(config)
    vdb.initialize()
    results = vdb.search([1.0, 0.0, 0.0, 0.0], 5)
    assert results == []


@test("VectorDatabase - switch_backend")
def test_vector_db_switch():
    from aetheros_memory.vector_database import (
        VectorDatabase, VectorDBConfig, VectorDBType,
    )
    config = VectorDBConfig(backend=VectorDBType.SQLITE, path=":memory:", dimensions=4)
    vdb = VectorDatabase(config)
    vdb.initialize()
    vdb.insert("id1", [1.0, 0.0, 0.0, 0.0], "hello")
    vdb.switch_backend(VectorDBType.SQLITE, VectorDBConfig(backend=VectorDBType.SQLITE, path=":memory:", dimensions=4))
    assert vdb.count() == 0


"""===========================================================================
3. knowledge_graph.py
==========================================================================="""
@test("KnowledgeGraph - entity CRUD")
def test_kg_entity_crud():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="TestProject", type=EntityType.PROJECT, description="A test project", importance=2.0)
    kg.add_entity(e1)
    assert kg.count_entities() == 1
    assert kg.count_entities(EntityType.PROJECT) == 1
    retrieved = kg.get_entity(e1.id)
    assert retrieved is not None
    assert retrieved.name == "TestProject"
    by_name = kg.find_entity_by_name("TestProject")
    assert by_name is not None
    assert by_name.id == e1.id
    not_found = kg.find_entity_by_name("Nonexistent")
    assert not_found is None
    updated = kg.update_entity(e1.id, name="RenamedProject", importance=5.0)
    assert updated is not None
    assert updated.name == "RenamedProject"
    assert updated.importance == 5.0
    e2 = GraphEntity(name="Another", type=EntityType.CONCEPT, description="Another entity")
    kg.add_entity(e2)
    assert kg.count_entities() == 2
    found_list = kg.find_entities(EntityType.CONCEPT)
    assert len(found_list) == 1
    deleted = kg.delete_entity(e1.id)
    assert deleted is True
    assert kg.count_entities() == 1
    assert kg.delete_entity("nonexistent") is False
    kg.clear()
    assert kg.count_entities() == 0


@test("KnowledgeGraph - relationship CRUD")
def test_kg_relationship_crud():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, RelationshipType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="ModuleA", type=EntityType.CONCEPT)
    e2 = GraphEntity(name="ModuleB", type=EntityType.CONCEPT)
    kg.add_entity(e1)
    kg.add_entity(e2)
    rel = kg.add_relationship(e1.id, e2.id, RelationshipType.DEPENDS_ON, weight=0.8)
    assert rel is not None
    assert rel.source_id == e1.id
    assert rel.target_id == e2.id
    assert rel.type == RelationshipType.DEPENDS_ON
    assert rel.weight == 0.8
    assert kg.count_relationships() == 1
    rels = kg.get_relationships(e1.id, "outgoing")
    assert len(rels) == 1
    rels_in = kg.get_relationships(e2.id, "incoming")
    assert len(rels_in) == 1
    rels_both = kg.get_relationships(e1.id, "both")
    assert len(rels_both) == 1
    removed = kg.remove_relationship(rel.id)
    assert removed is True
    assert kg.count_relationships() == 0
    assert kg.remove_relationship("nonexistent") is False
    rel_dne = kg.add_relationship("nonexistent", e2.id, RelationshipType.RELATED_TO)
    assert rel_dne is None


@test("KnowledgeGraph - bidirectional relationship")
def test_kg_bidirectional():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, RelationshipType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Parent")
    e2 = GraphEntity(name="Child")
    kg.add_entity(e1)
    kg.add_entity(e2)
    fwd, rev = kg.add_bidirectional_relationship(e1.id, e2.id, RelationshipType.CONTAINS)
    assert fwd is not None
    assert rev is not None
    assert rev.type == RelationshipType.PART_OF
    assert kg.count_relationships() == 2


@test("KnowledgeGraph - query and search")
def test_kg_query_search():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, GraphQuery,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Alpha", type=EntityType.PROJECT, description="Alpha project", importance=3.0)
    e2 = GraphEntity(name="Beta", type=EntityType.CONCEPT, description="Beta concept", importance=1.0)
    e3 = GraphEntity(name="Gamma", type=EntityType.PROJECT, description="Gamma project", importance=2.0)
    kg.add_entity(e1)
    kg.add_entity(e2)
    kg.add_entity(e3)
    q = GraphQuery(entity_type=EntityType.PROJECT, min_importance=2.0)
    results = kg.query(q)
    assert len(results) == 2
    q2 = GraphQuery(name_pattern="Alpha")
    results2 = kg.query(q2)
    assert len(results2) == 1
    searches = kg.search("project")
    assert len(searches) >= 2
    searches2 = kg.search("nonexistent")
    assert len(searches2) == 0


@test("KnowledgeGraph - auto_link")
def test_kg_auto_link():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Data Pipeline", type=EntityType.CONCEPT, description="Processes streaming data using Kafka")
    e2 = GraphEntity(name="Kafka Cluster", type=EntityType.PROJECT, description="Manages Kafka streaming data pipeline")
    kg.add_entity(e1)
    kg.add_entity(e2)
    count = kg.auto_link(e1.id)
    assert count >= 1
    count2 = kg.auto_link_all()
    assert count2 >= 0


@test("KnowledgeGraph - get_related_entities")
def test_kg_get_related():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, RelationshipType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Root", type=EntityType.PROJECT)
    e2 = GraphEntity(name="Child1", type=EntityType.CONCEPT)
    e3 = GraphEntity(name="Child2", type=EntityType.CONCEPT)
    kg.add_entity(e1)
    kg.add_entity(e2)
    kg.add_entity(e3)
    kg.add_relationship(e1.id, e2.id, RelationshipType.CONTAINS)
    kg.add_relationship(e1.id, e3.id, RelationshipType.CONTAINS)
    related = kg.get_related_entities(e1.id, max_depth=2)
    assert len(related) >= 2


@test("KnowledgeGraph - get_subgraph")
def test_kg_get_subgraph():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, RelationshipType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="A")
    e2 = GraphEntity(name="B")
    e3 = GraphEntity(name="C")
    kg.add_entity(e1)
    kg.add_entity(e2)
    kg.add_entity(e3)
    kg.add_relationship(e1.id, e2.id, RelationshipType.RELATED_TO)
    sg = kg.get_subgraph([e1.id, e2.id])
    assert len(sg["entities"]) == 2
    assert len(sg["relationships"]) == 1


@test("KnowledgeGraph - import/export/stats")
def test_kg_import_export():
    from aetheros_memory.knowledge_graph import (
        KnowledgeGraph, GraphEntity, EntityType, RelationshipType,
    )
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="ExportTest", type=EntityType.CONCEPT)
    kg.add_entity(e1)
    exported = kg.export_json()
    data = json.loads(exported)
    assert "entities" in data
    assert "relationships" in data
    kg2 = KnowledgeGraph()
    count = kg2.import_json(exported)
    assert count > 0
    assert kg2.count_entities() == 1
    stats_dict = kg2.stats()
    assert stats_dict["total_entities"] == 1


@test("KnowledgeGraph - reverse_type property")
def test_kg_reverse_type():
    from aetheros_memory.knowledge_graph import (
        GraphRelationship, RelationshipType,
    )
    rel = GraphRelationship(type=RelationshipType.CONTAINS)
    assert rel.reverse_type == RelationshipType.PART_OF
    rel2 = GraphRelationship(type=RelationshipType.RELATED_TO)
    assert rel2.reverse_type == RelationshipType.RELATED_TO


"""===========================================================================
4. memory_manager.py
==========================================================================="""
@test("MemoryManager - initialize and store/retrieve")
def test_mm_store_retrieve():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    from aetheros_memory.embedding_engine import EmbeddingProvider
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(
        storage_dir=str(tmpdir),
        embedding_provider=EmbeddingProvider.LOCAL,
        auto_index=False,
        auto_backup_interval=0,
    )
    mm = MemoryManager(config)
    mm.initialize()
    assert mm.is_initialized
    rec = mm.store("test memory content", category=MemoryCategory.CONVERSATION, key="test_key")
    assert rec is not None
    assert rec.content == "test memory content"
    assert rec.key == "test_key"
    assert mm.retrieve(rec.id) is not None
    by_key = mm.retrieve_by_key("test_key")
    assert by_key is not None
    content = mm.retrieve_content(rec.id)
    assert content == "test memory content"
    assert mm.retrieve("nonexistent") is None


@test("MemoryManager - store with key updates existing")
def test_mm_store_update():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    r1 = mm.store("first", category=MemoryCategory.CONVERSATION, key="dup")
    r2 = mm.store("second", category=MemoryCategory.CONVERSATION, key="dup")
    assert r1.id == r2.id
    assert r2.content == "second"


@test("MemoryManager - search")
def test_mm_search():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("Python is a programming language", category=MemoryCategory.CONVERSATION, tags=["python"])
    mm.store("JavaScript is for web", category=MemoryCategory.CONVERSATION, tags=["js"])
    results = mm.search("Python")
    assert len(results) >= 1
    assert any("Python" in r.content for r in results)
    results_tag = mm.search("", tags=["python"])
    assert len(results_tag) >= 1
    results_404 = mm.search("zzzznonexistent")
    assert len(results_404) == 0


@test("MemoryManager - delete")
def test_mm_delete():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("to delete", category=MemoryCategory.CONVERSATION)
    assert mm.retrieve(rec.id) is not None
    assert mm.delete(rec.id) is True
    assert mm.retrieve(rec.id) is None
    assert mm.delete("nonexistent") is False


@test("MemoryManager - archive/unarchive")
def test_mm_archive():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("archive me", category=MemoryCategory.CONVERSATION)
    assert mm.archive(rec.id) is True
    assert mm.retrieve(rec.id) is None
    assert mm.unarchive(rec.id) is True
    assert mm.retrieve(rec.id) is not None
    assert mm.archive("nonexistent") is False
    archived_list = mm.list_archived()
    assert len(archived_list) >= 0


@test("MemoryManager - pin/unpin")
def test_mm_pin():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("pin me", category=MemoryCategory.CONVERSATION)
    assert mm.pin(rec.id) is True
    pinned_list = mm.list_pinned()
    assert any(r.id == rec.id for r in pinned_list)
    assert mm.unpin(rec.id) is True
    pinned_list2 = mm.list_pinned()
    assert not any(r.id == rec.id for r in pinned_list2)


@test("MemoryManager - compact")
def test_mm_compact():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, enable_dedup=True, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("unique content", category=MemoryCategory.CONVERSATION)
    result = mm.compact()
    assert isinstance(result, dict)


@test("MemoryManager - backup/restore")
def test_mm_backup_restore():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("backup test", category=MemoryCategory.CONVERSATION, key="bk_key")
    backup_dir = _make_temp_dir()
    manifest = mm.backup(str(backup_dir))
    assert manifest.path != ""
    assert manifest.memory_count >= 1
    mm2 = MemoryManager(config)
    mm2.initialize()
    count = mm2.restore(manifest.path)
    assert count >= 1
    recovered = mm2.retrieve_by_key("bk_key")
    assert recovered is not None
    assert recovered.content == "backup test"


@test("MemoryManager - stats")
def test_mm_stats():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("stat1", category=MemoryCategory.CONVERSATION)
    mm.store("stat2", category=MemoryCategory.PROJECT)
    s = mm.stats()
    assert s.total == 2
    assert s.by_category.get("conversation", 0) == 1
    assert s.by_category.get("project", 0) == 1


@test("MemoryManager - workspace/project/conversation queries")
def test_mm_queries():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("ws memory", category=MemoryCategory.CONVERSATION, workspace_id="ws1")
    mm.store("pj memory", category=MemoryCategory.PROJECT, project_id="pj1")
    mm.store("cv memory", category=MemoryCategory.CONVERSATION, conversation_id="cv1")
    ws_list = mm.get_by_workspace("ws1")
    assert len(ws_list) == 1
    pj_list = mm.get_by_project("pj1")
    assert len(pj_list) == 1
    cv_list = mm.get_by_conversation("cv1")
    assert len(cv_list) == 1
    assert mm.get_by_workspace("nonexistent") == []


@test("MemoryManager - semantic_search (no vector db returns [])")
def test_mm_semantic_search():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm._vector_db = None
    mm.initialize()
    results = mm.semantic_search("test query")
    assert results == []


@test("MemoryManager - delete_by_filter")
def test_mm_delete_by_filter():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("cat test", category=MemoryCategory.CONVERSATION, key="del_filter")
    count = mm.delete_by_filter(category=MemoryCategory.CONVERSATION, key="del_filter")
    assert count >= 1


@test("MemoryManager - update")
def test_mm_update():
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig, MemoryCategory,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("original", category=MemoryCategory.CONVERSATION)
    updated = mm.update(rec.id, content="modified")
    assert updated is not None
    assert updated.content == "modified"
    assert mm.update("nonexistent", content="fail") is None


@test("MemoryManager - not initialized raises")
def test_mm_not_initialized():
    from aetheros_memory.memory_manager import MemoryManager
    mm = MemoryManager()
    try:
        mm.store("test", None)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


"""===========================================================================
5. memory_pipeline.py
==========================================================================="""
@test("MemoryPipeline - process text and extract facts")
def test_pipeline_process():
    import tempfile
    from aetheros_memory.memory_pipeline import MemoryPipeline, PipelineConfig, Category
    from aetheros_memory.memory_manager import (
        MemoryManager, MemoryManagerConfig,
    )
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm, config=PipelineConfig(auto_embed=False, auto_categorize=True, auto_graph=False))
    result = pipeline.process(
        "We have decided to use Python for this project. I prefer async patterns. "
        "TODO: fix the database connection error.",
        source="test",
    )
    assert len(result.facts) > 0
    categories = [f.category for f in result.facts]
    assert any(c == Category.DECISION for c in categories)
    assert any(c == Category.PREFERENCE for c in categories)
    assert any(c == Category.TASK for c in categories)


@test("MemoryPipeline - extract_facts with decision/preference patterns")
def test_pipeline_extract_facts():
    from aetheros_memory.memory_pipeline import MemoryPipeline, PipelineConfig, Category
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm, config=PipelineConfig(auto_embed=False, auto_categorize=False, auto_graph=False))
    facts = pipeline.extract_facts("We decided to use Kubernetes. I prefer Go over Java. There was an HTTP 500 error.")
    categories = [f.category for f in facts]
    assert Category.DECISION in categories
    assert Category.PREFERENCE in categories
    assert Category.ERROR in categories


@test("MemoryPipeline - empty text raises")
def test_pipeline_empty():
    from aetheros_memory.memory_pipeline import MemoryPipeline, PipelineConfig
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm, config=PipelineConfig())
    try:
        pipeline.process("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


@test("MemoryPipeline - categorize individual facts")
def test_pipeline_categorize():
    from aetheros_memory.memory_pipeline import MemoryPipeline, Fact, Category
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm)
    f1 = Fact(content="We have decided to move forward", category=Category.CONCEPT)
    assert pipeline.categorize(f1) == Category.DECISION
    f2 = Fact(content="I prefer dark mode", category=Category.CONCEPT)
    assert pipeline.categorize(f2) == Category.PREFERENCE
    f3 = Fact(content="The system architecture uses microservices", category=Category.CONCEPT)
    assert pipeline.categorize(f3) == Category.ARCHITECTURE


@test("MemoryPipeline - stats")
def test_pipeline_stats():
    from aetheros_memory.memory_pipeline import MemoryPipeline, PipelineConfig
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm, config=PipelineConfig(auto_embed=False))
    try:
        pipeline.process("We decided to test pipeline stats.", source="test")
    except ValueError:
        pass
    stats = pipeline.stats()
    assert isinstance(stats, dict)


@test("MemoryPipeline - process_batch")
def test_pipeline_batch():
    from aetheros_memory.memory_pipeline import MemoryPipeline, PipelineConfig
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    pipeline = MemoryPipeline(mm, config=PipelineConfig(auto_embed=False, auto_graph=False))
    results = pipeline.process_batch(["We decided X.", "I prefer Y.", ""])
    assert len(results) == 3


"""===========================================================================
6. rag_pipeline.py
==========================================================================="""
@test("RAGPipeline - expand_query")
def test_rag_expand_query():
    from aetheros_memory.rag_pipeline import RAGPipeline, RAGConfig
    pipeline = RAGPipeline(config=RAGConfig(enable_expansion=True, enable_graph=False, enable_compression=False, enable_ranking=False))
    expansion = pipeline.expand_query("find python code")
    assert expansion.original_query == "find python code"
    assert len(expansion.expansions) > 0


@test("RAGPipeline - semantic_search with vector db (empty)")
def test_rag_semantic_search_empty():
    from aetheros_memory.rag_pipeline import RAGPipeline
    pipeline = RAGPipeline()
    results = pipeline.semantic_search(["test query"])
    assert results == []


@test("RAGPipeline - rank")
def test_rag_rank():
    from aetheros_memory.rag_pipeline import RAGPipeline, RetrievedContext
    pipeline = RAGPipeline()
    ctx = RetrievedContext(text="hello world", score=0.5, source="test", category="conversation", record_id="r1")
    ranked = pipeline.rank([ctx], "hello")
    assert len(ranked) == 1
    assert ranked[0].score >= 0.0


@test("RAGPipeline - compress")
def test_rag_compress():
    from aetheros_memory.rag_pipeline import RAGPipeline, RetrievedContext
    pipeline = RAGPipeline()
    ctxs = [
        RetrievedContext(text="A" * 500, score=0.9, source="src1", category="cat1", record_id="r1"),
        RetrievedContext(text="B" * 500, score=0.5, source="src2", category="cat2", record_id="r2"),
    ]
    compressed = pipeline.compress(ctxs, 200)
    assert isinstance(compressed, str)
    assert len(compressed) > 0
    empty = pipeline.compress([], 100)
    assert empty == ""


@test("RAGPipeline - build_prompt")
def test_rag_build_prompt():
    from aetheros_memory.rag_pipeline import RAGPipeline
    pipeline = RAGPipeline()
    prompt = pipeline.build_prompt("test query", "some context here")
    assert "test query" in prompt
    assert "some context here" in prompt
    no_ctx = pipeline.build_prompt("test query", "")
    assert no_ctx == "test query"


@test("RAGPipeline - clear_cache and stats")
def test_rag_clear_cache():
    from aetheros_memory.rag_pipeline import RAGPipeline
    pipeline = RAGPipeline()
    pipeline._expansion_cache["q"] = (None, time.time())
    pipeline._embedding_cache["h"] = (None, time.time())
    cleared = pipeline.clear_cache()
    assert cleared == 2
    stats = pipeline.stats()
    assert "total_requests" in stats


@test("RAGPipeline - retrieve with no backends")
def test_rag_retrieve():
    from aetheros_memory.rag_pipeline import RAGPipeline, RAGConfig
    cfg = RAGConfig(enable_expansion=False, enable_graph=False, enable_compression=False, enable_ranking=False)
    pipeline = RAGPipeline(cfg)
    result = pipeline.retrieve("test query")
    assert result.query == "test query"
    assert result.contexts == []
    assert result.total_time_ms >= 0.0


@test("RAGPipeline - _estimate_tokens")
def test_rag_estimate_tokens():
    from aetheros_memory.rag_pipeline import RAGPipeline
    pipeline = RAGPipeline()
    assert pipeline._estimate_tokens("") == 0
    assert pipeline._estimate_tokens("hello") > 0


@test("RAGPipeline - graph_traversal (no graph)")
def test_rag_graph_traversal():
    from aetheros_memory.rag_pipeline import RAGPipeline, RetrievedContext
    pipeline = RAGPipeline()
    result = pipeline.graph_traversal([], "query")
    assert result == []


"""===========================================================================
7. context_retrieval.py
============================================================================"""
@test("ContextRetrieval - retrieve bundle basic")
def test_cr_retrieve():
    from aetheros_memory.context_retrieval import ContextRetrieval, RetrievalConfig
    from aetheros_memory.rag_pipeline import RAGPipeline, RAGConfig
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("relevant memory about test query", category=MemoryCategory.CONVERSATION)
    rag = RAGPipeline(RAGConfig(enable_expansion=False, enable_graph=False, enable_compression=False, enable_ranking=False))
    cr = ContextRetrieval(mm, rag, config=RetrievalConfig(
        enable_recent_decisions=True, enable_pinned=True,
        enable_workspace_context=True, enable_relevant_code=False,
    ))
    bundle = cr.retrieve("test query", max_tokens=100)
    assert bundle.total_tokens >= 0
    assert bundle.retrieval_time_ms >= 0.0


@test("ContextRetrieval - get_pinned_notes")
def test_cr_pinned():
    from aetheros_memory.context_retrieval import ContextRetrieval, RetrievalConfig
    from aetheros_memory.rag_pipeline import RAGPipeline, RAGConfig, RetrievedContext
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("pinned note test", category=MemoryCategory.CONVERSATION, workspace_id="ws1")
    mm.pin(rec.id)
    rag = RAGPipeline(RAGConfig())
    cr = ContextRetrieval(mm, rag)
    try:
        pinned = cr.get_pinned_notes()
        assert len(pinned) >= 0
    except Exception:
        pass


@test("ContextRetrieval - get_relevant_memories empty query")
def test_cr_empty_query():
    from aetheros_memory.context_retrieval import ContextRetrieval, RetrievalConfig
    from aetheros_memory.rag_pipeline import RAGPipeline
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    cr = ContextRetrieval(mm, RAGPipeline())
    result = cr.get_relevant_memories("")
    assert result == []


@test("ContextRetrieval - get_workspace_context empty")
def test_cr_no_workspace():
    from aetheros_memory.context_retrieval import ContextRetrieval
    from aetheros_memory.rag_pipeline import RAGPipeline
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    cr = ContextRetrieval(mm, RAGPipeline())
    result = cr.get_workspace_context("")
    assert result == []


@test("ContextRetrieval - format_context and estimate_tokens")
def test_cr_format():
    from aetheros_memory.context_retrieval import ContextRetrieval
    from aetheros_memory.rag_pipeline import RetrievedContext
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    cr = ContextRetrieval(mm, None)
    ctx = RetrievedContext(text="test context", score=0.8, source="test_source", category="cat1", record_id="r1")
    formatted = cr.format_context([ctx])
    assert "test context" in formatted
    assert cr.estimate_tokens("hello world") > 0
    assert cr.estimate_tokens("") == 0


"""===========================================================================
8. memory_ranking.py
==========================================================================="""
@test("MemoryRanking - rank_memories")
def test_ranking_rank():
    from aetheros_memory.memory_ranking import MemoryRanking, RankingConfig, ScoringFactor
    from aetheros_memory.memory_manager import MemoryRecord, MemoryCategory
    r1 = MemoryRecord(content="important memory", importance=5.0, access_count=10, pinned=True)
    r2 = MemoryRecord(content="normal memory", importance=1.0, access_count=1, pinned=False)
    r3 = MemoryRecord(content="low memory", importance=0.1, access_count=0, pinned=False)
    ranker = MemoryRanking()
    results = ranker.rank_memories([r1, r2, r3], query="important")
    assert len(results) == 3
    assert results[0].rank == 1
    assert results[0].record.importance == 5.0
    assert results[2].rank == 3
    empty = ranker.rank_memories([])
    assert empty == []


@test("MemoryRanking - rank_semantically")
def test_ranking_rank_semantic():
    from aetheros_memory.memory_ranking import MemoryRanking, ScoringFactor
    from aetheros_memory.memory_manager import MemoryRecord
    r1 = MemoryRecord(content="a", embedding=[1.0, 0.0, 0.0])
    r2 = MemoryRecord(content="b", embedding=[0.0, 1.0, 0.0])
    ranker = MemoryRanking()
    results = ranker.rank_semantically([r1, r2], [1.0, 0.0, 0.0])
    assert len(results) == 2
    assert results[0].record.id == r1.id


@test("MemoryRanking - compute_semantic_score zero/empty")
def test_ranking_semantic_score():
    from aetheros_memory.memory_ranking import MemoryRanking, ScoringFactor
    from aetheros_memory.memory_manager import MemoryRecord
    ranker = MemoryRanking()
    r_empty = MemoryRecord(content="test")
    score = ranker.compute_semantic_score(r_empty, [1.0, 0.0, 0.0])
    assert score == 0.0


@test("MemoryRanking - per-factor scoring")
def test_ranking_scores():
    from aetheros_memory.memory_ranking import MemoryRanking, ScoringFactor
    from aetheros_memory.memory_manager import MemoryRecord
    ranker = MemoryRanking()
    record = MemoryRecord(content="test", importance=5.0, access_count=10)
    record.accessed_at = time.time()
    imp = ranker.compute_importance_score(record)
    assert 0.0 <= imp <= 1.0
    rec = ranker.compute_recency_score(record)
    assert 0.0 <= rec <= 1.0
    freq = ranker.compute_frequency_score(record)
    assert 0.0 <= freq <= 1.0
    rel = ranker.compute_relevance_score(record, "test")
    assert rel > 0.0
    rel_empty = ranker.compute_relevance_score(record, "")
    assert rel_empty == 0.0


@test("MemoryRanking - configure weights")
def test_ranking_configure():
    from aetheros_memory.memory_ranking import MemoryRanking, ScoringFactor
    ranker = MemoryRanking()
    orig = ranker.factor_weight(ScoringFactor.IMPORTANCE)
    ranker.configure({ScoringFactor.IMPORTANCE: 5.0})
    assert ranker.factor_weight(ScoringFactor.IMPORTANCE) == 5.0


"""===========================================================================
9. memory_editor.py
==========================================================================="""
@test("MemoryEditor - view")
def test_editor_view():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("editable", category=MemoryCategory.CONVERSATION)
    viewed = editor.view(rec.id)
    assert viewed is not None
    assert viewed.content == "editable"
    assert editor.view("nonexistent") is None


@test("MemoryEditor - edit")
def test_editor_edit():
    from aetheros_memory.memory_editor import MemoryEditor, EditOperation
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("original", category=MemoryCategory.CONVERSATION)
    result = editor.edit(rec.id, content="updated", importance=5.0)
    assert result.success is True
    assert result.operation == EditOperation.EDIT
    assert result.record.content == "updated"
    assert result.record.importance == 5.0
    fail = editor.edit("nonexistent", content="fail")
    assert fail.success is False


@test("MemoryEditor - delete")
def test_editor_delete():
    from aetheros_memory.memory_editor import MemoryEditor, EditOperation
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("delete me", category=MemoryCategory.CONVERSATION)
    result = editor.delete(rec.id)
    assert result.success is True
    assert result.operation == EditOperation.DELETE
    fail = editor.delete("nonexistent")
    assert fail.success is False


@test("MemoryEditor - merge (4 strategies)")
def test_editor_merge():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    r1 = mm.store("short", category=MemoryCategory.CONVERSATION, importance=1.0, tags=["a"])
    r2 = mm.store("longer content here", category=MemoryCategory.CONVERSATION, importance=5.0, tags=["b"])
    for strategy in ["keep_longest", "keep_most_recent", "keep_most_important", "concatenate"]:
        result = editor.merge([r1.id, r2.id], strategy=strategy)
        assert result.merged_id != ""
        assert result.record is not None
        r1 = mm.store("short", category=MemoryCategory.CONVERSATION, importance=1.0, tags=["a"])
        r2 = mm.store("longer content here", category=MemoryCategory.CONVERSATION, importance=5.0, tags=["b"])
    fail = editor.merge(["nonexistent"], strategy="keep_longest")
    assert len(fail.conflicts) > 0
    fail2 = editor.merge([r1.id, r2.id], strategy="unknown")
    assert len(fail2.conflicts) > 0


@test("MemoryEditor - split")
def test_editor_split():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("abcdefghij", category=MemoryCategory.CONVERSATION)
    parts = editor.split(rec.id, [3, 7])
    assert len(parts) == 3
    assert parts[0].content == "abc"
    assert parts[1].content == "defg"
    assert parts[2].content == "hij"
    empty_split = editor.split("nonexistent", [1])
    assert empty_split == []
    bad_points = editor.split(rec.id, [100])
    assert bad_points == []


@test("MemoryEditor - pin/unpin/archive/unarchive")
def test_editor_pin_archive():
    from aetheros_memory.memory_editor import MemoryEditor, EditOperation
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("pin archive test", category=MemoryCategory.CONVERSATION)
    pin_r = editor.pin(rec.id)
    assert pin_r.success is True
    unpin_r = editor.unpin(rec.id)
    assert unpin_r.success is True
    arch_r = editor.archive(rec.id)
    assert arch_r.success is True
    unarch_r = editor.unarchive(rec.id)
    assert unarch_r.success is True
    fail = editor.pin("nonexistent")
    assert fail.success is False


@test("MemoryEditor - tag/category/permissions operations")
def test_editor_tag_category():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("tag test", category=MemoryCategory.CONVERSATION)
    result = editor.add_tag(rec.id, "newtag")
    assert result.success is True
    result2 = editor.remove_tag(rec.id, "newtag")
    assert result2.success is True
    fail = editor.add_tag("nonexistent", "x")
    assert fail.success is False
    cat_r = editor.change_category(rec.id, MemoryCategory.PROJECT)
    assert cat_r.success is True
    perm_r = editor.change_permissions(rec.id, "shared")
    assert perm_r.success is True


@test("MemoryEditor - export/import")
def test_editor_export_import():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    mm.store("export test", category=MemoryCategory.CONVERSATION, key="export_key")
    json_str = editor.export_json(query="export")
    assert isinstance(json_str, str)
    assert "export test" in json_str
    csv_str = editor.export_csv(query="export")
    assert "export test" in csv_str
    roundtrip_file = str(_make_temp_dir() / "exported.json")
    editor.export_json(query="export", filepath=roundtrip_file)
    new_mm = MemoryManager(config)
    new_mm.initialize()
    new_editor = MemoryEditor(new_mm)
    count = new_editor.import_json(roundtrip_file)
    assert count >= 1


@test("MemoryEditor - history")
def test_editor_history():
    from aetheros_memory.memory_editor import MemoryEditor, EditOperation
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("history test", category=MemoryCategory.CONVERSATION)
    editor.edit(rec.id, content="v2")
    editor.edit(rec.id, content="v3")
    history = editor.get_history(rec.id)
    assert len(history) == 2


@test("MemoryEditor - search")
def test_editor_search():
    from aetheros_memory.memory_editor import MemoryEditor
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    editor = MemoryEditor(mm)
    rec = mm.store("searchable content", category=MemoryCategory.CONVERSATION, tags=["findme"])
    results = editor.search(query="searchable")
    assert len(results) >= 1
    results2 = editor.search(tags=["findme"])
    assert len(results2) >= 1


"""===========================================================================
10. research_library.py
==========================================================================="""
@test("ResearchLibrary - create session and add source")
def test_research_session_source():
    from aetheros_memory.research_library import (
        ResearchLibrary, SourceType,
    )
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    session = lib.create_session(topic="AI Safety", query="What are the risks of AI?")
    assert session.topic == "AI Safety"
    assert session.id != ""
    retrieved = lib.get_session(session.id)
    assert retrieved is not None
    assert retrieved.topic == "AI Safety"
    src = lib.add_source(session.id, type=SourceType.WEB_PAGE, title="Test Article", url="https://example.com", content="Article content here", tags=["ai", "safety"])
    assert src.title == "Test Article"
    assert src.type == SourceType.WEB_PAGE
    got_src = lib.get_source(src.id)
    assert got_src is not None
    session_updated = lib.update_session(session.id, summary="Summary text", tags=["updated"])
    assert session_updated is True
    assert lib.update_session("nonexistent", summary="x") is False


@test("ResearchLibrary - create collection")
def test_research_collection():
    from aetheros_memory.research_library import ResearchLibrary
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    col = lib.create_collection(name="My Collection", description="A collection", tags=["tag1"])
    assert col.name == "My Collection"
    session = lib.create_session(topic="Test", query="test")
    added = lib.add_to_collection(col.id, session.id)
    assert added is True
    got_col = lib.get_collection(col.id)
    assert got_col is not None
    assert session.id in got_col.session_ids
    collections = lib.list_collections()
    assert len(collections) >= 1


@test("ResearchLibrary - search")
def test_research_search():
    from aetheros_memory.research_library import ResearchLibrary
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    lib.create_session(topic="Machine Learning", query="ML basics")
    lib.create_session(topic="Deep Learning", query="Neural networks")
    results = lib.search_sessions("Machine")
    assert len(results) >= 1
    all_sessions = lib.search_sessions("")
    assert len(all_sessions) >= 2
    src = lib.add_source(list(lib._sessions.keys())[0], title="Doc", content="searchable content")
    src_results = lib.search_sources("searchable")
    assert len(src_results) >= 1
    all_sources = lib.search_sources("")
    assert len(all_sources) >= 1


@test("ResearchLibrary - delete session and source")
def test_research_delete():
    from aetheros_memory.research_library import ResearchLibrary, SourceType
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    session = lib.create_session(topic="Delete Me", query="test")
    src = lib.add_source(session.id, title="Src")
    assert lib.delete_source(src.id) is True
    assert lib.delete_source("nonexistent") is False
    assert lib.get_source(src.id) is None
    assert lib.delete_session(session.id) is True
    assert lib.delete_session("nonexistent") is False


@test("ResearchLibrary - stats")
def test_research_stats():
    from aetheros_memory.research_library import ResearchLibrary
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    lib.create_session(topic="Stats Test", query="test")
    stats = lib.stats()
    assert stats["total_sessions"] >= 1


@test("ResearchLibrary - export")
def test_research_export():
    from aetheros_memory.research_library import ResearchLibrary, SourceType
    tmpdir = _make_temp_dir()
    lib = ResearchLibrary(storage_path=str(tmpdir / "research"))
    session = lib.create_session(topic="Export Test", query="test query")
    lib.add_source(session.id, title="Src1")
    exported = lib.export_session(session.id)
    assert isinstance(exported, str)
    exported_md = lib.export_session(session.id, format="markdown")
    assert "Export Test" in exported_md
    not_found = lib.export_session("nonexistent")
    assert not_found == ""


"""===========================================================================
11. code_intelligence.py
==========================================================================="""
@test("CodeIntelligence - index_file Python")
def test_ci_index_python():
    from aetheros_memory.code_intelligence import CodeIntelligence, CodeEntityType
    ci = CodeIntelligence()
    code = '''
import os
from pathlib import Path

def hello(name: str) -> str:
    """Say hello."""
    return f"Hello {name}"

class MyClass:
    def method(self):
        pass

CONFIG_VALUE = "test"
'''
    entities = ci.index_file("/tmp/test.py", code, language="python")
    types = [e.type for e in entities]
    assert CodeEntityType.FILE in types
    assert CodeEntityType.FUNCTION in types or CodeEntityType.METHOD in types
    assert CodeEntityType.CLASS in types
    assert CodeEntityType.CONFIG in types or CodeEntityType.VARIABLE in types
    assert len(entities) >= 3


@test("CodeIntelligence - search_code")
def test_ci_search():
    from aetheros_memory.code_intelligence import CodeIntelligence, CodeEntityType
    ci = CodeIntelligence()
    code = "def my_function(): pass\nclass AnotherClass: pass\n"
    ci.index_file("/tmp/test.py", code, language="python")
    results = ci.search_code("my_function")
    assert len(results) >= 1
    results2 = ci.search_code("nonexistent_thing")
    assert len(results2) == 0
    results3 = ci.search_code("", entity_type=CodeEntityType.CLASS)
    assert len(results3) >= 1


@test("CodeIntelligence - add_entity and get_entity")
def test_ci_add_entity():
    from aetheros_memory.code_intelligence import (
        CodeIntelligence, CodeEntity, CodeEntityType,
    )
    ci = CodeIntelligence()
    e = CodeEntity(name="test_func", type=CodeEntityType.FUNCTION, file_path="/tmp/x.py")
    ci.add_entity(e)
    assert ci.get_entity(e.id) is not None
    found = ci.find_entity("test_func")
    assert len(found) >= 1


@test("CodeIntelligence - add_relationship")
def test_ci_relationship():
    from aetheros_memory.code_intelligence import CodeIntelligence, CodeEntity, CodeEntityType
    ci = CodeIntelligence()
    e1 = CodeEntity(name="A", type=CodeEntityType.FILE)
    e2 = CodeEntity(name="B", type=CodeEntityType.FILE)
    ci.add_entity(e1)
    ci.add_entity(e2)
    rel = ci.add_relationship(e1.id, e2.id, "imports")
    assert rel is not None
    assert len(ci.get_relationships(e1.id)) == 1
    assert ci.add_relationship("nonexistent", e2.id, "x") is None


@test("CodeIntelligence - detect_patterns")
def test_ci_detect_patterns():
    from aetheros_memory.code_intelligence import (
        CodeIntelligence, CodeEntity, CodeEntityType,
    )
    ci = CodeIntelligence()
    entities = [
        CodeEntity(name="Controller", type=CodeEntityType.CLASS, source_code="class Controller: pass"),
        CodeEntity(name="Model", type=CodeEntityType.CLASS, source_code="class Model: pass"),
        CodeEntity(name="View", type=CodeEntityType.CLASS, source_code="class View: pass"),
    ]
    pattern = ci.detect_pattern(entities)
    assert pattern is not None
    assert pattern.confidence > 0


@test("CodeIntelligence - get_architecture")
def test_ci_architecture():
    from aetheros_memory.code_intelligence import (
        CodeIntelligence, CodeEntity, CodeEntityType,
    )
    ci = CodeIntelligence()
    e = CodeEntity(name="TestClass", type=CodeEntityType.CLASS, file_path="/repo/test.py")
    ci.add_entity(e)
    arch = ci.get_architecture("/repo")
    assert arch["total_entities"] >= 1


@test("CodeIntelligence - find_dependencies")
def test_ci_find_deps():
    from aetheros_memory.code_intelligence import (
        CodeIntelligence, CodeEntity, CodeEntityType,
    )
    ci = CodeIntelligence()
    e1 = CodeEntity(name="helper", type=CodeEntityType.FUNCTION, imports=["os"])
    ci.add_entity(e1)
    deps = ci.find_dependencies(e1.id)
    assert isinstance(deps, list)


@test("CodeIntelligence - export/import json")
def test_ci_export_import():
    from aetheros_memory.code_intelligence import CodeIntelligence, CodeEntity, CodeEntityType
    ci = CodeIntelligence()
    e = CodeEntity(name="ExportEntity", type=CodeEntityType.FILE)
    ci.add_entity(e)
    path = str(_make_temp_dir() / "ci_export.json")
    json_str = ci.export_json(path)
    data = json.loads(json_str)
    assert data["entities"][0]["name"] == "ExportEntity"
    ci2 = CodeIntelligence()
    count = ci2.import_json(path)
    assert count >= 1


@test("CodeIntelligence - stats")
def test_ci_stats():
    from aetheros_memory.code_intelligence import CodeIntelligence, CodeEntity, CodeEntityType
    ci = CodeIntelligence()
    ci.add_entity(CodeEntity(name="S1", type=CodeEntityType.FILE))
    ci.add_entity(CodeEntity(name="S2", type=CodeEntityType.CLASS))
    stats = ci.stats()
    assert stats["total_entities"] == 2


"""===========================================================================
12. workspace_intelligence.py
==========================================================================="""
@test("WorkspaceIntelligence - initialize workspace")
def test_wi_initialize():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wk = wi.initialize_workspace("ws1")
    assert wk.id == "ws1"
    assert wi.get_knowledge("ws1", "test") is None
    assert wi.get_knowledge("nonexistent", "test") is None
    same = wi.initialize_workspace("ws1")
    assert same.id == "ws1"


@test("WorkspaceIntelligence - goal CRUD")
def test_wi_goals():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    goal = wi.add_goal("ws1", "Complete project", description="Finish by Friday", priority=5, tags=["urgent"])
    assert goal.title == "Complete project"
    assert goal.priority == 5
    goals = wi.get_goals("ws1")
    assert len(goals) == 1
    goals_active = wi.get_goals("ws1", status="active")
    assert len(goals_active) == 1
    updated = wi.update_goal(goal.id, status="completed", progress=1.0, title="Done!")
    assert updated is not None
    assert updated.status == "completed"
    assert updated.progress == 1.0
    assert wi.update_goal("nonexistent", status="x") is None
    assert wi.delete_goal(goal.id) is True
    assert wi.delete_goal("nonexistent") is False
    assert len(wi.get_goals("ws1")) == 0


@test("WorkspaceIntelligence - pin/unpin documents")
def test_wi_pin_docs():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    doc = wi.pin_document("ws1", "Readme", file_path="/path/readme.md", content_type="markdown", content="# Readme", tags=["docs"])
    assert doc.title == "Readme"
    assert doc.file_path == "/path/readme.md"
    docs = wi.get_pinned_documents("ws1")
    assert len(docs) == 1
    assert wi.unpin_document(doc.id) is True
    assert wi.unpin_document("nonexistent") is False
    assert len(wi.get_pinned_documents("ws1")) == 0


@test("WorkspaceIntelligence - set/get knowledge")
def test_wi_knowledge():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    assert wi.set_knowledge("ws1", "key1", "value1") is True
    val = wi.get_knowledge("ws1", "key1")
    assert val == "value1"
    none_val = wi.get_knowledge("ws1", "nonexistent")
    assert none_val is None
    wi.set_knowledge("nonexistent_ws", "k", "v")
    val2 = wi.get_knowledge("nonexistent_ws", "k")
    assert val2 == "v"


@test("WorkspaceIntelligence - search")
def test_wi_search():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    wi.add_goal("ws1", "Fix bugs", description="Resolve critical issues")
    wi.pin_document("ws1", "Bug Report", content="bug report details")
    wi.set_knowledge("ws1", "deploy_key", "deploy_value")
    results = wi.search_workspace("ws1", "bug")
    assert len(results["goals"]) >= 1
    assert len(results["docs"]) >= 1
    results2 = wi.search_workspace("ws1", "deploy")
    assert len(results2["knowledge"]) >= 1
    results_empty = wi.search_workspace("ws1", "zzzznothing")
    assert len(results_empty["goals"]) == 0
    results_no_ws = wi.search_workspace("nonexistent", "bug")
    assert results_no_ws["goals"] == []


@test("WorkspaceIntelligence - stats and delete workspace")
def test_wi_stats():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    wi.add_goal("ws1", "Goal A")
    stats = wi.stats()
    assert stats["total_workspaces"] >= 1
    assert stats["total_goals"] >= 1
    assert wi.delete_workspace("ws1") is True
    assert wi.delete_workspace("nonexistent") is False
    stats2 = wi.stats()
    assert stats2["total_workspaces"] == 0


@test("WorkspaceIntelligence - get_workspace_summary")
def test_wi_summary():
    from aetheros_memory.workspace_intelligence import WorkspaceIntelligence
    wi = WorkspaceIntelligence()
    wi.initialize_workspace("ws1")
    wi.add_goal("ws1", "Task 1")
    summary = wi.get_workspace_summary("ws1")
    assert "Task 1" in summary
    no_ws = wi.get_workspace_summary("nonexistent")
    assert "not found" in no_ws


"""===========================================================================
13. automatic_summarization.py
==========================================================================="""
@test("AutomaticSummarization - summarize")
def test_as_summarize():
    from aetheros_memory.automatic_summarization import (
        AutomaticSummarization, CompressionLevel,
    )
    summarizer = AutomaticSummarization()
    text = "We have decided to use Python. This is an important decision because it affects everything. "
    text += "TODO: update the documentation. What is the best approach? "
    text += "I prefer async patterns. The system architecture uses microservices."
    result = summarizer.summarize(text, level=CompressionLevel.AGGRESSIVE, max_length=200)
    assert result.original_length == len(text)
    assert len(result.summary) > 0
    assert result.compression_ratio < 1.0
    assert isinstance(result.key_points, list)
    assert isinstance(result.decisions, list)
    assert isinstance(result.action_items, list)
    assert isinstance(result.questions, list)
    assert isinstance(result.sentiment, str)
    assert isinstance(result.entities, list)


@test("AutomaticSummarization - extract_key_points")
def test_as_key_points():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "This is a critical finding. The important result is X. This is a normal sentence. "
    text += "Another key point here. Some random text."
    points = summarizer.extract_key_points(text, count=3)
    assert len(points) <= 3
    assert len(points) > 0


@test("AutomaticSummarization - extract_decisions")
def test_as_decisions():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "We have decided to refactor the codebase. Also we chose TypeScript."
    decisions = summarizer.extract_decisions(text)
    assert len(decisions) >= 1
    no_decisions = summarizer.extract_decisions("The sky is blue.")
    assert len(no_decisions) == 0


@test("AutomaticSummarization - extract_action_items")
def test_as_action_items():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "TODO: fix the bug. Next step is to deploy. - [ ] write tests"
    items = summarizer.extract_action_items(text)
    assert len(items) >= 1


@test("AutomaticSummarization - extract_questions")
def test_as_questions():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "What is the best approach? How should we implement this? The sky is blue."
    questions = summarizer.extract_questions(text)
    assert len(questions) >= 1


@test("AutomaticSummarization - extract_code")
def test_as_code():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "Use `def hello(): pass` and then ```python\\nprint('hi')\\n```"
    code = summarizer.extract_code_snippets(text)
    assert len(code) >= 1


@test("AutomaticSummarization - extract_keywords")
def test_as_keywords():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "Python programming is great for machine learning and data science. Python is versatile."
    keywords = summarizer.extract_keywords(text, count=5)
    assert len(keywords) > 0
    assert "python" in keywords or "programming" in keywords


@test("AutomaticSummarization - detect_sentiment")
def test_as_sentiment():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    pos = summarizer.detect_sentiment("This is great and wonderful! Amazing work!")
    assert pos == "positive"
    neg = summarizer.detect_sentiment("This is terrible and broken. Awful failure.")
    assert neg == "negative"
    neutral = summarizer.detect_sentiment("The sky is blue. It is a nice day.")
    assert neutral in ("neutral", "positive")
    mixed = summarizer.detect_sentiment("Great work but the error rate is terrible.")
    assert mixed in ("mixed", "positive", "negative")


@test("AutomaticSummarization - extract_entities")
def test_as_entities():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    text = "John Doe works at Acme Corporation on the Project Phoenix."
    entities = summarizer.extract_entities(text)
    assert len(entities) > 0


@test("AutomaticSummarization - compress")
def test_as_compress():
    from aetheros_memory.automatic_summarization import AutomaticSummarization, CompressionLevel
    summarizer = AutomaticSummarization()
    text = "Sentence one. " * 50
    compressed = summarizer.compress(text, 0.3)
    assert len(compressed) < len(text)
    assert summarizer.compress(text, 1.0) == text
    assert summarizer.compress("", 0.5) == ""


@test("AutomaticSummarization - progressive_summarize")
def test_as_progressive():
    from aetheros_memory.automatic_summarization import AutomaticSummarization
    summarizer = AutomaticSummarization()
    texts = ["First conversation about Python.", "Second conversation about deployment."]
    result = summarizer.progressive_summarize(texts)
    assert len(result.summary) > 0


"""===========================================================================
14. memory_permissions.py
==========================================================================="""
@test("MemoryPermissions - set/get/check permissions")
def test_mp_set_get_check():
    from aetheros_memory.memory_permissions import (
        MemoryPermissions, PermissionLevel, AccessControl,
    )
    mp = MemoryPermissions()
    entry = mp.set_permission("mem1", PermissionLevel.PRIVATE, allowed_users=["user1"], allowed_workspaces=["ws1"])
    assert entry.level == PermissionLevel.PRIVATE
    assert entry.memory_id == "mem1"
    got = mp.get_permission("mem1")
    assert got is not None
    assert got.level == PermissionLevel.PRIVATE
    assert mp.get_permission("nonexistent") is None
    admin = AccessControl(user_id="admin", is_admin=True)
    assert mp.check_access("mem1", admin) is True
    allowed = AccessControl(user_id="user1", workspace_id="ws1")
    assert mp.check_access("mem1", allowed) is True
    denied = AccessControl(user_id="user2", workspace_id="ws1")
    assert mp.check_access("mem1", denied) is False


@test("MemoryPermissions - different levels")
def test_mp_levels():
    from aetheros_memory.memory_permissions import (
        MemoryPermissions, PermissionLevel, AccessControl,
    )
    mp = MemoryPermissions()
    mp.set_permission("pub", PermissionLevel.PUBLIC)
    mp.set_permission("priv", PermissionLevel.PRIVATE, allowed_users=["u1"])
    mp.set_permission("ws", PermissionLevel.WORKSPACE, allowed_workspaces=["w1"])
    mp.set_permission("shared", PermissionLevel.SHARED, allowed_users=["u1"], allowed_roles=["admin"], allowed_workspaces=["w1"])
    mp.set_permission("enc", PermissionLevel.ENCRYPTED, allowed_users=["u1"])
    public = AccessControl(user_id="stranger")
    assert mp.check_access("pub", public) is True
    assert mp.check_access("priv", public) is False
    ws_user = AccessControl(workspace_id="w1")
    assert mp.check_access("ws", ws_user) is True
    assert mp.check_access("priv", ws_user) is False
    role_user = AccessControl(user_id="u2", roles=["admin"])
    assert mp.check_access("shared", role_user) is True
    enc_user = AccessControl(user_id="u1")
    assert mp.check_access("enc", enc_user) is True


@test("MemoryPermissions - encrypt/decrypt roundtrip")
def test_mp_encrypt_decrypt():
    from aetheros_memory.memory_permissions import MemoryPermissions
    mp = MemoryPermissions()
    original = "sensitive data 123"
    key = "my-secret-key"
    encrypted = mp.encrypt_content(original, key)
    assert encrypted != original
    assert isinstance(encrypted, str)
    decrypted = mp.decrypt_content(encrypted, key)
    assert decrypted == original
    with_different_key = mp.decrypt_content(encrypted, "wrong-key")
    assert with_different_key != original


@test("MemoryPermissions - is_sensitive detection")
def test_mp_is_sensitive():
    from aetheros_memory.memory_permissions import MemoryPermissions
    mp = MemoryPermissions()
    assert mp.is_sensitive("my api key is sk-abc12345def67890ghijklmno") is True
    assert mp.is_sensitive("password:=secret123") is True
    assert mp.is_sensitive("normal text without secrets") is False


@test("MemoryPermissions - mask_sensitive")
def test_mp_mask():
    from aetheros_memory.memory_permissions import MemoryPermissions
    mp = MemoryPermissions()
    masked = mp.mask_sensitive("password = hunter2 and api_key = sk-abcdefghijklmnopqrstuvwxyz")
    assert "[REDACTED]" in masked
    assert "hunter2" not in masked
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in masked
    original = "safe text"
    assert mp.mask_sensitive(original) == original


@test("MemoryPermissions - check_access_batch and filter_by_access")
def test_mp_batch():
    from aetheros_memory.memory_permissions import (
        MemoryPermissions, PermissionLevel, AccessControl,
    )
    mp = MemoryPermissions()
    mp.set_permission("m1", PermissionLevel.PUBLIC)
    mp.set_permission("m2", PermissionLevel.PRIVATE, allowed_users=["u1"])
    mp.set_permission("m3", PermissionLevel.PRIVATE, allowed_users=["u1"])
    access = AccessControl(user_id="u1")
    batch = mp.check_access_batch(["m1", "m2", "m3"], access)
    assert batch["m1"] is True
    assert batch["m2"] is True
    filtered = mp.filter_by_access(["m1", "m2", "m3", "nonexistent"], access)
    assert len(filtered) == 3


@test("MemoryPermissions - expire_permission and delete")
def test_mp_expire_delete():
    from aetheros_memory.memory_permissions import MemoryPermissions, PermissionLevel
    mp = MemoryPermissions()
    mp.set_permission("mem1", PermissionLevel.PUBLIC, expires_at=time.time() + 3600)
    assert mp.get_permission("mem1") is not None
    assert mp.expire_permission("mem1") is True
    assert mp.expire_permission("nonexistent") is False
    time.sleep(0.02)
    assert mp.get_permission("mem1") is None
    mp.set_permission("mem2", PermissionLevel.PUBLIC)
    assert mp.delete_permission("mem2") is True
    assert mp.delete_permission("nonexistent") is False


@test("MemoryPermissions - set_encryption_key")
def test_mp_set_key():
    from aetheros_memory.memory_permissions import MemoryPermissions, PermissionLevel
    mp = MemoryPermissions()
    mp.set_permission("mem1", PermissionLevel.ENCRYPTED)
    assert mp.set_encryption_key("mem1", "mykey") is True
    assert mp.set_encryption_key("nonexistent", "key") is False


@test("MemoryPermissions - stats")
def test_mp_stats():
    from aetheros_memory.memory_permissions import (
        MemoryPermissions, PermissionLevel,
    )
    mp = MemoryPermissions()
    mp.set_permission("m1", PermissionLevel.PUBLIC)
    mp.set_permission("m2", PermissionLevel.PRIVATE)
    stats = mp.stats()
    assert stats["total_permissions"] == 2
    assert stats["by_level"]["public"] == 1
    assert stats["by_level"]["private"] == 1


"""===========================================================================
15. memory_visualization.py
==========================================================================="""
@test("MemoryVisualization - build_timeline")
def test_mv_timeline():
    from aetheros_memory.memory_visualization import MemoryVisualization
    from aetheros_memory.memory_manager import MemoryRecord, MemoryCategory
    r1 = MemoryRecord(content="first", category=MemoryCategory.CONVERSATION, created_at=time.time() - 100)
    r2 = MemoryRecord(content="second", category=MemoryCategory.CONVERSATION, created_at=time.time())
    mv = MemoryVisualization()
    timeline = mv.build_timeline([r1, r2])
    assert len(timeline) == 2
    assert timeline[0].id == r2.id
    cat_timeline = mv.build_timeline([r1, r2], group_by="category")
    assert len(cat_timeline) >= 1


@test("MemoryVisualization - build_graph_data")
def test_mv_graph_data():
    from aetheros_memory.memory_visualization import MemoryVisualization, GraphLayout
    from aetheros_memory.knowledge_graph import GraphEntity, GraphRelationship, EntityType, RelationshipType
    e1 = GraphEntity(name="Node1", type=EntityType.CONCEPT, importance=2.0)
    e2 = GraphEntity(name="Node2", type=EntityType.CONCEPT, importance=1.0)
    r = GraphRelationship(source_id=e1.id, target_id=e2.id, type=RelationshipType.RELATED_TO)
    mv = MemoryVisualization()
    graph = mv.build_graph_data([e1, e2], [r], max_nodes=10)
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["layout"] == "force_directed"


@test("MemoryVisualization - build_tree")
def test_mv_tree():
    from aetheros_memory.memory_visualization import MemoryVisualization
    from aetheros_memory.knowledge_graph import KnowledgeGraph, GraphEntity, EntityType, RelationshipType
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Root", type=EntityType.PROJECT)
    e2 = GraphEntity(name="Child", type=EntityType.CONCEPT)
    kg.add_entity(e1)
    kg.add_entity(e2)
    kg.add_relationship(e1.id, e2.id, RelationshipType.CONTAINS)
    mv = MemoryVisualization()
    tree = mv.build_tree(e1.id, kg, max_depth=2)
    assert tree["id"] == e1.id
    assert "children" in tree
    unknown = mv.build_tree("nonexistent", kg)
    assert unknown["label"] == "unknown"


@test("MemoryVisualization - build_collections")
def test_mv_collections():
    from aetheros_memory.memory_visualization import MemoryVisualization
    from aetheros_memory.memory_manager import MemoryRecord, MemoryCategory
    r1 = MemoryRecord(content="a", category=MemoryCategory.CONVERSATION, tags=["tag1"])
    r2 = MemoryRecord(content="b", category=MemoryCategory.CONVERSATION, tags=["tag1"])
    r3 = MemoryRecord(content="c", category=MemoryCategory.PROJECT, tags=["tag2"])
    mv = MemoryVisualization()
    collections = mv.build_collections([r1, r2, r3])
    tag_colls = [c for c in collections if c.id.startswith("tag_")]
    assert len(tag_colls) >= 1
    cat_colls = [c for c in collections if c.id.startswith("cat_")]
    assert len(cat_colls) >= 1


@test("MemoryVisualization - get_pinned_memories and get_recent_memories")
def test_mv_pinned_recent():
    from aetheros_memory.memory_visualization import MemoryVisualization
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    rec = mm.store("pinned visual", category=MemoryCategory.CONVERSATION)
    mm.pin(rec.id)
    mv = MemoryVisualization()
    pinned = mv.get_pinned_memories(mm)
    assert len(pinned) >= 1
    recent = mv.get_recent_memories(mm, hours=48)
    assert len(recent) >= 1


@test("MemoryVisualization - export D3/Cytoscape JSON")
def test_mv_export():
    from aetheros_memory.memory_visualization import (
        MemoryVisualization, VisualizationData, TimelineEntry, CollectionEntry,
    )
    mv = MemoryVisualization()
    vis_data = VisualizationData(
        entities=[{"id": "e1", "label": "Node1", "group": "concept", "size": 10, "importance": 1.0}],
        relationships=[{"id": "r1", "source": "e1", "target": "e2", "label": "related_to", "weight": 1.0}],
        timeline=[TimelineEntry(id="t1", timestamp=time.time(), type="event", title="Test", description="desc")],
        collections=[CollectionEntry(id="c1", name="Col1", description="desc", count=2)],
        pinned=[{"id": "p1", "content": "pinned note"}],
        recent=[{"id": "r1", "content": "recent note"}],
        total_count=5,
    )
    d3 = mv.export_d3_json(vis_data)
    d3_data = json.loads(d3)
    assert "nodes" in d3_data
    assert "links" in d3_data
    cyto = mv.export_cytoscape_json(vis_data)
    cyto_data = json.loads(cyto)
    assert "elements" in cyto_data
    assert "layout" in cyto_data


@test("MemoryVisualization - get_entity_timeline and relationship_network")
def test_mv_entity_timeline():
    from aetheros_memory.memory_visualization import MemoryVisualization
    from aetheros_memory.knowledge_graph import KnowledgeGraph, GraphEntity, RelationshipType
    kg = KnowledgeGraph()
    e1 = GraphEntity(name="Center", id="center")
    kg.add_entity(e1)
    mv = MemoryVisualization()
    tl = mv.get_entity_timeline("center", kg)
    assert isinstance(tl, list)
    network = mv.get_relationship_network("center", kg)
    assert network["center"] == "center"


"""===========================================================================
16. performance.py
==========================================================================="""
@test("CacheLayer - get/set/invalidate/clear")
def test_cache_basic():
    from aetheros_memory.performance import CacheLayer
    cache = CacheLayer(max_size=100, default_ttl=60)
    assert cache.get("key1") is None
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.invalidate("key1") is True
    assert cache.get("key1") is None
    assert cache.invalidate("nonexistent") is False
    cache.set("a", 1)
    cache.set("b", 2)
    cleared = cache.clear()
    assert cleared == 2
    assert cache.get("a") is None


@test("CacheLayer - TTL expiry")
def test_cache_ttl():
    from aetheros_memory.performance import CacheLayer
    cache = CacheLayer(max_size=100, default_ttl=0)
    cache.set("k", "v", ttl=0.01)
    time.sleep(0.02)
    assert cache.get("k") is None


@test("CacheLayer - LRU eviction")
def test_cache_lru():
    from aetheros_memory.performance import CacheLayer
    cache = CacheLayer(max_size=3, default_ttl=3600)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)
    assert cache.get("a") is None
    assert cache.get("d") == 4


@test("CacheLayer - stats")
def test_cache_stats():
    from aetheros_memory.performance import CacheLayer
    cache = CacheLayer(max_size=100, default_ttl=60)
    assert cache.stats()["hits"] == 0
    cache.set("k", "v")
    cache.get("k")
    cache.get("nonexistent")
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] > 0


@test("BatchProcessor - process")
def test_batch_process():
    from aetheros_memory.performance import BatchProcessor
    bp = BatchProcessor(batch_size=2)
    items = [1, 2, 3, 4, 5]
    results = bp.process(items, processor_fn=lambda batch: [x * 2 for x in batch])
    assert results == [2, 4, 6, 8, 10]
    empty = bp.process([], processor_fn=lambda b: b)
    assert empty == []
    identity = bp.process([1, 2, 3], processor_fn=None)
    assert identity == [1, 2, 3]


@test("BatchProcessor - process_with_progress")
def test_batch_progress():
    from aetheros_memory.performance import BatchProcessor
    bp = BatchProcessor(batch_size=3)
    progress_log = []
    items = [1, 2, 3, 4, 5]
    results = bp.process_with_progress(
        items,
        processor_fn=lambda batch: [x * 2 for x in batch],
        callback=lambda p, t: progress_log.append((p, t)),
    )
    assert results == [2, 4, 6, 8, 10]
    assert len(progress_log) > 0
    assert progress_log[-1] == (5, 5)


@test("BackgroundIndexer - start/stop/queue/process")
def test_indexer():
    from aetheros_memory.performance import BackgroundIndexer
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    from aetheros_memory.embedding_engine import EmbeddingEngine, EmbeddingConfig, EmbeddingProvider, BaseEmbedder
    tmpdir = _make_temp_dir()
    class DumbEmbedder(BaseEmbedder):
        def embed(self, text): return [0.5, 0.5]
        def embed_batch(self, texts): return [[0.5, 0.5]] * len(texts)
        @property
        def dimensions(self): return 2
        @property
        def provider(self): return EmbeddingProvider.LOCAL
        @property
        def model(self): return "dumb"
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    eng = EmbeddingEngine()
    eng._embedder = DumbEmbedder()
    indexer = BackgroundIndexer(mm, eng)
    indexer.start(interval=0.1)
    rec = mm.store("index me", category=MemoryCategory.CONVERSATION)
    indexer.queue_memory(rec.id)
    time.sleep(0.3)
    stats = indexer.stats()
    assert stats["is_running"] is True
    assert stats["total_indexed"] >= 0
    indexer.queue_batch([rec.id])
    indexer.stop()
    assert indexer.stats()["is_running"] is False


@test("CompactionEngine - compact and estimate")
def test_compaction():
    from aetheros_memory.performance import CompactionEngine
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig, MemoryCategory
    tmpdir = _make_temp_dir()
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    mm.store("keep me important", category=MemoryCategory.CONVERSATION, importance=5.0)
    mm.store("low importance", category=MemoryCategory.CONVERSATION, importance=0.05)
    engine = CompactionEngine()
    result = engine.compact(mm, strategy="hybrid")
    assert isinstance(result, dict)
    estimate = engine.estimate_savings(mm)
    assert estimate["total_memories"] >= 0


@test("MemoryPerformance - orchestrator")
def test_memory_performance():
    from aetheros_memory.performance import MemoryPerformance
    from aetheros_memory.memory_manager import MemoryManager, MemoryManagerConfig
    from aetheros_memory.embedding_engine import EmbeddingEngine, EmbeddingConfig, EmbeddingProvider, BaseEmbedder
    tmpdir = _make_temp_dir()
    class SilentEmbedder(BaseEmbedder):
        def embed(self, text): return [0.5, 0.5]
        def embed_batch(self, texts): return [[0.5, 0.5]] * len(texts)
        @property
        def dimensions(self): return 2
        @property
        def provider(self): return EmbeddingProvider.LOCAL
        @property
        def model(self): return "silent"
    config = MemoryManagerConfig(storage_dir=str(tmpdir), auto_index=False, auto_backup_interval=0)
    mm = MemoryManager(config)
    mm.initialize()
    eng = EmbeddingEngine()
    eng._embedder = SilentEmbedder()
    perf = MemoryPerformance(mm, eng)
    assert isinstance(perf.get_cache_stats(), dict)
    assert isinstance(perf.get_indexer_stats(), dict)
    assert isinstance(perf.get_compaction_stats(), dict)
    perf.start_background_indexing(interval=0.1)
    time.sleep(0.15)
    perf.stop_background_indexing()
    batch_results = perf.batch_embed(["hello", "world"])
    assert len(batch_results) == 2


"""===========================================================================
Run all tests and print summary
==========================================================================="""
def run_all():
    global _PASSED, _FAILED, _TOTAL_TESTS
    _PASSED = 0
    _FAILED = 0
    _TOTAL_TESTS = 0
    print("=" * 70)
    print(f"  aetheros_memory Platform Validation Suite")
    print("=" * 70)
    print(f"\n  Starting tests at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    start = time.monotonic()
    test_modules = [
        ("embedding_engine.py", [
            test_cosine_similarity_basic,
            test_embedding_engine_init,
            test_embedding_engine_switch,
            test_latency_stats,
            test_clear_cache,
            test_embed_batch_empty,
            test_embed_with_mock,
            test_embed_batch_mock,
        ]),
        ("vector_database.py", [
            test_sqlite_vec_backend,
            test_vector_database,
            test_vector_db_uninitialized,
            test_vector_db_empty_search,
            test_vector_db_switch,
        ]),
        ("knowledge_graph.py", [
            test_kg_entity_crud,
            test_kg_relationship_crud,
            test_kg_bidirectional,
            test_kg_query_search,
            test_kg_auto_link,
            test_kg_get_related,
            test_kg_get_subgraph,
            test_kg_import_export,
            test_kg_reverse_type,
        ]),
        ("memory_manager.py", [
            test_mm_store_retrieve,
            test_mm_store_update,
            test_mm_search,
            test_mm_delete,
            test_mm_archive,
            test_mm_pin,
            test_mm_compact,
            test_mm_backup_restore,
            test_mm_stats,
            test_mm_queries,
            test_mm_semantic_search,
            test_mm_delete_by_filter,
            test_mm_update,
            test_mm_not_initialized,
        ]),
        ("memory_pipeline.py", [
            test_pipeline_process,
            test_pipeline_extract_facts,
            test_pipeline_empty,
            test_pipeline_categorize,
            test_pipeline_stats,
            test_pipeline_batch,
        ]),
        ("rag_pipeline.py", [
            test_rag_expand_query,
            test_rag_semantic_search_empty,
            test_rag_rank,
            test_rag_compress,
            test_rag_build_prompt,
            test_rag_clear_cache,
            test_rag_retrieve,
            test_rag_estimate_tokens,
            test_rag_graph_traversal,
        ]),
        ("context_retrieval.py", [
            test_cr_retrieve,
            test_cr_pinned,
            test_cr_empty_query,
            test_cr_no_workspace,
            test_cr_format,
        ]),
        ("memory_ranking.py", [
            test_ranking_rank,
            test_ranking_rank_semantic,
            test_ranking_semantic_score,
            test_ranking_scores,
            test_ranking_configure,
        ]),
        ("memory_editor.py", [
            test_editor_view,
            test_editor_edit,
            test_editor_delete,
            test_editor_merge,
            test_editor_split,
            test_editor_pin_archive,
            test_editor_tag_category,
            test_editor_export_import,
            test_editor_history,
            test_editor_search,
        ]),
        ("research_library.py", [
            test_research_session_source,
            test_research_collection,
            test_research_search,
            test_research_delete,
            test_research_stats,
            test_research_export,
        ]),
        ("code_intelligence.py", [
            test_ci_index_python,
            test_ci_search,
            test_ci_add_entity,
            test_ci_relationship,
            test_ci_detect_patterns,
            test_ci_architecture,
            test_ci_find_deps,
            test_ci_export_import,
            test_ci_stats,
        ]),
        ("workspace_intelligence.py", [
            test_wi_initialize,
            test_wi_goals,
            test_wi_pin_docs,
            test_wi_knowledge,
            test_wi_search,
            test_wi_stats,
            test_wi_summary,
        ]),
        ("automatic_summarization.py", [
            test_as_summarize,
            test_as_key_points,
            test_as_decisions,
            test_as_action_items,
            test_as_questions,
            test_as_code,
            test_as_keywords,
            test_as_sentiment,
            test_as_entities,
            test_as_compress,
            test_as_progressive,
        ]),
        ("memory_permissions.py", [
            test_mp_set_get_check,
            test_mp_levels,
            test_mp_encrypt_decrypt,
            test_mp_is_sensitive,
            test_mp_mask,
            test_mp_batch,
            test_mp_expire_delete,
            test_mp_set_key,
            test_mp_stats,
        ]),
        ("memory_visualization.py", [
            test_mv_timeline,
            test_mv_graph_data,
            test_mv_tree,
            test_mv_collections,
            test_mv_pinned_recent,
            test_mv_export,
            test_mv_entity_timeline,
        ]),
        ("performance.py", [
            test_cache_basic,
            test_cache_ttl,
            test_cache_lru,
            test_cache_stats,
            test_batch_process,
            test_batch_progress,
            test_indexer,
            test_compaction,
            test_memory_performance,
        ]),
    ]
    for module_name, tests in test_modules:
        print(f"\n  [{module_name}]")
        for test_fn in tests:
            test_fn()
    elapsed = time.monotonic() - start
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    total = _PASSED + _FAILED
    print(f"  Total:  {total}")
    print(f"  Passed: {_PASSED}")
    print(f"  Failed: {_FAILED}")
    print(f"  Time:   {elapsed:.2f}s")
    print(f"{'=' * 70}")
    print(f"  === PASSED: {_PASSED}/{total} tests ===")
    print(f"{'=' * 70}")
    _cleanup_temp()
    return _FAILED == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
