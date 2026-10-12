"""
Artifact Manager — manages artifacts as first-class kernel objects.

Artifacts have metadata, versioning, provenance, and verification.
"""

from __future__ import annotations

import logging
import threading
import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, BinaryIO
from collections import defaultdict
from pathlib import Path
from enum import Enum

from kernel.core.types import (
    ProvenanceType,
    DataClassification,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


class ArtifactType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    MODEL_OUTPUT = "model_output"
    TOOL_RESULT = "tool_result"
    RESEARCH_REPORT = "research_report"
    CODE = "code"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DATASET = "dataset"
    LOG = "log"
    CHECKPOINT = "checkpoint"
    SNAPSHOT = "snapshot"
    CUSTOM = "custom"


@dataclass
class Artifact:
    """An artifact with full metadata."""
    artifact_id: str
    task_id: str
    agent_id: str
    creator: str  # agent, tool, model, human, system
    name: str
    artifact_type: ArtifactType
    content_type: str  # MIME type
    hash: str  # SHA256
    size: int  # bytes
    classification: DataClassification = DataClassification.INTERNAL
    provenance: ProvenanceType = ProvenanceType.TOOL_RETURNED
    created_at: float = field(default_factory=_now)
    modified_at: float = field(default_factory=_now)
    dependencies: List[str] = field(default_factory=list)  # Other artifact IDs
    version: int = 1
    parent_artifact_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    signature: str = ""  # Cryptographic signature
    storage_path: str = ""


@dataclass
class ArtifactVersion:
    """A version of an artifact."""
    version: int
    artifact_id: str
    hash: str
    size: int
    created_at: float
    created_by: str
    changelog: str = ""


class ArtifactManager:
    """
    Manages artifacts as first-class kernel objects.
    
    Supports create, read, modify, version, diff, share, quarantine, verify, delete, export.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Storage
        self.artifact_dir = Path(config.artifact_dir or "~/.aetheros/artifacts").expanduser() if hasattr(config, 'artifact_dir') else Path("~/.aetheros/artifacts").expanduser()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Registry
        self._artifacts: Dict[str, Artifact] = {}
        self._versions: Dict[str, List[ArtifactVersion]] = defaultdict(list)
        self._task_artifacts: Dict[str, List[str]] = defaultdict(list)  # task_id -> artifact_ids
        self._agent_artifacts: Dict[str, List[str]] = defaultdict(list)  # agent_id -> artifact_ids
        
        # Quarantine
        self._quarantined: Set[str] = set()

    def create_artifact(
        self,
        task_id: str,
        agent_id: str,
        creator: str,
        name: str,
        artifact_type: ArtifactType,
        content: bytes,
        content_type: str = "application/octet-stream",
        classification: DataClassification = DataClassification.INTERNAL,
        provenance: ProvenanceType = ProvenanceType.TOOL_RETURNED,
        dependencies: List[str] = None,
        parent_artifact_id: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Artifact:
        """Create a new artifact."""
        # Compute hash
        content_hash = hashlib.sha256(content).hexdigest()
        size = len(content)
        
        # Store content
        artifact_id = new_id("art")
        storage_path = self.artifact_dir / f"{artifact_id}.bin"
        with open(storage_path, 'wb') as f:
            f.write(content)
        
        artifact = Artifact(
            artifact_id=artifact_id,
            task_id=task_id,
            agent_id=agent_id,
            creator=creator,
            name=name,
            artifact_type=artifact_type,
            content_type=content_type,
            hash=content_hash,
            size=size,
            classification=classification,
            provenance=provenance,
            dependencies=dependencies or [],
            parent_artifact_id=parent_artifact_id,
            tags=tags or [],
            metadata=metadata or {},
            storage_path=str(storage_path),
        )
        
        # Record version
        version = ArtifactVersion(
            version=1,
            artifact_id=artifact_id,
            hash=content_hash,
            size=size,
            created_at=_now(),
            created_by=creator,
            changelog="Initial creation",
        )
        
        with self._lock:
            self._artifacts[artifact_id] = artifact
            self._versions[artifact_id].append(version)
            self._task_artifacts[task_id].append(artifact_id)
            self._agent_artifacts[agent_id].append(artifact_id)

        if self.event_bus:
            self.event_bus.emit("artifact.created", {
                "artifact_id": artifact_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "name": name,
                "type": artifact_type.value,
                "size": size,
            })

        logger.debug("ArtifactManager: created artifact %s (%s, %d bytes)", artifact_id, name, size)
        return artifact

    def read_artifact(self, artifact_id: str) -> Optional[bytes]:
        """Read artifact content."""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None
        
        if artifact_id in self._quarantined:
            logger.warning("Artifact %s is quarantined", artifact_id)
            return None
        
        try:
            with open(artifact.storage_path, 'rb') as f:
                return f.read()
        except Exception as exc:
            logger.error("Failed to read artifact %s: %s", artifact_id, exc)
            return None

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact metadata."""
        with self._lock:
            return self._artifacts.get(artifact_id)

    def update_artifact(
        self,
        artifact_id: str,
        content: bytes = None,
        name: str = None,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
        changelog: str = "",
    ) -> Optional[Artifact]:
        """Update an artifact (creates new version)."""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None
        
        if artifact_id in self._quarantined:
            logger.warning("Cannot update quarantined artifact %s", artifact_id)
            return None

        old_hash = artifact.hash
        old_size = artifact.size
        
        if content is not None:
            # Compute new hash
            content_hash = hashlib.sha256(content).hexdigest()
            size = len(content)
            
            # Store new content (versioned)
            version_path = self.artifact_dir / f"{artifact_id}_v{artifact.version + 1}.bin"
            with open(version_path, 'wb') as f:
                f.write(content)
            
            artifact.hash = content_hash
            artifact.size = size
            artifact.storage_path = str(version_path)
            artifact.modified_at = _now()
            artifact.version += 1
        
        if name:
            artifact.name = name
        if metadata:
            artifact.metadata.update(metadata)
        if tags:
            artifact.tags.extend(t for t in tags if t not in artifact.tags)
        
        # Record version
        version = ArtifactVersion(
            version=artifact.version,
            artifact_id=artifact_id,
            hash=artifact.hash,
            size=artifact.size,
            created_at=_now(),
            created_by=artifact.creator,
            changelog=changelog or f"Updated from v{artifact.version - 1}",
        )
        
        with self._lock:
            self._versions[artifact_id].append(version)

        if self.event_bus:
            self.event_bus.emit("artifact.updated", {
                "artifact_id": artifact_id,
                "version": artifact.version,
                "old_hash": old_hash,
                "new_hash": artifact.hash,
            })

        return artifact

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return False
        
        # Remove from storage
        try:
            Path(artifact.storage_path).unlink(missing_ok=True)
            # Also remove versioned files
            for v in self._versions.get(artifact_id, []):
                version_path = self.artifact_dir / f"{artifact_id}_v{v.version}.bin"
                version_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("Failed to delete artifact files: %s", exc)

        with self._lock:
            self._artifacts.pop(artifact_id, None)
            self._versions.pop(artifact_id, None)
            self._quarantined.discard(artifact_id)
            
            # Remove from indexes
            for task_id, arts in self._task_artifacts.items():
                if artifact_id in arts:
                    arts.remove(artifact_id)
            for agent_id, arts in self._agent_artifacts.items():
                if artifact_id in arts:
                    arts.remove(artifact_id)

        if self.event_bus:
            self.event_bus.emit("artifact.deleted", {
                "artifact_id": artifact_id,
            })

        return True

    def get_versions(self, artifact_id: str) -> List[ArtifactVersion]:
        """Get all versions of an artifact."""
        with self._lock:
            return list(self._versions.get(artifact_id, []))

    def diff_artifacts(self, artifact_id1: str, artifact_id2: str) -> Dict[str, Any]:
        """Diff two artifacts."""
        art1 = self.get_artifact(artifact_id1)
        art2 = self.get_artifact(artifact_id2)
        
        if not art1 or not art2:
            return {"error": "Artifact not found"}
        
        content1 = self.read_artifact(artifact_id1)
        content2 = self.read_artifact(artifact_id2)
        
        if content1 is None or content2 is None:
            return {"error": "Could not read artifact content"}
        
        return {
            "artifact1": {"id": artifact_id1, "hash": art1.hash, "size": art1.size},
            "artifact2": {"id": artifact_id2, "hash": art2.hash, "size": art2.size},
            "hashes_match": art1.hash == art2.hash,
            "size_diff": art2.size - art1.size,
            "content_diff": self._compute_diff(content1, content2),
        }

    def _compute_diff(self, content1: bytes, content2: bytes) -> Dict[str, Any]:
        """Compute diff between two byte sequences."""
        # Simple diff - in practice would use difflib
        return {
            "identical": content1 == content2,
            "len1": len(content1),
            "len2": len(content2),
        }

    def quarantine_artifact(self, artifact_id: str, reason: str = "security") -> bool:
        """Quarantine an artifact."""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return False
        
        with self._lock:
            self._quarantined.add(artifact_id)
        
        if self.event_bus:
            self.event_bus.emit("artifact.quarantined", {
                "artifact_id": artifact_id,
                "reason": reason,
            })
        
        return True

    def release_quarantine(self, artifact_id: str) -> bool:
        """Release artifact from quarantine."""
        with self._lock:
            self._quarantined.discard(artifact_id)
        
        if self.event_bus:
            self.event_bus.emit("artifact.quarantine_released", {
                "artifact_id": artifact_id,
            })
        
        return True

    def verify_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """Verify artifact integrity."""
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return {"verified": False, "error": "Artifact not found"}
        
        content = self.read_artifact(artifact_id)
        if content is None:
            return {"verified": False, "error": "Could not read content"}
        
        computed_hash = hashlib.sha256(content).hexdigest()
        verified = computed_hash == artifact.hash
        
        result = {
            "verified": verified,
            "artifact_id": artifact_id,
            "expected_hash": artifact.hash,
            "computed_hash": computed_hash,
            "size": len(content),
        }
        
        artifact.verification = result
        
        return result

    def get_task_artifacts(self, task_id: str) -> List[Artifact]:
        """Get all artifacts for a task."""
        with self._lock:
            artifact_ids = self._task_artifacts.get(task_id, [])
            return [self._artifacts[aid] for aid in artifact_ids if aid in self._artifacts]

    def get_agent_artifacts(self, agent_id: str) -> List[Artifact]:
        """Get all artifacts for an agent."""
        with self._lock:
            artifact_ids = self._agent_artifacts.get(agent_id, [])
            return [self._artifacts[aid] for aid in artifact_ids if aid in self._artifacts]

    def list_artifacts(
        self,
        artifact_type: ArtifactType = None,
        classification: DataClassification = None,
        agent_id: str = "",
        task_id: str = "",
        limit: int = 100,
    ) -> List[Artifact]:
        """List artifacts with filters."""
        with self._lock:
            artifacts = list(self._artifacts.values())
        
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        if classification:
            artifacts = [a for a in artifacts if a.classification == classification]
        if agent_id:
            artifacts = [a for a in artifacts if a.agent_id == agent_id]
        if task_id:
            artifacts = [a for a in artifacts if a.task_id == task_id]
        
        artifacts.sort(key=lambda a: a.created_at, reverse=True)
        return artifacts[:limit]

    def export_artifact(self, artifact_id: str, export_path: Path) -> bool:
        """Export artifact to a file."""
        content = self.read_artifact(artifact_id)
        if content is None:
            return False
        
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return False
        
        try:
            export_path.write_bytes(content)
            # Also write metadata
            meta_path = export_path.with_suffix(export_path.suffix + ".meta.json")
            meta_path.write_text(json.dumps(artifact.__dict__, default=str, indent=2))
            return True
        except Exception as exc:
            logger.error("Failed to export artifact: %s", exc)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get artifact manager statistics."""
        with self._lock:
            total = len(self._artifacts)
            total_size = sum(a.size for a in self._artifacts.values())
            quarantined = len(self._quarantined)
            
            by_type: Dict[str, int] = {}
            by_classification: Dict[str, int] = {}
            for artifact in self._artifacts.values():
                by_type[artifact.artifact_type.value] = by_type.get(artifact.artifact_type.value, 0) + 1
                by_classification[artifact.classification.value] = by_classification.get(artifact.classification.value, 0) + 1

        return {
            "total_artifacts": total,
            "total_size_bytes": total_size,
            "quarantined": quarantined,
            "by_type": by_type,
            "by_classification": by_classification,
            "storage_path": str(self.artifact_dir),
        }

    def shutdown(self) -> None:
        """Shutdown the artifact manager."""
        logger.info("ArtifactManager: shutting down")
        with self._lock:
            self._artifacts.clear()
            self._versions.clear()
            self._task_artifacts.clear()
            self._agent_artifacts.clear()
            self._quarantined.clear()