"""Tests for cache and loop guard functionality."""
from aetheros_memory_intelligence.cache import ScopeIsolatedCache
from aetheros_memory_intelligence.loop_guard import RetrievalLoopGuard, LoopDecision
from aetheros_memory_intelligence.retrieval import RetrievalResult
from aetheros_memory_intelligence.schema import MemoryEntry, MemoryEntryBuilder
from aetheros_memory_intelligence.types import MemoryState
import pytest


def test_cache_init():
    cache = ScopeIsolatedCache()
    assert cache._ttl_seconds == 300
    assert len(cache._cache) == 0
    assert cache.stats()["entries"] == 0
    assert cache.stats()["hits"] == 0
    assert cache.stats()["misses"] == 0
    assert cache.stats()["hit_rate"] == 0.0


def test_cache_custom_ttl():
    cache = ScopeIsolatedCache(ttl_seconds=60)
    assert cache._ttl_seconds == 60


def test_cache_put_and_get():
    cache = ScopeIsolatedCache(ttl_seconds=1)
    
    actor = {"user_id": "alice", "workspace_id": "ws1"}
    query = "test query"
    top_k = "5"
    
    # Put a value
    value_to_cache = "cached result"
    cache.put(actor, query, top_k, value_to_cache)
    
    # Should be able to get it
    cached = cache.get(actor, query, top_k)
    assert cached == value_to_cache
    
    # Stats
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 1.0


def test_cache_miss():
    cache = ScopeIsolatedCache()
    
    actor = {"user_id": "alice"}
    query = "nonexistent query"
    top_k = "10"
    
    cached = cache.get(actor, query, top_k)
    assert cached is None
    
    stats = cache.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.0


def test_cache_expiration():
    cache = ScopeIsolatedCache(ttl_seconds=0.1)  # Fast expiration for testing
    
    actor = {"user_id": "alice"}
    query = "expiring query"
    top_k = "5"
    
    # Put and immediately get
    cache.put(actor, query, top_k, "value")
    cached = cache.get(actor, query, top_k)
    assert cached == "value"
    
    # Wait for expiration
    import time
    time.sleep(0.15)
    
    # Should be expired now
    cached = cache.get(actor, query, top_k)
    assert cached is None
    
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


def test_cache_scope_isolation():
    cache = ScopeIsolatedCache()
    
    query = "same query"
    top_k = "5"
    value_a = "result for user A"
    value_b = "result for user B"
    
    # Put for user A
    cache.put({"user_id": "alice"}, query, top_k, value_a)
    # Put for user B (same query, different user)
    cache.put({"user_id": "bob"}, query, top_k, value_b)
    
    # Should get different values
    assert cache.get({"user_id": "alice"}, query, top_k) == value_a
    assert cache.get({"user_id": "bob"}, query, top_k) == value_b
    
    # Should be isolated by workspace too
    cache.put({"user_id": "alice", "workspace_id": "ws1"}, query, top_k, "ws1 result")
    cache.put({"user_id": "alice", "workspace_id": "ws2"}, query, top_k, "ws2 result")
    
    assert cache.get({"user_id": "alice", "workspace_id": "ws1"}, query, top_k) == "ws1 result"
    assert cache.get({"user_id": "alice", "workspace_id": "ws2"}, query, top_k) == "ws2 result"
    assert cache.get({"user_id": "alice"}, query, top_k) == value_a  # No workspace specified


def test_cache_overwrite_same_key():
    cache = ScopeIsolatedCache()
    
    actor = {"user_id": "alice"}
    query = "same query"
    top_k = "5"
    
    cache.put(actor, query, top_k, "first value")
    cache.put(actor, query, top_k, "second value")
    
    cached = cache.get(actor, query, top_k)
    assert cached == "second value"  # Should overwrite
    
    stats = cache.stats()
    assert stats["hits"] == 2  # Two gets (one after each put)
    assert stats["misses"] == 0


def test_cache_stats():
    cache = ScopeIsolatedCache()
    
    actor = {"user_id": "alice"}
    
    # Mix of hits and misses
    cache.put(actor, "q1", "5", "v1")
    cache.get(actor, "q1", "5")  # Hit
    cache.get(actor, "q2", "5")  # Miss
    cache.get(actor, "q1", "5")  # Hit
    cache.get(actor, "q3", "5")  # Miss
    cache.get(actor, "q1", "5")  # Hit
    
    stats = cache.stats()
    assert stats["entries"] == 1  # Only one unique cached item
    assert stats["hits"] == 3
    assert stats["misses"] == 2
    assert abs(stats["hit_rate"] - 0.6) < 0.001  # 3/5 = 0.6


def test_cache_clear_on_invalidate():
    cache = ScopeIsolatedCache()
    
    actor = {"user_id": "alice"}
    cache.put(actor, "query1", "5", "value1")
    cache.put(actor, "query2", "5", "value2")
    
    assert cache.get(actor, "query1", "5") == "value1"
    assert cache.get(actor, "query2", "5") == "value2"
    
    # Invalidate one key
    cache.invalidate([fake_id()])  # Non-existent ID should not crash
    # Still should have both
    assert cache.get(actor, "query1", "5") == "value1"
    assert cache.get(actor, "query2", "5") == "value2"
    
    # Invalidate actual keys (we don't have access to internal IDs easily)
    # Test invalidate_all
    cache.invalidate_all()
    
    # Should be empty now
    assert cache.get(actor, "query1", "5") is None
    assert cache.get(actor, "query2", "5") is None
    
    stats = cache.stats()
    assert stats["entries"] == 0


def fake_id():
    """Generate a fake ID for testing."""
    import uuid
    return str(uuid.uuid4())


def test_loop_guard_init():
    guard = RetrievalLoopGuard()
    assert guard.enabled == True
    assert guard._history == {}


def test_loop_guard_disabled():
    guard = RetrievalLoopGuard(enabled=False)
    assert guard.enabled == False
    
    decision = guard.check("any query", user_id="alice", workspace_id="ws1")
    assert decision.allowed == True
    assert decision.reason == ""


def test_loop_guard_allows_first_query():
    guard = RetrievalLoopGuard()
    
    decision = guard.check(
        "First ever query",
        user_id="alice",
        workspace_id="ws1",
        session_id="sess123",
        agent_id="agent456"
    )
    
    assert decision.allowed == True
    assert decision.reason == ""
    
    # Should be recorded in history
    key = "alice:ws1:sess123:agent456"
    assert key in guard._history
    assert "First ever query" in guard._history[key]


def test_loop_guard_blocks_repeated_query():
    guard = RetrievalLoopGuard()
    
    user_id = "alice"
    workspace_id = "ws1"
    session_id = "sess123"
    agent_id = "agent456"
    query = "Repeated query that should be blocked"
    
    # First query - should be allowed
    decision1 = guard.check(query, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision1.allowed == True
    assert decision1.reason == ""
    
    # Second query with same content - should be blocked
    decision2 = guard.check(query, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision2.allowed == False
    assert "retrieval loop" in decision2.reason.lower()
    assert decision2.reason != ""
    
    # Third query - should also be blocked
    decision3 = guard.check(query, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision3.allowed == False


def test_loop_guard_allows_different_query():
    guard = RetrievalLoopGuard()
    
    user_id = "alice"
    workspace_id = "ws1"
    session_id = "sess123"
    agent_id = "agent456"
    
    query1 = "First query about topic A"
    query2 = "Second query about topic B"
    
    # First query
    decision1 = guard.check(query1, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision1.allowed == True
    
    # Different query - should be allowed
    decision2 = guard.check(query2, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision2.allowed == True
    
    # First query again - should be blocked (it's a repeat)
    decision3 = guard.check(query1, user_id=user_id, workspace_id=workspace_id,
                           session_id=session_id, agent_id=agent_id)
    assert decision3.allowed == False


def test_loop_guard_scope_isolation():
    guard = RetrievalLoopGuard()
    
    query = "Same query in different scopes"
    
    # Query for user Alice
    decision1 = guard.check(query, user_id="alice", workspace_id="ws1")
    assert decision1.allowed == True
    
    # Same query for user Bob - should be allowed (different user)
    decision2 = guard.check(query, user_id="bob", workspace_id="ws1")
    assert decision2.allowed == True
    
    # Alice again - should be blocked
    decision3 = guard.check(query, user_id="alice", workspace_id="ws1")
    assert decision3.allowed == False
    
    # Bob again - should be blocked
    decision4 = guard.check(query, user_id="bob", workspace_id="ws1")
    assert decision4.allowed == False


def test_loop_guard_custom_history_limit():
    guard = RetrievalLoopGuard()
    # Access private attribute to test - in practice we'd need a getter or different approach
    # For now, just test that it works
    decision = guard.check("test", user_id="alice")
    assert decision.allowed == True
    
    # Check that history was updated
    assert len(guard._history) > 0


def test_loop_decision_dataclass():
    decision = LoopDecision(
        allowed=True,
        reason="test reason"
    )
    
    assert decision.allowed == True
    assert decision.reason == "test reason"
    
    decision2 = LoopDecision(
        allowed=False,
        reason="another reason"
    )
    
    assert decision2.allowed == False
    assert decision2.reason == "another reason"


def test_loop_guard_integration_with_retrieval_result():
    guard = RetrievalLoopGuard()
    
    # Create a mock retrieval result that would be blocked
    decision = guard.check(
        "Loop query",
        user_id="alice",
        workspace_id="ws1"
    )
    # First call - allowed
    assert decision.allowed == True
    
    # Second call - should be blocked
    decision = guard.check(
        "Loop query",
        user_id="alice",
        workspace_id="ws1"
    )
    assert decision.allowed == False
    assert decision.reason != ""
    
    # Create a RetrievalResult with the loop guard reason
    result = RetrievalResult(
        query="Loop query",
        memories=[],
        total_found=0,
        loop_guard_reason=decision.reason
    )
    
    assert result.loop_guard_reason == decision.reason
    assert result.loop_guard_reason != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])