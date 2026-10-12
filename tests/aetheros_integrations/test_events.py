"""Tests for aetheros_integrations.events — pub/sub, dedup, history, replay."""

import pytest

from aetheros_integrations.events import EventBus


@pytest.fixture
def bus(tmp_path):
    return EventBus(dirpath=tmp_path)


class TestPublishSubscribe:
    def test_subscriber_receives_event(self, bus):
        received = []

        def handler(envelope):
            received.append(envelope)

        bus.subscribe("email.received", handler)
        bus.publish("email.received", {"from": "a@b.c"}, kind="provider", source="gmail")
        assert len(received) == 1
        assert received[0].data["from"] == "a@b.c"
        assert received[0].type == "email.received"

    def test_wildcard_receives_all(self, bus):
        received = []

        def handler(envelope):
            received.append(envelope)

        bus.subscribe_wildcard(handler)
        bus.publish("a", {"n": 1})
        bus.publish("b", {"n": 2})
        assert len(received) == 2

    def test_unsubscribe(self, bus):
        received = []

        def handler(envelope):
            received.append(envelope)

        bus.subscribe("t", handler)
        assert bus.unsubscribe("t", handler) is True
        bus.publish("t", {})
        assert received == []

    def test_other_type_not_delivered(self, bus):
        received = []

        def handler(envelope):
            received.append(envelope)

        bus.subscribe("email.received", handler)
        bus.publish("other.event", {})
        assert received == []


class TestDedup:
    def test_duplicate_publish_deduped(self, bus):
        first = bus.publish("t", {"a": 1}, dedup_key="k1")
        second = bus.publish("t", {"a": 1}, dedup_key="k1")
        assert first.id == second.id
        assert len(bus.history()) == 1

    def test_distinct_payload_not_deduped(self, bus):
        bus.publish("t", {"a": 1}, dedup_key="k1")
        bus.publish("t", {"a": 2}, dedup_key="k2")
        assert len(bus.history()) == 2


class TestHistoryAndReplay:
    def test_history_filter(self, bus):
        bus.publish("t1", {"n": 1}, dedup_key="a")
        bus.publish("t2", {"n": 2}, dedup_key="b")
        assert len(bus.history()) == 2
        assert len(bus.history(event_type="t1")) == 1

    def test_replay_to_handler(self, bus):
        bus.publish("t1", {"n": 1}, dedup_key="a")
        replayed = []

        def handler(envelope):
            replayed.append(envelope)

        count = bus.replay(handler=handler)
        assert count == 1
        assert len(replayed) == 1

    def test_stats(self, bus):
        bus.publish("t1", {}, dedup_key="a")
        bus.publish("t1", {}, dedup_key="b")
        bus.publish("t2", {}, dedup_key="c")
        stats = bus.stats()
        assert stats["total"] == 3
        assert stats["by_type"]["t1"] == 2
        assert stats["by_type"]["t2"] == 1


class TestPersistence:
    def test_history_persists_across_instances(self, tmp_path):
        bus1 = EventBus(dirpath=tmp_path)
        bus1.publish("t1", {"n": 1}, dedup_key="persist-key")
        bus2 = EventBus(dirpath=tmp_path)
        history = bus2.history(event_type="t1")
        assert len(history) == 1
        assert history[0].data["n"] == 1
