"""Error taxonomy, error envelopes and user-safe error messages.

Every internal error supports an ``ErrorEnvelope`` with a stable error
type, a machine-readable error id, a diagnostic message (never surfaced
to normal users) and a separate user-facing ``safeMessage``.

Internal diagnostics and user-facing messages are strictly separated.
API keys, tokens, stack traces, filesystem paths and internal secrets
must never leak into ``safeMessage``.
"""

from __future__ import annotations

import enum
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class ErrorType(str, enum.Enum):
    """Standardized error taxonomy for the whole platform."""

    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    MEMORY_ERROR = "MEMORY_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class Severity(str, enum.Enum):
    """Severity of an error or incident."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY_CRITICAL = "SECURITY_CRITICAL"


#: Error types that are safe to retry (transient).
RETRYABLE_TYPES = frozenset(
    {
        ErrorType.NETWORK_ERROR,
        ErrorType.TIMEOUT,
        ErrorType.RATE_LIMIT,
        ErrorType.PROVIDER_ERROR,
    }
)

#: Error types that should never be retried blindly.
NON_RETRYABLE_TYPES = frozenset(
    {
        ErrorType.AUTHENTICATION_ERROR,
        ErrorType.AUTHORIZATION_ERROR,
        ErrorType.SECURITY_ERROR,
        ErrorType.VALIDATION_ERROR,
        ErrorType.CONFIGURATION_ERROR,
    }
)

#: User-safe message templates keyed by error type.
_USER_SAFE_MESSAGES: Dict[ErrorType, str] = {
    ErrorType.CONFIGURATION_ERROR: (
        "AetherOS configuration is invalid. Please check your settings or "
        "run `/doctor` to diagnose the problem."
    ),
    ErrorType.AUTHENTICATION_ERROR: (
        "Authentication with the external service failed. Check your API "
        "credentials or sign in again."
    ),
    ErrorType.AUTHORIZATION_ERROR: (
        "You are not authorized to perform this action."
    ),
    ErrorType.NETWORK_ERROR: (
        "A network connection problem prevented the request. AetherOS will "
        "retry automatically."
    ),
    ErrorType.TIMEOUT: (
        "The request took too long and timed out. AetherOS will retry or "
        "use an available fallback."
    ),
    ErrorType.RATE_LIMIT: (
        "The AI provider is temporarily rate-limited. AetherOS will retry "
        "or use an available fallback."
    ),
    ErrorType.PROVIDER_ERROR: (
        "The AI provider returned an error. AetherOS will retry or switch "
        "to an available fallback provider."
    ),
    ErrorType.MODEL_ERROR: (
        "The requested model could not complete the request. AetherOS will "
        "try again or use a fallback model."
    ),
    ErrorType.TOOL_ERROR: (
        "A tool failed while performing the action. AetherOS will retry "
        "the operation."
    ),
    ErrorType.MEMORY_ERROR: (
        "The memory system is temporarily unavailable. AetherOS will "
        "continue without memory access."
    ),
    ErrorType.STORAGE_ERROR: (
        "There was a problem reading or writing local data. AetherOS will "
        "retry the operation."
    ),
    ErrorType.PROTOCOL_ERROR: (
        "A communication protocol error occurred. AetherOS will retry."
    ),
    ErrorType.VALIDATION_ERROR: (
        "The request could not be validated. Please rephrase and try again."
    ),
    ErrorType.SECURITY_ERROR: (
        "A security check prevented this operation. If this seems wrong, "
        "contact your administrator."
    ),
    ErrorType.RESOURCE_EXHAUSTED: (
        "AetherOS ran out of a required resource (memory, disk, or rate "
        "budget). Close some sessions and try again."
    ),
    ErrorType.INTERNAL_ERROR: (
        "An unexpected internal error occurred. The details have been "
        "recorded for diagnosis."
    ),
    ErrorType.UNKNOWN_ERROR: (
        "Something unexpected went wrong. The details have been recorded "
        "for diagnosis."
    ),
}


def classify_error(exc: BaseException) -> ErrorType:
    """Best-effort classification of an exception into the taxonomy.

    Uses message scanning and common exception types; never raises.
    """
    if exc is None:
        return ErrorType.UNKNOWN_ERROR
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    if any(marker in name for marker in ("authentication", "unauthorized", "apikey", "apikeyerror")):
        return ErrorType.AUTHENTICATION_ERROR
    if any(marker in name for marker in ("permission", "authorization", "forbidden")):
        return ErrorType.AUTHORIZATION_ERROR
    if any(marker in name for marker in ("timeout",)):
        return ErrorType.TIMEOUT
    if any(marker in name for marker in ("ratelimit", "rate_limit", "429")):
        return ErrorType.RATE_LIMIT
    if any(marker in name for marker in ("network", "connection", "socket", "connectionerror")):
        return ErrorType.NETWORK_ERROR
    if any(marker in name for marker in ("provider", "upstream", "gateway", "api")):
        return ErrorType.PROVIDER_ERROR
    if any(marker in name for marker in ("model", "contextlength", "completion")):
        return ErrorType.MODEL_ERROR
    if any(marker in name for marker in ("tool",)):
        return ErrorType.TOOL_ERROR
    if any(marker in name for marker in ("memory",)):
        return ErrorType.MEMORY_ERROR
    if any(marker in name for marker in ("storage", "disk", "sqlite", "ioerror")):
        return ErrorType.STORAGE_ERROR
    if any(marker in name for marker in ("validation", "valueerror", "typeerror", "parserror")):
        return ErrorType.VALIDATION_ERROR
    if any(marker in name for marker in ("security", "signature", "hmac", "crypto")):
        return ErrorType.SECURITY_ERROR
    if any(marker in name for marker in ("memoryerror", "resource", "exhausted")):
        return ErrorType.RESOURCE_EXHAUSTED
    if any(marker in name for marker in ("config", "keyerror", "lookuperror")):
        return ErrorType.CONFIGURATION_ERROR

    if "429" in msg:
        return ErrorType.RATE_LIMIT
    if "401" in msg or "invalid api key" in msg:
        return ErrorType.AUTHENTICATION_ERROR
    if "403" in msg:
        return ErrorType.AUTHORIZATION_ERROR
    if "timeout" in msg or "timed out" in msg:
        return ErrorType.TIMEOUT
    if "connection" in msg or "network" in msg or "dns" in msg:
        return ErrorType.NETWORK_ERROR
    if "context length" in msg or "max_tokens" in msg:
        return ErrorType.MODEL_ERROR

    return ErrorType.INTERNAL_ERROR


def user_safe_message(error_type: ErrorType, exc: Optional[BaseException] = None) -> str:
    """Return a user-safe message for an error type.

    Never includes exception internals; falls back to a generic message.
    """
    return _USER_SAFE_MESSAGES.get(error_type, _USER_SAFE_MESSAGES[ErrorType.UNKNOWN_ERROR])


@dataclass
class ErrorEnvelope:
    """Standard envelope wrapping an internal error.

    ``message`` is the internal diagnostic message — it may contain
    technical detail but must never contain secrets.  ``safeMessage`` is
    what normal users see.
    """

    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: ErrorType = ErrorType.UNKNOWN_ERROR
    message: str = ""
    safe_message: str = ""
    severity: Severity = Severity.ERROR
    component: str = ""
    operation: str = ""
    trace_id: Optional[str] = None
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    retryable: bool = False
    recovery_action: str = ""
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        component: str = "",
        operation: str = "",
        trace_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        message: Optional[str] = None,
        severity: Optional[Severity] = None,
        recovery_action: str = "",
    ) -> "ErrorEnvelope":
        """Build an envelope from an exception, classifying it automatically."""
        error_type = classify_error(exc)
        return cls(
            type=error_type,
            message=message or f"{type(exc).__name__}: {exc}",
            safe_message=user_safe_message(error_type, exc),
            severity=severity or (Severity.CRITICAL if isinstance(exc, SystemExit) else Severity.ERROR),
            component=component,
            operation=operation,
            trace_id=trace_id,
            mission_id=mission_id,
            task_id=task_id,
            agent_id=agent_id,
            retryable=error_type in RETRYABLE_TYPES,
            recovery_action=recovery_action,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dict (never includes stack traces)."""
        return {
            "error_id": self.error_id,
            "type": self.type.value,
            "message": self.message,
            "safe_message": self.safe_message,
            "severity": self.severity.value,
            "component": self.component,
            "operation": self.operation,
            "trace_id": self.trace_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "retryable": self.retryable,
            "recovery_action": self.recovery_action,
            "timestamp": self.timestamp,
        }


def format_traceback(exc: BaseException) -> str:
    """Return a compact traceback string for diagnostics (not for users)."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))