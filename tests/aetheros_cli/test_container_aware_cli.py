"""Tests for container-aware CLI routing (NixOS container mode).

When container.enable = true in the NixOS module, the activation script
writes a .container-mode metadata file. The host CLI detects this and
execs into the container instead of running locally.
"""
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aetheros_cli.config import (
    get_container_exec_info,
)


# =============================================================================
# get_container_exec_info
# =============================================================================


@pytest.fixture
def container_env(tmp_path, monkeypatch):
    """Set up a fake AETHEROS_HOME with .container-mode file."""
    aetheros_home = tmp_path / ".aetheros"
    aetheros_home.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(aetheros_home))
    monkeypatch.delenv("HERMES_DEV", raising=False)

    container_mode = aetheros_home / ".container-mode"
    container_mode.write_text(
        "# Written by NixOS activation script. Do not edit manually.\n"
        "backend=podman\n"
        "container_name=aetheros\n"
        "exec_user=aetheros\n"
        "aetheros_bin=/data/current-package/bin/aetheros\n"
    )
    return aetheros_home


def test_get_container_exec_info_returns_metadata(container_env):
    """Reads .container-mode and returns all fields including exec_user."""
    with patch("aetheros_constants.is_container", return_value=False):
        info = get_container_exec_info()

    assert info is not None
    assert info["backend"] == "podman"
    assert info["container_name"] == "aetheros"
    assert info["exec_user"] == "aetheros"
    assert info["aetheros_bin"] == "/data/current-package/bin/aetheros"


def test_get_container_exec_info_none_inside_container(container_env):
    """Returns None when we're already inside a container."""
    with patch("aetheros_constants.is_container", return_value=True):
        info = get_container_exec_info()

    assert info is None


def test_get_container_exec_info_none_without_file(tmp_path, monkeypatch):
    """Returns None when .container-mode doesn't exist (native mode)."""
    aetheros_home = tmp_path / ".aetheros"
    aetheros_home.mkdir()
    monkeypatch.setenv("AETHEROS_HOME", str(aetheros_home))
    monkeypatch.delenv("HERMES_DEV", raising=False)

    with patch("aetheros_constants.is_container", return_value=False):
        info = get_container_exec_info()

    assert info is None


def test_get_container_exec_info_skipped_when_aetheros_dev(container_env, monkeypatch):
    """Returns None when HERMES_DEV=1 is set (dev mode bypass)."""
    monkeypatch.setenv("HERMES_DEV", "1")

    with patch("aetheros_constants.is_container", return_value=False):
        info = get_container_exec_info()

    assert info is None


def test_get_container_exec_info_not_skipped_when_aetheros_dev_zero(container_env, monkeypatch):
    """HERMES_DEV=0 does NOT trigger bypass — only '1' does."""
    monkeypatch.setenv("HERMES_DEV", "0")

    with patch("aetheros_constants.is_container", return_value=False):
        info = get_container_exec_info()

    assert info is not None


def test_get_container_exec_info_defaults():
    """Falls back to defaults for missing keys."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        aetheros_home = Path(tmpdir) / ".aetheros"
        aetheros_home.mkdir()
        (aetheros_home / ".container-mode").write_text(
            "# minimal file with no keys\n"
        )

        with patch("aetheros_constants.is_container", return_value=False), \
             patch.dict(get_container_exec_info.__globals__, {"get_aetheros_home": lambda: aetheros_home}), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HERMES_DEV", None)
            info = get_container_exec_info()

        assert info is not None
        assert info["backend"] == "docker"
        assert info["container_name"] == "aetheros"
        assert info["exec_user"] == "aetheros"
        assert info["aetheros_bin"] == "/data/current-package/bin/aetheros"


def test_get_container_exec_info_docker_backend(container_env):
    """Correctly reads docker backend with custom exec_user."""
    (container_env / ".container-mode").write_text(
        "backend=docker\n"
        "container_name=aetheros-custom\n"
        "exec_user=myuser\n"
        "aetheros_bin=/opt/aetheros/bin/aetheros\n"
    )

    with patch("aetheros_constants.is_container", return_value=False):
        info = get_container_exec_info()

    assert info["backend"] == "docker"
    assert info["container_name"] == "aetheros-custom"
    assert info["exec_user"] == "myuser"
    assert info["aetheros_bin"] == "/opt/aetheros/bin/aetheros"


def test_get_container_exec_info_crashes_on_permission_error(container_env):
    """PermissionError propagates instead of being silently swallowed."""
    with patch("aetheros_constants.is_container", return_value=False), \
         patch("builtins.open", side_effect=PermissionError("permission denied")):
        with pytest.raises(PermissionError):
            get_container_exec_info()


# =============================================================================
# _exec_in_container
# =============================================================================


@pytest.fixture
def docker_container_info():
    return {
        "backend": "docker",
        "container_name": "aetheros",
        "exec_user": "aetheros",
        "aetheros_bin": "/data/current-package/bin/aetheros",
    }


@pytest.fixture
def podman_container_info():
    return {
        "backend": "podman",
        "container_name": "aetheros",
        "exec_user": "aetheros",
        "aetheros_bin": "/data/current-package/bin/aetheros",
    }


def test_exec_in_container_calls_execvp(docker_container_info):
    """Verifies os.execvp is called with correct args: runtime, tty flags,
    user, env vars, container name, binary, and CLI args."""
    from aetheros_cli.main import _exec_in_container

    with patch("shutil.which", return_value="/usr/bin/docker"), \
         patch("subprocess.run") as mock_run, \
         patch("sys.stdin") as mock_stdin, \
         patch("os.execvp") as mock_execvp, \
         patch.dict(os.environ, {"TERM": "xterm-256color", "LANG": "en_US.UTF-8"},
                    clear=False):
        mock_stdin.isatty.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        _exec_in_container(docker_container_info, ["chat", "-m", "opus"])

    mock_execvp.assert_called_once()
    cmd = mock_execvp.call_args[0][1]
    assert cmd[0] == "/usr/bin/docker"
    assert cmd[1] == "exec"
    assert "-it" in cmd
    idx_u = cmd.index("-u")
    assert cmd[idx_u + 1] == "aetheros"
    e_indices = [i for i, v in enumerate(cmd) if v == "-e"]
    e_values = [cmd[i + 1] for i in e_indices]
    assert "TERM=xterm-256color" in e_values
    assert "LANG=en_US.UTF-8" in e_values
    assert "aetheros" in cmd
    assert "/data/current-package/bin/aetheros" in cmd
    assert "chat" in cmd


def test_exec_in_container_non_tty_uses_i_only(docker_container_info):
    """Non-TTY mode uses -i instead of -it."""
    from aetheros_cli.main import _exec_in_container

    with patch("shutil.which", return_value="/usr/bin/docker"), \
         patch("subprocess.run") as mock_run, \
         patch("sys.stdin") as mock_stdin, \
         patch("os.execvp") as mock_execvp:
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        _exec_in_container(docker_container_info, ["sessions", "list"])

    cmd = mock_execvp.call_args[0][1]
    assert "-i" in cmd
    assert "-it" not in cmd


def test_exec_in_container_no_runtime_hard_fails(podman_container_info):
    """Hard fails when runtime not found (no fallback)."""
    from aetheros_cli.main import _exec_in_container

    with patch("shutil.which", return_value=None), \
         patch("subprocess.run") as mock_run, \
         patch("os.execvp") as mock_execvp, \
         pytest.raises(SystemExit) as exc_info:
        _exec_in_container(podman_container_info, ["chat"])

    mock_run.assert_not_called()
    mock_execvp.assert_not_called()
    assert exc_info.value.code != 0


def test_exec_in_container_sudo_probe_sets_prefix(podman_container_info):
    """When first probe fails and sudo probe succeeds, execvp is called
    with sudo -n prefix."""
    from aetheros_cli.main import _exec_in_container

    def which_side_effect(name):
        if name == "podman":
            return "/usr/bin/podman"
        if name == "sudo":
            return "/usr/bin/sudo"
        return None

    with patch("shutil.which", side_effect=which_side_effect), \
         patch("subprocess.run") as mock_run, \
         patch("sys.stdin") as mock_stdin, \
         patch("os.execvp") as mock_execvp:
        mock_stdin.isatty.return_value = True
        mock_run.side_effect = [
            MagicMock(returncode=1),  # direct probe fails
            MagicMock(returncode=0),  # sudo probe succeeds
        ]

        _exec_in_container(podman_container_info, ["chat"])

    mock_execvp.assert_called_once()
    cmd = mock_execvp.call_args[0][1]
    assert cmd[0] == "/usr/bin/sudo"
    assert cmd[1] == "-n"
    assert cmd[2] == "/usr/bin/podman"
    assert cmd[3] == "exec"


def test_exec_in_container_probe_timeout_prints_message(docker_container_info):
    """TimeoutExpired from probe produces a human-readable error, not a
    raw traceback."""
    from aetheros_cli.main import _exec_in_container

    with patch("shutil.which", return_value="/usr/bin/docker"), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(
             cmd=["docker", "inspect"], timeout=15)), \
         patch("os.execvp") as mock_execvp, \
         pytest.raises(SystemExit) as exc_info:
        _exec_in_container(docker_container_info, ["chat"])

    mock_execvp.assert_not_called()
    assert exc_info.value.code == 1


def test_exec_in_container_container_not_running_no_sudo(docker_container_info):
    """When runtime exists but container not found and no sudo available,
    prints helpful error about root containers."""
    from aetheros_cli.main import _exec_in_container

    def which_side_effect(name):
        if name == "docker":
            return "/usr/bin/docker"
        return None

    with patch("shutil.which", side_effect=which_side_effect), \
         patch("subprocess.run") as mock_run, \
         patch("os.execvp") as mock_execvp, \
         pytest.raises(SystemExit) as exc_info:
        mock_run.return_value = MagicMock(returncode=1)

        _exec_in_container(docker_container_info, ["chat"])

    mock_execvp.assert_not_called()
    assert exc_info.value.code == 1
