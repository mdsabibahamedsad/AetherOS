from __future__ import annotations

import logging
import time
from typing import Any, Optional

from aetheros_automation.orchestrator.models import Plan, OrchestrationTask

logger = logging.getLogger(__name__)


class OrchestratorMemory:
    def __init__(self):
        self._conversation_memory: dict[str, list[dict]] = {}
        self._task_memory: dict[str, dict] = {}
        self._long_term: dict[str, dict] = {}

    def store_conversation(self, agent_id: str, role: str, content: str):
        if agent_id not in self._conversation_memory:
            self._conversation_memory[agent_id] = []
        self._conversation_memory[agent_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })

    def get_conversation(self, agent_id: str, limit: int = 50) -> list[dict]:
        return self._conversation_memory.get(agent_id, [])[-limit:]

    def store_task_result(
        self, task_id: str, result: dict, plan_id: str = ""
    ):
        self._task_memory[task_id] = {
            "result": result,
            "plan_id": plan_id,
            "timestamp": time.time(),
        }

    def get_task_result(self, task_id: str) -> Optional[dict]:
        entry = self._task_memory.get(task_id)
        return entry["result"] if entry else None

    def store_knowledge(self, key: str, data: dict):
        self._long_term[key] = {
            "data": data,
            "timestamp": time.time(),
            "access_count": 0,
        }

    def retrieve_knowledge(self, key: str) -> Optional[dict]:
        entry = self._long_term.get(key)
        if entry:
            entry["access_count"] = entry.get("access_count", 0) + 1
            return entry["data"]
        return None

    def search_knowledge(self, query: str) -> list[dict]:
        query_lower = query.lower()
        results = []
        for key, entry in self._long_term.items():
            if query_lower in key.lower():
                results.append({
                    "key": key,
                    "data": entry["data"],
                    "timestamp": entry["timestamp"],
                })
        return results[:10]

    def clear_agent_memory(self, agent_id: str):
        self._conversation_memory.pop(agent_id, None)

    def clear_all(self):
        self._conversation_memory.clear()
        self._task_memory.clear()
        self._long_term.clear()

    def get_stats(self) -> dict:
        return {
            "conversation_entries": sum(len(v) for v in self._conversation_memory.values()),
            "conversation_agents": len(self._conversation_memory),
            "task_results": len(self._task_memory),
            "long_term_entries": len(self._long_term),
        }
