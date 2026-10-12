"""
AetherOS canonical error taxonomy (Master 59 §35).

One typed, serializable, traceable error model for the control plane,
runtime plane, and isolation plane. Every error carries a machine-readable
code, a user-readable message, trace linkage (trace/capsule/agent/intent
ids), and an optional remediation hint. Boundary layers translate these
to/from builtin exceptions without losing the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from kernel.core.types import _now, new_id


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass
class AetherosError(Exception):
    """Base for all canonical errors. `code` is stable API; `message` is human."""
    code: str = "internal_error"
    message: str = "internal error"
    trace_id: str = ""
    capsule_id: str = ""
    agent_id: str = ""
    intent_id: str = ""
    hint: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)
    error_id: str = field(default_factory=lambda: new_id("err"))

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "code": self.code,
            "message": self.message,
            "trace_id": self.trace_id,
            "capsule_id": self.capsule_id,
            "agent_id": self.agent_id,
            "intent_id": self.intent_id,
            "hint": self.hint,
            "details": dict(self.details),
            "timestamp": self.timestamp,
            "class": type(self).__name__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AetherosError":
        kind = _CODE_TO_CLASS.get(data.get("code", ""), AetherosError)
        err = kind.__new__(kind)
        AetherosError.__init__(
            err, code=data.get("code", "internal_error"),
            message=data.get("message", "internal error"),
            trace_id=data.get("trace_id", ""),
            capsule_id=data.get("capsule_id", ""),
            agent_id=data.get("agent_id", ""),
            intent_id=data.get("intent_id", ""),
            hint=data.get("hint", ""),
            details=dict(data.get("details", {})),
            timestamp=data.get("timestamp", _now()),
            error_id=data.get("error_id", new_id("err")))
        return err


# ---------------------------------------------------------------------------
# Taxonomy (§35). Each code maps to exactly one class.
# ---------------------------------------------------------------------------


@dataclass
class ConfigurationError(AetherosError):
    code: str = "configuration_error"
    message = "invalid configuration"


@dataclass
class ValidationError(AetherosError):
    code: str = "validation_error"
    message = "validation failed"


@dataclass
class AuthenticationError(AetherosError):
    code: str = "authentication_error"
    message = "authentication failed"


@dataclass
class AuthorizationError(AetherosError):
    code: str = "authorization_error"
    message = "not authorized"


@dataclass
class PolicyDeniedError(AuthorizationError):
    code: str = "policy_denied"
    message = "policy denied the action"


@dataclass
class CapabilityDeniedError(AuthorizationError):
    code: str = "capability_denied"
    message = "capability not granted"


@dataclass
class ResourceLimitError(AetherosError):
    code: str = "resource_limit"
    message = "resource limit exceeded"


@dataclass
class ToolExecutionError(AetherosError):
    code: str = "tool_execution_error"
    message = "tool execution failed"


@dataclass
class ModelError(AetherosError):
    code: str = "model_error"
    message = "model call failed"


@dataclass
class ModelUnavailableError(ModelError):
    code: str = "model_unavailable"
    message = "model unavailable (not configured or unhealthy)"


@dataclass
class NetworkError(AetherosError):
    code: str = "network_error"
    message = "network operation failed"


@dataclass
class BrowserError(AetherosError):
    code: str = "browser_error"
    message = "browser operation failed"


@dataclass
class ComputerControlError(AetherosError):
    code: str = "computer_control_error"
    message = "computer-control operation failed"


@dataclass
class MemoryError(AetherosError):
    code: str = "memory_error"
    message = "memory operation failed"


@dataclass
class CheckpointError(AetherosError):
    code: str = "checkpoint_error"
    message = "checkpoint operation failed"


@dataclass
class VerificationError(AetherosError):
    code: str = "verification_error"
    message = "verification failed"


@dataclass
class RecoveryError(AetherosError):
    code: str = "recovery_error"
    message = "recovery failed"


@dataclass
class SecurityViolationError(AetherosError):
    code: str = "security_violation"
    message = "security boundary violation"


@dataclass
class QuarantineError(SecurityViolationError):
    code: str = "quarantined"
    message = "capsule/agent is quarantined"


@dataclass
class IsolationError(SecurityViolationError):
    code: str = "isolation_error"
    message = "isolation boundary violation"


@dataclass
class ExpiredError(AuthorizationError):
    code: str = "expired"
    message = "expired (capsule, grant, approval, or credential)"


@dataclass
class RateLimitError(ResourceLimitError):
    code: str = "rate_limited"
    message = "rate limit exceeded"


@dataclass
class IdempotencyError(AetherosError):
    code: str = "idempotency_conflict"
    message = "duplicate side-effect blocked by idempotency key"


@dataclass
class MigrationError(AetherosError):
    code: str = "migration_error"
    message = "capsule migration failed"


@dataclass
class ReplayError(AetherosError):
    code: str = "replay_denied"
    message = "replay would execute side effects; denied"


_CODE_TO_CLASS = {
    "configuration_error": ConfigurationError,
    "validation_error": ValidationError,
    "authentication_error": AuthenticationError,
    "authorization_error": AuthorizationError,
    "policy_denied": PolicyDeniedError,
    "capability_denied": CapabilityDeniedError,
    "resource_limit": ResourceLimitError,
    "tool_execution_error": ToolExecutionError,
    "model_error": ModelError,
    "model_unavailable": ModelUnavailableError,
    "network_error": NetworkError,
    "browser_error": BrowserError,
    "computer_control_error": ComputerControlError,
    "memory_error": MemoryError,
    "checkpoint_error": CheckpointError,
    "verification_error": VerificationError,
    "recovery_error": RecoveryError,
    "security_violation": SecurityViolationError,
    "quarantined": QuarantineError,
    "isolation_error": IsolationError,
    "expired": ExpiredError,
    "rate_limited": RateLimitError,
    "idempotency_conflict": IdempotencyError,
    "migration_error": MigrationError,
    "replay_denied": ReplayError,
}


# ---------------------------------------------------------------------------
# Builtin translation (boundaries speak builtins; core speaks codes)
# ---------------------------------------------------------------------------

_BUILTIN_MAP = [
    (PermissionError, AuthorizationError, "authorization_error"),
    (KeyError, ValidationError, "validation_error"),
    (ValueError, ValidationError, "validation_error"),
    (TimeoutError, ToolExecutionError, "tool_execution_error"),
]


def from_builtin(exc: BaseException, **trace: str) -> AetherosError:
    """Translate a builtin exception to the canonical taxonomy (best effort)."""
    if isinstance(exc, AetherosError):
        return exc
    text = str(exc)[:500]
    lowered = text.lower()
    if isinstance(exc, PermissionError):
        if "quota" in lowered or "budget" in lowered or "insufficient resources" in lowered:
            return ResourceLimitError(message=text, **trace)
        if "quarantine" in lowered:
            return QuarantineError(message=text, **trace)
        if "expired" in lowered:
            return ExpiredError(message=text, **trace)
        if "capability" in lowered and "manifest" in lowered:
            return CapabilityDeniedError(message=text, **trace)
        if "rate limit" in lowered:
            return RateLimitError(message=text, **trace)
        return PolicyDeniedError(message=text, **trace)
    if isinstance(exc, (KeyError, ValueError)):
        return ValidationError(message=text, **trace)
    if isinstance(exc, TimeoutError):
        return ToolExecutionError(message=text, hint="retry with backoff", **trace)
    return AetherosError(message=text, **trace)


def error_codes() -> List[str]:
    return sorted(_CODE_TO_CLASS)
