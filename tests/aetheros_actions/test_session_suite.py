"""Phase 2K — SessionManager: lifecycle, isolation, stop semantics.

Covers: create/resume/close, interrupted + corrupted sessions, concurrent
session isolation, pause/resume, stop signals, and emergency-stop fanout.
"""

from __future__ import annotations

import threading

import pytest

from aetheros_actions.permissions import AutonomyLevel
from aetheros_actions.session import ComputerUseSession, SessionManager, StopSignal
from aetheros_actions.state import ComputerUseState


class TestLifecycle:
    def test_create_and_get(self):
        mgr = SessionManager()
        s = mgr.create(agent_id="ag-1")
        assert mgr.get(s.session_id) is s

    def test_close_removes(self):
        mgr = SessionManager()
        s = mgr.create()
        assert mgr.get(s.session_id) is not None
        mgr.remove(s.session_id)
        assert mgr.get(s.session_id) is None

    def test_resume_same_object(self):
        mgr = SessionManager()
        s = mgr.create()
        assert mgr.get(s.session_id) is s  # same isolated session survives

    def test_unique_ids(self):
        mgr = SessionManager()
        a, b = mgr.create(), mgr.create()
        assert a.session_id != b.session_id


class TestIsolation:
    def test_concurrent_sessions_isolated(self):
        mgr = SessionManager()
        a, b = mgr.create(), mgr.create()
        a.emergency_stop()
        assert a.should_stop()
        assert not b.should_stop()
        assert b.state.state is ComputerUseState.IDLE

    def test_state_machines_independent(self):
        mgr = SessionManager()
        a, b = mgr.create(), mgr.create()
        a.state.transition(ComputerUseState.EXECUTING)
        assert a.state.state is ComputerUseState.EXECUTING
        assert b.state.state is ComputerUseState.IDLE

    def test_stop_all_fanout(self):
        mgr = SessionManager()
        a, b = mgr.create(), mgr.create()
        n = mgr.stop_all()
        assert n == 2
        assert a.should_stop() and b.should_stop()
        assert a.state.state is ComputerUseState.CANCELLED


class TestStopSignals:
    def test_stop_cancel_emergency_all_stop(self):
        for sig in (StopSignal.STOP, StopSignal.CANCEL, StopSignal.EMERGENCY_STOP):
            s = ComputerUseSession()
            s.request(sig)
            assert s.should_stop(), sig

    def test_emergency_stop_cancels_from_idle(self):
        s = ComputerUseSession()
        s.emergency_stop()
        assert s.state.state is ComputerUseState.CANCELLED

    def test_pause_resume_cycle(self):
        s = ComputerUseSession()
        s.pause()
        assert s.is_paused()
        s.resume()
        assert not s.is_paused()
        assert not s.should_stop()

    def test_pause_not_stop(self):
        s = ComputerUseSession()
        s.pause()
        assert not s.should_stop()

    def test_clear_stop_clears_non_emergency(self):
        s = ComputerUseSession()
        s.stop()
        s.clear_stop()
        assert not s.should_stop()

    def test_clear_stop_does_not_clear_emergency(self):
        s = ComputerUseSession()
        s.emergency_stop()
        s.clear_stop()
        assert s.should_stop()
        assert s.state.state is ComputerUseState.CANCELLED

    def test_signal_accessor(self):
        s = ComputerUseSession()
        s.pause()
        assert s.signal is StopSignal.PAUSE


class TestInterruptedCorrupted:
    def test_interrupted_session_final_state(self):
        mgr = SessionManager()
        s = mgr.create()
        s.emergency_stop()
        assert s.state.is_terminal()
        assert s.state.state is ComputerUseState.CANCELLED

    def test_corrupted_signal_never_reused(self):
        s = ComputerUseSession()
        s.emergency_stop()
        # Once cancelled, the state machine refuses to re-enter active states.
        from aetheros_actions.state import InvalidTransition
        with pytest.raises(InvalidTransition):
            s.state.transition(ComputerUseState.EXECUTING)

    def test_thread_safe_request(self):
        s = ComputerUseSession()
        threads = [threading.Thread(target=s.stop) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.should_stop()


class TestAutonomy:
    def test_int_autonomy_coerced(self):
        mgr = SessionManager()
        s = mgr.create(autonomy_level=2)
        assert s.autonomy_level is AutonomyLevel.LOW_RISK_AUTO

    def test_default_autonomy_safe(self):
        mgr = SessionManager()
        assert mgr.create().autonomy_level is AutonomyLevel.SAFE_AUTONOMOUS

    def test_set_autonomy(self):
        s = ComputerUseSession()
        s.set_autonomy(AutonomyLevel.OBSERVE_ONLY)
        assert s.autonomy_level is AutonomyLevel.OBSERVE_ONLY