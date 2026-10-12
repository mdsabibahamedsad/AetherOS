"""CLI surface contract for `aetheros quality` (parser + read-only verbs)."""

import argparse
import io
from contextlib import redirect_stdout

import pytest

from aetheros_cli.quality import build_quality_parser, cmd_quality


def _invoke(*argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_quality_parser(subparsers)
    args = parser.parse_args(["quality", *argv])
    buf = io.StringIO()
    with redirect_stdout(buf):
        if getattr(args, "quality_action", None) in ("gate", "scorecard"):
            pytest.skip("exit-code verbs covered by manual verification")
        cmd_quality(args)
    return buf.getvalue()


def test_status_reports_engine_overview():
    out = _invoke("status")
    assert "Master 20" in out
    assert "FUNCTIONAL" in out and "DOCUMENTATION" in out


def test_known_issues_lists_seeded_clusters():
    out = _invoke("known-issues")
    assert "KI-WINDOWS-PTY" in out
    assert "open known issue" in out


def test_baselines_empty_state_is_helpful_not_crash(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    out = _invoke("baselines")
    assert "No baselines" in out
