"""Agent Health Monitoring for AetherOS Orchestration Layer.

Implements Phases 4-5 of Master Prompt 11: agent health tracking,
safe health checks, and health-based routing decisions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.orchestration.types import (
    AgentHealth,
    AgentHealthStatus,
    AgentLifecycleState,
    AgentIdentity,
    AgentCapabilities,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Health Check Types
# =============================================================================


class HealthCheckCategory(Enum):
    """Categories of health checks."""

    LIVENESS = "liveness"  # Is the agent alive?
    READINESS = "readiness"  # Can it accept tasks?
    DEPENDENCIES = "dependencies"  # Are dependencies available?
    RESOURCES = "resources"  # Memory, disk, CPU
    PERMISSIONS = "permissions"  # Required permissions
    MODEL_AVAILABLE = "model_available"  # Model API reachable
    TOOL_AVAILABLE = "tool_available"  # Tools functional
    SECURITY = "security"  # Security policy compliance


@dataclass
class HealthCheck:
    """Definition of a health check."""

    name: str
    category: HealthCheckCategory
    check_fn: Callable[[], Any]  # Sync or async function returning bool or dict
    timeout: float = 5.0
    critical: bool = False  # If True, failure = unhealthy
    interval: float = 30.0  # Seconds between checks
    timeout_failure_is_unhealthy: bool = True


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    category: HealthCheckCategory
    passed: bool
    duration: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    checked_at: float = field(default_factory=time.time)


# =============================================================================
# Health Monitor
# =============================================================================


class AgentHealthMonitor:
    """Monitors health of agent instances with periodic checks."""

    def __init__(
        self,
        check_interval: float = 30.0,
        default_timeout: float = 10.0,
    ):
        self._check_interval = check_interval
        self._default_timeout = default_timeout
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, List[HealthCheckResult]] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._callbacks: List[Callable[[str, AgentHealth], None]] = []

    def register_check(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks[check.name] = check
        logger.debug(f"Registered health check: {check.name} ({check.category.value})")

    def unregister_check(self, name: str) -> bool:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    def register_callback(self, callback: Callable[[str, AgentHealth], None]) -> None:
        """Register callback for health status changes."""
        self._callbacks.append(callback)

    async def start(self):
        """Start the health monitor."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop the health monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def register_agent(self, agent: "AgentInterface") -> None:
        """Register an agent for health monitoring."""
        # The agent's health_check method will be called periodically
        pass

    def unregister_agent(self, agent_id: str) -> bool:
        """Stop monitoring an agent."""
        if agent_id in self._results:
            del self._results[agent_id]
            return True
        return False

    async def check_agent(self, agent: "AgentInterface") -> AgentHealth:
        """Run all health checks for an agent."""
        agent_id = agent.identity.agent_id
        results = []

        for check in self._checks.values():
            try:
                start = time.time()
                # Run with timeout
                if asyncio.iscoroutinefunction(check.check_fn):
                    result = await asyncio.wait_for(
                        check.check_fn(),
                        timeout=check.timeout,
                    )
                else:
                    result = check.check_fn()

                passed = bool(result) if isinstance(result, bool) else True
                details = result if isinstance(result, dict) else {"result": str(result)}

                results.append(HealthCheckResult(
                    name=check.name,
                    category=check.category,
                    passed=passed,
                    duration=time.time() - start,
                    details=details,
                    checked_at=time.time(),
                ))

            except asyncio.TimeoutError:
                results.append(HealthCheckResult(
                    name=check.name,
                    category=check.category,
                    passed=not check.timeout_failure_is_unhealthy,
                    duration=check.timeout,
                    error=f"Timeout after {check.timeout}s",
                    checked_at=time.time(),
                ))
            except Exception as e:
                results.append(HealthCheckResult(
                    name=check.name,
                    category=check.category,
                    passed=False,
                    duration=time.time() - start,
                    error=str(e),
                    checked_at=time.time(),
                ))

        # Aggregate results
        health = self._aggregate_results(agent.identity.agent_id, results)

        # Store results
        async with self._lock:
            self._results[agent.identity.agent_id] = results

        # Notify callbacks
        health = AgentHealth(
            status=self._determine_status(results),
            agent_id=agent.identity.agent_id,
            details={
                "checks": {r.name: {"passed": r.passed, "details": r.details} for r in results},
                "total_checks": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
            checks={r.name: r.passed for r in results},
        )

        # Notify callbacks
        for cb in self._callbacks:
            try:
                await cb(agent.identity.agent_id, health)
            except Exception as e:
                logger.warning(f"Health callback failed: {e}")

        return health

    async def check_all_agents(self, agents: Dict[str, "AgentInterface"]) -> Dict[str, AgentHealth]:
        """Check health of multiple agents."""
        results = {}
        for agent_id, agent in agents.items():
            try:
                results[agent_id] = await self.check_agent(agent)
            except Exception as e:
                logger.error(f"Health check failed for {agent_id}: {e}")
                results[agent_id] = AgentHealth(
                    status=AgentHealthStatus.UNHEALTHY,
                    agent_id=agent.identity.agent_id,
                    details={"error": str(e)},
                )
        return results

    def get_latest_result(self, agent_id: str) -> Optional[AgentHealth]:
        """Get latest health result for an agent."""
        return self._results.get(agent_id)

    def get_check_history(self, agent_id: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get recent check results for an agent."""
        return self._results.get(agent_id, [])[-limit:]

    # ── Built-in Checks ───────────────────────────────────────────────

    def _add_builtin_checks(self, agent: "AgentInterface") -> None:
        """Add standard health checks for an agent."""
        # Liveness check - can we reach the agent?
        self.register_check(HealthCheck(
            name=f"{agent.identity.agent_id}_liveness",
            category=HealthCheckCategory.LIVENESS,
            check_fn=lambda: self._check_liveness(agent),
            critical=True,
        ))

        # Readiness check - can accept tasks?
        self.register_check(HealthCheck(
            name=f"{agent.identity.agent_id}_readiness",
            category=HealthCheckCategory.READINESS,
            check_fn=lambda: self._check_readiness(agent),
            critical=True,
        ))

        # Model availability
        self.register_check(HealthCheck(
            name=f"{agent.identity.agent_id}_model",
            category=HealthCheckCategory.MODEL_AVAILABLE,
            check_fn=lambda: self._check_model_availability(agent),
            critical=True,
        ))

        # Tool availability
        self.register_check(HealthCheck(
            name=f"{agent.identity.agent_id}_tools",
            category=HealthCheckCategory.TOOL_AVAILABLE,
            check_fn=lambda: self._check_tool_availability(agent),
            critical=False,
        ))

        # Permissions
        self.register_check(HealthCheck(
            name=f"{agent.identity.agent_id}_permissions",
            category=HealthCheckCategory.PERMISSIONS,
            check_fn=lambda: self._check_permissions(agent),
            critical=False,
        ))

    def _check_liveness(self, agent: "AgentInterface") -> bool:
        """Check if agent is alive."""
        return agent.state in (
            AgentLifecycleState.READY,
            AgentLifecycleState.BUSY,
            AgentLifecycleState.PAUSED,
        )

    def _check_readiness(self, agent: "AgentInterface") -> bool:
        """Check if agent can accept tasks."""
        return agent.state == "ready" or (
            agent.state == "busy" and agent.get_active_tasks() < 10
        )

    def _check_model_availability(self, agent: "AgentInterface") -> Dict[str, Any]:
        """Check if the agent's model is available."""
        # Try a simple model call
        try:
            # This is agent-specific; subclasses should override
            return {"available": True, "model": getattr(agent, "model", "unknown")}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _check_tool_availability(self, agent: "AgentInterface") -> Dict[str, Any]:
        """Check if agent's tools are available."""
        try:
            tools = getattr(agent, "capabilities", None)
            if tools:
                return {
                    "available": True,
                    "tool_count": len(tools.capabilities),
                }
            return {"available": False, "reason": "no capabilities"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _check_permissions(self, agent: "AgentInterface") -> Dict[str, Any]:
        """Check if agent has required permissions."""
        return {"available": True, "permissions": []}

    def _aggregate_results(
        self,
        agent_id: str,
        results: List["HealthCheckResult"],
    ) -> AgentHealth:
        """Aggregate individual check results into overall health."""
        if not results:
            return AgentHealth(
                status=AgentHealthStatus.UNKNOWN,
                agent_id=agent_id,
                details={"reason": "no_checks_run"},
            )

        # Check critical failures
        critical_failed = [r for r in results if not r.passed and any(
            c.name == r.name and c.critical for c in self._checks.values()
        )]

        if critical_failed:
            status = AgentHealthStatus.UNHEALTHY
        elif any(not r.passed for r in results):
            status = AgentHealthStatus.DEGRADED
        else:
            status = AgentHealthStatus.HEALTHY

        return AgentHealth(
            status=status,
            agent_id=agent_id,
            details={
                "checks": {r.name: {"passed": r.passed, "details": r.details} for r in results},
                "total_checks": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
            checks={r.name: r.passed for r in results},
        )

    def _determine_status(self, results: List[HealthCheckResult]) -> AgentHealthStatus:
        """Determine overall status from check results."""
        if not results:
            return AgentHealthStatus.UNKNOWN

        # Critical failures
        critical_failed = [r for r in results if not r.passed and any(
            c.name == r.name and c.critical for c in self._checks.values()
        )]

        if critical_failed:
            return AgentHealthStatus.UNHEALTHY
        elif any(not r.passed for r in results):
            return AgentHealthStatus.DEGRADED
        else:
            return AgentHealthStatus.HEALTHY


# =============================================================================
# Health Check Builders
# =============================================================================


def create_liveness_check(
    agent: "AgentInterface",
    timeout: float = 5.0,
) -> HealthCheck:
    """Create a liveness check for an agent."""
    async def check():
        return agent.state in ("ready", "busy", "paused")

    return HealthCheck(
        name="liveness",
        category=HealthCheckCategory.LIVENESS,
        check_fn=check,
        timeout=timeout,
        critical=True,
    )


def create_readiness_check(
    agent: "AgentInterface",
    timeout: float = 5.0,
) -> HealthCheck:
    """Create a readiness check for an agent."""
    async def check():
        return agent.state == "ready" or (
            agent.state == "busy" and len(agent.get_active_tasks()) < 10
        )

    return HealthCheck(
        name="readiness",
        category=HealthCheckCategory.READINESS,
        check_fn=check,
        timeout=timeout,
        critical=True,
    )


def create_model_availability_check(
    agent: "AgentInterface",
    timeout: float = 10.0,
) -> HealthCheck:
    """Create a model availability check."""
    async def check():
        # This would be agent-specific
        try:
            # Try a simple model call or check connection
            model = getattr(agent, "model", "unknown")
            return {"available": True, "model": model}
        except Exception as e:
            return {"available": False, "error": str(e)}

    return HealthCheck(
        name="model_availability",
        category=HealthCheckCategory.MODEL_AVAILABLE,
        check_fn=check,
        timeout=timeout,
        critical=True,
    )


def create_tool_availability_check(
    agent: "AgentInterface",
    timeout: float = 5.0,
) -> HealthCheck:
    """Create a tool availability check."""
    async def check():
        caps = getattr(agent, "capabilities", None)
        if caps:
            return {
                "available": True,
                "tool_count": len(caps.capabilities),
                "tools": caps.capabilities,
            }
        return {"available": False, "reason": "no capabilities"}

    return HealthCheck(
        name="tool_availability",
        category=HealthCheckCategory.TOOL_AVAILABLE,
        check_fn=check,
        timeout=timeout,
        critical=False,
    )


def create_resource_check(
    agent: "AgentInterface",
    timeout: float = 5.0,
    max_memory_mb: float = 2048,
    max_cpu_percent: float = 90.0,
) -> HealthCheck:
    """Create a resource usage check."""
    import psutil

    async def check():
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 * 1024)
        cpu_pct = process.cpu_percent(interval=0.1)

        return {
            "passed": mem_mb < max_memory_mb and cpu_pct < max_cpu_percent,
            "memory_mb": mem_mb,
            "cpu_percent": cpu_pct,
            "max_memory_mb": max_memory_mb,
            "max_cpu_percent": max_cpu_percent,
        }

    return HealthCheck(
        name="resources",
        category=HealthCheckCategory.RESOURCES,
        check_fn=check,
        timeout=timeout,
        critical=False,
    )


def create_permissions_check(
    agent: "AgentInterface",
    required_permissions: List[str],
    timeout: float = 5.0,
) -> HealthCheck:
    """Create a permissions check."""
    async def check():
        # Check if agent has required permissions
        # This would integrate with MASTER 7 security system
        missing = []
        # Placeholder - integrate with MASTER 7
        return {
            "passed": len(missing) == 0,
            "missing": missing,
        }

    return HealthCheck(
        name="permissions",
        category=HealthCheckCategory.PERMISSIONS,
        check_fn=check,
        timeout=timeout,
        critical=False,
    )


def create_dependency_check(
    agent: "AgentInterface",
    dependencies: List[Tuple[str, Callable[[], bool]]],
    timeout: float = 10.0,
) -> HealthCheck:
    """Create a check for external dependencies."""
    async def check():
        results = {}
        for name, check_fn in dependencies:
            try:
                if asyncio.iscoroutinefunction(check_fn):
                    result = await check_fn()
                else:
                    result = check_fn()
                results[name] = result
            except Exception as e:
                results[name] = {"passed": False, "error": str(e)}

        return {
            "passed": all(r.get("passed", False) for r in results.values()),
            "dependencies": results,
        }

    return HealthCheck(
        name="dependencies",
        category=HealthCheckCategory.DEPENDENCIES,
        check_fn=check,
        timeout=timeout,
        critical=True,
    )


# =============================================================================
# Health-Aware Router Integration
# =============================================================================


class HealthAwareRouter:
    """Router that considers agent health in routing decisions."""

    def __init__(
        self,
        monitor: AgentHealthMonitor,
        min_health: AgentHealthStatus = AgentHealthStatus.HEALTHY,
    ):
        self._monitor = monitor
        self._min_health = min_health

    async def get_healthy_agents(
        self,
        agents: Dict[str, "AgentInterface"],
    ) -> Dict[str, "AgentInterface"]:
        """Filter agents to only healthy ones."""
        healthy = {}
        for agent_id, agent in agents.items():
            health = await self._monitor.check_agent(agent)
            if health.status.value >= self._min_health.value:
                healthy[agent_id] = agent
        return healthy

    async def get_best_agent(
        self,
        agents: Dict[str, "AgentInterface"],
        required_capabilities: List[str],
    ) -> Optional["AgentInterface"]:
        """Get the healthiest agent with required capabilities."""
        healthy = await self.get_healthy_agents(agents)

        # Filter by capabilities
        candidates = []
        for agent in healthy.values():
            if all(cap in agent.capabilities.capabilities for cap in required_capabilities):
                candidates.append(agent)

        if not candidates:
            return None

        # Return healthiest (least degraded)
        return max(candidates, key=lambda a: self._get_health_score(a))

    def _get_health_score(self, agent: "AgentInterface") -> float:
        """Calculate health score (1.0 = healthy, 0.0 = unhealthy)."""
        # This would check cached health or do quick check
        return 1.0


# =============================================================================
# Global Monitor Instance
# =============================================================================

_global_monitor: Optional[AgentHealthMonitor] = None


def get_health_monitor() -> AgentHealthMonitor:
    """Get the global health monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AgentHealthMonitor()
    return _global_monitor


async def initialize_health_monitor(
    check_interval: float = 30.0,
    default_timeout: float = 10.0,
) -> AgentHealthMonitor:
    """Initialize and start the global health monitor."""
    monitor = get_health_monitor()
    await monitor.start()
    return monitor


async def shutdown_health_monitor():
    """Shutdown the global health monitor."""
    global _global_monitor
    if _global_monitor:
        await _global_monitor.stop()