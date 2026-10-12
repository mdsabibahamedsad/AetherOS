"""Tests for aetheros_integrations.context — offline queue and integration memory."""

import time

import pytest

from aetheros_integrations.context import IntegrationMemory, OfflineQueue


@pytest.fixture
def settings():
    from aetheros_integrations.config import IntegrationsSettings

    return IntegrationsSettings(data_dir="integrations")


class TestOfflineQueue:
    def test_enqueue_and_pending(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)
        item = q.enqueue("i1", "send_message", {"text": "hello"})
        pending = q.list_pending()
        assert [p.id for p in pending] == [item.id]

    def test_enqueue_dedup(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)
        first = q.enqueue("i1", "send_message", {"text": "x"}, dedup_key="dup-1")
        second = q.enqueue("i1", "send_message", {"text": "x"}, dedup_key="dup-1")
        assert first.id == second.id
        assert len(q.list_pending()) == 1

    def test_flush_delivers(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)
        processed = []

        def processor(item):
            processed.append(item.id)

        q.set_processor(processor)
        item = q.enqueue("i1", "send_message", {"text": "hi"})
        item.next_retry_at = time.time() - 1
        result = q.flush()
        assert result["delivered"] == 1
        assert result["dead"] == 0
        assert q.get(item.id).status == "done"

    def test_flush_dead_after_max_attempts(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)
        calls = []

        def processor(item):
            calls.append(1)
            raise RuntimeError("provider down")

        q.set_processor(processor)
        item = q.enqueue("i1", "send_message", {"text": "hi"})
        item.max_attempts = 2
        item.next_retry_at = time.time() - 1
        q.flush()
        assert q.get(item.id).status == "queued"  # one attempt, exponential backoff applied
        item.next_retry_at = time.time() - 1  # simulate backoff elapsed
        q.flush()
        assert q.get(item.id).status == "dead"
        assert q.get(item.id).attempts == 2

    def test_flush_skips_future_items(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)

        def processor(item):
            raise AssertionError("should not run")

        q.set_processor(processor)
        item = q.enqueue("i1", "send_message", {"text": "hi"})
        item.next_retry_at = time.time() + 10000
        q.flush()
        assert q.get(item.id).status == "queued"

    def test_stats(self, tmp_path, settings):
        q = OfflineQueue(dirpath=tmp_path, settings=settings)
        q.enqueue("i1", "send_message", {"text": "a"})
        q.enqueue("i1", "send_message", {"text": "b"})
        stats = q.stats()
        assert stats["queued"] == 2
        assert stats["total"] == 2


class TestIntegrationMemory:
    def test_store_and_get(self, tmp_path):
        mem = IntegrationMemory(dirpath=tmp_path)
        mem.store("digest", "here is the content", source="workflow")
        record = mem.get("digest")
        assert record["content"] == "here is the content"
        assert record["source"] == "workflow"

    def test_search(self, tmp_path):
        mem = IntegrationMemory(dirpath=tmp_path)
        mem.store("summary-1", "The build succeeded today")
        mem.store("summary-2", "Nothing noteworthy")
        results = mem.search("build")
        assert len(results) == 1
        assert results[0]["key"] == "summary-1"

    def test_memory_persists(self, tmp_path):
        mem1 = IntegrationMemory(dirpath=tmp_path)
        mem1.store("k", "value", source="s")
        mem2 = IntegrationMemory(dirpath=tmp_path)
        assert mem2.get("k")["content"] == "value"
