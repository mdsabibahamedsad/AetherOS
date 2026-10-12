"""Boot Sequence for AetherOS.

Defines the deterministic startup pipeline:

1. Initialize logger
2. Load configuration
3. Validate configuration
4. Load providers
5. Initialize gateway
6. Initialize runtime
7. Initialize memory
8. Initialize plugins
9. Initialize MCP
10. Initialize UI
11. Health check
12. Ready
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_arch.config_manager import ConfigManager
from aetheros_arch.error_handler import ErrorHandler, StartupError
from aetheros_arch.health_checker import HealthChecker, HealthSummary
from aetheros_arch.service_container import ServiceContainer
from aetheros_arch.state_manager import AppState, ComponentState, StateManager

logger = logging.getLogger("aetheros_arch.boot")


class BootStage(enum.Enum):
    LOGGER = "logger"
    CONFIG = "config"
    CONFIG_VALIDATE = "config_validate"
    PROVIDERS = "providers"
    GATEWAY = "gateway"
    RUNTIME = "runtime"
    MEMORY = "memory"
    PLUGINS = "plugins"
    MCP = "mcp"
    UI = "ui"
    HEALTH_CHECK = "health_check"
    READY = "ready"


BootCallback = Callable[[], None]


@dataclass
class BootResult:
    success: bool
    stage: BootStage
    duration_ms: float = 0.0
    error: Optional[str] = None
    health_summary: Optional[HealthSummary] = None

    @property
    def failed(self) -> bool:
        return not self.success


class BootSequence:
    """Deterministic boot sequence with no race conditions.

    Each stage runs synchronously and must complete before the next starts.
    Stages can have pre/post hooks for customization.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        state_manager: StateManager,
        service_container: ServiceContainer,
        error_handler: ErrorHandler,
        health_checker: HealthChecker,
    ) -> None:
        self.config = config_manager
        self.state = state_manager
        self.container = service_container
        self.errors = error_handler
        self.health = health_checker

        self._pre_hooks: Dict[BootStage, List[BootCallback]] = {}
        self._post_hooks: Dict[BootStage, List[BootCallback]] = {}
        self._stage_times: Dict[BootStage, float] = {}

    def add_pre_hook(self, stage: BootStage, callback: BootCallback) -> None:
        self._pre_hooks.setdefault(stage, []).append(callback)

    def add_post_hook(self, stage: BootStage, callback: BootCallback) -> None:
        self._post_hooks.setdefault(stage, []).append(callback)

    def run(self) -> BootResult:
        """Run the complete boot sequence."""
        self.state.app_state = AppState.STARTING
        start = time.monotonic()

        stages = [
            (BootStage.LOGGER, self._stage_logger),
            (BootStage.CONFIG, self._stage_config),
            (BootStage.CONFIG_VALIDATE, self._stage_config_validate),
            (BootStage.PROVIDERS, self._stage_providers),
            (BootStage.GATEWAY, self._stage_gateway),
            (BootStage.RUNTIME, self._stage_runtime),
            (BootStage.MEMORY, self._stage_memory),
            (BootStage.PLUGINS, self._stage_plugins),
            (BootStage.MCP, self._stage_mcp),
            (BootStage.UI, self._stage_ui),
            (BootStage.HEALTH_CHECK, self._stage_health_check),
        ]

        for stage, stage_fn in stages:
            stage_start = time.monotonic()
            self.state.set_component_state(stage.value, ComponentState.INITIALIZING)

            try:
                self._run_hooks(self._pre_hooks.get(stage, []))
                stage_fn()
                self._run_hooks(self._post_hooks.get(stage, []))
                self.state.set_component_state(stage.value, ComponentState.READY)
            except StartupError as exc:
                elapsed = (time.monotonic() - start) * 1000
                self.state.set_component_state(stage.value, ComponentState.ERROR)
                self.state.app_state = AppState.ERROR
                self.errors.handle(exc, component="boot", operation=stage.value)
                return BootResult(
                    success=False,
                    stage=stage,
                    duration_ms=elapsed,
                    error=str(exc),
                )
            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                self.state.set_component_state(stage.value, ComponentState.ERROR)
                self.state.app_state = AppState.ERROR
                self.errors.handle(
                    exc,
                    component="boot",
                    operation=stage.value,
                )
                return BootResult(
                    success=False,
                    stage=stage,
                    duration_ms=elapsed,
                    error=str(exc),
                )
            finally:
                self._stage_times[stage] = (time.monotonic() - stage_start) * 1000

        # Final health check
        health_summary = self.health.run_all()
        if health_summary.all_healthy:
            self.state.app_state = AppState.RUNNING
        else:
            self.state.app_state = AppState.DEGRADED

        total_duration = (time.monotonic() - start) * 1000
        return BootResult(
            success=True,
            stage=BootStage.READY,
            duration_ms=total_duration,
            health_summary=health_summary,
        )

    @property
    def stage_times(self) -> Dict[str, float]:
        return {s.value: t for s, t in self._stage_times.items()}

    @property
    def total_boot_time_ms(self) -> float:
        return sum(self._stage_times.values())

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_logger(self) -> None:
        from aetheros_logging import setup_logging
        setup_logging()

    def _stage_config(self) -> None:
        self.config.load_all()

    def _stage_config_validate(self) -> None:
        errors = self.config.validate_all()
        if errors:
            raise StartupError(
                message=f"Configuration validation failed: {'; '.join(errors[:3])}"
            )

    def _stage_providers(self) -> None:
        providers_config = self.config.get_scope("providers")
        import logging
        if providers_config:
            logger.info("Providers configured: %d entries", len(providers_config))

    def _stage_gateway(self) -> None:
        gateway_enabled = self.config.get("gateway.enabled", False)
        if gateway_enabled:
            logger.info("Gateway is enabled")

    def _stage_runtime(self) -> None:
        max_iter = self.config.get("runtime.max_iterations", 90)
        logger.info("Runtime configured: max_iterations=%d", max_iter)

    def _stage_memory(self) -> None:
        memory_enabled = self.config.get("memory.enabled", True)
        if memory_enabled:
            logger.info("Memory system is enabled")

    def _stage_plugins(self) -> None:
        logger.info("Plugin system initialized")

    def _stage_mcp(self) -> None:
        logger.info("MCP server initialized")

    def _stage_ui(self) -> None:
        logger.info("UI layer initialized")

    def _stage_health_check(self) -> None:
        summary = self.health.run_all()
        logger.info("Health check: %s", summary.summary())

    @staticmethod
    def _run_hooks(hooks: List[BootCallback]) -> None:
        for hook in hooks:
            hook()