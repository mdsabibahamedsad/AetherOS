from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class ProjectStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ARCHIVED = "archived"
    PLANNING = "planning"


@dataclass
class ProjectKnowledge:
    id: str
    name: str
    description: str = ""
    status: str = ProjectStatus.ACTIVE
    goals: list[str] = field(default_factory=list)
    file_count: int = 0
    task_count: int = 0
    completed_tasks: int = 0
    conversation_count: int = 0
    decisions: list[dict] = field(default_factory=list)
    important_people: list[str] = field(default_factory=list)
    open_problems: list[str] = field(default_factory=list)
    recent_activity: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "goals": self.goals,
            "file_count": self.file_count,
            "task_count": self.task_count,
            "completed_tasks": self.completed_tasks,
            "conversation_count": self.conversation_count,
            "decisions": self.decisions,
            "important_people": self.important_people,
            "open_problems": self.open_problems,
            "recent_activity": self.recent_activity[-50:],
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ProjectIntelligence:
    def __init__(self):
        self._projects: dict[str, ProjectKnowledge] = {}

    def register_project(self, project_id: str, name: str, description: str = "",
                         goals: list[str] | None = None, tags: list[str] | None = None) -> ProjectKnowledge:
        now = datetime.now().isoformat()
        project = ProjectKnowledge(
            id=project_id,
            name=name,
            description=description,
            goals=goals or [],
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        self._projects[project_id] = project
        return project

    def get_project(self, project_id: str) -> Optional[ProjectKnowledge]:
        return self._projects.get(project_id)

    def update_project(self, project_id: str, **updates) -> Optional[ProjectKnowledge]:
        project = self._projects.get(project_id)
        if not project:
            return None
        for key, value in updates.items():
            if hasattr(project, key) and key != "id":
                setattr(project, key, value)
        project.updated_at = datetime.now().isoformat()
        return project

    def record_decision(self, project_id: str, decision: str, rationale: str = "",
                        made_by: str = "") -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        project.decisions.append({
            "description": decision,
            "rationale": rationale,
            "made_by": made_by,
            "date": datetime.now().isoformat(),
        })
        project.updated_at = datetime.now().isoformat()
        return True

    def record_activity(self, project_id: str, activity_type: str, description: str):
        project = self._projects.get(project_id)
        if not project:
            return
        project.recent_activity.append({
            "type": activity_type,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        })
        project.updated_at = datetime.now().isoformat()

    def add_open_problem(self, project_id: str, problem: str) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        if problem not in project.open_problems:
            project.open_problems.append(problem)
            project.updated_at = datetime.now().isoformat()
        return True

    def resolve_open_problem(self, project_id: str, problem: str) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        if problem in project.open_problems:
            project.open_problems.remove(problem)
            project.updated_at = datetime.now().isoformat()
            return True
        return False

    def get_project_summary(self, project_id: str) -> dict:
        project = self._projects.get(project_id)
        if not project:
            return {"error": "Project not found"}
        progress = 0
        if project.task_count > 0:
            progress = int((project.completed_tasks / project.task_count) * 100)
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "progress_pct": progress,
            "goals": project.goals,
            "file_count": project.file_count,
            "task_summary": f"{project.completed_tasks}/{project.task_count} tasks completed",
            "decisions_count": len(project.decisions),
            "open_problems_count": len(project.open_problems),
            "recent_activity": project.recent_activity[-5:] if project.recent_activity else [],
            "last_updated": project.updated_at,
        }

    def search_projects(self, query: str = "") -> list[ProjectKnowledge]:
        if not query:
            return list(self._projects.values())
        q = query.lower()
        return [p for p in self._projects.values()
                if q in p.name.lower() or q in p.description.lower()
                or any(q in g.lower() for g in p.goals)
                or any(q in t.lower() for t in p.tags)]

    def get_all_projects(self, status: str = "") -> list[ProjectKnowledge]:
        if status:
            return [p for p in self._projects.values() if p.status == status]
        return list(self._projects.values())

    def delete_project(self, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        del self._projects[project_id]
        return True
