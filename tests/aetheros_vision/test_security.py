"""Tests for aetheros_vision.security — secret redaction and upload policy."""

import pytest

from aetheros_vision.security import (
    assert_upload_allowed,
    redact_sensitive_text,
    requires_upload_consent,
)


class TestRedactSensitiveText:
    def test_redacts_openai_key(self):
        out = redact_sensitive_text("key is sk-abcdefghijklmnopqrstuvwxyz123456 end")
        assert "sk-" not in out
        assert "[REDACTED" in out

    def test_redacts_google_api_key(self):
        out = redact_sensitive_text("using AIzaSyBwXabcdefghijklmnopqrstuvwxyz-123")
        assert "AIza" not in out

    def test_redacts_github_token(self):
        out = redact_sensitive_text("token ghp_abcdefghijklmnopqrstuvwxyz012345")
        assert "ghp_" not in out

    def test_redacts_bearer_header(self):
        out = redact_sensitive_text("Authorization: bearer abcdefghijklmnopqrstuvwxyz12")
        assert "bearer" not in out

    def test_redacts_email(self):
        out = redact_sensitive_text("contact person@example.com please")
        assert "person@example.com" not in out
        assert "[REDACTED" in out

    def test_redacts_key_value_pair(self):
        out = redact_sensitive_text("password=hunter2 stuff")
        assert "hunter2" not in out

    def test_redacts_ssn(self):
        out = redact_sensitive_text("ssn 123-45-6789 ok")
        assert "123-45-6789" not in out

    def test_plain_text_unchanged(self):
        out = redact_sensitive_text("just a normal sentence about vision")
        assert out == "just a normal sentence about vision"

    def test_empty_input(self):
        assert redact_sensitive_text("") == ""

    def test_none_input(self):
        assert redact_sensitive_text(None) is None


class TestUploadPolicy:
    def test_local_only_no_consent_needed(self):
        assert requires_upload_consent(local_only=True) is False

    def test_cloud_processing_needs_consent(self):
        assert requires_upload_consent(local_only=False) is True

    def test_assert_local_only_passes(self):
        assert_upload_allowed(local_only=True)  # no raise

    def test_assert_cloud_raises(self):
        with pytest.raises(PermissionError):
            assert_upload_allowed(local_only=False)
