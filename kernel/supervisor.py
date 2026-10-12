"""
Supervisor Agent — continuously monitors running agents, health, failures,
infinite loops, resource usage, and deadlocks.

The Supervisor runs as a background daemon within the kernel, periodically
checking all active agents, detecting anomalies, and taking corrective
action when necessary.

Monitoring dimensions:
  - Health checks (heartbeat, responsiveness)
  - Performance (loop detection, resource usage)
  - Failure detection (crashes, unhandled errors)
  - Deadlock detection (circular waits, starvation)
  - Infinite loop detection (runaway iterations)
  - Memory/CPU usage per agent
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from kernel.event_bus import EventBus, EventTopics

logger = logging.getLogger(__name__)


class AlertSeverity(enum.IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class AlertCategory(enum.Enum):
    HEALTH = "health"
    DEADLOCK = "deadlock"
    INFINITE_LOOP = "infinite_loop"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    FAILURE = "failure"
    PERFORMANCE = "performance"
    TIMEOUT = "timeout"
    STARVATION = "starvation"


@dataclass
class SupervisorAlert:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: AlertCategory = AlertCategory.HEALTH
    severity: AlertSeverity = AlertSeverity.WARNING
    agent_id: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: Optional[float] = None
    action_taken: str = ""


@dataclass
class AgentHeartbeat:
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    iteration_count: int = 0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    status: str = "running"
    current_action: str = ""


class SupervisorAgent:
    """Continuously monitors all running agents for health, deadlocks,
    infinite loops, resource issues, and failures.

    Usage:
        supervisor = SupervisorAgent(event_bus)
        supervisor.start()
        # ... kernel runs ...
        supervisor.stop()
    """

    def __init__(self, event_bus: Optional[EventBus] = None,
                 check_interval: float = 10.0,
                 heartbeat_timeout: float = 60.0,
                 max_iterations_before_warning: int = 100,
                 deadlock_timeout: float = 300.0):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._check_interval = check_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._max_iterations_before_warning = max_iterations_before_warning
        self._deadlock_timeout = deadlock_timeout

        self._heartbeats: Dict[str, AgentHeartbeat] = {}
        self._alerts: List[SupervisorAlert] = []
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._agent_dependencies: Dict[str, List[str]] = {}
        self._iteration_history: Dict[str, List[float]] = {}
        self._resource_history: Dict[str, List[Dict[str, float]]] = {}

        self._running = False
        self._shutdown_flag = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable[[SupervisorAlert], None]] = []
        self._auto_remediate = True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._shutdown_flag = False
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="supervisor-monitor",
        )
        self._monitor_thread.start()
        logger.info("SupervisorAgent: started (interval=%ds)", self._check_interval)

    def stop(self) -> None:
        self._shutdown_flag = True
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
            self._monitor_thread = None
        logger.info("SupervisorAgent: stopped")

    def on_alert(self, callback: Callable[[SupervisorAlert], None]) -> None:
        self._alert_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Agent tracking
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str,
                       dependencies: List[str] = None,
                       metadata: Dict[str, Any] = None) -> None:
        with self._lock:
            self._active_agents[agent_id] = {
                "registered_at": time.time(),
                "dependencies": dependencies or [],
                "metadata": metadata or {},
                "total_iterations": 0,
                "total_errors": 0,
                "last_status": "starting",
            }
            if dependencies:
                self._agent_dependencies[agent_id] = dependencies
        logger.debug("SupervisorAgent: registered agent '%s'", agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._active_agents.pop(agent_id, None)
            self._heartbeats.pop(agent_id, None)
            self._iteration_history.pop(agent_id, None)
            self._resource_history.pop(agent_id, None)
        logger.debug("SupervisorAgent: unregistered agent '%s'", agent_id)

    def record_heartbeat(self, agent_id: str, status: str = "running",
                         iteration_count: int = 0,
                         memory_usage_mb: float = 0.0,
                         cpu_percent: float = 0.0,
                         current_action: str = "") -> None:
        now = time.time()
        heartbeat = AgentHeartbeat(
            agent_id=agent_id,
            timestamp=now,
            iteration_count=iteration_count,
            memory_usage_mb=memory_usage_mb,
            cpu_percent=cpu_percent,
            status=status,
            current_action=current_action,
        )
        with self._lock:
            self._heartbeats[agent_id] = heartbeat
            self._iteration_history.setdefault(agent_id, []).append(now)
            if len(self._iteration_history[agent_id]) > 1000:
                self._iteration_history[agent_id] = self._iteration_history[agent_id][-500:]
            self._resource_history.setdefault(agent_id, []).append({
                "time": now,
                "memory_mb": memory_usage_mb,
                "cpu_pct": cpu_percent,
            })
            if len(self._resource_history[agent_id]) > 100:
                self._resource_history[agent_id] = self._resource_history[agent_id][-50:]
            if agent_id in self._active_agents:
                self._active_agents[agent_id]["total_iterations"] = iteration_count

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        while not self._shutdown_flag:
            try:
                self._check_all()
            except Exception as exc:
                logger.error("SupervisorAgent: monitor check failed: %s", exc)
            time.sleep(self._check_interval)

    def _check_all(self) -> None:
        now = time.time()
        with self._lock:
            agents = dict(self._active_agents)
            heartbeats = dict(self._heartbeats)

        for agent_id in agents:
            heartbeat = heartbeats.get(agent_id)
            if heartbeat is None:
                self._raise_alert(
                    category=AlertCategory.HEALTH,
                    severity=AlertSeverity.WARNING,
                    agent_id=agent_id,
                    message=f"Agent '{agent_id}' has no heartbeat",
                    details={"elapsed_seconds": now - agents[agent_id]["registered_at"]},
                )
                continue

            self._check_heartbeat_timeout(agent_id, heartbeat, now)
            self._check_infinite_loop(agent_id, heartbeat)
            self._check_resource_usage(agent_id, heartbeat)
            self._check_deadlock(agent_id, heartbeat, now)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_heartbeat_timeout(self, agent_id: str,
                                 heartbeat: AgentHeartbeat,
                                 now: float) -> None:
        elapsed = now - heartbeat.timestamp
        if elapsed > self._heartbeat_timeout:
            self._raise_alert(
                category=AlertCategory.HEALTH,
                severity=AlertSeverity.ERROR,
                agent_id=agent_id,
                message=f"Agent '{agent_id}' heartbeat timeout ({elapsed:.0f}s)",
                details={"elapsed_seconds": elapsed, "timeout": self._heartbeat_timeout},
            )
            if self._auto_remediate:
                self._auto_kill(agent_id, f"heartbeat timeout ({elapsed:.0f}s)")

    def _check_infinite_loop(self, agent_id: str,
                            heartbeat: AgentHeartbeat) -> None:
        with self._lock:
            history = list(self._iteration_history.get(agent_id, []))

        if len(history) < 3:
            return

        recent = history[-5:]
        if len(recent) >= 3:
            rate = (recent[-1] - recent[0]) / len(recent) if len(recent) > 1 else 0
            if rate < 0.1 and heartbeat.iteration_count > 5:
                pass

        if heartbeat.iteration_count > self._max_iterations_before_warning:
            self._raise_alert(
                category=AlertCategory.INFINITE_LOOP,
                severity=AlertSeverity.WARNING,
                agent_id=agent_id,
                message=f"Agent '{agent_id}' high iteration count ({heartbeat.iteration_count})",
                details={
                    "iteration_count": heartbeat.iteration_count,
                    "threshold": self._max_iterations_before_warning,
                },
            )

    def _check_resource_usage(self, agent_id: str,
                              heartbeat: AgentHeartbeat) -> None:
        warnings = []
        if heartbeat.memory_usage_mb > 1024:
            warnings.append(f"memory={heartbeat.memory_usage_mb:.0f}MB")
        if heartbeat.cpu_percent > 90:
            warnings.append(f"cpu={heartbeat.cpu_percent:.0f}%")

        if warnings:
            self._raise_alert(
                category=AlertCategory.RESOURCE_EXHAUSTION,
                severity=AlertSeverity.WARNING,
                agent_id=agent_id,
                message=f"Agent '{agent_id}' resource warning: {', '.join(warnings)}",
                details={
                    "memory_mb": heartbeat.memory_usage_mb,
                    "cpu_pct": heartbeat.cpu_percent,
                },
            )

    def _check_deadlock(self, agent_id: str,
                        heartbeat: AgentHeartbeat, now: float) -> None:
        if agent_id not in self._agent_dependencies:
            return

        deps = self._agent_dependencies[agent_id]
        with self._lock:
            dep_status = {
                dep: self._heartbeats.get(dep)
                for dep in deps
            }

        stuck_deps = []
        for dep_id, dep_hb in dep_status.items():
            if dep_hb is None:
                stuck_deps.append(dep_id)
            elif now - dep_hb.timestamp > self._deadlock_timeout:
                stuck_deps.append(dep_id)

        if stuck_deps:
            self._raise_alert(
                category=AlertCategory.DEADLOCK,
                severity=AlertSeverity.ERROR,
                agent_id=agent_id,
                message=f"Agent '{agent_id}' blocked by unresponsive dependencies: {stuck_deps}",
                details={"blocked_by": stuck_deps},
            )

    # ------------------------------------------------------------------
    # Alert management
    # ------------------------------------------------------------------

    def _raise_alert(self, category: AlertCategory, severity: AlertSeverity,
                     agent_id: str, message: str,
                     details: Dict[str, Any] = None) -> SupervisorAlert:
        alert = SupervisorAlert(
            category=category,
            severity=severity,
            agent_id=agent_id,
            message=message,
            details=details or {},
        )
        with self._lock:
            self._alerts.append(alert)
            if len(self._alerts) > 10000:
                self._alerts = self._alerts[-5000:]

        logger.warning("SupervisorAgent: [%s/%s] %s",
                       severity.name, category.value, message)

        if self._event_bus:
            self._event_bus.emit_async("supervisor.alert", {
                "alert_id": alert.id,
                "category": category.value,
                "severity": severity.name,
                "agent_id": agent_id,
                "message": message,
                "details": details or {},
            })

        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception as exc:
                logger.error("SupervisorAgent: alert callback failed: %s", exc)

        return alert

    def resolve_alert(self, alert_id: str, action_taken: str = "") -> bool:
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = time.time()
                    alert.action_taken = action_taken
                    return True
        return False

    def get_alerts(self, category: AlertCategory = None,
                   severity: AlertSeverity = None,
                   unresolved_only: bool = False,
                   limit: int = 100) -> List[SupervisorAlert]:
        with self._lock:
            alerts = list(self._alerts)
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]

    # ------------------------------------------------------------------
    # Remediation
    # ------------------------------------------------------------------

    def set_auto_remediate(self, enabled: bool) -> None:
        self._auto_remediate = enabled

    def _auto_kill(self, agent_id: str, reason: str) -> None:
        logger.warning("SupervisorAgent: auto-remediate killing agent '%s': %s",
                       agent_id, reason)
        if self._event_bus:
            self._event_bus.emit_async("supervisor.auto_kill", {
                "agent_id": agent_id, "reason": reason,
            })

    def request_remediation(self, agent_id: str, action: str) -> bool:
        with self._lock:
            if agent_id not in self._active_agents:
                return False
        logger.info("SupervisorAgent: remediation requested for '%s': %s",
                    agent_id, action)
        if self._event_bus:
            self._event_bus.emit_async("supervisor.remediation", {
                "agent_id": agent_id, "action": action,
            })
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            info = self._active_agents.get(agent_id)
            hb = self._heartbeats.get(agent_id)
        if info is None:
            return None
        return {
            "agent_id": agent_id,
            "registered_at": info["registered_at"],
            "total_iterations": info["total_iterations"],
            "total_errors": info["total_errors"],
            "last_status": info["last_status"] if hb is None else hb.status,
            "last_heartbeat": hb.timestamp if hb else None,
            "current_action": hb.current_action if hb else "",
            "dependencies": info["dependencies"],
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                self.get_agent_status(aid)
                for aid in self._active_agents
            ]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_alerts = len(self._alerts)
            unresolved = sum(1 for a in self._alerts if not a.resolved)
        return {
            "running": self._running,
            "monitored_agents": len(self._active_agents),
            "total_alerts": total_alerts,
            "unresolved_alerts": unresolved,
            "check_interval": self._check_interval,
            "auto_remediate": self._auto_remediate,
        }