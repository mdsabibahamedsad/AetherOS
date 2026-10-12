"""Provider Manager — registration, lifecycle, health, priority, fallback.

Wraps the existing ``providers`` registry with a comprehensive management
layer that supports enable/disable, health monitoring, priority ordering,
and automatic fallback chains.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_providers.manager")


class ProviderStatus(enum.Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ProviderInfo:
    name: str
    display_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    priority: int = 0
    enabled: bool = True
    health_check_passed: bool = False
    last_health_check: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    consecutive_failures: int = 0
    recovery_after: float = 0.0
    api_key_configured: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_function_calling: bool = True
    model_count: int = 0
    provider_type: str = "cloud"


HealthCheckFn = Callable[[], bool]


class ProviderManager:
    """Comprehensive provider lifecycle manager.

    Wraps the existing ``providers`` registry. Supports:
    - Register, enable, disable, remove, reconnect
    - Health checking with configurable intervals
    - Priority-based ordering
    - Automatic fallback chains
    - Status tracking and recovery
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, ProviderInfo] = {}
        self._health_checks: Dict[str, HealthCheckFn] = {}
        self._fallback_chains: Dict[str, List[str]] = {}
        self._listeners: List[Callable[[str, ProviderStatus, ProviderStatus], None]] = []
        self._health_check_interval: float = 60.0
        self._recovery_delay: float = 30.0
        self._max_consecutive_failures: int = 3

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        display_name: str = "",
        priority: int = 0,
        provider_type: str = "cloud",
        health_check_fn: Optional[HealthCheckFn] = None,
    ) -> ProviderInfo:
        """Register a provider with the manager."""
        with self._lock:
            info = ProviderInfo(
                name=name,
                display_name=display_name or name,
                priority=priority,
                provider_type=provider_type,
            )
            self._providers[name] = info
            if health_check_fn:
                self._health_checks[name] = health_check_fn
            logger.info("Provider registered: %s (priority=%d, type=%s)", name, priority, provider_type)
            return info

    def register_from_profile(self, profile: Any) -> ProviderInfo:
        """Register a provider from an existing ``ProviderProfile`` instance."""
        name = profile.name
        return self.register(
            name=name,
            display_name=profile.display_name or name,
            priority=0,
            provider_type="cloud",
            health_check_fn=lambda: True,
        )

    def discover_all(self) -> int:
        """Discover and register all providers from the existing registry."""
        try:
            from providers import list_providers
            profiles = list_providers()
            count = 0
            for profile in profiles:
                if profile.name not in self._providers:
                    self.register_from_profile(profile)
                    count += 1
            logger.info("Discovered %d providers from registry", count)
            return count
        except ImportError:
            logger.warning("providers registry not available")
            return 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def enable(self, name: str) -> bool:
        with self._lock:
            info = self._providers.get(name)
            if info is None:
                return False
            info.enabled = True
            info.status = ProviderStatus.UNKNOWN
            logger.info("Provider enabled: %s", name)
            return True

    def disable(self, name: str) -> bool:
        with self._lock:
            info = self._providers.get(name)
            if info is None:
                return False
            info.enabled = False
            old_status = info.status
            info.status = ProviderStatus.DISABLED
            self._notify(name, old_status, ProviderStatus.DISABLED)
            logger.info("Provider disabled: %s", name)
            return True

    def remove(self, name: str) -> bool:
        with self._lock:
            if name not in self._providers:
                return False
            del self._providers[name]
            self._health_checks.pop(name, None)
            self._fallback_chains.pop(name, None)
            logger.info("Provider removed: %s", name)
            return True

    # ------------------------------------------------------------------
    # Status & Health
    # ------------------------------------------------------------------

    def get_status(self, name: str) -> Optional[ProviderStatus]:
        info = self._providers.get(name)
        return info.status if info else None

    def get_info(self, name: str) -> Optional[ProviderInfo]:
        return self._providers.get(name)

    def check_health(self, name: str) -> bool:
        """Run a health check for a specific provider."""
        info = self._providers.get(name)
        if info is None:
            return False
        if not info.enabled:
            return False

        check_fn = self._health_checks.get(name)
        if check_fn is None:
            info.health_check_passed = True
            info.status = ProviderStatus.ONLINE
            return True

        start = time.monotonic()
        try:
            healthy = check_fn()
            elapsed = (time.monotonic() - start) * 1000
            info.latency_ms = round(elapsed, 1)
            info.last_health_check = time.time()

            old_status = info.status
            if healthy:
                info.health_check_passed = True
                info.consecutive_failures = 0
                info.status = ProviderStatus.ONLINE
            else:
                info.consecutive_failures += 1
                info.status = ProviderStatus.DEGRADED if info.consecutive_failures < self._max_consecutive_failures else ProviderStatus.OFFLINE
            if old_status != info.status:
                self._notify(name, old_status, info.status)
            return healthy
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            info.latency_ms = round(elapsed, 1)
            info.last_health_check = time.time()
            info.consecutive_failures += 1
            info.error_count += 1
            old_status = info.status
            info.status = ProviderStatus.ERROR
            info.health_check_passed = False
            if old_status != info.status:
                self._notify(name, old_status, info.status)
            logger.warning("Health check failed for %s: %s", name, exc)
            return False

    def check_all_health(self) -> Dict[str, bool]:
        """Run health checks for all enabled providers."""
        results = {}
        with self._lock:
            names = list(self._providers.keys())
        for name in names:
            results[name] = self.check_health(name)
        return results

    def get_healthy_providers(self) -> List[ProviderInfo]:
        return [
            info for info in self._providers.values()
            if info.enabled and info.status == ProviderStatus.ONLINE
        ]

    def get_enabled_providers(self) -> List[ProviderInfo]:
        return [
            info for info in self._providers.values()
            if info.enabled
        ]

    def get_providers_by_priority(self) -> List[ProviderInfo]:
        return sorted(
            self.get_enabled_providers(),
            key=lambda p: (-p.priority, p.name),
        )

    def get_providers_by_type(self, provider_type: str) -> List[ProviderInfo]:
        return [
            info for info in self._providers.values()
            if info.provider_type == provider_type and info.enabled
        ]

    # ------------------------------------------------------------------
    # Fallback chains
    # ------------------------------------------------------------------

    def set_fallback_chain(self, primary: str, fallbacks: List[str]) -> None:
        """Set fallback providers for a primary provider."""
        with self._lock:
            self._fallback_chains[primary] = fallbacks

    def get_fallback_chain(self, name: str) -> List[str]:
        return self._fallback_chains.get(name, [])

    def resolve_with_fallback(self, name: str) -> List[str]:
        """Resolve a provider name to an ordered list including fallbacks."""
        result = [name]
        chain = self.get_fallback_chain(name)
        for fb in chain:
            info = self._providers.get(fb)
            if info and info.enabled:
                result.append(fb)
        return result

    # ------------------------------------------------------------------
    # Priority management
    # ------------------------------------------------------------------

    def set_priority(self, name: str, priority: int) -> bool:
        with self._lock:
            info = self._providers.get(name)
            if info is None:
                return False
            info.priority = priority
            return True

    def get_prioritized(self, names: Optional[List[str]] = None) -> List[ProviderInfo]:
        providers = [
            info for info in self._providers.values()
            if info.enabled and (names is None or info.name in names)
        ]
        return sorted(providers, key=lambda p: (-p.priority, p.name))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_status_change(self, callback: Callable[[str, ProviderStatus, ProviderStatus], None]) -> None:
        self._listeners.append(callback)

    def _notify(self, name: str, old: ProviderStatus, new: ProviderStatus) -> None:
        for cb in self._listeners:
            try:
                cb(name, old, new)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_health_check_interval(self, seconds: float) -> None:
        self._health_check_interval = seconds

    def set_recovery_delay(self, seconds: float) -> None:
        self._recovery_delay = seconds

    def mark_recovered(self, name: str) -> None:
        with self._lock:
            info = self._providers.get(name)
            if info:
                info.consecutive_failures = 0
                info.status = ProviderStatus.ONLINE

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def all_providers(self) -> Dict[str, ProviderInfo]:
        with self._lock:
            return dict(self._providers)

    @property
    def provider_names(self) -> List[str]:
        return list(self._providers.keys())

    @property
    def online_count(self) -> int:
        return sum(1 for p in self._providers.values() if p.status == ProviderStatus.ONLINE)

    @property
    def enabled_count(self) -> int:
        return sum(1 for p in self._providers.values() if p.enabled)

    def summary(self) -> str:
        lines = [f"Provider Manager: {self.enabled_count} enabled, {self.online_count} online"]
        for info in sorted(self._providers.values(), key=lambda p: (-p.priority, p.name)):
            status_icon = {
                ProviderStatus.ONLINE: "✓",
                ProviderStatus.OFFLINE: "✗",
                ProviderStatus.DEGRADED: "⚠",
                ProviderStatus.ERROR: "!!",
                ProviderStatus.DISABLED: "⊘",
                ProviderStatus.UNKNOWN: "?",
            }.get(info.status, "?")
            lines.append(
                f"  {status_icon} {info.display_name} "
                f"(priority={info.priority}, latency={info.latency_ms:.0f}ms)"
            )
        return "\n".join(lines)