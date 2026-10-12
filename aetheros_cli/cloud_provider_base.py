"""
Abstract cloud provider interface for AetherOS Cloud Sync.

Defines the :class:`CloudProvider` ABC that all sync backends implement,
along with built-in providers (local filesystem, custom server), a provider
registry, connection pooling with retry logic, and timeout handling.

Supported backend types:
  - Local Only (filesystem-based)
  - Cloud Sync (S3, B2, etc.)
  - Self-Hosted Sync
  - Custom Server
  - Remote AetherOS Instance
"""

from __future__ import annotations

import abc
import json
import logging
import os
import shutil
import threading
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY_LOCK = threading.Lock()
_DEFAULT_CONNECT_TIMEOUT = 15.0
_DEFAULT_READ_TIMEOUT = 60.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BACKOFF = 1.5


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FileMetadata:
    """Metadata for a file stored on a sync provider."""
    path: str
    size: int
    etag: str
    last_modified: float
    is_directory: bool = False
    mime_type: str = ""
    checksum: str = ""
    version: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "is_directory": self.is_directory,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "version": self.version,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileMetadata:
        return cls(
            path=data["path"],
            size=data.get("size", 0),
            etag=data.get("etag", ""),
            last_modified=data.get("last_modified", 0.0),
            is_directory=data.get("is_directory", False),
            mime_type=data.get("mime_type", ""),
            checksum=data.get("checksum", ""),
            version=data.get("version", ""),
            extra=data.get("extra", {}),
        )


@dataclass
class SyncTransportConfig:
    """Transport configuration for a sync provider backend."""
    provider_type: str
    endpoint: str = ""
    credentials: Dict[str, str] = field(default_factory=dict)
    encryption_key: str = ""
    compression: bool = True
    sync_interval: int = 300
    connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = _DEFAULT_READ_TIMEOUT
    max_retries: int = _DEFAULT_MAX_RETRIES
    retry_backoff: float = _DEFAULT_RETRY_BACKOFF
    region: str = ""
    bucket: str = ""
    prefix: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_type": self.provider_type,
            "endpoint": self.endpoint,
            "compression": self.compression,
            "sync_interval": self.sync_interval,
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "max_retries": self.max_retries,
            "retry_backoff": self.retry_backoff,
            "region": self.region,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SyncTransportConfig:
        return cls(
            provider_type=data.get("provider_type", "local"),
            endpoint=data.get("endpoint", ""),
            credentials=data.get("credentials", {}),
            encryption_key=data.get("encryption_key", ""),
            compression=data.get("compression", True),
            sync_interval=data.get("sync_interval", 300),
            connect_timeout=data.get("connect_timeout", _DEFAULT_CONNECT_TIMEOUT),
            read_timeout=data.get("read_timeout", _DEFAULT_READ_TIMEOUT),
            max_retries=data.get("max_retries", _DEFAULT_MAX_RETRIES),
            retry_backoff=data.get("retry_backoff", _DEFAULT_RETRY_BACKOFF),
            region=data.get("region", ""),
            bucket=data.get("bucket", ""),
            prefix=data.get("prefix", ""),
            extra=data.get("extra", {}),
        )


# ---------------------------------------------------------------------------
# Retry utilities
# ---------------------------------------------------------------------------


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts have been exhausted."""


def with_retry(
    fn: Callable[..., Any],
    max_retries: int = _DEFAULT_MAX_RETRIES,
    backoff: float = _DEFAULT_RETRY_BACKOFF,
    retryable_exceptions: tuple = (OSError, ConnectionError, TimeoutError),
    **kwargs: Any,
) -> Any:
    """Execute *fn* with exponential backoff retry logic.

    Args:
        fn: The callable to execute.
        max_retries: Maximum number of retry attempts.
        backoff: Multiplier for exponential backoff.
        retryable_exceptions: Exception types that trigger a retry.
        **kwargs: Forwarded to *fn*.

    Returns:
        The return value of *fn*.

    Raises:
        RetryExhaustedError: If all attempts fail.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return fn(**kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = backoff ** attempt
                logger.debug(
                    "Retry %d/%d for %s after %.1fs: %s",
                    attempt + 1, max_retries, fn.__name__, wait, exc,
                )
                time.sleep(wait)
    raise RetryExhaustedError(
        f"{fn.__name__} failed after {max_retries + 1} attempts: {last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------


class ConnectionPool:
    """Simple connection pool for provider connections.

    Maintains a dict of named connections with configurable TTL and
    reconnection logic. Thread-safe.
    """

    def __init__(self, ttl: float = 300.0) -> None:
        self._ttl = ttl
        self._connections: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, name: str) -> Optional[Any]:
        """Return a cached connection if it hasn't expired."""
        with self._lock:
            ts = self._timestamps.get(name)
            if ts is None:
                return None
            if time.monotonic() - ts > self._ttl:
                self._connections.pop(name, None)
                self._timestamps.pop(name, None)
                return None
            return self._connections.get(name)

    def put(self, name: str, connection: Any) -> None:
        """Store a connection in the pool."""
        with self._lock:
            self._connections[name] = connection
            self._timestamps[name] = time.monotonic()

    def remove(self, name: str) -> None:
        """Remove a connection from the pool."""
        with self._lock:
            self._connections.pop(name, None)
            self._timestamps.pop(name, None)

    def clear(self) -> None:
        """Remove all connections."""
        with self._lock:
            self._connections.clear()
            self._timestamps.clear()

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._connections)


# ---------------------------------------------------------------------------
# Abstract base provider
# ---------------------------------------------------------------------------


class CloudProvider(abc.ABC):
    """Abstract base class for cloud sync providers.

    All sync backends must implement these methods. Providers are registered
    in the :class:`ProviderRegistry` and instantiated via
    :meth:`ProviderRegistry.create`.
    """

    def __init__(self, config: SyncTransportConfig) -> None:
        self.config = config
        self._pool = ConnectionPool()
        self._authenticated = False

    @property
    def provider_type(self) -> str:
        return self.config.provider_type

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def authenticate(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """Authenticate with the provider.

        Args:
            credentials: Optional credential overrides. Falls back to
                ``config.credentials`` if not provided.

        Returns:
            True if authentication succeeded.
        """
        ...

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def upload(self, path: str, data: bytes) -> str:
        """Upload *data* to *path* on the provider.

        Args:
            path: Remote path for the file.
            data: Raw bytes to upload.

        Returns:
            An etag or version identifier for the uploaded file.
        """
        ...

    @abc.abstractmethod
    def download(self, path: str) -> bytes:
        """Download the file at *path* from the provider.

        Args:
            path: Remote path of the file.

        Returns:
            Raw file contents as bytes.
        """
        ...

    @abc.abstractmethod
    def list(self, path: str) -> List[FileMetadata]:
        """List files and directories under *path*.

        Args:
            path: Remote directory path to list.

        Returns:
            A list of :class:`FileMetadata` objects.
        """
        ...

    @abc.abstractmethod
    def delete(self, path: str) -> bool:
        """Delete the file at *path*.

        Args:
            path: Remote path to delete.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        ...

    @abc.abstractmethod
    def move(self, from_path: str, to_path: str) -> bool:
        """Move or rename a file on the provider.

        Args:
            from_path: Source path.
            to_path: Destination path.

        Returns:
            True on success.
        """
        ...

    @abc.abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether a file exists at *path*.

        Returns:
            True if the file exists.
        """
        ...

    @abc.abstractmethod
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """Return extended metadata for a file.

        Returns:
            A dict with at least ``size``, ``etag``, ``last_modified``.
        """
        ...

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        """Tear down the provider connection."""
        self._pool.clear()
        self._authenticated = False

    def is_connected(self) -> bool:
        """Return whether the provider has an active authenticated session."""
        return self._authenticated

    def health_check(self) -> bool:
        """Quick connectivity check.

        Default implementation calls ``exists("/")``. Providers may override
        with a lighter check.
        """
        try:
            return self.exists("")
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Built-in providers
# ---------------------------------------------------------------------------


class LocalProvider(CloudProvider):
    """Filesystem-based provider for self-hosted / local-only sync.

    Uses a local directory as the sync store. All paths are relative to the
    configured ``endpoint`` (which defaults to ``~/.aetheros/sync/store/``).
    """

    def __init__(self, config: SyncTransportConfig) -> None:
        super().__init__(config)
        if not config.endpoint:
            self._root = get_aetheros_home() / "sync" / "store"
        else:
            self._root = Path(config.endpoint)
        self._root.mkdir(parents=True, exist_ok=True)
        self._authenticated = True

    def _resolve(self, path: str) -> Path:
        clean = path.strip("/\\").replace("\\", "/") if path else ""
        resolved = (self._root / clean).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise PermissionError(f"Path traversal denied: {path}")
        return resolved

    def authenticate(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        self._authenticated = self._root.exists()
        return self._authenticated

    def upload(self, path: str, data: bytes) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()
        logger.debug("LocalProvider: uploaded %s (%d bytes)", path, len(data))
        return checksum

    def download(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_bytes()

    def list(self, path: str) -> List[FileMetadata]:
        target = self._resolve(path)
        if not target.exists():
            return []
        if target.is_file():
            return [self._metadata(target, path)]

        results: List[FileMetadata] = []
        for entry in sorted(target.iterdir()):
            rel = entry.relative_to(self._root).as_posix()
            results.append(self._metadata(entry, rel))
        return results

    def _metadata(self, entry: Path, rel_path: str) -> FileMetadata:
        stat = entry.stat()
        checksum = ""
        if entry.is_file() and stat.st_size < 100 * 1024 * 1024:
            try:
                checksum = hashlib.sha256(entry.read_bytes()).hexdigest()
            except Exception:
                pass
        return FileMetadata(
            path=rel_path,
            size=stat.st_size,
            etag=checksum or str(stat.st_mtime_ns),
            last_modified=stat.st_mtime,
            is_directory=entry.is_dir(),
            version=checksum,
            checksum=checksum,
        )

    def delete(self, path: str) -> bool:
        target = self._resolve(path)
        if not target.exists():
            return False
        if target.is_file():
            target.unlink()
        else:
            shutil.rmtree(str(target))
        logger.debug("LocalProvider: deleted %s", path)
        return True

    def move(self, from_path: str, to_path: str) -> bool:
        src = self._resolve(from_path)
        dst = self._resolve(to_path)
        if not src.exists():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.debug("LocalProvider: moved %s -> %s", from_path, to_path)
        return True

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def get_metadata(self, path: str) -> Dict[str, Any]:
        entry = self._resolve(path)
        if not entry.exists():
            return {}
        return self._metadata(entry, path).to_dict()


class CustomProvider(CloudProvider):
    """Provider that calls a custom HTTP/S server for sync operations.

    The server must implement the AetherOS sync REST API:
      - POST   /auth          authenticate
      - PUT    /<path>        upload
      - GET    /<path>        download
      - GET    /<path>/list   list directory
      - DELETE /<path>        delete
      - POST   /<path>/move   move
      - HEAD   /<path>        exists
      - GET    /<path>/meta   get_metadata
    """

    def __init__(self, config: SyncTransportConfig) -> None:
        super().__init__(config)
        self._http_client: Optional[Any] = None
        self._base_url = config.endpoint.rstrip("/")
        self._session_token: str = ""

    def _ensure_client(self) -> Any:
        if self._http_client is not None:
            return self._http_client
        try:
            import httpx
        except ImportError:
            raise RuntimeError(
                "httpx is required for CustomProvider. Install with: pip install httpx"
            )
        timeout = httpx.Timeout(
            self.config.read_timeout,
            connect=self.config.connect_timeout,
        )
        self._http_client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={"User-Agent": "AetherOS-Sync/1.0"},
        )
        return self._http_client

    def _headers(self) -> Dict[str, str]:
        h = {}
        if self._session_token:
            h["Authorization"] = f"Bearer {self._session_token}"
        return h

    def authenticate(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        creds = credentials or self.config.credentials
        client = self._ensure_client()
        try:
            resp = client.post("/auth", json=creds, headers=self._headers())
            if resp.is_success:
                data = resp.json()
                self._session_token = data.get("token", "")
                self._authenticated = True
                return True
            logger.warning("CustomProvider auth failed: %s", resp.status_code)
        except Exception as exc:
            logger.error("CustomProvider auth error: %s", exc)
        self._authenticated = False
        return False

    def upload(self, path: str, data: bytes) -> str:
        client = self._ensure_client()
        resp = with_retry(
            client.put,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}",
            content=data,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.headers.get("etag", resp.headers.get("x-amz-version-id", ""))

    def download(self, path: str) -> bytes:
        client = self._ensure_client()
        resp = with_retry(
            client.get,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.content

    def list(self, path: str) -> List[FileMetadata]:
        client = self._ensure_client()
        resp = with_retry(
            client.get,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}/list",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return [FileMetadata.from_dict(item) for item in resp.json()]

    def delete(self, path: str) -> bool:
        client = self._ensure_client()
        resp = with_retry(
            client.delete,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}",
            headers=self._headers(),
        )
        return resp.is_success

    def move(self, from_path: str, to_path: str) -> bool:
        client = self._ensure_client()
        resp = with_retry(
            client.request,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            method="POST",
            url=f"/{from_path.lstrip('/')}/move",
            json={"to": to_path},
            headers=self._headers(),
        )
        return resp.is_success

    def exists(self, path: str) -> bool:
        client = self._ensure_client()
        resp = with_retry(
            client.head,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}",
            headers=self._headers(),
        )
        return resp.is_success

    def get_metadata(self, path: str) -> Dict[str, Any]:
        client = self._ensure_client()
        resp = with_retry(
            client.get,
            max_retries=self.config.max_retries,
            backoff=self.config.retry_backoff,
            url=f"/{path.lstrip('/')}/meta",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def disconnect(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None
        self._authenticated = False
        self._session_token = ""


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """Registry of available :class:`CloudProvider` implementations.

    Providers are registered by type name and instantiated via :meth:`create`.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Type[CloudProvider]] = {}

    def register(self, type_name: str, provider_cls: Type[CloudProvider]) -> None:
        """Register a provider class under *type_name*.

        Args:
            type_name: The provider type identifier (e.g. ``"local"``,
                ``"custom"``, ``"s3"``).
            provider_cls: The :class:`CloudProvider` subclass to register.
        """
        with _PROVIDER_REGISTRY_LOCK:
            if type_name in self._providers:
                logger.warning(
                    "Overwriting registered provider '%s' (%s -> %s)",
                    type_name, self._providers[type_name].__name__,
                    provider_cls.__name__,
                )
            self._providers[type_name] = provider_cls
            logger.debug("Registered cloud provider: %s -> %s", type_name, provider_cls.__name__)

    def unregister(self, type_name: str) -> None:
        """Remove a previously registered provider."""
        with _PROVIDER_REGISTRY_LOCK:
            self._providers.pop(type_name, None)

    def get(self, type_name: str) -> Optional[Type[CloudProvider]]:
        """Return the provider class for *type_name*, or None."""
        with _PROVIDER_REGISTRY_LOCK:
            return self._providers.get(type_name)

    def list_types(self) -> List[str]:
        """Return all registered provider type names."""
        with _PROVIDER_REGISTRY_LOCK:
            return list(self._providers.keys())

    def create(self, type_name: str, config: SyncTransportConfig) -> CloudProvider:
        """Instantiate a provider by type name.

        Args:
            type_name: The registered provider type.
            config: Transport configuration for the new instance.

        Returns:
            A configured :class:`CloudProvider` instance.

        Raises:
            ValueError: If the provider type is not registered.
        """
        cls = self.get(type_name)
        if cls is None:
            raise ValueError(
                f"Unknown cloud provider type: '{type_name}'. "
                f"Available: {', '.join(self.list_types())}"
            )
        return cls(config)

    def create_from_config(self, config: SyncTransportConfig) -> CloudProvider:
        """Convenience method: create a provider from a transport config.

        Uses ``config.provider_type`` as the type name.
        """
        return self.create(config.provider_type, config)


# ---------------------------------------------------------------------------
# Global registry singleton
# ---------------------------------------------------------------------------

_default_registry = ProviderRegistry()
_default_registry.register("local", LocalProvider)
_default_registry.register("custom", CustomProvider)


def get_provider_registry() -> ProviderRegistry:
    """Return the global default :class:`ProviderRegistry` instance."""
    return _default_registry


def register_provider(type_name: str, provider_cls: Type[CloudProvider]) -> None:
    """Convenience: register a provider on the global registry."""
    _default_registry.register(type_name, provider_cls)


def create_provider(config: SyncTransportConfig) -> CloudProvider:
    """Convenience: create a provider from config via the global registry."""
    return _default_registry.create_from_config(config)
