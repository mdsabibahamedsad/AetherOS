"""
Node Health Monitor — monitors node health through heartbeats and probes.

Detects node failures, network partitions, and degraded performance.
Emits health events through the kernel event bus for observability.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class HealthStatus(enum.Enum):
    """Health status levels for cluster nodes."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    SUSPECT = "suspect"
    UNHEALTHY = "unhealthy"
    TIMEOUT = "timeout"


@dataclass
class HealthCheckResult:
    """Result of a health check against a node.

    Attributes:
        node_id: The target node ID
        status: Health status
        latency_ms: Response latency in milliseconds
        error: Error message if check failed
        timestamp: When the check was performed
        details: Additional diagnostic information
    """
    node_id: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class NodeHealthMonitor:
    """Monitors cluster node health via heartbeat tracking and probes.

    Tracks heartbeat timestamps for all nodes and detects failures
    when heartbeats time out. Integrates with the cluster manager
    for failure handling.

    Usage:
        monitor = NodeHealthMonitor(
            event_bus=event_bus,
            heartbeat_timeout=15.0,
            check_interval=5.0,
        )
        monitor.start(on_failure=handle_failure)
        # ... later ...
        monitor.stop()
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        heartbeat_timeout: float = 15.0,
        check_interval: float = 5.0,
    ):
        self._event_bus = event_bus
        self._heartbeat_timeout = heartbeat_timeout
        self._check_interval = check_interval
        self._lock = threading.RLock()

        # Heartbeat tracking
        # node_id -> last heartbeat timestamp
        self._heartbeats: Dict[str, float] = {}
        # node_id -> consecutive missed heartbeats
        self._missed: Dict[str, int] = {}
        # node_id -> current health status
        self._status: Dict[str, HealthStatus] = {}
        # node_id -> node-specific health check function
        self._check_fns: Dict[str, Callable[[], HealthCheckResult]] = {}

        # Running state
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_flag = False
        self._max_missed = 3

        # Failure callbacks
        self._on_failure: Optional[Callable[[str], None]] = None
        self._on_recovery: Optional[Callable[[str], None]] = None
        self._on_degraded: Optional[Callable[[str], HealthCheckResult]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        on_failure: Optional[Callable[[str], None]] = None,
        on_recovery: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Start the health monitor background thread.

        Args:
            on_failure: Callback when a node is declared failed
            on_recovery: Callback when a node recovers
        """
        if self._running:
            return

        self._on_failure = on_failure
        self._on_recovery = on_recovery
        self._running = True
        self._shutdown_flag = False

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="cluster-health-monitor",
        )
        self._monitor_thread.start()

        logger.info(
            "NodeHealthMonitor: started (timeout=%.1fs, interval=%.1fs)",
            self._heartbeat_timeout, self._check_interval,
        )

    def stop(self) -> None:
        """Stop the health monitor."""
        self._shutdown_flag = True
        self._running = False

        logger.info("NodeHealthMonitor: stopped")

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def record_heartbeat(self, node_id: str) -> None:
        """Record a heartbeat from a node.

        Clears the missed count and sets status to healthy.
        """
        now = time.time()
        with self._lock:
            prev_status = self._status.get(node_id)
            self._heartbeats[node_id] = now
            self._missed[node_id] = 0
            self._status[node_id] = HealthStatus.HEALTHY

            # If the node was previously unhealthy, fire recovery callback
            if prev_status in (HealthStatus.UNHEALTHY, HealthStatus.TIMEOUT, HealthStatus.SUSPECT):
                logger.info("NodeHealthMonitor: node %s recovered", node_id[:8])
                if self._on_recovery:
                    try:
                        self._on_recovery(node_id)
                    except Exception as exc:
                        logger.debug("NodeHealthMonitor: recovery callback failed: %s", exc)

                if self._event_bus:
                    self._event_bus.emit_async("cluster.health_recovered", {
                        "node_id": node_id,
                    })

    def get_health_status(self, node_id: str) -> HealthStatus:
        """Get the current health status of a node."""
        with self._lock:
            return self._status.get(node_id, HealthStatus.UNKNOWN)

    def get_all_status(self) -> Dict[str, HealthStatus]:
        """Get the health status of all tracked nodes."""
        with self._lock:
            return dict(self._status)

    def register_check(self, node_id: str,
                       check_fn: Callable[[], HealthCheckResult]) -> None:
        """Register a custom health check function for a node.

        The check_fn will be called periodically to verify node health.
        """
        with self._lock:
            self._check_fns[node_id] = check_fn

    def unregister_check(self, node_id: str) -> None:
        """Remove a custom health check function."""
        with self._lock:
            self._check_fns.pop(node_id, None)

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        """Background monitoring loop — checks all nodes for timeouts."""
        while not self._shutdown_flag:
            try:
                self._check_all()
            except Exception as exc:
                logger.error("NodeHealthMonitor: check error: %s", exc)
            time.sleep(self._check_interval)

    def _check_all(self) -> None:
        """Check all tracked nodes for heartbeats."""
        now = time.time()

        with self._lock:
            # Snapshot current heartbeats
            heartbeats = dict(self._heartbeats)
            check_fns = dict(self._check_fns)

        for node_id, last_heartbeat in heartbeats.items():
            elapsed = now - last_heartbeat

            if elapsed > self._heartbeat_timeout:
                with self._lock:
                    missed = self._missed.get(node_id, 0) + 1
                    self._missed[node_id] = missed

                if missed >= self._max_missed:
                    self._declare_failure(node_id)
                elif missed >= 2:
                    self._mark_suspect(node_id, elapsed)

        # Run custom health checks
        for node_id, check_fn in check_fns.items():
            try:
                result = check_fn()
                if result.status != HealthStatus.HEALTHY:
                    self._handle_check_failure(node_id, result)
            except Exception as exc:
                logger.debug(
                    "NodeHealthMonitor: check for %s failed: %s",
                    node_id[:8], exc,
                )

    def _declare_failure(self, node_id: str) -> None:
        """Declare a node as failed after too many missed heartbeats."""
        with self._lock:
            self._status[node_id] = HealthStatus.TIMEOUT

        logger.warning(
            "NodeHealthMonitor: node %s FAILED (missed %d heartbeats)",
            node_id[:8], self._missed.get(node_id, 0),
        )

        if self._event_bus:
            self._event_bus.emit_async("cluster.health_failed", {
                "node_id": node_id,
                "missed_count": self._missed.get(node_id, 0),
            })

        if self._on_failure:
            try:
                self._on_failure(node_id)
            except Exception as exc:
                logger.error("NodeHealthMonitor: failure callback error: %s", exc)

    def _mark_suspect(self, node_id: str, elapsed: float) -> None:
        """Mark a node as suspect (intermittent connectivity)."""
        with self._lock:
            self._status[node_id] = HealthStatus.SUSPECT

        logger.debug(
            "NodeHealthMonitor: node %s suspect (%.1fs since last heartbeat)",
            node_id[:8], elapsed,
        )

        if self._event_bus:
            self._event_bus.emit_async("cluster.health_suspect", {
                "node_id": node_id,
                "elapsed_seconds": elapsed,
            })

    def _handle_check_failure(self, node_id: str,
                              result: HealthCheckResult) -> None:
        """Handle a failed custom health check."""
        with self._lock:
            prev = self._status.get(node_id)
            self._status[node_id] = result.status

        if prev in (HealthStatus.HEALTHY, None):
            logger.warning(
                "NodeHealthMonitor: node %s health check failed: %s",
                node_id[:8], result.error or "unknown",
            )

            if self._event_bus:
                self._event_bus.emit_async("cluster.health_check_failed", {
                    "node_id": node_id,
                    "error": result.error,
                    "latency_ms": result.latency_ms,
                })

            if result.status == HealthStatus.UNHEALTHY and self._on_failure:
                try:
                    self._on_failure(node_id)
                except Exception as exc:
                    logger.error(
                        "NodeHealthMonitor: failure callback error: %s", exc,
                    )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return health monitor statistics."""
        with self._lock:
            status_counts: Dict[str, int] = {}
            for s in self._status.values():
                status_counts[s.value] = status_counts.get(s.value, 0) + 1

            return {
                "running": self._running,
                "tracked_nodes": len(self._heartbeats),
                "custom_checks": len(self._check_fns),
                "heartbeat_timeout": self._heartbeat_timeout,
                "status_counts": status_counts,
                "by_status": {
                    node_id: s.value
                    for node_id, s in self._status.items()
                },
            }

    def reset_node(self, node_id: str) -> None:
        """Reset health tracking for a node (e.g., after reconnection)."""
        with self._lock:
            self._missed[node_id] = 0
            self._status[node_id] = HealthStatus.UNKNOWN
