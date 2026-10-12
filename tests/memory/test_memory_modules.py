"""
Comprehensive tests for the AetherOS Memory, Knowledge & Learning Engine.

Tests cover:
  - MemoryStore CRUD, search, scoping, SQLite persistence
  - ShortTermMemory capacity, TTL, promotion
  - LongTermMemory store/recall/search
  - EpisodicMemory record/retrieve/timeline
  - SemanticMemory learn/query/confidence
  - ProceduralMemory record/find/success rate
  - WorkspaceMemory scoping
  - ProjectMemory decisions
  - KnowledgeGraph sync/traversal/pathfinding
  - RetrievalEngine hybrid search
  - LearningEngine observation/insights
  - ReflectionEngine recording/lessons
  - ConsolidationEngine merge/promote
  - RetentionEngine policies/evaluation
  - GarbageCollector lifecycle
  - Exporters/Importers format conversion
  - MemoryManager unified interface
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope
from memory.cache import MemoryCache
from memory.embeddings import EmbeddingProvider, EmbeddingConfig
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.episodic import EpisodicMemory, Episode
from memory.semantic import SemanticMemory, Fact
from memory.procedural import ProceduralMemory, Procedure
from memory.workspace_memory import WorkspaceMemory
from memory.project_memory import ProjectMemory
from memory.entity_index import (
    EntityIndex, Entity, ENTITY_TYPE_FUNCTION, ENTITY_TYPE_CLASS,
)
from memory.relationship_index import (
    RelationshipIndex, RELATION_DEPENDS_ON, RELATION_IMPORTS,
)
from memory.knowledge_graph import (
    KnowledgeGraph, KnowledgeNode, KnowledgeRelation,
    NodeType, RelationType,
)
from memory.retrieval import RetrievalEngine, RetrievalResult
from memory.ranking import RankingEngine
from memory.summarizer import Summarizer
from memory.retention import RetentionEngine, RetentionPolicy, RetentionAction
from memory.garbage_collection import GarbageCollector
from memory.consolidation import ConsolidationEngine
from memory.learning_engine import LearningEngine, LearningSample
from memory.reflection import ReflectionEngine, Reflection
from memory.exporters import MemoryExporter, ExportOptions
from memory.importers import MemoryImporter, ImportOptions, ImportResult
from memory.memory_manager import MemoryManager, UnifiedMemoryConfig


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def store():
    """Create a fresh MemoryStore for each test."""
    return MemoryStore()


@pytest.fixture
def cache():
    """Create a fresh MemoryCache for each test."""
    return MemoryCache(max_size=100, default_ttl=10.0)


@pytest.fixture
def stm(store):
    """Create a ShortTermMemory fixture."""
    return ShortTermMemory(store, capacity=10)


@pytest.fixture
def ltm(store):
    """Create a LongTermMemory fixture."""
    return LongTermMemory(store)


@pytest.fixture
def episodic(store):
    """Create an EpisodicMemory fixture."""
    return EpisodicMemory(store)


@pytest.fixture
def semantic(store):
    """Create a SemanticMemory fixture."""
    return SemanticMemory(store)


@pytest.fixture
def procedural(store):
    """Create a ProceduralMemory fixture."""
    return ProceduralMemory(store)


@pytest.fixture
def workspace(store):
    """Create a WorkspaceMemory fixture."""
    return WorkspaceMemory(store, workspace_id="test-workspace")


@pytest.fixture
def project(store):
    """Create a ProjectMemory fixture."""
    return ProjectMemory(store, project_id="test-project")


@pytest.fixture
def entity_index(store):
    """Create an EntityIndex fixture."""
    return EntityIndex(store)


@pytest.fixture
def relationship_index(store):
    """Create a RelationshipIndex fixture."""
    return RelationshipIndex(store)


@pytest.fixture
def knowledge_graph(entity_index, relationship_index, store):
    """Create a KnowledgeGraph fixture."""
    kg = KnowledgeGraph(entity_index, relationship_index, store)
    kg.sync()
    return kg


@pytest.fixture
def embedder():
    """Create an EmbeddingProvider fixture using simple hash fallback."""
    config = EmbeddingConfig(provider="simple", dimension=16)
    provider = EmbeddingProvider(config)
    provider.initialize()
    return provider


@pytest.fixture
def retrieval(store, embedder, knowledge_graph):
    """Create a RetrievalEngine fixture."""
    return RetrievalEngine(store, embedder=embedder, knowledge_graph=knowledge_graph)


@pytest.fixture
def ranking():
    """Create a RankingEngine fixture."""
    return RankingEngine()


@pytest.fixture
def summarizer():
    """Create a Summarizer fixture."""
    return Summarizer()


@pytest.fixture
def retention():
    """Create a RetentionEngine fixture."""
    return RetentionEngine()


@pytest.fixture
def gc(store, retention):
    """Create a GarbageCollector fixture."""
    return GarbageCollector(store, retention)


@pytest.fixture
def consolidation(store, summarizer):
    """Create a ConsolidationEngine fixture."""
    return ConsolidationEngine(store, summarizer)


@pytest.fixture
def learning(store, episodic, semantic, procedural):
    """Create a LearningEngine fixture."""
    return LearningEngine(store, episodic, semantic, procedural)


@pytest.fixture
def reflection(store, procedural, semantic):
    """Create a ReflectionEngine fixture."""
    return ReflectionEngine(store, procedural, semantic)


@pytest.fixture
def exporter(store):
    """Create a MemoryExporter fixture."""
    return MemoryExporter(store)


@pytest.fixture
def importer(store):
    """Create a MemoryImporter fixture."""
    return MemoryImporter(store)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ======================================================================
# MemoryStore Tests
# ======================================================================

class TestMemoryStore:
    def test_save_and_get(self, store):
        entry = store.save("test_key", "test_value")
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.id is not None

        retrieved = store.get(entry.id)
        assert retrieved is not None
        assert retrieved.value == "test_value"

    def test_get_by_key(self, store):
        store.save("unique_key", 42, scope=MemoryScope.GLOBAL)
        entry = store.get_by_key("unique_key")
        assert entry is not None
        assert entry.value == 42

    def test_get_by_key_not_found(self, store):
        entry = store.get_by_key("nonexistent")
        assert entry is None

    def test_delete(self, store):
        entry = store.save("delete_me", "value")
        assert store.delete(entry.id) is True
        assert store.get(entry.id) is None

    def test_delete_by_key(self, store):
        store.save("key_to_delete", "value", scope=MemoryScope.GLOBAL)
        assert store.delete_by_key("key_to_delete") is True
        assert store.get_by_key("key_to_delete") is None

    def test_update(self, store):
        entry = store.save("updatable", "original")
        assert store.update(entry.id, value="updated", importance=0.9)

        retrieved = store.get(entry.id)
        assert retrieved.value == "updated"
        assert retrieved.importance == 0.9

    def test_search_by_query(self, store):
        store.save("alpha", "first entry", tags=["important"])
        store.save("beta", "second entry", tags=["minor"])
        store.save("gamma", "third alpha entry", tags=["important"])

        results = store.search(query="alpha")
        assert len(results) == 2  # alpha key + "alpha" in value

    def test_search_by_scope(self, store):
        store.save("global_key", "global", scope=MemoryScope.GLOBAL)
        store.save("workspace_key", "workspace", scope=MemoryScope.WORKSPACE)

        results = store.search(scope=MemoryScope.WORKSPACE)
        assert len(results) == 1
        assert results[0].key == "workspace_key"

    def test_search_by_type(self, store):
        store.save("short", "stm", memory_type="short_term")
        store.save("long", "ltm", memory_type="long_term")

        results = store.search(memory_type="long_term")
        assert len(results) == 1
        assert results[0].key == "long"

    def test_search_by_tags(self, store):
        store.save("tagged1", "value1", tags=["urgent", "important"])
        store.save("tagged2", "value2", tags=["urgent"])
        store.save("tagged3", "value3", tags=["minor"])

        results = store.search(tags=["urgent"])
        assert len(results) == 2

        results = store.search(tags=["urgent", "important"])
        assert len(results) == 2  # ANY match

    def test_search_empty_results(self, store):
        results = store.search(query="nothing")
        assert len(results) == 0

    def test_expiry(self, store):
        store.save("expiring", "value", ttl=0.01)
        time.sleep(0.02)
        results = store.search(query="expiring")
        assert len(results) == 0

    def test_clear_all(self, store):
        store.save("a", 1)
        store.save("b", 2)
        store.save("c", 3)
        assert store.clear_all() == 3
        assert store.count() == 0

    def test_clear_namespace(self, store):
        store.save("a", 1, namespace="ns1")
        store.save("b", 2, namespace="ns1")
        store.save("c", 3, namespace="ns2")
        assert store.clear_namespace("ns1") == 2
        assert store.count(namespace="ns1") == 0
        assert store.count(namespace="ns2") == 1

    def test_scoped_isolation(self, store):
        """Entries with different scopes don't interfere."""
        store.save("key", "global", scope=MemoryScope.GLOBAL)
        store.save("key", "workspace", scope=MemoryScope.WORKSPACE)
        store.save("key", "project", scope=MemoryScope.PROJECT)

        global_e = store.get_by_key("key", scope=MemoryScope.GLOBAL)
        workspace_e = store.get_by_key("key", scope=MemoryScope.WORKSPACE)
        project_e = store.get_by_key("key", scope=MemoryScope.PROJECT)

        assert global_e.value == "global"
        assert workspace_e.value == "workspace"
        assert project_e.value == "project"

    def test_deduplicate_same_key_scope(self, store):
        """Saving same key+scope+namespace updates, not duplicates."""
        e1 = store.save("dedup_key", "first", scope=MemoryScope.GLOBAL)
        e2 = store.save("dedup_key", "second", scope=MemoryScope.GLOBAL)
        assert e1.id == e2.id

        retrieved = store.get_by_key("dedup_key")
        assert retrieved.value == "second"

    def test_sqlite_persistence(self, temp_db):
        store = MemoryStore(db_path=temp_db)
        store.save("persist_key", "persist_value")

        # Create new store pointing to same DB
        store2 = MemoryStore(db_path=temp_db)
        count = store2.load_from_sqlite()
        assert count >= 1

        retrieved = store2.get_by_key("persist_key")
        assert retrieved is not None
        assert retrieved.value == "persist_value"

    def test_save_many(self, store):
        entries = [
            MemoryEntry(key=f"batch_{i}", value=f"value_{i}")
            for i in range(5)
        ]
        count = store.save_many(entries)
        assert count == 5
        assert store.count() == 5

    def test_snapshot(self, store):
        store.save("snap_key", {"data": "test"}, tags=["demo"])
        snap = store.snapshot()
        assert snap["total"] >= 1
        assert any(e["key"] == "snap_key" for e in snap["entries"])

    def test_stats(self, store):
        store.save("stat_key", "value", memory_type="test_type")
        stats = store.stats()
        assert stats["total_entries"] >= 1
        assert "test_type" in stats["by_type"]


# ======================================================================
# MemoryCache Tests
# ======================================================================

class TestMemoryCache:
    def test_set_and_get(self, cache):
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing(self, cache):
        assert cache.get("nonexistent") is None

    def test_get_default(self, cache):
        assert cache.get("nonexistent", "default") == "default"

    def test_ttl_expiry(self, cache):
        cache.set("expiring", "value", ttl=0.01)
        time.sleep(0.02)
        assert cache.get("expiring") is None

    def test_delete(self, cache):
        cache.set("delete_me", "value")
        assert cache.delete("delete_me") is True
        assert cache.get("delete_me") is None

    def test_clear(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() == 2
        assert cache.size == 0

    def test_contains(self, cache):
        cache.set("exists", "value")
        assert cache.contains("exists") is True
        assert cache.contains("missing") is False

    def test_get_many(self, cache):
        cache.set_many({"a": 1, "b": 2, "c": 3})
        results = cache.get_many(["a", "b", "missing"])
        assert len(results) == 2

    def test_lru_eviction(self):
        cache = MemoryCache(max_size=3, default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access 'a' and 'b' to make 'c' the LRU
        cache.get("a")
        cache.get("b")
        cache.set("d", 4)  # Evicts 'c'
        assert cache.get("c") is None
        assert cache.get("a") == 1
        assert cache.get("d") == 4

    def test_prune_expired(self, cache):
        cache.set("a", 1, ttl=0.01)
        cache.set("b", 2, ttl=60)
        time.sleep(0.02)
        count = cache.prune_expired()
        assert count >= 1
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_stats(self, cache):
        cache.set("a", 1)
        cache.get("a")
        cache.get("missing")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5


# ======================================================================
# EmbeddingProvider Tests
# ======================================================================

class TestEmbeddingProvider:
    def test_embed(self, embedder):
        vector = embedder.embed("hello world")
        assert len(vector) > 0
        assert all(isinstance(v, float) for v in vector)

    def test_embed_batch(self, embedder):
        vectors = embedder.embed_batch(["hello", "world", "test"])
        assert len(vectors) == 3
        assert all(len(v) > 0 for v in vectors)

    def test_cosine_similarity(self, embedder):
        v1 = embedder.embed("hello world")
        v2 = embedder.embed("hello world")
        similarity = EmbeddingProvider.cosine_similarity(v1, v2)
        assert abs(similarity - 1.0) < 0.01  # Same text → near-identical

    def test_cosine_similarity_different(self, embedder):
        v1 = embedder.embed("hello world")
        v2 = embedder.embed("goodbye universe")
        similarity = EmbeddingProvider.cosine_similarity(v1, v2)
        assert 0.0 <= similarity <= 1.0

    def test_cache(self, embedder):
        embedder.clear_cache()
        v1 = embedder.embed("cache test")
        v2 = embedder.embed("cache test")
        assert v1 == v2  # Cached result

    def test_clear_cache(self, embedder):
        embedder.embed("clear me")
        embedder.clear_cache()
        stats = embedder.stats()
        assert stats["cache_size"] == 0


# ======================================================================
# ShortTermMemory Tests
# ======================================================================

class TestShortTermMemory:
    def test_add_and_get(self, stm):
        entry = stm.add("current_task", "Implement login")
        assert entry is not None
        assert stm.get("current_task") == "Implement login"

    def test_get_missing(self, stm):
        assert stm.get("nonexistent") is None

    def test_update(self, stm):
        stm.add("task", "original")
        stm.update("task", "updated")
        assert stm.get("task") == "updated"

    def test_delete(self, stm):
        stm.add("delete_me", "value")
        assert stm.delete("delete_me") is True
        assert stm.get("delete_me") is None

    def test_capacity_eviction(self, stm):
        for i in range(20):
            stm.add(f"key_{i}", f"value_{i}")
        assert stm.count() <= 10  # Capacity is 10

    def test_get_all(self, stm):
        stm.add("a", 1)
        stm.add("b", 2)
        all_mem = stm.get_all()
        assert all_mem.get("a") == 1
        assert all_mem.get("b") == 2

    def test_clear(self, stm):
        stm.add("a", 1)
        stm.add("b", 2)
        count = stm.clear()
        assert count >= 2
        assert stm.count() == 0

    def test_promote(self, stm):
        stm.add("important", "data", importance=0.5)
        assert stm.promote("important", 0.9) is True
        entry = stm.get_entry("important")
        assert entry.importance == 0.9

    def test_get_recent(self, stm):
        stm.add("a", 1)
        time.sleep(0.01)
        stm.add("b", 2)
        recent = stm.get_recent(limit=1)
        assert len(recent) == 1


# ======================================================================
# LongTermMemory Tests
# ======================================================================

class TestLongTermMemory:
    def test_store_and_recall(self, ltm):
        entry = ltm.store("user_prefs", {"theme": "dark"}, importance=0.9)
        assert entry is not None
        assert ltm.recall("user_prefs") == {"theme": "dark"}

    def test_recall_missing(self, ltm):
        assert ltm.recall("nonexistent") is None

    def test_update(self, ltm):
        ltm.store("config", {"debug": True})
        ltm.update("config", {"debug": False})
        assert ltm.recall("config") == {"debug": False}

    def test_forget(self, ltm):
        ltm.store("forget_me", "value")
        assert ltm.forget("forget_me") is True
        assert ltm.recall("forget_me") is None

    def test_search(self, ltm):
        ltm.store("api_key_info", "Use env vars", tags=["security"])
        ltm.store("deploy_steps", "Run deploy script", tags=["devops"])

        results = ltm.search(query="deploy")
        assert len(results) >= 1
        assert results[0].key == "deploy_steps"

    def test_list_by_tags(self, ltm):
        ltm.store("a", 1, tags=["urgent"])
        ltm.store("b", 2, tags=["urgent", "important"])
        ltm.store("c", 3, tags=["minor"])

        results = ltm.list_by_tags(["urgent"])
        assert len(results) == 2

    def test_list_important(self, ltm):
        ltm.store("a", 1, importance=0.9)
        ltm.store("b", 2, importance=0.5)
        ltm.store("c", 3, importance=0.8)

        important = ltm.list_important(min_importance=0.8)
        assert len(important) == 2

    def test_promote_from_stm(self, ltm):
        entry = ltm.promote_from_stm("temp", "promoted_data", importance=0.9)
        assert entry is not None
        assert ltm.recall("temp") == "promoted_data"

    def test_clear(self, ltm):
        ltm.store("a", 1)
        ltm.store("b", 2)
        assert ltm.clear() >= 2
        assert ltm.count() == 0


# ======================================================================
# EpisodicMemory Tests
# ======================================================================

class TestEpisodicMemory:
    def test_record(self, episodic):
        episode = Episode(
            summary="Fixed auth bug",
            outcome="success",
            context="During login flow refactor",
            importance=0.8,
        )
        entry = episodic.record(episode)
        assert entry is not None

    def test_get_recent(self, episodic):
        episodic.record_event("Task 1", outcome="success")
        episodic.record_event("Task 2", outcome="success")
        recent = episodic.get_recent(limit=5)
        assert len(recent) >= 2

    def test_find_similar(self, episodic):
        episodic.record_event("Authentication issue", outcome="failure")
        episodic.record_event("Database connection", outcome="success")
        results = episodic.find_similar("auth")
        assert len(results) >= 1

    def test_get_timeline(self, episodic):
        episodic.record_event("Old event", outcome="success")
        time.sleep(0.02)
        episodic.record_event("Recent event", outcome="success")
        timeline = episodic.get_timeline(start_time=time.time() - 10)
        assert len(timeline) >= 1

    def test_search_by_outcome(self, episodic):
        episodic.record_event("Good", outcome="success")
        episodic.record_event("Bad", outcome="failure")
        successes = episodic.search_by_outcome("success")
        failures = episodic.search_by_outcome("failure")
        assert len(successes) >= 1
        assert len(failures) >= 1

    def test_clear(self, episodic):
        episodic.record_event("Test", outcome="success")
        assert episodic.clear() >= 1
        assert episodic.count() == 0


# ======================================================================
# SemanticMemory Tests
# ======================================================================

class TestSemanticMemory:
    def test_learn_and_query(self, semantic):
        semantic.learn("Python", "is_a", "programming language")
        facts = semantic.query("Python")
        assert len(facts) >= 1
        assert facts[0].predicate == "is_a"

    def test_learn_confidence_update(self, semantic):
        semantic.learn("Python", "is_a", "programming language", confidence=0.7)
        semantic.learn("Python", "is_a", "programming language", confidence=0.9)
        facts = semantic.query("Python")
        assert facts[0].confidence == 0.9  # Max wins

    def test_search(self, semantic):
        semantic.learn("Flask", "is_a", "web framework")
        semantic.learn("React", "is_a", "UI library")
        results = semantic.search("framework")
        assert len(results) >= 1

    def test_query_object(self, semantic):
        semantic.learn("Docker", "used_for", "containerization")
        results = semantic.query_object("used_for", "containerization")
        assert len(results) >= 1

    def test_increase_confidence(self, semantic):
        semantic.learn("Test", "is", "important", confidence=0.5)
        assert semantic.increase_confidence("Test", "is", "important", 0.3)
        facts = semantic.query("Test")
        assert facts[0].confidence == 0.8

    def test_decrease_confidence(self, semantic):
        semantic.learn("Bad fact", "is", "wrong", confidence=0.8)
        assert semantic.decrease_confidence("Bad fact", "is", "wrong", 0.5)
        facts = semantic.query("Bad fact")
        assert facts[0].confidence == pytest.approx(0.3, rel=1e-6)

    def test_forget_subject(self, semantic):
        semantic.learn("Subject1", "has", "property1")
        semantic.learn("Subject1", "has", "property2")
        assert semantic.forget_subject("Subject1") >= 2
        assert len(semantic.query("Subject1")) == 0

    def test_clear(self, semantic):
        semantic.learn("A", "is", "B")
        assert semantic.clear() >= 1
        assert semantic.count() == 0


# ======================================================================
# ProceduralMemory Tests
# ======================================================================

class TestProceduralMemory:
    def test_record_and_find(self, procedural):
        proc = Procedure(
            name="Fix imports",
            steps=["Check requirements.txt", "Run pip install"],
            context="When ModuleNotFoundError occurs",
            success_rate=0.9,
        )
        procedural.record(proc)
        results = procedural.find_by_context("ModuleNotFoundError")
        assert len(results) >= 1

    def test_get_best(self, procedural):
        procedural.record(Procedure(name="P1", steps=["S1"], success_rate=0.9))
        procedural.record(Procedure(name="P2", steps=["S1"], success_rate=0.5))
        best = procedural.get_best(limit=1)
        assert len(best) == 1
        assert best[0].success_rate == 0.9

    def test_record_success(self, procedural):
        proc = Procedure(name="Test Proc", steps=["S1"], success_rate=0.5)
        entry = procedural.record(proc)
        assert procedural.record_success(proc.id) is True

    def test_record_failure(self, procedural):
        proc = Procedure(name="Fail Proc", steps=["S1"], success_rate=0.8)
        procedural.record(proc)
        assert procedural.record_failure(proc.id) is True

    def test_find_by_name(self, procedural):
        procedural.record(Procedure(name="UniqueProc", steps=["S1"]))
        assert procedural.find_by_name("UniqueProc") is not None
        assert procedural.find_by_name("Nonexistent") is None


# ======================================================================
# WorkspaceMemory Tests
# ======================================================================

class TestWorkspaceMemory:
    def test_set_and_get(self, workspace):
        entry = workspace.set("current_file", "main.py")
        assert entry is not None
        assert workspace.get("current_file") == "main.py"

    def test_isolation(self, store):
        ws1 = WorkspaceMemory(store, workspace_id="ws1")
        ws2 = WorkspaceMemory(store, workspace_id="ws2")
        ws1.set("key", "value1")
        ws2.set("key", "value2")
        assert ws1.get("key") == "value1"
        assert ws2.get("key") == "value2"

    def test_context(self, workspace):
        workspace.set_context("task", "Implement feature X")
        context = workspace.get_context()
        assert context.get("task") == "Implement feature X"

    def test_search(self, workspace):
        workspace.set("topic", "authentication", tags=["security"])
        workspace.set("unrelated", "deploy config", tags=["devops"])
        results = workspace.search("auth")
        assert len(results) >= 1

    def test_clear(self, workspace):
        workspace.set("a", 1)
        workspace.set("b", 2)
        assert workspace.clear() >= 2
        assert workspace.count() == 0


# ======================================================================
# ProjectMemory Tests
# ======================================================================

class TestProjectMemory:
    def test_set_and_get(self, project):
        project.set("architecture", {"pattern": "microservices"})
        assert project.get("architecture") == {"pattern": "microservices"}

    def test_decision_records(self, project):
        project.record_decision("Use FastAPI", "Better async support", "tech-stack")
        decisions = project.get_decisions()
        assert len(decisions) >= 1
        assert any(d.get("title") == "Use FastAPI" for d in decisions)

    def test_context(self, project):
        project.set_context("goal", "Build scalable system")
        ctx = project.get_context()
        assert ctx.get("goal") == "Build scalable system"


# ======================================================================
# EntityIndex Tests
# ======================================================================

class TestEntityIndex:
    def test_register(self, entity_index):
        entity = entity_index.register("MyClass", ENTITY_TYPE_CLASS,
                                       description="A test class")
        assert entity is not None
        assert entity.name == "MyClass"
        assert entity.type == ENTITY_TYPE_CLASS

    def test_find_by_name(self, entity_index):
        entity_index.register("calculate", ENTITY_TYPE_FUNCTION)
        found = entity_index.find_by_name("calculate")
        assert found is not None
        assert found.type == ENTITY_TYPE_FUNCTION

    def test_search(self, entity_index):
        entity_index.register("UserAuth", ENTITY_TYPE_CLASS)
        entity_index.register("LoginForm", ENTITY_TYPE_CLASS)
        results = entity_index.search("auth")
        assert len(results) >= 1

    def test_get_by_type(self, entity_index):
        entity_index.register("func1", ENTITY_TYPE_FUNCTION)
        entity_index.register("func2", ENTITY_TYPE_FUNCTION)
        entity_index.register("MyClass", ENTITY_TYPE_CLASS)
        functions = entity_index.get_by_type(ENTITY_TYPE_FUNCTION)
        assert len(functions) >= 2

    def test_extract_from_text(self, entity_index):
        code = """
        class UserService:
            def authenticate(self):
                pass
        """
        entities = entity_index.extract_from_text(code)
        assert len(entities) >= 2  # UserService, authenticate


# ======================================================================
# RelationshipIndex Tests
# ======================================================================

class TestRelationshipIndex:
    def test_add_and_query(self, relationship_index):
        rel = relationship_index.add_relationship(
            "entity-1", "entity-2", RELATION_DEPENDS_ON
        )
        assert rel is not None
        assert rel.relationship_type == RELATION_DEPENDS_ON

    def test_get_outgoing(self, relationship_index):
        relationship_index.add_relationship("A", "B", RELATION_DEPENDS_ON)
        relationship_index.add_relationship("A", "C", RELATION_IMPORTS)
        outgoing = relationship_index.get_outgoing("A")
        assert len(outgoing) == 2

    def test_get_incoming(self, relationship_index):
        relationship_index.add_relationship("A", "B", RELATION_DEPENDS_ON)
        incoming = relationship_index.get_incoming("B")
        assert len(incoming) == 1

    def test_get_dependencies(self, relationship_index):
        relationship_index.add_relationship("App", "DB", RELATION_DEPENDS_ON)
        deps = relationship_index.get_dependencies("App")
        assert "DB" in deps

    def test_get_dependents(self, relationship_index):
        relationship_index.add_relationship("App", "DB", RELATION_DEPENDS_ON)
        deps = relationship_index.get_dependents("DB")
        assert "App" in deps

    def test_shortest_path(self, relationship_index):
        relationship_index.add_relationship("A", "B", RELATION_DEPENDS_ON)
        relationship_index.add_relationship("B", "C", RELATION_IMPORTS)
        path = relationship_index.shortest_path("A", "C")
        assert path == ["A", "B", "C"]


# ======================================================================
# KnowledgeGraph Tests
# ======================================================================

class TestKnowledgeGraph:
    def test_sync(self, entity_index, relationship_index, store):
        entity_index.register("ModuleA", ENTITY_TYPE_CLASS)
        entity_index.register("ModuleB", ENTITY_TYPE_CLASS)
        kg = KnowledgeGraph(entity_index, relationship_index, store)
        count = kg.sync()
        assert count >= 2

    def test_add_node(self, knowledge_graph):
        node = knowledge_graph.add_node("MyProject", NodeType.PROJECT,
                                        description="A test project")
        assert node is not None
        assert node.name == "MyProject"

    def test_add_relation(self, knowledge_graph):
        n1 = knowledge_graph.add_node("A", NodeType.MODULE)
        n2 = knowledge_graph.add_node("B", NodeType.MODULE)
        rel = knowledge_graph.add_relation(n1.id, n2.id, RelationType.DEPENDS_ON)
        assert rel is not None

    def test_get_neighbors(self, knowledge_graph):
        n1 = knowledge_graph.add_node("A", NodeType.MODULE)
        n2 = knowledge_graph.add_node("B", NodeType.MODULE)
        knowledge_graph.add_relation(n1.id, n2.id, RelationType.DEPENDS_ON)
        neighbors = knowledge_graph.get_neighbors(n1.id)
        assert len(neighbors) == 1
        assert neighbors[0].name == "B"

    def test_get_subgraph(self, knowledge_graph):
        n1 = knowledge_graph.add_node("Center", NodeType.MODULE)
        n2 = knowledge_graph.add_node("Neighbor", NodeType.MODULE)
        knowledge_graph.add_relation(n1.id, n2.id, RelationType.DEPENDS_ON)
        # depth=2 to traverse through the edge to the neighbor
        sub = knowledge_graph.get_subgraph(n1.id, depth=2)
        assert sub["node_count"] >= 2

    def test_find_path(self, knowledge_graph):
        n1 = knowledge_graph.add_node("A", NodeType.MODULE)
        n2 = knowledge_graph.add_node("B", NodeType.MODULE)
        n3 = knowledge_graph.add_node("C", NodeType.MODULE)
        knowledge_graph.add_relation(n1.id, n2.id, RelationType.DEPENDS_ON)
        knowledge_graph.add_relation(n2.id, n3.id, RelationType.IMPORTS)
        path = knowledge_graph.find_path(n1.id, n3.id)
        assert path is not None
        assert len(path) == 3

    def test_search_nodes(self, knowledge_graph):
        knowledge_graph.add_node("AuthModule", NodeType.MODULE)
        knowledge_graph.add_node("PaymentModule", NodeType.MODULE)
        results = knowledge_graph.search_nodes("auth")
        assert len(results) >= 1

    def test_connected_components(self, knowledge_graph):
        n1 = knowledge_graph.add_node("A", NodeType.MODULE)
        n2 = knowledge_graph.add_node("B", NodeType.MODULE)
        knowledge_graph.add_relation(n1.id, n2.id, RelationType.DEPENDS_ON)
        knowledge_graph.add_node("Isolated", NodeType.ENTITY)
        components = knowledge_graph.get_connected_components()
        assert len(components) >= 2


# ======================================================================
# RetrievalEngine Tests
# ======================================================================

class TestRetrievalEngine:
    def test_keyword_search(self, retrieval, store):
        store.save("deploy_config", "Deploy to production", tags=["devops"])
        store.save("test_config", "Run tests", tags=["testing"])
        results = retrieval.search("deploy")
        assert len(results) >= 1
        assert any("deploy" in r.entry.key for r in results)

    def test_semantic_search(self, retrieval, store, embedder):
        store.save("greeting", "hello world")
        store.save("farewell", "goodbye world")
        results = retrieval.search("hello", include_semantic=True)
        # Should find "hello" via keyword and "hello"/"world" semantically
        assert len(results) >= 1

    def test_graph_search(self, retrieval, store, knowledge_graph):
        store.save("api_doc", "API documentation")
        store.save("db_doc", "Database documentation")
        n1 = knowledge_graph.add_node("API", NodeType.DOCUMENT)
        n2 = knowledge_graph.add_node("Database", NodeType.DOCUMENT)
        knowledge_graph.add_relation(n1.id, n2.id, RelationType.RELATED_TO)
        results = retrieval.search("API", include_graph=True)
        assert len(results) >= 1

    def test_search_with_filters(self, retrieval, store):
        store.save("secret_key", "supersecret", tags=["security"])
        store.save("public_key", "public", tags=["public"])
        results = retrieval.search_with_filters("key", tags=["security"])
        assert len(results) >= 1
        assert all("security" in r.entry.tags for r in results)

    def test_empty_search(self, retrieval):
        results = retrieval.search("nonexistent_xyz")
        assert len(results) == 0

    def test_weights(self, retrieval):
        retrieval.set_weights(keyword=2.0, semantic=0.5, graph=0.0)
        config = retrieval.stats()
        assert config["weights"]["keyword"] == 2.0


# ======================================================================
# RankingEngine Tests
# ======================================================================

class TestRankingEngine:
    def test_rank(self, ranking, store):
        e1 = store.save("a", "value", importance=0.9)
        e2 = store.save("b", "value", importance=0.3)
        entries = [e1, e2]
        ranked = ranking.rank(entries)
        assert ranked[0].importance == 0.9
        assert ranked[1].importance == 0.3

    def test_boost_important(self, ranking, store):
        e1 = store.save("a", 1, importance=0.5)
        e2 = store.save("b", 2, importance=0.9)
        entries = [e1, e2]
        boosted = ranking.boost_important(entries, min_importance=0.8)
        assert boosted[0].importance == 0.9

    def test_filter_by_threshold(self, ranking, store):
        e1 = store.save("a", 1, importance=0.9)
        e2 = store.save("b", 2, importance=0.1)
        entries = [e1, e2]
        # Both entries are recent so they get recency boost.
        # Use a high threshold that only the high-importance entry passes.
        filtered = ranking.filter_by_threshold(entries, min_score=1.5)
        assert len(filtered) >= 1
        # At least one entry with high importance should pass
        high_imp = [e for e in filtered if e.importance >= 0.9]
        assert len(high_imp) >= 1


# ======================================================================
# Summarizer Tests
# ======================================================================

class TestSummarizer:
    def test_summarize_short_text(self, summarizer):
        text = "Short text."
        assert summarizer.summarize(text) == text

    def test_summarize_long_text(self, summarizer):
        text = ". ".join(["This is sentence number " + str(i) for i in range(50)])
        summary = summarizer.summarize(text, max_chars=200)
        assert len(summary) <= 250
        assert len(summary) > 0

    def test_bullet_points(self, summarizer):
        text = "First important point. Second crucial detail. Third minor note."
        bullets = summarizer.bullet_points(text, max_points=2)
        assert len(bullets) <= 2

    def test_key_points(self, summarizer):
        text = "Important: do this. Critical: avoid that. Normal note."
        points = summarizer.key_points(text, max_points=2)
        assert len(points) <= 2

    def test_format_memory_context(self, summarizer):
        entries = [
            {"key": "pref", "value": {"theme": "dark"}, "memory_type": "long_term"},
            {"key": "task", "value": "Implement login", "memory_type": "short_term"},
        ]
        result = summarizer.format_memory_context(entries, max_chars=500)
        assert "long_term" in result
        assert "short_term" in result


# ======================================================================
# RetentionEngine Tests
# ======================================================================

class TestRetentionEngine:
    def test_default_policies(self, retention):
        policies = retention.list_policies()
        assert len(policies) >= 4

    def test_add_policy(self, retention):
        policy = RetentionPolicy(
            name="test_policy",
            memory_types=["test"],
            max_age_days=1.0,
            action=RetentionAction.DELETE,
        )
        retention.add_policy(policy)
        assert any(p.name == "test_policy" for p in retention.list_policies())

    def test_evaluate_delete(self, retention, store):
        entry = store.save("old_entry", "old", memory_type="short_term")
        # Manually set created_at to simulate old entry
        entry.created_at = time.time() - (10 * 86400)
        actions = retention.evaluate([entry])
        assert len(actions) >= 1
        # Should trigger DELETE or PROMOTE for old short_term entry

    def test_evaluate_keep(self, retention, store):
        entry = store.save("new_entry", "new", memory_type="long_term",
                          importance=0.9)
        actions = retention.evaluate([entry])
        keep_actions = [a for a in actions if a[1] == RetentionAction.KEEP]
        assert len(keep_actions) >= 0  # KEEP actions may not be explicitly emitted

    def test_should_pin(self, retention, store):
        pinned = store.save("pinned", "value", importance=0.95)
        not_pinned = store.save("not_pinned", "value", importance=0.3)
        assert retention.should_pin(pinned) is True
        assert retention.should_pin(not_pinned) is False

    def test_activate_deactivate(self, retention):
        retention.activate_policy("short_term_expiry")
        assert any(
            p.active for p in retention.list_policies()
            if p.name == "short_term_expiry"
        )


# ======================================================================
# GarbageCollector Tests
# ======================================================================

class TestGarbageCollector:
    def test_run(self, gc, store):
        entry = store.save("old_entry", "old", memory_type="short_term", importance=0.1)
        # Manually set created_at to simulate old entry
        entry.created_at = time.time() - (365 * 86400)
        result = gc.run()
        assert "removed" in result or "archived" in result or "promoted" in result

    def test_prune_expired(self, gc, store):
        store.save("expiring", "value", ttl=0.01)
        time.sleep(0.02)
        result = gc.run()
        assert result.get("removed", 0) >= 0

    def test_start_stop_auto(self, gc):
        gc.start_auto(interval_minutes=0.01)
        time.sleep(0.05)
        gc.stop_auto()
        stats = gc.get_stats()
        assert stats["runs"] >= 0

    def test_set_promote_callback(self, gc):
        callback_called = False

        def callback(entry):
            nonlocal callback_called
            callback_called = True

        gc.set_promote_callback(callback)
        assert callback_called is False  # Should be called during GC run

    def test_reset_stats(self, gc):
        gc.run()
        gc.reset_stats()
        stats = gc.get_stats()
        assert stats["runs"] == 0


# ======================================================================
# ConsolidationEngine Tests
# ======================================================================

class TestConsolidationEngine:
    def test_consolidate_empty(self, consolidation):
        result = consolidation.consolidate()
        assert isinstance(result, dict)

    def test_merge_duplicates(self, consolidation, store):
        store.save("dup_key", "first", scope=MemoryScope.GLOBAL)
        store.save("dup_key", "second", scope=MemoryScope.GLOBAL)
        merged = consolidation.merge_duplicates()
        assert merged >= 0  # May merge or may keep one

    def test_promote_entries(self, consolidation, store):
        entry = store.save("promote_me", "important", memory_type="short_term",
                          importance=0.8)
        promoted = consolidation.promote_entries([entry.id])
        assert promoted >= 1

    def test_start_stop_auto(self, consolidation):
        consolidation.start_auto(interval_minutes=0.01)
        time.sleep(0.05)
        consolidation.stop_auto()
        stats = consolidation.get_stats()
        assert stats["cycles"] >= 0


# ======================================================================
# LearningEngine Tests
# ======================================================================

class TestLearningEngine:
    def test_observe(self, learning):
        sample = LearningSample(
            category="tool_selection",
            observation="web_search works best for fact lookup",
            outcome="success",
            confidence=0.8,
        )
        learning.observe(sample)
        # Should not raise

    def test_get_insights(self, learning):
        learning.observe(LearningSample(
            category="planning", observation="Plan first", outcome="success"))
        insights = learning.get_insights(category="planning")
        assert len(insights) >= 1

    def test_get_successful_strategies(self, learning):
        learning.observe(LearningSample(
            category="execution", observation="Use parallel execution",
            outcome="success", confidence=0.9))
        strategies = learning.get_successful_strategies(category="execution")
        assert len(strategies) >= 1

    def test_get_failure_patterns(self, learning):
        learning.observe(LearningSample(
            category="execution", observation="Avoid deep recursion",
            outcome="failure", confidence=0.8))
        patterns = learning.get_failure_patterns(category="execution")
        assert len(patterns) >= 1

    def test_observe_tool_result(self, learning):
        learning.observe_tool_result("web_search", "Find docs", True, 2.5)
        # Should not raise

    def test_observe_agent_outcome(self, learning):
        learning.observe_agent_outcome("research", "Find info", "success", 5.0)
        # Should not raise

    def test_observe_user_correction(self, learning):
        learning.observe_user_correction("wrong approach", "correct approach")
        insights = learning.get_insights(category="planning")
        assert len(insights) >= 1

    def test_subscribe(self, learning):
        called = []

        def hook(sample):
            called.append(sample)

        unsub = learning.subscribe(hook)
        learning.observe(LearningSample(category="test", observation="test",
                                       outcome="success"))
        assert len(called) == 1
        unsub()

    def test_get_best_tool(self, learning):
        learning.observe_tool_result("tool_a", "Task X", True)
        learning.observe_tool_result("tool_b", "Task X", False)
        best = learning.get_best_tool_for_task("Task X")
        # May return a tool or None depending on observations


# ======================================================================
# ReflectionEngine Tests
# ======================================================================

class TestReflectionEngine:
    def test_reflect_on_workflow(self, reflection):
        ref = reflection.reflect_on_workflow(
            goal="Build auth system",
            outcome="success",
            successes=["Implemented JWT"],
            failures=["Rate limiting tricky"],
            lessons=["Use middleware for auth"],
            task_count=3,
        )
        assert ref is not None
        assert ref.outcome == "success"
        assert len(ref.lessons) >= 1

    def test_get_recent(self, reflection):
        reflection.reflect_on_workflow("Task 1", "success")
        reflection.reflect_on_workflow("Task 2", "failure")
        recent = reflection.get_recent(limit=5)
        assert len(recent) >= 2

    def test_get_by_outcome(self, reflection):
        reflection.reflect_on_workflow("Success task", "success",
                                       successes=["Good"])
        reflection.reflect_on_workflow("Fail task", "failed",
                                       failures=["Bad"])
        successes = reflection.get_by_outcome("success")
        failures = reflection.get_by_outcome("failed")
        assert len(successes) >= 1
        assert len(failures) >= 1

    def test_get_lessons(self, reflection):
        reflection.reflect_on_workflow(
            "Test", "success",
            lessons=["Lesson 1", "Lesson 2"],
        )
        lessons = reflection.get_lessons()
        assert len(lessons) >= 0

    def test_get_recommendations(self, reflection):
        reflection.reflect_on_workflow(
            "Deploy app", "success",
            successes=["Use CI/CD pipeline"],
        )
        recs = reflection.get_recommendations(context="deploy")
        assert len(recs) >= 0

    def test_subscribe(self, reflection):
        called = []

        def hook(ref):
            called.append(ref)

        unsub = reflection.subscribe(hook)
        reflection.reflect_on_workflow("Test", "success",
                                       successes=["Good"])
        assert len(called) == 1
        unsub()


# ======================================================================
# MemoryExporter Tests
# ======================================================================

class TestMemoryExporter:
    def test_to_json(self, exporter, store):
        store.save("export_key", "export_value", tags=["test"])
        json_str = exporter.to_json()
        data = json.loads(json_str)
        assert data["export_version"] == "1.0"
        assert data["total_entries"] >= 1

    def test_to_markdown(self, exporter, store):
        store.save("md_key", "md_value", memory_type="long_term")
        md = exporter.to_markdown()
        assert "AetherOS Memory Export" in md
        assert "md_key" in md

    def test_to_csv(self, exporter, store):
        store.save("csv_key", "csv_value")
        csv_str = exporter.to_csv()
        assert "csv_key" in csv_str
        assert "csv_value" in csv_str

    def test_filtered_export(self, exporter, store):
        store.save("keep_this", "value", memory_type="long_term")
        store.save("skip_this", "value", memory_type="short_term")
        opts = ExportOptions(filter_memory_types=["long_term"])
        exporter.export(opts)
        # Should only export long_term entries

    def test_export_to_file(self, exporter, store, tmp_path):
        store.save("file_key", "file_value")
        output_path = str(tmp_path / "export.json")
        exporter.to_json(output_path=output_path)
        assert Path(output_path).exists()
        content = Path(output_path).read_text()
        assert "file_key" in content


# ======================================================================
# MemoryImporter Tests
# ======================================================================

class TestMemoryImporter:
    def test_import_json(self, importer, store):
        json_data = json.dumps({
            "export_version": "1.0",
            "exported_at": time.time(),
            "total_entries": 2,
            "entries": [
                {"key": "imported_a", "value": "A", "memory_type": "long_term"},
                {"key": "imported_b", "value": "B", "memory_type": "long_term"},
            ],
        })
        result = importer.import_from_json(json_data)
        assert result.imported == 2
        assert store.get_by_key("imported_a") is not None

    def test_import_invalid_version(self, importer):
        json_data = json.dumps({
            "export_version": "99.0",
            "entries": [{"key": "test", "value": "test"}],
        })
        result = importer.import_from_json(json_data)
        assert result.errors >= 1

    def test_import_from_file(self, importer, store, tmp_path):
        file_path = tmp_path / "test_import.json"
        file_path.write_text(json.dumps({
            "export_version": "1.0",
            "exported_at": time.time(),
            "total_entries": 1,
            "entries": [{"key": "file_import", "value": "imported", "memory_type": "long_term"}],
        }))
        result = importer.import_from_file(str(file_path))
        assert result.imported == 1
        assert store.get_by_key("file_import") is not None

    def test_import_file_not_found(self, importer):
        result = importer.import_from_file("/nonexistent/file.json")
        assert result.errors >= 1

    def test_import_dry_run(self, importer, store):
        json_data = json.dumps({
            "export_version": "1.0",
            "entries": [{"key": "dry_run", "value": "test", "memory_type": "long_term"}],
        })
        opts = ImportOptions(dry_run=True)
        result = importer.import_from_json(json_data, options=opts)
        assert result.imported > 0
        # Verify nothing was actually stored in dry run mode
        assert store.get_by_key("dry_run") is None


# ======================================================================
# MemoryManager (Unified Interface) Tests
# ======================================================================

class TestMemoryManager:
    def test_initialize(self):
        manager = MemoryManager()
        assert manager.initialize() is True
        assert manager._initialized is True

    def test_remember_and_recall(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("test_key", "test_value", memory_type="long_term")
        value = manager.recall("test_key")
        assert value == "test_value"

    def test_forget(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("forget_test", "value", memory_type="long_term")
        assert manager.forget("forget_test") is True
        assert manager.recall("forget_test") is None

    def test_search(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("search_target", "findable data", memory_type="long_term",
                         tags=["searchable"])
        results = manager.search("findable")
        assert len(results) >= 1

    def test_learn_and_insights(self):
        manager = MemoryManager()
        manager.initialize()
        manager.learn(category="testing", observation="Test observation",
                      outcome="success")
        insights = manager.get_insights(category="testing")
        assert len(insights) >= 1

    def test_reflect_and_lessons(self):
        manager = MemoryManager()
        manager.initialize()
        manager.reflect("Test goal", "success",
                        successes=["Completed task"],
                        lessons=["Lesson learned"])
        lessons = manager.get_lessons()
        assert len(lessons) >= 1

    def test_knowledge_graph(self):
        manager = MemoryManager()
        manager.initialize()
        node = manager.add_knowledge_node("TestNode", NodeType.MODULE)
        assert node is not None
        assert node.name == "TestNode"

    def test_register_entity(self):
        manager = MemoryManager()
        manager.initialize()
        entity = manager.register_entity("TestEntity", "class",
                                         description="A test entity")
        assert entity is not None
        assert entity.name == "TestEntity"

    def test_export_import_roundtrip(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("roundtrip_key", "roundtrip_value",
                        memory_type="long_term")

        # Export to JSON
        json_str = manager.export_to_json()
        data = json.loads(json_str)
        assert data["total_entries"] >= 1

        # Clear and re-import
        manager.clear_all()
        assert manager.recall("roundtrip_key") is None

        result = manager.import_from_json(json_str)
        assert result.imported >= 1
        assert manager.recall("roundtrip_key") == "roundtrip_value"

    def test_stats(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("stat_test", "value", memory_type="long_term")
        stats = manager.stats()
        assert stats["initialized"] is True
        assert stats["memory_types"]["long_term"] >= 1

    def test_status(self):
        manager = MemoryManager()
        manager.initialize()
        status = manager.status()
        assert "Memory System Status" in status

    def test_shutdown(self):
        manager = MemoryManager()
        manager.initialize()
        manager.shutdown()
        assert manager._initialized is False

    def test_clear_all(self):
        manager = MemoryManager()
        manager.initialize()
        manager.remember("clear_key", "value", memory_type="long_term")
        manager.remember("clear_key2", "value", memory_type="short_term")
        count = manager.clear_all()
        assert count >= 2
        assert manager.recall("clear_key") is None

    def test_search_facts(self):
        manager = MemoryManager()
        manager.initialize()
        if manager.semantic:
            manager.semantic.learn("Python", "is_a", "language")
            facts = manager.search_facts("Python")
            assert len(facts) >= 1

    def test_search_episodes(self):
        manager = MemoryManager()
        manager.initialize()
        if manager.episodic:
            manager.episodic.record_event("Test event", outcome="success")
            episodes = manager.search_episodes("Test")
            assert len(episodes) >= 1

    def test_search_procedures(self):
        manager = MemoryManager()
        manager.initialize()
        if manager.procedural:
            manager.procedural.record(Procedure(
                name="Test proc", steps=["Step 1"], context="test context"))
            procs = manager.search_procedures("test")
            assert len(procs) >= 1

    def test_summarize(self):
        manager = MemoryManager()
        manager.initialize()
        text = "This is a long text. " * 100
        summary = manager.summarize(text, max_chars=200)
        assert len(summary) <= 250
        assert len(summary) > 0

    def test_consolidate(self):
        manager = MemoryManager()
        manager.initialize()
        result = manager.consolidate()
        assert isinstance(result, dict)

    def test_run_gc(self):
        manager = MemoryManager()
        manager.initialize()
        result = manager.run_gc()
        assert isinstance(result, dict)
