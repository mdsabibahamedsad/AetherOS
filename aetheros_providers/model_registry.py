"""Default Model Registry — per-task model assignments.

Assigns different models to different tasks:
Main Chat, Vision, Coding, Planning, Research, Compression,
Browser, Voice, Title Generation, MCP, Automation.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetheros_providers.registry")


class TaskType(enum.Enum):
    MAIN_CHAT = "main_chat"
    VISION = "vision"
    CODING = "coding"
    PLANNING = "planning"
    RESEARCH = "research"
    COMPRESSION = "compression"
    BROWSER = "browser"
    VOICE = "voice"
    TITLE_GENERATION = "title_generation"
    MCP = "mcp"
    AUTOMATION = "automation"
    EMBEDDINGS = "embeddings"
    SUMMARIZATION = "summarization"
    RERANKING = "reranking"
    IMAGE_GENERATION = "image_generation"
    TRANSCRIPTION = "transcription"
    SPEECH = "speech"


@dataclass
class ModelAssignment:
    task: TaskType
    provider: str
    model_id: str
    display_name: str = ""
    is_active: bool = True
    assigned_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


DEFAULT_TASK_PROVIDERS: Dict[TaskType, str] = {
    TaskType.MAIN_CHAT: "openai",
    TaskType.VISION: "openai",
    TaskType.CODING: "anthropic",
    TaskType.PLANNING: "openai",
    TaskType.RESEARCH: "openai",
    TaskType.COMPRESSION: "openai",
    TaskType.BROWSER: "openai",
    TaskType.VOICE: "openai",
    TaskType.TITLE_GENERATION: "openai",
    TaskType.MCP: "openai",
    TaskType.AUTOMATION: "openai",
    TaskType.EMBEDDINGS: "openai",
    TaskType.SUMMARIZATION: "openai",
    TaskType.RERANKING: "cohere",
    TaskType.IMAGE_GENERATION: "openai",
    TaskType.TRANSCRIPTION: "openai",
    TaskType.SPEECH: "openai",
}

DEFAULT_TASK_MODELS: Dict[TaskType, str] = {
    TaskType.MAIN_CHAT: "gpt-4o",
    TaskType.VISION: "gpt-4o",
    TaskType.CODING: "claude-sonnet-4",
    TaskType.PLANNING: "o3-mini",
    TaskType.RESEARCH: "gpt-4o",
    TaskType.COMPRESSION: "gpt-4o-mini",
    TaskType.BROWSER: "gpt-4o",
    TaskType.VOICE: "gpt-4o-mini",
    TaskType.TITLE_GENERATION: "gpt-4o-mini",
    TaskType.MCP: "gpt-4o-mini",
    TaskType.AUTOMATION: "gpt-4o-mini",
    TaskType.EMBEDDINGS: "text-embedding-3-small",
    TaskType.SUMMARIZATION: "gpt-4o-mini",
    TaskType.RERANKING: "rerank-english-v3.0",
    TaskType.IMAGE_GENERATION: "dall-e-3",
    TaskType.TRANSCRIPTION: "whisper-1",
    TaskType.SPEECH: "tts-1",
}


class DefaultModelRegistry:
    """Manages default model assignments per task type.

    Each task can have a different provider and model.
    Supports dynamic reassignment and multi-provider workflows.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._assignments: Dict[TaskType, ModelAssignment] = {}
        self._task_names: Dict[TaskType, str] = {
            TaskType.MAIN_CHAT: "Main Chat",
            TaskType.VISION: "Vision",
            TaskType.CODING: "Coding",
            TaskType.PLANNING: "Planning",
            TaskType.RESEARCH: "Research",
            TaskType.COMPRESSION: "Compression",
            TaskType.BROWSER: "Browser",
            TaskType.VOICE: "Voice",
            TaskType.TITLE_GENERATION: "Title Generation",
            TaskType.MCP: "MCP",
            TaskType.AUTOMATION: "Automation",
            TaskType.EMBEDDINGS: "Embeddings",
            TaskType.SUMMARIZATION: "Summarization",
            TaskType.RERANKING: "Reranking",
            TaskType.IMAGE_GENERATION: "Image Generation",
            TaskType.TRANSCRIPTION: "Transcription",
            TaskType.SPEECH: "Speech",
        }
        self._load_defaults()

    def _load_defaults(self) -> None:
        for task in TaskType:
            self._assignments[task] = ModelAssignment(
                task=task,
                provider=DEFAULT_TASK_PROVIDERS.get(task, "openai"),
                model_id=DEFAULT_TASK_MODELS.get(task, "gpt-4o"),
                display_name=self._task_names.get(task, task.value),
            )

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def assign(self, task: TaskType, provider: str, model_id: str) -> ModelAssignment:
        with self._lock:
            assignment = ModelAssignment(
                task=task,
                provider=provider,
                model_id=model_id,
                display_name=self._task_names.get(task, task.value),
            )
            self._assignments[task] = assignment
            logger.info("Model assigned: %s → %s/%s", task.value, provider, model_id)
            return assignment

    def get_assignment(self, task: TaskType) -> Optional[ModelAssignment]:
        with self._lock:
            return self._assignments.get(task)

    def get_provider(self, task: TaskType) -> str:
        assignment = self.get_assignment(task)
        return assignment.provider if assignment else "openai"

    def get_model(self, task: TaskType) -> str:
        assignment = self.get_assignment(task)
        return assignment.model_id if assignment else "gpt-4o"

    def get_provider_and_model(self, task: TaskType) -> tuple:
        assignment = self.get_assignment(task)
        if assignment:
            return (assignment.provider, assignment.model_id)
        return ("openai", "gpt-4o")

    def reset_to_default(self, task: Optional[TaskType] = None) -> None:
        with self._lock:
            if task:
                self._assignments[task] = ModelAssignment(
                    task=task,
                    provider=DEFAULT_TASK_PROVIDERS.get(task, "openai"),
                    model_id=DEFAULT_TASK_MODELS.get(task, "gpt-4o"),
                    display_name=self._task_names.get(task, task.value),
                )
            else:
                self._load_defaults()

    # ------------------------------------------------------------------
    # Task descriptions
    # ------------------------------------------------------------------

    def get_task_display_name(self, task: TaskType) -> str:
        return self._task_names.get(task, task.value)

    def set_task_display_name(self, task: TaskType, name: str) -> None:
        with self._lock:
            self._task_names[task] = name

    def list_tasks(self) -> List[TaskType]:
        return list(TaskType)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def assign_bulk(self, assignments: Dict[TaskType, tuple]) -> None:
        for task, (provider, model) in assignments.items():
            self.assign(task, provider, model)

    def get_all_assignments(self) -> Dict[str, Dict[str, str]]:
        result = {}
        with self._lock:
            for task, assignment in self._assignments.items():
                name = self._task_names.get(task, task.value)
                result[name] = {
                    "task": task.value,
                    "provider": assignment.provider,
                    "model": assignment.model_id,
                }
        return result

    def to_config_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                assignment.task.value: {
                    "provider": assignment.provider,
                    "model": assignment.model_id,
                }
                for assignment in self._assignments.values()
            }

    def from_config_dict(self, config: Dict[str, Any]) -> None:
        for task_value, mapping in config.items():
            try:
                task = TaskType(task_value)
                self.assign(task, mapping.get("provider", "openai"), mapping.get("model", "gpt-4o"))
            except (ValueError, KeyError):
                logger.warning("Unknown task type in config: %s", task_value)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = ["Default Model Assignments:"]
        with self._lock:
            for task in TaskType:
                assignment = self._assignments.get(task)
                if assignment:
                    lines.append(
                        f"  {self._task_names.get(task, task.value):20s}"
                        f" → {assignment.provider:15s} / {assignment.model_id}"
                    )
        return "\n".join(lines)