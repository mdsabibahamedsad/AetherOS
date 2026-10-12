"""Task-scoped blackboard and versioned artifact store (P19-21).

The blackboard holds artifacts refs, verified facts, approved decisions and
warnings for ONE orchestration task. Cross-task reads require an explicit
share grant (P71-72); unrelated private memory is never attached here.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class ShareDenied(Exception):
    """P72 — cross-task read without an explicit grant."""


class SecretInArtifact(Exception):
    """P79 — artifact content looks like a credential."""


def _secret_scan(text: str) -> bool:
    try:
        from agent.memory_os.security import scan_secrets

        return scan_secrets(text) is not None
    except Exception:
        return False


@dataclass
class Artifact:
    """Versioned artifact with mandatory provenance (P20-21)."""

    artifact_id: str
    version: int
    kind: str                    # file|report|research|code|test_result|screenshot|data
    content: str                 # inline payload or path reference
    creator_agent: str
    task_id: str
    created_at: float
    parent_artifact: str = ""
    hash: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        content: str,
        creator_agent: str,
        task_id: str,
        parent_artifact: str = "",
        provenance: Optional[Dict[str, Any]] = None,
    ) -> "Artifact":
        return cls(
            artifact_id=uuid.uuid4().hex[:12],
            version=1,
            kind=kind,
            content=content,
            creator_agent=creator_agent,
            task_id=task_id,
            created_at=time.time(),
            parent_artifact=parent_artifact,
            hash=hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            provenance=dict(provenance or {}),
        )


class ArtifactStore:
    """In-memory index with optional JSON persistence per task."""

    def __init__(self, persist_dir: Optional[str] = None):
        self._artifacts: Dict[str, Artifact] = {}
        self.persist_dir = Path(persist_dir) if persist_dir else None
        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)

    def add(self, artifact: Artifact) -> Artifact:
        if _secret_scan(artifact.content):
            raise SecretInArtifact(
                "artifact content looks like a credential; refused (P79)"
            )
        # versioned child: bump parent instead of silently overwriting (P21)
        if artifact.parent_artifact:
            parent = self._artifacts.get(artifact.parent_artifact)
            if parent is not None:
                artifact.version = parent.version + 1
        self._artifacts[artifact.artifact_id] = artifact
        self._persist()
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def history(self, root_id: str) -> List[Artifact]:
        chain: List[Artifact] = []
        cur = self._artifacts.get(root_id)
        while cur is not None:
            chain.append(cur)
            cur = (
                self._artifacts.get(cur.parent_artifact)
                if cur.parent_artifact else None
            )
        return list(reversed(chain))

    def all_for_task(self, task_id: str) -> List[Artifact]:
        return [a for a in self._artifacts.values() if a.task_id == task_id]

    def _persist(self) -> None:
        if not self.persist_dir:
            return
        payload = {aid: vars(a) | {"provenance": a.provenance}
                   for aid, a in self._artifacts.items()}
        fd, tmp = tempfile.mkstemp(dir=str(self.persist_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, default=str)
            os.replace(tmp, self.persist_dir / "artifacts.json")
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass


class TaskBlackboard:
    """P19 — shared, task-scoped state. Everything written is DATA; nothing
    here can change orchestrator policy."""

    def __init__(self, task_id: str, store: Optional[ArtifactStore] = None):
        self.task_id = task_id
        self.artifacts = store or ArtifactStore()
        self.verified_facts: List[str] = []
        self.approved_decisions: List[str] = []
        self.warnings: List[str] = []
        self.status_notes: List[str] = []
        self._shares: set = set()   # other task ids granted READ access

    # -- writes ---------------------------------------------------------------

    def add_artifact(self, **kwargs) -> Artifact:
        kwargs.setdefault("task_id", self.task_id)
        return self.artifacts.add(Artifact.create(**kwargs))

    def add_verified_fact(self, fact: str, *, verified_by: str,
                          evidence_artifact: str = "") -> None:
        entry = f"{fact} [verified_by={verified_by}"
        if evidence_artifact:
            entry += f" evidence={evidence_artifact}"
        self.verified_facts.append(entry + "]")

    def add_approved_decision(self, decision: str, *, approved_by: str) -> None:
        self.approved_decisions.append(f"{decision} [approved_by={approved_by}]")

    def add_warning(self, warning: str, *, source_agent: str = "") -> None:
        prefix = f"[{source_agent}] " if source_agent else ""
        self.warnings.append(prefix + warning)

    # -- isolation / sharing (P71-72) ------------------------------------------

    def grant_share(self, other_task_id: str) -> None:
        self._shares.add(other_task_id)

    def revoke_share(self, other_task_id: str) -> None:
        self._shares.discard(other_task_id)

    def export_for_task(self, requesting_task_id: str) -> Dict[str, Any]:
        """Cross-task view: only with an explicit grant; own task sees all."""
        if requesting_task_id != self.task_id and \
                requesting_task_id not in self._shares:
            raise ShareDenied(
                f"task {requesting_task_id} has no share grant on {self.task_id}"
            )
        return {
            "task_id": self.task_id,
            "verified_facts": list(self.verified_facts),
            "approved_decisions": list(self.approved_decisions),
            "warnings": list(self.warnings),
            "status_notes": list(self.status_notes),
            "artifact_ids": [a.artifact_id
                             for a in self.artifacts.all_for_task(self.task_id)],
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "verified_facts": list(self.verified_facts),
            "approved_decisions": list(self.approved_decisions),
            "warnings": list(self.warnings),
            "status_notes": list(self.status_notes),
            "artifact_count": len(self.artifacts.all_for_task(self.task_id)),
        }
