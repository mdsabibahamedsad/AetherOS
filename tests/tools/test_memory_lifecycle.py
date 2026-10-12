"""Acceptance tests for tools/memory_lifecycle.py.

E2E: exercise the real resolution chain (MemoryStore + lifecycle module) against
a temp AETHEROS_HOME. No mocks of the store.
"""

import json
import pytest

from tools.memory_tool import MemoryStore
from tools.memory_lifecycle import (
    maintain,
    lifecycle_stats,
    detect_conflicts,
    list_conflicts,
    resolve_conflicts,
    reconsolidate,
    apply_decay,
    purge_secrets,
    rank_search,
    build_index,
    extract_attributes,
    token_similarity,
    make_entry,
    entry_text,
    entry_metadata,
    permission_level,
    set_permission,
    share_entry,
    visible_entries,
)


def _fresh_store() -> MemoryStore:
    store = MemoryStore()
    store.load_from_disk()
    return store


# =========================================================================
# Conflict detection
# =========================================================================

class TestDetectConflicts:
    def test_attribute_conflict(self):
        store = _fresh_store()
        store.add("user", "User name is Alice.")
        hits = detect_conflicts(store, "user", "User name is Bob.")
        kinds = [h["kind"] for h in hits]
        assert "attribute" in kinds
        attr = next(h for h in hits if h["kind"] == "attribute")
        assert attr["attr"] == "name"
        assert attr["old_value"] == "alice"
        assert attr["new_value"] == "bob"

    def test_polarity_conflict(self):
        store = _fresh_store()
        store.add("memory", "User uses Python for backend work.")
        hits = detect_conflicts(
            store, "memory", "User does not use Python for backend work."
        )
        assert any(h["kind"] == "polarity" for h in hits)

    def test_near_duplicate(self):
        store = _fresh_store()
        store.add("memory", "User prefers dark mode in editors.")
        hits = detect_conflicts(store, "memory", "User prefers dark mode in all editors.")
        assert any(h["kind"] == "near_duplicate" for h in hits)

    def test_exact_duplicate_not_reported_as_conflict(self):
        store = _fresh_store()
        store.add("memory", "User prefers dark mode.")
        hits = detect_conflicts(store, "memory", "User prefers dark mode.")
        assert hits == []


class TestListConflicts:
    def test_reports_attribute_and_polarity_across_targets(self):
        store = _fresh_store()
        store.add("user", "User name is Alice.")
        store.add("user", "User name is Bob.", metadata={"source": "conflict"})
        store.add("memory", "User uses Python for backend work.")
        store.add("memory", "User does not use Python for backend work.", metadata={"source": "negation"})
        report = list_conflicts(store)
        kinds = [c["kind"] for c in report["conflicts"]]
        assert "attribute" in kinds and "polarity" in kinds
        assert report["count"] >= 2


# =========================================================================
# Conflict resolution
# =========================================================================

class TestResolveConflicts:
    def test_resolve_attribute_pair_keeps_one(self):
        store = _fresh_store()
        store.add("user", "User name is Alice.")
        store.add("user", "User name is Bob.", metadata={"source": "conflict"})
        report = resolve_conflicts(store, "user")
        assert report["resolved"] == 1
        remaining = [entry_text(e) for e in store._entries_for("user", "default")]
        assert len(remaining) == 1
        assert "Bob" in remaining[0]

    def test_resolve_polarity_pair(self):
        store = _fresh_store()
        store.add("memory", "User uses Python for backend work.")
        store.add("memory", "User does not use Python for backend work.", metadata={"source": "negation"})
        report = resolve_conflicts(store, "memory")
        assert report["resolved"] == 1
        remaining = [entry_text(e) for e in store._entries_for("memory", "default")]
        assert len(remaining) == 1

    def test_dry_run_does_not_mutate(self):
        store = _fresh_store()
        store.add("user", "User name is Alice.")
        store.add("user", "User name is Bob.", metadata={"source": "conflict"})
        report = resolve_conflicts(store, "user", dry_run=True)
        assert report["resolved"] == 1
        assert len(store._entries_for("user", "default")) == 2

    def test_antonym_pair_not_merged_by_reconsolidate_default(self):
        store = _fresh_store()
        store.add("memory", "User prefers dark mode in editors.")
        store.add("memory", "User prefers light mode in editors.", metadata={"source": "antonym"})
        report = reconsolidate(store)
        assert report["merged"] == 0
        assert len(store._entries_for("memory", "default")) == 2


# =========================================================================
# Reconsolidation
# =========================================================================

class TestReconsolidate:
    def test_merges_exact_near_duplicates(self):
        store = _fresh_store()
        store.add("memory", "User prefers dark mode in editors.")
        store.add("memory", "User prefers dark mode in all editors.", metadata={"source": "dup"})
        report = reconsolidate(store)
        assert report["merged"] == 1
        assert len(store._entries_for("memory", "default")) == 1

    def test_pinned_entries_survive_budget_reclaim(self):
        store = _fresh_store()
        store.add("memory", "User pinned fact that must survive.",
                  metadata={"pinned": True, "confidence": 0.1})
        for i in range(30):
            store.add("memory", f"Low priority filler fact number {i}.",
                      metadata={"confidence": 0.1})
        store._set_entries("memory", store._entries_for("memory", "default"), "default")
        before_pinned = sum(
            1 for e in store._entries_for("memory", "default")
            if entry_metadata(e).get("pinned")
        )
        report = reconsolidate(store)
        assert report["archived"] >= 0
        remaining = store._entries_for("memory", "default")
        pinned_now = [e for e in remaining if entry_metadata(e).get("pinned")]
        assert len(pinned_now) == before_pinned
        assert "pinned fact" in entry_text(pinned_now[0])


# =========================================================================
# Decay
# =========================================================================

class TestApplyDecay:
    def test_recent_entries_not_decayed(self):
        store = _fresh_store()
        store.add("memory", "Fresh fact recorded today.",
                  metadata={"created_at": __import__("time").time(), "confidence": 0.9})
        report = apply_decay(store, halflife_days=90.0)
        assert report["decayed"] == 0

    def test_stale_entries_archived_via_ttl(self):
        store = _fresh_store()
        import time
        old = time.time() - 60 * 60 * 24 * 400  # 400 days ago
        store.add("memory", "Ancient fact that should have expired.",
                  metadata={"updated_at": old, "ttl": 3600, "confidence": 0.5})
        report = apply_decay(store, halflife_days=90.0)
        # TTL (1 hour) has long elapsed → archived (not counted as decayed).
        assert report["archived"] == 1

    def test_stale_entries_decay_confidence(self):
        store = _fresh_store()
        import time
        old = time.time() - 60 * 60 * 24 * 400  # 400 days ago, no TTL
        store.add("memory", "Old fact with decaying confidence.",
                  metadata={"updated_at": old, "confidence": 0.9})
        report = apply_decay(store, halflife_days=90.0)
        assert report["decayed"] == 1
        remaining = store._entries_for("memory", "default")
        assert remaining, "decayed entry survives (just loses confidence)"
        assert entry_metadata(remaining[0])["confidence"] < 0.9


# =========================================================================
# Secrets
# =========================================================================

class TestPurgeSecrets:
    def test_redacts_api_key_like_tokens(self):
        store = _fresh_store()
        store.add("memory", "The key is sk-test1234abcdefghijklmnop and must be rotated.")
        report = purge_secrets(store, mode="redact")
        assert report["found"] >= 1
        assert report["redacted"] >= 1
        remaining = store._entries_for("memory", "default")
        assert remaining, "entry should survive, only the secret should be redacted"
        assert "sk-test1234abcdefghijklmnop" not in "\n".join(remaining)


# =========================================================================
# Search / ranking
# =========================================================================

class TestRankSearch:
    def test_relevant_entry_ranks_first(self):
        store = _fresh_store()
        store.add("memory", "User works at Acme Corporation.")
        store.add("memory", "User prefers dark mode in editors.")
        hits = rank_search(store, "prefers dark mode")
        assert hits, "should return ranked results"
        assert "dark mode" in hits[0]["text"]

    def test_build_index_includes_entries(self):
        store = _fresh_store()
        store.add("memory", "User works at Acme Corporation.")
        index = build_index(store)
        assert isinstance(index, dict)
        assert any(
            (tgt, scp, pos) for tgt, scp, pos in _flatten_index(index)
            if scp == "default"
        )


def _flatten_index(index):
    """Yield every (target, scope, position) tuple in a token index."""
    for _tok, refs in index.items():
        for ref in refs:
            yield ref


# =========================================================================
# Attributes & tokens
# =========================================================================

class TestExtractAttributes:
    def test_extracts_name(self):
        assert extract_attributes("User name is Alice.") == [("name", "alice")]

    def test_extracts_company(self):
        assert ("company", "acme") in extract_attributes("User company is Acme.")

    def test_empty_on_no_attribute(self):
        assert extract_attributes("Remember to commit before lunch.") == []


class TestTokenSimilarity:
    def test_identical_is_one(self):
        assert token_similarity("User prefers dark mode.", "User prefers dark mode.") == 1.0

    def test_disjoint_is_zero(self):
        assert token_similarity("alpha beta", "gamma delta") == 0.0


# =========================================================================
# Permissions
# =========================================================================

class TestPermissions:
    def test_permission_levels(self):
        assert permission_level("private") == 0
        assert permission_level("shared") == 1
        assert permission_level("public") == 2
        assert permission_level("agent") == 3

    def test_share_entry_grants_visibility(self):
        store = _fresh_store()
        store.add("memory", "Shared fact.")
        share_entry(store, "memory", "Shared fact", with_owner="other_agent")
        visible = visible_entries(store, "memory", owner="other_agent")
        assert any("Shared fact" in entry_text(e) for e in visible)

    def test_private_not_visible_to_other_agent(self):
        store = _fresh_store()
        store.add("memory", "Private fact.",
                  metadata={"owner": "main_agent", "permission": "private"})
        visible = visible_entries(store, "memory", owner="other_agent")
        assert all("Private fact" not in entry_text(e) for e in visible)
        # The owner still sees it.
        assert any("Private fact" in entry_text(e)
                   for e in visible_entries(store, "memory", owner="main_agent"))


# =========================================================================
# Full maintenance pass
# =========================================================================

class TestMaintain:
    def test_maintain_resolves_and_reports(self):
        store = _fresh_store()
        store.add("user", "User name is Alice.")
        store.add("user", "User name is Bob.", metadata={"source": "conflict"})
        report = maintain(store, dry_run=True)
        assert report["dry_run"] is True
        assert report["conflicts"]["resolved"] == 1

    def test_maintain_live_is_invariant_safe(self):
        store = _fresh_store()
        store.add("memory", "User works at Acme Corporation.")
        store.add("memory", "User prefers dark mode in editors.")
        report = maintain(store)
        # No conflicts introduced; the two distinct facts survive.
        assert report["conflicts"]["resolved"] == 0
        remaining = [entry_text(e) for e in store._entries_for("memory", "default")]
        assert len(remaining) == 2
        assert any("dark mode" in t for t in remaining)
        assert any("Acme" in t for t in remaining)

    def test_lifecycle_stats_shape(self):
        store = _fresh_store()
        store.add("memory", "User prefers dark mode.")
        stats = lifecycle_stats(store)
        assert stats["total"] == 1
        assert stats["by_target"]["memory"] == 1
        assert stats["by_permission"].get("private") == 1
        assert stats["avg_confidence"] >= 0.0
