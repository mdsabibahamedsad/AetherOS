"""Regression tests for Master 76 CLI updater hardening.

Covers two guards added after real observed crashes:
1. Unparseable `git rev-list --count` output aborts safely WITH stash/branch
   restore (previously: unhandled ValueError AFTER stashing/switching,
   stranding user state).
2. Non-string update argv elements (resolver arity flips, unconfigured
   mocks, corrupt installs) abort with a clear message instead of a deep
   TypeError or, worse, executing a garbage command.
3. `_git_cmd()` platform contract (Windows NTFS workaround prefix).
"""

import sys
from types import SimpleNamespace

import pytest

from aetheros_cli import main as aetheros_main


def _setup(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir(exist_ok=True)
    monkeypatch.setattr(aetheros_main, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(aetheros_main, "_refresh_active_lazy_features", lambda: None)


def test_garbage_rev_list_restores_stash_and_branch(monkeypatch, tmp_path, capsys):
    """Garbage rev-list output → exit 1, stash restored, branch restored."""
    _setup(tmp_path, monkeypatch)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(
        aetheros_main, "_stash_local_changes_if_needed", lambda *a, **kw: "abc123"
    )
    restored = []
    monkeypatch.setattr(
        aetheros_main,
        "_restore_stashed_changes",
        lambda *a, **kw: restored.append(a) or True,
    )

    recorded = []

    def fake_run(cmd, **kwargs):
        recorded.append(cmd)
        joined = " ".join(str(c) for c in cmd)
        if "rev-parse" in joined and "--abbrev-ref" in joined:
            return SimpleNamespace(stdout="feature-x\n", stderr="", returncode=0)
        if "rev-list" in joined:
            return SimpleNamespace(stdout="not-a-number\n", stderr="", returncode=0)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(aetheros_main.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        aetheros_main.cmd_update(SimpleNamespace())

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Could not determine available updates" in out
    assert "restored" in out
    # Stash restored exactly once with the stashed ref.
    assert len(restored) == 1
    assert restored[0][2] == "abc123"
    # Branch switched back to the original feature branch.
    checkouts = [c for c in recorded if "checkout" in c and "feature-x" in c]
    assert len(checkouts) >= 1


def test_non_string_update_argv_aborts_cleanly(monkeypatch, capsys):
    """A non-string argv element (e.g. resolver arity flip) → clean abort."""
    import aetheros_cli.managed_uv as managed_uv

    monkeypatch.setattr(managed_uv, "update_managed_uv", lambda: None)
    monkeypatch.setattr(managed_uv, "ensure_uv", lambda: 12345)
    monkeypatch.setattr("shutil.which", lambda name: None)

    ran = []
    monkeypatch.setattr(
        aetheros_main.subprocess, "run", lambda *a, **kw: ran.append(a) or SimpleNamespace(returncode=0)
    )

    with pytest.raises(SystemExit) as exc:
        aetheros_main._cmd_update_pip(SimpleNamespace())

    assert exc.value.code == 1
    assert "malformed update command" in capsys.readouterr().out
    assert ran == []


def test_git_cmd_platform_contract(monkeypatch):
    """_git_cmd carries the Windows NTFS workaround only on win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert aetheros_main._git_cmd() == ["git", "-c", "windows.appendAtomically=false"]
    monkeypatch.setattr(sys, "platform", "linux")
    assert aetheros_main._git_cmd() == ["git"]
