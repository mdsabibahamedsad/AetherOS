"""Automatic redaction of secrets and sensitive content for telemetry.

Redaction must never depend on developers remembering to redact manually.
This module provides dict- and text-level redaction that scrubs API keys,
authorization headers, passwords, cookies, private keys, tokens, session
secrets and provider secrets before they reach logs, traces, metrics,
diagnostic bundles or exports.

Text-level redaction reuses the existing ``agent.redact`` engine (the
single canonical text redactor in AetherOS — we do not duplicate it).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

REDACTED = "[REDACTED]"

#: Keys whose values are always treated as secrets (case-insensitive,
#: exact match).  Substring matches like ``token_count`` / ``session_id``
#: are deliberately NOT redacted.
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "access_token",
        "refresh_token",
        "id_token",
        "auth_token",
        "client_secret",
        "clientsecret",
        "secret",
        "secrets",
        "password",
        "passwd",
        "private_key",
        "private-key",
        "authorization",
        "cookie",
        "cookies",
        "set_cookie",
        "jwt",
        "token",
        "bearer",
        "ssh_key",
        "signing_key",
        "signing_secret",
        "webhook_secret",
        "verification_token",
        "aws_secret_access_key",
    }
)

#: Substring-based sensitive key detection for keys like
#: ``OPENAI_API_KEY``, ``HERMES_API_KEY``, ``X-API-Key``.
_SENSITIVE_KEY_RE = re.compile(
    r"(?:API[_-]?KEY|APIKEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH(?:_TOKEN)?|SIGNING)_?$",
    re.IGNORECASE,
)


def _is_sensitive_key(key: str) -> bool:
    """Return True when a dict key looks sensitive."""
    if not key:
        return False
    normalized = key.strip().strip('"').lower()
    if normalized in _SENSITIVE_KEYS:
        return True
    # env-style: OPENAI_API_KEY
    return bool(_SENSITIVE_KEY_RE.search(normalized))


def redact_value(value: Any, key: str = "") -> Any:
    """Recursively redact a structured value.

    Sensitive keys are replaced wholesale with ``[REDACTED]``.  String
    values (and strings under non-sensitive keys) are passed through the
    canonical text redactor so embedded secrets are scrubbed too.
    """
    if value is None:
        return None
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(v, key) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    """Redact secrets embedded in a text blob via the canonical redactor."""
    if not isinstance(text, str) or not text:
        return text
    try:
        from agent.redact import redact_sensitive_text
        return redact_sensitive_text(text, force=True)
    except Exception:
        return _fallback_redact(text)


# Conservative local fallback (never used when agent.redact is importable).
_FALLBACK_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*\S+"), r"\1=" + REDACTED),
    (re.compile(r"(?i)(Bearer\s+)\S+"), r"\1" + REDACTED),
]


def _fallback_redact(text: str) -> str:
    for pattern, repl in _FALLBACK_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a redacted copy of a telemetry payload dict."""
    if not isinstance(payload, dict):
        return {"value": redact_value(payload)}
    return redact_value(payload)


def safe_message(text: str) -> str:
    """Redact a user-facing message before display (belt-and-suspenders)."""
    return redact_text(text)