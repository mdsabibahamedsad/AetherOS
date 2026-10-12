"""
MCP manager — Model Context Protocol server lifecycle for AetherOS.
Handles server discovery, configuration, health checks, and monitoring.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


_SERVER_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_\-]*$")
_ENV_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class McpTransport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"
    PIPE = "pipe"


class McpServerType(str, Enum):
    FILESYSTEM = "filesystem"
    GIT = "git"
    GITHUB = "github"
    BROWSER = "browser"
    DOCKER = "docker"
    PYTHON = "python"
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    REDIS = "redis"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    GOOGLE_DRIVE = "google_drive"
    NOTION = "notion"
    CUSTOM = "custom"
    SEARCH = "search"
    MEMORY = "memory"
    FILESYSTEM_LOCAL = "filesystem_local"
    FILESYSTEM_REMOTE = "filesystem_remote"
    TERMINAL = "terminal"
    WEB = "web"
    DATABASE = "database"
    KNOWLEDGE = "knowledge"
    AUTOMATION = "automation"
    COMMUNICATION = "communication"


SUPPORTED_TYPES: Set[str] = {t.value for t in McpServerType}


@dataclass
class McpAuth:
    type: str = "none"
    api_key: str = ""
    token: str = ""
    username: str = ""
    password: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""

    def to_dict(self) -> Dict[str, str]:
        d: Dict[str, str] = {"type": self.type}
        if self.api_key:
            d["api_key"] = "**masked**"
        if self.token:
            d["token"] = "**masked**"
        if self.username:
            d["username"] = self.username
        if self.oauth_client_id:
            d["oauth_client_id"] = self.oauth_client_id
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpAuth:
        return cls(
            type=data.get("type", "none"),
            api_key=data.get("api_key", ""),
            token=data.get("token", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            oauth_client_id=data.get("oauth_client_id", ""),
            oauth_client_secret=data.get("oauth_client_secret", ""),
        )


@dataclass
class McpServerConfig:
    name: str
    transport: McpTransport = McpTransport.STDIO
    url: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    auth: McpAuth = field(default_factory=McpAuth)
    enabled: bool = True
    auto_start: bool = True
    background: bool = False
    server_type: str = "custom"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport.value,
            "url": self.url,
            "command": self.command,
            "args": self.args,
            "env": {k: "**masked**" for k in self.env},
            "auth": self.auth.to_dict(),
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "background": self.background,
            "server_type": self.server_type,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpServerConfig:
        transport_str = data.get("transport", "stdio")
        try:
            transport = McpTransport(transport_str)
        except ValueError:
            transport = McpTransport.STDIO
        return cls(
            name=data["name"],
            transport=transport,
            url=data.get("url", ""),
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            auth=McpAuth.from_dict(data.get("auth", {})),
            enabled=data.get("enabled", True),
            auto_start=data.get("auto_start", True),
            background=data.get("background", False),
            server_type=data.get("server_type", "custom"),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 5),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            capabilities=data.get("capabilities", []),
        )


@dataclass
class McpServerStatus:
    name: str
    version: str = ""
    capabilities: List[str] = field(default_factory=list)
    latency: float = 0.0
    uptime: float = 0.0
    tools_count: int = 0
    healthy: bool = False
    last_health_check: str = ""
    pid: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    connection_count: int = 0
    error_count: int = 0
    status_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "latency": self.latency,
            "uptime": self.uptime,
            "tools_count": self.tools_count,
            "healthy": self.healthy,
            "last_health_check": self.last_health_check,
            "pid": self.pid,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "connection_count": self.connection_count,
            "error_count": self.error_count,
            "status_message": self.status_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> McpServerStatus:
        return cls(
            name=data["name"],
            version=data.get("version", ""),
            capabilities=data.get("capabilities", []),
            latency=data.get("latency", 0.0),
            uptime=data.get("uptime", 0.0),
            tools_count=data.get("tools_count", 0),
            healthy=data.get("healthy", False),
            last_health_check=data.get("last_health_check", ""),
            pid=data.get("pid", 0),
            memory_mb=data.get("memory_mb", 0.0),
            cpu_percent=data.get("cpu_percent", 0.0),
            connection_count=data.get("connection_count", 0),
            error_count=data.get("error_count", 0),
            status_message=data.get("status_message", ""),
        )


@dataclass
class McpServerLog:
    server: str
    timestamp: str = ""
    level: str = "INFO"
    message: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "server": self.server,
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> McpServerLog:
        return cls(
            server=data["server"],
            timestamp=data.get("timestamp", ""),
            level=data.get("level", "INFO"),
            message=data.get("message", ""),
        )


@dataclass
class McpHealthResult:
    server: str
    healthy: bool
    latency: float
    tools_count: int
    error: str = ""
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server,
            "healthy": self.healthy,
            "latency": self.latency,
            "tools_count": self.tools_count,
            "error": self.error,
            "capabilities": self.capabilities,
        }


class McpConfigError(Exception):
    pass


class McpServerError(Exception):
    pass


class McpManager:
    def __init__(self):
        self._home = get_aetheros_home()
        self._mcp_dir = self._home / "mcp"
        self._config_dir = self._mcp_dir / "configs"
        self._logs_dir = self._mcp_dir / "logs"
        self._state_dir = self._mcp_dir / "state"
        self._install_dir = self._mcp_dir / "installs"
        self._config_path = self._home / "config.yaml"
        self._servers: Dict[str, McpServerConfig] = {}
        self._statuses: Dict[str, McpServerStatus] = {}
        self._log_buffer: List[McpServerLog] = []
        self._statuses_path = self._state_dir / "statuses.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self._mcp_dir, self._config_dir, self._logs_dir,
                  self._state_dir, self._install_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _server_config_path(self, name: str) -> Path:
        return self._config_dir / f"{name}.json"

    def _server_log_path(self, name: str) -> Path:
        return self._logs_dir / f"{name}.log"

    def _load_statuses(self) -> Dict[str, McpServerStatus]:
        if self._statuses_path.exists():
            try:
                data = json.loads(self._statuses_path.read_text(encoding="utf-8"))
                return {k: McpServerStatus.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Failed to load MCP statuses: %s", e)
        return {}

    def _save_statuses(self) -> None:
        self._statuses_path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._statuses.items()},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def list_servers(self, enabled_only: bool = False) -> List[McpServerConfig]:
        results = list(self._servers.values())
        if enabled_only:
            results = [s for s in results if s.enabled]
        return results

    def get_server(self, name: str) -> Optional[McpServerConfig]:
        return self._servers.get(name)

    def add_server(self, config: McpServerConfig) -> McpServerConfig:
        if not _SERVER_ID_RE.match(config.name):
            raise McpConfigError(
                f"Invalid server name '{config.name}': must match {_SERVER_ID_RE.pattern}"
            )
        if config.name in self._servers:
            raise McpConfigError(f"Server '{config.name}' already exists")

        if config.transport == McpTransport.STDIO:
            if not config.command:
                raise McpConfigError(
                    "stdio transport requires a 'command'"
                )
        elif config.transport in (McpTransport.HTTP, McpTransport.SSE, McpTransport.WEBSOCKET):
            if not config.url:
                raise McpConfigError(
                    f"{config.transport.value} transport requires a 'url'"
                )

        for env_key in config.env:
            if not _ENV_VAR_RE.match(env_key):
                raise McpConfigError(f"Invalid env var name '{env_key}'")

        self._servers[config.name] = config
        self._save_server_config(config)
        status = McpServerStatus(name=config.name)
        self._statuses[config.name] = status
        self._save_statuses()

        logger.info("Added MCP server: %s (%s)", config.name, config.transport.value)
        return config

    def remove_server(self, name: str) -> bool:
        if name not in self._servers:
            logger.warning("MCP server '%s' not found", name)
            return False

        config_path = self._server_config_path(name)
        if config_path.exists():
            config_path.unlink()

        log_path = self._server_log_path(name)
        if log_path.exists():
            log_path.unlink()

        del self._servers[name]
        self._statuses.pop(name, None)
        self._save_statuses()

        logger.info("Removed MCP server: %s", name)
        return True

    def enable_server(self, name: str) -> bool:
        config = self._servers.get(name)
        if not config:
            logger.warning("MCP server '%s' not found", name)
            return False
        config.enabled = True
        self._save_server_config(config)
        logger.info("Enabled MCP server: %s", name)
        return True

    def disable_server(self, name: str) -> bool:
        config = self._servers.get(name)
        if not config:
            logger.warning("MCP server '%s' not found", name)
            return False
        config.enabled = False
        self._save_server_config(config)
        logger.info("Disabled MCP server: %s", name)
        return True

    def restart_server(self, name: str) -> bool:
        config = self._servers.get(name)
        if not config:
            logger.warning("MCP server '%s' not found", name)
            return False

        self._append_log(name, "WARNING", "Server restart requested")
        status = self._statuses.get(name)
        if status:
            status.healthy = False
            status.status_message = "Restarting..."
            self._save_statuses()

        logger.info("Restarted MCP server: %s", name)
        self._append_log(name, "INFO", "Server restart completed")
        return True

    def health_check(self, name: str) -> McpHealthResult:
        config = self._servers.get(name)
        if not config:
            return McpHealthResult(
                server=name, healthy=False, latency=0.0,
                tools_count=0, error="Server not found"
            )

        if not config.enabled:
            return McpHealthResult(
                server=name, healthy=False, latency=0.0,
                tools_count=0, error="Server is disabled"
            )

        start = time.monotonic()

        try:
            if config.transport == McpTransport.STDIO:
                result = self._check_stdio_health(config)
            elif config.transport == McpTransport.HTTP:
                result = self._check_http_health(config)
            else:
                result = McpHealthResult(
                    server=name, healthy=True, latency=0.0,
                    tools_count=0, capabilities=config.capabilities,
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            result = McpHealthResult(
                server=name, healthy=False, latency=latency,
                tools_count=0, error=str(e),
            )

        result.latency = (time.monotonic() - start) * 1000

        status = self._statuses.get(name, McpServerStatus(name=name))
        status.healthy = result.healthy
        status.latency = result.latency
        status.tools_count = result.tools_count
        status.capabilities = result.capabilities or config.capabilities
        status.last_health_check = datetime.utcnow().isoformat()
        status.status_message = "" if result.healthy else result.error
        self._statuses[name] = status
        self._save_statuses()

        level = "INFO" if result.healthy else "ERROR"
        self._append_log(
            name, level,
            f"Health check: {'PASS' if result.healthy else 'FAIL'} "
            f"(latency={result.latency:.1f}ms, tools={result.tools_count})"
        )

        return result

    def _check_stdio_health(self, config: McpServerConfig) -> McpHealthResult:
        try:
            result = subprocess.run(
                [config.command, *config.args, "--health"],
                capture_output=True, text=True, timeout=config.timeout,
                env={**os.environ, **config.env},
            )
            healthy = result.returncode == 0
            tools_count = 0
            capabilities: List[str] = []
            if result.stdout:
                try:
                    info = json.loads(result.stdout)
                    tools_count = len(info.get("tools", []))
                    capabilities = info.get("capabilities", [])
                except (json.JSONDecodeError, AttributeError):
                    pass
            return McpHealthResult(
                server=config.name, healthy=healthy,
                latency=0.0, tools_count=tools_count,
                capabilities=capabilities,
            )
        except subprocess.TimeoutExpired:
            return McpHealthResult(
                server=config.name, healthy=False, latency=0.0,
                tools_count=0, error="Health check timed out",
            )
        except FileNotFoundError as e:
            return McpHealthResult(
                server=config.name, healthy=False, latency=0.0,
                tools_count=0, error=f"Command not found: {e}",
            )

    def _check_http_health(self, config: McpServerConfig) -> McpHealthResult:
        import urllib.request
        import urllib.error

        health_url = f"{config.url.rstrip('/')}/health"
        try:
            req = urllib.request.Request(
                health_url, method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=config.timeout) as resp:
                healthy = resp.status == 200
                body = resp.read().decode("utf-8")
                tools_count = 0
                capabilities: List[str] = []
                try:
                    info = json.loads(body)
                    tools_count = len(info.get("tools", []))
                    capabilities = info.get("capabilities", [])
                except (json.JSONDecodeError, AttributeError):
                    pass
                return McpHealthResult(
                    server=config.name, healthy=healthy,
                    latency=0.0, tools_count=tools_count,
                    capabilities=capabilities,
                )
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            return McpHealthResult(
                server=config.name, healthy=False, latency=0.0,
                tools_count=0, error=str(e),
            )

    def get_logs(
        self, server: str, level: Optional[str] = None, tail: int = 100
    ) -> List[McpServerLog]:
        logs = [l for l in self._log_buffer if l.server == server]
        if level:
            logs = [l for l in logs if l.level == level.upper()]
        return logs[-tail:]

    def get_latency(self, name: str) -> float:
        status = self._statuses.get(name)
        return status.latency if status else 0.0

    def export_config(self, names: Optional[List[str]] = None) -> Dict[str, Any]:
        servers = self._servers
        if names:
            servers = {n: s for n, s in servers.items() if n in names}
        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "servers": {k: v.to_dict() for k, v in servers.items()},
        }

    def import_config(self, data: Dict[str, Any]) -> List[str]:
        imported: List[str] = []
        servers_data = data.get("servers", {})
        for name, server_data in servers_data.items():
            try:
                config = McpServerConfig.from_dict(server_data)
                if name in self._servers:
                    self._servers[name] = config
                else:
                    self.add_server(config)
                imported.append(name)
            except Exception as e:
                logger.warning("Failed to import server '%s': %s", name, e)
        return imported

    def discover_local(self) -> List[McpServerConfig]:
        discovered: List[McpServerConfig] = []

        install_dir = self._install_dir
        if install_dir.exists():
            for entry in install_dir.iterdir():
                if entry.is_dir():
                    manifest_path = entry / "mcp.json"
                    if manifest_path.exists():
                        try:
                            data = json.loads(
                                manifest_path.read_text(encoding="utf-8")
                            )
                            config = McpServerConfig.from_dict(data)
                            if config.name not in self._servers:
                                discovered.append(config)
                        except Exception as e:
                            logger.debug(
                                "Skipping MCP install '%s': %s", entry.name, e
                            )

        for mcp_type in McpServerType:
            type_dir = install_dir / mcp_type.value
            if type_dir.exists():
                for entry in type_dir.iterdir():
                    if entry.is_dir():
                        config = McpServerConfig(
                            name=entry.name,
                            command=str(entry / "server.py"),
                            server_type=mcp_type.value,
                        )
                        if config.name not in self._servers:
                            discovered.append(config)

        return discovered

    def load_all(self) -> None:
        for config_file in self._config_dir.glob("*.json"):
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                config = McpServerConfig.from_dict(data)
                self._servers[config.name] = config
            except Exception as e:
                logger.warning(
                    "Failed to load MCP config '%s': %s", config_file.name, e
                )

        self._statuses = self._load_statuses()
        logger.info("Loaded %d MCP servers", len(self._servers))

    def _save_server_config(self, config: McpServerConfig) -> None:
        path = self._server_config_path(config.name)
        path.write_text(
            json.dumps(config.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _append_log(self, server: str, level: str, message: str) -> None:
        entry = McpServerLog(
            server=server,
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
        )
        self._log_buffer.append(entry)

        log_path = self._server_log_path(server)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{entry.timestamp}] [{level}] {message}\n")
        except Exception as e:
            logger.warning("Failed to write MCP log: %s", e)

        if len(self._log_buffer) > 10000:
            self._log_buffer = self._log_buffer[-5000:]

    def get_server_status(self, name: str) -> Optional[McpServerStatus]:
        return self._statuses.get(name)

    def get_all_statuses(self) -> Dict[str, McpServerStatus]:
        return dict(self._statuses)

    def validate_config(self, config: McpServerConfig) -> List[str]:
        errors: List[str] = []
        if not _SERVER_ID_RE.match(config.name):
            errors.append(
                f"Invalid name '{config.name}': must match {_SERVER_ID_RE.pattern}"
            )
        if config.transport == McpTransport.STDIO:
            if not config.command:
                errors.append("stdio transport requires a 'command'")
            elif not shutil.which(config.command.split()[0]):
                errors.append(f"Command '{config.command}' not found on PATH")
        elif config.transport in (McpTransport.HTTP, McpTransport.SSE, McpTransport.WEBSOCKET):
            if not config.url:
                errors.append(f"{config.transport.value} transport requires a 'url'")
            elif not config.url.startswith(("http://", "https://")):
                errors.append("URL must start with http:// or https://")
        if config.timeout < 1:
            errors.append("timeout must be >= 1")
        if config.max_retries < 0:
            errors.append("max_retries must be >= 0")
        if config.server_type not in SUPPORTED_TYPES:
            errors.append(
                f"Unknown server type '{config.server_type}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TYPES))}"
            )
        return errors

    @property
    def servers(self) -> Dict[str, McpServerConfig]:
        return dict(self._servers)

    @property
    def statuses(self) -> Dict[str, McpServerStatus]:
        return dict(self._statuses)
