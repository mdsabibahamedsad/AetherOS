"""Tests for the unified agent lifecycle state machine."""

from __future__ import annotations

import pytest

from aetheros_automation.lifecycle import (
    AgentLifecycle,
    LifecycleRegistry,
    LifecycleState,
)


class TestAgentLifecycle:
    def test_initial_state_is_idle(self):
        lc = AgentLifecycle("a1")
        assert lc.state == LifecycleState.IDLE
        assert lc.is_terminal is False

    def test_canonical_flow(self):
        lc = AgentLifecycle("a1")
        lc.transition(LifecycleState.PLANNING, "user request")
        lc.transition(LifecycleState.EXECUTING)
        lc.transition(LifecycleState.WAITING)
        lc.transition(LifecycleState.EXECUTING)
        lc.transition(LifecycleState.REVIEWING)
        lc.transition(LifecycleState.COMPLETED)
        lc.transition(LifecycleState.ARCHIVED)
        assert lc.state == LifecycleState.ARCHIVED
        assert lc.is_terminal is True
        assert len(lc.history) == 7

    def test_illegal_transition_raises(self):
        lc = AgentLifecycle("a1")
        with pytest.raises(ValueError):
            lc.transition(LifecycleState.ARCHIVED)

    def test_force_transition_bypasses_validation(self):
        lc = AgentLifecycle("a1")
        lc.transition(LifecycleState.COMPLETED, force=True)
        assert lc.state == LifecycleState.COMPLETED

    def test_self_transition_is_noop(self):
        lc = AgentLifecycle("a1")
        record = lc.transition(LifecycleState.IDLE)
        assert lc.state == LifecycleState.IDLE
        assert record.to_state == LifecycleState.IDLE

    def test_allowed_next(self):
        lc = AgentLifecycle("a1")
        allowed = set(lc.allowed_next())
        assert LifecycleState.PLANNING in allowed
        assert LifecycleState.COMPLETED in allowed

    def test_listeners_notified(self):
        lc = AgentLifecycle("a1")
        events = []
        lc.on_transition(lambda record: events.append(record.to_state.value))
        lc.transition(LifecycleState.PLANNING)
        assert events == ["planning"]

    def test_snapshot_contains_state_and_history(self):
        lc = AgentLifecycle("a1")
        lc.transition(LifecycleState.PLANNING)
        snap = lc.snapshot()
        assert snap["state"] == "planning"
        assert len(snap["history"]) == 1
        assert snap["entity_id"] == "a1"


class TestLifecycleRegistry:
    def test_create_and_get(self):
        reg = LifecycleRegistry()
        tracker = reg.create("task-1")
        assert reg.get("task-1") is tracker

    def test_ensure_is_idempotent(self):
        reg = LifecycleRegistry()
        a = reg.ensure("x")
        b = reg.ensure("x")
        assert a is b

    def test_summary_counts(self):
        reg = LifecycleRegistry()
        reg.create("t1")
        t2 = reg.create("t2")
        t2.transition(LifecycleState.EXECUTING)
        summary = reg.summarize()
        assert summary["total"] == 2
        assert summary["active"] == 1
        assert summary["by_state"]["executing"] == 1

    def test_active_filters(self):
        reg = LifecycleRegistry()
        reg.create("t1")
        t2 = reg.create("t2")
        t2.transition(LifecycleState.EXECUTING)
        assert [t.entity_id for t in reg.active()] == ["t2"]
