"""Tests for the `aetheros research` CLI subcommand wiring."""

import argparse
import json

import pytest

from aetheros_cli.research_cmd import register_research_subparser


@pytest.fixture
def parser():
    root = argparse.ArgumentParser()
    register_research_subparser(root.add_subparsers(dest="command"))
    return root


def run(parser, argv):
    args = parser.parse_args(argv)
    with pytest.raises(SystemExit) as exc:
        args.func(args)
    return exc.value.code


def test_start_no_run_creates_planning_task(parser, capsys):
    code = run(parser, ["research", "start", "--no-run", "--json", "what is x"])
    assert code == 0
    from agent.research.store import ResearchStore

    store = ResearchStore()
    try:
        tasks = store.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].status.value == "PLANNING"
        assert tasks[0].objective
        assert tasks[0].plan
    finally:
        store.close()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PLANNING"


def test_list_and_show_round_trip(parser, capsys):
    assert run(parser, ["research", "start", "--no-run", "query one"]) == 0
    assert run(parser, ["research", "list"]) == 0
    out = capsys.readouterr().out
    assert "query one" in out

    from agent.research.store import ResearchStore

    store = ResearchStore()
    try:
        rid = store.list_tasks()[0].research_id
    finally:
        store.close()

    assert run(parser, ["research", "show", "--json", rid]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["task"]["research_id"] == rid
    assert any(t["to_status"] == "PLANNING" for t in data["transitions"])


def test_report_before_completion_exits_one(parser):
    assert run(parser, ["research", "start", "--no-run", "unfinished q"]) == 0
    from agent.research.store import ResearchStore

    store = ResearchStore()
    try:
        rid = store.list_tasks()[0].research_id
    finally:
        store.close()
    assert run(parser, ["research", "report", rid]) == 1


def test_cancel_planning_task(parser):
    run(parser, ["research", "start", "--no-run", "cancel me"])
    from agent.research.store import ResearchStore

    store = ResearchStore()
    try:
        rid = store.list_tasks()[0].research_id
    finally:
        store.close()
    assert run(parser, ["research", "cancel", rid]) == 0
    assert run(parser, ["research", "cancel", rid]) == 1


def test_unknown_ids_exit_two(parser):
    assert run(parser, ["research", "show", "doesnotexist"]) == 2
    assert run(parser, ["research", "report", "doesnotexist"]) == 2


def test_invalid_depth_rejected():
    from aetheros_cli.research_cmd import _depth

    with pytest.raises(SystemExit):
        _depth("bogus")
