"""Tests for aetheros_security.classification (data classification + flow control)."""

import pytest

from aetheros_security.classification import (
    DataClassification,
    DataFlowGuard,
    classify_content,
    classify_value,
    classification_ge,
    get_data_flow_guard,
)


class TestClassifyContent:
    def test_secret_api_key(self):
        assert classify_content("key sk-1234567890abcdefghijklmnop q") == DataClassification.SECRET

    def test_secret_private_key(self):
        assert classify_content("-----BEGIN RSA PRIVATE KEY-----\nabc") == DataClassification.SECRET

    def test_secret_bearer(self):
        assert classify_content("Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789") == DataClassification.SECRET

    def test_secret_jwt(self):
        assert classify_content("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc") == DataClassification.SECRET

    def test_highly_sensitive_password(self):
        assert classify_content("the password is hunter2") == DataClassification.HIGHLY_SENSITIVE

    def test_highly_sensitive_api_key_label(self):
        assert classify_content("api_key = 1234567890abcdef") == DataClassification.HIGHLY_SENSITIVE

    def test_sensitive_ssn(self):
        assert classify_content("SSN 123-45-6789") == DataClassification.SENSITIVE

    def test_sensitive_credit_card(self):
        assert classify_content("credit card 4111-1111-1111-1111") == DataClassification.SENSITIVE

    def test_private_email(self):
        assert classify_content("contact me at alice@example.com") == DataClassification.PRIVATE

    def test_internal_default(self):
        assert classify_content("the weather today is sunny") == DataClassification.INTERNAL

    def test_empty_is_public(self):
        assert classify_content("") == DataClassification.PUBLIC

    def test_explicit_override(self):
        assert classify_content("anything", classification=DataClassification.SECRET) == DataClassification.SECRET

    def test_classify_value_dict_keys(self):
        assert classify_value({"password": "x"}) == DataClassification.HIGHLY_SENSITIVE

    def test_classification_ge(self):
        assert classification_ge(DataClassification.SECRET, DataClassification.PRIVATE)
        assert not classification_ge(DataClassification.PRIVATE, DataClassification.SECRET)


class TestDataFlowGuard:
    def test_public_flows(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.PUBLIC,
                             source="web", destination="web:send")
        assert d.allowed

    def test_internal_flows(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.INTERNAL,
                             source="memory", destination="knowledge:write")
        assert d.allowed

    def test_private_internal_ok(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.PRIVATE,
                             source="memory", destination="memory:write")
        assert d.allowed

    def test_private_external_blocked(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.PRIVATE,
                             source="memory", destination="email:send")
        assert not d.allowed

    def test_private_external_allowed_with_policy(self):
        guard = DataFlowGuard()
        guard.allow_flow("memory", "email:send")
        d = guard.check_flow(classification=DataClassification.PRIVATE,
                             source="memory", destination="email:send")
        assert d.allowed

    def test_secret_never_leaves(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.SECRET,
                             source="memory", destination="web:send")
        assert not d.allowed
        # Even with policy + global switch, secret stays in.
        guard.allow_flow("memory", "web:send")
        guard.set_allow_external_sensitive(True)
        d2 = guard.check_flow(classification=DataClassification.SECRET,
                              source="memory", destination="web:send")
        assert not d2.allowed

    def test_sensitive_external_requires_policy(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.SENSITIVE,
                             source="memory", destination="cloud:upload")
        assert not d.allowed
        guard.allow_flow("memory", "cloud:upload")
        assert guard.check_flow(classification=DataClassification.SENSITIVE,
                                source="memory",
                                destination="cloud:upload").allowed

    def test_sensitive_internal_ok(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.HIGHLY_SENSITIVE,
                             source="memory", destination="filesystem:write")
        assert d.allowed

    def test_explicit_deny_wins(self):
        guard = DataFlowGuard()
        guard.deny_flow("memory", "knowledge:write")
        d = guard.check_flow(classification=DataClassification.INTERNAL,
                             source="memory", destination="knowledge:write")
        assert not d.allowed

    def test_external_host_destination_detected(self):
        guard = DataFlowGuard()
        d = guard.check_flow(classification=DataClassification.SENSITIVE,
                             source="memory", destination="example.com")
        assert not d.allowed

    def test_singleton(self):
        assert get_data_flow_guard() is get_data_flow_guard()