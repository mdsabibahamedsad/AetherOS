from __future__ import annotations
import json, logging, os, time, uuid, shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class ProjectMetadata:
    id: str = ""
    name: str = ""
    path: str = ""
    language: str = ""
    framework: str = ""
    description: str = ""
    version: str = "1.0.0"
    created_at: float = 0.0
    updated_at: float = 0.0
    last_opened_at: float = 0.0
    tags: list[str] = field(default_factory=list)
    is_favorite: bool = False
    git_url: str = ""
    build_system: str = ""
    test_framework: str = ""
    package_manager: str = ""
    icon: str = "code"

class ProjectManager:
    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or os.path.expanduser("~/.aetheros/developer/projects")
        self._workspaces_dir = os.path.expanduser("~/.aetheros/developer/workspaces")
        os.makedirs(self._data_dir, exist_ok=True)
        os.makedirs(self._workspaces_dir, exist_ok=True)
        self._recent: list[str] = self._load_recent()
        self._favorites: list[str] = self._load_favorites()

    def create_project(self, name: str, path: str, language: str = "", framework: str = "", description: str = "") -> ProjectMetadata:
        project_id = uuid.uuid4().hex[:12]
        meta = ProjectMetadata(id=project_id, name=name, path=os.path.abspath(path), language=language, framework=framework, description=description, created_at=time.time(), updated_at=time.time())
        os.makedirs(meta.path, exist_ok=True)
        self._save_metadata(meta)
        self._add_recent(project_id)
        return meta

    def open_project(self, path: str) -> ProjectMetadata | None:
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return None
        existing = self._find_by_path(path)
        if existing:
            existing.last_opened_at = time.time()
            self._save_metadata(existing)
            self._add_recent(existing.id)
            return existing
        name = os.path.basename(path)
        lang = self._detect_language(path)
        framework = self._detect_framework(path, lang)
        project_id = uuid.uuid4().hex[:12]
        meta = ProjectMetadata(id=project_id, name=name, path=path, language=lang, framework=framework, created_at=time.time(), updated_at=time.time(), last_opened_at=time.time())
        self._save_metadata(meta)
        self._add_recent(project_id)
        return meta

    def import_project(self, name: str, source_path: str, dest_path: str) -> ProjectMetadata:
        src = os.path.abspath(source_path)
        dst = os.path.abspath(os.path.join(dest_path, name))
        if os.path.exists(dst):
            raise FileExistsError(f"Target path {dst} already exists")
        shutil.copytree(src, dst)
        return self.open_project(dst)

    def clone_repository(self, url: str, dest_path: str, branch: str = "") -> ProjectMetadata:
        import subprocess
        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        dst = os.path.abspath(os.path.join(dest_path, repo_name))
        if os.path.exists(dst):
            raise FileExistsError(f"Target path {dst} already exists")
        cmd = ["git", "clone", url, dst]
        if branch:
            cmd.extend(["-b", branch])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")
        return self.open_project(dst)

    def get_project(self, project_id: str) -> ProjectMetadata | None:
        return self._load_metadata(project_id)

    def list_projects(self) -> list[ProjectMetadata]:
        projects = []
        for name in os.listdir(self._data_dir):
            if name.endswith(".json"):
                meta = self._load_metadata(name[:-5])
                if meta:
                    projects.append(meta)
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def get_recent_projects(self, limit: int = 10) -> list[ProjectMetadata]:
        projects = []
        for pid in self._recent[:limit]:
            meta = self._load_metadata(pid)
            if meta:
                projects.append(meta)
        return projects

    def get_favorite_projects(self) -> list[ProjectMetadata]:
        projects = []
        for pid in self._favorites:
            meta = self._load_metadata(pid)
            if meta:
                projects.append(meta)
        return projects

    def toggle_favorite(self, project_id: str) -> bool:
        meta = self._load_metadata(project_id)
        if not meta:
            return False
        meta.is_favorite = not meta.is_favorite
        self._save_metadata(meta)
        if meta.is_favorite:
            if project_id not in self._favorites:
                self._favorites.append(project_id)
        else:
            self._favorites = [f for f in self._favorites if f != project_id]
        self._save_favorites()
        return meta.is_favorite

    def delete_project(self, project_id: str) -> bool:
        path = os.path.join(self._data_dir, f"{project_id}.json")
        if os.path.isfile(path):
            os.remove(path)
        self._recent = [r for r in self._recent if r != project_id]
        self._favorites = [f for f in self._favorites if f != project_id]
        self._save_recent()
        self._save_favorites()
        return True

    def update_project(self, project_id: str, **kwargs) -> ProjectMetadata | None:
        meta = self._load_metadata(project_id)
        if not meta:
            return None
        for key, val in kwargs.items():
            if hasattr(meta, key):
                setattr(meta, key, val)
        meta.updated_at = time.time()
        self._save_metadata(meta)
        return meta

    def _detect_language(self, path: str) -> str:
        """Detect primary language from project files."""
        scores: dict[str, int] = {}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith((".", "node_modules", "__pycache__", "venv", ".venv", "target", "build", "dist"))]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                lang_map = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".jsx": "JavaScript", ".tsx": "TypeScript",
                    ".rs": "Rust", ".go": "Go", ".java": "Java", ".c": "C", ".cpp": "C++", ".h": "C", ".hpp": "C++",
                    ".html": "HTML", ".css": "CSS", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
                    ".md": "Markdown", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
                    ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin",
                    ".cs": "C#", ".ex": "Elixir", ".exs": "Elixir",
                }
                lang = lang_map.get(ext)
                if lang:
                    scores[lang] = scores.get(lang, 0) + 1
            if root != path and len(os.listdir(root)) == 0:
                continue
        return max(scores, key=scores.get) if scores else "Unknown"

    def _detect_framework(self, path: str, language: str) -> str:
        files = set()
        for root, _, fnames in os.walk(path):
            files.update(fnames)
        checks = {
            "react": lambda f: "package.json" in f,
            "next.js": lambda f: "next.config.js" in f or "next.config.ts" in f,
            "vue": lambda f: "vue.config.js" in f,
            "django": lambda f: "manage.py" in f,
            "flask": lambda f: "app.py" in f or "wsgi.py" in f,
            "fastapi": lambda f: "main.py" in f,
            "spring": lambda f: "pom.xml" in f or "build.gradle" in f,
            "rails": lambda f: "Gemfile" in f and "Rakefile" in f,
            "express": lambda f: "package.json" in f and "app.js" in files,
        }
        for name, check in checks.items():
            if check(files):
                return name
        return ""

    def _find_by_path(self, path: str) -> ProjectMetadata | None:
        norm = os.path.normpath(path)
        for name in os.listdir(self._data_dir):
            if name.endswith(".json"):
                meta = self._load_metadata(name[:-5])
                if meta and os.path.normpath(meta.path) == norm:
                    return meta
        return None

    def _load_metadata(self, project_id: str) -> ProjectMetadata | None:
        path = os.path.join(self._data_dir, f"{project_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return ProjectMetadata(**data)
        except Exception:
            return None

    def _save_metadata(self, meta: ProjectMetadata):
        path = os.path.join(self._data_dir, f"{meta.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2, default=str)

    def _add_recent(self, project_id: str):
        self._recent = [project_id] + [r for r in self._recent if r != project_id]
        self._save_recent()

    def _load_recent(self) -> list[str]:
        path = os.path.join(self._data_dir, "_recent.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f: return json.load(f)
            except Exception: pass
        return []

    def _save_recent(self):
        with open(os.path.join(self._data_dir, "_recent.json"), "w", encoding="utf-8") as f:
            json.dump(self._recent[:50], f)

    def _load_favorites(self) -> list[str]:
        path = os.path.join(self._data_dir, "_favorites.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f: return json.load(f)
            except Exception: pass
        return []

    def _save_favorites(self):
        with open(os.path.join(self._data_dir, "_favorites.json"), "w", encoding="utf-8") as f:
            json.dump(self._favorites, f)
