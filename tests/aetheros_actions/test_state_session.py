"""Tests for the state machine, session management, and cancellation."""

from __future__ import annotations

import pytest

from aetheros_actions.permissions import AutonomyLevel
from aetheros_actions.session import ComputerUseSession, SessionManager, StopSignal
from aetheros_actions.state import ComputerUseState, InvalidTransition, StateMachine


class TestStateMachine:
    def test_valid_sequence(self):
        sm = StateMachine()
        sm.transition(ComputerUseState.OBSERVING)
        sm.transition(ComputerUseState.PLANNING)
        sm.transition(ComputerUseState.WAITING_FOR_PERMISSION)
        sm.transition(ComputerUseState.EXECUTING)
        sm.transition(ComputerUseState.VERIFYING)
        sm.transition(ComputerUseState.COMPLETED)
        assert sm.state is ComputerUseState.COMPLETED
        assert sm.is_terminal()

    def test_emergency_stop_from_executing(self):
        sm = StateMachine()
        sm.transition(ComputerUseState.EXECUTING)
        sm.transition(ComputerUseState.CANCELLED)
        assert sm.state is ComputerUseState.CANCELLED

    def test_invalid_transition_raises(self):
        sm = StateMachine()
        with pytest.raises(InvalidTransition):
            sm.transition(ComputerUseState.COMPLETED)  # IDLE → COMPLETED invalid

    def test_terminal_is_frozen(self):
        sm = StateMachine()
        sm.transition(ComputerUseState.PLANNING)
        sm.transition(ComputerUseState.EXECUTING)
        sm.transition(ComputerUseState.VERIFYING)
        sm.transition(ComputerUseState.COMPLETED)
        with pytest.raises(InvalidTransition):
            sm.transition(ComputerUseState.EXECUTING)

    def test_active_states_can_stop(self):
        sm = StateMachine()
        sm.transition(ComputerUseState.EXECUTING)
        assert sm.can_stop()
        sm.transition(ComputerUseState.COMPLETED)
        assert not sm.can_stop()


class TestSession:
    def test_create_and_get(self):
        mgr = SessionManager()
        s = mgr.create(agent_id="ag-1")
        assert mgr.get(s.session_id) is s
        assert s.state.state is ComputerUseState.IDLE

    def test_default_autonomy(self):
        mgr = SessionManager()
        s = mgr.create()
        assert s.autonomy_level == AutonomyLevel.SAFE_AUTONOMOUS

    def test_int_autonomy_coerced(self):
        mgr = SessionManager()
        s = mgr.create(autonomy_level=2)
        assert s.autonomy_level == AutonomyLevel.LOW_RISK_AUTO

    def test_stop_signal(self):
        s = ComputerUseSession()
        s.emergency_stop()
        assert s.should_stop()
        assert s.state.state is ComputerUseState.CANCELLED

    def test_pause_resume(self):
        s = ComputerUseSession()
        s.pause()
        assert s.is_paused()
        s.resume()
        assert not s.is_paused()

    def test_stop_fanout(self):
        mgr = SessionManager()
        s1 = mgr.create()
        s2 = mgr.create()
        n = mgr.stop_all(StopSignal.EMERGENCY_STOP)
        assert n == 2
        assert s1.should_stop() and s2.should_stop()