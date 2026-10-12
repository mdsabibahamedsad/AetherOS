from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class SpaceVisibility(str, Enum):
    PRIVATE = "private"
    SHARED_READ = "shared_read"
    SHARED_WRITE = "shared_write"
    PUBLIC = "public"


class SpaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class DataCategory(str, Enum):
    PERSONAL = "personal"
    WORK = "work"
    PROJECT = "project"
    ACCOUNT = "account"
    AGENT = "agent"
    ORGANIZATION = "organization"
    CLIENT = "client"
    RESEARCH = "research"


@dataclass
class KnowledgeSpace:
    id: str
    name: str
    description: str = ""
    icon: str = ""
    color: str = ""
    category: DataCategory = DataCategory.PERSONAL
    visibility: SpaceVisibility = SpaceVisibility.PRIVATE
    members: dict[str, SpaceRole] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    document_count: int = 0
    memory_count: int = 0
    size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "category": self.category.value,
            "visibility": self.visibility.value,
            "members": {k: v.value for k, v in self.members.items()},
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "document_count": self.document_count,
            "memory_count": self.memory_count,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> KnowledgeSpace:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            color=data.get("color", ""),
            category=DataCategory(data.get("category", "personal")),
            visibility=SpaceVisibility(data.get("visibility", "private")),
            members={k: SpaceRole(v) for k, v in data.get("members", {}).items()},
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            document_count=data.get("document_count", 0),
            memory_count=data.get("memory_count", 0),
            size_bytes=data.get("size_bytes", 0),
        )


class KnowledgeSpaceManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "spaces_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._spaces: dict[str, KnowledgeSpace] = {}
        self._load()
        if "default" not in self._spaces:
            self.create_space("Default", DataCategory.PERSONAL, "default", "Default workspace")

    def _path(self) -> Path:
        return self._storage_path / "knowledge_spaces.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                for item in data:
                    space = KnowledgeSpace.from_dict(item)
                    self._spaces[space.id] = space
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([s.to_dict() for s in self._spaces.values()], indent=2, default=str), "utf-8")

    def _generate_id(self) -> str:
        import uuid
        return f"space_{uuid.uuid4().hex[:8]}"

    def create_space(self, name: str, category: DataCategory = DataCategory.PERSONAL,
                     icon: str = "", description: str = "",
                     visibility: SpaceVisibility = SpaceVisibility.PRIVATE) -> KnowledgeSpace:
        now = datetime.now().isoformat()
        space_id = self._generate_id()
        space = KnowledgeSpace(
            id=space_id,
            name=name,
            description=description,
            icon=icon,
            category=category,
            visibility=visibility,
            created_at=now,
            updated_at=now,
        )
        self._spaces[space_id] = space
        self._save()
        return space

    def get_space(self, space_id: str) -> Optional[KnowledgeSpace]:
        return self._spaces.get(space_id)

    def update_space(self, space_id: str, **updates) -> Optional[KnowledgeSpace]:
        space = self._spaces.get(space_id)
        if not space:
            return None
        for key, value in updates.items():
            if hasattr(space, key) and key != "id":
                if key == "category":
                    setattr(space, key, DataCategory(value) if isinstance(value, str) else value)
                elif key == "visibility":
                    setattr(space, key, SpaceVisibility(value) if isinstance(value, str) else value)
                else:
                    setattr(space, key, value)
        space.updated_at = datetime.now().isoformat()
        self._save()
        return space

    def delete_space(self, space_id: str) -> bool:
        if space_id == "default" or space_id not in self._spaces:
            return False
        del self._spaces[space_id]
        self._save()
        return True

    def list_spaces(self, category: Optional[DataCategory] = None) -> list[KnowledgeSpace]:
        results = list(self._spaces.values())
        if category:
            results = [s for s in results if s.category == category]
        return sorted(results, key=lambda x: x.name)

    def add_member(self, space_id: str, user_id: str, role: SpaceRole = SpaceRole.VIEWER) -> bool:
        space = self._spaces.get(space_id)
        if not space:
            return False
        space.members[user_id] = role
        space.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def remove_member(self, space_id: str, user_id: str) -> bool:
        space = self._spaces.get(space_id)
        if not space or user_id not in space.members:
            return False
        del space.members[user_id]
        space.updated_at = datetime.now().isoformat()
        self._save()
        return True

    def get_user_spaces(self, user_id: str) -> list[KnowledgeSpace]:
        return [s for s in self._spaces.values() if user_id in s.members or s.visibility != SpaceVisibility.PRIVATE]

    def check_access(self, space_id: str, user_id: str, required_role: SpaceRole = SpaceRole.VIEWER) -> bool:
        space = self._spaces.get(space_id)
        if not space:
            return False
        if space.visibility == SpaceVisibility.PUBLIC:
            return True
        if user_id not in space.members:
            return space.visibility in (SpaceVisibility.SHARED_READ, SpaceVisibility.SHARED_WRITE)
        role = space.members[user_id]
        hierarchy = {SpaceRole.OWNER: 4, SpaceRole.ADMIN: 3, SpaceRole.EDITOR: 2, SpaceRole.CONTRIBUTOR: 1, SpaceRole.VIEWER: 0}
        return hierarchy.get(role, 0) >= hierarchy.get(required_role, 0)

    def get_spaces_by_category(self, category: DataCategory) -> list[KnowledgeSpace]:
        return [s for s in self._spaces.values() if s.category == category]
