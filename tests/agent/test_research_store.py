"""Tests for the SQLite research store: persistence, idempotency, resume."""

import time

import pytest

from agent.research.models import (
    Claim,
    Evidence,
    ResearchDepth,
    ResearchSource,
    ResearchTask,
    TaskStatus,
)
from agent.research.state import StateTransition
from agent.research.store import ResearchStore


@pytest.fixture
def store(tmp_path):
    s = ResearchStore(db_path=tmp_path / "research.db")
    yield s
    s.close()


class TestTasks:
    def test_create_get_round_trip(self, store):
        task = ResearchTask(user_query="why is the sky blue", depth=ResearchDepth.DEEP)
        store.create_task(task)
        loaded = store.get_task(task.research_id)
        assert loaded.user_query == "why is the sky blue"
        assert loaded.depth == ResearchDepth.DEEP
        assert loaded.status == TaskStatus.CREATED

    def test_save_updates_and_lists(self, store):
        task = ResearchTask(user_query="q1")
        store.create_task(task)
        task.status = TaskStatus.SEARCHING
        store.save_task(task)
        tasks = store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.SEARCHING
        assert store.find_latest_by_query("q1").research_id == task.research_id
        assert store.find_latest_by_query("missing") is None

    def test_list_excludes_terminal_when_requested(self, store):
        done = ResearchTask(user_query="done")
        done.status = TaskStatus.COMPLETED
        running = ResearchTask(user_query="running")
        running.status = TaskStatus.SEARCHING
        for t in (done, running):
            store.create_task(t)
        ids = {t.research_id for t in store.list_tasks(include_terminal=False)}
        assert running.research_id in ids
        assert done.research_id not in ids

    def test_resumable_excludes_created_and_terminal(self, store):
        fresh = ResearchTask(user_query="fresh")
        mid = ResearchTask(user_query="mid")
        mid.status = TaskStatus.PAUSED
        done = ResearchTask(user_query="done")
        done.status = TaskStatus.FAILED
        for t in (fresh, mid, done):
            store.create_task(t)
        ids = {t.research_id for t in store.resumable_tasks()}
        assert ids == {mid.research_id}


class TestTransitions:
    def test_recorded_in_order(self, store):
        rid = "abc123"
        for i, (frm, to) in enumerate(
            [("CREATED", "PLANNING"), ("PLANNING", "SEARCHING")]
        ):
            store.record_transition(
                StateTransition(task_id=rid, from_status=frm, to_status=to)
            )
        events = store.get_transitions(rid)
        assert [e.to_status for e in events] == ["PLANNING", "SEARCHING"]
        assert events[0].timestamp <= events[1].timestamp


class TestSources:
    def _source(self, url, **kw):
        return ResearchSource(url=url, **kw)

    def test_upsert_idempotent_per_page_key(self, store):
        first = self._source("https://example.com/a?utm_campaign=x")
        second = self._source("https://www.example.com/a")
        assert store.upsert_source("t", first) is True
        assert store.upsert_source("t", second) is False
        sources = store.list_sources("t")
        assert len(sources) == 1
        assert sources[0].source_id == first.source_id

    def test_refresh_updates_hash_keeps_identity(self, store):
        src = self._source("https://example.com/doc")
        store.upsert_source("t", src)
        original_id = src.source_id
        src.content_hash = "cafebabe"
        store.upsert_source("t", src)
        rows = store.list_sources("t")
        assert len(rows) == 1
        assert rows[0].source_id == original_id
        assert rows[0].content_hash == "cafebabe"

    def test_same_page_different_tasks_are_distinct(self, store):
        assert store.upsert_source("taskA", self._source("https://x.test/p")) is True
        assert store.upsert_source("taskB", self._source("https://x.test/p")) is True

    def test_count_sources_with_hash(self, store):
        a = self._source("https://a.test/1", content_hash="h")
        b = self._source("https://b.test/2", content_hash="h")
        c = self._source("https://c.test/3", content_hash="other")
        for s in (a, b, c):
            store.upsert_source("t", s)
        assert store.count_sources_with_hash("t", "h") == 2


class TestClaimsAndEvidence:
    def test_claim_text_idempotent_normalized(self, store):
        a = Claim(text="The widget supports retries.")
        b = Claim(text="  the   widget supports retries. ")
        assert store.add_claim("t", a) is True
        assert store.add_claim("t", b) is False
        assert b.claim_id == a.claim_id
        assert len(store.list_claims("t")) == 1

    def test_evidence_dedup_same_slot(self, store):
        claim = Claim(text="Something verifiable about results.")
        store.add_claim("t", claim)
        e1 = Evidence(claim_id=claim.claim_id, source_id="s1", location="sentence:0")
        e2 = Evidence(claim_id=claim.claim_id, source_id="s1", location="sentence:0")
        e3 = Evidence(claim_id=claim.claim_id, source_id="s2", location="sentence:0")
        assert store.add_evidence("t", e1) is True
        assert store.add_evidence("t", e2) is False
        assert store.add_evidence("t", e3) is True
        assert len(store.list_evidence("t")) == 2

    def test_update_claim_persists_status(self, store):
        claim = Claim(text="A claim that will be confirmed later on.")
        store.add_claim("t", claim)
        from agent.research.models import ClaimStatus

        claim.status = ClaimStatus.CONFIRMED
        claim.confidence = 0.9
        store.update_claim("t", claim)
        loaded = store.list_claims("t")[0]
        assert loaded.status == ClaimStatus.CONFIRMED
        assert loaded.confidence == pytest.approx(0.9)


class TestUsage:
    def test_usage_counts(self, store):
        task = ResearchTask(user_query="u")
        store.create_task(task)
        store.log_event(task.research_id, "query", "q one")
        store.log_event(task.research_id, "query", "q two")
        store.log_event(task.research_id, "query", "q two")
        src = ResearchSource(url="https://u.test/1", content_hash="x")
        store.upsert_source(task.research_id, src)
        usage = store.usage(task.research_id)
        assert usage["queries"] == 2
        assert usage["pages"] == 1

    def test_events_round_trip(self, store):
        task = ResearchTask(user_query="e")
        store.create_task(task)
        store.log_event(task.research_id, "phase", "SEARCHING")
        events = store.get_events(task.research_id)
        assert events and events[0]["kind"] == "phase"
