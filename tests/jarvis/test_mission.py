"""Tests for the Jarvis mission manager (aetheros_jarvis.mission)."""

import pytest

from aetheros_jarvis.mission import MissionManager
from aetheros_jarvis.models import MissionStatus, MissionStepStatus


def _steps(n=3):
    return [{"description": f"step {i}", "tool": "shell", "params": {"cmd": f"echo {i}"}} for i in range(n)]


class TestMissionLifecycle:
    def test_create_and_plan(self):
        mm = MissionManager()
        plan = mm.create("Ship v0.16")
        assert plan.status == MissionStatus.DRAFT
        mm.plan(plan.id, _steps())
        assert plan.status == MissionStatus.AWAITING_APPROVAL
        assert len(plan.steps) == 3

    def test_plan_no_approval_is_approved(self):
        mm = MissionManager()
        plan = mm.create("Quick task", approval_required=False)
        mm.plan(plan.id, _steps(1))
        assert plan.status == MissionStatus.APPROVED

    def test_unknown_mission_plan_returns_none(self):
        mm = MissionManager()
        assert mm.plan("nope", _steps()) is None

    def test_approve_and_deny(self):
        mm = MissionManager()
        plan = mm.create("Task")
        mm.plan(plan.id, _steps(1))
        mm.approve(plan.id)
        assert plan.status == MissionStatus.APPROVED
        mm2 = MissionManager()
        plan2 = mm2.create("Task2")
        mm2.plan(plan2.id, _steps(1))
        mm2.approve(plan2.id, approved=False)
        assert plan2.status == MissionStatus.CANCELLED

    def test_list_missions(self):
        mm = MissionManager()
        mm.create("A")
        mm.create("B")
        assert len(mm.list_missions()) == 2


class TestMissionExecution:
    def test_execute_without_approval_is_cancelled(self):
        mm = MissionManager()
        plan = mm.create("Mission")
        mm.plan(plan.id, _steps())
        report = mm.execute(plan.id)
        assert plan.status == MissionStatus.CANCELLED
        assert "approval required" in report.summary

    def test_execute_denied_by_approval_callback(self):
        mm = MissionManager()
        mm.set_approval_callback(lambda plan: False)
        plan = mm.create("Mission")
        mm.plan(plan.id, _steps())
        report = mm.execute(plan.id)
        assert report.status == MissionStatus.CANCELLED

    def test_approved_mission_runs_steps(self):
        mm = MissionManager()
        mm.set_approval_callback(lambda plan: True)
        mm.set_step_executor(lambda plan, step: f"ran:{step.description}")
        plan = mm.create("Mission")
        mm.plan(plan.id, _steps(2))
        report = mm.execute(plan.id)
        assert plan.status == MissionStatus.COMPLETED
        assert report.status == MissionStatus.COMPLETED
        assert all(s.status == MissionStepStatus.COMPLETED for s in plan.steps)
        assert report.steps[0].result == "ran:step 0"

    def test_no_approval_required_runs_directly(self):
        mm = MissionManager()
        mm.set_step_executor(lambda plan, step: "ok")
        plan = mm.create("Direct", approval_required=False)
        mm.plan(plan.id, _steps(1))
        report = mm.execute(plan.id)
        assert report.status == MissionStatus.COMPLETED

    def test_fail_fast_on_approved_mission(self):
        mm = MissionManager()
        mm.set_approval_callback(lambda plan: True)
        mm.set_step_executor(lambda plan, step: (_ for _ in ()).throw(RuntimeError("boom")) if step.description == "step 1" else "ok")
        plan = mm.create("Mission")
        mm.plan(plan.id, _steps(3))
        report = mm.execute(plan.id)
        assert plan.status == MissionStatus.FAILED
        assert report.status == MissionStatus.FAILED
        assert report.steps[0].status == MissionStepStatus.COMPLETED
        assert report.steps[1].status == MissionStepStatus.FAILED
        assert report.steps[2].status == MissionStepStatus.PENDING  # not run (fail-fast)
        assert len(report.errors) == 1
        assert "boom" in report.errors[0]

    def test_execute_twice_rejected(self):
        mm = MissionManager()
        mm.set_approval_callback(lambda plan: True)
        mm.set_step_executor(lambda plan, step: "ok")
        plan = mm.create("Mission")
        mm.plan(plan.id, _steps(1))
        mm.execute(plan.id)
        with pytest.raises(RuntimeError):
            mm.execute(plan.id)

    def test_unknown_mission_execute_raises(self):
        mm = MissionManager()
        with pytest.raises(KeyError):
            mm.execute("missing")

    def test_report_markdown(self):
        mm = MissionManager()
        mm.set_approval_callback(lambda plan: True)
        mm.set_step_executor(lambda plan, step: "done")
        plan = mm.create("Write docs")
        mm.plan(plan.id, _steps(1))
        report = mm.execute(plan.id)
        md = report.to_markdown()
        assert "Write docs" in md
        assert "completed" in md

    def test_snapshot(self):
        mm = MissionManager()
        snap = mm.snapshot()
        assert "missions" in snap
        assert "approval_callback" in snap
        assert snap["approval_callback"] is False
