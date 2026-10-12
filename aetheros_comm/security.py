"""
Agent Communication Fabric — secret redaction and credential isolation
(master spec steps 24, 25, 26).

Before any message is logged, payloads and metadata are redacted (step 25).
Agents never receive raw credentials inside messages (step 24): the fabric
scans payloads for credential-shaped values and rejects them on sensitive
channels, and offers capability-scoped credential handles instead of raw
secrets.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from aetheros_security.redaction import get_redaction_manager
    _REDACTION_AVAILABLE = True
except Exception:  # pragma: no cover
    _REDACTION_AVAILABLE = False

#: Payload keys that are treated as credentials and rejected on sensitive
#: channels (step 24) / redacted everywhere (step 25).
_CREDENTIAL_KEYS = {
    "api_key", "apikey", "apiKey", "token", "access_token", "refresh_token",
    "password", "passwd", "secret", "client_secret", "private_key",
    "authorization", "credential", "credentials", "session_secret",
}

#: Credential-shaped value hints detected inside free text (step 25).
_CREDENTIAL_PATTERNS = (
    ("sk-", "api_key"),
    ("ghp_", "github_token"),
    ("AKIA", "aws_access_key"),
    ("xoxb-", "slack_token"),
    ("AIza", "google_key"),
)


@dataclass
class CredentialScanResult:
    """Result of scanning a payload for embedded credentials."""

    found: bool
    matched_keys: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)


def redact_payload(data: Any) -> Any:
    """Deep-redact ``data`` for logging / telemetry (step 25)."""
    if _REDACTION_AVAILABLE:
        try:
            return get_redaction_manager().redact_dict(
                _as_dict(data))
        except Exception:
            pass
    # Fallback: minimal structural redaction.
    return _fallback_redact(data)


def _as_dict(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data
    return {"value": data}


def _fallback_redact(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _fallback_redact(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_fallback_redact(v) for v in data]
    if isinstance(data, str):
        for prefix, _name in _CREDENTIAL_PATTERNS:
            if prefix in data:
                return "***REDACTED***"
    return data


def scan_for_credentials(payload: Dict[str, Any]) -> CredentialScanResult:
    """Scan a payload for raw credentials (step 24).

    Recursively inspects mapping keys and string values for credential-shaped
    content. The fabric rejects payloads that contain raw credentials on
    sensitive message channels.
    """
    matched_keys: List[str] = []
    matched_patterns: List[str] = []
    _scan(payload, matched_keys, matched_patterns, _CREDENTIAL_KEYS)
    return CredentialScanResult(
        found=bool(matched_keys or matched_patterns),
        matched_keys=matched_keys,
        matched_patterns=matched_patterns,
    )


def _scan(value: Any, keys: List[str], patterns: List[str],
          sensitive_keys: set) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in sensitive_keys:
                keys.append(k)
            _scan(v, keys, patterns, sensitive_keys)
    elif isinstance(value, list):
        for item in value:
            _scan(item, keys, patterns, sensitive_keys)
    elif isinstance(value, str):
        for prefix, name in _CREDENTIAL_PATTERNS:
            if value.startswith(prefix) or prefix in value:
                patterns.append(name)
                break


def to_log_safe(envelope_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return a redacted, log-safe copy of an envelope dict (step 25)."""
    copy = dict(envelope_dict)
    if "payload" in copy:
        copy["payload"] = redact_payload(copy["payload"])
    if "metadata" in copy:
        copy["metadata"] = redact_payload(copy["metadata"])
    if "securityContext" in copy:
        copy["securityContext"] = redact_payload(copy["securityContext"])
    if "signature" in copy and copy["signature"]:
        copy["signature"] = "***SIGNATURE***"
    return copy