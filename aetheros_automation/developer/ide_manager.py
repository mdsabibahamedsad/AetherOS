from __future__ import annotations
import logging, os
from typing import Any

from aetheros_automation.developer.project_manager import ProjectManager
from aetheros_automation.developer.code_indexer import CodeIndexer
from aetheros_automation.developer.task_runner import TaskRunner
from aetheros_automation.developer.process_manager import ProcessManager
from aetheros_automation.developer.debug_client import DebugClient
from aetheros_automation.developer.git_integration import GitIntegration
from aetheros_automation.developer.code_review_engine import CodeReviewEngine
from aetheros_automation.developer.dependency_manager import DependencyManager
from aetheros_automation.developer.project_generator import ProjectGenerator
from aetheros_automation.developer.ai_coding_assistant import AICodingAssistant

logger = logging.getLogger(__name__)

class IDEManager:
    def __init__(self):
        self.project_manager = ProjectManager()
        self.code_indexer = CodeIndexer()
        self.task_runner = TaskRunner()
        self.process_manager = ProcessManager()
        self.debug_client = DebugClient()
        self.git_integration = GitIntegration()
        self.code_review_engine = CodeReviewEngine()
        self.dependency_manager = DependencyManager()
        self.project_generator = ProjectGenerator()
        self.ai_coding = AICodingAssistant()
        self._active_project_id: str = ""
        self._active_file: str = ""
        self._open_files: list[str] = []

    @property
    def active_project_id(self) -> str:
        return self._active_project_id

    @active_project_id.setter
    def active_project_id(self, value: str):
        self._active_project_id = value

    def open_file(self, file_path: str):
        if file_path not in self._open_files:
            self._open_files.append(file_path)
        self._active_file = file_path

    def close_file(self, file_path: str):
        if file_path in self._open_files:
            self._open_files.remove(file_path)
        if self._active_file == file_path and self._open_files:
            self._active_file = self._open_files[-1]

    def get_open_files(self) -> list[str]:
        return list(self._open_files)

    def get_ide_status(self) -> dict[str, Any]:
        return {
            "projects": len(self.project_manager.list_projects()),
            "active_project": self._active_project_id,
            "open_files": len(self._open_files),
            "active_file": self._active_file,
            "running_processes": len(self.process_manager.list_processes()),
            "git_available": self.git_integration._git_available,
        }
