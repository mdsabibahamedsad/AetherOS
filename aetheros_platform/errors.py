"""Canonical typed errors (Master 62 §7). No secret/filesystem leakage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

CATEGORIES = (
    "AUTHENTICATION_REQUIRED", "AUTHORIZATION_DENIED", "POLICY_DENIED",
    "APPROVAL_REQUIRED", "INVALID_REQUEST", "INVALID_SCHEMA", "RATE_LIMITED",
    "QUOTA_EXCEEDED", "RESOURCE_UNAVAILABLE", "MODEL_UNAVAILABLE",
    "TOOL_UNAVAILABLE", "AGENT_UNAVAILABLE", "TIMEOUT", "CONFLICT",
    "IDEMPOTENCY_CONFLICT", "NETWORK_ERROR", "STORAGE_ERROR",
    "SECURITY_VIOLATION", "SANDBOX_VIOLATION", "PROMPT_INJECTION_DETECTED",
    "DATA_EXFILTRATION_BLOCKED", "CAPABILITY_NOT_GRANTED", "UNSUPPORTED_VERSION",
    "DEPRECATED_API", "INTERNAL_ERROR",
)

HTTP_STATUS = {
    "AUTHENTICATION_REQUIRED": 401, "AUTHORIZATION_DENIED": 403,
    "POLICY_DENIED": 403, "APPROVAL_REQUIRED": 403, "INVALID_REQUEST": 400,
    "INVALID_SCHEMA": 422, "RATE_LIMITED": 429, "QUOTA_EXCEEDED": 429,
    "RESOURCE_UNAVAILABLE": 503, "MODEL_UNAVAILABLE": 503,
    "TOOL_UNAVAILABLE": 503, "AGENT_UNAVAILABLE": 503, "TIMEOUT": 504,
    "CONFLICT": 409, "IDEMPOTENCY_CONFLICT": 409, "NETWORK_ERROR": 502,
    "STORAGE_ERROR": 500, "SECURITY_VIOLATION": 403, "SANDBOX_VIOLATION": 403,
    "PROMPT_INJECTION_DETECTED": 400, "DATA_EXFILTRATION_BLOCKED": 403,
    "CAPABILITY_NOT_GRANTED": 403, "UNSUPPORTED_VERSION": 400,
    "DEPRECATED_API": 410, "INTERNAL_ERROR": 500,
}

RETRYABLE = {"RATE_LIMITED", "QUOTA_EXCEEDED", "TIMEOUT", "NETWORK_ERROR",
             "RESOURCE_UNAVAILABLE", "MODEL_UNAVAILABLE", "TOOL_UNAVAILABLE",
             "AGENT_UNAVAILABLE"}


@dataclass
class AetherError(Exception):
    code: str
    message: str
    category: str = "INTERNAL_ERROR"
    retryable: bool = False
    severity: str = "error"
    requestId: str = ""
    traceId: str = ""
    taskId: str = ""
    capability: str = ""
    policyDecision: str = ""
    remediation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert self.category in CATEGORIES, self.category
        if not self.retryable:
            self.retryable = self.category in RETRYABLE

    @property
    def http_status(self) -> int:
        return HTTP_STATUS.get(self.category, 500)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def err(category: str, message: str, **kw: Any) -> AetherError:
    return AetherError(code=category, message=message, category=category, **kw)
