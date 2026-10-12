"""Master-13 slice 2: event bus, trigger specs and structured filters."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.events import (
    MAX_PAYLOAD_CHARS,
    AutomationBus,
    publish_external,
    reset_bus,
)


@pytest.fixture(autouse=True)
def fresh_bus():
    reset_bus()
    yield
    reset_bus()


class TestAutomationBus:
    def test_publish_envelope(self):
        bus = AutomationBus()
        evt = bus.publish("task.failed", {"code": 7}, source="scheduler")
        assert evt.event_type == "task.failed"
        assert evt.payload == {"code": 7}
        assert evt.source == "scheduler"
        assert evt.trust == "internal"
        assert evt.event_id

    def test_subscribe_receives(self):
        bus = AutomationBus()
        seen = []
        bus.subscribe(seen.append)
        evt = bus.publish("file.created", {"path": "/x"})
        assert seen == [evt]

    def test_dedup_on_event_id(self):
        bus = AutomationBus()
        first = bus.publish("webhook.received", {}, event_id="abc")
        second = bus.publish("webhook.received", {}, event_id="abc")
        assert first is not None and second is None

    def test_trust_normalized(self):
        bus = AutomationBus()
        ext = publish_external("file.modified", {})
        assert ext.trust == "external"

    def test_external_payload_capped(self):
        bus = AutomationBus()
        evt = bus.publish(
            "file.created",
            {"blob": "x" * (MAX_PAYLOAD_CHARS * 3)},
            trust="external",
        )
        assert len(evt.payload["blob"]) <= MAX_PAYLOAD_CHARS

    def test_recent_newest_first(self):
        bus = AutomationBus()
        for i in range(3):
            bus.publish(f"e{i}", {"i": i})
        recent = bus.recent(limit=2)
        assert [e["event_type"] for e in recent] == ["e2", "e1"]

    def test_handler_exception_does_not_break_others(self):
        bus = AutomationBus()
        seen = []

        def boom(_evt):
            raise RuntimeError("boom")

        bus.subscribe(boom)
        bus.subscribe(seen.append)
        bus.publish("x.y")
        assert len(seen) == 1


def _trigger(**overrides):
    base = {
        "kind": "event",
        "event_types": ["task.failed"],
        "filters": [],
    }
    base.update(overrides)
    return base


class TestNormalizeTrigger:
    def test_empty_forms_are_none(self):
        from automation.triggers import normalize_trigger

        assert normalize_trigger(None) is None
        assert normalize_trigger({}) is None
        assert normalize_trigger({"kind": "manual"}) is None

    def test_invalid_kind_raises(self):
        from automation.triggers import normalize_trigger

        with pytest.raises(ValueError):
            normalize_trigger({"kind": "cron"})

    def test_requires_event_types(self):
        from automation.triggers import normalize_trigger

        with pytest.raises(ValueError):
            normalize_trigger({"kind": "event"})

    def test_comma_string_types(self):
        from automation.triggers import normalize_trigger

        spec = normalize_trigger({"kind": "event", "event_types": "a.b, c.d"})
        assert spec["event_types"] == ["a.b", "c.d"]

    def test_filter_shorthand_and_ops_validated(self):
        from automation.triggers import normalize_trigger

        spec = normalize_trigger({
            "kind": "event",
            "event_types": ["t"],
            "filters": {"payload.status": "failed"},
        })
        assert spec["filters"] == [{"path": "payload.status", "op": "eq", "value": "failed"}]

        with pytest.raises(ValueError):
            normalize_trigger({
                "kind": "event",
                "event_types": ["t"],
                "filters": [{"path": "p", "op": "regex", "value": ".*"}],
            })

    def test_negative_cooldown_raises(self):
        from automation.triggers import normalize_trigger

        with pytest.raises(ValueError):
            normalize_trigger({
                "kind": "event",
                "event_types": ["t"],
                "cooldown_seconds": -5,
            })


class TestEventMatches:
    def _evt(self, **overrides):
        base = {
            "event_type": "task.failed",
            "trust": "internal",
            "payload": {"status": "failed", "retries": 2},
        }
        base.update(overrides)
        return base

    def test_type_gate(self):
        from automation.triggers import event_matches

        assert not event_matches(_trigger(event_types=["other"]), self._evt())

    def test_internal_always_allowed(self):
        from automation.triggers import event_matches

        assert event_matches(_trigger(), self._evt())

    def test_external_requires_opt_in(self):
        from automation.triggers import event_matches

        ext = self._evt(trust="external")
        assert not event_matches(_trigger(), ext)
        assert event_matches(_trigger(allow_untrusted=True), ext)

    def test_operators(self):
        from automation.triggers import event_matches

        eq = _trigger(filters=[{"path": "payload.status", "op": "eq", "value": "failed"}])
        ne = _trigger(filters=[{"path": "payload.status", "op": "ne", "value": "ok"}])
        inop = _trigger(filters=[{"path": "payload.retries", "op": "in", "value": [2, 3]}])
        prefix = _trigger(filters=[{"path": "payload.status", "op": "prefix", "value": "fail"}])
        exists = _trigger(filters=[{"path": "payload.missing", "op": "exists"}])
        missing_neq = _trigger(filters=[{"path": "payload.missing", "op": "ne", "value": "x"}])

        for passing in (eq, ne, inop, prefix):
            assert event_matches(passing, self._evt())
        assert not event_matches(exists, self._evt())
        # Fail closed: a filter on an absent path blocks the match.
        assert not event_matches(missing_neq, self._evt())

    def test_all_filters_must_pass(self):
        from automation.triggers import event_matches

        both = _trigger(filters=[
            {"path": "payload.status", "op": "eq", "value": "failed"},
            {"path": "payload.retries", "op": "eq", "value": 9},
        ])
        assert not event_matches(both, self._evt())

    def test_event_scope_paths(self):
        from automation.triggers import event_matches

        flt = _trigger(filters=[{"path": "event.source", "op": "prefix", "value": "webhook:"}])
        assert event_matches(flt, self._evt(source="webhook:alerts"))

    def test_non_event_trigger_never_matches(self):
        from automation.triggers import event_matches

        assert not event_matches({"kind": "manual"}, self._evt())
        assert not event_matches(None, self._evt())
