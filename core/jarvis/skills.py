from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
import importlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    enabled: bool = True
    path: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class SkillsManager:
    def __init__(self, skills_dir: Optional[Path] = None):
        self._skills_dir = skills_dir or Path.home() / ".aetheros" / "skills"
        self._builtin_dir = Path(__file__).parent.parent.parent / "skills"
        self._lock = threading.Lock()
        self._skills: dict[str, Skill] = {}
        self._enabled_skills: set[str] = set()

    def load_builtin(self):
        self._scan_directory(self._builtin_dir, builtin=True)
        self._scan_directory(self._skills_dir, builtin=False)

    def _scan_directory(self, directory: Path, builtin: bool = False):
        if not directory.exists():
            return
        try:
            for skill_dir in directory.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        try:
                            content = skill_md.read_text()
                            name = self._parse_field(content, "name") or skill_dir.name
                            description = self._parse_field(content, "description") or ""
                            category = self._parse_field(content, "category") or "general"
                            skill = Skill(
                                name=name,
                                description=description,
                                category=category,
                                path=str(skill_dir),
                                enabled=builtin,
                            )
                            with self._lock:
                                self._skills[name] = skill
                                if builtin:
                                    self._enabled_skills.add(name)
                        except Exception as e:
                            logger.debug(f"Could not load skill from {skill_dir}: {e}")
        except Exception as e:
            logger.debug(f"Could not scan skills directory {directory}: {e}")

    def _parse_field(self, content: str, field: str) -> Optional[str]:
        import re
        match = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def get_skill(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def get_all(self) -> list[Skill]:
        with self._lock:
            return sorted(self._skills.values(), key=lambda s: s.name)

    def get_by_category(self, category: str) -> list[Skill]:
        with self._lock:
            return sorted(
                [s for s in self._skills.values() if s.category == category],
                key=lambda s: s.name,
            )

    def get_categories(self) -> list[str]:
        with self._lock:
            return sorted(set(s.category for s in self._skills.values()))

    def enable(self, name: str) -> bool:
        with self._lock:
            if name in self._skills:
                self._enabled_skills.add(name)
                self._skills[name].enabled = True
                return True
            return False

    def disable(self, name: str) -> bool:
        with self._lock:
            if name in self._skills:
                self._enabled_skills.discard(name)
                self._skills[name].enabled = False
                return True
            return False

    def is_enabled(self, name: str) -> bool:
        with self._lock:
            return name in self._enabled_skills

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total": len(self._skills),
                "enabled": len(self._enabled_skills),
                "categories": len(self.get_categories()),
            }
