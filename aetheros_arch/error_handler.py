"""Centralized Error Handling System for AetherOS.

Provides structured error handling with:
- Typed error hierarchy
- User-friendly error messages
- Recovery suggestions
- Automatic diagnostics
- No raw tracebacks to users
"""

from __future__ import annotations

import enum
import logging
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger("aetheros_arch.error")


class ErrorLevel(enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(enum.Enum):
    CONFIG = "configuration"
    NETWORK = "network"
    PROVIDER = "provider"
    AUTH = "authentication"
    RUNTIME = "runtime"
    MEMORY = "memory"
    PLUGIN = "plugin"
    TOOL = "tool"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information captured at the error site."""

    component: str = ""
    operation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""


@dataclass
class ErrorReport:
    """Structured error report for user display."""

    message: str
    level: ErrorLevel = ErrorLevel.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    context: ErrorContext = field(default_factory=ErrorContext)
    traceback: str = ""
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def user_message(self) -> str:
        """Return a user-friendly message with no raw traceback."""
        parts = [self.message]
        if self.context.suggestion:
            parts.append(f"  Suggestion: {self.context.suggestion}")
        if self.context.component:
            parts.append(f"  Component: {self.context.component}")
        return "\n".join(parts)

    def diagnostic_message(self) -> str:
        """Return a detailed diagnostic message (for logs)."""
        parts = [
            f"[{self.level.value.upper()}] {self.category.value}: {self.message}",
        ]
        if self.context.component:
            parts.append(f"  Component: {self.context.component}")
        if self.context.operation:
            parts.append(f"  Operation: {self.context.operation}")
        if self.context.details:
            parts.append(f"  Details: {self.context.details}")
        if self.traceback:
            parts.append(f"  Traceback:\n{self.traceback}")
        return "\n".join(parts)


class AetherOSError(Exception):
    """Base exception for all AetherOS errors."""

    def __init__(
        self,
        message: str,
        level: ErrorLevel = ErrorLevel.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self._message = message
        self.level = level
        self.category = category
        self.context = context or ErrorContext()
        self.cause = cause

    @property
    def message(self) -> str:
        return self._message

    def to_report(self) -> ErrorReport:
        tb = ""
        if self.cause:
            tb = "".join(
                traceback.format_exception(
                    type(self.cause), self.cause, self.cause.__traceback__
                )
            )
        return ErrorReport(
            message=self._message,
            level=self.level,
            category=self.category,
            context=self.context,
            traceback=tb,
        )


class ConfigError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.ERROR, ErrorCategory.CONFIG, context, cause)


class NetworkError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.ERROR, ErrorCategory.NETWORK, context, cause)


class ProviderError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.ERROR, ErrorCategory.PROVIDER, context, cause)


class AuthError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.ERROR, ErrorCategory.AUTH, context, cause)


class RuntimeError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.ERROR, ErrorCategory.RUNTIME, context, cause)


class StartupError(AetherOSError):
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message, ErrorLevel.CRITICAL, ErrorCategory.STARTUP, context, cause)


_SUGGESTIONS: Dict[str, str] = {
    "connection refused": "Check that the service is running and the port is correct.",
    "timeout": "The request timed out. Check your network connection and try again.",
    "api key": "Your API key may be invalid or missing. Run `aetheros setup` to configure it.",
    "not found": "The requested resource was not found. Check the path or identifier.",
    "permission denied": "You don't have permission to access this resource.",
    "authentication": "Authentication failed. Check your credentials and try again.",
    "rate limit": "Too many requests. Please wait and try again.",
    "unexpected": "An unexpected error occurred. Please try again.",
}


class ErrorHandler:
    """Centralized error handler.

    Captures, categorizes, and reports errors with user-friendly messages.
    """

    def __init__(self) -> None:
        self._history: List[ErrorReport] = []
        self._max_history = 100

    def handle(
        self,
        exc: Exception,
        component: str = "",
        operation: str = "",
        suggestion: str = "",
    ) -> ErrorReport:
        """Handle an exception and return a structured report."""
        if isinstance(exc, AetherOSError):
            report = exc.to_report()
            if component:
                report.context.component = component
            if operation:
                report.context.operation = operation
            if suggestion:
                report.context.suggestion = suggestion
        else:
            report = self._build_report(exc, component, operation, suggestion)

        self._history.append(report)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._log(report)
        return report

    def handle_and_exit(
        self,
        exc: Exception,
        component: str = "",
        operation: str = "",
        suggestion: str = "",
        exit_code: int = 1,
    ) -> None:
        """Handle an error and exit the process."""
        report = self.handle(exc, component, operation, suggestion)
        print(f"\nError: {report.user_message()}", file=sys.stderr)
        if report.level == ErrorLevel.CRITICAL:
            logger.critical(report.diagnostic_message())
        sys.exit(exit_code)

    def recent_errors(self, count: int = 5) -> List[ErrorReport]:
        return self._history[-count:]

    def clear_history(self) -> None:
        self._history.clear()

    @staticmethod
    def suggest_fix(message: str) -> str:
        """Generate a recovery suggestion based on the error message."""
        msg_lower = message.lower()
        for keyword, suggestion in _SUGGESTIONS.items():
            if keyword in msg_lower:
                return suggestion
        return ""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_report(
        self,
        exc: Exception,
        component: str,
        operation: str,
        suggestion: str,
    ) -> ErrorReport:
        tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        msg = str(exc) or type(exc).__name__
        return ErrorReport(
            message=msg,
            level=self._classify_level(exc),
            category=self._classify_category(exc, msg),
            context=ErrorContext(
                component=component,
                operation=operation,
                suggestion=suggestion or self.suggest_fix(msg),
            ),
            traceback=tb,
        )

    @staticmethod
    def _classify_level(exc: Exception) -> ErrorLevel:
        if isinstance(exc, StartupError):
            return ErrorLevel.CRITICAL
        if isinstance(exc, (ConfigError, AuthError)):
            return ErrorLevel.ERROR
        if isinstance(exc, NetworkError):
            return ErrorLevel.WARNING
        return ErrorLevel.ERROR

    @staticmethod
    def _classify_category(exc: Exception, msg: str) -> ErrorCategory:
        if isinstance(exc, ConfigError):
            return ErrorCategory.CONFIG
        if isinstance(exc, NetworkError):
            return ErrorCategory.NETWORK
        if isinstance(exc, ProviderError):
            return ErrorCategory.PROVIDER
        if isinstance(exc, AuthError):
            return ErrorCategory.AUTH
        if isinstance(exc, RuntimeError):
            return ErrorCategory.RUNTIME
        if isinstance(exc, StartupError):
            return ErrorCategory.STARTUP
        msg_lower = msg.lower()
        if "config" in msg_lower:
            return ErrorCategory.CONFIG
        if "network" in msg_lower or "connection" in msg_lower:
            return ErrorCategory.NETWORK
        if "api_key" in msg_lower or "auth" in msg_lower:
            return ErrorCategory.AUTH
        if "provider" in msg_lower:
            return ErrorCategory.PROVIDER
        return ErrorCategory.UNKNOWN

    @staticmethod
    def _log(report: ErrorReport) -> None:
        log_method = {
            ErrorLevel.DEBUG: logger.debug,
            ErrorLevel.INFO: logger.info,
            ErrorLevel.WARNING: logger.warning,
            ErrorLevel.ERROR: logger.error,
            ErrorLevel.CRITICAL: logger.critical,
        }.get(report.level, logger.error)
        log_method(report.diagnostic_message())