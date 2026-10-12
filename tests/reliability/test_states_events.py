"""Tests for the recovery state machine and event schema."""

import pytest

from aetheros_reliability.events import (
    RecoveryEvent,
    RecoveryEventStore,
    RecoveryResult,
)
from aetheros_reliability.states import (
    RecoveryState,
    RecoveryStateMachine,
)


class TestRecoveryStateMachine:
    def test_initial_state_normal(self):
        sm = RecoveryStateMachine()
        assert sm.state == RecoveryState.NORMAL

    def test_valid_sequence(self):
        sm = RecoveryStateMachine()
        sm.enter(RecoveryState.FAILURE_DETECTED, reason="gateway crash")
        sm.enter(RecoveryState.DIAGNOSING)
        sm.enter(RecoveryState.RECOVERING)
        sm.enter(RecoveryState.VERIFYING)
        sm.enter(RecoveryState.RECOVERED)
        assert sm.state == RecoveryState.RECOVERED

    def test_illegal_transition_raises(self):
        sm = RecoveryStateMachine()
        with pytest.raises(ValueError):
            sm.enter(RecoveryState.RECOVERED)

    def test_force_transition_allowed(self):
        sm = RecoveryStateMachine()
        record = sm.enter(RecoveryState.SAFE_MODE, reason="operator", force=True)
        assert sm.state == RecoveryState.SAFE_MODE
        assert record.operator is True

    def test_can_enter(self):
        sm = RecoveryStateMachine()
        assert sm.can_enter(RecoveryState.DEGRADED)
        assert not sm.can_enter(RecoveryState.RECOVERY_MODE)

    def test_history_records_transitions(self):
        sm = RecoveryStateMachine()
        sm.enter(RecoveryState.FAILURE_DETECTED)
        sm.enter(RecoveryState.DIAGNOSING)
        history = sm.history()
        assert len(history) == 2
        assert history[0]["to"] == "failure_detected"

    def test_in_recovery(self):
        sm = RecoveryStateMachine()
        assert not sm.in_recovery()
        sm.enter(RecoveryState.FAILURE_DETECTED)
        assert sm.in_recovery()

    def test_snapshot_shape(self):
        sm = RecoveryStateMachine()
        snap = sm.snapshot()
        assert snap["state"] == "normal"
        assert "history" in snap and "since" in snap


class TestRecoveryEvent:
    def test_event_fields(self):
        ev = RecoveryEvent(
            component_id="gateway",
            failure_type="CRASH",
            action="restart",
            diagnosis="heartbeat timeout",
            attempt=2,
        )
        d = ev.to_dict()
        assert d["componentId"] == "gateway"
        assert d["failureType"] == "CRASH"
        assert d["attempt"] == 2
        assert d["recoveryId"]

    def test_event_from_dict_roundtrip(self):
        ev = RecoveryEvent(
            component_id="backend",
            failure_type="OOM",
            action="restart",
            verified=True,
        )
        restored = RecoveryEvent.from_dict(ev.to_dict())
        assert restored.component_id == "backend"
        assert restored.verified is True

    def test_event_store_ring_bounded(self):
        store = RecoveryEventStore(max_events=5)
        for i in range(10):
            store.record(RecoveryEvent(
                component_id=f"c{i}", failure_type="T", action="restart",
            ))
        assert len(store.recent(100)) == 5

    def test_event_store_for_component(self):
        store = RecoveryEventStore()
        store.record(RecoveryEvent(component_id="gateway", failure_type="C", action="r"))
        store.record(RecoveryEvent(component_id="backend", failure_type="C", action="r"))
        assert len(store.for_component("gateway")) == 1

    def test_recovery_result_values(self):
        assert RecoveryResult.SUCCESS.value == "success"
        assert RecoveryResult.BLOCKED.value == "blocked"
