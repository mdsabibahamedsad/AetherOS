"""
AetherOS Agent Hypervisor 1.0 — capsule filesystem virtualization (§17-§19).

Logical capsule filesystem::

    /
    ├── workspace/   (READ_WRITE)
    ├── scratch/     (TEMPORARY)
    ├── artifacts/   (ARTIFACT_MOUNT)
    ├── cache/       (TEMPORARY)
    ├── tmp/         (TEMPORARY)
    ├── memory/      (READ_WRITE)
    └── readonly/    (READ_ONLY)

The host filesystem is inaccessible unless explicitly mounted (§17); every
mount requires policy (§18); every access passes the path guard (§19).
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from kernel.core.hypervisor.guards import (
    PathEscapeError,
    validate_capsule_path,
    validate_mount_host_path,
)
from kernel.core.hypervisor.types import CapsuleMount, MountType

logger = logging.getLogger(__name__)

LOGICAL_DIRS = ("workspace", "scratch", "artifacts", "cache", "tmp",
                "memory", "readonly")


@dataclass
class MountRecord:
    mount: CapsuleMount
    resolved_host: str
    policy_version: str = "1.0"

    def to_dict(self) -> Dict[str, object]:
        d = self.mount.to_dict()
        d["resolved_host"] = self.resolved_host
        d["policy_version"] = self.policy_version
        return d


class CapsuleFilesystem:
    """Per-capsule virtual filesystem rooted at <base>/<capsule_id>/."""

    def __init__(self, capsule_id: str, base_dir: str,
                 mounts: List[CapsuleMount] | None = None,
                 policy_version: str = "1.0") -> None:
        self.capsule_id = capsule_id
        self.root = os.path.abspath(os.path.join(base_dir, capsule_id))
        self.policy_version = policy_version
        self._mounts: Dict[str, MountRecord] = {}
        for mount in mounts or []:
            self.add_mount(mount)

    # -- provisioning ----------------------------------------------------
    def provision(self) -> str:
        os.makedirs(self.root, exist_ok=True)
        for name in LOGICAL_DIRS:
            os.makedirs(os.path.join(self.root, name), exist_ok=True)
        return self.root

    def add_mount(self, mount: CapsuleMount) -> MountRecord:
        """Register a mount. Host sources are validated; policy recorded."""
        if mount.mount_type == MountType.SECRET_MOUNT:
            raise PathEscapeError("SECRET mounts resolve via SecretBroker, never as paths")
        if mount.host_path:
            host = validate_mount_host_path(mount.host_path)
        else:
            logical = (mount.capsule_path or f"/{mount.name}").lstrip("/").split("/")[0]
            host = os.path.join(self.root, logical)
        record = MountRecord(mount=mount, resolved_host=host,
                             policy_version=self.policy_version)
        key = (mount.capsule_path or f"/{mount.name}").rstrip("/") or "/"
        self._mounts[key] = record
        return record

    def list_mounts(self) -> List[MountRecord]:
        return list(self._mounts.values())

    # -- resolution ------------------------------------------------------
    def resolve(self, logical_path: str) -> str:
        """Resolve a capsule-logical path to a host path (guarded)."""
        if not logical_path.startswith("/"):
            logical_path = "/" + logical_path
        # Route through the longest matching mount prefix.
        for prefix in sorted(self._mounts, key=len, reverse=True):
            if logical_path == prefix or logical_path.startswith(prefix + "/"):
                record = self._mounts[prefix]
                rel = logical_path[len(prefix):].lstrip("/")
                return validate_capsule_path(record.resolved_host, rel or ".")
        # Default: resolve inside the capsule root (deny-by-default: the
        # root itself contains only capsule-private logical dirs).
        return validate_capsule_path(self.root, logical_path.lstrip("/"))

    def _writable_check(self, host_path: str) -> None:
        for prefix in sorted(self._mounts, key=len, reverse=True):
            record = self._mounts[prefix]
            rh = record.resolved_host
            if host_path == rh or host_path.startswith(rh + os.sep):
                if record.mount.read_only or record.mount.mount_type == MountType.READ_ONLY:
                    raise PathEscapeError(f"read-only mount: {prefix}")
                if record.mount.mount_type == MountType.ARTIFACT_MOUNT:
                    raise PathEscapeError(
                        f"artifact mount is append-only via ArtifactManager: {prefix}")
                return
        # Inside capsule-private root: writable.
        if host_path == self.root or host_path.startswith(self.root + os.sep):
            return
        raise PathEscapeError(f"no writable mount for path: {host_path!r}")

    # -- operations ------------------------------------------------------
    def read_bytes(self, logical_path: str) -> bytes:
        host = self.resolve(logical_path)
        with open(host, "rb") as fh:
            return fh.read()

    def write_bytes(self, logical_path: str, data: bytes) -> int:
        host = self.resolve(logical_path)
        self._writable_check(host)
        os.makedirs(os.path.dirname(host), exist_ok=True)
        with open(host, "wb") as fh:
            return fh.write(data)

    def copy_on_write(self, source_logical: str, dest_logical: str) -> str:
        """COPY_ON_WRITE: materialize a private copy before mutation (§18)."""
        src = self.resolve(source_logical)
        dst = self.resolve(dest_logical)
        self._writable_check(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return dst

    def metadata(self) -> Dict[str, object]:
        total = 0
        files = 0
        if os.path.isdir(self.root):
            for dirpath, _dirnames, filenames in os.walk(self.root):
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    try:
                        total += os.path.getsize(fp)
                        files += 1
                    except OSError:
                        continue
        return {
            "root": self.root,
            "bytes": total,
            "files": files,
            "mounts": [m.to_dict() for m in self.list_mounts()],
        }

    def destroy(self, *, preserve_artifacts_to: Optional[str] = None) -> Dict[str, object]:
        """Tear down capsule-private storage. Artifacts survive only via
        explicit export (§117: never delete persistent artifacts accidentally)."""
        meta = self.metadata()
        if preserve_artifacts_to:
            src = os.path.join(self.root, "artifacts")
            if os.path.isdir(src):
                os.makedirs(preserve_artifacts_to, exist_ok=True)
                for fn in os.listdir(src):
                    s = os.path.join(src, fn)
                    d = os.path.join(preserve_artifacts_to, fn)
                    if os.path.isfile(s) and not os.path.exists(d):
                        shutil.copy2(s, d)
        shutil.rmtree(self.root, ignore_errors=True)
        meta["destroyed"] = not os.path.exists(self.root)
        meta["artifacts_exported_to"] = preserve_artifacts_to or ""
        return meta


def capsule_base_dir(config: object) -> str:
    """Base directory for capsule roots (profile-aware via checkpoint_dir)."""
    base = getattr(config, "checkpoint_dir", None) or "~/.aetheros/capsules"
    path = os.path.abspath(os.path.expanduser(base))
    Path(path).mkdir(parents=True, exist_ok=True)
    return path
