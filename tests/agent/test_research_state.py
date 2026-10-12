"""Tests for the research state machine (observable transitions)."""

import pytest

from agent.research.state import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    IllegalTransition,
    ResearchStateMachine,
)
from agent.research.models import TaskStatus as S


class TestTransitions:
    def test_happy_path_is_legal(self):
        machine = ResearchStateMachine("t1")
        path = [
            S.PLANNING,
            S.SEARCHING,
            S.COLLECTING,
            S.READING,
            S.EXTRACTING,
            S.VERIFYING,
            S.SYNTHESIZING,
            S.REVIEWING,
            S.COMPLETED,
        ]
        for target in path:
            machine.transition(target)
        assert machine.status is S.COMPLETED
        assert machine.is_terminal
        assert len(machine.history) == len(path)

    def test_illegal_jump_raises(self):
        machine = ResearchStateMachine("t2")
        with pytest.raises(IllegalTransition):
            machine.transition(S.COMPLETED)

    def test_terminal_states_have_no_exits(self):
        for terminal in TERMINAL_STATES:
            machine = ResearchStateMachine("t3", initial=terminal)
            for target in TaskStatus_values():
                if target is terminal:
                    continue
                assert not machine.can_transition(target), (
                    f"terminal {terminal} should not reach {target}"
                )

    def test_observers_see_every_transition(self):
        seen = []
        machine = ResearchStateMachine("t4")
        machine.observe(seen.append)
        machine.transition(S.PLANNING, detail="d1")
        machine.transition(S.SEARCHING, detail="d2")
        assert [e.to_status for e in seen] == ["PLANNING", "SEARCHING"]
        assert seen[0].from_status == "CREATED"
        assert seen[1].detail == "d2"
        assert all(e.task_id == "t4" for e in seen)

    def test_cancel_from_created_is_legal(self):
        machine = ResearchStateMachine("t5")
        machine.transition(S.CANCELLED, detail="user")
        assert machine.is_terminal

    def test_every_state_has_transition_table_entry_or_is_terminal(self):
        for state in list(S):
            assert state in TERMINAL_STATES or state in ALLOWED_TRANSITIONS


def TaskStatus_values():
    from agent.research.models import TaskStatus

    return list(TaskStatus)
