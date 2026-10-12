"""
Artifact Synchronizer — synchronizes generated artifacts across cluster nodes.

Handles synchronization of:
  - Patches and code changes
  - Reports and documentation
  - Logs and test results
  - Any generated files

Uses smart transfer decisions to avoid unnecessary data movement.
"""

from __future__ import annotations

import enum
import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class SyncDirection(enum.Enum):
    """Direction of artifact synchronization."""
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class SyncStrategy(enum.Enum):
    """Strategy for deciding what to sync."""
    ALL = "all"
    CHANGED_ONLY = "changed_only"
    SIZE_BASED = "size_based"
    MANIFEST_ONLY = "manifest_only"


@dataclass
class Artifact:
    """An artifact that can be synchronized between nodes.

    Attributes:
        path: Local path to the artifact
        size_bytes: File size in bytes
        checksum: SHA-256 checksum for change detection
        last_modified: Last modification time
        metadata: Additional metadata (tags, labels, etc.)
        sync: Whether this artifact should be synced
    """
    path: str = ""
    size_bytes: int = 0
    checksum: str = ""
    last_modified: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    sync: bool = True


class ArtifactSynchronizer:
    """Synchronizes artifacts across cluster nodes.

    Avoids unnecessary transfers by:
      1. Comparing checksums before transfer
      2. Only syncing changed files
      3. Skipping files above/below size thresholds
      4. Using manifest-based sync for large directories

    Usage:
        sync = ArtifactSynchronizer(event_bus)
        sync.sync_artifact(
            local_path="/tmp/output/report.md",
            remote_node="node-2",
            remote_path="/data/output/report.md",
        )
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        max_file_size_mb: int = 100,
        min_file_size_bytes: int = 1,
    ):
        self._event_bus = event_bus
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._min_file_size = min_file_size_bytes
        self._lock = threading.RLock()

        # Sync history: (local_path, remote_node) -> Artifact
        self._synced: Dict[tuple, Artifact] = {}
        self._sync_count = 0
        self._bytes_transferred = 0

        # Handlers for remote transfer
        self._transfer_handlers: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_max_file_size(self, size_mb: int) -> None:
        """Set the maximum file size for synchronization."""
        self._max_file_size = size_mb * 1024 * 1024

    def set_min_file_size(self, size_bytes: int) -> None:
        """Set the minimum file size for synchronization."""
        self._min_file_size = size_bytes

    # ------------------------------------------------------------------
    # Artifact management
    # ------------------------------------------------------------------

    def compute_artifact(self, path: str) -> Optional[Artifact]:
        """Compute artifact metadata from a local file path.

        Returns None if the file doesn't exist or exceeds size limits.
        """
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            return None

        stat = file_path.stat()
        if stat.st_size > self._max_file_size:
            logger.debug(
                "ArtifactSync: skipping %s (%d bytes exceeds max %d)",
                path, stat.st_size, self._max_file_size,
            )
            return None

        if stat.st_size < self._min_file_size:
            logger.debug(
                "ArtifactSync: skipping %s (%d bytes below min %d)",
                path, stat.st_size, self._min_file_size,
            )
            return None

        return Artifact(
            path=str(file_path.absolute()),
            size_bytes=stat.st_size,
            checksum=self._compute_checksum(path),
            last_modified=stat.st_mtime,
        )

    def _compute_checksum(self, path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        try:
            sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, OSError) as exc:
            logger.warning("ArtifactSync: checksum failed for %s: %s", path, exc)
            return ""

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------

    def sync_artifact(
        self,
        local_path: str,
        remote_node: str,
        remote_path: str,
        direction: SyncDirection = SyncDirection.PUSH,
        strategy: SyncStrategy = SyncStrategy.CHANGED_ONLY,
    ) -> bool:
        """Synchronize an artifact between local and remote nodes.

        Args:
            local_path: Path to the local artifact
            remote_node: Target remote node ID
            remote_path: Destination path on remote node
            direction: Sync direction
            strategy: Sync strategy

        Returns:
            True if sync was performed, False if skipped
        """
        artifact = self.compute_artifact(local_path)
        if artifact is None:
            return False

        # Check if we need to sync (change detection)
        if strategy == SyncStrategy.CHANGED_ONLY:
            key = (local_path, remote_node)
            with self._lock:
                previous = self._synced.get(key)

            if previous and previous.checksum == artifact.checksum:
                logger.debug(
                    "ArtifactSync: %s unchanged on %s, skipping",
                    local_path, remote_node[:8],
                )
                return False

        # Perform the transfer
        try:
            self._perform_transfer(
                local_path=local_path,
                remote_node=remote_node,
                remote_path=remote_path,
                direction=direction,
                artifact=artifact,
            )

            # Record sync
            key = (local_path, remote_node)
            with self._lock:
                self._synced[key] = artifact
                self._sync_count += 1
                self._bytes_transferred += artifact.size_bytes

            logger.info(
                "ArtifactSync: synced %s -> %s (%s, %d bytes)",
                local_path, remote_node[:8], remote_path, artifact.size_bytes,
            )

            if self._event_bus:
                self._event_bus.emit_async("cluster.artifact_synced", {
                    "local_path": local_path,
                    "remote_node": remote_node,
                    "remote_path": remote_path,
                    "size_bytes": artifact.size_bytes,
                    "direction": direction.value,
                })

            return True

        except Exception as exc:
            logger.error(
                "ArtifactSync: sync failed for %s -> %s: %s",
                local_path, remote_node[:8], exc,
            )
            return False

    def sync_directory(
        self,
        local_dir: str,
        remote_node: str,
        remote_dir: str,
        pattern: str = "*",
        recursive: bool = True,
        direction: SyncDirection = SyncDirection.PUSH,
    ) -> int:
        """Synchronize multiple artifacts from a directory.

        Args:
            local_dir: Local directory to sync
            remote_node: Target remote node ID
            remote_dir: Remote directory path
            pattern: Glob pattern for files to include
            recursive: Whether to recurse into subdirectories
            direction: Sync direction

        Returns:
            Number of artifacts synced
        """
        base_path = Path(local_dir)
        if not base_path.exists() or not base_path.is_dir():
            return 0

        if recursive:
            files = list(base_path.rglob(pattern))
        else:
            files = list(base_path.glob(pattern))

        synced = 0
        for file_path in files:
            if not file_path.is_file():
                continue

            local_file = str(file_path)
            relative = str(file_path.relative_to(base_path))
            remote_file = str(Path(remote_dir) / relative)

            if self.sync_artifact(local_file, remote_node, remote_file, direction):
                synced += 1

        return synced

    def _perform_transfer(
        self,
        local_path: str,
        remote_node: str,
        remote_path: str,
        direction: SyncDirection,
        artifact: Artifact,
    ) -> None:
        """Perform the actual file transfer.

        Uses registered transfer handlers if available, otherwise logs
        the transfer as a notification (for external sync tools like rsync).
        """
        with self._lock:
            handler = self._transfer_handlers.get(remote_node)

        if handler:
            handler(local_path, remote_node, remote_path, direction, artifact)
        else:
            # No handler registered — log the transfer request
            logger.info(
                "ArtifactSync: transfer request %s -> %s:%s (%s, %d bytes)",
                local_path, remote_node[:8], remote_path,
                artifact.checksum[:12], artifact.size_bytes,
            )

    def register_transfer_handler(
        self,
        node_id: str,
        handler: Any,
    ) -> None:
        """Register a custom transfer handler for a node.

        The handler should accept (local_path, remote_node, remote_path, direction, artifact).
        """
        with self._lock:
            self._transfer_handlers[node_id] = handler

    def unregister_transfer_handler(self, node_id: str) -> None:
        """Remove a transfer handler."""
        with self._lock:
            self._transfer_handlers.pop(node_id, None)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return artifact sync statistics."""
        with self._lock:
            return {
                "total_syncs": self._sync_count,
                "bytes_transferred": self._bytes_transferred,
                "tracked_artifacts": len(self._synced),
                "max_file_size_mb": self._max_file_size // (1024 * 1024),
            }
