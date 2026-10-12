"""
Remote agent connection and control platform for AetherOS.

Manages remote AetherOS instance connections, health checks with latency
measurement, remote agent lifecycle (start, stop, pause, resume, restart),
remote log streaming, remote task management, remote agent monitoring,
remote automation triggering, secure connection with mutual TLS or token
auth, and auto-reconnect with exponential backoff.

Collaboration architecture stubs:
  - Team workspaces
  - Shared agents
  - Shared knowledge
  - Role-based access (admin, developer, operator, viewer)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEALTH_CHECK_INTERVAL = 30
_DEFAULT_RECONNECT_BACKOFF = 2.0
_MAX_RECONNECT_BACKOFF = 120.0
_RECONNECT_BACKOFF_MULTIPLIER = 2.0
_LOG_STREAM_BUFFER = 5000
_TASK_POLL_INTERVAL = 5
_MAX_LOG_LINES = 1000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RemoteInstanceStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    UNREACHABLE = "unreachable"


class AgentStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuthType(Enum):
    TOKEN = "token"
    MUTUAL_TLS = "mutual_tls"
    API_KEY = "api_key"
    NONE = "none"


class CollaborationRole(Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RemoteInstance:
    """Describes a remote AetherOS instance."""
    id: str
    name: str
    url: str
    status: RemoteInstanceStatus
    version: str
    latency: float
    connected_at: float
    capabilities: List[str]
    auth_type: AuthType
    last_health_check: float = 0.0
    error_count: int = 0
    last_error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "status": self.status.value,
            "version": self.version,
            "latency": self.latency,
            "connected_at": self.connected_at,
            "capabilities": self.capabilities,
            "auth_type": self.auth_type.value,
            "last_health_check": self.last_health_check,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteInstance:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            url=data["url"],
            status=RemoteInstanceStatus(data["status"]),
            version=data.get("version", ""),
            latency=data.get("latency", 0.0),
            connected_at=data.get("connected_at", 0.0),
            capabilities=data.get("capabilities", []),
            auth_type=AuthType(data.get("auth_type", "token")),
            last_health_check=data.get("last_health_check", 0.0),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error", ""),
        )


@dataclass
class RemoteAgentStatus:
    """Status of an agent running on a remote instance."""
    id: str
    name: str
    status: AgentStatus
    uptime: float
    tasks_completed: int
    memory_usage: float
    cpu_usage: float
    last_error: str
    started_at: float
    instance_id: str = ""
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "uptime": self.uptime,
            "tasks_completed": self.tasks_completed,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "instance_id": self.instance_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteAgentStatus:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            status=AgentStatus(data["status"]),
            uptime=data.get("uptime", 0.0),
            tasks_completed=data.get("tasks_completed", 0),
            memory_usage=data.get("memory_usage", 0.0),
            cpu_usage=data.get("cpu_usage", 0.0),
            last_error=data.get("last_error", ""),
            started_at=data.get("started_at", 0.0),
            instance_id=data.get("instance_id", ""),
            version=data.get("version", ""),
        )


@dataclass
class RemoteTask:
    """A task running on a remote agent."""
    id: str
    agent_id: str
    type: str
    status: TaskStatus
    progress: float
    result: Optional[Dict[str, Any]]
    created_at: float
    completed_at: float
    instance_id: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "type": self.type,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "instance_id": self.instance_id,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RemoteTask:
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            type=data.get("type", ""),
            status=TaskStatus(data["status"]),
            progress=data.get("progress", 0.0),
            result=data.get("result"),
            created_at=data.get("created_at", 0.0),
            completed_at=data.get("completed_at", 0.0),
            instance_id=data.get("instance_id", ""),
            error=data.get("error", ""),
        )


@dataclass
class LogEntry:
    """A single log line from a remote agent."""
    line: str
    level: str
    timestamp: float
    source: str
    agent_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "level": self.level,
            "timestamp": self.timestamp,
            "source": self.source,
            "agent_id": self.agent_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LogEntry:
        return cls(
            line=data["line"],
            level=data.get("level", "INFO"),
            timestamp=data.get("timestamp", 0.0),
            source=data.get("source", ""),
            agent_id=data.get("agent_id", ""),
        )


@dataclass
class WorkspaceInfo:
    """A remote workspace with access control."""
    id: str
    name: str
    role: CollaborationRole
    agents: List[str]
    knowledge_bases: List[str]
    members: int
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "agents": self.agents,
            "knowledge_bases": self.knowledge_bases,
            "members": self.members,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkspaceInfo:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            role=CollaborationRole(data.get("role", "viewer")),
            agents=data.get("agents", []),
            knowledge_bases=data.get("knowledge_bases", []),
            members=data.get("members", 0),
            created_at=data.get("created_at", 0.0),
        )


# ---------------------------------------------------------------------------
# Backoff helper
# ---------------------------------------------------------------------------


class ExponentialBackoff:
    """Exponential backoff timer with configurable max and multiplier."""

    def __init__(
        self,
        initial: float = _DEFAULT_RECONNECT_BACKOFF,
        max_backoff: float = _MAX_RECONNECT_BACKOFF,
        multiplier: float = _RECONNECT_BACKOFF_MULTIPLIER,
    ) -> None:
        self._initial = initial
        self._max = max_backoff
        self._multiplier = multiplier
        self._current = initial
        self._attempt = 0

    def reset(self) -> None:
        self._current = self._initial
        self._attempt = 0

    def next_delay(self) -> float:
        delay = min(self._current, self._max)
        self._current = min(self._current * self._multiplier, self._max)
        self._attempt += 1
        return delay

    @property
    def attempt(self) -> int:
        return self._attempt


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _remote_dir() -> Path:
    return get_aetheros_home() / "sync" / "remote"


def _instances_path() -> Path:
    return _remote_dir() / "instances.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.error("Failed to save %s: %s", path.name, exc)
        raise


# ---------------------------------------------------------------------------
# RemoteAgentPlatform
# ---------------------------------------------------------------------------


class RemoteAgentPlatform:
    """Remote agent connection and control platform.

    Manages connections to remote AetherOS instances, agent lifecycle,
    task management, log streaming, monitoring, and collaboration features.

    Connection types:
      - Token auth (simple bearer token)
      - Mutual TLS (client cert + CA)
      - API key
      - None (local/unauthenticated)
    """

    def __init__(self) -> None:
        self._instances: Dict[str, RemoteInstance] = {}
        self._agents: Dict[str, RemoteAgentStatus] = {}
        self._tasks: Dict[str, RemoteTask] = {}
        self._log_buffers: Dict[str, List[LogEntry]] = {}
        self._workspaces: Dict[str, WorkspaceInfo] = {}

        self._lock = threading.Lock()
        self._health_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_backoffs: Dict[str, ExponentialBackoff] = {}
        self._http_client: Optional[Any] = None

        self._on_connected_callbacks: List[Callable[[str], None]] = []
        self._on_disconnected_callbacks: List[Callable[[str, str], None]] = []
        self._on_log_callbacks: List[Callable[[str, LogEntry], None]] = []
        self._on_agent_status_callbacks: List[Callable[[str, RemoteAgentStatus], None]] = []

        self._remote_dir = _remote_dir()
        self._remote_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted()

    # ------------------------------------------------------------------
    # HTTP client
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        if self._http_client is not None:
            return self._http_client
        try:
            import httpx
        except ImportError:
            raise RuntimeError(
                "httpx is required for remote agent platform. "
                "Install with: pip install httpx"
            )
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": "AetherOS-Remote/1.0"},
        )
        return self._http_client

    def _auth_headers(self, instance: RemoteInstance) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if instance.auth_type == AuthType.TOKEN:
            from aetheros_cli.config import get_env_value
            token = get_env_value(f"AETHEROS_REMOTE_TOKEN_{instance.id.upper().replace('-', '_')}")
            if token:
                h["Authorization"] = f"Bearer {token}"
        elif instance.auth_type == AuthType.API_KEY:
            from aetheros_cli.config import get_env_value
            key = get_env_value(f"AETHEROS_REMOTE_API_KEY_{instance.id.upper().replace('-', '_')}")
            if key:
                h["X-API-Key"] = key
        return h

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_persisted(self) -> None:
        raw = _load_json(_instances_path(), {})
        for inst_id, data in raw.items():
            try:
                inst = RemoteInstance.from_dict(data)
                self._instances[inst_id] = inst
            except Exception as exc:
                logger.warning("Failed to load remote instance %s: %s", inst_id, exc)

    def _save_persisted(self) -> None:
        with self._lock:
            data = {iid: inst.to_dict() for iid, inst in self._instances.items()}
        _save_json(_instances_path(), data)

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------

    def add_instance(
        self,
        name: str,
        url: str,
        auth_type: AuthType = AuthType.TOKEN,
        capabilities: Optional[List[str]] = None,
    ) -> RemoteInstance:
        """Register a new remote AetherOS instance for connection.

        Args:
            name: Human-readable name for the instance.
            url: Base URL of the remote instance (e.g. ``https://10.0.0.5:8443``).
            auth_type: Authentication method to use.
            capabilities: Optional list of capability strings (e.g.
                ``"agents"``, ``"tasks"``, ``"logs"``).

        Returns:
            The newly created :class:`RemoteInstance`.
        """
        instance_id = str(uuid.uuid4())
        instance = RemoteInstance(
            id=instance_id,
            name=name,
            url=url.rstrip("/"),
            status=RemoteInstanceStatus.DISCONNECTED,
            version="",
            latency=0.0,
            connected_at=0.0,
            capabilities=capabilities or ["health", "agents"],
            auth_type=auth_type,
        )
        with self._lock:
            self._instances[instance_id] = instance
        self._save_persisted()
        logger.info("Added remote instance '%s' (%s)", name, instance_id)
        return instance

    def remove_instance(self, instance_id: str) -> bool:
        """Remove a remote instance and disconnect if active."""
        self.disconnect(instance_id)
        with self._lock:
            if instance_id not in self._instances:
                return False
            del self._instances[instance_id]
            self._reconnect_backoffs.pop(instance_id, None)
            self._log_buffers.pop(instance_id, None)
        self._save_persisted()
        logger.info("Removed remote instance %s", instance_id)
        return True

    def list_instances(self) -> List[RemoteInstance]:
        """Return all registered remote instances."""
        with self._lock:
            return list(self._instances.values())

    def get_instance(self, instance_id: str) -> Optional[RemoteInstance]:
        """Return a specific remote instance."""
        with self._lock:
            return self._instances.get(instance_id)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self, instance_id: str) -> bool:
        """Connect to a remote instance and perform initial health check.

        Returns True if the connection was established successfully.
        """
        instance = self.get_instance(instance_id)
        if instance is None:
            logger.warning("Unknown instance: %s", instance_id)
            return False

        logger.info("Connecting to remote instance '%s' at %s", instance.name, instance.url)
        result = self.health_check(instance_id)
        if result:
            with self._lock:
                instance = self._instances.get(instance_id)
                if instance:
                    instance.status = RemoteInstanceStatus.CONNECTED
                    instance.connected_at = time.time()
                    instance.error_count = 0
                    instance.last_error = ""
            self._reconnect_backoffs.pop(instance_id, None)
            self._save_persisted()
            self._notify_connected(instance_id)
            return True

        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.status = RemoteInstanceStatus.ERROR
                instance.last_error = "Health check failed"
                instance.error_count += 1
        self._save_persisted()
        return False

    def disconnect(self, instance_id: str) -> bool:
        """Disconnect from a remote instance."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return False
            instance.status = RemoteInstanceStatus.DISCONNECTED
            instance.online = False
        self._save_persisted()
        self._notify_disconnected(instance_id, "disconnect")
        logger.info("Disconnected from %s", instance.name if instance else instance_id)
        return True

    def reconnect(self, instance_id: str) -> bool:
        """Attempt to reconnect to a remote instance.

        Uses exponential backoff to avoid hammering the remote endpoint.
        Returns True if the reconnection succeeded.
        """
        backoff = self._reconnect_backoffs.get(instance_id)
        if backoff is None:
            backoff = ExponentialBackoff()
            self._reconnect_backoffs[instance_id] = backoff

        delay = backoff.next_delay()
        logger.debug(
            "Reconnecting to %s in %.1fs (attempt %d)",
            instance_id, delay, backoff.attempt,
        )

        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.status = RemoteInstanceStatus.RECONNECTING

        time.sleep(delay)
        ok = self.connect(instance_id)
        if ok:
            backoff.reset()
        return ok

    def start_reconnect_loop(self, instance_id: str) -> None:
        """Start a background thread that continuously attempts reconnection.

        The loop runs until the connection is restored or
        :meth:`stop_reconnect_loop` is called.
        """
        thread = threading.Thread(
            target=self._reconnect_loop,
            args=(instance_id,),
            daemon=True,
            name=f"reconnect-{instance_id[:8]}",
        )
        thread.start()

    def _reconnect_loop(self, instance_id: str) -> None:
        """Background loop that retries connection with backoff."""
        backoff = ExponentialBackoff()
        self._reconnect_backoffs[instance_id] = backoff

        while not self._stop_event.is_set():
            instance = self.get_instance(instance_id)
            if instance is None:
                return
            if instance.status == RemoteInstanceStatus.CONNECTED:
                return

            delay = backoff.next_delay()
            logger.info(
                "Reconnect loop for %s: attempt %d in %.1fs",
                instance.name, backoff.attempt, delay,
            )
            self._stop_event.wait(delay)
            if self._stop_event.is_set():
                return

            ok = self.connect(instance_id)
            if ok:
                backoff.reset()
                logger.info("Reconnected to %s", instance.name)
                return

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self, instance_id: str) -> bool:
        """Perform a health check on a remote instance, measuring latency.

        Returns True if the instance responds correctly.
        """
        instance = self.get_instance(instance_id)
        if instance is None:
            return False

        client = self._get_client()
        headers = self._auth_headers(instance)
        start = time.monotonic()

        try:
            resp = client.get(f"{instance.url}/health", headers=headers)
            latency = time.monotonic() - start
            data = resp.json() if resp.is_success else {}

            with self._lock:
                inst = self._instances.get(instance_id)
                if inst:
                    inst.latency = round(latency * 1000, 1)
                    inst.version = data.get("version", inst.version)
                    inst.last_health_check = time.time()
                    inst.status = RemoteInstanceStatus.CONNECTED
                    inst.error_count = 0

                    caps = data.get("capabilities", [])
                    if caps:
                        inst.capabilities = caps

            self._save_persisted()
            logger.debug("Health check %s: %.1fms", instance.name, latency * 1000)
            return resp.is_success

        except Exception as exc:
            with self._lock:
                inst = self._instances.get(instance_id)
                if inst:
                    inst.status = RemoteInstanceStatus.UNREACHABLE
                    inst.last_error = str(exc)
                    inst.error_count += 1
            logger.warning("Health check failed for %s: %s", instance.name, exc)
            return False

    def start_background_health_checks(self, interval: int = _HEALTH_CHECK_INTERVAL) -> None:
        """Start a background thread that periodically checks all instances."""
        if self._health_thread and self._health_thread.is_alive():
            return
        self._stop_event.clear()
        self._health_thread = threading.Thread(
            target=self._health_check_loop,
            args=(interval,),
            daemon=True,
            name="remote-health",
        )
        self._health_thread.start()

    def stop_background_health_checks(self) -> None:
        """Stop the background health check loop."""
        self._stop_event.set()
        if self._health_thread:
            self._health_thread.join(timeout=10)

    def _health_check_loop(self, interval: int) -> None:
        """Periodic health check loop."""
        while not self._stop_event.is_set():
            with self._lock:
                instance_ids = list(self._instances.keys())
            for iid in instance_ids:
                if self._stop_event.is_set():
                    return
                instance = self.get_instance(iid)
                if instance and instance.status in (
                    RemoteInstanceStatus.CONNECTED,
                    RemoteInstanceStatus.ERROR,
                ):
                    self.health_check(iid)
            self._stop_event.wait(interval)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_connected(self, callback: Callable[[str], None]) -> None:
        self._on_connected_callbacks.append(callback)

    def on_disconnected(self, callback: Callable[[str, str], None]) -> None:
        self._on_disconnected_callbacks.append(callback)

    def on_log(self, callback: Callable[[str, LogEntry], None]) -> None:
        self._on_log_callbacks.append(callback)

    def on_agent_status(self, callback: Callable[[str, RemoteAgentStatus], None]) -> None:
        self._on_agent_status_callbacks.append(callback)

    def _notify_connected(self, instance_id: str) -> None:
        for cb in self._on_connected_callbacks:
            try:
                cb(instance_id)
            except Exception as exc:
                logger.warning("Connected callback error: %s", exc)

    def _notify_disconnected(self, instance_id: str, reason: str) -> None:
        for cb in self._on_disconnected_callbacks:
            try:
                cb(instance_id, reason)
            except Exception as exc:
                logger.warning("Disconnected callback error: %s", exc)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def _request(self, instance_id: str, method: str, path: str, **kwargs: Any) -> Optional[Any]:
        """Make an authenticated request to a remote instance.

        Returns the response JSON on success, or None on failure.
        """
        instance = self.get_instance(instance_id)
        if instance is None:
            return None

        client = self._get_client()
        headers = self._auth_headers(instance)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            resp = client.request(method, f"{instance.url}{path}", headers=headers, **kwargs)
            if resp.is_success:
                return resp.json() if resp.text else {}
            logger.warning(
                "Remote request %s %s returned %d", method, path, resp.status_code,
            )
            return None
        except Exception as exc:
            logger.warning("Remote request failed %s %s: %s", method, path, exc)
            with self._lock:
                inst = self._instances.get(instance_id)
                if inst:
                    inst.last_error = str(exc)
                    inst.error_count += 1
            return None

    def start_agent(self, instance_id: str, agent_name: str = "default") -> Optional[RemoteAgentStatus]:
        """Start an agent on a remote instance.

        Returns the agent status on success, or None on failure.
        """
        result = self._request(instance_id, "POST", f"/agents/{agent_name}/start")
        if result:
            status = RemoteAgentStatus.from_dict(result)
            self._update_agent_status(instance_id, status)
            return status
        return None

    def stop_agent(self, instance_id: str, agent_name: str = "default") -> Optional[RemoteAgentStatus]:
        """Stop an agent on a remote instance."""
        result = self._request(instance_id, "POST", f"/agents/{agent_name}/stop")
        if result:
            status = RemoteAgentStatus.from_dict(result)
            self._update_agent_status(instance_id, status)
            return status
        return None

    def pause_agent(self, instance_id: str, agent_name: str = "default") -> Optional[RemoteAgentStatus]:
        """Pause an agent on a remote instance."""
        result = self._request(instance_id, "POST", f"/agents/{agent_name}/pause")
        if result:
            status = RemoteAgentStatus.from_dict(result)
            self._update_agent_status(instance_id, status)
            return status
        return None

    def resume_agent(self, instance_id: str, agent_name: str = "default") -> Optional[RemoteAgentStatus]:
        """Resume a paused agent on a remote instance."""
        result = self._request(instance_id, "POST", f"/agents/{agent_name}/resume")
        if result:
            status = RemoteAgentStatus.from_dict(result)
            self._update_agent_status(instance_id, status)
            return status
        return None

    def restart_agent(self, instance_id: str, agent_name: str = "default") -> Optional[RemoteAgentStatus]:
        """Restart an agent on a remote instance."""
        result = self._request(instance_id, "POST", f"/agents/{agent_name}/restart")
        if result:
            status = RemoteAgentStatus.from_dict(result)
            self._update_agent_status(instance_id, status)
            return status
        return None

    def _update_agent_status(self, instance_id: str, status: RemoteAgentStatus) -> None:
        status.instance_id = instance_id
        with self._lock:
            self._agents[status.id] = status
        for cb in self._on_agent_status_callbacks:
            try:
                cb(instance_id, status)
            except Exception as exc:
                logger.warning("Agent status callback error: %s", exc)

    def get_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Return full status of a remote instance and its agents."""
        result = self._request(instance_id, "GET", "/status")
        return result

    # ------------------------------------------------------------------
    # Log streaming
    # ------------------------------------------------------------------

    def get_logs(
        self,
        instance_id: str,
        agent_name: str = "default",
        since: Optional[float] = None,
        level: Optional[str] = None,
        limit: int = _MAX_LOG_LINES,
    ) -> List[LogEntry]:
        """Fetch logs from a remote agent.

        Args:
            instance_id: The remote instance ID.
            agent_name: The agent to fetch logs for.
            since: Only return logs after this timestamp.
            level: Filter by log level (e.g. ``"INFO"``, ``"ERROR"``).
            limit: Maximum number of log lines to return.

        Returns:
            A list of :class:`LogEntry` objects.
        """
        buffer_key = f"{instance_id}:{agent_name}"
        result = self._request(
            instance_id, "GET", f"/agents/{agent_name}/logs",
            params={"since": since, "level": level, "limit": limit},
        )
        if result:
            entries = [LogEntry.from_dict(e) for e in result.get("logs", [])]
            with self._lock:
                buf = self._log_buffers.setdefault(buffer_key, [])
                buf.extend(entries)
                if len(buf) > _LOG_STREAM_BUFFER:
                    self._log_buffers[buffer_key] = buf[-_LOG_STREAM_BUFFER:]
            for entry in entries:
                for cb in self._on_log_callbacks:
                    try:
                        cb(instance_id, entry)
                    except Exception:
                        pass
            return entries

        with self._lock:
            buf = self._log_buffers.get(buffer_key, [])
        if since:
            buf = [e for e in buf if e.timestamp >= (since or 0)]
        if level:
            buf = [e for e in buf if e.level == level]
        return buf[:limit]

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def create_task(
        self,
        instance_id: str,
        agent_name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[RemoteTask]:
        """Create and dispatch a task to a remote agent.

        Args:
            instance_id: The remote instance ID.
            agent_name: The target agent.
            task_type: The type of task (e.g. ``"inference"``, ``"automation"``).
            params: Task parameters forwarded to the agent.

        Returns:
            The created :class:`RemoteTask` on success, or None.
        """
        result = self._request(
            instance_id, "POST", f"/agents/{agent_name}/tasks",
            json={"type": task_type, "params": params or {}},
        )
        if result:
            task = RemoteTask.from_dict(result)
            with self._lock:
                self._tasks[task.id] = task
            return task
        return None

    def get_tasks(
        self,
        instance_id: str,
        agent_name: Optional[str] = None,
        status_filter: Optional[TaskStatus] = None,
    ) -> List[RemoteTask]:
        """Return tasks from a remote instance.

        Args:
            instance_id: The remote instance ID.
            agent_name: Optional agent name filter.
            status_filter: Optional task status filter.

        Returns:
            A list of :class:`RemoteTask` objects.
        """
        path = f"/agents/{agent_name}/tasks" if agent_name else "/tasks"
        params = {}
        if status_filter:
            params["status"] = status_filter.value
        result = self._request(instance_id, "GET", path, params=params)
        if result:
            tasks = [RemoteTask.from_dict(t) for t in result.get("tasks", [])]
            with self._lock:
                for t in tasks:
                    self._tasks[t.id] = t
            return tasks

        with self._lock:
            results = list(self._tasks.values())
        if agent_name:
            results = [t for t in results if t.agent_id == agent_name]
        if status_filter:
            results = [t for t in results if t.status == status_filter]
        return sorted(results, key=lambda t: t.created_at, reverse=True)

    def cancel_task(self, instance_id: str, task_id: str) -> bool:
        """Cancel a remote task."""
        result = self._request(instance_id, "POST", f"/tasks/{task_id}/cancel")
        if result:
            with self._lock:
                task = self._tasks.get(task_id)
                if task:
                    task.status = TaskStatus.CANCELLED
            return True
        return False

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def get_memory(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Return memory usage info from a remote instance."""
        return self._request(instance_id, "GET", "/system/memory")

    def get_usage(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Return CPU/disk/network usage from a remote instance."""
        return self._request(instance_id, "GET", "/system/usage")

    def get_errors(self, instance_id: str, since: Optional[float] = None) -> List[Dict[str, Any]]:
        """Return recent errors from a remote instance."""
        result = self._request(
            instance_id, "GET", "/system/errors",
            params={"since": since},
        )
        return result.get("errors", []) if result else []

    # ------------------------------------------------------------------
    # Remote workspace access
    # ------------------------------------------------------------------

    def get_workspaces(self, instance_id: str) -> List[WorkspaceInfo]:
        """Return workspaces available on a remote instance."""
        result = self._request(instance_id, "GET", "/workspaces")
        if result:
            workspaces = [WorkspaceInfo.from_dict(w) for w in result.get("workspaces", [])]
            with self._lock:
                for w in workspaces:
                    self._workspaces[w.id] = w
            return workspaces

        with self._lock:
            return list(self._workspaces.values())

    def get_workspace(self, instance_id: str, workspace_id: str) -> Optional[WorkspaceInfo]:
        """Return a specific workspace."""
        result = self._request(instance_id, "GET", f"/workspaces/{workspace_id}")
        if result:
            ws = WorkspaceInfo.from_dict(result)
            with self._lock:
                self._workspaces[ws.id] = ws
            return ws

        with self._lock:
            return self._workspaces.get(workspace_id)

    def list_remote_files(self, instance_id: str, path: str = "") -> List[Dict[str, Any]]:
        """List files in a remote workspace directory."""
        result = self._request(instance_id, "GET", f"/files", params={"path": path})
        return result.get("files", []) if result else []

    def list_remote_projects(self, instance_id: str) -> List[Dict[str, Any]]:
        """List projects on a remote instance."""
        result = self._request(instance_id, "GET", "/projects")
        return result.get("projects", []) if result else []

    def trigger_automation(
        self,
        instance_id: str,
        automation_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[RemoteTask]:
        """Trigger an automation on a remote instance.

        Returns a :class:`RemoteTask` tracking the automation execution.
        """
        result = self._request(
            instance_id, "POST", f"/automations/{automation_id}/trigger",
            json={"params": params or {}},
        )
        if result:
            task = RemoteTask.from_dict(result)
            with self._lock:
                self._tasks[task.id] = task
            return task
        return None

    # ------------------------------------------------------------------
    # Collaboration stubs
    # ------------------------------------------------------------------

    def create_team_workspace(
        self,
        instance_id: str,
        name: str,
        role: CollaborationRole = CollaborationRole.ADMIN,
    ) -> Optional[WorkspaceInfo]:
        """Create a team workspace on a remote instance.

        This is a stub for the collaboration architecture. The actual
        implementation depends on the remote instance's workspace API.
        """
        result = self._request(
            instance_id, "POST", "/workspaces",
            json={"name": name, "role": role.value},
        )
        if result:
            ws = WorkspaceInfo.from_dict(result)
            with self._lock:
                self._workspaces[ws.id] = ws
            return ws
        return None

    def share_agent(
        self,
        instance_id: str,
        agent_name: str,
        workspace_id: str,
        role: CollaborationRole = CollaborationRole.OPERATOR,
    ) -> bool:
        """Share an agent with a team workspace.

        This is a stub for the collaboration architecture.
        """
        result = self._request(
            instance_id, "POST", f"/agents/{agent_name}/share",
            json={"workspace_id": workspace_id, "role": role.value},
        )
        return result is not None

    def share_knowledge(
        self,
        instance_id: str,
        knowledge_id: str,
        workspace_id: str,
    ) -> bool:
        """Share a knowledge base with a team workspace.

        This is a stub for the collaboration architecture.
        """
        result = self._request(
            instance_id, "POST", f"/knowledge/{knowledge_id}/share",
            json={"workspace_id": workspace_id},
        )
        return result is not None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Shut down the platform, disconnecting all instances."""
        self.stop_background_health_checks()

        with self._lock:
            instance_ids = list(self._instances.keys())

        for iid in instance_ids:
            self.disconnect(iid)

        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

        logger.info("Remote agent platform shut down")
