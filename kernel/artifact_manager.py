"""
Artifact Manager — stores, versions, and retrieves artifacts produced by agents.

Every agent can produce artifacts including:
  - Code (source files, patches, scripts)
  - Reports (analysis, research findings, summaries)
  - Images (screenshots, diagrams, generated images)
  - Documents (markdown, JSON, YAML, configs)
  - Logs (execution traces, debug output)
  - Plans (task graphs, execution plans, schedules)
  - Summaries (conversation summaries, extractive summaries)

All artifacts are versioned, searchable, and retrievable by ID.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import mimetypes
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ArtifactType(enum.Enum):
    CODE = "code"
    REPORT = "report"
    IMAGE = "image"
    DOCUMENT = "document"
    LOG = "log"
    PLAN = "plan"
    SUMMARY = "summary"
    DATA = "data"
    CONFIG = "config"
    UNKNOWN = "unknown"


class ArtifactVisibility(enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    MISSION = "mission"
    PUBLIC = "public"


@dataclass
class ArtifactVersion:
    version: int = 1
    content_hash: str = ""
    content_size: int = 0
    created_at: float = field(default_factory=time.time)
    created_by: str = ""
    message: str = ""
    storage_path: str = ""


@dataclass
class Artifact:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    type: ArtifactType = ArtifactType.UNKNOWN
    mime_type: str = "text/plain"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    visibility: ArtifactVisibility = ArtifactVisibility.MISSION
    owner_agent_id: str = ""
    plan_id: str = ""
    task_id: str = ""
    mission_id: str = ""

    content: Optional[Any] = None
    content_path: Optional[str] = None
    content_size: int = 0

    versions: List[ArtifactVersion] = field(default_factory=list)
    current_version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    checksum: str = ""


class ArtifactManager:
    """Central artifact storage and versioning system.

    Every artifact is stored with full version history, searchable
    by metadata, tags, content, and relationships.

    Usage:
        artifacts = ArtifactManager(storage_dir="/tmp/artifacts", event_bus=bus)

        # Store an artifact
        art = artifacts.store(
            name="build-script.py",
            content=code_string,
            type=ArtifactType.CODE,
            owner_agent_id="agent-1",
            tags=["python", "build"],
        )

        # Retrieve
        retrieved = artifacts.get(art.id)
        content = retrieved.content

        # List by mission
        mission_artifacts = artifacts.list_by_mission(mission_id="mission-123")
    """

    def __init__(self, storage_dir: Optional[str] = None,
                 event_bus: Optional[EventBus] = None,
                 max_versions_per_artifact: int = 50):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._artifacts: Dict[str, Artifact] = {}
        self._index_by_agent: Dict[str, Set[str]] = {}
        self._index_by_mission: Dict[str, Set[str]] = {}
        self._index_by_plan: Dict[str, Set[str]] = {}
        self._index_by_type: Dict[str, Set[str]] = {}
        self._index_by_tag: Dict[str, Set[str]] = {}
        self._max_versions = max_versions_per_artifact

        self._storage_dir = storage_dir
        self._total_storage_bytes = 0

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(self, name: str, content: Any,
              type: ArtifactType = ArtifactType.UNKNOWN,
              owner_agent_id: str = "",
              plan_id: str = "",
              task_id: str = "",
              mission_id: str = "",
              tags: List[str] = None,
              description: str = "",
              visibility: ArtifactVisibility = ArtifactVisibility.MISSION,
              mime_type: str = "",
              metadata: Dict[str, Any] = None,
              dependencies: List[str] = None,
              version_message: str = "") -> Artifact:
        tags = tags or []
        metadata = metadata or {}
        mime_type = mime_type or self._detect_mime_type(name, content)
        content_bytes = self._serialize_content(content)
        content_hash = hashlib.sha256(content_bytes).hexdigest()[:16]

        with self._lock:
            artifact = Artifact(
                name=name,
                type=type,
                mime_type=mime_type,
                description=description,
                tags=tags,
                visibility=visibility,
                owner_agent_id=owner_agent_id,
                plan_id=plan_id,
                task_id=task_id,
                mission_id=mission_id,
                content=content,
                content_size=len(content_bytes),
                current_version=1,
                checksum=content_hash,
                metadata=metadata,
                dependencies=dependencies or [],
            )

            version = ArtifactVersion(
                version=1,
                content_hash=content_hash,
                content_size=len(content_bytes),
                created_by=owner_agent_id,
                message=version_message or "Initial version",
            )

            if self._storage_dir:
                storage_path = self._save_to_disk(artifact.id, 1, content_bytes)
                version.storage_path = storage_path
                artifact.content_path = storage_path

            artifact.versions.append(version)
            self._artifacts[artifact.id] = artifact
            self._index(artifact)

        self._total_storage_bytes += len(content_bytes)

        if self._event_bus:
            self._event_bus.emit_async("artifact.stored", {
                "artifact_id": artifact.id,
                "name": name,
                "type": type.value,
                "owner": owner_agent_id,
                "size": len(content_bytes),
                "version": 1,
            })

        logger.info("ArtifactManager: stored '%s' (%s, %d bytes, v1)",
                     name, type.value, len(content_bytes))
        return artifact

    def update(self, artifact_id: str, content: Any,
               owner_agent_id: str = "",
               version_message: str = "",
               metadata: Dict[str, Any] = None) -> Optional[Artifact]:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if artifact is None:
                return None

            content_bytes = self._serialize_content(content)
            content_hash = hashlib.sha256(content_bytes).hexdigest()[:16]

            new_version = artifact.current_version + 1

            version = ArtifactVersion(
                version=new_version,
                content_hash=content_hash,
                content_size=len(content_bytes),
                created_by=owner_agent_id or artifact.owner_agent_id,
                message=version_message or f"Version {new_version}",
            )

            if self._storage_dir:
                storage_path = self._save_to_disk(artifact.id, new_version, content_bytes)
                version.storage_path = storage_path
                artifact.content_path = storage_path

            artifact.versions.append(version)
            if len(artifact.versions) > self._max_versions:
                artifact.versions = artifact.versions[-self._max_versions:]

            artifact.content = content
            artifact.content_size = len(content_bytes)
            artifact.current_version = new_version
            artifact.checksum = content_hash
            artifact.updated_at = time.time()
            if metadata:
                artifact.metadata.update(metadata)

        self._total_storage_bytes += len(content_bytes)

        if self._event_bus:
            self._event_bus.emit_async("artifact.updated", {
                "artifact_id": artifact_id,
                "version": new_version,
                "owner": owner_agent_id,
            })

        logger.info("ArtifactManager: updated '%s' to v%d (%d bytes)",
                     artifact.name, new_version, len(content_bytes))
        return artifact

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def get(self, artifact_id: str, version: int = 0) -> Optional[Artifact]:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if artifact is None:
                return None
            if version > 0 and version != artifact.current_version:
                artifact = self._get_version_snapshot(artifact, version)
            return artifact

    def get_content(self, artifact_id: str, version: int = 0) -> Optional[Any]:
        artifact = self.get(artifact_id, version)
        if artifact is None:
            return None
        if artifact.content is not None:
            return artifact.content
        if artifact.content_path and self._storage_dir:
            return self._load_from_disk(artifact.content_path)
        return None

    def get_version(self, artifact_id: str,
                    version_number: int) -> Optional[ArtifactVersion]:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if artifact is None:
                return None
            for v in artifact.versions:
                if v.version == version_number:
                    return v
        return None

    def _get_version_snapshot(self, artifact: Artifact,
                              version: int) -> Artifact:
        import copy
        snapshot = copy.deepcopy(artifact)
        for v in artifact.versions:
            if v.version == version:
                snapshot.content_hash = v.content_hash
                snapshot.content_size = v.content_size
                snapshot.content_path = v.storage_path
                break
        snapshot.content = None
        if snapshot.content_path and self._storage_dir:
            try:
                snapshot.content = self._load_from_disk(snapshot.content_path)
            except Exception:
                pass
        return snapshot

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete(self, artifact_id: str) -> bool:
        with self._lock:
            artifact = self._artifacts.pop(artifact_id, None)
            if artifact is None:
                return False
            self._deindex(artifact)

        if self._storage_dir:
            self._clean_disk_artifact(artifact.id)

        if self._event_bus:
            self._event_bus.emit_async("artifact.deleted", {
                "artifact_id": artifact_id,
            })

        logger.info("ArtifactManager: deleted '%s'", artifact.name)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def find(self, name: str = "", type: ArtifactType = None,
             owner: str = "", tags: List[str] = None,
             mission_id: str = "", plan_id: str = "",
             limit: int = 100) -> List[Artifact]:
        with self._lock:
            artifacts = list(self._artifacts.values())

        if name:
            artifacts = [a for a in artifacts if name.lower() in a.name.lower()]
        if type:
            artifacts = [a for a in artifacts if a.type == type]
        if owner:
            artifacts = [a for a in artifacts if a.owner_agent_id == owner]
        if tags:
            artifacts = [a for a in artifacts if any(t in a.tags for t in tags)]
        if mission_id:
            artifacts = [a for a in artifacts if a.mission_id == mission_id]
        if plan_id:
            artifacts = [a for a in artifacts if a.plan_id == plan_id]

        artifacts.sort(key=lambda a: a.updated_at, reverse=True)
        return artifacts[:limit]

    def list_by_agent(self, agent_id: str) -> List[Artifact]:
        with self._lock:
            ids = self._index_by_agent.get(agent_id, set())
            return sorted(
                [self._artifacts[a] for a in ids if a in self._artifacts],
                key=lambda a: a.updated_at, reverse=True,
            )

    def list_by_mission(self, mission_id: str) -> List[Artifact]:
        with self._lock:
            ids = self._index_by_mission.get(mission_id, set())
            return sorted(
                [self._artifacts[a] for a in ids if a in self._artifacts],
                key=lambda a: a.updated_at, reverse=True,
            )

    def list_by_plan(self, plan_id: str) -> List[Artifact]:
        with self._lock:
            ids = self._index_by_plan.get(plan_id, set())
            return sorted(
                [self._artifacts[a] for a in ids if a in self._artifacts],
                key=lambda a: a.updated_at, reverse=True,
            )

    def list_by_type(self, type: ArtifactType) -> List[Artifact]:
        with self._lock:
            ids = self._index_by_type.get(type.value, set())
            return sorted(
                [self._artifacts[a] for a in ids if a in self._artifacts],
                key=lambda a: a.updated_at, reverse=True,
            )

    def search_tags(self, tags: List[str]) -> List[Artifact]:
        with self._lock:
            results = set()
            for tag in tags:
                ids = self._index_by_tag.get(tag.lower(), set())
                results.update(ids)
            return sorted(
                [self._artifacts[a] for a in results if a in self._artifacts],
                key=lambda a: a.updated_at, reverse=True,
            )

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _index(self, artifact: Artifact) -> None:
        self._index_by_agent.setdefault(artifact.owner_agent_id, set()).add(artifact.id)
        if artifact.mission_id:
            self._index_by_mission.setdefault(artifact.mission_id, set()).add(artifact.id)
        if artifact.plan_id:
            self._index_by_plan.setdefault(artifact.plan_id, set()).add(artifact.id)
        self._index_by_type.setdefault(artifact.type.value, set()).add(artifact.id)
        for tag in artifact.tags:
            self._index_by_tag.setdefault(tag.lower(), set()).add(artifact.id)

    def _deindex(self, artifact: Artifact) -> None:
        for idx in (self._index_by_agent.get(artifact.owner_agent_id, set()),
                    self._index_by_mission.get(artifact.mission_id, set()),
                    self._index_by_plan.get(artifact.plan_id, set()),
                    self._index_by_type.get(artifact.type.value, set())):
            idx.discard(artifact.id)
        for tag in artifact.tags:
            self._index_by_tag.get(tag.lower(), set()).discard(artifact.id)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_to_disk(self, artifact_id: str, version: int,
                      content: bytes) -> str:
        if not self._storage_dir:
            return ""
        artifact_dir = Path(self._storage_dir) / artifact_id[:2] / artifact_id[2:4] / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        file_path = artifact_dir / f"v{version}"
        file_path.write_bytes(content)
        return str(file_path)

    def _load_from_disk(self, path: str) -> Any:
        data = Path(path).read_bytes()
        try:
            return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return data

    def _clean_disk_artifact(self, artifact_id: str) -> None:
        if not self._storage_dir:
            return
        artifact_dir = Path(self._storage_dir) / artifact_id[:2] / artifact_id[2:4] / artifact_id
        import shutil
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_content(content: Any) -> bytes:
        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode("utf-8")
        try:
            return json.dumps(content, indent=2, default=str).encode("utf-8")
        except (TypeError, ValueError):
            return str(content).encode("utf-8")

    @staticmethod
    def _detect_mime_type(name: str, content: Any) -> str:
        if name:
            mime, _ = mimetypes.guess_type(name)
            if mime:
                return mime
        if isinstance(content, (dict, list)):
            return "application/json"
        if isinstance(content, str):
            if content.lstrip().startswith(("{", "[")):
                return "application/json"
            if content.lstrip().startswith(("#", "---")):
                return "text/markdown"
            if "<?xml" in content[:100]:
                return "application/xml"
            return "text/plain"
        if isinstance(content, bytes):
            return "application/octet-stream"
        return "text/plain"

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            type_counts: Dict[str, int] = {}
            for a in self._artifacts.values():
                type_counts[a.type.value] = type_counts.get(a.type.value, 0) + 1
            total_versions = sum(len(a.versions) for a in self._artifacts.values())
        return {
            "total_artifacts": len(self._artifacts),
            "total_versions": total_versions,
            "total_storage_bytes": self._total_storage_bytes,
            "by_type": type_counts,
            "by_agent": {k: len(v) for k, v in self._index_by_agent.items()},
        }