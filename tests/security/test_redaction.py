"""Tests for aetheros_security.redaction (secret redaction + scanning)."""

import pytest

from aetheros_security.redaction import RedactionManager


@pytest.fixture
def rm():
    return RedactionManager()


class TestCoreRedaction:
    def test_api_key_pattern(self, rm):
        out = rm.redact("sk-1234567890abcdefghijklmnopqrstuv")
        assert "sk-***REDACTED***" in out

    def test_bearer_token(self, rm):
        out = rm.redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def")
        assert "Bearer ***REDACTED***" in out

    def test_password_key_value(self, rm):
        out = rm.redact("password=hunter2secret; password = s3cretlongpw")
        assert "hunter2secret" not in out
        assert "s3cretlongpw" not in out

    def test_aws_keys(self, rm):
        out = rm.redact("AKIAIOSFODNN7EXAMPLE")
        assert "AKIAIOSFODNN7EXAMPLE" not in out

    def test_github_token(self, rm):
        out = rm.redact("ghp_1234567890abcdefghijklmnopqrstuvwxyz")
        assert "REDACTED" in out

    def test_private_key_block(self, rm):
        pem = ("-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBgkqhkiG9w0BAQEFAASC\n"
               "-----END PRIVATE KEY-----")
        out = rm.redact(pem)
        assert "REDACTED-PRIVATE-KEY" in out
        assert "MIIBVQIBADANBgkqhkiG9w0BAQEFAASC" not in out

    def test_db_uri(self, rm):
        out = rm.redact("postgres://user:secretpass@host:5432/db")
        assert "secretpass" not in out

    def test_webhook_url(self, rm):
        out = rm.redact("https://discord.com/api/webhooks/123/abc-secret-token")
        assert "123/abc-secret-token" not in out

    def test_json_secret(self, rm):
        out = rm.redact('{"api_key": "sk-abcdefghijklmnopqrstuvwxyz", "ok": 1}')
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in out


class TestExactSecretRedaction:
    def test_register_secret(self, rm):
        rm.register_secret("S3RV1CE-PASSW0RD")
        out = rm.redact("the password is S3RV1CE-PASSW0RD everywhere")
        assert "S3RV1CE-PASSW0RD" not in out

    def test_bulk_register(self, rm):
        rm.register_secret("alpha")
        rm.register_secret("beta")
        out = rm.redact("alpha and beta")
        assert "alpha" not in out
        assert "beta" not in out


class TestStructurePreservation:
    def test_redact_dict(self, rm):
        data = {"url": "https://api.example.com/v1",
                "token": "sk-abcdefghijklmnop", "n": 42}
        out = rm.redact_dict(data)
        assert out["n"] == 42
        assert "sk-abcdefghijklmnop" not in out["token"]
        assert out["url"] == "https://api.example.com/v1"

    def test_redact_dict_nested(self, rm):
        data = {"nested": {"auth": {"password": "pw1234567890"}},
                "items": [{"secret": "sk-abcdefghijklmnop"}]}
        out = rm.redact_dict(data)
        assert "pw1234567890" not in repr(out)
        assert "sk-abcdefghijklmnop" not in repr(out)
        assert out["items"][0]["secret"].startswith("***")

    def test_redact_json_roundtrip(self, rm):
        import json
        payload = json.dumps({"k": "value", "password": "p4ssw0rd12345678"})
        out = rm.redact_json(payload)
        parsed = json.loads(out)
        assert "p4ssw0rd12345678" not in out
        assert parsed["password"] == "***REDACTED***"

    def test_redact_binary_blob(self, rm):
        data = {"binary": b"sk-abcdefghijklmnopqrstuvwxyz"}
        out = rm.redact_dict(data)
        assert isinstance(out["binary"], str)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in out["binary"]


class TestScanning:
    def test_scan_finds_secret(self, rm):
        res = rm.scan("key=sk-abcdefghijklmnopqrstuvwxyz")
        assert res.redacted is True
        assert res.matched_types

    def test_scan_clean(self, rm):
        res = rm.scan("just normal text without secrets")
        assert res.redacted is False
        assert res.matched_types == []

    def test_scan_redacts_text(self, rm):
        res = rm.scan("ghp_1234567890abcdefghijklmnopqrstuvwxyz")
        assert res.redacted is True
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in res.text


class TestCustomPattern:
    def test_add_pattern(self, rm):
        rm.add_pattern("internal-id", r"ID-[A-Z0-9]{6}", "[ID-REDACTED]")
        out = rm.redact("reference ID-AB12CD ok")
        assert "ID-AB12CD" not in out
        assert "[ID-REDACTED]" in out

    def test_get_stats(self, rm):
        stats = rm.get_stats()
        assert stats["patterns"] >= 10
        assert stats["registered_secrets"] >= 0