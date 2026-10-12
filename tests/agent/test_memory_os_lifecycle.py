"""Lifecycle: promotion, conflicts, dedup, expiry/decay, consolidation,
correction cascade (P17-18, P21, P24-26, P48-55)."""

import time

from agent.memory_os.lifecycle import Lifecycle
from agent.memory_os.manager import MemoryManager
from agent.memory_os.models import (
    Confidence,
    FeedbackKind,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    PreferenceKind,
    SourceType,
)
from agent.memory_os.security import AccessContext


def test_promotion_stops_at_candidate_without_user():
    m = MemoryManager()
    o = m.remember("User likes tea", source_type=SourceType.MODEL_INFERENCE,
                   semantic_key="pref:drink")
    assert o.effective_status is MemoryStatus.CANDIDATE
    d = m.lifecycle.promote(o.item)
    assert not d.approved and "approval" in d.reason


def test_promotion_with_user_approval_activates():
    m = MemoryManager()
    ctx = AccessContext.user()
    o = m.remember("User likes tea", source_type=SourceType.MODEL_INFERENCE,
                   semantic_key="pref:drink")
    item = m.confirm_candidate(o.item.memory_id, ctx, approve=True)
    assert item is not None and item.status is MemoryStatus.ACTIVE


def test_denied_candidate_is_forgotten():
    m = MemoryManager()
    ctx = AccessContext.user()
    o = m.remember("guess: user dislikes mornings",
                   source_type=SourceType.MODEL_INFERENCE)
    assert m.confirm_candidate(o.item.memory_id, ctx, approve=False) is None
    assert m.store.get_item(o.item.memory_id) is None


def test_session_memory_never_promotes_automatically():
    m = MemoryManager()
    o = m.remember("scratch note", scope=MemoryScope.SESSION)
    d = Lifecycle(m.store).promote(o.item)
    assert not d.approved


def test_conflict_detected_not_silently_overwritten():
    m = MemoryManager()
    ctx = AccessContext.user()
    v1 = m.remember("Preferred editor is vim", type_=MemoryType.PREFERENCE,
                    preference_kind=PreferenceKind.EXPLICIT,
                    semantic_key="pref:editor", ctx=ctx)
    v2 = m.remember("Preferred editor is emacs", type_=MemoryType.PREFERENCE,
                    preference_kind=PreferenceKind.EXPLICIT,
                    semantic_key="pref:editor", ctx=ctx)
    assert v2.conflict_with == v1.item.memory_id
    assert v2.item.status is MemoryStatus.CANDIDATE  # human must decide


def test_explicit_update_supersedes_and_preserves_history():
    m = MemoryManager()
    ctx = AccessContext.user()
    base = m.remember("Uses laptop X", semantic_key="device:laptop")
    updated = m.update(base.item.memory_id, "Uses laptop Y", ctx)
    assert updated.version == 2
    versions = m.versions(base.item.memory_id, ctx)
    assert any(v["version"] == 2 for v in versions)


def test_dedup_identical_content_merges_once():
    m = MemoryManager()
    a = m.remember("Team standup happens at 9:15", tags=["ritual"])
    b = m.remember("Team standup happens at 9:15", tags=["ritual"])
    assert b.merged_into == a.item.memory_id
    statuses = {i.memory_id: i.status for i in
                m.store.query_items(limit=50)}
    assert statuses[b.item.memory_id] is MemoryStatus.MERGED \
        if b.item.memory_id in statuses else True


def test_ttl_expiry_sweep_and_purge():
    m = MemoryManager()
    o = m.remember("temp cache hint", ttl_seconds=-1.0)
    expired = m.lifecycle.expire_sweep()
    assert o.item.memory_id in expired
    refreshed = m.store.get_item(o.item.memory_id)
    assert refreshed.status is MemoryStatus.EXPIRED
    assert m.lifecycle.purge_expired() >= 1
    assert m.store.get_item(o.item.memory_id) is None


def test_decay_skips_exempt_and_explicit_preferences():
    m = MemoryManager()
    old = time.time() - 90 * 86400
    pref = MemoryItem(content="always answer in German",
                      type=MemoryType.PREFERENCE,
                      preference_kind=PreferenceKind.EXPLICIT,
                      importance=0.2, created_at=old, updated_at=old,
                      last_accessed_at=old)
    scratch = MemoryItem(content="random scratch thought",
                         type=MemoryType.EPISODIC, importance=0.1,
                         created_at=old, updated_at=old,
                         last_accessed_at=old)
    for it in (pref, scratch):
        m.store.upsert_item(it)
    cands = m.lifecycle.decay_candidates(idle_days=30)
    ids = {c.memory_id for c in cands}
    assert scratch.memory_id in ids
    assert pref.memory_id not in ids


def test_feedback_useful_raises_importance_correction_supersedes():
    m = MemoryManager()
    o = m.remember("The API base url is https://api.example.com",
                   confidence=Confidence.HIGH)
    before_importance = o.item.importance
    it = m.lifecycle.apply_feedback(o.item, FeedbackKind.USEFUL)
    assert it.importance > before_importance
    bad = m.remember("Wrong fact that user corrects")
    fixed = m.lifecycle.apply_feedback(bad.item, FeedbackKind.INCORRECT)
    assert fixed.status is MemoryStatus.SUPERSEDED


def test_correction_cascades_to_derived():
    m = MemoryManager()
    root = m.remember("Server region is eu-west-1", semantic_key="infra:region")
    derived = MemoryItem(content="derived: latency stats for eu-west-1",
                         status=MemoryStatus.ACTIVE,
                         metadata={"derived_of": root.item.memory_id})
    m.store.upsert_item(derived)
    n = m.lifecycle.invalidate_derived(root.item.memory_id, [derived.memory_id])
    assert n == 1
    assert m.store.get_item(derived.memory_id).status is MemoryStatus.SUPERSEDED


def test_stale_detection_and_revalidation():
    m = MemoryManager()
    stale = MemoryItem(
        content="pricing as of 2025",
        type=MemoryType.TEMPORAL,
        created_at=time.time() - 120 * 86400,
        updated_at=time.time() - 120 * 86400,
        revalidate_after=time.time() - 3600,
    )
    m.store.upsert_item(stale)
    cands = m.lifecycle.stale_candidates()
    assert stale.memory_id in {c.memory_id for c in cands}
    ok_item = m.lifecycle.mark_revalidated(stale, True)
    assert ok_item.revalidate_after > time.time()


def test_consolidation_folds_episodes_into_candidate_semantic():
    m = MemoryManager()
    for i in range(4):
        e = MemoryItem(
            content=f"episodic deploy failure detail {i}",
            summary=f"deploy failed night {i}",
            type=MemoryType.EPISODIC,
            semantic_key="deploy-flaky",
            scope=MemoryScope.PROJECT, project_id="web",
        )
        e.provenance.actor = f"session-{i}"
        e.provenance.evidence_ids = [f"ev{i}"]
        m.store.upsert_item(e)
    produced = m.lifecycle.consolidate(min_events=3)
    assert len(produced) == 1
    c = produced[0]
    assert c.type is MemoryType.SEMANTIC
    assert c.status is MemoryStatus.CANDIDATE      # P18: still needs approval
    assert len(c.provenance.evidence_ids) >= 3     # provenance retained
