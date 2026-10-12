from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._dirty: bool = False
        self._store_path = self._default_store_path()
        self._load()

    @property
    def role(self) -> AgentRole:
        return AgentRole.MEMORY

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("Memory agent executing: %s", task.name)

        desc = task.description.lower()

        if "remember" in desc or "store" in desc:
            key = task.metadata.get("key", task.name)
            value = task.metadata.get("value", task.description)
            await self.remember(key, value)
            return f"Stored '{key}'."

        if "recall" in desc or "get" in desc or "retrieve" in desc:
            key = task.metadata.get("key", task.name)
            value = await self.recall(key)
            if value is not None:
                formatted = json.dumps(value, indent=2) if not isinstance(value, str) else value
                return f"# Memory: {key}\n{formatted}"
            return f"No value found for '{key}'."

        if "clear" in desc or "reset" in desc:
            self._store.clear()
            self._dirty = True
            self._save()
            return "Memory cleared."

        context_data = await self.get_context_for_task(task)
        return json.dumps(context_data, indent=2)

    async def remember(self, key: str, value: Any) -> None:
        logger.info("Remembering %s", key)
        self._store[key] = value
        self._dirty = True
        self._save()

    async def recall(self, key: str) -> Any:
        logger.info("Recalling %s", key)
        return self._store.get(key)

    async def get_context_for_task(self, task: Task) -> dict:
        logger.info("Building context for task: %s", task.name)
        related: dict[str, Any] = {}

        desc_lower = task.description.lower()
        desc_words = set(desc_lower.split())

        for key, value in self._store.items():
            key_lower = key.lower()
            key_words = set(key_lower.replace("_", " ").split())
            if desc_words & key_words or any(w in key_lower for w in desc_words):
                related[key] = value

        return {
            "task_id": task.id,
            "task_name": task.name,
            "context_keys": list(self._store.keys()),
            "related_memories": related,
            "memory_count": len(self._store),
        }

    def _default_store_path(self) -> Path:
        try:
            from aetheros_constants import get_aetheros_home
            base = get_aetheros_home()
        except ImportError:
            base = Path(os.getenv("AETHEROS_HOME", Path.home() / ".aetheros"))
        return base / "automation_memory.json"

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = self._store_path.read_text(encoding="utf-8")
                self._store = json.loads(data)
                logger.info("Loaded %d memory entries", len(self._store))
        except Exception as e:
            logger.warning("Failed to load memory store: %s", e)
            self._store = {}

    def _save(self) -> None:
        if not self._dirty:
            return
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(
                json.dumps(self._store, indent=2, default=str),
                encoding="utf-8",
            )
            self._dirty = False
            logger.info("Memory store saved (%d entries)", len(self._store))
        except Exception as e:
            logger.warning("Failed to save memory store: %s", e)


AgentRegistry.register(AgentRole.MEMORY, MemoryAgent)
