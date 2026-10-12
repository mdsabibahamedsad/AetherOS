"""Tests for aetheros_integrations.security — vault, audit, redaction, permissions."""

import pytest

from aetheros_integrations.security import (
    AuditLog,
    CredentialVault,
    PermissionManager,
    VaultUnavailableError,
    redact_dict,
    redact_sensitive_text,
)


@pytest.fixture
def settings(tmp_path):
    from aetheros_integrations.config import IntegrationsSettings

    return IntegrationsSettings(data_dir="integrations")


class TestCredentialVault:
    def test_store_and_decrypt_roundtrip(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "ghp_secret123"})
        assert env.id
        decrypted = vault.decrypt(env.id)
        assert decrypted["pat"] == "ghp_secret123"

    def test_ciphertext_is_not_plaintext(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "ghp_super_secret"})
        raw = (tmp_path / "credentials.json").read_text(encoding="utf-8")
        assert "ghp_super_secret" not in raw
        assert env.ciphertext.decode("utf-8", "replace") != "ghp_super_secret"

    def test_store_api_key_and_auth_header(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "ghp_abc123"}, kind="pat")
        from aetheros_integrations.auth import AuthEngine

        auth = AuthEngine(vault=vault, settings=settings)
        header = auth.auth_header(env.id)
        assert header == {"Authorization": "Bearer ghp_abc123"}

    def test_delete(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "x"})
        assert vault.delete(env.id) is True
        assert vault.delete(env.id) is False
        with pytest.raises(KeyError):
            vault.decrypt(env.id)

    def test_rotate(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "old"})
        before = env.version
        rotated = vault.rotate(env.id, {"pat": "new"})
        assert rotated.version == before + 1
        assert vault.decrypt(env.id)["pat"] == "new"

    def test_rotate_all_for(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        vault.store("github", {"pat": "a"})
        vault.store("github", {"pat": "b"})
        vault.store("slack", {"bearer": "c"})
        count = vault.rotate_all_for("github", {"pat": "rotated"})
        assert count == 2
        for env in vault.list():
            if env.provider_key == "github":
                assert vault.decrypt(env.id)["pat"] == "rotated"

    def test_export_redacted_masks_ciphertext(self, tmp_path, settings):
        vault = CredentialVault(settings, dirpath=tmp_path)
        vault.store("github", {"pat": "secret"})
        exported = vault.export_redacted()
        assert len(exported) == 1
        assert exported[0]["ciphertext"] == "<encrypted>"

    def test_env_key_used_when_set(self, tmp_path, settings, monkeypatch):
        monkeypatch.setenv("AETHEROS_INTEGRATIONS_VAULT_KEY", "unit-test-master-secret")
        vault = CredentialVault(settings, dirpath=tmp_path)
        env = vault.store("github", {"pat": "val"})
        assert vault.decrypt(env.id)["pat"] == "val"
        assert not (tmp_path / "vault.key").exists()


class TestAuditLog:
    def test_record_and_query(self, tmp_path, settings):
        audit = AuditLog(dirpath=tmp_path, settings=settings)
        audit.record("credential.created", actor="user", target="github", detail={"kind": "api_key"})
        audit.record("integration.installed", actor="user", target="1234")
        entries = audit.query()
        assert len(entries) == 2
        created = audit.query(action="credential.created")
        assert len(created) == 1
        assert created[0].detail["kind"] == "api_key"

    def test_query_filter_by_actor(self, tmp_path, settings):
        audit = AuditLog(dirpath=tmp_path, settings=settings)
        audit.record("a", actor="alice")
        audit.record("b", actor="bob")
        assert len(audit.query(actor="alice")) == 1


class TestRedaction:
    def test_redacts_api_key_pair(self):
        assert "sk-test123" not in redact_sensitive_text("api_key=sk-test1234567890")

    def test_redacts_bearer(self):
        assert "Bearer" not in redact_sensitive_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456")

    def test_plain_text_preserved(self):
        assert redact_sensitive_text("hello world") == "hello world"

    def test_none(self):
        assert redact_sensitive_text(None) is None

    def test_redact_dict_masks_sensitive_keys(self):
        out = redact_dict({"access_token": "abc", "name": "repo", "nested": {"api_key": "xyz"}})
        assert out["access_token"] == "<redacted>"
        assert out["name"] == "repo"
        assert out["nested"]["api_key"] == "<redacted>"


class TestPermissionManager:
    def test_deny_by_default(self):
        pm = PermissionManager()
        assert pm.can("x", "read") is False

    def test_allow_action(self):
        pm = PermissionManager()
        pm.set_permissions("x", {"allow": ["read"]})
        assert pm.can("x", "read") is True
        assert pm.can("x", "write") is False

    def test_deny_overrides_allow(self):
        pm = PermissionManager()
        pm.set_permissions("x", {"allow": ["read"], "deny": ["read"]})
        assert pm.can("x", "read") is False

    def test_allow_all(self):
        pm = PermissionManager()
        pm.set_permissions("x", {"allow_all": True})
        assert pm.can("x", "anything") is True

    def test_remove(self):
        pm = PermissionManager()
        pm.set_permissions("x", {"allow_all": True})
        pm.remove("x")
        assert pm.can("x", "anything") is False
