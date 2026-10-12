"""
Artifact Manager — tracks all artifacts generated during engineering workflows.

Tracks:
  - Patches and diffs
  - Generated files
  - Reports (lint, test, analysis, review)
  - Logs
  - Design documents
  - Test results
  - Release bundles

Provides reproducible outputs with provenance tracking.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArtifactType(enum.Enum):
    """Types of artifacts that can be tracked."""
    PATCH = "patch"
    GENERATED_FILE = "generated_file"
    REPORT = "report"
    LOG = "log"
    DESIGN_DOCUMENT = "design_document"
    TEST_RESULT = "test_result"
    RELEASE_BUNDLE = "release_bundle"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    DIAGRAM = "diagram"
    ANALYSIS = "analysis"
    REVIEW = "review"
    SPECIFICATION = "specification"
    ARCHITECTURE = "architecture"
    PLAN = "plan"


@dataclass
class ArtifactEntry:
    """A single tracked artifact.

    Attributes:
        id: Unique artifact ID
        type: Type of artifact
        name: Human-readable name
        description: Optional description
        file_path: Path to the artifact file on disk
        workflow_id: ID of the workflow that produced this artifact
        task_id: ID of the task that produced this artifact
        created_at: When the artifact was created
        size_bytes: File size in bytes
        checksum: SHA-256 checksum of the file content
        metadata: Additional metadata
        tags: Tags for categorization and search
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: ArtifactType = ArtifactType.REPORT
    name: str = ""
    description: str = ""
    file_path: str = ""
    workflow_id: str = ""
    task_id: str = ""
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class ArtifactCollection:
    """A collection of related artifacts (e.g. all artifacts from one workflow).

    Attributes:
        id: Unique collection ID
        name: Collection name
        description: Optional description
        artifacts: List of artifact entries
        created_at: When the collection was created
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    artifacts: List[ArtifactEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ArtifactManager:
    """Manages artifacts produced by engineering workflows.

    Provides storage, retrieval, and provenance tracking for all
    artifacts generated during the engineering lifecycle.

    Usage:
        manager = ArtifactManager(base_dir=Path("./artifacts"))
        entry = manager.register(
            type=ArtifactType.REPORT,
            name="lint-results.json",
            file_path="/tmp/lint-results.json",
            workflow_id="wf-123",
        )
        col = manager.get_workflow_artifacts("wf-123")
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = base_dir or Path.cwd() / ".aetheros" / "engineering" / "artifacts"
        self._artifacts: Dict[str, ArtifactEntry] = {}
        self._collections: Dict[str, ArtifactCollection] = {}
        self._index_file = self._base_dir / "artifact_index.json"

        # Create base directory if it doesn't exist
        self._base_dir.mkdir(parents=True, exist_ok=True)

        # Load existing index
        self._load_index()

    def _load_index(self) -> None:
        """Load artifact index from disk."""
        if self._index_file.exists():
            try:
                data = json.loads(self._index_file.read_text(encoding="utf-8"))
                artifacts_data = data.get("artifacts", {})
                for aid, entry in artifacts_data.items():
                    entry["type"] = ArtifactType(entry["type"])
                    self._artifacts[aid] = ArtifactEntry(**entry)
                collections_data = data.get("collections", {})
                for cid, col_data in collections_data.items():
                    # Reconstruct artifact references
                    artifact_ids = col_data.pop("artifact_ids", [])
                    col = ArtifactCollection(**col_data)
                    col.artifacts = [
                        self._artifacts[aid] for aid in artifact_ids
                        if aid in self._artifacts
                    ]
                    self._collections[cid] = col
                logger.debug(
                    "ArtifactManager: loaded %d artifacts, %d collections",
                    len(self._artifacts), len(self._collections),
                )
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("ArtifactManager: failed to load index: %s", exc)

    def _save_index(self) -> None:
        """Persist artifact index to disk."""
        try:
            data = {
                "artifacts": {
                    aid: {
                        **{k: v for k, v in entry.__dict__.items() if k != "type"},
                        "type": entry.type.value,
                    }
                    for aid, entry in self._artifacts.items()
                },
                "collections": {
                    cid: {
                        **{k: v for k, v in col.__dict__.items() if k != "artifacts"},
                        "artifact_ids": [a.id for a in col.artifacts],
                    }
                    for cid, col in self._collections.items()
                },
            }
            self._index_file.parent.mkdir(parents=True, exist_ok=True)
            self._index_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.error("ArtifactManager: failed to save index: %s", exc)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, type: ArtifactType, name: str,
                 file_path: str = "",
                 description: str = "",
                 workflow_id: str = "",
                 task_id: str = "",
                 metadata: Dict[str, Any] = None,
                 tags: List[str] = None) -> ArtifactEntry:
        """Register a new artifact.

        Args:
            type: Type of artifact
            name: Human-readable name
            file_path: Path to the artifact file
            description: Optional description
            workflow_id: ID of the producing workflow
            task_id: ID of the producing task
            metadata: Additional metadata
            tags: Tags for categorization

        Returns:
            The registered ArtifactEntry
        """
        size_bytes = 0
        checksum = ""
        if file_path:
            path_obj = Path(file_path)
            if path_obj.exists():
                size_bytes = path_obj.stat().st_size
                try:
                    import hashlib
                    checksum = hashlib.sha256(
                        path_obj.read_bytes()
                    ).hexdigest()[:16]
                except Exception:
                    pass

        entry = ArtifactEntry(
            type=type,
            name=name,
            description=description,
            file_path=str(file_path),
            workflow_id=workflow_id,
            task_id=task_id,
            size_bytes=size_bytes,
            checksum=checksum,
            metadata=metadata or {},
            tags=tags or [],
        )

        self._artifacts[entry.id] = entry

        # Auto-add to collection if workflow_id is provided
        if workflow_id:
            col = self._collections.get(workflow_id)
            if col is None:
                col = ArtifactCollection(
                    id=workflow_id,
                    name=f"Workflow {workflow_id[:12]}",
                )
                self._collections[workflow_id] = col
            col.artifacts.append(entry)

        self._save_index()

        logger.debug(
            "ArtifactManager: registered %s '%s' (%s)",
            type.value, name, file_path or "(no file)",
        )
        return entry

    def get(self, artifact_id: str) -> Optional[ArtifactEntry]:
        """Get an artifact by ID."""
        return self._artifacts.get(artifact_id)

    def find(self, type: Optional[ArtifactType] = None,
             workflow_id: Optional[str] = None,
             tags: Optional[List[str]] = None,
             name_contains: Optional[str] = None) -> List[ArtifactEntry]:
        """Find artifacts matching the given criteria.

        Args:
            type: Filter by artifact type
            workflow_id: Filter by workflow ID
            tags: Filter by tags (must match all)
            name_contains: Filter by name substring

        Returns:
            List of matching artifact entries
        """
        results = list(self._artifacts.values())

        if type:
            results = [a for a in results if a.type == type]
        if workflow_id:
            results = [a for a in results if a.workflow_id == workflow_id]
        if tags:
            results = [
                a for a in results
                if all(tag in a.tags for tag in tags)
            ]
        if name_contains:
            results = [
                a for a in results if name_contains.lower() in a.name.lower()
            ]

        results.sort(key=lambda a: a.created_at, reverse=True)
        return results

    def store_file(self, artifact_id: str, content: str,
                   extension: str = ".txt") -> Optional[Path]:
        """Store content as a file artifact.

        Args:
            artifact_id: ID of the artifact
            content: Content to store
            extension: File extension (e.g. ".json", ".md", ".txt")

        Returns:
            Path to the stored file, or None if artifact not found
        """
        entry = self._artifacts.get(artifact_id)
        if entry is None:
            logger.warning("ArtifactManager: artifact %s not found", artifact_id)
            return None

        filename = f"{entry.id}_{entry.name}{extension}"
        file_path = self._base_dir / filename

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        entry.file_path = str(file_path)
        entry.size_bytes = file_path.stat().st_size

        import hashlib
        entry.checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        self._save_index()
        return file_path

    def read_content(self, artifact_id: str) -> Optional[str]:
        """Read the content of a stored artifact file.

        Args:
            artifact_id: ID of the artifact

        Returns:
            File content as string, or None if not found or no file
        """
        entry = self._artifacts.get(artifact_id)
        if entry is None or not entry.file_path:
            return None

        path = Path(entry.file_path)
        if path.exists():
            return path.read_text(encoding="utf-8")

        return None

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def create_collection(self, name: str, description: str = "",
                          artifact_ids: List[str] = None) -> ArtifactCollection:
        """Create a new artifact collection.

        Args:
            name: Collection name
            description: Optional description
            artifact_ids: Initial artifact IDs to include

        Returns:
            The created ArtifactCollection
        """
        collection = ArtifactCollection(
            name=name,
            description=description,
            artifacts=[
                self._artifacts[aid] for aid in (artifact_ids or [])
                if aid in self._artifacts
            ],
        )
        self._collections[collection.id] = collection
        self._save_index()
        return collection

    def get_collection(self, collection_id: str) -> Optional[ArtifactCollection]:
        """Get a collection by ID."""
        return self._collections.get(collection_id)

    def get_workflow_artifacts(self, workflow_id: str) -> List[ArtifactEntry]:
        """Get all artifacts for a given workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of artifact entries for the workflow
        """
        col = self._collections.get(workflow_id)
        if col:
            return list(col.artifacts)
        return self.find(workflow_id=workflow_id)

    def list_collections(self) -> List[ArtifactCollection]:
        """List all artifact collections."""
        return sorted(
            self._collections.values(),
            key=lambda c: c.created_at,
            reverse=True,
        )

    def add_to_collection(self, collection_id: str,
                          artifact_id: str) -> bool:
        """Add an artifact to a collection."""
        col = self._collections.get(collection_id)
        entry = self._artifacts.get(artifact_id)
        if col is None or entry is None:
            return False
        if entry not in col.artifacts:
            col.artifacts.append(entry)
            self._save_index()
        return True

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_manifest(self, collection_id: str,
                        format: str = "json") -> Optional[str]:
        """Export a collection manifest.

        Args:
            collection_id: Collection ID
            format: Export format ("json" or "markdown")

        Returns:
            The formatted manifest string, or None if collection not found
        """
        col = self._collections.get(collection_id)
        if col is None:
            return None

        if format == "json":
            return json.dumps({
                "collection": {
                    "id": col.id,
                    "name": col.name,
                    "created_at": datetime.fromtimestamp(col.created_at).isoformat(),
                    "artifact_count": len(col.artifacts),
                },
                "artifacts": [
                    {
                        "id": a.id,
                        "type": a.type.value,
                        "name": a.name,
                        "file_path": a.file_path,
                        "created_at": datetime.fromtimestamp(a.created_at).isoformat(),
                        "size_bytes": a.size_bytes,
                        "checksum": a.checksum,
                        "tags": a.tags,
                    }
                    for a in col.artifacts
                ],
            }, indent=2)

        elif format == "markdown":
            lines = [
                f"# Artifact Collection: {col.name}",
                f"",
                f"- **ID**: {col.id}",
                f"- **Created**: {datetime.fromtimestamp(col.created_at).isoformat()}",
                f"- **Artifacts**: {len(col.artifacts)}",
                f"",
                f"## Artifacts",
                f"",
                f"| ID | Type | Name | Size | Tags |",
                f"|----|------|------|------|------|",
            ]
            for a in col.artifacts:
                lines.append(
                    f"| {a.id[:8]} | {a.type.value} | {a.name} | "
                    f"{a.size_bytes}B | {', '.join(a.tags[:3])} |"
                )
            return "\n".join(lines)

        return None

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def purge(self, older_than_days: float = 30.0) -> int:
        """Remove artifacts older than the specified number of days.

        Args:
            older_than_days: Age threshold in days

        Returns:
            Number of artifacts removed
        """
        cutoff = time.time() - (older_than_days * 86400)
        to_remove = [
            aid for aid, entry in self._artifacts.items()
            if entry.created_at < cutoff
        ]

        for aid in to_remove:
            entry = self._artifacts.pop(aid, None)
            if entry and entry.file_path:
                try:
                    Path(entry.file_path).unlink(missing_ok=True)
                except Exception:
                    pass

        # Clean up empty collections
        for cid in list(self._collections.keys()):
            col = self._collections[cid]
            col.artifacts = [a for a in col.artifacts if a.id in self._artifacts]
            if not col.artifacts:
                del self._collections[cid]

        self._save_index()
        logger.info("ArtifactManager: purged %d artifacts older than %.0f days",
                     len(to_remove), older_than_days)
        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get artifact manager statistics."""
        by_type: Dict[str, int] = {}
        total_size = 0
        for entry in self._artifacts.values():
            by_type[entry.type.value] = by_type.get(entry.type.value, 0) + 1
            total_size += entry.size_bytes

        return {
            "total_artifacts": len(self._artifacts),
            "total_collections": len(self._collections),
            "by_type": by_type,
            "total_size_bytes": total_size,
            "base_directory": str(self._base_dir),
        }
