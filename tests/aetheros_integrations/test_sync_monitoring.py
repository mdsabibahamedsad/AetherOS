"""Tests for aetheros_integrations.sync and monitoring."""

import time

import pytest

from aetheros_integrations.monitoring import Monitor
from aetheros_integrations.sync import SyncEngine


@pytest.fixture
def settings():
    from aetheros_integrations.config import IntegrationsSettings

    return IntegrationsSettings(data_dir="integrations")


class TestSyncEngine:
    def test_cursor_default_empty(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)
        assert sync.get_cursor("s1") == ""

    def test_set_and_get_cursor(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)
        sync.set_cursor("s1", "cursor-123")
        assert sync.get_cursor("s1") == "cursor-123"

    def test_pull_detects_new_records(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)

        def fetch(cursor):
            return [
                {"id": "1", "cursor": "c1"},
                {"id": "2", "cursor": "c2"},
            ]

        result = sync.pull("s1", fetch, key_fn=lambda r: r["id"])
        assert result["new"] == 2
        assert result["fetched"] == 2
        assert result["cursor"] == "c2"

    def test_pull_incremental_skips_seen(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)
        sync.mark_seen("s1", "1")

        def fetch(cursor):
            return [{"id": "1", "cursor": "c1"}, {"id": "2", "cursor": "c2"}]

        result = sync.pull("s1", fetch, key_fn=lambda r: r["id"])
        assert result["new"] == 1
        assert result["seen"] == 1

    def test_mark_seen_and_is_seen(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)
        assert sync.is_seen("s1", "abc") is False
        sync.mark_seen("s1", "abc", meta={"kind": "issue"})
        assert sync.is_seen("s1", "abc") is True

    def test_stats(self, tmp_path, settings):
        sync = SyncEngine(dirpath=tmp_path, settings=settings)
        sync.mark_seen("s1", "a")
        sync.mark_seen("s1", "b")
        sync.set_cursor("s1", "cur")
        stats = sync.stats("s1")
        assert stats["seen"] == 2
        assert stats["cursor"] == "cur"


class TestMonitor:
    def test_record_and_query(self, tmp_path, settings):
        mon = Monitor(dirpath=tmp_path, settings=settings)
        mon.record("i1", "latency_ms", 12.5)
        mon.record("i1", "failure")
        samples = mon.query(integration_id="i1")
        assert len(samples) == 2
        assert mon.query(metric="failure")[0].metric == "failure"

    def test_recorder_helpers(self, tmp_path, settings):
        mon = Monitor(dirpath=tmp_path, settings=settings)
        mon.record_api_error("i1", 429, "rate limited")
        mon.record_failure("i1", "timeout")
        mon.record_retry("i1", 2)
        mon.record_quota("i1", 60, 100)
        assert len(mon.query(integration_id="i1")) == 4
        assert mon.query(metric="api_error")[0].extra["status"] == 429

    def test_summary(self, tmp_path, settings):
        mon = Monitor(dirpath=tmp_path, settings=settings)
        mon.record("i1", "latency_ms", 10)
        mon.record("i1", "latency_ms", 20)
        mon.record_failure("i1", "x")
        mon.record_retry("i1", 1)
        summary = mon.summary("i1")
        assert summary["samples"] == 4
        assert summary["failures"] == 1
        assert summary["retries"] == 1
        assert summary["avg_latency_ms"] == 15.0
        assert summary["max_latency_ms"] == 20.0

    def test_retention_pruning(self, tmp_path, settings):
        settings.monitoring.retention_s = 0.001
        mon = Monitor(dirpath=tmp_path, settings=settings)
        mon.record("i1", "latency_ms", 10)
        time.sleep(0.01)
        mon.record("i1", "latency_ms", 20)  # triggers prune; old sample dropped
        assert len(mon.query(integration_id="i1")) <= 1
