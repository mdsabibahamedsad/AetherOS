"""
Secret Redaction for AetherOS
=============================

Centralized secret detection and redaction (master security spec step 19).

Detects and redacts:

    - API keys (sk-..., key=..., apikey=...)
    - Bearer tokens (Authorization: Bearer ...)
    - OAuth tokens
    - Passwords
    - Private keys (PEM blocks)
    - Session cookies
    - JWTs
    - Database credentials (URI with password)
    - Webhook secrets
    - SSH private keys
    - Cloud credentials (aws_secret_access_key, etc.)
    - GitHub tokens (ghp_, gho_, github_pat_)

Redaction happens before content is written to logs, telemetry, error
reports, debug output, or model context. Known secret values from the
SecretsManager are also registered for exact-match redaction.

Usage::

    from aetheros_security.redaction import RedactionManager

    redactor = RedactionManager()
    safe = redactor.redact("My key is sk-1234567890abcdefgh")
    safe_json = redactor.redact_json({"api_key": "sk-123..."})
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RedactionPattern:
    """A redaction regex pattern."""
    name: str
    pattern: str
    replacement: str = "***REDACTED***"


@dataclass
class RedactionResult:
    """Result of a redaction pass."""
    redacted: bool
    text: str
    matched_types: List[str] = field(default_factory=list)


class RedactionManager:
    """Detects and redacts secret-like values from text.

    Both pattern-based (regex) and exact-value (registered secrets)
    redaction are applied. Registered secret values are matched verbatim —
    the strongest form of redaction.
    """

    def __init__(self) -> None:
        self._patterns: List[RedactionPattern] = []
        self._exact_secrets: set[str] = set()
        self._load_default_patterns()

    def _load_default_patterns(self) -> None:
        self._patterns = [
            # OpenAI-style keys
            RedactionPattern("openai_key", r"\bsk-[a-zA-Z0-9]{20,}\b", "sk-***REDACTED***"),
            # Anthropic keys
            RedactionPattern("anthropic_key", r"\bsk-ant-[a-zA-Z0-9\-]{20,}\b", "sk-ant-***REDACTED***"),
            # AWS access key IDs (bare form)
            RedactionPattern("aws_access_key_id", r"\bAKIA[0-9A-Z]{16}\b", "AKIA***REDACTED***"),
            # Generic api keys
            RedactionPattern(
                "api_key",
                r"(?i)(?:api[_-]?key|apikey|api_token)[\"']?\s*[=:]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?",
                r"\1=***REDACTED***",
            ),
            # Bearer tokens
            RedactionPattern(
                "bearer",
                r"(?i)(authorization\s*[:=]\s*)bearer\s+[a-zA-Z0-9\-._~+/]+=*",
                r"\1Bearer ***REDACTED***",
            ),
            # JWT (three dot-separated base64url segments)
            RedactionPattern(
                "jwt",
                r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b",
                "***REDACTED***",
            ),
            # OAuth tokens
            RedactionPattern(
                "oauth_token",
                r"(?i)(oauth[_-]?token|access[_-]?token|refresh[_-]?token)\s*[=:]\s*['\"]?([a-zA-Z0-9\-._~+/]{16,})['\"]?",
                r"\1=***REDACTED***",
            ),
            # Passwords
            RedactionPattern(
                "password",
                r"(?i)(password|passwd|pwd)[\"']?\s*[=:]\s*['\"]?([^\s'\"\&]{8,})['\"]?",
                r"\1=***REDACTED***",
            ),
            # Private keys (PEM) - multi-line
            RedactionPattern(
                "private_key",
                r"-----BEGIN(?: [A-Z ]+)? PRIVATE KEY-----[\s\S]+?-----END(?: [A-Z ]+)? PRIVATE KEY-----",
                "***REDACTED-PRIVATE-KEY***",
            ),
            # SSH private keys
            RedactionPattern("ssh_key", r"\b(?:ssh-(?:rsa|ed25519|ecdsa)) [a-zA-Z0-9+/=]+",
                             "***REDACTED***"),
            # Session cookies
            RedactionPattern(
                "session_cookie",
                r"(?i)(session|sessionid|auth|connect\.sid)\s*=\s*[a-zA-Z0-9\-_.]{16,}",
                r"\1=***REDACTED***",
            ),
            # Database connection URIs with password
            RedactionPattern(
                "db_uri",
                r"(?i)(postgres(?:ql)?|mysql|mongo(?:db)?|redis|amqp|http|https)://[^:\s/@]+:[^@\s]+@",
                r"\1://***REDACTED***@",
            ),
            # GitHub tokens
            RedactionPattern(
                "github_token",
                r"\bgh[pousr]_[a-zA-Z0-9]{36,}\b",
                "***REDACTED***",
            ),
            RedactionPattern(
                "github_pat",
                r"\bgithub_pat_[a-zA-Z0-9_]{22,}\b",
                "***REDACTED***",
            ),
            # AWS credentials
            RedactionPattern(
                "aws_secret",
                r"(?i)(aws[_-]?secret[_-]?access[_-]?key|secret[_-]?access[_-]?key)\s*[=:]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
                r"\1=***REDACTED***",
            ),
            # Webhook secrets
            RedactionPattern(
                "webhook_secret",
                r"(?i)(webhook[_-]?secret|signing[_-]?secret|secret[_-]?key)\s*[=:]\s*['\"]?([a-zA-Z0-9\-_]{16,})['\"]?",
                r"\1=***REDACTED***",
            ),
            # Webhook URLs (discord/slack-style) — path carries the secret.
            RedactionPattern(
                "webhook_url",
                r"(?i)https?://[a-z0-9.\-]+/api/webhooks/[a-z0-9\-_/]+",
                "https://***WEBHOOK-REDACTED***",
            ),
            # Generic long high-entropy tokens in common key=value form
            RedactionPattern(
                "generic_token",
                r"(?i)\b(token|secret|credential|private[_-]?key)\s*[=:]\s*['\"]?([a-zA-Z0-9\-._]{16,})['\"]?",
                r"\1=***REDACTED***",
            ),
        ]

    # ------------------------------------------------------------------
    # Pattern redaction
    # ------------------------------------------------------------------

    def add_pattern(self, name: str, pattern: str,
                    replacement: str = "***REDACTED***") -> None:
        self._patterns.append(RedactionPattern(name, pattern, replacement))

    def redact(self, text: str) -> str:
        """Redact all detected secrets from a string."""
        return self._redact_with_types(text)[0]

    def _redact_with_types(self, text: str) -> tuple[str, List[str]]:
        """Redact and return (redacted_text, matched_type_names)."""
        if not text:
            return text, []
        result = text
        matched: List[str] = []
        for pattern in self._patterns:
            try:
                new_result = re.sub(pattern.pattern, pattern.replacement, result)
                if new_result != result:
                    matched.append(pattern.name)
                    result = new_result
            except re.error:
                continue
        # Exact-match redaction for registered secrets (verbatim).
        for secret in sorted(self._exact_secrets, key=len, reverse=True):
            if secret and secret in result:
                result = result.replace(secret, "***REDACTED***")
                matched.append("registered_secret")
        return result, sorted(set(matched))

    def scan(self, text: str) -> RedactionResult:
        """Return whether redaction changed the text, plus matched types."""
        redacted, matched = self._redact_with_types(text)
        return RedactionResult(
            redacted=redacted != text,
            text=redacted,
            matched_types=matched,
        )

    # ------------------------------------------------------------------
    # Structured redaction
    # ------------------------------------------------------------------

    def redact_dict(self, data: Dict[str, Any],
                    sensitive_keys: Optional[set] = None) -> Dict[str, Any]:
        """Recursively redact secret values from a mapping.

        Keys whose name suggests sensitivity (``key``, ``token``,
        ``password``, ``secret``, ``credential``, ``auth``) are redacted
        wholesale; all other string values are pattern-redacted.
        """
        sensitive = sensitive_keys or {
            "key", "api_key", "apikey", "token", "access_token", "refresh_token",
            "password", "passwd", "secret", "client_secret", "auth",
            "authorization", "credential", "private_key", "session_id",
        }
        out: Dict[str, Any] = {}
        for k, v in data.items():
            k_lower = k.lower()
            if isinstance(v, dict):
                out[k] = self.redact_dict(v, sensitive)
            elif isinstance(v, list):
                out[k] = [self.redact_dict(item, sensitive) if isinstance(item, dict)
                          else self.redact(item) if isinstance(item, str)
                          else item for item in v]
            elif isinstance(v, str):
                if k_lower in sensitive or "secret" in k_lower or "token" in k_lower:
                    out[k] = "***REDACTED***"
                else:
                    out[k] = self.redact(v)
            elif isinstance(v, bytes):
                try:
                    out[k] = self.redact(v.decode("utf-8", errors="replace"))
                except Exception:
                    out[k] = v
            else:
                out[k] = v
        return out

    def redact_json(self, text: str) -> str:
        """Redact a JSON string while preserving structure."""
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return self.redact(text)
        return json.dumps(self.redact_dict(data), indent=2)

    # ------------------------------------------------------------------
    # Registered secrets (exact match)
    # ------------------------------------------------------------------

    def register_secret(self, value: str) -> None:
        """Register a known secret value for exact-match redaction.

        Values registered here are redacted verbatim wherever they appear.
        """
        if value:
            self._exact_secrets.add(value)

    def register_secrets_from_manager(self) -> int:
        """Pull known secret values from the SecretsManager.

        Returns the number of values registered. Values are held in memory
        only — never logged or persisted.
        """
        count = 0
        try:
            from aetheros_security.secrets import get_secrets_manager
            manager = get_secrets_manager()
            for meta in manager.list_secrets():
                value = manager.retrieve(meta["name"], check_expiry=False)
                if value:
                    self._exact_secrets.add(value)
                    count += 1
        except Exception:
            logger.debug("Could not load secrets for redaction", exc_info=True)
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "patterns": len(self._patterns),
            "registered_secrets": len(self._exact_secrets),
        }


# Global redaction manager
_redaction_manager: RedactionManager | None = None


def get_redaction_manager() -> RedactionManager:
    """Return the global RedactionManager singleton."""
    global _redaction_manager
    if _redaction_manager is None:
        _redaction_manager = RedactionManager()
    return _redaction_manager