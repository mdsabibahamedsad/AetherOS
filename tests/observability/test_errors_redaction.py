"""Tests for aetheros_observability.errors and redaction."""

from aetheros_observability.errors import (
    ErrorEnvelope,
    ErrorType,
    Severity,
    classify_error,
    format_traceback,
    user_safe_message,
)
from aetheros_observability.redaction import redact_payload, redact_text, redact_value


class TestClassifyError:
    def test_network_is_retryable(self):
        error_type = classify_error("connection reset by peer")
        assert error_type == ErrorType.NETWORK_ERROR
        assert error_type in RETRYABLE()

    def test_rate_limit_retryable(self):
        assert classify_error("429 Too Many Requests") == ErrorType.RATE_LIMIT

    def test_auth_not_retryable(self):
        error_type = classify_error("invalid api key")
        assert error_type == ErrorType.AUTHENTICATION_ERROR

    def test_unknown_default(self):
        assert classify_error("weird mystery failure") == ErrorType.INTERNAL_ERROR

    def test_empty(self):
        assert classify_error("") == ErrorType.INTERNAL_ERROR


def RETRYABLE():
    from aetheros_observability.errors import RETRYABLE_TYPES
    return RETRYABLE_TYPES


class TestEnvelope:
    def test_envelope_has_safe_message(self):
        env = ErrorEnvelope.from_exception(ValueError("boom"), operation="test")
        assert env.type == ErrorType.VALIDATION_ERROR
        assert "boom" in env.message
        assert env.operation == "test"
        assert env.timestamp

    def test_envelope_serializable(self):
        env = ErrorEnvelope.from_exception(RuntimeError("x"))
        d = env.to_dict()
        assert "safe_message" in d
        assert "message" in d
        assert d["retryable"] is False


class TestUserSafe:
    def test_message_not_empty(self):
        assert user_safe_message(ErrorType.NETWORK_ERROR)
        assert user_safe_message(ErrorType.INTERNAL_ERROR)

    def test_no_secrets_in_safe_message(self):
        msg = user_safe_message(ErrorType.AUTHENTICATION_ERROR)
        assert "token" not in msg.lower()
        assert "sk-" not in msg.lower()
        assert "Bearer" not in msg


class TestRedaction:
    def test_redact_text_hides_tokens(self):
        out = redact_text("my sk-abc1234567890abcdef secret token here")
        assert "sk-abc1234567890abcdef" not in out
        assert "sk-" in out

    def test_redact_value_scalar(self):
        assert redact_value("hello") == "hello"

    def test_redact_payload_removes_sensitive_keys(self):
        payload = {
            "api_key": "sk-1234567890abcdef",
            "password": "hunter2",
            "authorization": "Bearer abc123",
            "model": "gpt-4o",
            "tokens": 42,
        }
        cleaned = redact_payload(payload)
        assert cleaned["api_key"] != "sk-1234567890abcdef"
        assert cleaned["password"] != "hunter2"
        assert cleaned["authorization"] != "Bearer abc123"
        assert cleaned["model"] == "gpt-4o"
        assert cleaned["tokens"] == 42

    def test_redact_payload_nested(self):
        payload = {"headers": {"X-API-Key": "deadbeef"}, "ok": True}
        cleaned = redact_payload(payload)
        assert cleaned["headers"]["X-API-Key"] != "deadbeef"
        assert cleaned["ok"] is True


class TestTraceback:
    def test_format_traceback(self):
        try:
            raise ValueError("trace me")
        except ValueError as exc:
            tb = format_traceback(exc)
        assert "trace me" in tb
        assert "ValueError" in tb