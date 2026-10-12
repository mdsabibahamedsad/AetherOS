"""CLI surface: `aetheros memory-os` verbs through the argparse handler."""

import json

import pytest

from aetheros_cli.memory_os_cmd import register_memory_os_subparser


@pytest.fixture
def parser():
    import argparse

    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    register_memory_os_subparser(sub)
    return p


def _run(parser, argv):
    args = parser.parse_args(argv)
    return args.func(args), args


def test_remember_then_search_roundtrip(parser, capsys):
    code, _ = _run(parser, ["memory-os", "remember",
                            "User prefers tabular reports on Fridays",
                            "--type", "preference", "--key", "pref:reports"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "active"

    code2, _ = _run(parser, ["memory-os", "search", "tabular reports fridays"])
    assert code2 == 0
    text = capsys.readouterr().out
    assert "tabular" in text


def test_search_empty_states_no_fabrication(parser, capsys):
    _run(parser, ["memory-os", "search", "completely unknown quantum fox"])
    assert "(no stored memory matched" in capsys.readouterr().out


def test_status_reports_stats_and_controls(parser, capsys):
    _run(parser, ["memory-os", "status"])
    text = capsys.readouterr().out
    assert "db_path" in text and "private_mode" in text


def test_list_and_forget_flow(parser, capsys):
    _run(parser, ["memory-os", "remember", "forgettable note xylophone"])
    capsys.readouterr()
    _run(parser, ["memory-os", "list"])
    listed = capsys.readouterr().out
    mid = None
    for line in listed.splitlines():
        if line.startswith("(") and "xylophone" in line:
            mid = line.split(")")[0].lstrip("(")
            break
    assert mid, f"list output missing item: {listed!r}"
    code3, _ = _run(parser, ["memory-os", "forget", mid])
    assert f"{mid}: deleted=True" in capsys.readouterr().out


def test_private_mode_toggle(parser, capsys):
    _run(parser, ["memory-os", "private-mode", "on"])
    assert "ON" in capsys.readouterr().out
    _run(parser, ["memory-os", "private-mode", "off"])
    assert "OFF" in capsys.readouterr().out


def test_audit_chain_reported_ok(parser, capsys):
    _run(parser, ["memory-os", "remember", "audited item kestrel"])
    capsys.readouterr()
    code, _ = _run(parser, ["memory-os", "audit"])
    assert "chain-integrity: OK" in capsys.readouterr().out
    assert code == 0
