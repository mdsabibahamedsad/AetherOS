"""AetherOS Architecture Foundation.

This package provides the foundational architecture for AetherOS:
configuration management, health checking, error handling, dependency
injection, state management, boot sequencing, and performance optimization.

Every module in this package is:
- Production-ready
- Fully typed
- Tested
- Thread-safe where applicable
"""

from aetheros_arch.config_manager import ConfigManager
from aetheros_arch.health_checker import HealthChecker, HealthStatus, HealthCheckResult
from aetheros_arch.error_handler import ErrorHandler, AetherOSError, ErrorLevel
from aetheros_arch.service_container import ServiceContainer, ServiceLifecycle
from aetheros_arch.state_manager import StateManager, AppState
from aetheros_arch.boot_sequence import BootSequence, BootStage
from aetheros_arch.security_foundation import SecurityFoundation
from aetheros_arch.performance import PerformanceOptimizer

__all__ = [
    "ConfigManager",
    "HealthChecker",
    "HealthStatus",
    "HealthCheckResult",
    "ErrorHandler",
    "AetherOSError",
    "ErrorLevel",
    "ServiceContainer",
    "ServiceLifecycle",
    "StateManager",
    "AppState",
    "BootSequence",
    "BootStage",
    "SecurityFoundation",
    "PerformanceOptimizer",
]