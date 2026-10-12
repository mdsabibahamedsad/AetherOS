"""Tests for aetheros_security.secrets and aetheros_security.sandbox."""

import time

import pytest

from aetheros_security.secrets import SecretBackend, SecretCategory, SecretsManager
from aetheros_security.sandbox import Sandbox, SandboxConfig


@pytest.fixture
def secrets(tmp_path):
    # Force the encrypted vault backend so tests are hermetic and
    # OS-store-independent.
    return SecretsManager(backend=SecretBackend.ENCRYPTED_VAULT, home=tmp_path)


class TestSecrets:
    def test_store_retrieve(self, secrets):
        assert secrets.store("api_key", "sk-test-123", category=SecretCategory.API_KEY)
        assert secrets.retrieve("api_key") == "sk-test-123"

    def test_store_retrieve_roundtrip(self, secrets):
        secrets.store("db_pass", "p@ssw0rd", category=SecretCategory.DB_PASSWORD)
        assert secrets.retrieve("db_pass") == "p@ssw0rd"

    def test_value_not_in_metadata(self, secrets, tmp_path):
        secrets.store("token", "super-secret-value", category=SecretCategory.API_KEY)
        for meta in secrets.list_secrets():
            blob = str(meta).lower()
            assert "super-secret-value" not in blob

    def test_delete(self, secrets):
        secrets.store("tmp", "v", category=SecretCategory.GENERIC)
        assert secrets.delete("tmp")
        assert secrets.retrieve("tmp") is None

    def test_rotate(self, secrets):
        secrets.store("key", "old", category=SecretCategory.API_KEY)
        assert secrets.rotate("key", "new")
        assert secrets.retrieve("key") == "new"

    def test_expiry(self, secrets):
        secrets.store("shortlived", "v", category=SecretCategory.GENERIC, expires_in=1)
        time.sleep(1.1)
        assert secrets.retrieve("shortlived") is None

    def test_categories_present(self):
        for cat in ("api_key", "jwt_token", "refresh_token", "db_password"):
            assert cat in [c.value for c in SecretCategory]

    def test_backend_force(self, secrets):
        assert secrets.backend == SecretBackend.ENCRYPTED_VAULT

    def test_audit_events_emitted_on_store_and_retrieve(self, secrets):
        from aetheros_security.audit import AuditEventType, AuditLogger

        secrets.store("aud_key", "super-secret-value", category=SecretCategory.API_KEY)
        assert secrets.retrieve("aud_key") == "super-secret-value"

        audit = AuditLogger()
        events = [e["event_type"] for e in audit.get_recent(100)]
        assert AuditEventType.SECRET_CREATED.value in events
        assert AuditEventType.SECRET_ACCESSED.value in events

    def test_audit_entries_never_contain_secret_value(self, secrets):
        from aetheros_security.audit import AuditLogger

        secrets.store("aud_key2", "super-secret-value", category=SecretCategory.API_KEY)
        secrets.retrieve("aud_key2")

        audit = AuditLogger()
        for entry in audit.get_recent(100):
            assert "super-secret-value" not in str(entry).lower()
            assert "super-secret-value" not in str(entry["details"]).lower()


class TestSandbox:
    def test_import_windows_safe(self):
        # Importing the sandbox must not raise on Windows (no `resource` at
        # module top level).
        import aetheros_security.sandbox as sbox
        assert sbox.Sandbox is not None

    def test_config_defaults(self):
        cfg = SandboxConfig(name="test")
        assert cfg.network_access is False
        assert cfg.mode.value == "standard"

    def test_enter_exit(self):
        cfg = SandboxConfig(name="test")
        sb = Sandbox(cfg)
        sb.enter()
        assert sb.is_active
        sb.exit()
        assert not sb.is_active

    def test_context_manager(self):
        with Sandbox(SandboxConfig(name="test")) as sb:
            assert sb.is_active

    def test_path_allow_deny(self):
        cfg = SandboxConfig(
            name="test",
            allowed_paths=["/tmp", r"C:\tmp"],
            denied_paths=["/etc", r"C:\Windows"],
        )
        sb = Sandbox(cfg)
        assert sb.check_path_allowed("/tmp/foo")
        assert not sb.check_path_allowed("/etc/passwd")
        assert not sb.check_path_allowed(r"C:\Windows\system32")

    def test_host_allow_deny(self):
        cfg = SandboxConfig(
            name="test",
            network_access=True,
            allowed_hosts=["example.com"],
            denied_hosts=["evil.com"],
        )
        sb = Sandbox(cfg)
        assert sb.check_host_allowed("example.com")
        assert not sb.check_host_allowed("evil.com")
        # Network access off => no hosts allowed.
        sb2 = Sandbox(SandboxConfig(name="test", network_access=False))
        assert not sb2.check_host_allowed("example.com")

    def test_execute_echo(self):
        import platform
        cfg = SandboxConfig(name="test")
        sb = Sandbox(cfg)
        sb.enter()
        cmd = "echo hello"
        result = sb.execute(cmd)
        assert "hello" in result.output

    def test_execute_requires_enter(self):
        sb = Sandbox(SandboxConfig(name="test"))
        result = sb.execute("echo hi")
        assert not result.success

    def test_env_scrub(self):
        import os
        os.environ["AETHEROS_API_KEY"] = "should-not-leak"
        cfg = SandboxConfig(name="test")
        sb = Sandbox(cfg)
        sb.enter()
        result = sb.execute(
            "cmd /c echo %AETHEROS_API_KEY%" if os.name == "nt" else "printenv AETHEROS_API_KEY"
        )
        os.environ.pop("AETHEROS_API_KEY", None)
        assert "should-not-leak" not in result.output
