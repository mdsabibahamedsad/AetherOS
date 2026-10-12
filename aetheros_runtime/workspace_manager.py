"""Workspace Manager — multiple workspaces, projects, profiles, pinned folders, templates.

Organizes the file system into structured workspaces and projects.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_runtime.workspace")


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    path: Path = Path.cwd()
    description: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        data = dict(data)
        data["path"] = Path(data.pop("path", "."))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Workspace:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default"
    root_path: Path = Path.cwd()
    projects: List[Project] = field(default_factory=list)
    pinned_folders: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_active: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    template: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": str(self.root_path),
            "projects": [p.to_dict() for p in self.projects],
            "pinned_folders": self.pinned_folders,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "settings": self.settings,
            "template": self.template,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        data = dict(data)
        data["root_path"] = Path(data.pop("root_path", "."))
        projects_data = data.pop("projects", [])
        ws = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        ws.projects = [Project.from_dict(p) for p in projects_data]
        return ws


class WorkspaceManager:
    """Manages multiple workspaces, projects, and pinned folders.

    Supports:
    - Multiple workspaces with independent project lists
    - Per-workspace pinned folders
    - Project CRUD
    - Templates for new projects
    - Persistence to JSON
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._workspaces: Dict[str, Workspace] = {}
        self._active_workspace_id: Optional[str] = None
        self._storage_dir = storage_dir

        self._create_default()

        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _create_default(self) -> None:
        ws = Workspace(name="Default", root_path=Path.cwd(), is_active=True)
        self._workspaces[ws.id] = ws
        self._active_workspace_id = ws.id

    # ------------------------------------------------------------------
    # Workspace CRUD
    # ------------------------------------------------------------------

    def create_workspace(self, name: str, root_path: Optional[Path] = None) -> Workspace:
        ws = Workspace(name=name, root_path=root_path or Path.cwd())
        with self._lock:
            self._workspaces[ws.id] = ws
        self._save()
        logger.info("Workspace created: %s", name)
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def get_active_workspace(self) -> Optional[Workspace]:
        with self._lock:
            if self._active_workspace_id:
                return self._workspaces.get(self._active_workspace_id)
            return None

    def set_active_workspace(self, workspace_id: str) -> bool:
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            for ws in self._workspaces.values():
                ws.is_active = False
            self._workspaces[workspace_id].is_active = True
            self._active_workspace_id = workspace_id
        self._save()
        return True

    def delete_workspace(self, workspace_id: str) -> bool:
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            del self._workspaces[workspace_id]
            if self._active_workspace_id == workspace_id:
                remaining = list(self._workspaces.keys())
                if remaining:
                    first = remaining[0]
                    self._workspaces[first].is_active = True
                    self._active_workspace_id = first
                else:
                    self._active_workspace_id = None
        self._save()
        return True

    def list_workspaces(self) -> List[Workspace]:
        with self._lock:
            return list(self._workspaces.values())

    def rename_workspace(self, workspace_id: str, name: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.name = name
            ws.updated_at = time.time()
        self._save()
        return True

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    def add_project(self, workspace_id: str, project: Project) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.projects.append(project)
            ws.updated_at = time.time()
        self._save()
        return True

    def remove_project(self, workspace_id: str, project_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.projects = [p for p in ws.projects if p.id != project_id]
            ws.updated_at = time.time()
        self._save()
        return True

    def get_project(self, workspace_id: str, project_id: str) -> Optional[Project]:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return None
            for p in ws.projects:
                if p.id == project_id:
                    return p
            return None

    def list_projects(self, workspace_id: Optional[str] = None) -> List[Project]:
        with self._lock:
            if workspace_id:
                ws = self._workspaces.get(workspace_id)
                return list(ws.projects) if ws else []
            all_projects = []
            for ws in self._workspaces.values():
                all_projects.extend(ws.projects)
            return all_projects

    def create_project(
        self, name: str, path: Optional[Path] = None,
        workspace_id: Optional[str] = None, description: str = "",
    ) -> Optional[Project]:
        target = workspace_id or self._active_workspace_id
        if not target:
            return None
        project = Project(name=name, path=path or Path.cwd(), description=description)
        if self.add_project(target, project):
            return project
        return None

    # ------------------------------------------------------------------
    # Pinned folders
    # ------------------------------------------------------------------

    def pin_folder(self, workspace_id: str, folder_path: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            if folder_path not in ws.pinned_folders:
                ws.pinned_folders.append(folder_path)
                ws.updated_at = time.time()
        self._save()
        return True

    def unpin_folder(self, workspace_id: str, folder_path: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            if folder_path in ws.pinned_folders:
                ws.pinned_folders.remove(folder_path)
                ws.updated_at = time.time()
        self._save()
        return True

    def get_pinned_folders(self, workspace_id: Optional[str] = None) -> List[str]:
        with self._lock:
            if workspace_id:
                ws = self._workspaces.get(workspace_id)
                return list(ws.pinned_folders) if ws else []
            active = self.get_active_workspace()
            return list(active.pinned_folders) if active else []

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def apply_template(self, workspace_id: str, template_name: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.template = template_name
            ws.updated_at = time.time()
        self._save()
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._storage_dir:
            return
        try:
            data = {
                "workspaces": {wid: ws.to_dict() for wid, ws in self._workspaces.items()},
                "active_workspace_id": self._active_workspace_id,
            }
            path = self._storage_dir / "workspaces.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save workspaces: %s", exc)

    def _load(self) -> None:
        if not self._storage_dir:
            return
        path = self._storage_dir / "workspaces.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._workspaces.clear()
            for wid, raw in data.get("workspaces", {}).items():
                self._workspaces[wid] = Workspace.from_dict(raw)
            self._active_workspace_id = data.get("active_workspace_id")
            logger.info("Loaded %d workspaces", len(self._workspaces))
        except Exception as exc:
            logger.warning("Failed to load workspaces: %s", exc)

    def health_check(self) -> bool:
        return len(self._workspaces) > 0

    def summary(self) -> str:
        with self._lock:
            total_projects = sum(len(ws.projects) for ws in self._workspaces.values())
            return f"Workspace Manager: {len(self._workspaces)} workspaces, {total_projects} projects"