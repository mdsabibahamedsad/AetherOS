"""Tests for aetheros_security.filesystem (path security + traversal)."""

import os

import pytest

from aetheros_security.filesystem import (
    FilesystemAccessError,
    FilesystemSecurity,
    PROTECTED_PATH_PATTERNS,
)


@pytest.fixture
def fs():
    security = FilesystemSecurity()
    security.allow("workspace/**", access="read_write")
    return security


class TestPathCanonicalization:
    def test_traversal_rejected(self, fs):
        for path in ("../../etc/passwd", "workspace/../../etc/passwd",
                     "..\\..\\windows\\system32", "..%2f..%2fetc"):
            with pytest.raises(FilesystemAccessError):
                fs.resolve(path)

    def test_abs_path_allowed(self, fs, tmp_path):
        workdir = tmp_path / "workspace"
        workdir.mkdir()
        resolved = fs.resolve(str(workdir / "notes.md"))
        assert os.path.isabs(resolved)

    def test_unc_rejected(self):
        fs = FilesystemSecurity()
        with pytest.raises(FilesystemAccessError):
            fs.resolve(r"\\server\share\file")

    def test_alternate_data_stream_rejected(self):
        fs = FilesystemSecurity()
        with pytest.raises(FilesystemAccessError):
            fs.resolve("workspace/file.txt:secret")

    def test_safe_resolve_never_raises(self, fs):
        ok, value = fs.safe_resolve("../../etc/passwd")
        assert not ok
        ok2, value2 = fs.safe_resolve("workspace/a.txt")
        assert ok2


class TestAccessChecks:
    def test_read_allowed_in_workspace(self, fs):
        assert fs.can_read("workspace/a.txt")

    def test_write_allowed_read_write(self, fs):
        assert fs.can_write("workspace/b.txt")

    def test_outside_workspace_denied(self, fs):
        assert not fs.can_read("/tmp/outside.txt")

    def test_read_only_path_blocks_write(self, tmp_path):
        fs = FilesystemSecurity()
        fs.allow("workspace/**", access="read_only")
        assert fs.can_read("workspace/a.txt")
        assert not fs.can_write("workspace/a.txt")
        assert not fs.can_delete("workspace/a.txt")

    def test_execute_scope(self, tmp_path):
        fs = FilesystemSecurity()
        fs.allow("scripts/**", access="execute")
        assert fs.can_execute("scripts/run.sh")
        assert not fs.can_write("scripts/run.sh")

    def test_explicit_deny_wins(self):
        fs = FilesystemSecurity()
        fs.allow("**", access="read_write")
        fs.deny("**/secrets/**")
        assert fs.can_read("anything.txt")
        assert not fs.can_read("secrets/key.txt")

    def test_zero_trust_no_rules_denies_all(self):
        fs = FilesystemSecurity()
        assert not fs.can_read("anything.txt")
        assert not fs.can_write("anything.txt")


class TestProtectedPaths:
    def test_protected_patterns_never_readable(self):
        fs = FilesystemSecurity()
        fs.allow("**", access="read_write")  # even with broad allow
        for path in ("/home/u/.ssh/id_rsa",
                     "~/.ssh/config",
                     "/home/u/.aws/credentials",
                     "/home/u/.config/gcloud/application_default_credentials.json",
                     "/home/u/.kube/config",
                     "/home/u/.docker/config.json",
                     "/home/u/.netrc",
                     "/home/u/.gnupg/secring.gpg",
                     "/home/u/id_rsa",
                     "/home/u/client_secret.json",
                     "/home/u/credentials.json"):
            assert not fs.can_read(path), path

    def test_protected_in_workspace_too(self, fs):
        # Even inside an allowed workspace, protected files are blocked.
        assert not fs.can_read("workspace/.ssh/id_rsa")
        assert not fs.can_read("workspace/secrets_index.json")
        assert not fs.can_read("workspace/.encryption_key")

    def test_add_protected(self):
        fs = FilesystemSecurity()
        fs.allow("**")
        fs.add_protected("**/my_private_dir/**")
        assert not fs.can_read("somewhere/my_private_dir/x.txt")


class TestRedTeamPathCases:
    def test_env_file_blocked(self):
        fs = FilesystemSecurity()
        fs.allow("**", access="read_write")
        # .env and credentials patterns are protected regardless of allow.
        assert not fs.can_read(".env")
        assert not fs.can_read("workspace/.env")

    def test_private_key_blocked_even_with_broad_allow(self):
        fs = FilesystemSecurity()
        fs.allow("**")
        assert not fs.can_read("/home/u/id_ed25519")
        assert not fs.can_read("backup.pem")

    def test_get_stats(self, fs):
        stats = fs.get_stats()
        assert stats["allow_rules"] >= 1
        assert stats["protected_patterns"] >= 1
        assert "PROTECTED_PATH_PATTERNS" in globals() or True
        assert len(PROTECTED_PATH_PATTERNS) > 10