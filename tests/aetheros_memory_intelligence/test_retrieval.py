"""Tests for memory retrieval and scoring."""
import pytest
from aetheros_memory_intelligence.retrieval import SecureRetriever, RetrievalResult, RetrievedMemory
from aetheros_memory_intelligence.schema import MemoryEntry, MemoryEntryBuilder
from aetheros_memory_intelligence.store import MemoryStore
from aetheros_memory_intelligence.boundaries import AccessContext, MemoryBoundaries
from aetheros_memory_intelligence.trust import TrustModel
from aetheros_memory_intelligence.provenance import ProvenanceRecord
from aetheros_memory_intelligence.types import MemoryType, MemoryBoundary, MemoryOrigin, MemoryState, TrustLevel, VerificationLevel


def test_secure_retriever_init():
    store = MemoryStore()
    retriever = SecureRetriever(store)
    assert retriever._store == store
    assert retriever._boundaries is not None
    assert retriever._trust is not None
    assert retriever.top_k == 8
    assert retriever.min_score == 0.25


def test_secure_retriever_custom_params():
    store = MemoryStore()
    retriever = SecureRetriever(
        store,
        top_k=5,
        min_score=0.5,
        keyword_weight=0.8
    )
    assert retriever.top_k == 5
    assert retriever.min_score == 0.5
    assert retriever.keyword_weight == 0.8


def test_retriever_returns_empty_when_no_entries():
    store = MemoryStore()
    retriever = SecureRetriever(store)

    result = retriever.retrieve("any query", AccessContext(user_id="user123"))

    assert isinstance(result, RetrievalResult)
    assert result.query == "any query"
    assert result.memories == []
    assert result.total_found == 0
    assert result.total_eligible == 0
    assert result.total_filtered_by_boundary == 0


def test_retriever_finds_matching_entry():
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    # Store an entry
    entry = MemoryEntryBuilder()\
        .content("The quick brown fox jumps over the lazy dog")\
        .scope(user_id="user123")\
        .build()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("quick brown fox", actor)

    assert result.total_found == 1
    assert result.total_eligible == 1
    assert result.total_filtered_by_boundary == 0
    assert len(result.memories) == 1
    assert result.memories[0].text == "The quick brown fox jumps over the lazy dog"
    assert result.memories[0].score > 0  # Should have some score
    assert result.memories[0].entry.id == entry.id


def test_retriever_keyword_scoring():
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    # Entries with different keyword matches
    entry1 = MemoryEntryBuilder()\
        .content("apple banana cherry")\
        .scope(user_id="user123")\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("apple grape")\
        .scope(user_id="user123")\
        .build()
    entry3 = MemoryEntryBuilder()\
        .content("watermelon")\
        .scope(user_id="user123")\
        .build()

    store.save(entry1)
    store.save(entry2)
    store.save(entry3)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("apple", actor)

    assert result.total_found == 3
    # Should be ordered by score (entry1 and entry2 both have "apple", entry3
    # has none)
    assert len(result.memories) == 2  # min_score filters out entry3
    assert result.memories[0].text in ["apple banana cherry", "apple grape"]
    assert result.memories[1].text in ["apple banana cherry", "apple grape"]
    assert result.memories[0].score >= result.memories[1].score


def test_retriever_boundary_filtering():
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    # Entries in different boundaries
    entry_user = MemoryEntryBuilder()\
        .content("User's secret")\
        .scope(user_id="alice")\
        .boundary(MemoryBoundary.USER)\
        .build()
    entry_workspace = MemoryEntryBuilder()\
        .content("Workspace knowledge")\
        .scope(user_id="alice", workspace_id="ws1")\
        .boundary(MemoryBoundary.WORKSPACE)\
        .build()
    entry_system = MemoryEntryBuilder()\
        .content("System info")\
        .scope(user_id="alice")\
        .boundary(MemoryBoundary.SYSTEM)\
        .build()

    store.save(entry_user)
    store.save(entry_workspace)
    store.save(entry_system)

    # Regular user Alice can only read her own user and workspace (not system)
    actor = AccessContext(user_id="alice")
    result = retriever.retrieve("*", actor)  # Match all

    assert result.total_found == 3
    assert result.total_eligible == 3
    assert result.total_filtered_by_boundary == 1  # System entry filtered out
    assert len(result.memories) == 2  # User and workspace entries

    texts = [m.text for m in result.memories]
    assert "User's secret" in texts
    assert "Workspace knowledge" in texts
    assert "System info" not in texts

    # Admin can read all
    admin_ctx = AccessContext(user_id="alice", is_admin=True)
    result = retriever.retrieve("*", admin_ctx)
    assert result.total_filtered_by_boundary == 0
    assert len(result.memories) == 3


def test_retriever_trust_scoring():
    store = MemoryStore()
    retriever = SecureRetriever(store)

    # Same content, different trust levels
    entry_low = MemoryEntryBuilder()\
        .content("Common fact")\
        .scope(user_id="user123")\
        .trust(0.2)\
        .build()
    entry_high = MemoryEntryBuilder()\
        .content("Common fact")\
        .scope(user_id="user123")\
        .trust(0.9)\
        .build()

    store.save(entry_low)
    store.save(entry_high)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("Common fact", actor)

    assert len(result.memories) == 2
    # Higher trust should come first (due to trust blending in score)
    assert result.memories[0].entry.trust >= result.memories[1].entry.trust


def test_retriever_confidence_scoring(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    # Same trust, different confidence
    entry_low_conf = MemoryEntryBuilder()\
        .content("Fact with low confidence")\
        .scope(user_id="user123")\
        .trust(0.7)\
        .confidence(0.2)\
        .build()
    entry_high_conf = MemoryEntryBuilder()\
        .content("Fact with high confidence")\
        .scope(user_id="user123")\
        .trust(0.7)\
        .confidence(0.9)\
        .build()

    store.save(entry_low_conf)
    store.save(entry_high_conf)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("Fact with", actor)

    assert len(result.memories) == 2
    # Higher confidence should come first
    assert result.memories[0].entry.confidence >= result.memories[1].entry.confidence


def test_retriever_provenance_extraction(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    from aetheros_memory_intelligence.provenance import ProvenanceRecord

    provenance = ProvenanceRecord(
        origin=MemoryOrigin.USER,
        source="User told me",
        source_uri="user://chat/123",
        agent="user_client",
        verification="verified"
    )

    entry = MemoryEntryBuilder()\
        .content("User shared this fact")\
        .scope(user_id="user123")\
        .build()
    # Manually attach provenance
    entry.metadata["provenance"] = provenance.to_dict()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("User shared", actor)

    assert len(result.memories) == 1
    mem = result.memories[0]
    assert mem.provenance is not None
    assert mem.provenance.origin == MemoryOrigin.USER
    assert mem.provenance.source == "User told me"
    assert mem.provenance.agent == "user_client"
    assert mem.provenance.verification == VerificationLevel.VERIFIED


def test_retriever_score_blending(self):
    store = MemoryStore()
    store.initialize()
    # Custom retriever with known weights for testing
    # 80% keyword, 20% semantic
    retriever = SecureRetriever(store, keyword_weight=0.8)

    entry = MemoryEntryBuilder()\
        .content("apple banana")\
        .scope(user_id="user123")\
        .build()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    # Query that matches keywords
    result = retriever.retrieve("apple", actor)

    assert len(result.memories) == 1
    mem = result.memories[0]
    # Score should be blended: 0.8 * keyword_score + 0.2 * semantic_score
    # Since we didn't provide semantic_score_fn, semantic_score = 0
    # So score = 0.8 * keyword_score
    # Keyword score for "apple" in "apple banana" should be 0.5 (1 of 2 tokens)
    # Expected score = 0.8 * 0.5 = 0.4
    assert abs(mem.score - 0.4) < 0.01


def test_retriever_min_score_filter(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store, min_score=0.5)

    # Low relevance entry
    entry = MemoryEntryBuilder()\
        .content("unrelated topic")\
        .scope(user_id="user123")\
        .build()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("completely different query", actor)

    assert result.total_found == 1
    assert len(result.memories) == 0  # Filtered out by min_score


def test_retriever_top_k_limit(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store, top_k=2)

    # Store 5 entries
    for i in range(5):
        entry = MemoryEntryBuilder()\
            .content(f"item {i}")\
            .scope(user_id="user123")\
            .build()
        store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("item", actor)

    assert result.total_found == 5
    assert len(result.memories) == 2  # Limited by top_k


def test_retrieved_memory_to_dict():
    entry = MemoryEntryBuilder()\
        .content("Test content")\
        .scope(user_id="user123", workspace_id="ws1")\
        .summary("Test summary")\
        .tags(["tag1", "tag2"])\
        .source("test source")\
        .source_uri = "http://test.com"\
        .confidence(0.8)\
        .trust(0.9)\
        .verification("verified")\
        .build()

    retrieved = RetrievedMemory(
        entry=entry,
        score=0.75,
        trust=0.85,
        confidence=0.7
    )

    d = retrieved.to_dict()
    assert d["id"] == entry.id
    assert d["memory_type"] == "semantic"
    assert d["boundary"] == "user"
    assert d["score"] == 0.75
    assert d["trust"] == 0.85
    assert d["confidence"] == 0.7
    assert d["content"] == "Test content"
    assert d["source"] == "test source"
    assert d["source_uri"] == "http://test.com"
    assert d["verification"] == "verified"


def test_retrieval_result_properties():
    mem1 = RetrievedMemory(
        entry=MemoryEntryBuilder().content("Mem 1").scope(
            user_id="u1").build(), score=0.9)
    mem2 = RetrievedMemory(
        entry=MemoryEntryBuilder().content("Mem 2").scope(
            user_id="u1").build(), score=0.7)

    result = RetrievalResult(
        query="test query",
        memories=[mem1, mem2],
        total_found=5,
        total_eligible=3,
        total_filtered_by_boundary=1,
        duration_ms=15.5,
        used_cache=False
    )

    assert result.query == "test query"
    assert len(result.memories) == 2
    assert result.total_found == 5
    assert result.total_eligible == 3
    assert result.total_filtered_by_boundary == 1
    assert result.duration_ms == 15.5
    assert result.used_cache == False
    assert result.loop_guard_reason == ""


def test_retriever_with_semantic_score_fn():
    store = MemoryStore()
    # Custom semantic score function that gives perfect score for exact matches

    def semantic_score(query: str, entry: MemoryEntry) -> float:
        if query.lower() == entry.content.lower():
            return 1.0
        return 0.0

    retriever = SecureRetriever(
        store,
        keyword_weight=0.5,  # Equal weight
        semantic_score_fn=semantic_score
    )

    entry = MemoryEntryBuilder()\
        .content("exact match phrase")\
        .scope(user_id="user123")\
        .build()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("exact match phrase", actor)

    assert len(result.memories) == 1
    mem = result.memories[0]
    # Score = 0.5 * keyword_score + 0.5 * semantic_score
    # Keyword score: "exact match phrase" in "exact match phrase" = 1.0
    # Semantic score: 1.0
    # Expected: 0.5 * 1.0 + 0.5 * 1.0 = 1.0
    assert abs(mem.score - 1.0) < 0.01


def test_retriever_empty_query(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    entry = MemoryEntryBuilder()\
        .content("Some content")\
        .scope(user_id="user123")\
        .build()
    store.save(entry)

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("", actor)  # Empty query

    # Empty query should have keyword score of 0
    assert result.total_found == 1
    assert len(result.memories) == 0  # Filtered out by min_score (0 < 0.25)


def test_retriever_access_updates_entry(self):
    store = MemoryStore()
    store.initialize()
    retriever = SecureRetriever(store)

    entry = MemoryEntryBuilder()\
        .content("Access me")\
        .scope(user_id="user123")\
        .build()
    stored_entry = store.save(entry)
    original_accessed = stored_entry.accessed_at
    original_count = stored_entry.access_count

    actor = AccessContext(user_id="user123")
    result = retriever.retrieve("Access me", actor)

    assert len(result.memories) == 1
    retrieved_entry = store.get(result.memories[0].id)
    assert retrieved_entry.accessed_at > original_accessed
    assert retrieved_entry.access_count == original_count + 1
