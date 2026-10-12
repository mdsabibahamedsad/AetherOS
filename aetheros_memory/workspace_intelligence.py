"""Workspace Intelligence module.

Each workspace tracks goals, pinned documents, a knowledge base,
tasks, agents, and full memory across sessions.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_memory.workspace_intelligence")

try:
    from aetheros_memory.memory_manager import MemoryManager, MemoryCategory
except ImportError:
    MemoryManager = None
    MemoryCategory = None


@dataclass
class Goal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "active"
    priority: int = 3
    created_at: float = field(default_factory=time.time)
    due_date: Optional[float] = None
    progress: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "due_date": self.due_date,
            "progress": self.progress,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            workspace_id=data.get("workspace_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=data.get("status", "active"),
            priority=data.get("priority", 3),
            created_at=data.get("created_at", time.time()),
            due_date=data.get("due_date"),
            progress=data.get("progress", 0.0),
            tags=data.get("tags", []),
        )


@dataclass
class PinnedDocument:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = ""
    title: str = ""
    file_path: str = ""
    content_type: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    pinned_at: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "title": self.title,
            "file_path": self.file_path,
            "content_type": self.content_type,
            "content": self.content,
            "tags": self.tags,
            "pinned_at": self.pinned_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PinnedDocument":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            workspace_id=data.get("workspace_id", ""),
            title=data.get("title", ""),
            file_path=data.get("file_path", ""),
            content_type=data.get("content_type", ""),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            pinned_at=data.get("pinned_at", time.time()),
            notes=data.get("notes", ""),
        )


@dataclass
class WorkspaceKnowledge:
    id: str = ""
    goals: List[Goal] = field(default_factory=list)
    pinned_docs: List[PinnedDocument] = field(default_factory=list)
    knowledge_base: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goals": [g.to_dict() for g in self.goals],
            "pinned_docs": [d.to_dict() for d in self.pinned_docs],
            "knowledge_base": self.knowledge_base,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceKnowledge":
        return cls(
            id=data.get("id", ""),
            goals=[Goal.from_dict(g) for g in data.get("goals", [])],
            pinned_docs=[PinnedDocument.from_dict(d) for d in data.get("pinned_docs", [])],
            knowledge_base=data.get("knowledge_base", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class WorkspaceIntelligence:
    """Manages workspace-level goals, pinned documents, and knowledge base."""

    def __init__(self, storage_path: Optional[str] = None,
                 memory_manager: Optional[Any] = None):
        self._lock = threading.RLock()
        self._workspaces: Dict[str, WorkspaceKnowledge] = {}
        self._storage_path: Optional[str] = storage_path
        self._memory_manager = memory_manager

    def initialize_workspace(self, workspace_id: str) -> WorkspaceKnowledge:
        with self._lock:
            if workspace_id in self._workspaces:
                return self._workspaces[workspace_id]
            knowledge = WorkspaceKnowledge(id=workspace_id)
            self._workspaces[workspace_id] = knowledge
            logger.info("Initialized workspace: %s", workspace_id)
            return knowledge

    def get_knowledge(self, workspace_id: str) -> Optional[WorkspaceKnowledge]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def add_goal(self, workspace_id: str, title: str, description: str = "",
                 priority: int = 3, due_date: Optional[float] = None,
                 tags: Optional[List[str]] = None) -> Goal:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                knowledge = self.initialize_workspace(workspace_id)
            goal = Goal(
                workspace_id=workspace_id,
                title=title,
                description=description,
                priority=max(1, min(5, priority)),
                due_date=due_date,
                tags=tags or [],
            )
            knowledge.goals.append(goal)
            knowledge.updated_at = time.time()
            if self._memory_manager is not None:
                try:
                    self._memory_manager.remember(
                        f"goal:{goal.id}",
                        goal.to_dict(),
                        memory_type="workspace",
                    )
                except Exception:
                    pass
            return goal

    def update_goal(self, goal_id: str, status: Optional[str] = None,
                    progress: Optional[float] = None,
                    title: Optional[str] = None,
                    description: Optional[str] = None) -> Optional[Goal]:
        with self._lock:
            for knowledge in self._workspaces.values():
                for goal in knowledge.goals:
                    if goal.id == goal_id:
                        if status is not None:
                            goal.status = status
                        if progress is not None:
                            goal.progress = max(0.0, min(1.0, progress))
                        if title is not None:
                            goal.title = title
                        if description is not None:
                            goal.description = description
                        knowledge.updated_at = time.time()
                        return goal
            return None

    def get_goals(self, workspace_id: str,
                  status: Optional[str] = None) -> List[Goal]:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                return []
            if status:
                return [g for g in knowledge.goals if g.status == status]
            return list(knowledge.goals)

    def delete_goal(self, goal_id: str) -> bool:
        with self._lock:
            for knowledge in self._workspaces.values():
                for i, goal in enumerate(knowledge.goals):
                    if goal.id == goal_id:
                        knowledge.goals.pop(i)
                        knowledge.updated_at = time.time()
                        return True
            return False

    def pin_document(self, workspace_id: str, title: str,
                     file_path: str = "", content_type: str = "",
                     content: str = "", tags: Optional[List[str]] = None,
                     notes: str = "") -> PinnedDocument:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                knowledge = self.initialize_workspace(workspace_id)
            doc = PinnedDocument(
                workspace_id=workspace_id,
                title=title,
                file_path=file_path,
                content_type=content_type,
                content=content,
                tags=tags or [],
                notes=notes,
            )
            knowledge.pinned_docs.append(doc)
            knowledge.updated_at = time.time()
            return doc

    def unpin_document(self, doc_id: str) -> bool:
        with self._lock:
            for knowledge in self._workspaces.values():
                for i, doc in enumerate(knowledge.pinned_docs):
                    if doc.id == doc_id:
                        knowledge.pinned_docs.pop(i)
                        knowledge.updated_at = time.time()
                        return True
            return False

    def get_pinned_documents(self, workspace_id: str) -> List[PinnedDocument]:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                return []
            return list(knowledge.pinned_docs)

    def set_knowledge(self, workspace_id: str, key: str, value: str) -> bool:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                knowledge = self.initialize_workspace(workspace_id)
            knowledge.knowledge_base[key] = value
            knowledge.updated_at = time.time()
            return True

    def get_knowledge(self, workspace_id: str, key: str) -> Optional[str]:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                return None
            return knowledge.knowledge_base.get(key)

    def search_workspace(self, workspace_id: str,
                         query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                return {"goals": [], "docs": [], "knowledge": []}
            matched_goals = [
                g.to_dict() for g in knowledge.goals
                if query_lower in g.title.lower()
                or query_lower in g.description.lower()
                or any(query_lower in t.lower() for t in g.tags)
            ]
            matched_docs = [
                d.to_dict() for d in knowledge.pinned_docs
                if query_lower in d.title.lower()
                or query_lower in d.content.lower()
                or query_lower in d.notes.lower()
            ]
            matched_kb = [
                {"key": k, "value": v}
                for k, v in knowledge.knowledge_base.items()
                if query_lower in k.lower() or query_lower in v.lower()
            ]
            return {
                "goals": matched_goals,
                "docs": matched_docs,
                "knowledge": matched_kb,
            }

    def get_workspace_summary(self, workspace_id: str) -> str:
        with self._lock:
            knowledge = self._workspaces.get(workspace_id)
            if knowledge is None:
                return f"Workspace '{workspace_id}' not found."
            active_goals = [g for g in knowledge.goals if g.status == "active"]
            completed_goals = [g for g in knowledge.goals if g.status == "completed"]
            avg_progress = (sum(g.progress for g in active_goals) / len(active_goals)
                            if active_goals else 0.0)
            lines = [
                f"Workspace: {knowledge.id}",
                f"Created: {datetime.fromtimestamp(knowledge.created_at, tz=timezone.utc).isoformat()}",
                f"Goals: {len(knowledge.goals)} total, "
                f"{len(active_goals)} active, {len(completed_goals)} completed",
                f"Average progress: {avg_progress:.0%}",
                f"Pinned docs: {len(knowledge.pinned_docs)}",
                f"Knowledge entries: {len(knowledge.knowledge_base)}",
            ]
            if active_goals:
                lines.append("Active goals:")
                for g in sorted(active_goals, key=lambda x: x.priority, reverse=True):
                    lines.append(f"  [{g.priority}] {g.title} ({g.progress:.0%})")
            return "\n".join(lines)

    def delete_workspace(self, workspace_id: str) -> bool:
        with self._lock:
            if workspace_id in self._workspaces:
                del self._workspaces[workspace_id]
                return True
            return False

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_goals = 0
            total_docs = 0
            total_kb = 0
            status_counts: Dict[str, int] = {}
            for knowledge in self._workspaces.values():
                total_goals += len(knowledge.goals)
                total_docs += len(knowledge.pinned_docs)
                total_kb += len(knowledge.knowledge_base)
                for g in knowledge.goals:
                    status_counts[g.status] = status_counts.get(g.status, 0) + 1
            return {
                "total_workspaces": len(self._workspaces),
                "total_goals": total_goals,
                "total_pinned_docs": total_docs,
                "total_knowledge_entries": total_kb,
                "goals_by_status": status_counts,
                "storage_path": self._storage_path,
            }

    def persist(self) -> None:
        if self._storage_path:
            data = {wid: wk.to_dict() for wid, wk in self._workspaces.items()}
            Path(self._storage_path).write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8",
            )
            logger.info("WorkspaceIntelligence persisted to %s", self._storage_path)

    def load(self, filepath: Optional[str] = None) -> int:
        path = filepath or self._storage_path
        if path and Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            with self._lock:
                for wid, wk_data in data.items():
                    self._workspaces[wid] = WorkspaceKnowledge.from_dict(wk_data)
            return len(data)
        return 0