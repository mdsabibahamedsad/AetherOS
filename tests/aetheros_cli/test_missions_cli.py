"""Tests for the ``aetheros mission`` CLI surface (aetheros_cli.missions).

The CLI wraps MissionManager + the real AgentExecutionEngine.  These tests
exercise the argparse dispatch and slash entry using a step executor (no
network / no real LLM) so they are deterministic and fast.
"""

from __future__ import annotations

import pytest

from aetheros_cli.missions import build_parser, mission_command, run_slash


def _build_args(*tokens):
    """Parse a ``aetheros mission ...`` argv list into a Namespace."""
    import argparse

    wrap = argparse.ArgumentParser(prog="aetheros")
    sub = wrap.add_subparsers(dest="_top")
    parser = build_parser(sub)
    parser.prog = "aetheros mission"
    return wrap.parse_args(["mission", *tokens])


class TestMissionCLI:
    @pytest.fixture(autouse=True)
    def _reset_manager(self, monkeypatch):
        import aetheros_cli.missions as m

        monkeypatch.setattr(m, "_MANAGER", None)

    def test_create_plans_runs_lifecycle(self, monkeypatch, capsys):
        import aetheros_cli.missions as m

        holder = {}

        def fake_manager():
            if holder.get("mm") is None:
                from aetheros_jarvis.mission import MissionManager

                mm = MissionManager()
                mm.set_approval_callback(lambda plan: True)
                mm.set_step_executor(lambda plan, step: f"ok:{step.description}")
                holder["mm"] = mm
            return holder["mm"]

        monkeypatch.setattr(m, "_get_manager", fake_manager)

        args = _build_args("create", "Ship", "v2")
        assert mission_command(args) == 0
        out = capsys.readouterr().out
        assert "Created mission" in out

    def test_plan_and_run_flow(self, monkeypatch, capsys):
        import aetheros_cli.missions as m

        holder = {}

        def fake_manager():
            if holder.get("mm") is None:
                from aetheros_jarvis.mission import MissionManager

                mm = MissionManager()
                mm.set_approval_callback(lambda plan: True)
                mm.set_step_executor(lambda plan, step: f"ok:{step.description}")
                holder["mm"] = mm
            return holder["mm"]

        monkeypatch.setattr(m, "_get_manager", fake_manager)

        mission_command(_build_args("create", "Do", "it"))
        # capture the id
        out = capsys.readouterr().out
        mid = out.split("Created mission ")[1].split(":")[0].strip()

        assert mission_command(_build_args("plan", mid, "step one", "step two")) == 0
        out = capsys.readouterr().out
        assert "Planned 2 step(s)" in out

        rc = mission_command(_build_args("run", mid, "--auto-approve"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "finished" in out
        assert "step one" in out

    def test_list_empty(self, monkeypatch, capsys):
        import aetheros_cli.missions as m

        def fake_manager():
            from aetheros_jarvis.mission import MissionManager

            return MissionManager()

        monkeypatch.setattr(m, "_get_manager", fake_manager)
        assert mission_command(_build_args("list")) == 0
        assert "No missions yet" in capsys.readouterr().out

    def test_unknown_mission_show(self, capsys):
        args = _build_args("show", "nope")
        assert mission_command(args) == 1

    def test_missing_create_goal_exits(self):
        with pytest.raises(SystemExit):
            _build_args("create")


class TestMissionSlash:
    @pytest.fixture(autouse=True)
    def _reset_manager(self, monkeypatch):
        import aetheros_cli.missions as m

        monkeypatch.setattr(m, "_MANAGER", None)

    def test_slash_help(self):
        out = run_slash("help")
        assert "Mission mode" in out

    def test_slash_bare_shows_help(self):
        out = run_slash("")
        assert "Mission mode" in out

    def test_slash_full_flow(self, monkeypatch):
        import aetheros_cli.missions as m

        holder = {}

        def fake_manager():
            if holder.get("mm") is None:
                from aetheros_jarvis.mission import MissionManager

                mm = MissionManager()
                mm.set_approval_callback(lambda plan: True)
                mm.set_step_executor(lambda plan, step: f"ok:{step.description}")
                holder["mm"] = mm
            return holder["mm"]

        monkeypatch.setattr(m, "_get_manager", fake_manager)

        out1 = run_slash("create test goal")
        mid = out1.split("Created mission ")[1].split(":")[0].strip()

        out2 = run_slash(f"plan {mid} step-alpha")
        assert "Planned 1 step(s)" in out2

        out3 = run_slash(f"run {mid} --auto-approve")
        assert "finished" in out3

        out4 = run_slash(f"show {mid}")
        assert mid in out4