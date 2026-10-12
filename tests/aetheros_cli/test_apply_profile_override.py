"""Regression tests for _apply_profile_override AETHEROS_HOME guard (issue #22502).

When AETHEROS_HOME is set to the aetheros root (e.g. systemd hardcodes
AETHEROS_HOME=/root/.aetheros), _apply_profile_override must still read
active_profile and update AETHEROS_HOME to the profile directory.

When AETHEROS_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path



def _run_apply_profile_override(
    tmp_path, monkeypatch, *, aetheros_home: str | None, active_profile: str | None,
    argv: list[str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["AETHEROS_HOME"] after the call,
    or None if unset.
    """
    aetheros_root = tmp_path / ".aetheros"
    aetheros_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (aetheros_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (aetheros_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if aetheros_home is not None:
        monkeypatch.setenv("AETHEROS_HOME", aetheros_home)
    else:
        monkeypatch.delenv("AETHEROS_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["aetheros", "gateway", "start"])

    from aetheros_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("AETHEROS_HOME")


class TestApplyProfileOverrideAetherosHomeGuard:
    """Regression guard for issue #22502.

    Verifies that AETHEROS_HOME pointing to the aetheros root does NOT suppress
    the active_profile check, while AETHEROS_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_aetheros_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """AETHEROS_HOME=/root/.aetheros + active_profile=coder must redirect
        AETHEROS_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets AETHEROS_HOME to the aetheros root
        and the user switches to a profile via `aetheros profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        aetheros_root = tmp_path / ".aetheros"
        aetheros_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            aetheros_home=str(aetheros_root),
            active_profile="coder",
        )

        assert result is not None, "AETHEROS_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected AETHEROS_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected AETHEROS_HOME to end with 'coder', got: {result!r}"
        )

    def test_aetheros_home_already_profile_dir_is_trusted(self, tmp_path, monkeypatch):
        """AETHEROS_HOME=.../profiles/coder must not be overridden even when
        active_profile says something different.

        Preserves the child-process inheritance contract: a subprocess spawned
        with AETHEROS_HOME already set to a specific profile must stay in that
        profile.
        """
        aetheros_root = tmp_path / ".aetheros"
        profile_dir = aetheros_root / "profiles" / "coder"
        profile_dir.mkdir(parents=True, exist_ok=True)

        (aetheros_root / "active_profile").write_text("other")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("AETHEROS_HOME", str(profile_dir))
        monkeypatch.setattr(sys, "argv", ["aetheros", "gateway", "start"])

        from aetheros_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("AETHEROS_HOME") == str(profile_dir), (
            "AETHEROS_HOME must remain unchanged when already pointing to a profile dir"
        )

    def test_aetheros_home_unset_reads_active_profile(self, tmp_path, monkeypatch):
        """Classic case: AETHEROS_HOME unset + active_profile=coder must set
        AETHEROS_HOME to the profile directory (existing behaviour must not regress).
        """
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            aetheros_home=None,
            active_profile="coder",
        )

        assert result is not None
        assert "coder" in result

    def test_aetheros_home_unset_default_profile_no_redirect(self, tmp_path, monkeypatch):
        """active_profile=default must not redirect AETHEROS_HOME."""
        aetheros_root = tmp_path / ".aetheros"
        aetheros_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("AETHEROS_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", ["aetheros", "gateway", "start"])
        (aetheros_root / "active_profile").write_text("default")

        from aetheros_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("AETHEROS_HOME") is None

    def test_subcommand_profile_flag_is_not_consumed(self, tmp_path, monkeypatch):
        """Command argv flags named --profile must stay with that command.

        Docker Desktop's MCP Toolkit uses `docker mcp gateway run --profile ...`.
        When that argv is passed through `aetheros mcp add --args`, the early
        profile pre-parser must not interpret the Docker profile as a Aetheros
        profile.
        """
        aetheros_root = tmp_path / ".aetheros"
        aetheros_root.mkdir(parents=True, exist_ok=True)
        argv = [
            "aetheros",
            "mcp",
            "add",
            "docker-research",
            "--command",
            "docker",
            "--args",
            "mcp",
            "gateway",
            "run",
            "--profile",
            "research",
        ]

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("AETHEROS_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", list(argv))

        from aetheros_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("AETHEROS_HOME") is None
        assert sys.argv == argv

    def test_profile_after_chat_subcommand_is_still_consumed(self, tmp_path, monkeypatch):
        """Profile flags historically work after normal Aetheros subcommands."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            aetheros_home=None,
            active_profile="coder",
            argv=["aetheros", "chat", "-p", "coder", "-q", "hello"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["aetheros", "chat", "-q", "hello"]

    def test_top_level_profile_after_value_flag_is_consumed(self, tmp_path, monkeypatch):
        """Top-level --profile still works after other top-level value flags."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            aetheros_home=None,
            active_profile="coder",
            argv=["aetheros", "-m", "gpt-5", "--profile", "coder", "chat"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["aetheros", "-m", "gpt-5", "chat"]

    def test_top_level_profile_after_continue_flag_is_consumed(self, tmp_path, monkeypatch):
        """--continue has an optional value, so a following --profile is a flag."""
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            aetheros_home=None,
            active_profile="coder",
            argv=["aetheros", "--continue", "--profile", "coder"],
        )

        assert result is not None
        assert result.endswith("coder")
        assert sys.argv == ["aetheros", "--continue"]
