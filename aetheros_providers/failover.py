"""Failover System — automatic retry, fallback model/provider, recovery.

If one provider fails:
- Automatically retry
- Fallback to another model
- Fallback to another provider
- Configurable retry delay
- Automatic recovery detection
"""

from __future__ import annotations

import enum
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_providers.multi_provider import MultiProviderOrchestrator

logger = logging.getLogger("aetheros_providers.failover")


class FailoverStrategy(enum.Enum):
    """Strategy for failover behavior."""
    RETRY_SAME = "retry_same"
    FALLBACK_MODEL = "fallback_model"
    FALLBACK_PROVIDER = "fallback_provider"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class FailoverConfig:
    strategy: FailoverStrategy = FailoverStrategy.RETRY_SAME
    max_retries: int = 3
    retry_delay_base: float = 1.0
    retry_delay_max: float = 30.0
    retry_jitter: float = 0.5
    fallback_models: List[str] = field(default_factory=list)
    fallback_providers: List[str] = field(default_factory=list)
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 60.0
    recovery_check_interval: float = 30.0


@dataclass
class FailoverResult:
    success: bool
    provider: str
    model: str
    attempts: int = 0
    total_latency_ms: float = 0.0
    error: str = ""
    used_fallback: bool = False
    fallback_chain: List[str] = field(default_factory=list)


ProviderCallFn = Callable[[str, str, Dict[str, Any]], Any]


class FailoverManager:
    """Automatic failover management for provider calls.

    Supports:
    - Retry with exponential backoff and jitter
    - Fallback to alternative models
    - Fallback to alternative providers
    - Circuit breaker pattern
    - Automatic recovery detection
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._configs: Dict[str, FailoverConfig] = {}
        self._circuit_state: Dict[str, Dict[str, Any]] = {}
        self._call_fn: Optional[ProviderCallFn] = None
        self._provider_manager: Optional[Any] = None

    def set_call_function(self, call_fn: ProviderCallFn) -> None:
        self._call_fn = call_fn

    def set_provider_manager(self, pm: Any) -> None:
        self._provider_manager = pm

    def configure(self, provider: str, config: FailoverConfig) -> None:
        with self._lock:
            self._configs[provider] = config

    def get_config(self, provider: str) -> FailoverConfig:
        with self._lock:
            return self._configs.get(provider, FailoverConfig())

    # ------------------------------------------------------------------
    # Execution with failover
    # ------------------------------------------------------------------

    def execute(
        self,
        provider: str,
        model: str,
        params: Dict[str, Any],
    ) -> FailoverResult:
        """Execute a provider call with automatic failover."""
        config = self.get_config(provider)
        fallback_models = config.fallback_models[:]
        fallback_providers = config.fallback_providers[:]
        result = FailoverResult(success=False, provider=provider, model=model)

        if self._is_circuit_open(provider):
            result.success = False
            result.error = f"Circuit breaker open for {provider}"
            return result

        chain = [(provider, model)]
        for fb_model in fallback_models:
            chain.append((provider, fb_model))
        for fb_provider in fallback_providers:
            chain.append((fb_provider, model))

        result.fallback_chain = [f"{p}/{m}" for p, m in chain]

        for idx, (current_provider, current_model) in enumerate(chain):
            retries = config.max_retries if idx == 0 else 1

            for attempt in range(retries):
                result.attempts += 1
                start = time.monotonic()

                try:
                    if self._call_fn:
                        response = self._call_fn(current_provider, current_model, params)
                    else:
                        response = self._make_fallback_call(current_provider, current_model, params)

                    elapsed = (time.monotonic() - start) * 1000
                    result.total_latency_ms += elapsed
                    result.success = True
                    result.provider = current_provider
                    result.model = current_model
                    result.used_fallback = idx > 0

                    self._record_success(current_provider)
                    return result

                except Exception as exc:
                    elapsed = (time.monotonic() - start) * 1000
                    result.total_latency_ms += elapsed
                    result.error = str(exc)

                    if attempt < retries - 1:
                        delay = self._calculate_delay(attempt, config)
                        logger.warning(
                            "Retry %d/%d for %s/%s in %.1fs: %s",
                            attempt + 1, retries, current_provider, current_model,
                            delay, exc,
                        )
                        time.sleep(delay)

        self._record_failure(provider)
        result.success = False
        return result

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def _is_circuit_open(self, provider: str) -> bool:
        with self._lock:
            state = self._circuit_state.get(provider, {})
            if not state.get("open", False):
                return False
            if time.time() - state.get("opened_at", 0) >= self.get_config(provider).circuit_breaker_reset_seconds:
                state["open"] = False
                state["failures"] = 0
                logger.info("Circuit breaker reset for %s", provider)
                return False
            return True

    def _record_success(self, provider: str) -> None:
        with self._lock:
            state = self._circuit_state.setdefault(provider, {})
            state["failures"] = 0
            state["open"] = False

    def _record_failure(self, provider: str) -> None:
        with self._lock:
            config = self.get_config(provider)
            state = self._circuit_state.setdefault(provider, {})
            state["failures"] = state.get("failures", 0) + 1
            if state["failures"] >= config.circuit_breaker_threshold:
                state["open"] = True
                state["opened_at"] = time.time()
                logger.warning(
                    "Circuit breaker opened for %s (%d failures)",
                    provider, state["failures"],
                )

    def reset_circuit_breaker(self, provider: str) -> None:
        with self._lock:
            self._circuit_state.pop(provider, None)

    def reset_all_circuit_breakers(self) -> None:
        with self._lock:
            self._circuit_state.clear()

    def get_circuit_state(self, provider: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._circuit_state.get(provider, {}))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _calculate_delay(self, attempt: int, config: FailoverConfig) -> float:
        delay = min(
            config.retry_delay_base * (2 ** attempt),
            config.retry_delay_max,
        )
        jitter = random.uniform(0, config.retry_jitter)
        return delay + jitter

    def _make_fallback_call(self, provider: str, model: str, params: Dict[str, Any]) -> Any:
        orch = MultiProviderOrchestrator()
        return orch.call_provider(provider, model, params)

    def circuit_status_summary(self) -> str:
        lines = ["Circuit Breaker Status:"]
        with self._lock:
            for provider, state in self._circuit_state.items():
                status = "OPEN" if state.get("open") else "CLOSED"
                failures = state.get("failures", 0)
                lines.append(f"  {provider:20s} {status:8s} ({failures} failures)")
        return "\n".join(lines)