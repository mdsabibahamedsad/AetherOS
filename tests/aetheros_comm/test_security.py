"""Security-focused tests for aetheros_comm.security — credential scanning."""

from __future__ import annotations

import pytest

from aetheros_comm.security import scan_for_credentials, to_log_safe


class TestScanForCredentials:
    def test_api_key_detected(self):
        scan = scan_for_credentials({"key": "sk-1234567890abcdef"})
        assert scan.found

    def test_password_detected(self):
        scan = scan_for_credentials({"password": "hunter2"})
        assert scan.found

    def test_token_key_detected(self):
        scan = scan_for_credentials({"auth": {"token": "abcd1234"}})
        assert scan.found

    def test_clean_payload_not_found(self):
        scan = scan_for_credentials({"task": "clean", "data": [1, 2, 3]})
        assert not scan.found

    def test_legitimate_words_not_flagged(self):
        scan = scan_for_credentials({"action": "key the lock", "note": "passwordless"})
        assert not scan.found

    def test_empty_payload(self):
        assert not scan_for_credentials({}).found
        assert not scan_for_credentials(None).found


class TestToLogSafe:
    def test_redacts_secret_keys(self):
        safe = to_log_safe({"payload": {"api_key": "sk-x", "task": "clean"}})
        assert safe["payload"]["task"] == "clean"
        assert safe["payload"]["api_key"] != "sk-x"

    def test_non_secret_passthrough(self):
        safe = to_log_safe({"payload": {"task": "clean", "n": 3}})
        assert safe["payload"] == {"task": "clean", "n": 3}

    def test_nested_redaction(self):
        safe = to_log_safe({"payload": {"auth": {"token": "abc"}}})
        assert safe["payload"]["auth"]["token"] != "abc"

    def test_redacts_metadata_and_security_context(self):
        safe = to_log_safe({"payload": {"clean": 1},
                            "metadata": {"secret": "hunter2"},
                            "securityContext": {"token": "xyz"}})
        assert safe["payload"]["clean"] == 1
        assert safe["metadata"]["secret"] != "hunter2"
        assert safe["securityContext"]["token"] != "xyz"

    def test_signature_redacted(self):
        safe = to_log_safe({"signature": "abc123"})
        assert safe["signature"] != "abc123"