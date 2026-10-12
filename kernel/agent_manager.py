"""
Multi-Agent Manager — enhanced lifecycle management for all agent types.

Provides comprehensive agent lifecycle management:
  - Register/Unregister agents
  - Start/Stop/Pause/Resume/Restart agents
  - Health checking per agent
  - Version management
  - Capability discovery
  - Permission management
  - Inter-agent communication setup
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from agents.specialized_agents import (
    SPECIALIZED_AGENT_DEFINITIONS, create_specialized_agent,
    list_agent_types, list_agent_capabilities,
)

logger = logging.getLogger(__name__)


class AgentLifecycleStatus(enum.Enum):
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class AgentHealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentMetadata:
    id: str = ""
    name: str = ""
    type: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    priority: int = 50
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    supported_models: List[str] = field(default_factory=list)
    cost_estimate_per_run: float = 0.0
    average_latency_ms: float = 0.0
    max_concurrent_tasks: int = 1
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentInstance:
    metadata: AgentMetadata = field(default_factory=AgentMetadata)
    status: AgentLifecycleStatus = AgentLifecycleStatus.REGISTERED
    health: AgentHealthStatus = AgentHealthStatus.UNKNOWN
    instance: Any = None
    thread: Optional[threading.Thread] = None
    started_at: Optional[float] = None
    last_heartbeat: Optional[float] = None
    current_task_id: str = ""
    total_tasks_completed: int = 0
    total_errors: int = 0
    error: str = ""
    lock: Any = field(default_factory=threading.RLock)


class AgentManager:
    """Enhanced multi-agent lifecycle manager.

    Manages all agent types with full lifecycle support including
    start, stop, pause, resume, restart, health checks, and
    capability-based discovery.

    Usage:
        mgr = AgentManager()
        mgr.register_agent("research-1", "research", {"model": "gpt-4"})
        mgr.start_agent("research-1")
        mgr.pause_agent("research-1")
        mgr.resume_agent("research-1")
        mgr.stop_agent("research-1")
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._agents: Dict[str, AgentInstance] = {}
        self._agent_types: Dict[str, List[str]] = {}
        self._capability_index: Dict[str, Set[str]] = {}
        self._global_callbacks: Dict[str, List[Callable]] = {}
        self._started = False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, agent_type: str,
                       config: Dict[str, Any] = None) -> AgentMetadata:
        config = config or {}
        defn = SPECIALIZED_AGENT_DEFINITIONS.get(agent_type)
        if defn is None:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list_agent_types()}")

        metadata = AgentMetadata(
            id=agent_id,
            name=config.get("name", defn["name"]),
            type=agent_type,
            version=config.get("version", "1.0.0"),
            description=config.get("description", defn["description"]),
            capabilities=defn.get("capabilities", []),
            priority=config.get("priority", defn.get("priority", 50)),
            dependencies=config.get("dependencies", defn.get("dependencies", [])),
            permissions=config.get("permissions", []),
            supported_models=config.get("supported_models", [defn.get("default_model", "reasoning")]),
            cost_estimate_per_run=config.get("cost_estimate_per_run", 0.0),
            average_latency_ms=config.get("average_latency_ms", 0.0),
            max_concurrent_tasks=config.get("max_concurrent_tasks", 1),
            tags=config.get("tags", []),
        )

        instance = AgentInstance(metadata=metadata)

        with self._lock:
            self._agents[agent_id] = instance
            self._agent_types.setdefault(agent_type, []).append(agent_id)
            for cap in metadata.capabilities:
                self._capability_index.setdefault(cap, set()).add(agent_id)

        logger.info("AgentManager: registered '%s' as %s (v%s)",
                     agent_id, agent_type, metadata.version)
        self._emit("agent_registered", {"agent_id": agent_id, "type": agent_type})
        return metadata

    def unregister_agent(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._agents.pop(agent_id, None)
            if instance is None:
                return False
            agent_type = instance.metadata.type
            agents = self._agent_types.get(agent_type, [])
            if agent_id in agents:
                agents.remove(agent_id)
            for cap in instance.metadata.capabilities:
                idx = self._capability_index.get(cap)
                if idx:
                    idx.discard(agent_id)

        logger.info("AgentManager: unregistered '%s'", agent_id)
        self._emit("agent_unregistered", {"agent_id": agent_id})
        return True

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------

    def start_agent(self, agent_id: str,
                    config: Dict[str, Any] = None) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                logger.error("AgentManager: '%s' not found", agent_id)
                return False
            if instance.status == AgentLifecycleStatus.RUNNING:
                logger.warning("AgentManager: '%s' already running", agent_id)
                return True

            instance.status = AgentLifecycleStatus.STARTING
            config = config or {}

        try:
            agent_type = instance.metadata.type
            agent_instance = create_specialized_agent(agent_type, agent_id, config)

            with self._lock:
                instance.instance = agent_instance
                instance.status = AgentLifecycleStatus.RUNNING
                instance.health = AgentHealthStatus.HEALTHY
                instance.started_at = time.time()
                instance.last_heartbeat = time.time()
                instance.error = ""

            logger.info("AgentManager: started '%s' (%s)", agent_id, agent_type)
            self._emit("agent_started", {"agent_id": agent_id, "type": agent_type})
            return True

        except Exception as exc:
            with self._lock:
                instance.status = AgentLifecycleStatus.FAILED
                instance.health = AgentHealthStatus.UNHEALTHY
                instance.error = str(exc)
            logger.error("AgentManager: failed to start '%s': %s", agent_id, exc)
            self._emit("agent_error", {"agent_id": agent_id, "error": str(exc)})
            return False

    def stop_agent(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False
            if instance.status not in (AgentLifecycleStatus.RUNNING,
                                        AgentLifecycleStatus.PAUSED,
                                        AgentLifecycleStatus.STARTING):
                return False
            instance.status = AgentLifecycleStatus.STOPPING

        with self._lock:
            instance.status = AgentLifecycleStatus.STOPPED
            instance.health = AgentHealthStatus.UNKNOWN
            instance.instance = None

        logger.info("AgentManager: stopped '%s'", agent_id)
        self._emit("agent_stopped", {"agent_id": agent_id})
        return True

    def pause_agent(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None or instance.status != AgentLifecycleStatus.RUNNING:
                return False
            instance.status = AgentLifecycleStatus.PAUSED

        logger.info("AgentManager: paused '%s'", agent_id)
        self._emit("agent_paused", {"agent_id": agent_id})
        return True

    def resume_agent(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None or instance.status != AgentLifecycleStatus.PAUSED:
                return False
            instance.status = AgentLifecycleStatus.RESUMING

        with self._lock:
            instance.status = AgentLifecycleStatus.RUNNING
            instance.last_heartbeat = time.time()

        logger.info("AgentManager: resumed '%s'", agent_id)
        self._emit("agent_resumed", {"agent_id": agent_id})
        return True

    def restart_agent(self, agent_id: str,
                      config: Dict[str, Any] = None) -> bool:
        self.stop_agent(agent_id)
        time.sleep(0.1)
        return self.start_agent(agent_id, config)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def check_health(self, agent_id: str) -> AgentHealthStatus:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return AgentHealthStatus.UNKNOWN
            if instance.status == AgentLifecycleStatus.RUNNING:
                now = time.time()
                if instance.last_heartbeat and now - instance.last_heartbeat > 120:
                    instance.health = AgentHealthStatus.DEGRADED
                else:
                    instance.health = AgentHealthStatus.HEALTHY
            elif instance.status == AgentLifecycleStatus.FAILED:
                instance.health = AgentHealthStatus.UNHEALTHY
            return instance.health

    def record_heartbeat(self, agent_id: str) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False
            instance.last_heartbeat = time.time()
            if instance.status == AgentLifecycleStatus.RUNNING:
                instance.health = AgentHealthStatus.HEALTHY
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return None
            return instance

    def get_metadata(self, agent_id: str) -> Optional[AgentMetadata]:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return None
            return instance.metadata

    def list_agents(self, agent_type: str = "",
                    status: AgentLifecycleStatus = None,
                    capability: str = "") -> List[AgentInstance]:
        with self._lock:
            if capability:
                agent_ids = self._capability_index.get(capability, set())
                instances = [self._agents[aid] for aid in agent_ids
                            if aid in self._agents]
            elif agent_type:
                agent_ids = self._agent_types.get(agent_type, [])
                instances = [self._agents[aid] for aid in agent_ids
                            if aid in self._agents]
            else:
                instances = list(self._agents.values())

        if status:
            instances = [i for i in instances if i.status == status]
        instances.sort(key=lambda i: i.metadata.priority, reverse=True)
        return instances

    def list_running(self) -> List[AgentInstance]:
        return self.list_agents(status=AgentLifecycleStatus.RUNNING)

    def find_by_capability(self, capability: str) -> List[AgentInstance]:
        return self.list_agents(capability=capability)

    def get_agent_types(self) -> Dict[str, List[str]]:
        with self._lock:
            return dict(self._agent_types)

    def get_capability_index(self) -> Dict[str, List[str]]:
        with self._lock:
            return {k: sorted(v) for k, v in self._capability_index.items()}

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def set_agent_version(self, agent_id: str, version: str) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False
            instance.metadata.version = version
        return True

    def get_agent_version(self, agent_id: str) -> Optional[str]:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return None
            return instance.metadata.version

    # ------------------------------------------------------------------
    # Permission management
    # ------------------------------------------------------------------

    def set_agent_permissions(self, agent_id: str,
                               permissions: List[str]) -> bool:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False
            instance.metadata.permissions = permissions
        return True

    def get_agent_permissions(self, agent_id: str) -> List[str]:
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return []
            return list(instance.metadata.permissions)

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        self._global_callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._global_callbacks.get(event, []):
            try:
                cb(data)
            except Exception as exc:
                logger.error("AgentManager: callback error for %s: %s", event, exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._agents)
            running = sum(1 for a in self._agents.values()
                         if a.status == AgentLifecycleStatus.RUNNING)
            paused = sum(1 for a in self._agents.values()
                        if a.status == AgentLifecycleStatus.PAUSED)
            failed = sum(1 for a in self._agents.values()
                        if a.status == AgentLifecycleStatus.FAILED)
            healthy = sum(1 for a in self._agents.values()
                         if a.health == AgentHealthStatus.HEALTHY)
            by_type: Dict[str, int] = {}
            for a in self._agents.values():
                by_type[a.metadata.type] = by_type.get(a.metadata.type, 0) + 1
        return {
            "total_agents": total,
            "running": running,
            "paused": paused,
            "failed": failed,
            "healthy": healthy,
            "by_type": by_type,
            "capability_count": len(self._capability_index),
        }